# SINDESTIVA-PE · Diagnóstico Funcional & Plano de Melhorias

**Data:** 07/09/2026 · **Versão:** 1.0 · **Branch:** main @ `fe23ab1`
**Método:** Inspeção de código + testes vivos contra produção (Vercel + Render)
**Status geral:** 🟡 Sistema em **Sprint 0/1 entregues mas ainda não utilizável pelo usuário final**

---

## TL;DR

| Camada | Status | Bloqueia uso? |
|---|---|---|
| API (Render) | 🟢 Viva, 60+ endpoints, OpenAPI/Swagger OK | Não |
| Schema do banco | 🟢 Migrado, 3 versions Alembic | Não |
| Seeds | 🔴 **Nunca rodaram em prod** — 0 usuários, 0 TPAs | **SIM** |
| Scraping TPA/Suape | 🟢 OK (113 células hoje) | Não |
| Scraping EscalaNet/Recife | 🔴 **100% falha** — DNS `escalanet.recife.gov.br` não resolve | **SIM** (perde Recife) |
| Lousa preview | 🟡 Renderiza 94 células mas **0 TPAs vinculados** | **SIM** |
| Centro de Comando (web) | 🟡 Páginas existem, sem login, usa MOCK quando API "vazia" | **SIM** |
| PWA do TPA | 🔴 **É stub** — 1 página só, sem rotas, sem auth, sem SW/manifest | **SIM** |
| Autenticação (NextAuth) | 🔴 Dependência instalada, **nunca integrada** | **SIM** |
| Domínios custom `*.lousa.pscode.ia.br` | 🔴 Não provisionados (DNS não resolve) | Cosmético |
| CI | 🟢 Configurado (lint + typecheck + pytest + ruff) | Não |

**Veredito:** backend está sólido (8 sprints implementados, 60+ endpoints). O que falta para o sistema virar utilizável é: **(1) rodar seeds em prod**, **(2) resolver EscalaNet**, **(3) terminar o PWA** (login + 4 abas + SW + manifest), **(4) colocar NextAuth no WEB e gate de rotas**.

---

## 1. Estado dos deployments

### 1.1 URLs reais (verificadas em 07/09/2026 às 10:56 UTC)

| Serviço | URL | HTTP | Observação |
|---|---|---|---|
| API | `https://sindestiva-api.onrender.com` | 200 | OK, `/docs` Swagger ativo |
| Web | `https://sindestiva-web.vercel.app` | 200 | OK, 7 rotas carregam |
| PWA | `https://sindestiva-pwa.vercel.app` | 200 | OK mas só renderiza 1 página demo |
| Docs Swagger | `https://sindestiva-api.onrender.com/docs` | 200 | OpenAPI 60+ schemas |
| Docs ReDoc | `https://sindestiva-api.onrender.com/redoc` | (provavelmente 200) | — |

### 1.2 URLs antigas/erradas no AGENTS.md

| URL antiga | HTTP |
|---|---|
| `https://lousa-sindestiva.vercel.app` | 404 |
| `https://lousa-tpa.vercel.app` | 404 |
| `https://lousa-sindestiva-api.vercel.app` | 404 |
| `https://{web,pwa,api}.lousa.pscode.ia.br` | DNS NXDOMAIN |

> **Recomendação:** atualizar `AGENTS.md` e `DEPLOY.md` com as URLs reais e remover as antigas.

### 1.3 Estrutura física

```
apps/web/src/app/     7 páginas + 4 componentes compartilhados + 3 sub-componentes
apps/pwa/src/app/     1 página (page.tsx) + layout — SEM rotas filhas
apps/api/app/         ~30 módulos Python (api/v1/{auth,users,remanejamentos,
                      ogmo,lousa_public,scraping,lgpd,auditoria,dpo,bi,health,lousa})
```

---

## 2. Banco de dados

### 2.1 Migrations Alembic aplicadas

```
0001_initial_lousa_main.py
0002_lousa_escala_origem.py
0003_lousa_alocacao.py
```

### 2.2 O que está populado (verificado via `/api/v1/scraping/status`)

