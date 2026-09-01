# SINDESTIVA-PE · Cronograma Gerencial — 45 dias

> **Cliente:** SINDESTIVA-PE (Sindicato dos Estivadores nos Portos de Pernambuco)
> **Fornecedor:** Suporte Gerencial
> **Sponsor cliente:** Josias Martins Santiago (Presidente)
> **Sponsor técnico:** Paulo Siqueira (Suporte Gerencial)
> **Produto:** Lousa Digital
> **Documento:** Cronograma executivo (resumo do plano de implementação v1.0)
> **Data:** 01/09/2026

---

## 1. Visão consolidada (1 página)

| Item | Valor |
|---|---|
| **Duração** | **45 dias corridos** (~32 dias úteis, ~6,4 semanas) |
| **Início** | **14/09/2026** (segunda-feira) |
| **Término** | **28/10/2026** (terça-feira) |
| **Marco intermediário (D+21)** | 05/10/2026 — Demo executiva pra Josias |
| **Go-Live (D+45)** | 28/10/2026 — Piloto com 1 fiscal em Suape |
| **Dedicação Paulo** | **100% (~40h/sem)** durante os 45 dias |
| **Horas totais** | **~256h** (32 dias × 8h) |
| **Investimento cash** | **R$ 2.800** (infra 45d + jurídico + viagem) |

---

## 2. Premissas do cronograma de 45 dias

Pra caber em 45 dias, **3 premissas mudam em relação ao plano original de 18 semanas**:

1. **Dedicação 100% do Paulo** (não 50-60%). Durante 45 dias, Becker/Córtex/Sinapse/FaceGate ficam em modo manutenção.
2. **Escopo reduzido** em ~40% — algumas features vão pra Fase 2 (ver seção 7).
3. **Paralelismo agressivo** — 2-3 desenvolvedores trabalhando em paralelo (Paulo + 1 estagiário/bolsista) onde for possível.
4. **Homologação curta** — 1 fiscal-piloto (Manoel Costa) usando por 3 dias consecutivos ao final, não 2 semanas.
5. **Sem hardening pesado** — segurança básica + backup, sem load test exaustivo. Endurecimento vai pra Fase 2.

> **Risco assumido:** MVP em 45 dias é apertado. Se algo estourar (TPA muda layout, Manoel ausente, problema de saúde do Paulo), o prazo pode escorregar 1-2 semanas. **Marcos intermediários (D+7, D+21, D+35)** funcionam como gatilhos de Go/No-Go.

---

## 3. Marcos (milestones) com datas fixas

| Marco | Data | Dias | Entregável | Validador |
|---|---|---|---|---|
| **M0** | 18/09/2026 (sex) | D+4 | Kickoff, CCT obtida, advogado contratado, infra pronta | Josias + Paulo |
| **M1** | 25/09/2026 (sex) | D+11 | **Demo 1 — Centro de Comando com Lousa oficial de Suape espelhada** | Manoel Costa |
| **M2** | 05/10/2026 (seg) | D+21 | **Demo executiva — Sistema completo (Lousa + Remanejamento + PWA + Auditoria)** | **Josias + Diretoria** |
| **M3** | 19/10/2026 (seg) | D+35 | **Homologação — Manoel opera 100% por 3 dias consecutivos** | Manoel |
| **M4** | **28/10/2026 (ter)** | **D+45** | **GO-LIVE — Sistema em produção, Manoel operando, OGMO notificado** | **Josias (assinatura)** |

**Gatilhos Go/No-Go:**
- **D+11 (M1):** se lousa não estiver espelhada com dados reais → reavaliar escopo
- **D+21 (M2):** se remanejamento + PWA não estiverem funcionando → esticar 15 dias (D+60)
- **D+35 (M3):** se Manoel não estiver homologando → esticar 10 dias (D+55)

---

## 4. Visão Gantt (7 sprints semanais)

