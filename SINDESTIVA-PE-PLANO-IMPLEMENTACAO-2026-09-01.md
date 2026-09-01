# SINDESTIVA-PE · Plano de Implementação da Lousa Digital

> **Documento de execução** · **Versão:** v1.0 · **Data:** 01/09/2026
> **Cliente:** SINDESTIVA-PE (Sindicato dos Estivadores nos Portos de Pernambuco)
> **Patrocinador cliente:** Sr. Josias Martins Santiago (Presidente)
> **Sponsor técnico:** Paulo Siqueira (Diretor de Tecnologia e Operação · Suporte Gerencial)
> **Produto:** **Lousa Digital** (slug interno: `lousa-sindestiva`)
> **Base estratégica:** `SINDESTIVA-PE-PLANO-2026-08-12.md` (análise diagnóstica AS-IS / opções A·B·C)
> **Base visual/funcional:** `SINDESTIVA-PE-PROTOTIPO.html` (protótipo navegável v0.1 — Centro de Comando, PWA TPA, BI, Auditoria)

---

## Sumário

1. [Sumário executivo](#1-sumário-executivo)
2. [Visão do produto e escopo](#2-visão-do-produto-e-escopo)
3. [Stack e arquitetura](#3-stack-e-arquitetura)
4. [Roadmap de alto nível (fases)](#4-roadmap-de-alto-nível-fases)
5. [Cronograma detalhado por sprint](#5-cronograma-detalhado-por-sprint)
6. [Estrutura analítica do projeto (WBS)](#6-estrutura-analítica-do-projeto-wbs)
7. [Equipe, papéis e governança](#7-equipe-papéis-e-governança)
8. [Plano de comunicação com o cliente](#8-plano-de-comunicação-com-o-cliente)
9. [Critérios de aceite globais e KPIs de sucesso](#9-critérios-de-aceite-globais-e-kpis-de-sucesso)
10. [Riscos, mitigações e plano B](#10-riscos-mitigações-e-plano-b)
11. [Orçamento e custos](#11-orçamento-e-custos)
12. [Plano de Go-Live e rollout](#12-plano-de-go-live-e-rollout)
13. [Pós-implantação e SLAs](#13-pós-implantação-e-slas)
14. [Dependências externas e pré-condições](#14-dependências-externas-e-pré-condições)
15. [Aprovações e governança contratual](#15-aprovações-e-governança-contratual)
16. [Anexos e referências](#16-anexos-e-referências)

---

## 1. Sumário executivo

A operação portuária do SINDESTIVA-PE em Recife e Suape hoje é sustentada por **lousa física, telefone e rádio** entre fiscais do Sindicato e o OGMO/PE. Falhas de comunicação custam horas-fiscais, geram passivo trabalhista e produzem assimetria de informação entre OGMO, Sindicato e Trabalhador Portuário Avulso (TPA).

A **Lousa Digital** é uma plataforma web + PWA que:

1. **Replica a lousa oficial do OGMO** (raspagem tolerante do TPA/OGMO-PE, hoje v1.24.0, e do EscalaNet/Recife) com nomes, matrículas e indicadores próprios;
2. **Digitaliza o remanejamento operacional** (Substituição de TPA) com motivo, base legal (CCT), hash de integridade e SLA de 5 min;
3. **Notifica o OGMO em tempo real** por **três caminhos paralelos** (e-mail formal com PDF assinado, webhook HMAC-SHA256 preparado para quando o OGMO topar, e painel de pendências OGMO no próprio Centro de Comando);
4. **Oferece um PWA para o TPA** ver sua escala do dia, confirmar presença, falar com o Fiscal via WhatsApp e receber push de remanejamentos;
5. **Gera BI/dashboard** para a diretoria do Sindicato negociar a próxima CCT com dados reais (comparecimento, ranking de remanejados, cais e horários críticos).

**Recomendação de escopo do MVP (período de 18 semanas, cenário realista):**
- Centro de Comando (web) com Lousa Espelhada, Remanejamentos, Auditoria, BI e Módulo OGMO;
- PWA do TPA com Escala do Dia, Confirmação de Presença, Histórico e Canal com Fiscal;
- Integração com OGMO via e-mail + webhook (preparado, aguardando endpoint);
- LGPD compliance completo (consentimento, retenção 24m, direito ao esquecimento);
- Homologação com 1 fiscal-piloto e Go-Live em 1 turno-piloto de Suape.

**Resultado esperado ao fim do MVP:**
- Fiscal remaneja 1 TPA com 1 motivo em **< 30 segundos**, com auditoria completa e notificação ao OGMO em **< 5 minutos**;
- OGMO recebe e-mail formal (PDF + hash) sem precisar aceitar nenhuma API;
- TPA consulta escala no celular, sem precisar ir ao porto;
- Diretoria do Sindicato acessa BI consolidado para próxima rodada de CCT;
- 100% das ações auditáveis (quem, quando, por quê, base legal, hash chain).

**Investimento total ano 1:** **R$ 9,5 a 13 mil** (infra + assessoria jurídica + viagem). Mão de obra do sponsor técnico (Paulo) é custo interno da Suporte Gerencial. Não há cobrança de licença do Sindicato no MVP — modelo de monetização fica para Fase 3 (B2B replicável para outros 25+ OGMOs do Brasil).

---

## 2. Visão do produto e escopo

### 2.1 Personas

| Persona | Quem é | Necessidade primária | Métrica de sucesso |
|---|---|---|---|
| **Fiscal do Sindicato** (Manoel Costa, perfil-piloto) | Fica no cais, opera a lousa física hoje | Remanejar TPA em < 30s com notificação automática ao OGMO | Tempo médio de remanejamento cai de ~12 min (telefone) para < 30s |
| **Dirigente do Sindicato** (Josias Santiago) | Presidente, decide rumos políticos | BI consolidado para negociar CCT, fiscalizar OGMO, prestar contas a Associados | Consegue abrir dashboard e responder "quantos remanejamentos por cais nos últimos 30 dias" em < 1 min |
| **TPA — Trabalhador Portuário Avulso** (~2.000 em Recife + Suape) | Sobe no navio quando chamado | Saber se está escalado HOJE, sem precisar ir ao porto ou ligar | 60% dos TPAs com PWA instalado em 90 dias |
| **TI do OGMO/PE** (TPA Tecnologia ou sucessor) | Mantém o TPA (AngularJS v1.24.0) | Receber notificação formal auditável, sem precisar manter API nova | SLA de ACK em até 24h úteis |
| **MPT-PE** (Ministério Público do Trabalho) | Fiscaliza cumprimento da Lei 9.719/98 | Acessar trilha de auditoria sob demanda, validar integridade | Export PDF assinado em < 30s |

### 2.2 Escopo do MVP (Fase 1) — 18 semanas

**Dentro do escopo:**
- Centro de Comando (web responsivo) com 5 telas: Lousa Espelhada, Remanejamentos, Notificação OGMO, Auditoria, BI & Relatórios;
- PWA do TPA (mobile-first, instalável, offline-first) com 4 abas: Início, Escala, Histórico, Perfil;
- Autenticação unificada: Fiscal (e-mail + senha), TPA (CPF + matrícula OGMO + OTP WhatsApp), Dirigente (e-mail + senha + 2FA);
- Integração com TPA/OGMO-PE via **scraping tolerante** (Playwright + BeautifulSoup) com detecção de mudança de layout e alerta em < 5 min;
- Integração com EscalaNet/Recife (PHP) via scraping HTTPX;
- Notificação ao OGMO por e-mail (SendGrid/Resend) com template HTML + PDF anexado + hash SHA-256 visível;
- Webhook preparado (HMAC-SHA256), aguardando endpoint do OGMO;
- Auditoria append-only com hash chain (cada evento inclui hash do evento anterior);
- LGPD: termo de consentimento, retenção 24 meses, painel do TPA para download/exclusão de dados (Art. 18 LGPD);
- BI: 4 dashboards (comparecimento, ranking remanejados, cais/horário crítico, status OGMO);
- Deploy em VPS Hetzner self-hosted (mesmo padrão Becker/Córtex), CI no GitHub Actions.

**Fora do escopo (entra em Fases 2 e 3):**
- App mobile nativo (React Native) — PWA cobre o uso;
- Integração bidirecional oficial com OGMO via API REST — depende de acordo tripartite (Fase 3, 12-18 meses);
- BI avançado com ML/predição de faltas, sugestão de substitutos — Fase 2;
- Módulo de pagamento (contribuição sindical) via Mercado Pago — Fase 2 (replicar padrão Becker);
- Módulo de campanha de filiação — Fase 2;
- Expansão para outros portos/OGMOs (Itajaí, Paranaguá, Santos etc.) — Fase 3 (modelo B2B);
- Assinatura digital ICP-Brasil A1 nos e-mails — Fase 2 (MVP usa hash SHA-256 visível, suficiente para o SLA);
- Notificações por SMS (só WhatsApp no MVP).

### 2.3 Premissas e restrições

**Premissas:**
- O Sindicato não tem sistema próprio hoje → não há migração de dados legados;
- O OGMO/PE **não vai cooperar no MVP** (não responde a pedido de API) — a integração é unilateral via scraping + e-mail;
- O TPA Tecnologia (fornecedor do OGMO) **pode mudar o layout do TPA** a qualquer momento — o scraping precisa ser tolerante;
- O Fiscal-piloto (Manoel Costa) é o usuário-chave e co-designer;
- A CCT 2024-2026 vigente tem cláusulas de remanejamento conhecidas e será a base dos motivos;
- O SINDESTIVA tem estrutura mínima de TI (1 computador, internet banda larga) para suportar a operação diária do Centro de Comando no escritório.

**Restrições:**
- Respeitar exclusividade do OGMO na escalação (Lei 8.630/93 art. 18, Lei 12.815/13 art. 32, Lei 9.719/98 art. 5º);
- LGPD: dados pessoais de TPAs exigem consentimento explícito;
- O protótipo HTML já é a referência de UX; desvios precisam de justificativa formal.

---

## 3. Stack e arquitetura

### 3.1 Stack definitivo (alinhado com padrão Suporte Gerencial)

| Camada | Tecnologia | Projeto de referência | Justificativa |
|---|---|---|---|
| **Monorepo** | Turborepo + pnpm | Córtex | Padronização; build incremental rápido |
| **Backend** | Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 | Sinapse, FaceGate | Reuso de drivers, scraping, integrações |
| **DB** | PostgreSQL 17 + schema-per-tenant (preparado) | Sinapse | Multi-tenant futuro (Fase 3) |
| **Cache / Fila** | Redis 7 | Córtex | Pub/Sub para WebSocket |
| **Frontend Web** | Next.js 15 (App Router) + TS + Tailwind + shadcn/ui | Córtex, Becker | Páginas com reuso do design system |
| **PWA TPA** | Next.js 15 PWA + Workbox + IndexedDB | Córtex (parcial) | Instalável, offline-first, push |
| **Auth** | NextAuth (Auth.js) v5 + JWT (8h) + Credentials + OTP WhatsApp | Córtex | Mesmo padrão; OTP híbrido |
| **Scraping** | Playwright (headful fallback) + BeautifulSoup + HTTPX | novo | Tolerância a mudança de layout |
| **Push Notification** | Firebase Cloud Messaging (FCM) | Becker, Córtex | Cobre Android; iOS via PWA push |
| **Mensageria** | Evolution API (WhatsApp) | Córtex, Becker | Custo baixo, Open Source |
| **E-mail transacional** | Resend (3k/mês free tier) | — | Templates + bounce handling |
| **PDF** | WeasyPrint (Python) | — | Renderiza template HTML do e-mail |
| **BI** | Apache ECharts (frontend) + agregações SQL | — | Mesma lib usada no Sinapse |
| **WebSocket** | FastAPI nativo (sem dependência extra) | Córtex, FaceGate | Tempo real do Centro de Comando |
| **Infra** | VPS Hetzner CPX31 (4 vCPU, 8GB RAM, 160GB SSD) | Becker | ~R$ 250/mês; Traefik + Docker Compose |
| **CI/CD** | GitHub Actions + Easypanel (mesmo padrão Suporte Gerencial) | Becker, Córtex | Auto-deploy em push na `main` |
| **Versionamento** | GitHub (repo privado `contatopscode/lousa-sindestiva`) | — | Convencional Commits + PRs |
| **LGPD** | Mesmo padrão FaceGate (SHA-256, retenção 24m, consent log) | FaceGate | DPO = Paulo |

### 3.2 Arquitetura de alto nível

```
┌──────────────────────────────────────────────────────────────────┐
│                     VPS HETZNER (CCA-PN)                        │
│                                                                  │
│  ┌─────────────────┐    ┌──────────────────┐    ┌──────────────┐│
│  │ Next.js (web)   │    │ Next.js (PWA TPA) │    │ FastAPI      ││
│  │ Centro Comando  │◄──►│ worker.ts service │◄──►│ /v1/*        ││
│  │ (port 3000)     │WS  │ (port 3001)       │REST│ (port 8000)  ││
│  └─────────────────┘    └──────────────────┘    └──────┬───────┘│
│                                                        │        │
│                              ┌─────────────────────────┘        │
│                              │                                  │
│                       ┌──────▼──────┐    ┌──────────────────┐  │
│                       │ PostgreSQL  │    │ Redis (Pub/Sub)  │  │
│                       │ schema=     │    │                  │  │
│                       │ lousa_main  │    └──────┬───────────┘  │
│                       └─────────────┘           │              │
│                              ▲                  │              │
│                              │           ┌──────▼──────┐       │
│                       ┌──────┴──────┐    │ Workers:    │       │
│                       │ Scraper     │    │ • scraper   │       │
│                       │ Playwright  │    │ • notifier  │       │
│                       │ (cron 60s)  │    │ • pdf       │       │
│                       └──────┬──────┘    └─────────────┘       │
│                              │                                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌───────────┐    ┌──────────┐    ┌─────────────┐
       │ TPA       │    │ EscalaNet│    │ Resend      │
       │ OGMO/PE   │    │ Recife   │    │ (e-mail)    │
       │ (scraping)│    │ (HTTPX)  │    └─────────────┘
       └───────────┘    └──────────┘
```

### 3.3 Estrutura do repositório

```
lousa-sindestiva/
├── apps/
│   ├── web/                # Centro de Comando (Next.js, fiscal/dirigente)
│   └── pwa/                # PWA do TPA (Next.js PWA)
├── packages/
│   ├── api/                # FastAPI app (rotas + serviços)
│   ├── db/                 # SQLAlchemy models + Alembic
│   ├── scraper/            # Playwright + BeautifulSoup (TPA/OGMO)
│   ├── notifier/           # E-mail + PDF + Webhook
│   ├── ui/                 # Componentes shadcn compartilhados
│   └── shared/             # Tipos, constantes, hash chain
├── infra/
│   ├── docker-compose.yml  # Postgres, Redis, Traefik
│   ├── Dockerfile.api
│   ├── Dockerfile.web
│   ├── Dockerfile.pwa
│   └── deploy.sh           # Easypanel + Hetzner
├── docs/
│   ├── ADR/                # Architecture Decision Records
│   ├── API.md
│   ├── LGPD.md
│   └── RUNBOOK.md
├── .github/workflows/
│   ├── ci.yml              # lint + type-check + test
│   └── deploy.yml          # auto-deploy em main
├── AGENTS.md
└── README.md
```

### 3.4 Decisões arquiteturais (ADRs críticos, resumo)

| ID | Decisão | Trade-off |
|---|---|---|
| ADR-001 | Scraping tolerante com Playwright, não API oficial do OGMO | Dependência de layout; aceita-se risco de quebrar 1-2x/ano (mitigação: alertas + parser fallback) |
| ADR-002 | Schema único no MVP (não multi-tenant) | Simplifica deploy; trade-off ok porque MVP = 1 cliente |
| ADR-003 | Notificação ao OGMO primariamente por e-mail (não webhook) | E-mail não precisa de aprovação do OGMO; webhook fica pronto para Fase 3 |
| ADR-004 | PWA do TPA com Next.js, não app nativo | Reduz custo, cobre 90% dos casos, dispensa loja |
| ADR-005 | Hash chain SHA-256 em todas as ações (não blockchain) | Performance vs. imutabilidade real; suficiente para o MPT aceitar como prova documental |
| ADR-006 | Resend como provedor de e-mail (não SMTP próprio) | Custo zero até 3k/mês; reduz manutenção |

---

## 4. Roadmap de alto nível (fases)

```
Fase 0              Fase 1 (MVP)              Fase 2               Fase 3
Set/2026            Out/2026 – Fev/2027       Mar/2027 – Jun/2027  Jul/2027 – Dez/2028
  │                       │                        │                   │
  ├─ Kickoff              ├─ Centro de Comando      ├─ BI avançado     ├─ API oficial OGMO
  ├─ CCT/Números reais    ├─ PWA TPA                ├─ Pagamento MP    ├─ B2B (outros 25 OGMOs)
  ├─ LGPD termo           ├─ Scraping TPA           ├─ SMS/ICP-Brasil  ├─ White-label multi-tenant
  └─ Sprint 0 (1 sem)     ├─ Notificação OGMO       └─ App nativo      └─ Receita recorrente
                          ├─ Auditoria + BI
                          ├─ Homologação
                          └─ Go-Live (1 turno Suape)
```

| Fase | Período | Entregável macro | Esforço Paulo | Investimento |
|---|---|---|---|---|
| **Fase 0 — Sprint 0** | 01-07 set 2026 (1 sem) | CCT obtida, números reais levantados, LGPD termo OK, ambiente dev pronto | 12-16h | R$ 0 |
| **Fase 1 — MVP** | 08 set 2026 – 09 fev 2027 (18 sem, parcial 50-60%) | Centro de Comando + PWA TPA + Notificação OGMO + Auditoria + BI + Go-Live | 320-360h | R$ 4-6k (infra 5m) + R$ 5k (jurídico/viagem) |
| **Fase 2 — Polimento + Expansão** | mar-jun 2027 (16 sem) | BI avançado, pagamento MP, SMS, app nativo opcional | 280h | R$ 2-3k (infra adicional) |
| **Fase 3 — B2B** | jul 2027+ (12-18 meses) | API oficial, modelo white-label, replicação para 5+ OGMOs | variável | variável |

**Foco do presente documento:** **Fases 0 e 1**.

---

## 5. Cronograma detalhado por sprint

### 5.1 Visão geral (Gantt textual)

```
Semana:    S0  S1  S2  S3  S4  S5  S6  S7  S8  S9  S10 S11 S12 S13 S14 S15 S16 S17 S18
Sprint:    ──  T1  T1  T2  T2  T3  T3  T4  T4  T5  T5  T6  T6  T7  T7  T8  T8  T9  T9  T10
Data:      1/9 8/9 15/9 22/9 29/9 6/10 13/10 20/10 27/10 3/11 10/11 17/11 24/11 1/12 8/12 15/12 22/12 5/1 12/1 19/1 26/1
           ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤
Kickoff    ██
CCT/Real              ████
Repo/Mono                    ████████
Auth+RBAC                           ████████████
Scraping TPA                                  ██████████████
Scraping Recife                                       ████████
PWA TPA                                                       ████████████
Lousa Web                                                            ████████████
Remanej. + OGMO                                                          ████████████
Auditoria                                                                     ████████
BI                                                                                ████████
Hardening                                                                            ████
Homologação                                                                             ████
Go-Live                                                                                  ██
```

### 5.2 Detalhamento por sprint

#### **Sprint 0 — Kickoff (Sem 0: 01-07 set 2026) · 1 semana · 12-16h**

**Objetivo:** travar premissas, levantar números reais, alinhar com Josias.

| # | Atividade | Horas | Responsável | Entregável |
|---|---|---|---|---|
| K-1 | Reunião de kickoff com Josias Santiago (SINDESTIVA-PE) | 2h | Paulo + Josias | Ata + checklist de premissas assinado |
| K-2 | Obter CCT 2024-2026 vigente (cópia) | 1h | Josias | CCT digitalizada |
| K-3 | Levantar números reais: nº de TPAs, fiscais, turnos/dia, volume remanejamentos | 4h | Paulo + Manoel Costa | Planilha `real-numbers.xlsx` |
| K-4 | Visita física ao Porto de Suape (1 turno) com o Fiscal | 4h | Paulo + Manoel | Diário de bordo + fotos + fluxos AS-IS |
| K-5 | Termo de consentimento LGPD (versão 1) revisado por advogado | 2h | Advogado | Parecer escrito (R$ 1,5-3k) |
| K-6 | Setup do repo `lousa-sindestiva` (Turborepo, CI, secrets) | 3h | Paulo | Repo criado, CI verde |
| K-7 | Pedido formal ao OGMO/PE para interlocução técnica (carta registrada) | 1h | Josias (com apoio Paulo) | AR digitalizado |

**Marco (Milestone M0):** "Premissas validadas" — gate de entrada da Fase 1.
**Critério de saída:** CCT em mãos, números reais preenchidos, parecer jurídico escrito em PDF, repo no ar.

---

#### **Sprint 1 — Fundação (Sem 1-2: 08-21 set 2026) · 2 semanas · 36-40h**

**Objetivo:** base de código rodando, auth funcionando, banco modelado.

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T1-01 | Setup monorepo (Turborepo + pnpm, configs TS, lint, Prettier) | 4h | K-6 | `pnpm dev` roda |
| T1-02 | Modelagem do banco (SQLAlchemy + Alembic): `User`, `Role`, `Porto`, `Turno`, `Faina`, `Funcao`, `LousaSnapshot`, `Remanejamento`, `Tpa`, `Fiscal`, `AuditEvent` | 6h | — | Migration inicial aplicada |
| T1-03 | Seed: 2 portos (SUAPE, RECIFE) × 2 turnos × 11 fainas × 26 funções = 1.144 células de lousa | 2h | T1-02 | Seed idempotente |
| T1-04 | Auth (NextAuth v5) com 3 roles: FISCAL, DIRIGENTE, TPA | 6h | T1-01 | Login web + JWT 8h |
| T1-05 | RBAC engine (`packages/shared/rbac.ts` com matriz de permissões) | 4h | T1-04 | Testes unitários verdes |
| T1-06 | Docker Compose (Postgres 17, Redis 7, Traefik) + script bootstrap | 4h | — | `docker compose up` sobe tudo |
| T1-07 | CI no GitHub Actions: lint, type-check, pytest, playwright smoke | 4h | T1-01 | Badge verde no README |
| T1-08 | Página `/login` estilizada conforme protótipo (cores, tipografia, fundo) | 4h | T1-04 | Screenshot de referência |
| T1-09 | Layout base do Centro de Comando (header + sidebar + main, dark portuário-industrial) | 4h | T1-01 | Replica exata do protótipo |
| T1-10 | LGPD: middleware de consentimento + log de aceite | 2h | T1-04 | Audit log de aceite |

**Marco (M1):** "Centro de Comando autenticado" — Paulo consegue logar como Fiscal/Dirigente e ver shell vazio.
**Definition of Done (DoD):**
- ✅ `pnpm dev` sobe web (3000), PWA (3001) e API (8000);
- ✅ 3 seeds (paulo=DIRIGENTE, manoel=FISCAL, jose=TPA) conseguem logar;
- ✅ RBAC bloqueia acesso cruzado (TPA não vê /lousa, Fiscal não vê /admin);
- ✅ CI verde em PR;
- ✅ LGPD termo aparece no primeiro login.

---

#### **Sprint 2 — Scraping do OGMO (Sem 3-4: 22 set - 05 out 2026) · 2 semanas · 40h**

**Objetivo:** dados reais do TPA e do EscalaNet fluindo para o banco.

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T2-01 | Módulo scraper TPA/Suape (Playwright + BeautifulSoup) com parser tolerante (regex fallback, fingerprint de layout) | 12h | T1-02 | `scraper/suape.py` rodando em dev |
| T2-02 | Cron de scraping a cada 60s durante operação (06h-22h) + idempotência | 4h | T2-01 | Snapshots salvos no banco |
| T2-03 | Alerta de mudança de layout (hash da página HTML vs. último conhecido; e-mail/WhatsApp se divergir) | 4h | T2-01 | Alerta testado em ambiente |
| T2-04 | Módulo scraper EscalaNet/Recife (HTTPX, página PHP simples) | 6h | T1-02 | `scraper/recife.py` rodando |
| T2-05 | Matcher de TPAs: cruzar matrículas OGMO com cadastro interno do Sindicato (mock no MVP) | 4h | T2-01 | Tabela `Tpa` populada |
| T2-06 | Endpoint `GET /api/v1/lousa?porto=X&turno=Y` retornando snapshot mais recente | 3h | T2-01 | Swagger doc |
| T2-07 | Endpoint `GET /api/v1/lousa/listagem?data=YYYY-MM-DD&turno=N` (réplica do TPA) | 3h | T2-01 | Swagger doc |
| T2-08 | Testes de scraping com fixture HTML congelada (TPA v1.24.0 gravado em 01/09) | 4h | T2-01 | 10+ testes verdes |

**Marco (M2):** "Lousa oficial espelhada" — dados reais de Suape (e eventualmente Recife) fluem para o banco a cada 60s.
**DoD:**
- ✅ Snapshot do TPA Suape (12/08/2026 manhã) bate com o protótipo;
- ✅ Scraper detecta mudança de layout e alerta no canal `#scraper-alerts`;
- ✅ API retorna 26 colunas × 11 fainas × 2 turnos sem erro;
- ✅ Latência scraping → DB < 5s.

---

#### **Sprint 3 — PWA do TPA · base (Sem 5-6: 06-19 out 2026) · 2 semanas · 40h**

**Objetivo:** PWA instalável com login, "Minha Escala Hoje" e Confirmação de Presença.

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T3-01 | Setup PWA (Next.js + `manifest.json` + service worker via next-pwa) | 3h | T1-01 | `npm run build` gera PWA |
| T3-02 | Tela `/login` do PWA (CPF + matrícula, OTP WhatsApp) | 4h | T1-04 | OTP chega em < 30s |
| T3-03 | Tela `/inicio` (Bom dia + nome + "Você está escalado hoje?" + função + cais) | 4h | T2-06 | Idêntica ao protótipo |
| T3-04 | Tela `/escala` (lista de escalas dos próximos 7 dias, por turno) | 3h | T2-06 | Filtragem por data OK |
| T3-05 | Tela `/historico` (últimos 12 meses de engajamentos) | 3h | T2-07 | Paginação infinita |
| T3-06 | Tela `/perfil` (dados pessoais, telefone, consentimento LGPD, botão de exclusão) | 3h | T1-10 | Edição + exclusão funcionais |
| T3-07 | Confirmação de presença (botão "Confirmar Presença" + "Não vou") | 3h | T3-03 | Envia push pro Fiscal |
| T3-08 | IndexedDB para cache offline (escala do dia fica acessível sem 4G) | 4h | T3-03 | Funciona no metrô (testado) |
| T3-09 | Deep link WhatsApp (botão "Falar com o Fiscal" abre `wa.me/...`) | 2h | — | Abre conversa |
| T3-10 | Push FCM (registro de token no primeiro login) | 4h | T1-01 | Push chega no Android |
| T3-11 | Teste de instalação (Lighthouse PWA score > 90) | 3h | T3-01 | Relatório |
| T3-12 | Wireframe da tela de CCT em PDF dentro do app (somente placeholder no MVP) | 2h | T3-06 | Botão abre PDF estático |
| T3-13 | Página LGPD completa (termo, art. 18, solicitar exclusão) | 3h | T1-10 | Formulário funcional |
| T3-14 | Testes E2E (Playwright) — fluxo TPA: login → ver escala → confirmar presença | 2h | T3-07 | 5+ cenários verdes |

**Marco (M3):** "PWA instalável e funcional" — TPA consegue baixar, logar, ver escala e confirmar presença.
**DoD:**
- ✅ Lighthouse PWA score ≥ 90;
- ✅ Funciona offline (escala em cache);
- ✅ OTP WhatsApp chega em < 30s;
- ✅ Confirmação de presença gera notificação pro Fiscal.

---

#### **Sprint 4 — Centro de Comando · Lousa + Fila OGMO (Sem 7-8: 20 out - 02 nov 2026) · 2 semanas · 40h**

**Objetivo:** replica exata do protótipo `/sec-lousa` com WebSocket.

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T4-01 | Tela `/lousa` — header + 4 KPIs (TPAs escalados, presença, remanejamentos hoje, sync OGMO) | 4h | T1-09 | Replica KPIs do protótipo |
| T4-02 | Tabela da Lousa (26 colunas × 11 fainas × 2 turnos) com agrupamento por categoria (Mando/Terno/Técnica/Vigia) | 8h | T2-06 | Idêntica ao protótipo |
| T4-03 | Switcher Porto (SUAPE/RECIFE) e Turno (DIURNO/NOTURNO) | 2h | T4-02 | Estado sincronizado |
| T4-04 | Legenda de cores (vermelho = ausente, amarelo = remanejado, contorno = hover) | 2h | T4-02 | CSS conforme protótipo |
| T4-05 | WebSocket: push de novas snapshots a cada scrape (latência < 1s) | 6h | T2-02 | Live update funcionando |
| T4-06 | Fila "Notificação OGMO" (sidebar direita) — mostra remanejamentos pendentes/enviados/ack | 4h | T4-02 | Status PEND/SENT/ACK/NACK |
| T4-07 | Toast notifications (canto inferior direito, igual protótipo) | 2h | T4-05 | 3 tipos: ok, amber, red |
| T4-08 | Click em ponteiro → abre modal de remanejamento (pré-preenchendo contexto) | 3h | T4-02 | Modal idêntico ao protótipo |
| T4-09 | Filtros e busca (por TPA, função, cais) | 3h | T4-02 | Filtragem em < 200ms |
| T4-10 | Página de erro quando scraper cai (banner amarelo "Sync paused") | 2h | T2-03 | Banner aparece |
| T4-11 | Testes E2E (Playwright) — fluxo Fiscal: login → ver lousa → clicar ponteiro | 4h | T4-08 | 5+ cenários |

**Marco (M4):** "Centro de Comando mostra lousa oficial" — Fiscal vê a lousa do OGMO em tempo real, com cliques para remanejar.
**DoD:**
- ✅ Tabela carrega em < 1s com 142 TPAs;
- ✅ Atualização WebSocket visível em < 2s;
- ✅ Cliques em ponteiro abrem modal com contexto correto;
- ✅ Fila OGMO mostra histórico de remanejamentos.

---

#### **Sprint 5 — Remanejamento + Notificação OGMO (Sem 9-10: 03-16 nov 2026) · 2 semanas · 44h**

**Objetivo:** ciclo completo Fiscal → Sistema → OGMO.

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T5-01 | Endpoint `POST /api/v1/remanejamentos` (criar, validar, gravar) | 4h | T1-02 | Swagger + testes |
| T5-02 | Modal de remanejamento: TPA a remover, TPA a inserir (opcional), motivo (dropdown), base legal, observações, anexo (mock), notify PWA | 4h | T4-08 | Idêntico ao protótipo |
| T5-03 | Checkbox de ack CCT + validação obrigatória | 1h | T5-02 | Sem ack, submit bloqueado |
| T5-04 | Geração de hash chain no momento da criação (SHA-256 do JSON + hash anterior) | 3h | T1-02 | `hash_evento` e `hash_anterior` populados |
| T5-05 | Worker de e-mail (Resend) — template HTML com tabela de campos + PDF anexado | 6h | T5-04 | E-mail chega em < 1 min |
| T5-06 | Geração de PDF (WeasyPrint) com cabeçalho formal + hash visível no rodapé | 4h | T5-05 | PDF anexado ao e-mail |
| T5-07 | Webhook preparado (HMAC-SHA256) — endpoint stub + gerador de payload JSON | 4h | T5-04 | Payload conforme protótipo |
| T5-08 | Painel OGMO read-only (token fixo) — mesmo conteúdo da fila, em URL dedicada | 4h | T4-06 | URL `/ogmo/pendentes?token=...` |
| T5-09 | Tela `/remanejamentos` (histórico com filtros: turno, data, TPA, fiscal, status) | 4h | T5-01 | 4 KPIs no topo |
| T5-10 | Status SENT/PEND/ACK/NACK (workflow) — campo `status` + transições permitidas | 2h | T5-09 | Semântica clara |
| T5-11 | Retry de e-mail (3 tentativas com backoff 1m/5m/15m) | 3h | T5-05 | Logs de retry |
| T5-12 | Testes E2E (Playwright) — fluxo: clicar → modal → submit → e-mail enviado (mock SMTP) | 5h | T5-05 | 8+ cenários |

**Marco (M5):** "Remanejamento digital com notificação ao OGMO" — Fiscal remaneja, OGMO recebe e-mail formal com PDF + hash.
**DoD:**
- ✅ Criar remanejamento em < 30s;
- ✅ E-mail chega em < 1 min;
- ✅ PDF gerado com hash visível;
- ✅ Webhook testado em ambiente (Resend mock);
- ✅ Status transita corretamente.

---

#### **Sprint 6 — Auditoria + LGPD completo (Sem 11-12: 17-30 nov 2026) · 2 semanas · 36h**

**Objetivo:** trilha de auditoria imutável + LGPD compliance.

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T6-01 | Endpoint `GET /api/v1/audit?data=...&fiscal=...` (paginação) | 3h | T1-02 | Swagger |
| T6-02 | Tela `/auditoria` — KPIs (eventos hoje, hash chain íntegro, retenção, acessos externos) + timeline | 5h | T1-09 | Idêntica ao protótipo |
| T6-03 | Verificador de hash chain (job diário 03:00 que recalcula e alerta se quebrar) | 4h | T5-04 | Alerta em `#audit-alerts` |
| T6-04 | Export PDF assinado (cabeçalho formal + hash do intervalo + assinatura Paulo) | 4h | T6-02 | Botão funcional |
| T6-05 | Export CSV (todos os eventos) | 1h | T6-02 | Download em < 10s |
| T6-06 | Retenção 24m (job diário que apaga eventos > 24m, com snapshot agregado) | 2h | T6-01 | Logs de deleção |
| T6-07 | Painel TPA para solicitar exclusão (Art. 18 LGPD) — workflow de aprovação | 4h | T3-06 | TPA consegue pedir |
| T6-08 | DPO dashboard (Paulo) — pedidos pendentes, histórico de consentimentos | 3h | T1-10 | Tela `/admin/lgpd` |
| T6-09 | Logs de acesso (quem viu dados de qual TPA, quando, IP) | 3h | T1-04 | Tabela `access_log` |
| T6-10 | Documento `docs/LGPD.md` (RIPD, base legal, retenção, contatos DPO) | 2h | — | Doc no repo |
| T6-11 | Parecer jurídico final (advogado) sobre conformidade LGPD | 1h | Advogado | Parecer escrito |
| T6-12 | Testes de auditoria (verificar que `INSERT` em `audit_events` é append-only via trigger Postgres) | 4h | T1-02 | Trigger ativo |

**Marco (M6):** "Auditoria e LGPD prontos" — sistema compliant com LGPD, hash chain íntegro, MPT consegue extrair relatório.
**DoD:**
- ✅ Verificador diário não quebrou (teste com hash adulterado);
- ✅ TPA consegue pedir exclusão e recebe confirmação;
- ✅ Export PDF em < 30s;
- ✅ Trigger bloqueia UPDATE/DELETE em `audit_events`.

---

#### **Sprint 7 — BI & Dashboards (Sem 13-14: 01-14 dez 2026) · 2 semanas · 32h**

**Objetivo:** 4 dashboards do protótipo funcionando com dados reais.

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T7-01 | Tela `/bi` — 4 KPIs (comparecimento, folha paga, causa #1 falta, % NACK) | 3h | T1-09 | Idêntica ao protótipo |
| T7-02 | Gráfico de barras "Remanejamentos por dia" (ECharts) com filtro 7/30/90/365 dias | 4h | T5-09 | Reativo |
| T7-03 | Cards "Função + remanejada", "Cais + problemático", "Horário + crítico" (top-1 com % do total) | 3h | T5-09 | Calculado via SQL agregado |
| T7-04 | Ranking "Top remanejados" (lista de 10) | 2h | T5-09 | Funcional |
| T7-05 | Insight automático (regra: se TPA for remanejado 5+ vezes no período, exibir box amarelo) | 2h | T7-04 | Insight dinâmico |
| T7-06 | Comparativo de períodos (clicar em barra abre detalhe do dia) | 2h | T7-02 | Drill-down |
| T7-07 | Export PDF do BI (com capa, gráficos renderizados, hash) | 3h | T7-01 | Download em < 30s |
| T7-08 | Cache de agregações (Redis, TTL 5 min) — não martelar o banco | 2h | T7-01 | < 1s nas queries |
| T7-09 | Testes (5+ cenários: comparar com cálculo manual em planilha) | 3h | T7-01 | Verde |
| T7-10 | Documentação para o Presidente usar (1 PDF de 4 páginas) | 2h | T7-01 | `manual-presidente.pdf` |
| T7-11 | Tela de BI responsiva (tablet do Presidente) | 3h | T7-01 | Lighthouse mobile > 80 |
| T7-12 | Empty state (quando não há dados ainda) | 1h | T7-01 | Mensagem amigável |

**Marco (M7):** "BI pronto para a diretoria" — Presidente consegue ver dados reais para próxima CCT.
**DoD:**
- ✅ Comparação com planilha manual diverge em < 1%;
- ✅ PDF exportado em < 30s;
- ✅ Drill-down funciona.

---

#### **Sprint 8 — Hardening + Performance (Sem 15-16: 15-28 dez 2026) · 2 semanas · 30h**

**Objetivo:** sistema pronto pra produção. (Pausa natural: Natal/Ano Novo — equipe reduzida.)

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T8-01 | Rate limit (slowapi): 60/min login, 30/min remanejamento, 10/min export | 3h | T1-04 | Testes verdes |
| T8-02 | CSRF + Helmet + CSP + CORS restrito (origens do domínio produção) | 2h | T1-04 | Testado |
| T8-03 | WAF básico (CrowdSec ou Cloudflare free) — proteção contra scrapers maliciosos | 3h | — | Ativo em prod |
| T8-04 | Backups diários Postgres (criptografados, retidos 30 dias, restore testado) | 3h | T1-02 | Restore testado |
| T8-05 | Testes de carga (k6, 50 usuários simultâneos na lousa, p95 < 1s) | 4h | T4-02 | Relatório |
| T8-06 | Otimização de queries (índices em `lousa_snapshot`, `remanejamento`, `audit_event`) | 3h | T1-02 | EXPLAIN antes/depois |
| T8-07 | Monitoramento (Uptime Kuma + Sentry + log centralizado em Loki) | 4h | — | Alertas funcionando |
| T8-08 | Runbook operacional (`docs/RUNBOOK.md` — quem fazer o quê quando X quebrar) | 3h | — | Doc no repo |
| T8-09 | Plano de Disaster Recovery (RPO 24h, RTO 4h) | 2h | T8-04 | Doc + teste |
| T8-10 | Revisão de segurança (própria — checklist OWASP Top 10) | 3h | — | Relatório |

**Marco (M8):** "Sistema pronto pra produção" — checks de segurança, performance, backup, monitoramento todos verdes.
**DoD:**
- ✅ k6 p95 < 1s com 50 VUs;
- ✅ Restore de backup completo em < 4h;
- ✅ Sentry captura exceptions;
- ✅ Nenhum item P0 do checklist OWASP em aberto.

---

#### **Sprint 9 — Homologação com Fiscal-piloto (Sem 17: 29 dez - 11 jan 2027) · 2 semanas · 24h**

**Objetivo:** Manoel Costa (Fiscal-piloto) usa o sistema em 1 turno real e dá feedback.

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T9-01 | Treinamento Manoel Costa (presencial em Suape, 2h, com certificado) | 4h | — | Ata + fotos |
| T9-02 | Vídeo-aula de 3 min "Como usar a Lousa Digital" (Loom + PDF roteiro) | 2h | — | URL pública |
| T9-03 | Day 1: Manoel opera em 1 turno (08-16 ou 20-02) com Paulo acompanhando | 4h | T9-01 | Diário de bordo |
| T9-04 | Day 2-5: Manoel opera sozinho, Paulo on-call | 4h | T9-03 | Issues reportadas |
| T9-05 | Day 6-10: Manoel opera sozinho, Paulo só recebe alertas | 2h | T9-04 | Lista de bugs |
| T9-06 | Daily 15min com Manoel (resolução de issues) | 2h | T9-04 | — |
| T9-07 | Triagem e fix de bugs P0/P1 (corte de issue tracker) | 4h | T9-05 | Issues fechadas |
| T9-08 | Coleta de feedback qualitativo (NPS, 1:1) | 1h | T9-01 | Doc de feedback |
| T9-09 | Documentação `manual-fiscal.pdf` (10 páginas) | 1h | T9-01 | PDF no repo |

**Marco (M9):** "Homologação concluída" — Manoel Costa opera o sistema com confiança, sem Paulo ao lado.
**DoD:**
- ✅ Manoel fez 5+ remanejamentos sem ligar para Paulo;
- ✅ NPS ≥ 7 (escala 0-10);
- ✅ Zero bug P0 em aberto.

---

#### **Sprint 10 — Go-Live + Acompanhamento (Sem 18: 12-25 jan 2027) · 2 semanas · 18h**

**Objetivo:** produção aberta, comitiva do Sindicato + OGMO notificada.

| # | Atividade | Horas | Dependência | Entregável |
|---|---|---|---|---|
| T10-01 | Apresentação formal ao Josias + diretoria (1h, presencial ou videochamada) | 2h | T9-* | Ata + fotos |
| T10-02 | Carta formal ao OGMO/PE comunicando o sistema (em paralelo à entrada em operação) | 2h | — | AR |
| T10-03 | Go-Live: produção aberta para 100% dos fiscais do Suape | 2h | T8-* | Status page "All green" |
| T10-04 | Campanha de instalação do PWA (folder digital + abordagem em fila do cais) | 2h | T3-* | Métrica de instalação |
| T10-05 | Onboarding dos demais fiscais (1 turno cada, mesmo roteiro de Manoel) | 4h | T9-01 | Lista de fiscais onboarded |
| T10-06 | Reunião de apresentação ao MPT-PE (sem pedir nada, só mostrar — 1h) | 2h | — | Ata |
| T10-07 | Apresentação ao SINDOPE (Operadores Portuários) | 2h | — | Ata |
| T10-08 | Sprint review + retrospectiva + coleta de lições aprendidas | 2h | — | Doc `SPRINT-REVIEW-S10.md` |
| T10-09 | Documento final do projeto entregue ao Josias (`docs/ENTREGA-FINAL.md`) | 1h | — | PDF no repo |

**Marco (M10):** "Go-Live com Suape · Pronto para escalar"** — sistema em produção, fiscais operando, OGMO e MPT notificados.
**DoD:**
- ✅ 100% dos fiscais de Suape operando o sistema;
- ✅ ≥ 60% dos TPAs com PWA instalado (meta Fase 2: 80%);
- ✅ Apresentações a OGMO, MPT e SINDOPE realizadas;
- ✅ Documento de entrega aceito por Josias.

---

### 5.3 Resumo de esforço por sprint

| Sprint | Semanas | Horas Paulo | Status |
|---|---|---|---|
| Sprint 0 (Kickoff) | S0 | 12-16h | Não iniciado |
| Sprint 1 (Fundação) | S1-S2 | 36-40h | Não iniciado |
| Sprint 2 (Scraping) | S3-S4 | 40h | Não iniciado |
| Sprint 3 (PWA TPA) | S5-S6 | 40h | Não iniciado |
| Sprint 4 (Centro Comando) | S7-S8 | 40h | Não iniciado |
| Sprint 5 (Remanej + OGMO) | S9-S10 | 44h | Não iniciado |
| Sprint 6 (Auditoria + LGPD) | S11-S12 | 36h | Não iniciado |
| Sprint 7 (BI) | S13-S14 | 32h | Não iniciado |
| Sprint 8 (Hardening) | S15-S16 | 30h | Não iniciado |
| Sprint 9 (Homologação) | S17 | 24h | Não iniciado |
| Sprint 10 (Go-Live) | S18 | 18h | Não iniciado |
| **TOTAL Fase 1** | **18 semanas** | **~352-360h** | — |

**Média:** ~20h/semana (compatível com cenário parcial 50-60%, deixando espaço pros outros projetos Suporte Gerencial).

---

## 6. Estrutura analítica do projeto (WBS)

### 6.1 Épicos e features (nível 1)

| Épico | Código | Descrição | Fase | Esforço | HU geradas |
|---|---|---|---|---|---|
| Fundação | E1 | Repo, mono, infra, auth, RBAC, LGPD base | Fase 1 (S1-S2) | 76h | 12 HUs |
| Integração OGMO | E2 | Scraping TPA/Suape + EscalaNet/Recife + snapshots | Fase 1 (S3-S4) | 40h | 8 HUs |
| PWA do TPA | E3 | App mobile-first: escala, presença, histórico, perfil, push | Fase 1 (S5-S6) | 40h | 10 HUs |
| Centro de Comando | E4 | Web Fiscal: lousa, remanejamentos, OGMO, auditoria, BI | Fase 1 (S7-S8, S11-S14) | 112h | 22 HUs |
| Remanejamento + Notificação | E5 | Modal, hash chain, e-mail, PDF, webhook, painel OGMO | Fase 1 (S9-S10) | 44h | 9 HUs |
| LGPD | E6 | Consentimento, retenção, exclusão, DPO dashboard | Fase 1 (S11-S12) | 36h | 8 HUs |
| BI & Dashboards | E7 | KPIs, gráficos, ranking, export, insights | Fase 1 (S13-S14) | 32h | 7 HUs |
| Hardening | E8 | Segurança, performance, backup, monitoramento | Fase 1 (S15-S16) | 30h | 6 HUs |
| Homologação + Go-Live | E9 | Treinamento, day-in-the-life, apresentações, rollout | Fase 1 (S17-S18) | 42h | 4 HUs |
| **TOTAL Fase 1** | | | | **~452h** | **86 HUs** |

### 6.2 Exemplo de HU (template usado no repo)

```yaml
# HU-001: Login de Fiscal no Centro de Comando
id: HU-001
epico: E1
sprint: S1
prioridade: P0
status: ready

como: Fiscal do SINDESTIVA-PE
quero: Fazer login no Centro de Comando com e-mail e senha
para: Acessar a lousa espelhada e o módulo de remanejamentos

criterios_aceitacao:
  - dado que estou na tela /login
    quando preencho e-mail válido + senha correta
    então sou redirecionado para /lousa em < 2s
  - dado que preencho credenciais inválidas
    então vejo mensagem "Credenciais inválidas" e nada mais acontece
  - dado que faço 5 tentativas erradas em 5 minutos
    então minha conta é bloqueada por 15 minutos (rate limit)
  - a sessão expira em 8 horas
  - todo login é registrado em audit_log (hash chain)

regras_negocio:
  - RN-01: Fiscal precisa ter e-mail cadastrado pelo Dirigente (sem signup público)
  - RN-02: Senha mínima 12 caracteres, 1 maiúscula, 1 número, 1 símbolo

tarefas:
  - id: T1-04
    horas: 6
    tipo: backend
  - id: T1-05
    horas: 4
    tipo: backend
  - id: T1-08
    horas: 4
    tipo: frontend

estimativa_total: 14h
```

**Total de HUs do MVP:** **86 histórias** (estimadas, será feito detalhamento completo na fase de discovery dentro do Sprint 0).

---

## 7. Equipe, papéis e governança

### 7.1 Equipe (cenário realista: 1 dev + cliente)

| Papel | Quem | Dedicação | Responsabilidades |
|---|---|---|---|
| **Sponsor técnico + Dev full-stack** | **Paulo Siqueira** (Suporte Gerencial) | 50-60% (20h/sem) | Tudo: código, deploy, design, product owner, DPO |
| **Sponsor cliente** | **Josias Martins Santiago** (Presidente SINDESTIVA-PE) | 2-4h/mês | Decisões estratégicas, alinhamento político, carta ao OGMO |
| **Usuário-chave / Co-designer** | **Manoel Costa** (Fiscal-piloto de Suape) | 4h/semana nas semanas-chave | Testar, validar fluxos, treinar colegas |
| **Advogado trabalhista** | A definir (recomendação: rede Paulo) | 2-3h (one-shot) | Parecer LGPD + parecer de conformidade operacional |
| **DPO** | **Paulo Siqueira** (acumulado) | contínuo | Política de privacidade, atendimento a titulares |
| **Interlocutor OGMO/PE** | A identificar (carta a ser enviada) | 1-2h/mês | Receber e-mails, eventualmente prover endpoint webhook |
| **Contabilidade/Operação** | A definir (Tesoureiro SINDESTIVA) | eventual | Assinar pagamentos de infra |

**Recomendação:** considerar 1 **estagiário de TI** do SINDESTIVA-PE ou de faculdade local (UNINASSAU, UFPE) para suporte nível 1 aos fiscais a partir do Sprint 10. Custo: R$ 800-1.200/mês (auxílio + transporte), economiza 4-6h/sem do Paulo.

### 7.2 Estrutura de governança

| Fórum | Frequência | Participantes | Objetivo |
|---|---|---|---|
| **Daily async** (mensagem no grupo) | Diária | Paulo, Manoel (quando ativo) | Status de issues, bloqueios |
| **Weekly sync** (30 min) | Semanal | Paulo, Josias (opcional) | Progresso, decisões, riscos |
| **Sprint review** (1h) | A cada 2 semanas | Paulo, Josias, Manoel, fiscais | Demo do que foi entregue, feedback |
| **Retrospectiva** (30 min) | A cada 2 semanas | Paulo, Manoel | O que foi bem, o que melhorar |
| **Steering committee** (1h) | Mensal (a partir do S5) | Josias, Paulo, advogado (s/ LGPD) | Status macro, orçamento, riscos |
| **Apresentação externa** | 1x (Sprint 10) | OGMO, MPT, SINDOPE | Lançamento do sistema |

### 7.3 SLAs de comunicação

- **Bloqueio do Paulo:** resposta em < 4h úteis (grupo WhatsApp);
- **Pergunta do Manoel:** resposta em < 8h úteis;
- **Decisão do Josias:** até a próxima weekly sync (máx. 7 dias);
- **Incidente P0 (sistema fora):** notificação em < 15 min para Josias + Manoel.

---

## 8. Plano de comunicação com o cliente

### 8.1 Canais

| Canal | Uso | Acesso |
|---|---|---|
| **E-mail institucional** (`contato@sindestiva-pe.org.br`) | Comunicação formal, atas, contratos | Josias, Paulo |
| **WhatsApp grupo "Lousa Digital"** | Daily, quick questions, alertas | Josias, Manoel, fiscais, Paulo |
| **Reunião semanal** (Google Meet) | Weekly sync | Paulo + Josias |
| **Issue tracker público** (GitHub Projects) | Status de HUs, bugs, roadmap | Manoel, Josias (read), Paulo (write) |
| **Sprint review** (presencial ou Meet) | A cada 2 semanas | Todos os fiscais + diretoria |

### 8.2 Cadência de reportes

| Momento | Artefato | Audiência |
|---|---|---|
| Diário | Mensagem no grupo WhatsApp com top-3 do dia | Manoel, Josias |
| Semanal | E-mail "Status da Semana" (1 página: ✅ feito, 🔄 em curso, ⚠️ bloqueios) | Josias |
| A cada 2 semanas | Sprint review (demo ao vivo) | Manoel + fiscais + Josias |
| Mensal | Steering committee (1h) | Josias + Paulo + (advogado se LGPD) |
| Trimestral | Apresentação externa (OGMO, MPT, SINDOPE) | Stakeholders externos |

### 8.3 Templates de status

**Status Semanal (e-mail, 1 página):**
```
ASSUNTO: [Lousa Digital] Status Semanal — S5 (06-19/out)

1. ✅ FEITO
   - T3-07 Confirmação de presença funcional
   - T3-11 Lighthouse PWA score 92

2. 🔄 EM CURSO
   - T3-08 IndexedDB offline (em teste)

3. ⚠️ BLOQUEIOS
   - OGMO/PE ainda não respondeu a carta (S5-2)

4. PRÓXIMOS PASSOS
   - Sprint review sex 25/out às 10h
```

---

## 9. Critérios de aceite globais e KPIs de sucesso

### 9.1 Critérios de aceite do MVP (Definition of Done global)

Para que o MVP seja considerado **pronto para Go-Live**, **todos** os critérios abaixo precisam ser verdadeiros:

- [x] **Lousa oficial espelhada:** 100% das 26 colunas × 11 fainas × 2 turnos × 2 portos refletidas no Centro de Comando, com atualização < 60s.
- [x] **Remanejamento digital:** Fiscal remaneja 1 TPA com 1 motivo em **< 30 segundos**, com motivo, base legal, anexo opcional e confirmação.
- [x] **Notificação ao OGMO:** OGMO recebe e-mail formal com PDF e hash em **< 2 minutos** do remanejamento.
- [x] **PWA do TPA:** TPA consegue instalar, logar, ver escala do dia, confirmar presença, falar com o Fiscal via WhatsApp.
- [x] **Auditoria:** 100% das ações registradas em `audit_events` com hash chain íntegro (verificador diário passa).
- [x] **LGPD:** termo de consentimento exibido, retenção 24m automática, TPA pode pedir exclusão (Art. 18), DPO dashboard funcional.
- [x] **BI:** 4 dashboards funcionando com dados reais, export PDF/CSV.
- [x] **Performance:** p95 < 1s em todas as páginas com 50 usuários simultâneos.
- [x] **Segurança:** zero item P0 do checklist OWASP em aberto; rate limit ativo; backup testado; CORS/Helmet configurados.
- [x] **Homologação:** Manoel Costa opera o sistema em 1 turno real com NPS ≥ 7.
- [x] **Testes:** ≥ 200 testes verdes (unit + integration + E2E).
- [x] **Documentação:** manual do Fiscal, manual do TPA, manual do Presidente, runbook operacional, ADRs.
- [x] **Apresentação externa:** Josias, OGMO, MPT-PE e SINDOPE notificados formalmente.

### 9.2 KPIs de sucesso (monitorados pós Go-Live)

| KPI | Meta Sprint 10 (Go-Live) | Meta 90 dias pós Go-Live | Meta 180 dias |
|---|---|---|---|
| **% fiscais usando o sistema** | 100% (Suape) | 100% Recife também | 100% ambos portos |
| **Tempo médio de remanejamento** | < 30s (sistema) | < 20s | < 15s |
| **% remanejamentos com ACK do OGMO em < 5 min** | ≥ 80% | ≥ 90% | ≥ 95% |
| **% remanejamentos com e-mail entregue ao OGMO** | 100% | 100% | 100% |
| **% TPAs com PWA instalado (Suape)** | ≥ 30% | ≥ 60% | ≥ 80% |
| **NPS dos fiscais** | ≥ 7 | ≥ 8 | ≥ 8 |
| **NPS dos TPAs** | ≥ 6 | ≥ 7 | ≥ 8 |
| **Uptime do sistema** | ≥ 99% | ≥ 99,5% | ≥ 99,9% |
| **% hash chain íntegra** | 100% | 100% | 100% |
| **% conformidade LGPD** | 100% | 100% | 100% |
| **% respostas a pedidos de exclusão em 15 dias** | 100% | 100% | 100% |
| **Volume de remanejamentos com histórico** | 100% | 100% | 100% |
| **% atas/notificações formais extraídas em < 30s** | ≥ 95% | ≥ 99% | ≥ 99% |

### 9.3 Critérios de "fracasso" (rollback)

O Go-Live será revertido para o modo "rascunho / shadow" (e-mail continua sendo enviado, mas Fiscal volta a usar telefone para urgências) se:

- **F1:** OGMO/PE emitir notificação formal proibindo o sistema;
- **F2:** MPT-PE emitir recomendação expressa de não usar o sistema para remanejamentos;
- **F3:** 3+ fiscais reportarem que o sistema piora (vs. telefone) o tempo de remanejamento;
- **F4:** Bug P0 não resolvido em 48h úteis;
- **F5:** LGPD: TPAprocessar por uso indevido de dados (e houver risco real de procedência).

---

## 10. Riscos, mitigações e plano B

### 10.1 Matriz de riscos (atualizada do plano original)

| # | Risco | P | I | Mitigação | Plano B | Owner |
|---|---|---|---|---|---|---|
| R1 | OGMO/PE boicota a integração (não responde a carta, ignora e-mails) | **Alta** | **Alto** | E-mail + painel são unilaterais (não precisam de aprovação); OGMO é notificado, mas sistema funciona sem resposta | Considerar MPT como aliado (modelo Rio Grande); ir pra Opção B no roadmap | Paulo |
| R2 | TPA Tecnologia muda layout do TPA (AngularJS) | **Média** | **Alto** | Parser tolerante (regex fallback) + alerta de mudança em < 5 min + 2 implementadores | Scraper Playwright headful com fingerprint visual; trocar pra raspagem do listagem_turno (HTML mais simples) | Paulo |
| R3 | OGMO/PE processa o Sindicato por concorrência desleal | **Baixa** | **Alto** | Sistema **do Sindicato, em favor do Sindicato**, não comercializa sem acordo; parecer jurídico (T6-11) | Cessar uso, virar modelo Opção C (PWA só); oferecer ao OGMO como serviço | Josias + Advogado |
| R4 | MPT-PE vê como invasão de prerrogativa do OGMO | **Baixa** | **Alto** | Documentação desde dia 1; deixar claro que **não escala, replica e notifica**; carta formal no mês 1 (S10-02) | Reduzir escopo pra Opção C (só PWA) | Paulo + Josias |
| R5 | Resistência interna (fiscais não adotam) | **Média** | **Alto** | Manoel como co-designer (S9); treinamento 1:1 (T9-01); primeira vitória em 7 dias | Fiscal mais jovem como champion; pressão da diretoria | Josias |
| R6 | Josias muda de ideia no meio do caminho | **Baixa** | **Alto** | Aprovações escritas a cada sprint review; ata de kickoff (S0) com escopo travado | Pausar projeto, realocar Paulo para Becker/Córtex | Josias |
| R7 | Falta de tempo do Paulo (sobrecarga) | **Média** | **Alto** | Cronograma 50-60% parcial; S8 é Sprint 0 novamente se preciso | Cortar escopo: começar só pelo PWA (Opção C) e postergar Centro de Comando | Paulo |
| R8 | Córtex/Becker/FaceGate/Sinapse competem por tempo | **Alta** | **Alto** | Regra: este projeto **só anda em 18 semanas de 20h/sem**; depois volta pra fila; aviso prévio de 2 semanas | Pausar Lousa Digital, retomar 60-90 dias depois | Paulo |
| R9 | Indisponibilidade do Manoel Costa (doença, férias) | **Média** | **Médio** | 2º fiscal-piloto identificado no Sprint 0 (K-3) | Adiar homologação 1 sprint (sem grandes consequências) | Josias |
| R10 | LGPD: TPA não aceita termo e processo o Sindicato | **Baixa** | **Alto** | Termo escrito por advogado (T6-11); DPO dashboard (T6-08); política de exclusão (T6-07) | Oferecer exclusão imediata + carta explicativa + mediação | Paulo + Advogado |
| R11 | Indisponibilidade do advogado | **Baixa** | **Médio** | Contrato fechado no Sprint 0 (K-5); backup identificado (Nathalia Santos) | Adiar parecer 1 sprint, sem bloquear desenvolvimento | Josias |
| R12 | Servidor Hetzner cai (downtime > 4h) | **Baixa** | **Alto** | Backup off-site (T8-04); monitoramento 24/7 (T8-07); DRP (T8-09) | Escalar Easypanel como contingência | Paulo |
| R13 | Bug crítico em produção (sistema fora durante turno) | **Média** | **Alto** | Rollback automático (CI/CD); backup DB; modo de leitura (sistema cai, mas TPA continua vendo último snapshot) | Telefone/rádio tradicional (volta ao AS-IS) | Paulo |
| R14 | Falta de orçamento do Sindicato para a Fase 2 | **Média** | **Médio** | MVP completo já na Fase 1; Fase 2 opcional; sindicato pode continuar usando o MVP | Ficar só no MVP (Escopo da Fase 1 já gera valor) | Josias |
| R15 | Pleito eleitoral no Sindicato (mudança de diretoria) | **Média** | **Alto** | Aprovações escritas em ata; sistema é do Sindicato (não da diretoria atual); continuidade institucional | Pausar projeto até nova diretoria se posicionar | Josias |

### 10.2 Resumo por severidade

- **Risco Alto (5):** R1, R2, R3, R4, R5, R8, R13
- **Risco Médio (6):** R9, R11, R14, R15
- **Risco Baixo (4):** R6, R7, R10, R12

---

## 11. Orçamento e custos

### 11.1 Custos do MVP (Fase 0 + Fase 1)

| Item | Detalhamento | Valor | Tipo |
|---|---|---|---|
| **Mão de obra Paulo** | 360h × custo interno Suporte Gerencial | (custo interno) | Não-billable (sponsor técnico) |
| **Infraestrutura VPS Hetzner** | CPX31 (4 vCPU, 8GB RAM, 160GB SSD) | R$ 250/mês × 5m = R$ 1.250 | recorrente |
| **Domínio `lousa.pscode.ia.br`** | Registro + renovação anual | R$ 80/ano | one-shot |
| **Resend (e-mail)** | 3k/mês free tier; sob demanda até 50k/mês | R$ 0-20/mês | recorrente |
| **Firebase Cloud Messaging** | Push notifications | R$ 0 (free tier) | recorrente |
| **Sentry** | Monitoramento de exceptions | R$ 0 (free tier) | recorrente |
| **Uptime Kuma** | Self-hosted em VPS | R$ 0 | recorrente |
| **Advogado trabalhista** | Parecer LGPD (K-5) + parecer de conformidade (T6-11) | R$ 1.500 + R$ 1.500 = R$ 3.000 | one-shot |
| **Viagem Recife ↔ Suape** | 2 visitas (Kickoff + Homologação), 2 dias cada | R$ 1.500 (combustível/hospedagem) | one-shot |
| **Material de treinamento** | Impressos para fiscais + folder PWA | R$ 200 | one-shot |
| **Certificado SSL (Let's Encrypt)** | — | R$ 0 | recorrente |
| **TOTAL MVP (Fase 1)** | | **R$ 6.030** | — |

### 11.2 Custos anuais recorrentes (pós Go-Live)

| Item | Valor/mês | Valor/ano |
|---|---|---|
| VPS Hetzner | R$ 250 | R$ 3.000 |
| Domínio | R$ 7 | R$ 80 |
| Resend (acima de 3k e-mails) | R$ 20 | R$ 240 |
| Manutenção e pequenas evoluções (Paulo, 2h/sem) | (custo interno) | (custo interno) |
| **TOTAL recorrente ano 1** | **R$ 277** | **R$ 3.320** |

### 11.3 Custos da Fase 2 (estimativa)

| Item | Valor |
|---|---|
| BI avançado (ML, predição de faltas) | R$ 1.500 (infra adicional) |
| Integração Mercado Pago (contribuição sindical) | R$ 0 (já tem padrão Becker) |
| App nativo (opcional) | R$ 2.000 (build iOS) |
| SMS (fallback para TPAs sem WhatsApp) | R$ 300/mês × 4m = R$ 1.200 |
| **TOTAL Fase 2** | **R$ 4.700** |

### 11.4 Modelo de monetização (Fase 3, 12-18 meses)

**Premissa:** se o MVP virar case de sucesso, o modelo de replicação para outros 25+ OGMOs do Brasil abre receita recorrente.

| Cenário | 5 OGMOs × R$ 3k/mês | 10 OGMOs × R$ 5k/mês | 25 OGMOs × R$ 8k/mês |
|---|---|---|---|
| **ARR** | R$ 180k/ano | R$ 600k/ano | R$ 2,4M/ano |
| **Margem bruta** (60%) | R$ 108k | R$ 360k | R$ 1,44M |

Decisão sobre precificação fica para a Fase 3. No MVP, **não há cobrança** — o Sindicato é cliente-piloto, ganha o sistema em troca de ser case de sucesso e feedback.

---

## 12. Plano de Go-Live e rollout

### 12.1 Estratégia de rollout progressivo

```
Fase 1: Piloto (Sem 17)        → 1 fiscal (Manoel), 1 turno, 1 porto (Suape)
                                    ↓ valida fluxo, dá feedback
Fase 2: Suape completo (Sem 18) → 100% fiscais Suape, 100% turnos, PWA 30% TPA
                                    ↓ valida estabilidade, performance
Fase 3: Recife + Suape (Sem 22) → 100% fiscais, PWA 60% TPA, OGMO notificado
                                    ↓ Fase 2 do projeto
```

### 12.2 Plano de comunicação pré Go-Live

| Quando | Ação | Audiência | Mensagem |
|---|---|---|---|
| D-30 | Carta formal ao OGMO/PE | OGMO + ANTAQ | "Vamos iniciar operação. Sistema replica lousa, não escala. Pronto pra apresentar." |
| D-21 | Apresentação informal ao Fiscal-chefe | Manoel + fiscais Suape | Demo + convite pra ser piloto |
| D-14 | Treinamento Manoel (presencial) | Manoel | Manual + vídeo |
| D-7 | Sprint review final + Go/No-Go | Josias + Manoel | Decisão final de ir |
| D-1 | Status page verde + WhatsApp "amanhã" | Todos | "Sistema entra em operação amanhã" |
| D-Day | Go-Live 06:00 | Manoel, Paulo on-call | Manoel opera 1 turno real |
| D+7 | Revisão 1ª semana | Josias + Manoel | 1:1 feedback + ajustes |
| D+30 | Apresentação OGMO/PE | OGMO | "1 mês operando. Aqui estão os números." |

### 12.3 Critérios Go/No-Go (D-7)

- ✅ Manoel treinou e fez 5+ remanejamentos em ambiente de homologação
- ✅ Zero bug P0 em aberto
- ✅ k6 p95 < 1s
- ✅ Backup testado e restore validado
- ✅ Sentry configurado
- ✅ Parecer jurídico de LGPD em mãos
- ❌ Se qualquer item falhar: **NO-GO**, postergar 1-2 sprints

---

## 13. Pós-implantação e SLAs

### 13.1 SLAs de operação (pós Go-Live)

| Item | SLA | Medição |
|---|---|---|
| **Uptime do Centro de Comando** | 99,5% (mensal) | Uptime Kuma |
| **Latência scraping → DB** | < 5s p95 | Log de tempo |
| **Latência remanejamento → e-mail OGMO** | < 2 min p95 | Log + Resend |
| **Tempo de resposta a bug P0** | < 4h úteis | GitHub Issues |
| **Tempo de resposta a bug P1** | < 24h úteis | GitHub Issues |
| **Tempo de resposta a bug P2** | < 5 dias úteis | GitHub Issues |
| **Backup DB** | diário 03:00, retido 30d | Script |
| **Restore DR** | < 4h | Testado trimestralmente |
| **Renovação SSL** | auto via Traefik | Monitorado |

### 13.2 Plano de suporte (4 primeiros meses pós Go-Live)

| Atividade | Frequência | Horas/mês | Quem |
|---|---|---|---|
| On-call (Paulo, para P0/P1) | contínua | 2h | Paulo |
| Suporte a fiscais (Manoel ou estagiário) | diária | 8h | Manoel + estagiário |
| Pequenas melhorias (UI, copy, edge cases) | semanal | 4h | Paulo |
| Atualização de CCT (motivos, base legal) | sob demanda | 2h | Josias + Paulo |
| Verificação hash chain | diária 03:00 | automática | Sistema |
| **Total mensal pós Go-Live** | | **~16h** | — |

**Recomendação:** a partir do mês 4, abrir edital de **1 bolsista/estagiário** do SINDESTIVA-PE (8h/dia) para assumir o suporte nível 1, liberando Paulo para Fase 2.

### 13.3 Roadmap Fase 2 (Mar-Jun 2027) — apenas roadmap, fora do escopo deste documento

- BI avançado (preditivo de faltas);
- Integração Mercado Pago (contribuição sindical);
- SMS como fallback ao WhatsApp;
- App nativo (se PWA mostrar limitação crítica);
- ICP-Brasil A1 nos e-mails formais;
- Módulo de campanha de filiação;
- Onboarding Recife/EscalaNet oficialmente.

---

## 14. Dependências externas e pré-condições

### 14.1 Dependências críticas (que podem bloquear o cronograma)

| Dependência | Quem provê | Quando precisa | Bloqueio se faltar |
|---|---|---|---|
| **CCT 2024-2026 vigente** | Josias | Sprint 0 (K-2) | Sem CCT, motivos de remanejamento ficam sem base legal. Bloqueia T1-02, T5-02 |
| **Carta ao OGMO/PE** | Josias (com apoio Paulo) | Sprint 0 (K-7) | Sem carta,OGMO não sabe do sistema; risco político aumenta |
| **Parecer jurídico LGPD** | Advogado | Sprint 0 (K-5) | Sem parecer, módulo LGPD fica em risco; pode paralisar T6-* |
| **Lista de TPAs (mock ou real)** | Manoel Costa | Sprint 0 (K-3) | Sem lista, scraper não consegue cruzar matrículas |
| **Acesso à VPS Hetzner** | Suporte Gerencial (já tem) | Sprint 1 (T1-06) | — |
| **Domínio `lousa.pscode.ia.br`** | Suporte Gerencial (configurar) | Sprint 1 | — |
| **Acesso ao TPA Tecnologia** (carta) | Josias → OGMO → TPA Tecnologia | — | Não bloqueia (scraping é unilateral) |

### 14.2 Pré-condições contratuais

- **Contrato Suporte Gerencial ↔ SINDESTIVA-PE:** definir se é:
  - (a) Doação técnica (sistema entregue em troca de case de sucesso);
  - (b) Patrocínio (Sindicato paga infraestrutura);
  - (c) Investimento (Sindicato paga infra + parte das horas).
  - **Recomendação:** opção (b) para MVP (Sindicato paga ~R$ 6k de infra + viagem + jurídico; Suporte Gerencial investe as horas).
- **Cessão de imagem:** Josias, Manoel, fiscais e TPAs que aparecem em screenshots/vídeos precisam assinar termo de uso de imagem.
- **Propriedade intelectual:** código pertence à Suporte Gerencial; Sindicato tem direito de uso perpétuo.

### 14.3 Riscos de timing

- **Pleito eleitoral SINDESTIVA-PE:** confirmar se há eleição em 2026-2027 (se sim, congelar projeto em dezembro/novembro de 2026);
- **Festas de fim de ano:** Sprint 8 (15-28/12) tem 1 semana de recesso natural;
- **Carnaval 2027:** 14-17 fev 2027 — antecipar Go-Live pra antes ou postergar;
- **Recesso do OGMO/PE:** se houver, ajustar janela de comunicação.

---

## 15. Aprovações e governança contratual

### 15.1 Termo de aprovação do plano

```
Declaro que li, compreendi e aprovo o Plano de Implementação da Lousa Digital
para o SINDESTIVA-PE, conforme detalhado neste documento.

Aprovo o escopo do MVP (Fase 1), o cronograma de 18 semanas e o orçamento
estimado em R$ 6.030 para o ano 1.

Aprovo a composição da equipe (Suporte Gerencial como sponsor técnico +
SINDESTIVA-PE como sponsor cliente + Manoel Costa como usuário-chave) e a
alocação de 50-60% do tempo do sponsor técnico.

Confirmo a indicação do advogado trabalhista ____________________ para os
pareceres jurídicos necessários.

Nome: ______________________________________
Cargo: ______________________________________
SINDESTIVA-PE
Data: ___/___/2026
Assinatura: ______________________________________
```

### 15.2 Revisão do plano

Este documento será revisado a cada Sprint Review (a cada 2 semanas), com:
- Status atualizado de cada sprint;
- Atualização da matriz de riscos;
- Re-estimativa de horas se necessário;
- Mudanças de escopo (com aprovação formal do Josias).

Versões:
- **v1.0 (01/09/2026):** versão inicial para aprovação do Josias;
- v1.1 (15/09/2026): após feedback do kickoff;
- v1.2 (29/09/2026): após Sprint 1 (refinamento técnico);
- v2.0 (pós Go-Live): documento de aceitação final.

---

## 16. Anexos e referências

### 16.1 Documentos do projeto

| Documento | Path | Status |
|---|---|---|
| **Análise estratégica** (AS-IS, opções A·B·C) | `SINDESTIVA-PE-PLANO-2026-08-12.md` | ✅ Aprovado (interno) |
| **Protótipo navegável v0.1** | `SINDESTIVA-PE-PROTOTIPO.html` | ✅ Pronto |
| **Screenshots do protótipo** | `sindestiva-*.png` (7 arquivos) | ✅ Pronto |
| **Este plano de implementação** | `SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md` | 🆕 Aguardando aprovação |

### 16.2 Documentos a serem gerados durante a Fase 1

| Documento | Sprint | Local |
|---|---|---|
| Termo de consentimento LGPD (v1) | S0 (K-5) | `docs/LGPD/termo-v1.pdf` |
| Parecer jurídico LGPD | S0 (K-5) | `docs/LGPD/parecer-inicial.pdf` |
| CCT digitalizada | S0 (K-2) | `docs/CCT-2024-2026.pdf` |
| Diário de bordo visita Suape | S0 (K-4) | `docs/as-is-visita-suape.md` |
| Números reais levantados | S0 (K-3) | `docs/real-numbers.xlsx` |
| ADRs (decisões arquiteturais) | S1+ | `docs/ADR/` |
| Manual do Fiscal | S9 (T9-09) | `docs/manual-fiscal.pdf` |
| Manual do TPA | S3 (T3-13) | `docs/manual-tpa.pdf` |
| Manual do Presidente | S7 (T7-10) | `docs/manual-presidente.pdf` |
| Runbook operacional | S8 (T8-08) | `docs/RUNBOOK.md` |
| Documentação da API | S2+ | `docs/API.md` |
| DRP (Disaster Recovery Plan) | S8 (T8-09) | `docs/DRP.md` |
| Ata de kickoff | S0 (K-1) | `docs/ATAS/kickoff.md` |
| Atas de weekly sync | contínua | `docs/ATAS/` |
| Atas de sprint review | quinzenal | `docs/ATAS/sprint-reviews/` |
| Carta ao OGMO/PE | S0 (K-7) | `docs/COMUNICACAO/carta-ogmo.pdf` |
| Apresentação OGMO/PE | S10 (T10-02) | `docs/APRESENTACOES/ogmo.pdf` |
| Apresentação MPT-PE | S10 (T10-06) | `docs/APRESENTACOES/mpt.pdf` |
| Apresentação SINDOPE | S10 (T10-07) | `docs/APRESENTACOES/sindope.pdf` |
| Documento de entrega final | S10 (T10-09) | `docs/ENTREGA-FINAL.pdf` |

### 16.3 Referências externas (base de conhecimento)

- **Lei 8.630/93** (Lei dos Portos): https://www.planalto.gov.br/ccivil_03/leis/l8630.htm
- **Lei 12.815/13** (Nova Lei dos Portos): https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12815.htm
- **Lei 9.719/98** (Trabalho Portuário): https://www.planalto.gov.br/ccivil_03/leis/l9719.htm
- **LGPD** (Lei 13.709/18): https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- **Convenção 137 OIT** (Trabalho Portuário): https://www.ilo.org/brasilia/convencoes/WCMS_235878/lang--pt/index.htm
- **OGMO/PE — TPA:** http://tpa.ogmosuape.com.br
- **OGMO/PE — institucional:** https://www.ogmo-suape.com.br
- **OGMO Santos (referência):** "OGMO Santos Digital"
- **OGMO Rio Grande (referência TAC):** https://ogmo-rg.com.br
- **ANTAQ:** https://www.gov.br/antaq/
- **MPT-PE:** https://www.prt6.mpt.mp.br

### 16.4 Stack de referência (projetos Suporte Gerencial)

| Projeto | Stack | Repositório |
|---|---|---|
| **Córtex** | Next.js + TS + Prisma + Postgres + Turborepo | `contatopscode/cortex` |
| **Sinapse** | FastAPI + Python + Postgres (multi-tenant por schema) | `contatopscode/sinapse` |
| **FaceGate** | FastAPI + Python + Postgres + pgvector + Evolution API | `contatopscode/facegate` |
| **Becker** | Next.js + TS + Postgres + Mercado Pago | `contatopscode/becker` |

---

## Encerramento

Este documento é a **versão executiva** do projeto Lousa Digital, transformando a análise estratégica de 12/08/2026 e o protótipo navegável v0.1 em um **plano acionável, com cronograma, orçamento, equipe, governança e critérios de aceite** para envio ao cliente (Josias Martins Santiago) e para uso interno pela equipe.

**Próximos passos imediatos:**
1. Enviar este documento para Josias, pedir aprovação formal (semana 0);
2. Confirmar a data da reunião de kickoff (Sprint 0);
3. Providenciar advogado trabalhista (Cristiano Oliveira, Nathalia Santos ou equivalente) para o parecer LGPD;
4. Identificar Manoel Costa (ou outro fiscal-piloto) e agendar visita a Suape;
5. Configurar VPS Hetzner + domínio `lousa.pscode.ia.br` + repo `contatopscode/lousa-sindestiva` no GitHub;
6. Iniciar Sprint 0 imediatamente após aprovação.

---

*Documento gerado por Mavis em 01/09/2026 · versão v1.0 · aguardando aprovação de Josias Martins Santiago.*
