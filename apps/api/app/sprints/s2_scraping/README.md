# Sprint 2 — Scraping (21-27/09/2026)

## Marco: M1 Lousa oficial de Suape espelhada

### Entregáveis
- Scraper TPA/Suape (Playwright headless, parser tolerante 3 níveis)
- Cron de scraping a cada 60s durante operação (06h-22h)
- Alerta de mudança de layout (hash HTML + e-mail/WhatsApp)
- Scraper EscalaNet/Recife (HTTPX, PHP simples)
- Matcher de TPAs (matrícula OGMO × cadastro Sindicato)
- Endpoints `GET /api/v1/lousa/atual?porto=X&turno=Y`
- Endpoint `GET /api/v1/lousa/porto/{slug}/turno/{turno}`

### Tabelas tocadas
- `lousa_snapshots` (insert a cada scrape)
- `lousa_cells` (insert em batch — 1.144 cells/snapshot)
- `layout_fingerprints` (insert quando HTML muda)
- `navios` (insert opcional quando scraper identifica navio)

### Tarefas
- T2-01: scraper TPA/Suape
- T2-02: cron 60s (`app/jobs/scraper_tpa.py`)
- T2-03: alerta mudança layout (R2)
- T2-04: scraper EscalaNet/Recife (`app/jobs/scraper_escalanet.py`)
- T2-05: matcher de TPAs (D13 — coluna `tpas.matricula_ogmo`)
- T2-06/T2-07: endpoints `GET /lousa/atual`, `GET /lousa/...` (OK)
- T2-08: testes com fixture HTML congelada

### Decisões abertas a sinalizar

- **D6** (normalização lousa_cells): Sprint 2 grava TUDO; Sprint 7
  adiciona partição mensal. Migration 0001 já prepara
  `data_referencia` desnormalizado pra BI.
- **D12** (parser heurística vs ML): recomendação = heurística (regex
  + fallback). ML em Fase 2.

### Risco #1 do sprint
**R2 — TPA Tecnologia muda layout**. Mitigação: hash do HTML bruto
em `lousa_snapshots.html_hash_sha256` + alerta < 5 min quando
divergir do último conhecido (`layout_fingerprints.is_current = true`).