| Tabela | Conteúdo |
|---|---|
| `portos`, `turnos`, `funcoes`, `fainas` | ✅ Catálogo seedado (4 portos, 7 fainas, 24 funções) |
| `lousa_snapshot` | ✅ 12 snapshots hoje (6 TPA × 2 turnos + tentativas ESCALANET) |
| `lousa_cells` | ✅ 94–113 cells/dia capturadas do TPA |
| `tpas` (TPAs) | ❌ **0 registros** |
| `users` (operadores) | ❌ **0 registros** (Paulo/Manoel/Josias semeados não autenticam) |
| `remanejamentos` | ❌ **0** |
| `audit_events` | ❌ **0** (hash chain não iniciada) |
| `ogmo_notificacoes` | ❌ **0** |
| `lgpd_*` | ❌ **0** |

### 2.3 Seed nunca rodou em prod

Tentativa de login com as 3 contas seed (Paulo/Manoel/Josias) → todas retornam `INVALID_CREDENTIALS`.

Conclusão: o `entrypoint.sh` faz `Base.metadata.create_all` (DDL) mas **não roda os seeds**. Eles existem como scripts Python em `apps/api/scripts/seed_*.py`, mas só rodam manualmente.

---

## 3. API — análise de endpoints

### 3.1 Endpoints públicos (sem auth) — funciona ✅

| Endpoint | Resultado |
|---|---|
| `GET /health` | 200 `{status:"ok"}` |
| `GET /` | 200 metadata |
| `GET /api/v1/health` | 200 `{db:"ok"}` |
| `GET /docs` (Swagger) | 200 |
| `GET /openapi.json` | 200 (60+ paths) |
| `GET /api/v1/lousa/public/preview` | 200, retorna 94 cells (mas `tpa_id: null`) |
| `GET /api/v1/lgpd/termo-consentimento/texto` | 200, v1.0 |
| `GET /api/v1/lousa/public/tpa/{matricula}/escala` | **404 TPA não encontrado** (todas as matrículas testadas) |
| `POST /api/v1/auth/login` (creds errados) | 401 `INVALID_CREDENTIALS` ✅ |
| `POST /api/v1/auth/login` (creds seed) | 401 `INVALID_CREDENTIALS` ❌ seeds não rodaram |
| `GET /api/v1/scraping/status` | 200 (12 itens, 6 TPA ok, 6 ESCALANET falhando) |

### 3.2 Endpoints protegidos (com auth) — gate OK ✅

Testados sem token, todos retornam 401 `AUTH_REQUIRED` corretamente:
- `/api/v1/remanejamentos` ✅
- `/api/v1/auditoria/eventos` ✅
- `/api/v1/bi/kpis` ✅
- `/api/v1/dpo/*` ✅

> Boa notícia: o middleware de auth está sólido.

### 3.3 Inconsistência encontrada

- `POST /api/v1/auth/login` retorna `{"detail":{"code":"INVALID_CREDENTIALS"...}}` (RFC 7807-style)
- `GET /api/v1/remanejamentos` retorna `{"detail":"Autenticação obrigatória."}` (string simples)

**Dois formatos de erro** circulando. Recomendação: padronizar tudo no formato estruturado (`{code, message}`).

### 3.4 Bug crítico: matcher TPA↔célula

`/api/v1/lousa/public/preview` retorna:

```json
{"id":"f4035e66...", "faina_id":"...", "funcao_id":"...", "tpa_id":null,
 "tpa_nome":null, "tpa_matricula":"162", "status":"NORMAL"}
```

- 94/94 cells com `tpa_matricula` (ex: `"162"`, `"100"`, `"208"`) capturadas pelo scraper
- 0/94 com `tpa_id` (porque `tpas` está vazio)
- `stats.total_tpas_escalados: 0`

**Impacto:** WEB centro-comando mostra nomes "?" em vez de nomes reais, PWA `/tpa/{X}/escala` sempre 404.

---

## 4. Scraping — análise

### 4.1 TPA/Suape ✅ (94–113 cells/dia)

- Endpoint: `http://tpa.ogmosuape.com.br`
- Status atual: 6/6 SUCCESS, 1.6s médio
- Layout fingerprint: estável

### 4.2 EscalaNet/Recife 🔴 100% falha

- Endpoint configurado: `http://escalanet.recife.gov.br` (de `apps/api/app/scrapers/escalanet.py`)
- Erro em 100% das tentativas: `HTTP error: [Errno -2] Name or service not known`
- **Confirmado:** `curl https://escalanet.recife.gov.br` localmente também falha com `Could not resolve host`
- **Diagnóstico:** o domínio não existe mais ou foi descontinuado. Recife pode ter migrado para outro sistema.

