# SINDESTIVA-PE · AGENTS.md

> Guia de contexto para IAs e humanos que vão trabalhar neste repo.
> Última atualização: 01/09/2026 · Modo privado (sem push pro GitHub).

---

## 1. O que é o SINDESTIVA-PE

O **SINDESTIVA-PE** é o Sindicato dos Estivadores nos Portos de Pernambuco. Hoje
a operação portuária em Recife e Suape é sustentada por **lousa física,
telefone e rádio** entre fiscais do Sindicato e o OGMO/PE — falhas de
comunicação custam horas-fiscais, geram passivo trabalhista e produzem
assimetria de informação entre OGMO, Sindicato e Trabalhador Portuário Avulso
(TPA).

Este repo contém a **Lousa Digital** (slug interno `lousa-sindestiva`):
plataforma web + PWA que **replica a lousa oficial do OGMO**, **digitaliza o
remanejamento operacional** com hash chain SHA-256, **notifica o OGMO** por
e-mail formal + PDF + webhook (preparado), e oferece um **PWA do TPA** para
escala do dia, confirmação de presença e canal direto com o Fiscal.

- **Patrocinador cliente:** Josias Martins Santiago (Presidente)
- **Sponsor técnico:** Paulo Siqueira (Diretor de Tecnologia e Operação · Suporte Gerencial)
- **Fiscal-piloto:** Manoel Costa (Suape)
- **Público-alvo:** ~2.000 TPAs + ~10 fiscais + diretoria

---

## 2. Stack

| Camada | Tecnologia | Por quê |
|---|---|---|
| Monorepo | **Turborepo + pnpm 10** | Mesmo padrão Becker/Córtex |
| Frontend Web | **Next.js 15 (App Router) + TS 5 + Tailwind 4** | SSR, server actions, reuso |
| PWA TPA | **Next.js 15 PWA + Workbox + IndexedDB** | Mobile-first, offline-first |
| Backend | **Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2** | Mesma stack Sinapse/FaceGate |
| Banco | **PostgreSQL 17** (schema `lousa_main`) | Schema único no MVP (ADR-002) |
| Cache/PubSub | **Redis 7** | WebSocket e filas leves |
| Scraping | **Playwright + BeautifulSoup + HTTPX** | Tolerância a mudança de layout |
| E-mail | **Resend** | 3k/mês free tier |
| PDF | **WeasyPrint** | Renderiza template HTML do e-mail |
| BI | **Apache ECharts** (frontend) + agregações SQL | Mesma lib do Sinapse |
| Auth | **NextAuth v5 + JWT 8h + Credentials + OTP WhatsApp** | Híbrido (mesmo padrão Córtex) |
| Push | **Firebase Cloud Messaging (FCM)** | Android; iOS via PWA push |
| WhatsApp | **Evolution API** | Mesmo padrão Becker/Córtex |
| Reverse proxy | **Traefik v3** | TLS automático em prod |
| CI/CD | **GitHub Actions + Easypanel + Hetzner CPX31** | Mesmo padrão Suporte Gerencial |
| LGPD | Mesmo padrão FaceGate (SHA-256, retenção 24m, consent log) | DPO = Paulo |

---

## 3. Estrutura de pastas

```
sindestiva-pe/                      ← raiz do monorepo
├── apps/
│   ├── web/                        # Centro de Comando (Next.js 15, fiscal/dirigente)
│   ├── pwa/                        # PWA do TPA (Next.js 15 PWA, mobile-first)
│   └── api/                        # FastAPI (rotas + serviços + workers)
├── packages/
│   ├── shared/                     # Tipos TS compartilhados (RBAC, enums, hash chain)
│   └── ui/                         # Componentes React (shadcn/ui base, tema portuário)
├── services/
│   └── scraper/                    # Worker Python FORA do Turborepo (cron 60s)
├── infra/
│   ├── docker-compose.yml          # Postgres 17 + Redis 7 + Traefik + MailHog
│   └── docker/
│       ├── postgres/init.sql       # Extensões + schema lousa_main
│       └── traefik/                # Config estática
├── .github/workflows/ci.yml
├── AGENTS.md                       # este arquivo
├── README.md
├── package.json                    # raiz com workspaces
├── turbo.json
├── pnpm-workspace.yaml
├── .env.example                    # template (NUNCA commitar .env)
├── .nvmrc                          # 22
├── .python-version                 # 3.12
├── .editorconfig
└── .gitignore
```

