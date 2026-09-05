#!/bin/sh
# =============================================================================
# SINDESTIVA-PE · API entrypoint (Sprint 0+)
#
# Roda migrations Alembic antes de subir o uvicorn. Idempotente — Alembic
# detecta que o schema já está no estado atual e não faz nada.
#
# Decisões:
#  - Usa `alembic upgrade head` (não `alembic stamp head`): se o schema está
#    vazio, cria tudo; se já tem migrations, só aplica as pendentes.
#  - Falha fast: se migrations falharem, uvicorn NÃO sobe (deploy fica
#    vermelho, aciona alerta).
#  - O env.py já faz CREATE SCHEMA IF NOT EXISTS lousa_main + SET search_path,
#    então mesmo o cluster Postgres compartilhado do Sinapse funciona.
# =============================================================================
set -e

echo "==> entrypoint.sh: rodando migrations Alembic..."
uv run alembic upgrade head

echo "==> entrypoint.sh: iniciando uvicorn..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
