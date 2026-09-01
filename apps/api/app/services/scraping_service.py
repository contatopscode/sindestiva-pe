"""SINDESTIVA-PE · Serviço de scraping (Sprint 2).

Orquestra scrapers (TPA/EscalaNet) e persiste em `lousa_escala_origem`
+ `lousa_alocacao` de forma idempotente.

Decisões:
  - **UPSERT** em `lousa_escala_origem` via ON CONFLICT (fonte, porto,
    turno, data_referencia) DO UPDATE. Atualiza `content_hash`,
    `payload_jsonb`, `duracao_ms`, `status` etc. — mantém imutabilidade
    do `id` (UUID) e `scraped_at` no `created_at`.
  - Se o `content_hash` mudou entre scrapes do mesmo dia, detectamos
    mudança de layout (R2 do plano).
  - **DELETE + INSERT** em `lousa_alocacao` para a origem — garante
    consistência com a versão mais recente do HTML. Volume baixo
    (1.144 linhas/dia) não justifica UPSERT por linha.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    Faina,
    Funcao,
    LousaAlocacao,
    LousaEscalaOrigem,
    Porto,
    Turno,
)
from app.models.enums import FonteEscalaEnum, StatusScrapingEnum
from app.scrapers import raspar_escalanet, raspar_tpa

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ScrapingResultado:
    """Resultado de 1 execução de scraping (1 fonte × 1 porto × 1 turno × 1 data)."""

    sucesso: bool
    escala_origem_id: UUID | None
    fonte: FonteEscalaEnum
    porto_slug: str
    turno_codigo: str
    data: date
    status: StatusScrapingEnum
    total_celulas: int
    duracao_ms: int
    content_hash: str
    layout_mudou: bool
    erro_detalhes: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _buscar_ou_none(
    db: AsyncSession,
    model: type[Any],
    coluna_codigo: Any,
    codigo: str,
) -> Any:
    """SELECT 1 linha por código. Retorna None se não encontrar."""
    stmt = select(model).where(coluna_codigo == codigo)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def executar_scraping(
    db: AsyncSession,
    *,
    fonte: FonteEscalaEnum,
    porto_slug: str,
    turno_codigo: str,
    data: date,
    http_client: Any | None = None,
) -> ScrapingResultado:
    """Executa 1 ciclo de scraping e persiste o resultado.

    Args:
        db: sessão async do SQLAlchemy.
        fonte: TPA ou ESCALANET.
        porto_slug: "SUAPE" (TPA) ou "RECIFE" (EscalaNet).
        turno_codigo: "DIURNO" ou "NOTURNO".
        data: data de referência.
        http_client: cliente HTTP opcional (default usa httpx). Útil
            para testes — passa um fake que retorna HTML estático.

    Returns:
        ScrapingResultado com status, contagens e IDs.
    """
    # 1. Resolve catálogos (porto + turno) — falha se não existir.
    porto = await _buscar_ou_none(db, Porto, Porto.codigo, porto_slug)
    if porto is None:
        return ScrapingResultado(
            sucesso=False,
            escala_origem_id=None,
            fonte=fonte,
            porto_slug=porto_slug,
            turno_codigo=turno_codigo,
            data=data,
            status=StatusScrapingEnum.FALHA,
            total_celulas=0,
            duracao_ms=0,
            content_hash="",
            layout_mudou=False,
            erro_detalhes=f"Porto {porto_slug!r} não cadastrado.",
        )
    turno = await _buscar_ou_none(db, Turno, Turno.codigo, turno_codigo)
    if turno is None:
        return ScrapingResultado(
            sucesso=False,
            escala_origem_id=None,
            fonte=fonte,
            porto_slug=porto_slug,
            turno_codigo=turno_codigo,
            data=data,
            status=StatusScrapingEnum.FALHA,
            total_celulas=0,
            duracao_ms=0,
            content_hash="",
            layout_mudou=False,
            erro_detalhes=f"Turno {turno_codigo!r} não cadastrado.",
        )

    # 2. Executa o scraper.
    if fonte == FonteEscalaEnum.TPA:
        bruto = await raspar_tpa(porto_slug, data, http_client=http_client)
    elif fonte == FonteEscalaEnum.ESCALANET:
        bruto = await raspar_escalanet(porto_slug, data, http_client=http_client)
    else:
        # MANUAL_FISCAL não tem scraping — entrada via PWA (Sprint 4).
        return ScrapingResultado(
            sucesso=False,
            escala_origem_id=None,
            fonte=fonte,
            porto_slug=porto_slug,
            turno_codigo=turno_codigo,
            data=data,
            status=StatusScrapingEnum.FALHA,
            total_celulas=0,
            duracao_ms=0,
            content_hash="",
            layout_mudou=False,
            erro_detalhes=f"Fonte {fonte.value!r} não suporta scraping automático.",
        )

    # 3. Determina status final.
    if bruto.erro_detalhes:
        status = StatusScrapingEnum.FALHA
    elif bruto.layout_mudou:
        status = StatusScrapingEnum.LAYOUT_MUDOU
    elif not bruto.celulas:
        status = StatusScrapingEnum.SEM_DADOS
    else:
        status = StatusScrapingEnum.SUCESSO

    # 4. UPSERT em `lousa_escala_origem` (idempotente).
    payload_jsonb: dict[str, Any] = {
        "html_bruto": bruto.html_bruto,
        "celulas": [
            {
                "faina_codigo": c.faina_codigo,
                "funcao_codigo": c.funcao_codigo,
                "trabalhador_matricula": c.trabalhador_matricula,
            }
            for c in bruto.celulas
        ],
    }
    agora = datetime.now(tz=UTC)
    insert_stmt = (
        pg_insert(LousaEscalaOrigem)
        .values(
            fonte=fonte,
            porto_id=porto.id,
            turno_id=turno.id,
            data_referencia=data,
            url_origem=bruto.url_origem,
            content_hash=bruto.content_hash,
            payload_jsonb=payload_jsonb,
            duracao_ms=bruto.duracao_ms,
            status=status,
            erro_detalhes=bruto.erro_detalhes,
            scraped_at=agora,
            created_at=agora,
        )
        .on_conflict_do_update(
            constraint="uq_escala_origem_fonte_porto_turno_data",
            set_={
                "url_origem": bruto.url_origem,
                "content_hash": bruto.content_hash,
                "payload_jsonb": payload_jsonb,
                "duracao_ms": bruto.duracao_ms,
                "status": status,
                "erro_detalhes": bruto.erro_detalhes,
                "scraped_at": agora,
            },
        )
        .returning(LousaEscalaOrigem.id)
    )
    result = await db.execute(insert_stmt)
    escala_origem_id: UUID = result.scalar_one()
    log.info(
        "scraping_service.upsert_escala_origem",
        escala_origem_id=str(escala_origem_id),
        fonte=fonte.value,
        porto=porto_slug,
        turno=turno_codigo,
        data=data.isoformat(),
        status=status.value,
        celulas=len(bruto.celulas),
    )

    # 5. Se scrape OK, regenera alocações (DELETE + INSERT idempotente).
    if status in (StatusScrapingEnum.SUCESSO, StatusScrapingEnum.PARCIAL, StatusScrapingEnum.LAYOUT_MUDOU):
        # 5a. Cache de fainas e funções (por codigo) — evita N+1.
        fainas_result = await db.execute(select(Faina))
        fainas_idx = {f.codigo: f for f in fainas_result.scalars().all()}
        funcoes_result = await db.execute(select(Funcao))
        funcoes_idx = {f.codigo: f for f in funcoes_result.scalars().all()}

        # 5b. Apaga alocações anteriores desta origem.
        delete_stmt = LousaAlocacao.__table__.delete().where(
            LousaAlocacao.escala_origem_id == escala_origem_id
        )
        await db.execute(delete_stmt)

        # 5c. Insere alocações (apenas fainas/funções conhecidas no catálogo).
        alocacoes_inserir: list[dict[str, Any]] = []
        for celula in bruto.celulas:
            faina = fainas_idx.get(celula.faina_codigo)
            funcao = funcoes_idx.get(celula.funcao_codigo)
            if faina is None or funcao is None:
                # Catálogo incompleto — pula (alerta no log).
                log.warning(
                    "scraping_service.catalogo_miss",
                    faina=celula.faina_codigo,
                    funcao=celula.funcao_codigo,
                    origem=str(escala_origem_id),
                )
                continue
            alocacoes_inserir.append({
                "escala_origem_id": escala_origem_id,
                "porto_id": porto.id,
                "turno_id": turno.id,
                "faina_id": faina.id,
                "funcao_id": funcao.id,
                "data_referencia": data,
                "trabalhador_matricula": celula.trabalhador_matricula,
                "fk_mando": 1 if funcao.categoria == "MANDO" else None,
                "fk_terno": 1 if funcao.categoria == "TERNO" else None,
                "fk_tecnica": 1 if funcao.categoria == "TECNICA" else None,
                "fk_vigia": 1 if funcao.categoria == "VIGIA" else None,
                "scraped_at": agora,
                "created_at": agora,
            })
        if alocacoes_inserir:
            await db.execute(LousaAlocacao.__table__.insert(), alocacoes_inserir)

    await db.commit()
    return ScrapingResultado(
        sucesso=status in (StatusScrapingEnum.SUCESSO, StatusScrapingEnum.PARCIAL, StatusScrapingEnum.LAYOUT_MUDOU),
        escala_origem_id=escala_origem_id,
        fonte=fonte,
        porto_slug=porto_slug,
        turno_codigo=turno_codigo,
        data=data,
        status=status,
        total_celulas=len(bruto.celulas),
        duracao_ms=bruto.duracao_ms,
        content_hash=bruto.content_hash,
        layout_mudou=bruto.layout_mudou,
        erro_detalhes=bruto.erro_detalhes,
    )


__all__ = ["ScrapingResultado", "executar_scraping"]
