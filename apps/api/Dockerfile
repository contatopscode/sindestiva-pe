# syntax=docker/dockerfile:1.7
# =============================================================================
# SINDESTIVA-PE · API Dockerfile
#
# Multi-stage build para a API FastAPI (Sprint 0+).
# Render: Web Service (sindestiva-api).
#
# Decisões:
#  - Base `python:3.12-slim-bookworm` (libpango/libcairo atualizados p/
#    WeasyPrint 64.x; libgbm/libnss3，万一 Playwright for usado no futuro).
#  - `uv` em vez de `pip` (mesmo padrão do scraper e do Sinapse).
#  - `uv sync --frozen --no-dev` — reproduzível (uv.lock) e sem deps de teste.
#  - `uv run` ativa o venv automaticamente.
#  - Usuário não-root (`appuser`) — hardening básico.
#  - Health check via `GET /health` (FastAPI endpoint do app.main).
# =============================================================================

# ----- Stage 1: deps (cache layer) -----
FROM python:3.12-slim-bookworm AS deps

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# System deps (WeasyPrint precisa de Cairo/Pango; Playwright，万一 use no futuro)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    # WeasyPrint
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev libcairo2 libpangoft2-1.0-0 \
    fonts-liberation fonts-noto-color-emoji \
    # Playwright chromium
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Install uv (binary, sem pip)
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /app

# Copia manifestos PRIMEIRO (cache de layer: deps só reinstalam se mudar).
# README.md é necessário porque o pyproject declara `readme = "README.md"`
# e o hatchling valida esse arquivo durante `uv sync` (mesmo em modo
# install-only, o backend de build é invocado).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# ----- Stage 2: runtime (imagem final, mais enxuta) -----
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

# Re-instala system deps no stage final (não dá pra herdar do stage 1)
# WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libcairo2 libpangoft2-1.0-0 \
    fonts-liberation fonts-noto-color-emoji \
    # tini para sinais (SIGTERM limpo pro uvicorn)
    tini \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser

WORKDIR /app

# Copia venv do stage deps (caminho idêntico)
COPY --from=deps --chown=appuser:appuser /app/.venv /app/.venv

# Copia código da aplicação
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./

USER appuser

EXPOSE 8000

# Health check (Render usa `HEALTHCHECK_PATH` configurado no render.yaml;
# este HEALTHCHECK é fallback para docker run local).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status == 200 else 1)"

# tini como PID 1 (forwarda SIGTERM pro uvicorn → graceful shutdown)
ENTRYPOINT ["/usr/bin/tini", "--"]

# uvicorn direto (sem `uv run` porque o venv já está no PATH)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
