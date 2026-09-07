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

from fastapi import APIRouter, Header, HTTPException

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
    # Garante que `apps/api/scripts` está no sys.path (é onde estão os
    # scripts — fora do pacote `app`).
    scripts_dir = Path(__file__).resolve().parents[3] / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

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


@router.post(
    "/run-seeds",
    summary="[ADMIN] Roda seed_catalogos + seed_users + seed_tpas (idempotente)",
)
async def run_seeds(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict:
    """Roda os 3 seeds em ordem. Cada um é idempotente.

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
