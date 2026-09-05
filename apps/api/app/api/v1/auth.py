"""SINDESTIVA-PE · /auth (login real + me).

Sprint 1 T1-08: implementação real do fluxo de auth, com:
- Verificação de credencial no DB (bcrypt)
- Bloqueio após 5 tentativas (15min)
- JWT com claims de role + fiscal_id
- Auditoria (last_login_at, IP, user agent)
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import get_current_user_id, oauth2_scheme
from app.models import User
from app.schemas.user import LoginRequest, LoginResponse, UserRead
from app.services.auth_service import AuthError, authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    """Extrai IP do request (com fallback X-Forwarded-For se vier proxy)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=LoginResponse, summary="Login com email+senha (T1-08)")
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Sprint 1: verifica credenciais reais no DB.

    Returns:
        LoginResponse com access_token JWT, expires_in (8h), user.
    """
    try:
        user, token = await authenticate(
            db,
            email=payload.email,
            password=payload.password,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})
    except Exception as exc:  # noqa: BLE001
        # Captura qualquer outro erro (ex: select_in_relationship falha) e
        # retorna 500 com detalhes para debug em prod.
        from app.core.logging import get_logger
        log = get_logger(__name__)
        log.error("auth.login_unexpected", exc_type=type(exc).__name__, exc_msg=str(exc))
        raise HTTPException(
            status_code=500,
            detail={"code": "LOGIN_ERROR", "message": f"{type(exc).__name__}: {exc}"},
        ) from exc

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=8 * 3600,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead, summary="Quem sou eu (do JWT)")
async def me(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Sprint 1: SELECT real em users (lazy-load perfis)."""
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Token ausente ou inválido."},
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": "Usuário não encontrado."},
        )
    return UserRead.model_validate(user)


@router.get("/config", summary="Config pública do front (NEXTAUTH_URL etc)")
async def public_config() -> dict[str, str]:
    """Expõe só vars não-sensíveis para o frontend."""
    return {
        "nextauth_url": settings.nextauth_url,
        "app_env": settings.app_env,
    }
