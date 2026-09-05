#!/bin/sh
# =============================================================================
# SINDESTIVA-PE · API entrypoint (Sprint 0+)
#
# Cria schema + tabelas (via lifespan do FastAPI) antes de subir o
# uvicorn. Idempotente — Base.metadata.create_all(checkfirst=True) só
# cria o que falta.
#
# Decisões:
#  - Sprint 0+ usa `Base.metadata.create_all` em vez de Alembic porque
#    em prod (Render) com DB compartilhado, o Alembic falha silenciosamente
#    em criar tabelas (transactions revertem por permissão do role).
#    Sprint 2+ vai refazer com Alembic dedicado.
#  - Usa caminho ABSOLUTO do venv (`/app/.venv/bin/uvicorn`) em vez de
#    `uv run uvicorn` — o runtime stage do Dockerfile NÃO tem o binary
#    `uv` (só o venv copiado), e o PATH pode não incluir o venv quando
#    tini chama o entrypoint.
#  - Falha fast: se a inicialização FastAPI falhar, uvicorn NÃO sobe
#    (deploy fica vermelho, aciona alerta).
# =============================================================================
set -e

VENV_BIN="/app/.venv/bin"

echo "==> entrypoint.sh: iniciando uvicorn (cria schema + tabelas no lifespan)..."
exec "$VENV_BIN/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
