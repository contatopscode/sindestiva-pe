# SINDESTIVA-PE · Sprints (visão executiva)

> Mapa entre **7 sprints × 8 marcos** (M0–M10 do plano v1.0, mas o
> cronograma 45d usa M0–M4) × **entregáveis** × **tabelas tocadas**.
> Tabela única de referência pro coder agent.

| Sprint | Marco | Período (plano 18 sem) | Período (cron 45d) | Entregável principal | Tabelas tocadas | Tarefas |
|---|---|---|---|---|---|---|
| **S0** | M0 Kickoff | 01–07/09/2026 | 14–18/09/2026 | (sem código) Josias + Manoel alinhados, CCT obtida, advogado contratado, infra provisionada | — | K-1 a K-7 |
| **S1** | M1 Centro autenticado | 08–20/09/2026 | 14–20/09/2026 | schema + auth NextAuth v5 + 5 catálogos seed | **todas as 25 tabelas** (migration 0001) + 5 catálogos | T1-01 a T1-11 |
| **S2** | M2 Lousa espelhada | 21/09–04/10 | 21–27/09 | scrapers TPA/Suape (Playwright) + EscalaNet/Recife (HTTPX); matcher de TPAs | `lousa_snapshots`, `lousa_cells`, `layout_fingerprints`, `navios` | T2-01 a T2-08 |
| **S3** | M3 PWA funcional | 05–18/10 | 28/09–04/10 | PWA TPA + termo LGPD v1 no fluxo | `tpa_confirmacoes_presenca`, `termos_consentimento`, `users` (login) | T3-01 a T3-09 |
| **S4** | M4 Centro tempo real | 19–25/10 | 05–11/10 | WebSocket push < 2s; Centro de Comando consumindo `lousa_*` em tempo real | (read em `lousa_snapshots`, `lousa_cells`) | T4-01 a T4-08 |
| **S5** | M5 Remanejamento + OGMO | 26/10–01/11 | 12–18/10 | fluxo completo + hash chain no create + Resend + WeasyPrint + webhook HMAC | `remanejamentos`, `remanejamento_historico`, `ogmo_notificacoes`, `cct_clausulas` | T5-01 a T5-12 |
| **S6** | M6 Auditoria + LGPD | 02–15/11 | 19–25/10 | hash chain SHA-256 (audit_events) + verificador 03:00 + DPO + Art. 18 + access_log middleware | `audit_events`, `hash_chain_checkpoint`, `lgpd_solicitacoes`, `lgpd_purge_log`, `access_log` | T6-01 a T6-15 |
| **S7** | M7-M8 BI + Hardening | 16–29/11 | 26–28/10 (apenas BI mínimo) | ECharts (4 dashboards) + slowapi + CSRF + partição mensal de `lousa_*` | (read agregado) + partições | T7-01 a T7-08 |

## Decisões macro vinculadas a sprints

- **D1 (TPA senha vs OTP)** — afeta Sprint 3 (PWA login) → confirma em K-2
- **D4 (turno intermediário)** — afeta Sprint 1 (seed turnos) → confirma em K-3
- **D5 (10 fainas + 26 funções)** — afeta Sprint 1 (seed catálogos) → confirma em K-3
- **D6 (normalização lousa_cells)** — afeta Sprint 7 (partição) → confirma em Sprint 4
- **D8/D9 (hash chain + histórico)** — afeta Sprint 5/6 → confirma em Sprint 5

## Riscos por sprint

| Sprint | Risco #1 | Mitigação |
|---|---|---|
| S2 | TPA Tecnologia muda layout (R2) | `layout_fingerprints` + alerta < 5 min (T2-03) |
| S3 | LGPD sem parecer do advogado (R3) | Termo v1 com revisão interna; parecer formal em S5 |
| S5 | OGMO/PE boicota integração (R1) | E-mail unilateral funciona sem aprovação; MPT como aliado |
| S6 | MPT interpreta como invasão | Trigger append-only + access_log + termo formal |
