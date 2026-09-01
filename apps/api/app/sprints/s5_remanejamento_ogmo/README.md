# Sprint 5 — Remanejamento + Notificação OGMO (12-18/10/2026)

## Marco: intermediário dentro de M3

### Entregáveis
- `POST /remanejamentos` com validação completa
- Hash chain SHA-256 no momento da criação
- Worker Resend (template HTML + PDF WeasyPrint)
- Webhook HMAC-SHA256 preparado (aguarda endpoint OGMO)
- Tela `/remanejamentos` (histórico + 4 KPIs)
- Status enum com transições controladas

### Tabelas tocadas
- `remanejamentos` (insert + status update)
- `remanejamento_historico` (insert por transição)
- `ogmo_notificacoes` (insert por tentativa de envio)
- `cct_clausulas` (seed a partir da CCT 2024-2026)

### Tarefas
- T5-01: POST /remanejamentos
- T5-02: validações (motivo, base legal, fiscal)
- T5-03: seed cct_clausulas (Josias entrega CCT)
- T5-04: hash chain no create
- T5-05: worker Resend
- T5-06: WeasyPrint PDF
- T5-07: webhook HMAC preparado
- T5-08: tela de leitura /remanejamentos
- T5-09: histórico (remanejamento_historico)
- T5-10: transições de status
- T5-11: retry com backoff
- T5-12: testes E2E Playwright

### Decisões abertas a sinalizar

- **D8** (hash chain remanejamentos × audit_events): Sprint 5
  decide. Recomendação = cadeia única global em `audit_events`;
  `remanejamentos.hash_evento` vira redundante.
- **D9** (remanejamento_historico × audit_events): Sprint 5/6 decide.
  Recomendação = unificar via view.

### Risco #1 do sprint
**R1 — OGMO/PE boicota integração**. Mitigação: e-mail unilateral
funciona sem aprovação; MPT como aliado (modelo OGMO-RG).
