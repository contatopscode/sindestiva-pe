# Sprint 7 — Go-Live (26-28/10/2026)

## Marco: M4 GO-LIVE + termo de aceite Josias

### Entregáveis
- Deploy final em produção (Hetzner CPX31 + Traefik)
- Backup completo + restore testado
- Monitoramento 24/7 (Uptime Kuma + Sentry)
- Apresentação formal a Josias + diretoria (1h)
- Carta formal ao OGMO/PE (AR digitalizado)
- Retrospectiva + documento de entrega
- Termo de aceite assinado por Josias
- Estabilização (Paulo on-call até 31/10)

### Tabelas tocadas
- (sem novas tabelas)
- (opcional Sprint 8 — adiar pra Fase 2): partição mensal
  de `lousa_snapshots` e `lousa_cells`

### Tarefas
- T7-01: deploy prod + smoke tests
- T7-02: backup completo + restore
- T7-03: monitoramento 24/7
- T7-04: apresentação Josias + diretoria
- T7-05: carta formal OGMO (com AR digitalizado)
- T7-06: retrospectiva + lições aprendidas
- T7-07: termo de aceite Josias
- T7-08: estabilização on-call

### Riscos finais (M4 Go-Live)
- Bug P0 não resolvido em 24h → Paulo on-call
- Performance ruim → load test manual com 10 usuários (R45-08)