```
       Set/2026                  Out/2026
       S  T  Q  Q  S  S  D | S  T  Q  Q  S  S  D | S  T  Q  Q  S  S  D | S  T  Q  Q  S  S  D
       14 15 16 17 18 19 20 | 21 22 23 24 25 26 27 | 28 29 30 01 02 03 04 | 05 06 07 08 09 10 11 | 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28
       ├─ S1 FOUNDATION ─┤ | ├─ S2 SCRAPER ────┤ | ├─ S3 CORE FEATURES ─────────┤ | ├─ S4 PWA TPA ──────────────┤
KICK   ██                       |                    |                                        |
CCT    ████                     |                    |                                        |
ADVOG  ████                     |                    |                                        |
REPO   ████                     |                    |                                        |
AUTH   ──────██████████         |                    |                                        |
SCRAP  ──────────────────────████████████           |                                        |
LOUSA  ─────────────────────────────────────────████ |                                        |
REMAN  ─────────────────────────────────────────────────████                                  |
OGMO N ─────────────────────────────────────────────────────████                                |
PWA    ─────────────────────────────────────────────────────────────────████████████           |
AUDIT  ──────────────────────────────────────────────────────────────────────────────████       |
BI MIN ───────────────────────────────────────────────────────────────────────────────────████  |
HOMO   ───────────────────────────────────────────────────────────────────────────────────────████
GO-LV  ─────────────────────────────────────────────────────────────────────────────────────────██
                                                                                                |
                                                                                                D+45
                                                                                                GO-LIVE
```

---

## 5. Detalhamento por sprint

### **Sprint 1 — Fundação (14-20/09/2026) · 5 dias úteis · 40h**

**Objetivo:** terreno preparado, time alinhado, base técnica no ar.

| # | Atividade | Horas | Status |
|---|---|---|---|
| S1-01 | Reunião de kickoff com Josias + Manoel (2h, presencial) | 2h | ⏳ |
| S1-02 | Obter CCT 2024-2026 vigente | 1h | ⏳ |
| S1-03 | Contratar advogado trabalhista (parecer LGPD, 1ª versão) | 2h | ⏳ |
| S1-04 | Configurar repo `contatopscode/lousa-sindestiva` (Turborepo + CI) | 4h | ⏳ |
| S1-05 | Provisionar VPS Hetzner + domínio `lousa.pscode.ia.br` | 4h | ⏳ |
| S1-06 | Setup Docker Compose (Postgres 17 + Redis 7 + Traefik) | 4h | ⏳ |
| S1-07 | Modelagem do schema Postgres (User, Role, LousaSnapshot, Remanejamento, AuditEvent) | 6h | ⏳ |
| S1-08 | Auth (NextAuth v5 + JWT 8h + 3 roles: Fiscal, Dirigente, TPA) | 8h | ⏳ |
| S1-09 | Página de login estilizada (réplica do protótipo) | 4h | ⏳ |
| S1-10 | Termo de consentimento LGPD (versão 1, no fluxo de login) | 3h | ⏳ |
| S1-11 | Carta formal ao OGMO/PE (modelo + AR digitalizado) | 2h | ⏳ |

**Entregável M0 (sex 18/09):** time alinhado, infra no ar, auth funcional, advog contratado.

---

### **Sprint 2 — Scraping TPA (21-27/09/2026) · 5 dias úteis · 40h**

**Objetivo:** lousa oficial do OGMO/PE fluindo para o banco em tempo real.

| # | Atividade | Horas | Status |
|---|---|---|---|
| S2-01 | Scraper TPA/Suape (Playwright headless, parser tolerante 3 níveis) | 12h | ⏳ |
| S2-02 | Cron de scraping a cada 60s (durante operação 06h-22h) | 4h | ⏳ |
| S2-03 | Alerta de mudança de layout (hash HTML + e-mail/WhatsApp) | 3h | ⏳ |
| S2-04 | Scraper EscalaNet/Recife (HTTPX, PHP simples) | 6h | ⏳ |
| S2-05 | Matcher de TPAs (cruzar matrículas OGMO × cadastro Sindicato) | 4h | ⏳ |
| S2-06 | Endpoint `GET /api/lousa?porto=X&turno=Y` | 2h | ⏳ |
| S2-07 | Endpoint `GET /api/lousa/listagem?data=...&turno=...` | 2h | ⏳ |
| S2-08 | Testes de scraping (fixture HTML congelada, 10+ casos) | 4h | ⏳ |
| S2-09 | Front: Lousa espelhada (matriz 26×11, alternador porto/turno) | 3h | ⏳ |

