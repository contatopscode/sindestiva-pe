#!/bin/sh
# =============================================================================
# SINDESTIVA-PE · API entrypoint (Sprint 0+)
#
# Roda migrations Alembic antes de subir o uvicorn. Idempotente — Alembic
# detecta que o schema já está no estado atual e não faz nada.
#
# Decisões:
#  - Usa caminho ABSOLUTO do `alembic` no venv (`/app/.venv/bin/alembic`)
#    em vez de `uv run alembic` — o runtime stage do Dockerfile NÃO tem
#    o binary `uv` (só o venv copiado), e o PATH pode não incluir o venv
#    quando tini chama o entrypoint.
#  - Falha fast: se migrations falharem, uvicorn NÃO sobe (deploy fica
#    vermelho, aciona alerta).
#  - O env.py já faz CREATE SCHEMA IF NOT EXISTS lousa_main + SET search_path,
#    então mesmo o cluster Postgres compartilhado do Sinapse funciona.
# =============================================================================
set -e

VENV_BIN="/app/.venv/bin"

echo "==> entrypoint.sh: rodando migrations Alembic..."
"$VENV_BIN/alembic" upgrade head

echo "==> entrypoint.sh: iniciando uvicorn..."
exec "$VENV_BIN/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