**Atenção:** `services/scraper` é propositalmente FORA do Turborepo. Tem ciclo
próprio (cron), reusa o mesmo `DATABASE_URL` da API e roda como worker separado.

---

## 4. Comandos essenciais

```bash
# Setup inicial
cp .env.example .env                # preencher NEXTAUTH_SECRET, RESEND_API_KEY
pnpm install                        # instala workspaces Node
cd apps/api && pip install -e ".[dev]"
cd services/scraper && pip install -e ".[dev]"

# Subir infra (Postgres 17 + Redis 7 + Traefik + MailHog)
pnpm db:up                          # só postgres + redis
pnpm infra:up                       # tudo
pnpm db:down
pnpm db:reset                       # apaga volumes e sobe de novo

# Dev
pnpm dev                            # sobe web (3000), pwa (3001), api (8000) em paralelo
pnpm dev:api                        # só a API
pnpm dev:worker                     # só o scraper (services/scraper)

# Banco
pnpm prisma migrate dev             # (quando Prisma entrar; antes, Alembic)
pnpm prisma studio

# Qualidade
pnpm lint                           # ruff + eslint
pnpm typecheck                      # tsc --noEmit
pnpm test                           # vitest + pytest
pnpm test:e2e                       # playwright
```

---

## 5. Convenções

