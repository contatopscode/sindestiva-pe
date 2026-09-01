"""SINDESTIVA-PE · ORM models (SQLAlchemy 2 async, Mapped[] + mapped_column).

Mapa rápido (1 ficheiro por domínio, conforme DD v1):

  base          → DeclarativeBase + AsyncAttrs + TimestampMixin + SoftDeleteMixin
  enums         → role, user_status, tpa_status, fiscal_status,
                  snapshot_status, cell_status, motivo_remanejamento,
                  status_remanejamento, canal_notificacao, status_notificacao,
                  termo_metodo, lgpd_tipo, lgpd_status
  users         → User
  catalogos     → Porto, Turno, Funcao, Faina, Navio, FeriadoNacional, CctClausula
  lousa         → LousaSnapshot, LousaCell, LayoutFingerprint
  remanejamento → Remanejamento, RemanejamentoHistorico
  ogmo          → OgmoNotificacao, OgmoWebhookEndpoint
  tpa_operacao  → TpaConfirmacaoPresenca
  auditoria     → AuditEvent, HashChainCheckpoint, AccessLog
  lgpd          → TermoConsentimento, LgpdSolicitacao, LgpdPurgeLog
  perfis_internos → Fiscal, Dirigente (perfis 1:1 com User;
                   renomeado de cidadao.py — nome semântico errado,
                   são perfis internos do Sindicato, não cidadãos externos)

DD v1 §3 lista 25 tabelas (o `roles` é ENUM, não tabela — DD §3.2
explicita esta decisão). Migration 0001 cria as 25 + 13 enums + 13
triggers.
"""
from app.models.auditoria import AccessLog, AuditEvent, HashChainCheckpoint
from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.catalogos import (
    CctClausula,
    Faina,
    FeriadoNacional,
    Funcao,
    Navio,
    Porto,
    Turno,
)
from app.models.enums import (
    CanalNotificacaoEnum,
    CellStatusEnum,
    FiscalStatusEnum,
    FonteEscalaEnum,
    LgpdStatusEnum,
    LgpdTipoEnum,
    MotivoRemanejamentoEnum,
    RoleEnum,
    SnapshotStatusEnum,
    StatusNotificacaoEnum,
    StatusRemanejamentoEnum,
    StatusScrapingEnum,
    TermoMetodoEnum,
    TpaStatusEnum,
    UserStatusEnum,
)
from app.models.lgpd import LgpdPurgeLog, LgpdSolicitacao, TermoConsentimento
from app.models.lousa import LayoutFingerprint, LousaCell, LousaSnapshot
from app.models.lousa_scraping import LousaAlocacao, LousaEscalaOrigem
from app.models.ogmo import OgmoNotificacao, OgmoWebhookEndpoint
from app.models.perfis_internos import Dirigente, Fiscal
from app.models.remanejamento import Remanejamento, RemanejamentoHistorico
from app.models.tpa_operacao import TpaConfirmacaoPresenca
from app.models.users import Tpa, User

__all__ = [
    # base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    # enums
    "CanalNotificacaoEnum",
    "CellStatusEnum",
    "FiscalStatusEnum",
    "FonteEscalaEnum",
    "LgpdStatusEnum",
    "LgpdTipoEnum",
    "MotivoRemanejamentoEnum",
    "RoleEnum",
    "SnapshotStatusEnum",
    "StatusNotificacaoEnum",
    "StatusRemanejamentoEnum",
    "StatusScrapingEnum",
    "TermoMetodoEnum",
    "TpaStatusEnum",
    "UserStatusEnum",
    # users
    "User",
    "Tpa",
    # perfis internos
    "Fiscal",
    "Dirigente",
    # catalogos
    "Porto",
    "Turno",
    "Funcao",
    "Faina",
    "Navio",
    "FeriadoNacional",
    "CctClausula",
    # lousa
    "LousaSnapshot",
    "LousaCell",
    "LayoutFingerprint",
    # lousa scraping (Sprint 2)
    "LousaEscalaOrigem",
    "LousaAlocacao",
    # remanejamento
    "Remanejamento",
    "RemanejamentoHistorico",
    # ogmo
    "OgmoNotificacao",
    "OgmoWebhookEndpoint",
    # tpa
    "TpaConfirmacaoPresenca",
    # auditoria
    "AuditEvent",
    "HashChainCheckpoint",
    "AccessLog",
    # lgpd
    "TermoConsentimento",
    "LgpdSolicitacao",
    "LgpdPurgeLog",
]
