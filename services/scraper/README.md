# services/scraper

> **Estado atual (Sprint B0): placeholder.** O entrypoint `sindestiva-scraper`
> só emite log e encerra. **Scraping de produção roda dentro do container
> `api`** (`apps/api/app/jobs/scraping_job.py`, lifespan do FastAPI).

Worker futuro do TPA/OGMO-PE e do EscalaNet/Recife (fora do Turborepo — ciclo
próprio). Reusa o mesmo banco (`DATABASE_URL`) da API. Até a migração do loop
para cá, monitore logs do serviço **api** e `GET /api/v1/scraping/status`.

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
