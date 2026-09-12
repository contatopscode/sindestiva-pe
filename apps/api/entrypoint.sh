#!/bin/sh
# =============================================================================
# SINDESTIVA-PE · API entrypoint (Coolify/prod-ready)
#
# Ordem de execução (todas idempotentes):
#   1. `alembic upgrade head` — aplica migrations pendentes
#   2. `seed_catalogos.py` (se catálogos vazios) — popula portos, turnos, funcoes,
#      fainas, feriados (idempotente: INSERT ... ON CONFLICT DO NOTHING).
#   3. `seed_initial.py` (se existir) — popula users essenciais (admin, etc)
#   4. `uvicorn` — inicia o servidor FastAPI
#
# Por que migrations antes de uvicorn?
#   - Sprint 0 usava `Base.metadata.create_all` no lifespan (idempotente mas
#     limitado). Agora temos Alembic em prod (3 versions aplicadas). Deixar
#     uvicorn subir antes das migrations causa race em requests que dependem
#     de tabelas novas.
#   - Em dev (`pnpm dev:api`), roda direto sem migrations.
#
# Por que seed_catalogos é separado do seed_initial?
#   - seed_catalogos popula tabelas SEM dependência de users (5 tabelas: portos,
#     turnos, funcoes, fainas, feriados). Precisa rodar PRIMEIRO pra o scraper
#     funcionar (precisa de portos/turnos).
#   - seed_initial popula users (admin, demo) que dependem dos catálogos.
#
# Falha fast: qualquer erro aqui mata o container com exit≠0, Coolify não
# promove pra healthy e aciona alerta.
# =============================================================================
set -e

VENV_BIN="/app/.venv/bin"

echo "==> [1/4] Alembic upgrade head (idempotente)..."
"$VENV_BIN/alembic" upgrade head || {
    echo "ERRO: alembic upgrade falhou. Abortando."
    exit 1
}

echo "==> [2/4] Seed catálogos (idempotente — popula portos/turnos/funcoes/fainas/feriados)..."
if [ -f "/app/scripts/seed_catalogos.py" ]; then
    "$VENV_BIN/python" /app/scripts/seed_catalogos.py || {
        echo "AVISO: seed_catalogos falhou (não-bloqueante). Prosseguindo."
    }
else
    echo "    (sem seed_catalogos.py — pulando)"
fi

echo "==> [3/4] Seed inicial (idempotente — só popula users se vazio)..."
if [ -f "/app/scripts/seed_initial.py" ]; then
    "$VENV_BIN/python" /app/scripts/seed_initial.py || {
        echo "AVISO: seed_initial falhou (não-bloqueante). Prosseguindo."
    }
else
    echo "    (sem seed_initial.py — pulando)"
fi

echo "==> [4/4] Iniciando uvicorn..."
exec "$VENV_BIN/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
