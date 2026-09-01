"""SINDESTIVA-PE · Job scheduler (Sprint 6 T6-03 + T6-06).

Centraliza a execução de jobs assíncronos via APScheduler:
- `hash_chain_verifier` (T6-03): roda diariamente às 03:00 (Sprint 6)
  - Recalcula SHA-256 de toda a cadeia de `audit_events`
  - Grava resultado em `hash_chain_checkpoint`
  - Se `integro = false`, alerta (e-mail para DPO — futuro)
- `lgpd_purge` (T6-06): roda diariamente às 04:00 (Sprint 6)
  - Deleta linhas onde `purge_after < now()` em TODAS as tabelas com
    esse campo
  - Grava log imutável em `lgpd_purge_log` (audit do audit)
  - Preserva referência histórica (id + tabela)

Pega-dica: usar APScheduler 3.x AsyncIOScheduler pra rodar dentro do
event loop FastAPI sem asyncio.run (lembrete cross-projeto).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import session_scope
from app.core.logging import get_logger
from app.models import (
    AccessLog,
    AuditEvent,
    HashChainCheckpoint,
    LgpdPurgeLog,
)
from app.services.hash_chain import GENESIS_HASH, verify_chain

log = get_logger(__name__)

# Singleton scheduler
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Retorna o scheduler singleton (lazy init)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="America/Recife")
    return _scheduler


async def start_scheduler() -> None:
    """Inicia o scheduler com os jobs Sprint 6. Idempotente."""
    scheduler = get_scheduler()
    if scheduler.running:
        log.info("scheduler.ja_rodando")
        return

    # T6-03: hash chain verifier — diariamente às 03:00 (America/Recife)
    scheduler.add_job(
        _job_hash_chain_verifier,
        CronTrigger(hour=3, minute=0, timezone="America/Recife"),
        id="hash_chain_verifier",
        name="Hash Chain Verifier (T6-03)",
        replace_existing=True,
        max_instances=1,
    )

    # T6-06: LGPD purge — diariamente às 04:00 (America/Recife)
    scheduler.add_job(
        _job_lgpd_purge,
        CronTrigger(hour=4, minute=0, timezone="America/Recife"),
        id="lgpd_purge",
        name="LGPD Purge 24m (T6-06)",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    log.info(
        "scheduler.iniciado",
        jobs=[
            j.id
            for j in scheduler.get_jobs()
        ],
    )


async def stop_scheduler() -> None:
    """Para o scheduler gracefully."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("scheduler.parado")


# ---------------------------------------------------------------------------
# T6-03: Hash Chain Verifier
# ---------------------------------------------------------------------------

async def _job_hash_chain_verifier() -> dict:
    """Verifica integridade de TODA a cadeia de audit_events.

    Janela: varre a tabela inteira (em prod, Sprint 6 + monitoria
    pode limitar a últimas 24h pra performance). Pra MVP, varre tudo.

    Returns:
        Dict com `integro`, `total_eventos`, `primeiro_evento_com_falha`,
        `duracao_ms`. Usado pra criar o `HashChainCheckpoint`.
    """
    started = datetime.now(tz=timezone.utc)
    log.info("hash_chain_verifier.iniciado")

    async with session_scope() as db:
        # Carrega todos os eventos ordenados
        stmt = select(AuditEvent).order_by(AuditEvent.sequencia)
        result = await db.execute(stmt)
        events = list(result.scalars().all())

        integro, idx_falha = verify_chain(events)
        duracao_ms = int((datetime.now(tz=timezone.utc) - started).total_seconds() * 1000)

        # Calcula hash final pra checkpoint
        if events:
            hash_final = events[-1].hash_evento
            primeiro_seq = events[0].sequencia
            ultimo_seq = events[-1].sequencia
        else:
            hash_final = GENESIS_HASH
            primeiro_seq = 0
            ultimo_seq = 0

        # Grava checkpoint
        ckpt = HashChainCheckpoint(
            executado_em=started,
            executado_por="JOB_DIARIO",
            total_eventos_verificados=len(events),
            primeiro_sequencia=primeiro_seq,
            ultimo_sequencia=ultimo_seq,
            hash_calculado_final=hash_final,
            hash_esperado_final=hash_final,
            integro=integro,
            primeiro_evento_com_falha=idx_falha if not integro else None,
            duracao_ms=duracao_ms,
            alerta_enviado=False,
        )
        db.add(ckpt)
        await db.commit()

        log.info(
            "hash_chain_verifier.finalizado",
            integro=integro,
            total=len(events),
            idx_falha=idx_falha,
            duracao_ms=duracao_ms,
        )

        if not integro:
            log.error(
                "hash_chain_verifier.FALHA_DETECTADA",
                idx_falha=idx_falha,
                sequencia_afetada=events[idx_falha].sequencia if idx_falha is not None and idx_falha < len(events) else None,
            )
            # TODO: enviar alerta por e-mail pro DPO (S6 - Risco R3)
            # await send_alert_dpo(...)

        return {
            "integro": integro,
            "total_eventos": len(events),
            "primeiro_evento_com_falha": idx_falha,
            "duracao_ms": duracao_ms,
        }


