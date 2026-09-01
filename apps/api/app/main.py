"""SINDESTIVA-PE · FastAPI app entrypoint.

Estrutura final:
    app/
      main.py            # este arquivo
      core/              # config, security, logging, database
      models/            # ORM models (User, Tpa, LousaSnapshot, ...)
      schemas/           # Pydantic v2 schemas
      api/               # routers versionados (v1)
      services/          # regras de negócio (lousa, remanejamento, ogmo, audit, hash_chain)
      jobs/              # APScheduler (hash_chain_verifier, lgpd_purge)
      workers/           # entrypoints de processos longos
      sprints/           # código específico por sprint
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger("sindestiva.api")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Lifespan FastAPI.

    Pega-dica (cross-projeto, MEMORY): NUNCA usar `asyncio.run()`
    dentro do lifespan — quebra em prod porque o event loop já está
    ativo. Usar `AsyncSessionLocal` direto. Aqui só faço log + dispose
    do engine (que tem métodos nativos async).
    """
    log.info(
        "api.startup",
        env=settings.app_env,
        db_schema=settings.db_schema,
    )
    yield
    await engine.dispose()
    log.info("api.shutdown")


app = FastAPI(
    title="Lousa Digital · SINDESTIVA-PE API",
    version="0.1.0",
    description="API REST do Centro de Comando (Fiscal + Dirigente) e PWA do TPA.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_v1_router)


# ---------------------------------------------------------------------------
# Endpoints de meta (mantidos na raiz, fora do /api/v1)
# ---------------------------------------------------------------------------


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness probe simples (não toca DB). Para checagem de DB use
    `/api/v1/health`."""
    return {"status": "ok", "service": "sindestiva-api", "version": "0.1.0"}


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": "SINDESTIVA-PE · Lousa Digital",
        "docs": "/docs",
        "health_db": "/api/v1/health",
    }


def run() -> None:
    """Entry point para `sindestiva-api`."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_env == "development",
    )
