# syntax=docker/dockerfile:1.7
# =============================================================================
# SINDESTIVA-PE · Scraper Dockerfile (worker Python)
#
# Worker que roda scraping de TPA/Suape + EscalaNet/Recife a cada 60s.
# Mesmo padrão do `apps/api/Dockerfile` (uv + multi-stage + non-root).
# =============================================================================

# ----- Stage 1: deps -----
FROM python:3.12-slim-bookworm AS deps

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# System deps (Playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /app

# Copia manifestos
COPY services/scraper/pyproject.toml services/scraper/uv.lock services/scraper/README.md ./
RUN uv sync --frozen --no-dev

# ----- Stage 2: runtime -----
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 1001 scraperuser \
    && useradd --system --uid 1001 --gid scraperuser --home-dir /app --shell /usr/sbin/nologin scraperuser

WORKDIR /app

COPY --from=deps --chown=scraperuser:scraperuser /app/.venv /app/.venv
COPY --chown=scraperuser:scraperuser services/scraper ./scraper

USER scraperuser

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "scraper"]
