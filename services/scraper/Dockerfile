# syntax=docker/dockerfile:1.7
# =============================================================================
# SINDESTIVA-PE · Scraper Worker Dockerfile
#
# Render: Background Worker (sindestiva-scraper).
# Roda cron a cada 60s (06h-22h) contra TPA Tecnologia + EscalaNet.
#
# Decisões:
#  - Imagem MAIS LEVE que a da API (sem WeasyPrint, sem Playwright browser).
#    O scraper TPA atual usa só httpx + BeautifulSoup — Playwright é mantido
#    como dep Python para futuros layouts com JS, mas NÃO baixamos o browser
#    (~170MB) na build. Baixar sob demanda com `playwright install` se
#    algum scraper futuro precisar.
#  - `uv` (mesmo padrão da API).
#  - `tini` como PID 1 → forwarda SIGTERM para o worker → graceful shutdown.
#  - Health check via `python -c` que testa conexão DB (Redis opcional).
#  - Usuário não-root (`appuser`) — hardening básico.
# =============================================================================

FROM python:3.12-slim-bookworm AS deps

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# System deps mínimas (sem WeasyPrint, sem Playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /app

# Manifestos PRIMEIRO (cache de layer). README.md é necessário porque
# o pyproject declara `readme = "README.md"` e o hatchling valida.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev


FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/.venv/bin:$PATH"

# Apenas tini (para forwardar SIGTERM). Sem libs de browser/WeasyPrint.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser

WORKDIR /app

# venv do stage deps
COPY --from=deps --chown=appuser:appuser /app/.venv /app/.venv

# Código
COPY --chown=appuser:appuser sindestiva_scraper ./sindestiva_scraper
COPY --chown=appuser:appuser workers ./workers
COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./

USER appuser

# Worker roda indefinido até receber SIGTERM. Render envia SIGTERM
# antes de matar (kill grace period ~10s).
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "sindestiva_scraper"]