### 4.3 Scheduler

- APScheduler `AsyncIOScheduler` dentro do processo FastAPI (não há worker dedicado rodando)
- Cron configurado em `apps/api/app/jobs/scheduler.py`
- **Risco:** se o Render hibernar o web service, o scraping para. Mitigação prevista no plano: worker separado `sindestiva-scraper` (Sprint 2), mas **não está deployed em Render ainda** (não vi serviço correspondente no painel).

---

## 5. WEB (Centro de Comando) — análise

### 5.1 Rotas implementadas (todas 200)

| Rota | Página | Implementa? |
|---|---|---|
| `/` | redirect → `/centro-comando` | ✅ |
| `/centro-comando` | Lousa Espelhada (T1+T4) | ✅ com mock fallback |
| `/remanejamentos` | Lista | ✅ |
| `/remanejamentos/novo` | Criar | ✅ |
| `/ogmo` | Notificações OGMO | ✅ |
| `/auditoria` | Eventos | ✅ |
| `/bi` | BI + ECharts + PDF | ✅ |
| `/tpa` | Mini PWA embarcada | ✅ |
| `/login` | **404 — não existe** | ❌ |

### 5.2 Autenticação ausente

- `apps/web/src/lib/api.ts` linha 9: `TODO Sprint 1: trocar localStorage por sessão NextAuth + httpOnly cookie`
- `apps/web/src/lib/mock.ts` linha 333: `mock — Sprint 1 implementa NextAuth`
- `next-auth` está em `dependencies` mas **não foi integrado**
- JWT fica em `localStorage` (vulnerável a XSS)

### 5.3 Uso pesado de mocks

`apps/web/src/lib/api.ts` usa `MOCK_*` para quase tudo: remanejamentos, OGMO, auditoria, sessão. Quando a API retorna vazio (estado atual), o front mostra mocks. Resultado: **a UI funciona mas não reflete a realidade** (mostra remanejamentos fictícios).

### 5.4 Bug visual: Lousa

Como `tpa_id` é sempre null (sem TPAs no banco), o componente `LousaTable.tsx` mostra `?` em todas as células — usuário não vê quem está escalado.

---

## 6. PWA do TPA — análise (mais crítica)

### 6.1 Estrutura real (decepcionante)

```
apps/pwa/src/app/
├── layout.tsx       (1)
└── page.tsx         (1) — 174 linhas, demo selector hardcoded
```

**Não há:** `inicio/page.tsx`, `escala/page.tsx`, `historico/page.tsx`, `perfil/page.tsx`, `login/page.tsx`, `manifest.ts`, `service-worker`, `icon-192.png`, `icon-512.png`.

### 6.2 O que a única página faz

`page.tsx` (Sprint 0):
- Selector dropdown com 5 matrículas **hardcoded**: `0000000000`, `OG-0036`, `OG-101D`, `OG-177B`, `OG-31C9`
- **Nenhuma delas existe no banco** (todas retornam 404 da API)
- 4 botões de "bottom nav" sem destino (Início/Escala/Histórico/Perfil)
- Botão "✓ Confirmar Presença" sem `onClick`
- Botão "💬 Falar com o Fiscal" linka `links.fiscal_whatsapp` (placeholder)
- Mostra dados zerados (engajamentos 0, R$ 0,00)

### 6.3 Não é uma PWA de verdade

| Item PWA | Status |
|---|---|
| `manifest.json` | 🔴 404 — não existe nem em `public/` nem em `app/manifest.ts` (mas HTML referencia `/manifest.json`) |
| `sw.js` (service worker) | 🔴 404 — next-pwa configurado mas `public/` não foi gerado |
| `/icon-192.png`, `/icon-512.png` | 🔴 404 |
| Lighthouse PWA score | ❌ Não instalável |

### 6.4 Inconsistência de identidade

- API chamada: `${apiUrl}/api/v1/lousa/public/tpa/${matricula}/escala` ✅
- Mas matrículas hardcoded não batem com a realidade (formato correto seria `TPA-001` etc., seed)

---

## 7. Pendências priorizadas (por impacto)

### P0 · Bloqueiam uso real