- **Commits:** [Conventional Commits em PT-BR](https://www.conventionalcommits.org/).
  Prefixos: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `perf:`.
  Exemplo: `feat(lousa): adicionar modal de remanejamento com hash chain`.
- **Branches:** `main` (produção), `develop` (integração), `feat/T-XXX-descrição`,
  `fix/T-XXX-descrição`, `hotfix/descrição`.
- **Componentes React:** `kebab-case` no nome de arquivo (`lousa-table.tsx`),
  `PascalCase` no export. Máximo **300 linhas** por componente —超过拆分。
- **API REST-ish:** `GET/POST/PUT/DELETE /api/v1/<recurso>`. Versionamento
  obrigatório via `/v1/`. Erros em JSON `{error: {code, message, details}}`.
- **Banco:** nomes em `snake_case`, PK `uuid` (default `gen_random_uuid()`),
  timestamps `created_at`/`updated_at` em todas as tabelas, soft delete só
  quando explicitamente justificado.
- **Hash chain:** cada `audit_event` carrega `hash_evento` (SHA-256 do JSON +
  `hash_anterior`) e `hash_anterior` (referência). Trigger Postgres bloqueia
  `UPDATE/DELETE` em `audit_events` (T6-12).
- **Documentação:** ADRs em `docs/ADR/`, HUs em `docs/HU/`, atas em
  `docs/ATAS/`. Veja `SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md` seção 16.

---

## 6. Variáveis de ambiente

Todas centralizadas em `.env` (copie de `.env.example`). **Nunca commitar
`.env`.** Os arquivos `.env.example` lista as variáveis por seção:

| Seção | Variáveis chave | Quando preencher |
|---|---|---|
| Banco | `DATABASE_URL`, `POSTGRES_*` | Já tem default dev |
| Redis | `REDIS_URL` | Já tem default dev |
| Auth | `NEXTAUTH_SECRET` (`openssl rand -base64 32`), `NEXTAUTH_URL` | Sprint 1 |
| E-mail | `RESEND_API_KEY`, `RESEND_FROM` | Sprint 5 |
| WhatsApp | `EVOLUTION_API_*` | Sprint 1 (OTP TPA) |
| OGMO | `OGMO_EMAIL`, `OGMO_WEBHOOK_URL` | Sprint 0 (placeholder) + Sprint 5 |
| Push | `FCM_*` | Sprint 3 |
| Scraper | `SCRAPER_*` | Sprint 2 |

---

## 7. Como o scraping funciona

O **TPA/OGMO-PE** (AngularJS v1.24.0, mantido pelo TPA Tecnologia) é raspado
com **Playwright** (headful fallback) + **BeautifulSoup** (parser tolerante,
regex fallback, fingerprint de layout). A página muda sem aviso — risco R2
do plano. Mitigação: hash SHA-256 do HTML bruto; se divergir do último
conhecido, alerta em < 5 min no canal `#scraper-alerts` (WhatsApp + e-mail).

O **EscalaNet/Recife** (PHP simples, OGMO Recife) é raspado com **HTTPX**
direto. **URL real** (corrigida em 07/09/2026 — a URL antiga
`http://escalanet.recife.gov.br` não resolve DNS, foi descontinuada):

    POST http://www.ogmo-recife.org.br/EscalaNet/RelatorioResultadoEscala.php
    body: categoria=01&data=DD/MM/YYYY&periodo={46|47|48|49}&navio=&funcao=

Períodos: 46=0800/1400 (DIURNO), 47=1400/2000 (DIURNO), 48=2000/0200
(NOTURNO), 49=0200/0800 (NOTURNO). Mapeamento PT-BR→código em
`apps/api/app/scrapers/escalanet.py` (ESCALANET_FUNCAO_PARA_CODIGO).

O ciclo é **cron a cada 60s** durante operação (06h-22h), idempotente
(`INSERT ... ON CONFLICT DO UPDATE` em `lousa_snapshot`). Cada scrape vira
uma linha em `lousa_snapshot` com timestamp, hash do HTML e contagem de
células. O Centro de Comando consome via `GET /api/v1/lousa?porto=X&turno=Y`
e recebe updates via **WebSocket** (Redis Pub/Sub → FastAPI → Next.js).

Matcher de TPAs (Sprint 2, T2-05): cruza matrícula OGMO (numérica, ex:
`300443`, `162`) com cadastro interno do Sindicato (mock no MVP,
integração real com o cadastro do Sindicato quando houver).

---

## 8. MVP — escopo deste entregável (Fase 1 · 18 semanas)

### ✅ Dentro do escopo (Sprints 0-10)
- Centro de Comando (web) com 5 telas: Lousa Espelhada, Remanejamentos,
  Notificação OGMO, Auditoria, BI
- PWA do TPA com 4 abas: Início, Escala, Histórico, Perfil
- Auth: Fiscal (e-mail+senha), TPA (CPF+matrícula+OTP WhatsApp), Dirigente
  (e-mail+senha+2FA)
- Scraping TPA/Suape + EscalaNet/Recife
- Notificação OGMO por e-mail (Resend) + PDF (WeasyPrint) + webhook HMAC
  (preparado, aguardando endpoint)
- Auditoria append-only com hash chain SHA-256
- LGPD: consentimento, retenção 24m, Art. 18 (solicitar exclusão)
- 4 dashboards BI (ECharts) com export PDF
- Deploy em VPS Hetzner self-hosted, CI no GitHub Actions

### ❌ Fora do escopo (Fase 2 e 3)
- App mobile nativo (React Native) — PWA cobre o uso
- Integração bidirecional oficial com OGMO via API REST — depende de acordo
  tripartite (Fase 3)
- BI avançado com ML / predição de faltas — Fase 2
- Módulo de pagamento (contribuição sindical) via Mercado Pago — Fase 2
- Módulo de campanha de filiação — Fase 2
- Expansão para outros OGMOs (Itajaí, Paranaguá, Santos) — Fase 3 (B2B)
- Assinatura digital ICP-Brasil A1 nos e-mails — Fase 2
- Notificações por SMS (só WhatsApp no MVP)

---

## 9. Decisões de arquitetura (ADRs — resumo)

> ADRs completos em `docs/ADR/` (a criar em Sprint 1).

- **ADR-001** · Scraping tolerante com Playwright (não API oficial do OGMO).
  Aceita-se risco de quebrar 1-2x/ano. Mitigação: alerta < 5 min + parser fallback.
- **ADR-002** · Schema único `lousa_main` no MVP (não multi-tenant). Multi-tenant
  via schema-per-client entra em Fase 3 (B2B).
- **ADR-003** · Notificação ao OGMO primariamente por **e-mail** (não webhook).
  E-mail não precisa de aprovação do OGMO; webhook fica preparado para Fase 3.
- **ADR-004** · PWA do TPA com Next.js (não app nativo). Reduz custo, cobre 90%
  dos casos, dispensa loja.
- **ADR-005** · **Hash chain SHA-256** em todas as ações auditáveis (não
  blockchain). Performance vs. imutabilidade real; suficiente para o MPT aceitar
  como prova documental.
- **ADR-006** · **Resend** como provedor de e-mail (não SMTP próprio). Custo
  zero até 3k/mês.
- **ADR-007** · **Monorepo único** (`sindestiva-pe`) em vez de multi-repo.
  Mesmo padrão Becker/Córtex; reduz overhead de PRs cruzados.

---

## 10. Não fazer

- ❌ **NÃO** commitar `.env` (só `.env.example`). Está no `.gitignore` mas vale reforçar.
- ❌ **NÃO** expor `NEXTAUTH_SECRET`, `RESEND_API_KEY` ou qualquer credencial
  em logs, screenshots, issues ou commits.
- ❌ **NÃO** usar `any` em TypeScript. Use `unknown` + type guards ou
  refine o tipo. ESLint bloqueia (`@typescript-eslint/no-explicit-any: error`).
- ❌ **NÃO** criar componente React com mais de **300 linhas**. Quebre em
  sub-componentes. Lousa tem 26 colunas × 11 fainas — vai precisar.
- ❌ **NÃO** pular testes. Critério de aceite: **≥ 200 testes verdes** no
  Go-Live (unit + integration + E2E).
- ❌ **NÃO** usar `asyncio.run()` dentro de lifespan FastAPI (quebra em prod
  — pega-dica aprendida no FaceGate, ver `pegadinhas` no MEMORY do coder agent).

---

## 11. Links úteis

### Documentos do projeto (neste diretório)
- [`SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md`](./SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md)
  — plano executivo v1.0 (1090 linhas, 18 sprints, 86 HUs)
- [`SINDESTIVA-PE-CRONOGRAMA-45DIAS.md`](./SINDESTIVA-PE-CRONOGRAMA-45DIAS.md)
  — cronograma executivo de 45 dias (cenário 100% Paulo)
- [`SINDESTIVA-PE-PLANO-2026-08-12.md`](./SINDESTIVA-PE-PLANO-2026-08-12.md)
  — análise diagnóstica AS-IS / opções A·B·C (anterior)
- [`SINDESTIVA-PE-PROTOTIPO.html`](./SINDESTIVA-PE-PROTOTIPO.html) — protótipo
  navegável v0.1 (referência de UX)
- Screenshots do protótipo: `sindestiva-*.png` (7 arquivos)
- `gerar_gantt_45d.py` — script Python que gera o Gantt executivo

### Referências externas
- [Lei 8.630/93](https://www.planalto.gov.br/ccivil_03/leis/l8630.htm) (Lei dos Portos)
- [Lei 9.719/98](https://www.planalto.gov.br/ccivil_03/leis/l9719.htm) (Trabalho Portuário)
- [LGPD — Lei 13.709/18](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [OGMO/PE — TPA](http://tpa.ogmosuape.com.br)
- [OGMO Rio Grande (referência TAC)](https://ogmo-rg.com.br)

### Projetos irmãos Suporte Gerencial (mesmo padrão)
- `contatopscode/cortex` — Next.js + TS + Prisma + Postgres + Turborepo
- `contatopscode/sinapse` — FastAPI + Python + Postgres (multi-tenant por schema)
- `contatopscode/facegate` — FastAPI + Python + Postgres + pgvector + Evolution API
- `contatopscode/becker` — Next.js + TS + Postgres + Mercado Pago

---

## 12. Status atual (Sprint A — desbloqueio · 07/09/2026 · **CONCLUÍDA**)

### 🟢 Online em produção
- **API** `https://sindestiva-api.onrender.com` — 60+ endpoints, OpenAPI/Swagger, `/docs` ativo
- **Web (Centro de Comando)** `https://sindestiva-web.vercel.app` — 7 rotas (centro-comando, remanejamentos, ogmo, auditoria, bi, tpa, home)
- **PWA TPA** `https://sindestiva-pwa.vercel.app` — 1 página demo (Sprint 0 — Sprint C vai completar)
- **Schema DB** migrado (3 versions Alembic) + `Base.metadata.create_all` idempotente + `/admin/fix-purge-after-default` aplicado
- **Scraping TPA/Suape** ✅ ~94-113 células/dia
- **Scraping EscalaNet/Recife** ✅ 8 células agregadas de 24 TPAs reais (4 períodos: 46/47/48/49)
- **Seeds rodadas em prod** ✅ (Paulo/Manoel/Josias + TPA-001/TPA-002 + 8 catálogos) via endpoint `/admin/run-seeds`
- **Login validado** ✅ Paulo/Manoel/Josias autenticam; TPA-001 retorna escala

### 🟡 Validação Manoel Costa (07/09/2026)
- ✅ Estrutura Recife (PRODUCAO como faina default) **validada** com Manoel Costa
- Captura atual: ~24 TPAs/dia do EscalaNet (período 46 = 0800/1400, manhã ativa)
- Demais períodos (47/48/49) são vazios por design (turnos ainda não processados pelo OGMO)

### 🔴 Pendências (próxima sprint)
- Provisionar `*.lousa.pscode.ia.br` (DNS Cloudflare + domínios Vercel/Render) — guia em `DEPLOY.md §DNS`
- `RESEND_API_KEY` no Render (e-mail OGMO parado) — chave em https://resend.com (free 3k/mês)
- `EVOLUTION_API_KEY` no Render (OTP WhatsApp do TPA)

### 📋 Próximos marcos
- **M1** "Centro de Comando autenticado" — fim Sprint B (20/09/2026) — NextAuth + RBAC
- **M2** "PWA completo p/ TPA" — fim Sprint C (04/10/2026) — 4 abas + SW + manifest
- **M3** "Piloto Manoel Costa em Suape" — fim Sprint D (18/10/2026) — scraping dedicado + alertas + LGPD purge rodando

### 📄 Documentos do projeto
- [`DIAGNOSTICO-FUNCIONAL-2026-09-07.md`](./DIAGNOSTICO-FUNCIONAL-2026-09-07.md) — diagnóstico + plano de melhorias 4 sprints
- [`SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md`](./SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md) — plano executivo v1.0 (1090 linhas, 18 sprints, 86 HUs)

### 🛠 Endpoints admin one-shot (Sprint A — auth via `X-Admin-Token`)
- `POST /api/v1/admin/run-seeds` — roda 3 seeds idempotentes
- `POST /api/v1/admin/fix-purge-after-default` — aplica `now() + 5y` em `purge_after` de todas as tabelas
- `GET /api/v1/admin/debug/env` — diagnóstico bool de env vars críticas
