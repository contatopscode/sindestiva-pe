#!/bin/sh
# =============================================================================
# SINDESTIVA-PE · API entrypoint (Coolify/prod-ready)
#
# Ordem de execução (todas idempotentes):
#   1. `alembic upgrade head` — aplica migrations pendentes
#   2. `seed_initial.py` (se existir) — popula users + catálogos essenciais
#      se as tabelas estiverem vazias (não sobrescreve dados existentes)
#   3. `uvicorn` — inicia o servidor FastAPI
#
# Por que migrations antes de uvicorn?
#   - Sprint 0 usava `Base.metadata.create_all` no lifespan (idempotente mas
#     limitado). Agora temos Alembic em prod (3 versions aplicadas). Deixar
#     uvicorn subir antes das migrations causa race em requests que dependem
#     de tabelas novas.
#   - Em dev (`pnpm dev:api`), roda direto sem migrations.
#
# Falha fast: qualquer erro aqui mata o container com exit≠0, Coolify não
# promove pra healthy e aciona alerta.
# =============================================================================
set -e

VENV_BIN="/app/.venv/bin"

echo "==> [1/3] Alembic upgrade head (idempotente)..."
"$VENV_BIN/alembic" upgrade head || {
    echo "ERRO: alembic upgrade falhou. Abortando."
    exit 1
}

echo "==> [2/3] Seed inicial (idempotente — só popula se vazio)..."
if [ -f "/app/scripts/seed_initial.py" ]; then
    "$VENV_BIN/python" /app/scripts/seed_initial.py || {
        echo "AVISO: seed_initial falhou (não-bloqueante). Prosseguindo."
    }
else
    echo "    (sem seed_initial.py — pulando)"
fi

echo "==> [3/3] Iniciando uvicorn..."
exec "$VENV_BIN/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
