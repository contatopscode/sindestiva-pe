# Sprint 6 — Auditoria + LGPD (19-25/10/2026)

## Marco: M3 Homologação Manoel Costa

### Entregáveis
- Trigger BEFORE UPDATE/DELETE em `audit_events` (já na migration 0001)
- Verificador diário de hash chain (job 03:00, `app/jobs/hash_chain_verifier.py`)
- DPO dashboard (Paulo acumula DPO)
- Workflow Art. 18 LGPD (`lgpd_solicitacoes`)
- Middleware `access_log` em endpoints que retornam PII
- Job diário de purga 24m (job 04:00, `app/jobs/lgpd_purge.py`)
- BI mínimo: 4 KPIs (comparecimento, remanejamentos, ranking, gráfico 7d)

### Tabelas tocadas
- `audit_events` (insert em todo endpoint que toca PII)
- `hash_chain_checkpoint` (insert pelo job 03:00)
- `lgpd_solicitacoes` (insert por TPA + workflow)
- `lgpd_purge_log` (insert por job 04:00)
- `access_log` (insert por middleware)
- deleções em 13 tabelas com `purge_after`

### Tarefas
- T6-01: GET /auditoria/eventos (já stub)
- T6-02: timeline UI auditoria
- T6-03: job verificador 03:00 (`hash_chain_verifier.py`)
- T6-04: export PDF assinado
- T6-05: export CSV
- T6-06: job purga 24m (`lgpd_purge.py`)
- T6-07: workflow Art. 18
- T6-08: DPO dashboard
- T6-09: middleware access_log
- T6-10: BI mínimo 4 KPIs
- T6-11: tela auditoria
- T6-12: trigger append-only (já na migration 0001)
- T6-13: rate limit + Helmet + CORS
- T6-14: parecer jurídico final
- T6-15: testes LGPD

### Decisões abertas a sinalizar

- **D11** (retenção `termos_consentimento`): Sprint 6 decide.
  Recomendação = manter enquanto houver relação + 5a após exclusão.
