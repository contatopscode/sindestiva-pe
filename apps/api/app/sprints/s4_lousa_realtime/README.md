# Sprint 4 — Centro de Comando em tempo real (05-11/10/2026)

## Marco: intermediário dentro de M2

### Entregáveis
- WebSocket push < 2s de novos snapshots
- UI Centro de Comando consumindo `lousa_snapshots` + `lousa_cells`
- KPI cards (TPAs escalados, presença, remanejamentos, sync)
- Fila "Notificação OGMO" lateral (PEND/SENT/ACK/NACK)

### Tabelas tocadas
- (read em `lousa_snapshots`, `lousa_cells`)
- (read em `remanejamentos`, `ogmo_notificacoes`)

### Tarefas
- T4-01: WebSocket endpoint
- T4-02: query otimizada (Centro de Comando 1.144 cells)
- T4-03: render React (apps/web)
- T4-04: alternador porto/turno
- T4-05: WebSocket push
- T4-06: KPI cards
- T4-07: fila OGMO lateral
- T4-08: modal de remanejamento (preparação S5)

### Decisão aberta
- **D6** (normalização lousa_cells): confirmar em Sprint 4 se a
  query do Centro de Comando (< 2s) aguenta o volume antes da
  partição. Se não, antecipar partição pra Sprint 5.
