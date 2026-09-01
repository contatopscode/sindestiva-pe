"""SINDESTIVA-PE · Middleware AccessLog (Sprint 6 T6-09).

Registra toda **leitura** de dado pessoal em `access_log` (Art. 37 LGPD).

Aplica-se em endpoints que retornam PII (dados pessoais):
- /api/v1/users/{id} (qualquer leitura de outro user)
- /api/v1/tpa/{id} (leitura de TPA)
- /api/v1/remanejamentos (lista detalhe)
- /api/v1/auditoria/eventos (eventos com actor_user_id)

A LGPD exige rastreabilidade de "toda leitura" — não só escritas. Aqui
capturamos: user_id (ator), recurso_tipo, recurso_id, operacao,
contexto, IP, user_agent, timestamp.

Risco: volume alto. Job de purge (T6-06) cuida disso.
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import session_scope
from app.core.logging import get_logger
from app.models import AccessLog

log = get_logger(__name__)


# Recursos que devem ser logados (path prefix → recurso_tipo)
RECURSOS_LOGADOS: list[tuple[str, str]] = [
    ("/api/v1/users", "user"),
    ("/api/v1/tpa", "tpa"),
    ("/api/v1/fiscais", "fiscal"),
    ("/api/v1/dirigentes", "dirigente"),
    ("/api/v1/remanejamentos", "remanejamento"),
    ("/api/v1/ogmo/notificacoes", "ogmo_notificacao"),
    ("/api/v1/auditoria", "audit_event"),
    ("/api/v1/lgpd/solicitacoes", "lgpd_solicitacao"),
]


def _classify_request(method: str, path: str) -> tuple[str, str, str] | None:
    """Classifica request em (recurso_tipo, recurso_id, operacao) se deve ser logado.

    Returns None se não deve ser logado.
    """
    # Só loga leituras (GET) e exports
    if method not in ("GET",):
        return None

    # Ignora endpoints de listagem genérica (volume alto, baixo valor)
    if path.endswith("/users") and method == "GET" and path.count("/") == 4:
        # /api/v1/users (lista) — não loga
        return None

    for prefix, recurso_tipo in RECURSOS_LOGADOS:
        if path.startswith(prefix):
            # Tenta extrair ID do path
            parts = path.split("/")
            recurso_id = parts[-1] if len(parts) > 0 and parts[-1] else None
            # Valida se parece UUID
            if recurso_id and len(recurso_id) == 36 and recurso_id.count("-") == 4:
                return (recurso_tipo, recurso_id, "READ")
            # Listagem com query params (ex: /remanejamentos?limit=10)
            return None

    return None


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Middleware FastAPI que registra leituras de PII em access_log.

    Aplica-se DEPOIS do auth middleware (pra ter user_id do JWT).
    """

    async def dispatch(self, request: Request, call_next: Any):
        # Processa request
        response = await call_next(request)

        # Classifica (só loga leituras de PII)
        classification = _classify_request(request.method, request.url.path)
        if classification is None:
            return response

        recurso_tipo, recurso_id, operacao = classification

        # Pega user_id do JWT (se houver). O auth dep injeta o user.
        user_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            from app.core.security import decode_token  # noqa: PLC0415

            try:
                payload = decode_token(auth_header[7:])
                sub = payload.get("sub")
                if sub:
                    from uuid import UUID  # noqa: PLC0415

                    user_id = UUID(sub)
            except Exception:  # noqa: BLE001
                pass

        if user_id is None:
            # Sem user autenticado, não loga (vai pra audit via outro caminho)
            return response

        # IP + user agent
        ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )
        user_agent = request.headers.get("user-agent", "unknown")[:1000]

        contexto = f"{request.method} {request.url.path}"

        # Salva no DB (fire-and-forget pra não bloquear request)
        try:
            async with session_scope() as db:
                entry = AccessLog(
                    user_id=user_id,
                    recurso_tipo=recurso_tipo,
                    recurso_id=recurso_id,  # type: ignore[arg-type]
                    operacao=operacao,
                    contexto=contexto[:500],
                    ip_origem=ip,
                    user_agent=user_agent,
                )
                db.add(entry)
                await db.commit()
        except Exception as exc:  # noqa: BLE001
            log.error(
                "access_log.falhou",
                recurso=recurso_tipo,
                erro=str(exc),
            )

        return response


__all__ = ["AccessLogMiddleware"]
