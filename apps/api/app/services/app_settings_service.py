"""SINDESTIVA-PE · Leitura/escrita de app_settings + resolução OGMO WhatsApp."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.app_settings import OGMO_WHATSAPP_KEY, AppSetting
from app.services.evolution import _normalize_br

OgmoWhatsappFonte = Literal["db", "env", "none"]


async def get_setting(db: AsyncSession, key: str) -> str | None:
    row = (
        await db.execute(select(AppSetting.value).where(AppSetting.key == key))
    ).scalar_one_or_none()
    return row


async def upsert_setting(
    db: AsyncSession,
    key: str,
    value: str,
    user_id: UUID | str | None,
) -> AppSetting:
    uid = UUID(str(user_id)) if user_id else None
    existing = (
        await db.execute(select(AppSetting).where(AppSetting.key == key))
    ).scalar_one_or_none()
    if existing is None:
        row = AppSetting(key=key, value=value, updated_by=uid)
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row

    existing.value = value
    existing.updated_by = uid
    await db.commit()
    await db.refresh(existing)
    return existing


def normalize_ogmo_whatsapp(raw: str) -> str:
    """Valida e normaliza número BR (E.164 sem +). Levanta ValueError se inválido."""
    return _normalize_br(raw)


async def resolve_ogmo_whatsapp(
    db: AsyncSession,
) -> tuple[str | None, OgmoWhatsappFonte]:
    """Ordem: DB `ogmo_whatsapp` > env `OGMO_WHATSAPP` > none."""
    db_val = await get_setting(db, OGMO_WHATSAPP_KEY)
    if db_val and db_val.strip():
        try:
            return normalize_ogmo_whatsapp(db_val.strip()), "db"
        except ValueError:
            pass

    env_val = (settings.ogmo_whatsapp or "").strip()
    if env_val:
        try:
            return normalize_ogmo_whatsapp(env_val), "env"
        except ValueError:
            pass

    return None, "none"


def evolution_configured() -> bool:
    return bool(settings.evolution_api_url and settings.evolution_api_key)


__all__ = [
    "OGMO_WHATSAPP_KEY",
    "OgmoWhatsappFonte",
    "evolution_configured",
    "get_setting",
    "normalize_ogmo_whatsapp",
    "resolve_ogmo_whatsapp",
    "upsert_setting",
]