| # | Pendência | Impacto | Esforço |
|---|---|---|---|
| P0.1 | **Rodar seeds em prod** (users + TPAs + catalogos) | Tudo que depende de login/TPA falha | 1h (Shell do Render + 1 comando) |
| P0.2 | **EscalaNet morto** — descobrir endpoint real do Recife ou desligar feature | Scraping Recife 100% falha, masquerada como "rodando" | 4h (pesquisa + ajuste) |
| P0.3 | **PWA é stub** — implementar 4 abas (Início/Escala/Histórico/Perfil) + login CPF+matrícula+OTP | TPA não consegue usar o app | 2 sprints (T3-01 a T3-12) |
| P0.4 | **Auth WEB** — integrar NextAuth + gate de rotas por RBAC | Sem login, tudo exposto | 1 sprint (T1-08, T1-09, T1-10) |
| P0.5 | **PWA manifest + SW + ícones** | PWA não instalável, "Add to Home Screen" não funciona | 1 dia |

### P1 · Melhoram confiabilidade

| # | Pendência | Impacto | Esforço |
|---|---|---|---|
| P1.1 | Padronizar formato de erro da API (`{code, message}` em todos) | UX de erro inconsistente | 4h |
| P1.2 | Separar worker de scraping (sindestiva-scraper no Render) | Scraping para quando web hiberna | 1 sprint |
| P1.3 | Remover `MOCK_*` fallbacks do WEB | Mostra dados fictícios em prod | 1 sprint (T1-11) |
| P1.4 | Trocar JWT em `localStorage` por cookie httpOnly | Vulnerável a XSS | junto com P0.4 |
| P1.5 | Provisionar domínios `*.lousa.pscode.ia.br` (DNS + cert) | URLs customizadas quebradas | 2h |
| P1.6 | Atualizar `AGENTS.md` e `DEPLOY.md` com URLs reais | Documentação desatualizada | 30min |

### P2 · Polimento

| # | Pendência |
|---|---|
| P2.1 | Testes E2E (Playwright) — não existem ainda |
| P2.2 | Testes de unidade no WEB/PWA — 0 arquivos .test.ts |
| P2.3 | Screenshots do sistema em produção |
| P2.4 | Alertas Discord/email quando scraping falha (Sprint 2 T2-12) |
| P2.5 | Dashboard DPO com checkpoint de hash chain |
| P2.6 | Migrar de `Base.metadata.create_all` para Alembic dedicado (já tem 3 versions) |
| P2.7 | Variáveis `OGMO_EMAIL`, `RESEND_API_KEY` parecem vazias — e-mail OGMO não sai |

---

## 8. Plano de implementação — 4 sprints (~6 semanas)

### Sprint A · Desbloqueio operacional (1 semana)

**Objetivo:** sistema usável por Paulo/Manoel/Josias em modo leitura + remanejamento manual.

1. **A.1** Rodar seeds em prod
   - `python apps/api/scripts/seed_catalogos.py`
   - `python apps/api/scripts/seed_tpas_demo.py`
   - `python apps/api/scripts/seed_users.py`
   - Validar: 3 users autenticam + 2 TPAs visíveis no PWA
2. **A.2** Investigar EscalaNet — ligar para OGMO Recife, descobrir endpoint atual
3. **A.3** Atualizar AGENTS.md e DEPLOY.md com URLs reais
4. **A.4** Provisionar `*.lousa.pscode.ia.br` (DNS + Vercel + Render)

### Sprint B · Autenticação (1 semana)

**Objetivo:** WEB e PWA com login real, RBAC respeitado, sessão segura.

1. **B.1** NextAuth v5 no WEB (Credentials + JWT 8h)
2. **B.2** Gate de rotas (`/centro-comando`, `/bi`, `/ogmo` por role)
3. **B.3** Remover `MOCK_*` do `api.ts` (sempre usa API)
4. **B.4** Login TPA: CPF + matrícula OGMO + OTP WhatsApp (Evolution API)
5. **B.5** Página `/login` (WEB) e `/login` (PWA)
6. **B.6** Padronizar erros API

### Sprint C · PWA completo (2 semanas)

**Objetivo:** TPA consegue ver escala do dia, confirmar presença, ver histórico, gerenciar perfil LGPD.

