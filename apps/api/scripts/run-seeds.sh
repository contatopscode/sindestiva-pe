#!/bin/sh
# =============================================================================
# SINDESTIVA-PE · Seed runner (idempotente) — Sprint A.1
#
# Roda os 3 seeds em ordem:
#   1. catalogos (portos, turnos, funcoes, fainas) — sem dependência
#   2. users (Paulo/Manoel/Josias) — depende de funcoes (para FISCAL)
#   3. tpas_demo (TPA-001/TPA-002) — depende de users e funcoes
#
# Idempotente: cada seed usa upsert por chave natural (email, código).
#
# Onde rodar:
#   - Render Shell do serviço `sindestiva-api`
#   - Localmente: `bash scripts/run-seeds.sh` (do diretório apps/api/)
#
# Variáveis necessárias (já estão no .env do Render):
#   DATABASE_URL_ASYNC=postgresql+asyncpg://...
#
# Saída: imprime resumo com totais e exit 0 se OK, exit 1 se falhou.
# =============================================================================
set -e

VENV_BIN="${VENV_BIN:-/app/.venv/bin}"

# Detecta venv local (apps/api/.venv) se não houver /app/.venv
if [ ! -x "$VENV_BIN/python" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    VENV_BIN="$SCRIPT_DIR/../.venv/bin"
fi

PY="$VENV_BIN/python"

if [ ! -x "$PY" ]; then
    echo "ERRO: Python não encontrado em $VENV_BIN"
    echo "Set VENV_BIN=/caminho/do/.venv/bin antes de rodar."
    exit 1
fi

echo "==> Python: $($PY --version)"
echo "==> DB: ${DATABASE_URL_ASYNC:-<não setado>}"
echo

echo "================================================================"
echo " 1/3 · Seed de CATÁLOGOS (portos, turnos, funções, fainas)"
echo "================================================================"
$PY scripts/seed_catalogos.py
echo

echo "================================================================"
echo " 2/3 · Seed de USERS (Paulo/Manoel/Josias)"
echo "================================================================"
$PY scripts/seed_users.py
echo

echo "================================================================"
echo " 3/3 · Seed de TPAs demo (TPA-001, TPA-002)"
echo "================================================================"
$PY scripts/seed_tpas_demo.py
echo

echo "================================================================"
echo " ✅ Seeds concluídos!"
echo "================================================================"
echo
echo "Próximos passos:"
echo "  1. Validar login:"
echo "       POST /api/v1/auth/login {email:'paulo@pscode.ia.br', password:'sindestiva-dev-2026'}"
echo "  2. Disparar scrape TPA+ESCALANET:"
echo "       POST /api/v1/scraping/disparar {fonte:'TPA',porto:'SUAPE',turno:'DIURNO'}"
echo "       POST /api/v1/scraping/disparar {fonte:'ESCALANET',porto:'RECIFE',turno:'DIURNO'}"
echo "  3. Testar PWA com TPA-001 ou TPA-002 (não mais OG-101D)"
