"""SINDESTIVA-PE · Logging estruturado (structlog).

Convenções:
  - JSON em produção, console em dev
  - `request_id` em todo log (gerado por middleware ou herdado do
    header `X-Request-ID`)
  - Logger padrão: `sindestiva.<modulo>`

Migração para Sentry (já tem dep `sentry-sdk[fastapi]`) é feita em
Sprint 7 (deploy prod). Aqui só estrutura o log.
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

from app.core.config import settings

# ContextVar para request_id — middleware popula, log captura
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def _add_request_id(_: Any, __: str, event_dict: structlog.types.EventDict) -> structlog.types.EventDict:
    """Processor que injeta request_id no log se houver na ContextVar."""
    rid = request_id_ctx.get()
    if rid:
        event_dict.setdefault("request_id", rid)
    return event_dict


def configure_logging() -> None:
    """Configura structlog + stdlib logging. Idempotente."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # stdlib root
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_request_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (
                structlog.processors.JSONRenderer()
                if settings.app_env in ("production", "staging")
                else structlog.dev.ConsoleRenderer(colors=True)
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def new_request_id() -> str:
    """Gera um request_id novo e injeta na ContextVar."""
    rid = str(uuid.uuid4())
    request_id_ctx.set(rid)
    return rid


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Logger ergonômico: `log = get_logger(__name__)`."""
    return structlog.get_logger(name or "sindestiva")


__all__ = [
    "configure_logging",
    "new_request_id",
    "get_logger",
    "request_id_ctx",
]