1. **C.1** 4 rotas: `/inicio`, `/escala`, `/historico`, `/perfil`
2. **C.2** Bottom nav funcional + layout mobile-first real
3. **C.3** Manifest (`app/manifest.ts`) + ícones 192/512/maskable
4. **C.4** Service Worker via Workbox (cache offline + push)
5. **C.5** IndexedDB para offline-first (idb instalado)
6. **C.6** Confirmar Presença → POST real com hash integridade
7. **C.7** Modal termo de consentimento LGPD no primeiro login
8. **C.8** Perfil: edição telefone, exportar dados (Art. 18 V), pedir exclusão (Art. 18 VI)

### Sprint D · Robustez (2 semanas)

**Objetivo:** sistema pronto pra piloto Manoel Costa em Suape.

1. **D.1** Worker scraping dedicado (sindestiva-scraper no Render)
2. **D.2** Alertas scraping falha (Discord/WhatsApp)
3. **D.3** Hash chain verifier job em produção (Sprint 6 T6-03)
4. **D.4** LGPD purge job em produção (Sprint 6 T6-06)
5. **D.5** Notificação OGMO por e-mail (Resend) — variável RESEND_API_KEY precisa ser preenchida
6. **D.6** Migração Alembic dedicada (substituir `create_all`)
7. **D.7** Playwright E2E (5 fluxos críticos)
8. **D.8** Documentação: manual do fiscal, manual do TPA

---

## 9. Recomendações imediatas (próximas 24h)

| Ação | Quem | Tempo |
|---|---|---|
| Rodar `seed_users.py` + `seed_catalogos.py` + `seed_tpas_demo.py` no Shell do Render | Paulo | 30min |
| Confirmar com Manoel Costa se `escalanet.recife.gov.br` ainda existe ou se mudou | Paulo | 1 call |
| Preencher `RESEND_API_KEY` no `.env` do Render (e-mail OGMO) | Paulo | 15min |
| Atualizar `AGENTS.md` com URLs reais | Eu | 10min |
| Implementar **A.1** (seeds) + **A.3** (docs) antes da próxima demo | Eu | 1h |

---

## 10. Métricas de qualidade atuais

| Métrica | Valor | Meta MVP |
|---|---|---|
| Endpoints API | 60+ | ✅ |
| Endpoints testados em prod | 15/60 | 60/60 |
| Cobertura de testes backend | n/a (não medido) | ≥ 80% |
| Cobertura de testes WEB/PWA | 0% | ≥ 60% |
| Páginas WEB | 8 | 5 (atingido) |
| Páginas PWA | 1 | 4 (faltam 3) |
| TS errors (web/pwa) | 0 | 0 ✅ |
| Ruff (api) | clean | clean ✅ |
| Hash chain rodando | ❌ inativo | ✅ diário 03h |
| LGPD purge rodando | ❌ inativo | ✅ diário 04h |
| Uptime scraping TPA | 100% (hoje) | ≥ 95% |
| Uptime scraping EscalaNet | 0% | ≥ 95% |

---

## 11. Riscos abertos (top 5)

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| EscalaNet morreu e não temos alternativa p/ Recife | Alta | Alto | Validar com OGMO esta semana |
| Seeds não idempotentes podem dar erro ao rodar | Média | Médio | Testar em staging primeiro |
| PWA é a face visível p/ 2.000 TPAs — stub atual passa vergonha | Alta | Alto (reputação) | Sprint C é prioritário |
| Web service Render hiberna → scraping para | Média | Médio | Sprint D.1 (worker dedicado) |
| RESEND_API_KEY vazio → OGMO não recebe e-mail | Alta | Crítico | Provisionar antes do piloto |

---

## 12. Anexo: comandos úteis

```bash
# Rodar seeds em prod (via Render Shell)
python apps/api/scripts/seed_catalogos.py
python apps/api/scripts/seed_users.py
python apps/api/scripts/seed_tpas_demo.py

# Verificar saúde da API
curl https://sindestiva-api.onrender.com/api/v1/health

# Forçar scrape manual
curl -X POST https://sindestiva-api.onrender.com/api/v1/scraping/disparar \
  -H "Content-Type: application/json" \
  -d '{"fonte":"TPA","porto":"SUAPE","turno":"DIURNO"}'

# Validar hash chain
curl -X POST https://sindestiva-api.onrender.com/api/v1/auditoria/verificar-hash-chain \
  -H "Authorization: Bearer <JWT>"
```

---

**Próximo passo recomendado:** executar Sprint A.1 + A.3 ainda hoje, agendar 1h com Manoel Costa para validar Recife (A.2), e começar Sprint B (autenticação) na segunda-feira.
