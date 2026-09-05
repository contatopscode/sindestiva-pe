"""SINDESTIVA-PE · Settings (Pydantic v2).

Lê variáveis do `.env` (NUNCA commitar — só `.env.example`).
Defaults alinhados com a pegadinha do Mac do Paulo:
  - Postgres 17 na 5433 (NÃO 5432 — ocupado pelo Homebrew)
  - Redis 7 na 6380 (NÃO 6379)
  - Conexão via 127.0.0.1 (forçar IPv4)

Decisão Sprint 0+ (Sprint 0 refactor):
  - `database_url_sync` é DERIVADO de `database_url_async` substituindo
    `postgresql+asyncpg://` por `postgresql+psycopg://`. Assim só
    precisamos setar 1 env var (`DATABASE_URL_ASYNC`) em produção
    (Render, Vercel) e o Alembic (psycopg sync) também funciona.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Config central do SINDESTIVA-PE.

    Tudo é tipado. `lru_cache` garante singleton (importar `settings`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- Ambiente ----------
    app_env: Literal["development", "staging", "production", "test"] = "development"
    log_level: str = "info"
    tz: str = "America/Recife"

    # ---------- Banco (Postgres 17, schema `lousa_main`) ----------
    # Padrão do projeto: 127.0.0.1:5433 (NÃO 5432 — pegadinha Mac Paulo).
    database_url_async: str = Field(
        default="postgresql+asyncpg://sindestiva:sindestiva@127.0.0.1:5433/sindestiva",
        description="URL async (asyncpg) — usar em runtime FastAPI.",
    )
    database_url_sync: str = Field(
        default="",  # derivado de `database_url_async` no validator abaixo
        description="URL sync (psycopg v3) — usar em Alembic. Se vazio, deriva de `database_url_async`.",
    )
    postgres_user: str = "sindestiva"
    postgres_password: str = "sindestiva"
    postgres_db: str = "sindestiva"
    postgres_port: int = 5433
    db_schema: str = "lousa_main"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # ---------- Redis ----------
    redis_url: str = "redis://127.0.0.1:6380/0"
    redis_port: int = 6380

    # ---------- Auth ----------
    nextauth_secret: str = ""  # gerar: openssl rand -base64 32
    nextauth_url: str = "http://localhost:3000"
    jwt_expires_in: str = "8h"

    # ---------- TPA / OTP (WhatsApp via Evolution API) ----------
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""
    evolution_instance: str = "sindestiva"

    # ---------- OGMO ----------
    ogmo_email: str = "escalacao@ogmo-pe.com.br"
    ogmo_webhook_url: str = ""

    # ---------- E-mail (Resend) ----------
    resend_api_key: str = ""
    resend_from: str = "Lousa Sindestiva <noreply@lousa.pscode.ia.br>"

    # ---------- FCM (push PWA) ----------
    fcm_project_id: str = ""
    fcm_private_key: str = ""
    fcm_client_email: str = ""

    # ---------- Scraper ----------
    scraper_user_agent: str = "SINDESTIVA-Lousa/1.0 (+https://lousa.pscode.ia.br)"
    scraper_timeout: int = 30
    scraper_interval_seconds: int = 60

    # ---------- Observabilidade ----------
    sentry_dsn: str = ""

    @model_validator(mode="after")
    def _derive_database_url_sync(self) -> "Settings":
        """Se `DATABASE_URL_SYNC` não foi setado, deriva de `DATABASE_URL_ASYNC`.

        Substitui o driver `postgresql+asyncpg://` por `postgresql+psycopg://`
        (driver sync do Alembic). Necessário em prod (Render) porque só
        setamos `DATABASE_URL_ASYNC` no painel — duplicar a env var é fonte
        de bug (mudou uma, esqueceu a outra).
        """
        if not self.database_url_sync:
            self.database_url_sync = self.database_url_async.replace(
                "postgresql+asyncpg://", "postgresql+psycopg://", 1
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton de Settings (reutilizável em qualquer módulo)."""
    return Settings()


# Alias ergonômico — `from app.core.config import settings`.
settings = get_settings()
