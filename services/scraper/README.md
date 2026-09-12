# services/scraper

> **Estado atual (Sprint B0): placeholder.** O entrypoint `sindestiva-scraper`
> só emite log e encerra. **Scraping de produção roda dentro do container
> `api`** (`apps/api/app/jobs/scraping_job.py`, lifespan do FastAPI).

Worker futuro do TPA/OGMO-PE e do EscalaNet/Recife — fora do Turborepo
propositalmente (ciclo próprio, cron 60s quando deployado como worker
separado). **Em produção Coolify (2026-09), o loop ativo está no lifespan da
API** (`apps/api/app/jobs/scraping_job.py`); monitore logs do serviço **api** e
`GET /api/v1/scraping/status`. Este pacote permanece placeholder / worker
opcional. Reusa o mesmo banco (`DATABASE_URL`) da API.

## Run local

```bash
cd services/scraper
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
sindestiva-scraper
```

## Fontes

- **TPA OGMO/Suape** (AngularJS v1.24.0) — Playwright + BeautifulSoup, parser tolerante
- **EscalaNet/Recife** (PHP) — HTTPX direto
- Detecção de mudança de layout: hash SHA-256 do HTML vs. último conhecido
- Alertas: log + canal WhatsApp (Evolution API)
