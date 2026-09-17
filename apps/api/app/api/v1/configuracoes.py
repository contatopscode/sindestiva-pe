"""SINDESTIVA-PE · /configuracoes (admin DIRIGENTE — WhatsApp OGMO)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import get_current_user_id, get_current_user_role, oauth2_scheme
from app.models.app_settings import OGMO_WHATSAPP_KEY
from app.schemas.configuracoes import ConfiguracoesRead, ConfiguracoesUpdate
from app.services import app_settings_service as settings_svc

router = APIRouter(prefix="/configuracoes", tags=["configuracoes"])


def _require_dirigente(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> str:
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
        )
    role = get_current_user_role(token=token)
    if role != "DIRIGENTE":
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ROLE_REQUIRED",
                "message": f"Configurações restritas a DIRIGENTE (você é {role}).",
            },
        )
    return user_id


@router.get("", response_model=ConfiguracoesRead, summary="Lê configurações da plataforma")
async def get_configuracoes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[str, Depends(_require_dirigente)],
) -> ConfiguracoesRead:
    numero, fonte = await settings_svc.resolve_ogmo_whatsapp(db)
    return ConfiguracoesRead(
        ogmo_whatsapp=numero,
        ogmo_whatsapp_fonte=fonte,
        evolution_configured=settings_svc.evolution_configured(),
    )


@router.put("", response_model=ConfiguracoesRead, summary="Atualiza WhatsApp OGMO")
async def put_configuracoes(
    body: ConfiguracoesUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: Annotated[str, Depends(_require_dirigente)],
) -> ConfiguracoesRead:
    try:
        normalized = settings_svc.normalize_ogmo_whatsapp(body.ogmo_whatsapp)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_WHATSAPP", "message": str(exc)},
        ) from exc

    await settings_svc.upsert_setting(
        db,
        OGMO_WHATSAPP_KEY,
        normalized,
        user_id,
    )
    return ConfiguracoesRead(
        ogmo_whatsapp=normalized,
        ogmo_whatsapp_fonte="db",
        evolution_configured=settings_svc.evolution_configured(),
    )