# ---------------------------------------------------------------------------
# T6-06: LGPD Purge
# ---------------------------------------------------------------------------

# Tabelas com coluna `purge_after` + `deleted_at` (DD v1)
# NOTA: `remanejamento_historico` e `audit_events` são append-only (NÃO
# têm `deleted_at`) — não entram na lista. Outras tabelas com
# `SoftDeleteMixin` automaticamente têm `deleted_at` + `purge_after`.
# Em S6+ isso pode virar introspection automática do schema.
TABELAS_COM_PURGE: list[str] = [
    "users",
    "tpas",
    "fiscais",
    "dirigentes",
    "remanejamentos",
    "ogmo_notificacoes",
    "ogmo_webhook_endpoints",
    "tpa_confirmacoes_presenca",
    "lgpd_solicitacoes",
]


async def _job_lgpd_purge() -> dict:
    """Deleta linhas com `purge_after < now()` em todas as tabelas configuradas.

    Preserva referência histórica via `lgpd_purge_log` (id + tabela +
    hash do lote).

    **Importante**: cada tabela roda em sua PRÓPRIA transação/sessão
    (via `session_scope()` por iteração), pq se uma falha (ex: tabela
    sem `deleted_at`), a transação inteira abortaria.

    Returns:
        Dict com `total_deletados`, `por_tabela` (dict), `job_id`,
        `criterio`, `hash_lote_sha256`.
    """
    job_id = f"purge-{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    started = datetime.now(tz=timezone.utc)
    criterio = "purge_after < now()"

    log.info("lgpd_purge.iniciado", job_id=job_id)

    por_tabela: dict[str, int] = {}
    ids_por_tabela: dict[str, list[str]] = {}

    # 1. Fase: cada tabela em sua própria transação
    for tabela in TABELAS_COM_PURGE:
        try:
            async with session_scope() as db:
                # 1a. Coleta IDs antes de deletar
                ids_stmt = text(
                    f"SELECT id FROM lousa_main.{tabela} "
                    f"WHERE deleted_at IS NOT NULL AND purge_after < now()"
                )
                ids_rows = await db.execute(ids_stmt)
                ids = [str(r["id"]) for r in ids_rows]
                ids_por_tabela[tabela] = ids

                # 1b. Deleta
                del_stmt = text(
                    f"DELETE FROM lousa_main.{tabela} "
                    f"WHERE deleted_at IS NOT NULL AND purge_after < now()"
                )
                result = await db.execute(del_stmt)
                count = (
                    result.rowcount
                    if result.rowcount is not None and result.rowcount >= 0
                    else 0
                )
                por_tabela[tabela] = count
            # sessão sai aqui — cada tabela commitou sua própria transação
        except Exception as exc:  # noqa: BLE001
            log.error(
                "lgpd_purge.tabela_falhou",
                tabela=tabela,
                erro=str(exc),
            )
            por_tabela[tabela] = -1
            ids_por_tabela[tabela] = []

    # 2. Calcula hash do lote (audit do audit)
    canonical = json.dumps(
        {
            "job_id": job_id,
            "por_tabela": por_tabela,
            "criterio": criterio,
            "started": started.isoformat(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    hash_lote = hashlib.sha256(canonical.encode()).hexdigest()

    # 3. Grava log imutável (transação separada)
    async with session_scope() as db:
        log_row = LgpdPurgeLog(
            executado_em=started,
            tabela_origem="MULTI",
            registros_deletados=sum(v for v in por_tabela.values() if v > 0),
            criterio=criterio,
            registros_ids_antes_delete={"ids_por_tabela": ids_por_tabela},
            hash_lote_sha256=hash_lote,
            job_id=job_id,
        )
        db.add(log_row)
        await db.commit()

    log.info(
        "lgpd_purge.finalizado",
        job_id=job_id,
        total=sum(v for v in por_tabela.values() if v > 0),
        por_tabela=por_tabela,
    )

    return {
        "job_id": job_id,
        "total_deletados": sum(v for v in por_tabela.values() if v > 0),
        "por_tabela": por_tabela,
        "hash_lote_sha256": hash_lote,
    }


# ---------------------------------------------------------------------------
# API: trigger manual (admin) pra rodar job na hora
# ---------------------------------------------------------------------------

async def run_hash_chain_verifier_now() -> dict:
    """Dispara o job de hash chain na hora (endpoint admin)."""
    return await _job_hash_chain_verifier()


async def run_lgpd_purge_now() -> dict:
    """Dispara o job de purge na hora (endpoint admin, perigoso!)."""
    return await _job_lgpd_purge()


__all__ = [
    "start_scheduler",
    "stop_scheduler",
    "get_scheduler",
    "run_hash_chain_verifier_now",
    "run_lgpd_purge_now",
    "TABELAS_COM_PURGE",
]
