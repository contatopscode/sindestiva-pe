"""SINDESTIVA-PE · /auth (login mock + me).

Sprint 0: skeleton. Sprint 1 T1-08: implementar fluxo real
(NextAuth v5 valida no backend, este endpoint só reflete).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_user
from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.user import LoginRequest, LoginResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse, summary="Login stub (Sprint 0)")
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),  # noqa: ARG001
) -> LoginResponse:
    """Sprint 0: devolve JWT mock sem checar credenciais.

    Sprint 1 T1-08: implementar verificação real (NextAuth v5).
    """
    token = create_access_token(
        subject="00000000-0000-0000-0000-000000000000",
        extra_claims={"role": "FISCAL", "stub": True},
    )
    return LoginResponse(
        access_token=token,
        expires_in=8 * 3600,
        user=UserRead(
            id="00000000-0000-0000-0000-000000000000",
            email=payload.email,
            telefone=None,
            role="FISCAL",
            status="ATIVO",
            failed_login_count=0,
            last_login_at=None,
            accepted_terms_at=None,
            created_at="2026-09-01T00:00:00Z",
            updated_at="2026-09-01T00:00:00Z",
        ),
    )


@router.get("/me", response_model=UserRead, summary="Quem sou eu (do JWT)")
async def me(user_id: str = Depends(require_user)) -> UserRead:  # noqa: ARG001
    """Sprint 0: devolve placeholder a partir do `sub` do JWT.

    Sprint 1: SELECT real em `users` (Sprint 1 T1-08).
    """
    return UserRead(
        id=user_id,
        email=None,
        telefone=None,
        role="FISCAL",
        status="ATIVO",
        failed_login_count=0,
        last_login_at=None,
        accepted_terms_at=None,
        created_at="2026-09-01T00:00:00Z",
        updated_at="2026-09-01T00:00:00Z",
    )


@router.get("/config", summary="Config pública do front (NEXTAUTH_URL etc)")
async def public_config() -> dict[str, str]:
    """Expõe só vars não-sensíveis para o frontend."""
    return {
        "nextauth_url": settings.nextauth_url,
        "app_env": settings.app_env,
    }