**Entregável M1 (sex 25/09):** Lousa oficial de Suape aparecendo no Centro de Comando, atualizada a cada 60s. **Manoel valida ao vivo.**

---

### **Sprint 3 — Core: Lousa + Remanejamento + Notificação OGMO (28/09-04/10/2026) · 5 dias úteis · 44h**

**Objetivo:** ciclo completo Fiscal → Sistema → OGMO funcionando.

| # | Atividade | Horas | Status |
|---|---|---|---|
| S3-01 | KPIs operacionais (4 cards: TPAs escalados, presença, remanejamentos, sync) | 4h | ⏳ |
| S3-02 | Fila "Notificação OGMO" lateral (PEND/SENT/ACK/NACK) | 4h | ⏳ |
| S3-03 | Modal de remanejamento (8 motivos, base legal CCT, anexo) | 6h | ⏳ |
| S3-04 | Endpoint `POST /api/remanejamentos` (criar, validar, gravar) | 4h | ⏳ |
| S3-05 | Hash chain no momento da criação (SHA-256, append-only) | 3h | ⏳ |
| S3-06 | Worker de e-mail (Resend) — template HTML + PDF anexado | 6h | ⏳ |
| S3-07 | Geração de PDF (WeasyPrint) com hash visível no rodapé | 4h | ⏳ |
| S3-08 | Webhook preparado (HMAC-SHA256) com payload JSON | 3h | ⏳ |
| S3-09 | Tela de Remanejamentos (histórico + 4 KPIs) | 4h | ⏳ |
| S3-10 | WebSocket: push de novos snapshots em < 2s | 4h | ⏳ |
| S3-11 | Testes E2E Playwright (fluxo: login → lousa → clique → remanejamento → e-mail) | 2h | ⏳ |

**Entregável intermediário (seg 05/10):** tudo de M2 funcionando para a **demo executiva com Josias**.

---

### **Sprint 4 — PWA do TPA (05-11/10/2026) · 5 dias úteis · 40h**

**Objetivo:** TPA vê escala no celular, confirma presença, fala com Fiscal.

| # | Atividade | Horas | Status |
|---|---|---|---|
| S4-01 | Setup PWA (manifest + service worker + IndexedDB offline) | 3h | ⏳ |
| S4-02 | Tela de login (CPF + matrícula, OTP WhatsApp) | 4h | ⏳ |
| S4-03 | Tela "Início" (escala do dia, função, cais, navio) | 4h | ⏳ |
| S4-04 | Tela "Escala" (próximos 7 dias, filtragem por turno) | 3h | ⏳ |
| S4-05 | Tela "Histórico" (últimos 12 meses) | 3h | ⏳ |
| S4-06 | Tela "Perfil" (dados + botão excluir dados — Art. 18 LGPD) | 3h | ⏳ |
| S4-07 | Botão "Confirmar Presença" / "Não vou" | 3h | ⏳ |
| S4-08 | Deep link WhatsApp do Fiscal | 2h | ⏳ |
| S4-09 | Push FCM (registro de token no login) | 4h | ⏳ |
| S4-10 | CCT em PDF dentro do app | 2h | ⏳ |
| S4-11 | Teste com 5 TPAs-piloto + Lighthouse PWA score > 90 | 4h | ⏳ |
| S4-12 | Testes E2E Playwright | 5h | ⏳ |

**Entregável:** PWA instalável, testado com 5 TPAs-piloto reais.

---

### **Sprint 5 — Auditoria + LGPD + BI mínimo (12-18/10/2026) · 5 dias úteis · 40h**

**Objetivo:** trilha de auditoria, LGPD compliance, BI mínimo.

