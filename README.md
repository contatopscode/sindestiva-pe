# SINDESTIVA-PE · Lousa Digital

> Plataforma web + PWA que digitaliza a lousa portuária do
> **SINDESTIVA-PE** (Sindicato dos Estivadores nos Portos de Pernambuco),
> o remanejamento operacional de TPA, a notificação formal ao OGMO/PE e o BI
> para a diretoria.

[![Sprint](https://img.shields.io/badge/Sprint-S0%20Kickoff-0a0e1a)](#status)
[![Stack](https://img.shields.io/badge/Stack-Turborepo%20%2B%20Next.js%2015%20%2B%20FastAPI-2b6cff)](#stack)
[![Status](https://img.shields.io/badge/Status-privado%20%28sem%20push%29-f5a623)](#status)

---

## Quick start (5 minutos)

### Pré-requisitos

- **Node.js 22+** (veja `.nvmrc`) e **pnpm 10+**
  ```bash
  corepack enable
  corepack prepare pnpm@10 --activate
  ```
- **Python 3.12+** (veja `.python-version`) — recomendo `pyenv`
- **Docker + Docker Compose** (para Postgres, Redis, Traefik, MailHog)
- **Playwright** (instala no Sprint 2 com `playwright install chromium`)

### 1. Clone e instale

```bash
git clone git@github.com:contatopscode/lousa-sindestiva.git
cd lousa-sindestiva
cp .env.example .env
# Edite .env: gere NEXTAUTH_SECRET com `openssl rand -base64 32`
pnpm install
```

### 2. Suba a infra (Postgres + Redis + Traefik + MailHog)

```bash
pnpm db:up
```

Endpoints locais:
- Postgres: `127.0.0.1:5433` (user: `sindestiva` / pass: `sindestiva` / db: `sindestiva`)
- Redis: `127.0.0.1:6380`
- Traefik dashboard: <http://localhost:8080>
- MailHog UI: <http://localhost:8025> (SMTP em `1025`)

> **Nota Mac do Paulo:** portas `5433` e `6380` evitam conflito com
> Postgres@18 (5432) e Redis (6379) do Homebrew. Conexão via `127.0.0.1`
> força IPv4.

### 3. Instale dependências Python

```bash
cd apps/api && pip install -e ".[dev]" && cd ../..
cd services/scraper && pip install -e ".[dev]" && cd ../..
```

### 4. Rode tudo

```bash
pnpm dev          # sobe web (3000) + pwa (3001) + api (8000) em paralelo
```

Abra:
- Centro de Comando: <http://localhost:3000>
- PWA TPA: <http://localhost:3001>
- API + Swagger: <http://localhost:8000/docs>

### 5. (Opcional) Suba o worker de scraping

```bash
pnpm dev:worker   # services/scraper
```

---

## Status

🆕 **Sprint 0 — Kickoff (01-07/09/2026)** · em curso

| Marco | Data | Entregável |
|---|---|---|
| **M0** | 07/09/2026 | Premissas validadas (CCT, advogado, Manoel, repo) |
| **M1** | 20/09/2026 | Centro de Comando autenticado |
| **M2** | 05/10/2026 | Demo executiva (lousa + remanejamento + PWA) |
| **M3** | 19/10/2026 | Homologação Manoel Costa |
| **M4** | 28/10/2026 | **GO-LIVE** (Suape) |

Veja o plano completo em [`SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md`](./SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md).

---

## Stack

- **Monorepo:** Turborepo + pnpm 10
- **Web:** Next.js 15 (App Router) + TypeScript 5 + Tailwind 4
- **PWA:** Next.js 15 PWA + Workbox + IndexedDB
- **API:** Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2
- **DB:** PostgreSQL 17 (schema `lousa_main`)
- **Cache:** Redis 7 (WebSocket + filas)
- **Scraping:** Playwright + BeautifulSoup + HTTPX
- **E-mail:** Resend · **PDF:** WeasyPrint · **BI:** Apache ECharts
- **Auth:** NextAuth v5 + JWT + Credentials + OTP WhatsApp (Evolution API)
- **CI/CD:** GitHub Actions + Easypanel + Hetzner CPX31

---

## Estrutura

```
sindestiva-pe/
├── apps/
│   ├── web/      # Centro de Comando (Next.js 15)
│   ├── pwa/      # PWA do TPA (Next.js 15 PWA)
│   └── api/      # FastAPI
├── packages/
│   ├── shared/   # Tipos TS compartilhados
│   └── ui/       # Componentes React
├── services/
│   └── scraper/  # Worker Python (FORA do Turborepo, cron 60s)
├── infra/
│   ├── docker-compose.yml
│   └── docker/
├── .github/workflows/ci.yml
├── AGENTS.md     # contexto para IAs e humanos
└── README.md     # este arquivo
```

Mais detalhes em [`AGENTS.md`](./AGENTS.md).

---

## Comandos úteis

```bash
# Dev
pnpm dev                  # tudo em paralelo
pnpm dev:web              # só Centro de Comando
pnpm dev:pwa              # só PWA TPA
pnpm dev:api              # só API
pnpm dev:worker           # só scraper

# Infra
pnpm db:up                # postgres + redis
pnpm db:down
pnpm db:reset             # apaga volumes
pnpm db:logs
pnpm infra:up             # tudo (incl. traefik + mailhog)
pnpm infra:down

# Qualidade
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e

# Limpeza
pnpm clean                # remove node_modules + .turbo
```

---

## Personas

- **Fiscal do Sindicato** (Manoel Costa, perfil-piloto) — opera a lousa, remaneja TPAs
- **Dirigente do Sindicato** (Josias Santiago) — presidente, usa o BI para CCT
- **TPA** (~2.000 em Recife + Suape) — usa o PWA pra ver escala do dia
- **TI do OGMO/PE** — recebe notificação formal (e-mail + PDF)
- **MPT-PE** — fiscaliza cumprimento da Lei 9.719/98, usa trilha de auditoria

---

## Links

- [Plano de implementação v1.0](./SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md) (1090 linhas, 18 sprints)
- [Cronograma 45 dias](./SINDESTIVA-PE-CRONOGRAMA-45DIAS.md) (cenário 100% Paulo)
- [Análise diagnóstica 12/08](./SINDESTIVA-PE-PLANO-2026-08-12.md) (AS-IS / opções A·B·C)
- [Protótipo HTML v0.1](./SINDESTIVA-PE-PROTOTIPO.html) (referência de UX)

---

## Licença

Proprietary · SINDESTIVA-PE / Suporte Gerencial · 2026
