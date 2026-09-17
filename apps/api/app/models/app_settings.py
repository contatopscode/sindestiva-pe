"""SINDESTIVA-PE · Configurações da aplicação (key-value, schema lousa_main)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

OGMO_WHATSAPP_KEY = "ogmo_whatsapp"


class AppSetting(Base):
    """Par chave/valor editável via API (ex.: número WhatsApp do OGMO)."""

    __tablename__ = "app_settings"
    __table_args__ = ({"schema": "lousa_main"},)

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )


__all__ = ["AppSetting", "OGMO_WHATSAPP_KEY"]
