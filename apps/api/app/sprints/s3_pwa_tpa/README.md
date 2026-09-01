# Sprint 3 — PWA TPA + LGPD (28/09-04/10/2026)

## Marco: M2 Demo executiva (05/10) — sistema completo

### Entregáveis
- Setup PWA (manifest + service worker + IndexedDB offline)
- Login TPA (CPF + matrícula + OTP WhatsApp)
- Telas: Início (escala do dia), Escala (7 dias), Histórico, Perfil
- Botão "Confirmar Presença" / "Não vou"
- Push FCM
- Termo LGPD v1 no fluxo de primeiro login

### Tabelas tocadas
- `users` (login via telefone + OTP)
- `tpas` (matrícula_ogmo como chave de match)
- `tpa_confirmacoes_presenca` (insert por confirmação)
- `termos_consentimento` (insert no aceite)

### Tarefas
- T3-01: setup PWA
- T3-02: tela login
- T3-03: tela Início
- T3-04: tela Escala
- T3-05: tela Histórico
- T3-06: tela Perfil
- T3-07: botão confirmar presença
- T3-08: deep link WhatsApp Fiscal
- T3-09: push FCM

### Decisões abertas a sinalizar

- **D1** (TPA password vs OTP): Sprint 3 valida o fluxo. Se confirmar
  (a) só OTP, manter constraint. Se (b) opcional, remover.

### Risco #1 do sprint
**R3 — MPT interpreta como invasão**. Mitigação: termo formal com
advogado + aceite registrado em `termos_consentimento` (append-only).