| # | Atividade | Horas | Status |
|---|---|---|---|
| S5-01 | Tabela `audit_event` (trigger BEFORE UPDATE rejeita, mesmo padrão Sinapse) | 4h | ⏳ |
| S5-02 | Migração: trigger em `remanejamento`, `presenca`, `lousa_snapshot` | 3h | ⏳ |
| S5-03 | Hash chain SHA-256 (cada evento referencia o anterior) | 4h | ⏳ |
| S5-04 | Front: timeline de auditoria + verificador de integridade | 6h | ⏳ |
| S5-05 | Exportador PDF assinado + CSV | 4h | ⏳ |
| S5-06 | Endpoint `/api/lgpd/esquecer` (anonimiza TPA em 15 dias) | 3h | ⏳ |
| S5-07 | Verificador diário de hash chain (job 03h, alerta se quebrar) | 3h | ⏳ |
| S5-08 | BI mínimo: 4 KPIs (comparecimento, remanejamentos, ranking, gráfico 7d) | 6h | ⏳ |
| S5-09 | Tela de auditoria (export PDF/CSV, verificador) | 4h | ⏳ |
| S5-10 | Parecer jurídico final sobre LGPD (advogado) | 1h | ⏳ |
| S5-11 | Rate limit + Helmet + CORS | 2h | ⏳ |

**Entregável:** sistema compliance com LGPD, hash chain íntegro, BI mínimo.

---

### **Sprint 6 — Homologação + ajustes finais (19-25/10/2026) · 5 dias úteis · 36h**

**Objetivo:** Manoel opera 100% em 3 turnos reais, ajustes finais.

| # | Atividade | Horas | Status |
|---|---|---|---|
| S6-01 | Treinamento Manoel Costa (presencial em Suape, 2h) | 2h | ⏳ |
| S6-02 | Vídeo-aula de 3 min "Como usar a Lousa Digital" | 2h | ⏳ |
| S6-03 | Day 1: Manoel opera turno 08-16 com Paulo acompanhando | 8h | ⏳ |
| S6-04 | Day 2: Manoel opera turno 08-16 sozinho, Paulo on-call | 4h | ⏳ |
| S6-05 | Day 3: Manoel opera turno 08-16 sozinho | 2h | ⏳ |
| S6-06 | Daily 15min com Manoel (issues) | 3h | ⏳ |
| S6-07 | Triagem e fix de bugs P0/P1 | 8h | ⏳ |
| S6-08 | Coleta de feedback qualitativo (NPS, 1:1) | 1h | ⏳ |
| S6-09 | Ajustes finais de UX (cards reorganizados, atalhos) | 4h | ⏳ |
| S6-10 | Manual do Fiscal (1 PDF de 4 páginas) | 2h | ⏳ |

**Entregável M3 (seg 19/10 — começa na verdade no sábado 18 se Manoel preferir):** Manoel opera com confiança, NPS ≥ 7.

---

### **Sprint 7 — Go-Live (26-28/10/2026) · 3 dias úteis · 16h**

**Objetivo:** produção aberta, monitoramento 24/7, apresentação externa.

| # | Atividade | Horas | Status |
|---|---|---|---|
| S7-01 | Deploy final em produção + smoke tests | 4h | ⏳ |
| S7-02 | Backup completo + restore testado | 2h | ⏳ |
| S7-03 | Monitoramento 24/7 ativo (Uptime Kuma + Sentry) | 2h | ⏳ |
| S7-04 | Apresentação formal a Josias + diretoria (1h) | 2h | ⏳ |
| S7-05 | Carta formal ao OGMO/PE (AR digitalizado) | 2h | ⏳ |
| S7-06 | Retrospectiva + lições aprendidas + documento de entrega | 2h | ⏳ |
| S7-07 | Termo de aceite final assinado por Josias | 1h | ⏳ |
| S7-08 | Estabilização (Paulo on-call até 31/10) | 1h | ⏳ |

**Entregável M4 (ter 28/10):** **GO-LIVE** — Manoel operando em produção, Josias assina o termo de aceite.

---

## 6. Resumo de esforço

