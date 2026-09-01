# `app/jobs/` — Jobs assíncronos (Sprint 6 + Sprint 2)

Convenção: cada arquivo é um módulo top-level com `async def run()`.
O `__main__` permite rodar standalone (`python -m app.jobs.scraper_tpa`).

| Job | Quando roda | Sprint | Tabela que escreve |
|---|---|---|---|
| `scraper_tpa.py` | cron 60s, 06h-22h | S2 T2-01/02 | `lousa_snapshots`, `lousa_cells`, `layout_fingerprints` |
| `scraper_escalanet.py` | cron 5min, Recife | S2 T2-04 | `lousa_snapshots` (Recife) |
| `hash_chain_verifier.py` | diário 03:00 | S6 T6-03 | `hash_chain_checkpoint` |
| `lgpd_purge.py` | diário 04:00 | S6 T6-06 | `lgpd_purge_log` + deleções em 13 tabelas |

## Agendamento (decisão Sprint 0 → Sprint 7)

- **Sprint 0-6:** APScheduler in-process (lifespan FastAPI) — simples.
- **Sprint 7+:** avaliar worker separado (`services/scraper/`) pra isolar
  falhas. R45-08 do cronograma cita isso.
