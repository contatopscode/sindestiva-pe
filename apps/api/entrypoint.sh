#!/bin/sh
# =============================================================================
# SINDESTIVA-PE · API entrypoint (Coolify/prod-ready)
#
# Ordem de execução (todas idempotentes):
#   0. `ensure_db_extensions.py` — schema lousa_main + pgcrypto/citext/pg_trgm
#      (Coolify Postgres fresh não roda init.sql; create_all precisa de pg_trgm)
#   1. `ensure_db_migrations.py` — Alembic upgrade head + drift repair (stamp)
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

echo "==> [0/5] Postgres bootstrap (schema + extensions pg_trgm/citext/pgcrypto)..."
if [ -f "/app/scripts/ensure_db_extensions.py" ]; then
    "$VENV_BIN/python" /app/scripts/ensure_db_extensions.py || {
        echo "ERRO: ensure_db_extensions falhou. Abortando."
        echo "      Se o role não tem CREATE EXTENSION, rode como superuser:"
        echo "      CREATE EXTENSION IF NOT EXISTS pgcrypto;"
        echo "      CREATE EXTENSION IF NOT EXISTS citext;"
        echo "      CREATE EXTENSION IF NOT EXISTS pg_trgm;"
        exit 1
    }
else
    echo "ERRO: /app/scripts/ensure_db_extensions.py ausente. Abortando."
    exit 1
fi

echo "==> [1/5] Alembic migrate + drift repair (stamp se version > tabelas)..."
if [ -f "/app/scripts/ensure_db_migrations.py" ]; then
    "$VENV_BIN/python" /app/scripts/ensure_db_migrations.py || {
        echo "ERRO: ensure_db_migrations falhou. Abortando."
        exit 1
    }
else
    echo "ERRO: /app/scripts/ensure_db_migrations.py ausente. Abortando."
    exit 1
fi

echo "==> [2/5] Seed catálogos (idempotente — popula portos/turnos/funcoes/fainas/feriados)..."
if [ -f "/app/scripts/seed_catalogos.py" ]; then
    "$VENV_BIN/python" /app/scripts/seed_catalogos.py || {
        echo "AVISO: seed_catalogos falhou (não-bloqueante). Prosseguindo."
    }
else
    echo "    (sem seed_catalogos.py — pulando)"
fi

echo "==> [3/5] Seed inicial (idempotente — só popula users se vazio)..."
if [ -f "/app/scripts/seed_initial.py" ]; then
    "$VENV_BIN/python" /app/scripts/seed_initial.py || {
        echo "AVISO: seed_initial falhou (não-bloqueante). Prosseguindo."
    }
else
    echo "    (sem seed_initial.py — pulando)"
fi

echo "==> [4/5] Iniciando uvicorn..."
exec "$VENV_BIN/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