| Sprint | Foco | Horas | Marco |
|---|---|---|---|
| S1 (14-20/09) | Fundação + Kickoff | 40h | M0 |
| S2 (21-27/09) | Scraping TPA | 40h | M1 |
| S3 (28/09-04/10) | Lousa + Remanejamento + Notificação OGMO | 44h | (Demo executiva 05/10) |
| S4 (05-11/10) | PWA do TPA | 40h | — |
| S5 (12-18/10) | Auditoria + LGPD + BI mínimo | 40h | — |
| S6 (19-25/10) | Homologação com Manoel | 36h | M3 |
| S7 (26-28/10) | Go-Live | 16h | **M4 — GO-LIVE** |
| **TOTAL** | | **256h** | |

**Média:** ~40h/sem (dedicação integral do Paulo).

---

## 7. O que fica FORA do escopo de 45 dias (vai pra Fase 2 / 3)

| Feature | Justificativa | Fase |
|---|---|---|
| BI avançado (ML, predição de faltas, ECharts elaborados) | Substituído por 4 KPIs simples | Fase 2 |
| App nativo iOS/Android | PWA cobre 90% | Fase 2 (se PWA limitar) |
| SMS (fallback ao WhatsApp) | WhatsApp cobre 95% | Fase 2 |
| ICP-Brasil A1 nos e-mails | Hash SHA-256 já atende | Fase 2 |
| Multi-tenant B2B (outros OGMOs) | Após case validado | Fase 3 |
| API oficial OGMO ↔ Sindicato | Depende de acordo tripartite | Fase 3 (12-18 meses) |
| Load test exaustivo (k6, 50 VUs) | Validação manual basta no MVP | Fase 2 |
| Onboarding Recife (segundo porto) | MVP só Suape | Fase 2 |
| App do OGMO (read-only com token) | Painel do Fiscal já mostra tudo | Fase 2 |
| Campanha de instalação PWA em massa | Após validação com 5 TPAs-piloto | Fase 2 |
| DPO dashboard completo (Paulo acumula) | Funcional, não bonito | Fase 2 |
| Integração contábil/pagamento | Sistema paralelo | Fase 3 |
| Apresentação formal MPT-PE | Carta basta no MVP | Fase 2 |

---

## 8. Orçamento ajustado para 45 dias

| Item | Valor | Tipo |
|---|---|---|
| Infraestrutura VPS Hetzner (45 dias × R$ 250/mês) | R$ 375 | recorrente |
| Domínio `lousa.pscode.ia.br` | R$ 80 | one-shot |
| Resend (e-mail, free tier 3k/mês) | R$ 0 | recorrente |
| Firebase Cloud Messaging | R$ 0 | free tier |
| Advogado trabalhista (parecer LGPD) | R$ 1.500 | one-shot |
| Viagem Recife ↔ Suape (1 visita, 1 dia) | R$ 750 | one-shot |
| Material de treinamento | R$ 100 | one-shot |
| Mão de obra Paulo (256h) | (custo interno Suporte Gerencial) | não-billable |
| **TOTAL MVP (45 dias)** | **R$ 2.805** | — |

**Modelo recomendado (inalterado):** **Patrocínio** — Sindicato paga R$ 2.805 (infra + viagem + jurídico), Suporte Gerencial investe as 256h.

---

## 9. Riscos específicos do prazo de 45 dias

| # | Risco | P | I | Mitigação |
|---|---|---|---|---|
| R45-01 | TPA Tecnologia muda layout no meio do Sprint 2 | Média | Alto | Parser tolerante + alerta em < 5 min + modo degradado (caches últimos 7 dias) |
| R45-02 | Manoel Costa indisponível na semana de homologação | Média | Alto | Identificar fiscal-piloto #2 no Sprint 1 (K-3) |
| R45-03 | Paulo sobrecarregado (Becker/Córtex/Sinapse/FaceGate competem) | Alta | Alto | 45 dias de dedicação 100% exclusiva + aviso prévio aos outros projetos |
| R45-04 | OGMO/PE derruba o scraping (muda URL ou bloqueia IP) | Baixa | Alto | Scraper alternativo via listagem_turno (HTML mais simples) + retry distribuído |
| R45-05 | Advogado não entrega parecer a tempo | Baixa | Médio | Backup Nathalia Santos (contingência) + revisão interna do termo LGPD enquanto parecer não chega |
| R45-06 | MPT interpreta como invasão (antes de M10) | Baixa | Alto | Carta formal no M0 + scope restrito (replica, não escala) + reunião preventiva |
| R45-07 | Bug P0 não resolvido em 24h | Média | Alto | Paulo on-call 24/7 nos últimos 7 dias + rollback CI/CD |
| R45-08 | Performance ruim na homologação | Média | Médio | Load test manual com 10 usuários simultâneos no Sprint 5; cache Redis se preciso |

