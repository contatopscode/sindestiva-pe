"""SINDESTIVA-PE · Integração OGMO (notificações + webhook endpoints).

DD v1 §3.16, §3.17.

`OgmoNotificacao` rastreia **toda** tentativa de envio ao OGMO. É a
**prova documental** entregue ao OGMO/PE. Funciona **sem aprovação do
OGMO** (R1 do plano).

`OgmoWebhookEndpoint` fica vazio no MVP (OGMO/PE não respondeu à
carta) — preparado para Fase 3.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import CanalNotificacaoEnum, StatusNotificacaoEnum, pg_enum


# ---------------------------------------------------------------------------
# OgmoNotificacao (DD v1 §3.16)
# ---------------------------------------------------------------------------

class OgmoNotificacao(Base, TimestampMixin):
    """Cada e-mail/webhook enviado ao OGMO.

    Risco R1 (OGMO boicota): este tabela existe para provar que
    tentamos notificar. Mesmo sem ACK do OGMO, o sistema funciona
    unilateralmente.

    Retenção: 5 anos (audit).
    """

    __tablename__ = "ogmo_notificacoes"
    __table_args__ = (
        Index("idx_ogmo_notif_remanejamento", "remanejamento_id"),
        Index("idx_ogmo_notif_canal", "canal"),
        Index("idx_ogmo_notif_payload_gin", "payload_json", postgresql_using="gin"),
        Index("idx_ogmo_notif_hash", "payload_hash_sha256"),
        Index("idx_ogmo_notif_provider_id", "provider_message_id"),
        Index("idx_ogmo_notif_status", "status"),
        Index("idx_ogmo_notif_proxima_tentativa", "proxima_tentativa_em"),
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    remanejamento_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.remanejamentos.id", ondelete="RESTRICT"),
        nullable=False,
    )

    canal: Mapped[CanalNotificacaoEnum] = mapped_column(
        pg_enum(CanalNotificacaoEnum), nullable=False
    )
    template_id: Mapped[str] = mapped_column(Text, nullable=False)  # remanejamento_v1
    assunto: Mapped[str | None] = mapped_column(Text, nullable=True)

    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_hash_sha256: Mapped[str] = mapped_column(Text(64), nullable=False)

    destinatario_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    destinatario_webhook_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lousa_main.ogmo_webhook_endpoints.id", ondelete="SET NULL"),
        nullable=True,
    )

    provider_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[StatusNotificacaoEnum] = mapped_column(
        pg_enum(StatusNotificacaoEnum),
        nullable=False,
        server_default=text("'PENDENTE'::status_notificacao_enum"),
    )
    tentativas: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    proxima_tentativa_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    enviado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entregue_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    falhou_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    erro_detalhes: Mapped[str | None] = mapped_column(Text, nullable=True)

    pdf_anexo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # LGPD: retenção explícita 5 anos (não usa SoftDeleteMixin porque
    # não tem PII direta — só referência a remanejamento que tem PII
    # via FK).
    purge_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now() + INTERVAL '5 years'"),
    )


# ---------------------------------------------------------------------------
# OgmoWebhookEndpoint (DD v1 §3.17)
# ---------------------------------------------------------------------------

class OgmoWebhookEndpoint(Base, TimestampMixin):
    """Endpoints cadastrados do OGMO para notificação por webhook.

    No MVP fica vazio (OGMO/PE não respondeu à carta). Estrutura já
    existe para quando OGMO topar (Fase 3).

    TODO(D10): `secret_hmac` armazenado criptografado (pgcrypto ou
    KMS)? Recomendação SINDESTIVA Bot = (a) pgcrypto no MVP.
    """

    __tablename__ = "ogmo_webhook_endpoints"
    __table_args__ = (
        {"schema": "lousa_main"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))

    porto_id: Mapped[UUID] = mapped_column(
        ForeignKey("lousa_main.portos.id", ondelete="RESTRICT"),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(Text, nullable=False)
    secret_hmac: Mapped[str] = mapped_column(Text, nullable=False)  # criptografado (D10)
    eventos_assinados: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("ARRAY['remanejamento.criado','remanejamento.atualizado']"),
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    ultimo_ping_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_ping_status: Mapped[int | None] = mapped_column(Integer, nullable=True)


__all__ = ["OgmoNotificacao", "OgmoWebhookEndpoint"]
