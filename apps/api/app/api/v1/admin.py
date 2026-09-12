"""SINDESTIVA-PE · Endpoints administrativos (one-shot).

Sprint A: usado para rodar seeds em prod (Render free não tem Shell
persistente). Endpoints protegidos por `X-Admin-Token` (env
`ADMIN_SEED_TOKEN`). Em produção, este token é randômico, guardado
apenas no painel Render e nunca commitado.

ATENÇÃO: o token `admin_seed_token` dos Settings é um segredo de
infraestrutura. Se for vazio, o endpoint responde 503 (não autentica
ninguém). Se o header bater, executa.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(prefix="/admin", tags=["admin"])
log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------


def _check_admin_token(x_admin_token: str | None) -> None:
    """Levanta 503 se ADMIN_SEED_TOKEN não foi configurado, 401 se faltou
    header, 403 se o token não bate.
    """
    expected = settings.admin_seed_token
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_SEED_TOKEN não configurado no servidor.",
        )
    if not x_admin_token:
        raise HTTPException(
            status_code=401,
            detail="Header X-Admin-Token obrigatório.",
        )
    if x_admin_token != expected:
        raise HTTPException(
            status_code=403,
            detail="Token admin inválido.",
        )


async def _executar_seed(modulo_nome: str, fn_nome: str = "seed") -> dict:
    """Importa `modulo_nome` (apps.api.scripts.X) e executa `await fn_nome(...)`.

    Idempotente: cada seed usa upsert por chave natural (email, código).
    Retorna o dict que o seed emite (totais por entidade).
    """
    # Tenta vários caminhos possíveis para `scripts/` (cwd do Render = /app).
    candidates = [
        Path(__file__).resolve().parents[3]
        / "scripts",  # /app/scripts (apps/api/scripts)
        Path("/app/scripts"),  # cwd /app (Render)
        Path.cwd() / "apps" / "api" / "scripts",  # cwd raiz do repo
        Path.cwd() / "scripts",  # cwd /app/apps/api
    ]
    scripts_dir: Path | None = None
    for c in candidates:
        if c.is_dir():
            scripts_dir = c
            break
    if scripts_dir is None:
        tried = ", ".join(str(c) for c in candidates)
        raise RuntimeError(f"Diretório scripts/ não encontrado. Procurou em: {tried}")

    scripts_str = str(scripts_dir)
    if scripts_str not in sys.path:
        sys.path.insert(0, scripts_str)

    log.info("admin._executar_seed.import", modulo=modulo_nome, scripts_dir=scripts_str)
    modulo = importlib.import_module(modulo_nome)
    fn = getattr(modulo, fn_nome, None)
    if fn is None:
        raise RuntimeError(f"Módulo {modulo_nome} não tem função {fn_nome}().")
    if asyncio.iscoroutinefunction(fn):
        return await fn()
    return fn()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/debug/env",
    summary="[DEBUG] Mostra quais env vars críticas estão configuradas",
)
async def debug_env() -> dict:
    """Diagnóstico: retorna bool para cada env var crítica.

    Útil pra confirmar que `ADMIN_SEED_TOKEN` (e outros) chegaram
    no processo. Nunca expõe valores, só presença/configuração.
    """
    return {
        "admin_seed_token_set": bool(settings.admin_seed_token),
        "admin_seed_token_len": len(settings.admin_seed_token),
        "app_env": settings.app_env,
        "resend_api_key_set": bool(settings.resend_api_key),
        "evolution_api_key_set": bool(settings.evolution_api_key),
        "nextauth_secret_set": bool(settings.nextauth_secret),
        "ogmo_webhook_url_set": bool(settings.ogmo_webhook_url),
    }


@router.post(
    "/test-whatsapp",
    summary="[ADMIN] Envia msg de teste via WhatsApp (Evolution API)",
)
async def test_whatsapp(
    numero: str | None = None,
    texto: str | None = None,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict:
    """Dispara msg WhatsApp via Evolution API para validar integração end-to-end.

    Args (query):
        numero: destinatário (formato BR ou E.164). Default `5581999990001` (Paulo).
        texto: corpo da msg. Default placeholder.
    """
    _check_admin_token(x_admin_token)
    from app.services.evolution import send_text

    numero_dest = numero or "5581999990001"
    texto_dest = texto or "🔧 SINDESTIVA-PE · teste Evolution API via admin endpoint."
    log.warning("admin.test_whatsapp.invocado", numero=numero_dest)

    result = await send_text(numero_dest, texto_dest)
    log.warning(
        "admin.test_whatsapp.resultado",
        sucesso=result["success"],
        erro=result.get("error"),
    )
    return {
        "numero_destino": numero_dest,
        "texto_enviado": texto_dest,
        **result,
    }


@router.post(
    "/fix-purge-after-default",
    summary="[ADMIN] Adiciona DEFAULT now()+5y em colunas purge_after NOT NULL",
)
async def fix_purge_after_default(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Adiciona `DEFAULT now() + INTERVAL '5 years'` em todas as colunas
    `purge_after` que estão NOT NULL sem default.

    Workaround pro bug introduzido em `fe23ab1`: removemos
    `server_default` dos models pq Postgres não faz cast de `text()`
    para `timestamptz`. O default deveria ter sido adicionado via ALTER
    TABLE no `/init`, mas o schema já estava criado em prod sem o
    default — resultado: qualquer INSERT em dirigentes/fiscais/etc falha.

    Endpoint idempotente — ALTER COLUMN SET DEFAULT não falha se já existe.

    NÃO droca nenhuma tabela, NÃO altera dados existentes (só metadata).
    """
    from sqlalchemy import text as sql_text

    schema = settings.db_schema
    _check_admin_token(x_admin_token)
    log.warning("admin.fix_purge_after.invocado")

    purge_tables = [
        r[0]
        for r in (
            await db.execute(
                sql_text(
                    "SELECT table_name FROM information_schema.columns "
                    "WHERE table_schema = :s AND column_name = 'purge_after'"
                ),
                {"s": schema},
            )
        ).all()
    ]

    fixadas: list[str] = []
    for table_name in purge_tables:
        await db.execute(
            sql_text(
                f"ALTER TABLE {schema}.{table_name} "
                f"ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '5 years'"
            )
        )
        fixadas.append(table_name)
        log.info("admin.fix_purge_after.applied", table=table_name)

    # Commit (estamos numa sessão por request do FastAPI).
    await db.commit()
    log.warning("admin.fix_purge_after.ok", fixadas=fixadas)
    return {"ok": True, "schema": schema, "fixadas": fixadas}