**Gatilhos de prazo:**
- D+11 (M1) sem lousa espelhada → reavaliar escopo
- D+21 (M2) sem remanejamento funcionando → esticar 15 dias (D+60)
- D+35 (M3) sem Manoel homologando → esticar 10 dias (D+55)
- D+45 sem go-live possível → esticar para D+60 e renegociar escopo

---

## 10. Comunicação durante os 45 dias

| Frequência | Canal | Audiência | Conteúdo |
|---|---|---|---|
| **Diária (15min)** | WhatsApp | Manoel + Paulo | Status rápido, bloqueios |
| **Semanal (sex 14h)** | Google Meet 30min | Paulo + Josias | Status executivo, próximos passos |
| **D+21 (05/10)** | Presencial ou Meet 1h | Josias + Manoel + Diretoria | **Demo executiva completa** |
| **D+35 (19/10)** | Presencial em Suape 2h | Manoel | Treinamento formal |
| **D+45 (28/10)** | Presencial 1h | Josias + Manoel + Diretoria | **GO-LIVE + assinatura do termo de aceite** |

---

## 11. KPIs de controle (a cada semana)

| KPI | Meta |
|---|---|
| **Sprint burndown** | ≥ 90% das atividades do sprint concluídas |
| **Bugs P0 abertos** | ≤ 2 (deve zerar antes do M3) |
| **Cobertura de testes** | ≥ 60% (mínimo viável em 45 dias) |
| **Uptime da staging** | ≥ 95% |
| **Latência lousa (carregamento)** | < 2s |
| **Latência scraping → DB** | < 5s |
| **Latência remanejamento → e-mail OGMO** | < 2 min |

---

## 12. Termo de aceite simplificado (para D+45)

```
TERMO DE ACEITE — MVP LOUSA DIGITAL SINDESTIVA-PE

Pelo presente, declaro que o sistema entregue em 28/10/2026 atende
ao escopo do MVP (Fase 1) definido no Plano de Implementação v1.0,
com os seguintes marcos concluídos:

  [✓] M0 — Kickoff e setup (18/09/2026)
  [✓] M1 — Lousa oficial espelhada (25/09/2026)
  [✓] M2 — Demo executiva com Josias (05/10/2026)
  [✓] M3 — Homologação Manoel Costa (19/10/2026)
  [✓] M4 — GO-LIVE (28/10/2026)

Aprovo a entrega e autorizo o início da operação no Porto de Suape.

Nome: Josias Martins Santiago
Cargo: Presidente SINDESTIVA-PE
Data: ___/___/2026
Assinatura: ____________________________
```

---

## Encerramento

Este documento é o **resumo executivo** do plano de implementação completo (`SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md`, 67KB) e está ajustado para a janela apertada de 45 dias.

**Próximos passos imediatos (a fazer AGORA):**

1. **Validar com Josias** se 45 dias é viável e aceitável
2. **Confirmar Manoel Costa** como fiscal-piloto (ou indicar substituto)
3. **Identificar advogado** (Cristiano/Nathalia) e contratar para Sprint 1
4. **Reservar agenda do Paulo** 100% entre 14/09 e 28/10 (Becker/Córtex/Sinapse/FaceGate em modo manutenção)
5. **Carta formal ao OGMO/PE** pronta no M0 (D+4)
6. **Aprovar este documento** para iniciar o kickoff

---

*Documento gerado por Mavis em 01/09/2026 · v1.0 · ajuste para prazo de 45 dias corridos.*
