"""SINDESTIVA-PE · Migration 0004 — server_default em purge_after (Sprint 1+).

Dívida declarada em `app.models.base.SoftDeleteMixin` ("Sprint 1+:
reintroduzir via Alembic"). O `default` Python-side cobre INSERTs ORM,
mas se um deploy parte de schema vazio via `Base.metadata.create_all`,
o DEFAULT server-side precisa estar presente para INSERTs SQL diretos
e para o cenário do bug SINDESTIVA-PE-FSW-2026-006 (H1).

IMPORTANTE: usar `op.execute(...)` com SQL cru, NÃO
`mapped_column(server_default=sa.text(...))`. O wrapping de `text()`
pelo SQLAlchemy 2 no DDL do `create_all` foi o que quebrou em
`fe23ab1` (Postgres não faz cast de text() → timestamptz).

DD v1 §3 retenções: `users`/`tpas`/`tpa_confirmacoes_presenca` = 24m;
demais (`fiscais`, `dirigentes`, `remanejamentos`, `ogmo_notificacoes`,
`lgpd_solicitacoes`) = 5y. Alinhado com 0001:298-958.

Apenas 8 tabelas POSSUEM coluna `purge_after` na migration 0001
(linhas 298-958). Tabelas como `audit_events`, `hash_chain_checkpoint`
e `access_log` têm retenção INDEFINIDA por design (DD v1 §3.20/§3.21/
§3.22) e NÃO devem ser tocadas.

Forward-only (convenção do projeto), mas `downgrade()` simétrico é
provido por consistência com 0001/0002/0003.

Revision ID: 0004_purge_after_server_default
Revises: 0003_lousa_alocacao
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_purge_after_server_default"
down_revision: str | Sequence[str] | None = "0003_lousa_alocacao"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SCHEMA = "lousa_main"


def upgrade() -> None:
    # Retenção 24 months (D04 — alinhado com 0001:298-299, 350-351, 878-879).
    op.execute("ALTER TABLE lousa_main.users ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '24 months'")
    op.execute("ALTER TABLE lousa_main.tpas ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '24 months'")
    op.execute("ALTER TABLE lousa_main.tpa_confirmacoes_presenca ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '24 months'")
    # Retenção 5 years (D04 — alinhado com 0001:401-402, 445-446, 647-648,
    # 831-832, 957-958).
    op.execute("ALTER TABLE lousa_main.fiscais ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '5 years'")
    op.execute("ALTER TABLE lousa_main.dirigentes ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '5 years'")
    op.execute("ALTER TABLE lousa_main.remanejamentos ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '5 years'")
    op.execute("ALTER TABLE lousa_main.ogmo_notificacoes ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '5 years'")
    op.execute("ALTER TABLE lousa_main.lgpd_solicitacoes ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '5 years'")


def downgrade() -> None:
    # Downgrade simétrico para as 8 tabelas que efetivamente têm
    # `purge_after`. Idempotente — DROP DEFAULT não falha se já foi
    # removido.
    op.execute("ALTER TABLE lousa_main.users ALTER COLUMN purge_after DROP DEFAULT")
    op.execute("ALTER TABLE lousa_main.tpas ALTER COLUMN purge_after DROP DEFAULT")
    op.execute("ALTER TABLE lousa_main.tpa_confirmacoes_presenca ALTER COLUMN purge_after DROP DEFAULT")
    op.execute("ALTER TABLE lousa_main.fiscais ALTER COLUMN purge_after DROP DEFAULT")
    op.execute("ALTER TABLE lousa_main.dirigentes ALTER COLUMN purge_after DROP DEFAULT")
    op.execute("ALTER TABLE lousa_main.remanejamentos ALTER COLUMN purge_after DROP DEFAULT")
    op.execute("ALTER TABLE lousa_main.ogmo_notificacoes ALTER COLUMN purge_after DROP DEFAULT")
    op.execute("ALTER TABLE lousa_main.lgpd_solicitacoes ALTER COLUMN purge_after DROP DEFAULT")