@router.post(
    "/ensure-schema",
    summary="[ADMIN] Extensions + Alembic upgrade head + drift check",
)
async def ensure_schema(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict:
    """Reaplica bootstrap de Postgres e migrations com repair de drift.

    Se `alembic_version` estiver à frente de tabelas críticas (`portos`,
    `lousa_escala_origem`), faz `alembic stamp` seguro (sem downgrade DDL)
    e reexecuta `upgrade head`. Fallback: `create_all(checkfirst=True)`.

    Uso:
        curl -X POST https://api.hom.lousa.pscode.ia.br/api/v1/admin/ensure-schema \\
             -H "X-Admin-Token: $ADMIN_SEED_TOKEN"
    """
    from app.core.postgres_bootstrap import (
        ensure_schema_and_extensions,
        run_migrations_with_drift_repair,
    )

    _check_admin_token(x_admin_token)
    log.warning("admin.ensure_schema.invocado")

    try:
        bootstrap = ensure_schema_and_extensions()
    except Exception as exc:
        log.exception("admin.ensure_schema.bootstrap_falhou")
        raise HTTPException(
            status_code=500,
            detail=(
                f"Bootstrap Postgres falhou: {type(exc).__name__}: {exc}. "
                "Se o role não tem CREATE EXTENSION, peça ao DBA: "
                "CREATE EXTENSION IF NOT EXISTS pgcrypto, citext, pg_trgm;"
            ),
        ) from exc

    migrate = run_migrations_with_drift_repair()
    if not migrate.get("ok"):
        log.error("admin.ensure_schema.migrate_falhou", migrate=migrate)
        raise HTTPException(
            status_code=500,
            detail={
                "error": migrate.get("error"),
                "missing_after": migrate.get("missing_after"),
                "actions": migrate.get("actions"),
                "log_tail": migrate.get("log_tail"),
            },
        )

    log.warning(
        "admin.ensure_schema.ok",
        revision=migrate.get("revision_after"),
        missing_tables=migrate.get("missing_after"),
    )
    return {
        "ok": True,
        "bootstrap": bootstrap,
        "migrate": migrate,
        "next_step": "POST /api/v1/admin/run-seeds",
    }


@router.post(
    "/run-seeds",
    summary="[ADMIN] Roda seed_catalogos + seed_users + seed_tpas (idempotente)",
)
async def run_seeds(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict:
    """Roda os 3 seeds em ordem. Cada um é idempotente.

    Pré-requisito: tabelas existem (entrypoint ou `POST /admin/ensure-schema`).

    Uso:
        curl -X POST https://sindestiva-api.onrender.com/api/v1/admin/run-seeds \\
             -H "X-Admin-Token: $ADMIN_SEED_TOKEN"

    Resposta:
        {
          "ok": true,
          "steps": {
            "catalogos": {...},
            "users": {...},
            "tpas_demo": {...}
          }
        }
    """
    _check_admin_token(x_admin_token)
    log.warning("admin.run_seeds.invocado")

    steps: dict[str, dict] = {}
    try:
        steps["catalogos"] = await _executar_seed("seed_catalogos")
    except Exception as exc:
        log.exception("admin.run_seeds.catalogos_falhou")
        raise HTTPException(
            status_code=500,
            detail=f"Falha em seed_catalogos: {type(exc).__name__}: {exc}",
        ) from exc

    try:
        steps["users"] = await _executar_seed("seed_users")
    except Exception as exc:
        log.exception("admin.run_seeds.users_falhou")
        raise HTTPException(
            status_code=500,
            detail=f"Falha em seed_users: {type(exc).__name__}: {exc}",
        ) from exc

    try:
        steps["tpas_demo"] = await _executar_seed("seed_tpas_demo")
    except Exception as exc:
        log.exception("admin.run_seeds.tpas_falhou")
        raise HTTPException(
            status_code=500,
            detail=f"Falha em seed_tpas_demo: {type(exc).__name__}: {exc}",
        ) from exc

    log.warning("admin.run_seeds.ok", steps=list(steps.keys()))
    return {"ok": True, "steps": steps}


__all__ = ["router"]
