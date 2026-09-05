"""SINDESTIVA-PE · FastAPI app entrypoint.

Estrutura final:
    app/
      main.py            # este arquivo
      core/              # config, security, logging, database
      models/            # ORM models (User, Tpa, LousaSnapshot, ...)
      schemas/           # Pydantic v2 schemas
      api/               # routers versionados (v1)
      services/          # regras de negócio (lousa, remanejamento, ogmo, audit, hash_chain)
      jobs/              # APScheduler (hash_chain_verifier, lgpd_purge, scraping_job)
      scrapers/          # TPA + EscalaNet (Sprint 2)
      workers/           # entrypoints de processos longos
      sprints/           # código específico por sprint
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging, get_logger
from app.jobs.scheduler import start_scheduler as start_s6_scheduler, stop_scheduler as stop_s6_scheduler
from app.jobs.scraping_job import get_scheduler as get_scraping_scheduler
from app.middleware.access_log import AccessLogMiddleware

configure_logging()
log = get_logger("sindestiva.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan FastAPI.

    Pega-dica (cross-projeto, MEMORY): NUNCA usar `asyncio.run()`
    dentro do lifespan — quebra em prod porque o event loop já está
    ativo. Usar `AsyncSessionLocal` direto. Aqui só faço log + dispose
    do engine (que tem métodos nativos async).

    Sprint 2: inicia o `ScrapingScheduler` em background via
    `asyncio.create_task`.
    Sprint 6: adiciona scheduler de jobs (hash_chain_verifier 03:00,
    lgpd_purge 04:00).
    Sprint 0+ deploy: cria schema `lousa_main` se não existir (DB
    compartilhado no Render free tier — schema pode não estar lá).
    """
    log.info(
        "api.startup",
        env=settings.app_env,
        db_schema=settings.db_schema,
    )
    # Sprint 0+ deploy: garante schema `lousa_main` (idempotente).
    # Em dev local, init.sql do Docker já cria; em prod (Render) com DB
    # compartilhado (sinapse-db), o Alembic pode falhar em criar o schema
    # por permissão — então fazemos aqui no engine do app (que já tem o
    # event listener de search_path aplicado em cada connect).
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}"))
        log.info("api.schema_ensured", schema=settings.db_schema)
    except Exception as exc:  # noqa: BLE001
        log.warning("api.schema_create_failed", schema=settings.db_schema, erro=str(exc))
    # Sprint 6: inicia scheduler de jobs LGPD/auditoria
    await start_s6_scheduler()
    # Sprint 2: inicia o scheduler de scraping (interval = 15min).
    # Desabilitado em test environment para não interferir com pytest.
    if settings.app_env != "test":
        scheduler = get_scraping_scheduler()
        app.state.scraping_task = scheduler.start()
    yield
    # Shutdown: para o scheduler antes de dispose do engine.
    if getattr(app.state, "scraping_task", None) is not None:
        await get_scraping_scheduler().stop()
    await stop_s6_scheduler()
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
# CORS (Sprint 0 — DEV ONLY)
# ---------------------------------------------------------------------------
# Sprint 0: o Next.js roda em :3000 e a API em :8000 (origens diferentes).
# Em dev, habilita CORS pros origins locais. Em produção (Sprint 1+),
# trocar por lista explícita via env (mesmo padrão FaceGate/Córtex).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3010",  # SINDESTIVA web (sindestiva-bot Sprint 4)
        "http://127.0.0.1:3010",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware (Sprint 6 T6-09 — access_log Art. 37 LGPD)
# ---------------------------------------------------------------------------
app.add_middleware(AccessLogMiddleware)


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
        "scraping_status": "/api/v1/scraping/status",
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
