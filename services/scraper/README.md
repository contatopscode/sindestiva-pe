# services/scraper

Worker de scraping do TPA/OGMO-PE e do EscalaNet/Recife.

Fora do Turborepo propositalmente — tem ciclo próprio (cron 60s) e roda como
worker separado. Reusa o mesmo banco (`DATABASE_URL`) da API.

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
