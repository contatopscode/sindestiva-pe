# services/scraper

Worker de scraping do TPA/OGMO-PE e do EscalaNet/Recife.

Fora do Turborepo propositalmente — ciclo próprio (cron 60s) quando deployado
como worker separado. **Em produção Coolify (2026-09), o loop ativo está no
lifespan da API** (`apps/api/app/jobs/scraping_job.py`); use os logs do
serviço `api` para observabilidade. Este pacote permanece como placeholder /
worker opcional. Reusa o mesmo banco (`DATABASE_URL`) da API.

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
