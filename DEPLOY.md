# SINDESTIVA-PE · Guia de deploy (Coolify)

> Última atualização: **2026-09-12** · migração de Vercel+Render pra Coolify self-hosted.
>
> ⚠️ **Em migração** — Vercel/Render ainda ativos até Go-Live validar.

## Arquitetura alvo (TARGET — Coolify)

Redesign em andamento: **homologação (HOM) primeiro**, depois produção (PROD).
Checklist operacional: [`infra/coolify/README.md`](./infra/coolify/README.md).

| Aspecto | Homologação (`homolog`) | Produção (`production`) |
|---|---|---|
| **Branch Git** | `homolog` | `main` |
| **Environment Coolify** | `homolog` | `production` |
| **Domínios** | `api.hom.lousa.pscode.ia.br`, `web.hom.lousa…`, `pwa.hom.lousa…` | `api.lousa.pscode.ia.br`, `web.lousa…`, `pwa.lousa…` |
| **Banco / Redis** | Instâncias dedicadas no env HOM (não compartilhar com PROD) | Instâncias dedicadas no env PROD |

**Resources no Coolify (alvo):** um **Application** (ou Database) por componente — não um único Docker Compose:

1. `postgres` — Postgres 17 (`lousa_main`)
2. `redis` — Redis 7
3. `api` — FastAPI (`apps/api/Dockerfile`, porta **8000**)
4. `web` — Centro de Comando (`apps/web/Dockerfile`, porta **3000**)
5. `pwa` — PWA TPA (`apps/pwa/Dockerfile`, porta **3001**)

O serviço `scraper` do compose **não** entra no alvo: o loop de raspagem roda no **lifespan da API** (`apps/api/app/jobs/scraping_job.py`, iniciado em `app/main.py`). Logs de scraping → container **api**.

**Fases de migração**

| Fase | Entrega |
|---|---|
| **0** | Branch `homolog` no GitHub; documentação TARGET (este arquivo + `infra/coolify/`) |
| **1** | Coolify: projeto com env `homolog`; apps separados; deploy da branch `homolog` |
| **2** | DNS `*.hom.lousa.pscode.ia.br`; smoke tests (health, login, lousa) |
| **3** | Replicar stack no env `production` (branch `main`, domínios `*.lousa`) |
| **4** | Cutover: desativar Vercel/Render; webhooks `main` / `homolog` separados |
| **5** | Manter `infra/docker-compose.coolify.yml` só como **legado/fallback** local ou emergência |

## Arquitetura legado (fallback — Docker Compose único)

> **Status:** resource atual no Coolify (se existir) ou bootstrap rápido.
> **Não remover** `infra/docker-compose.coolify.yml` — referência e plano B.

```
                          ┌─────────────────────────────────┐
                          │      VPS Hetzner CPX31           │
                          │      Coolify 4.3.18 + Traefik    │
                          └────────────┬────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
            ▼                          ▼                          ▼
   ┌────────────────┐         ┌────────────────┐         ┌────────────────┐
   │  web (3000)    │         │  pwa (3001)    │         │  api (8000)    │
   │  Centro de     │         │  TPA PWA       │         │  FastAPI       │
   │  Comando       │         │                │         │  + migrations  │
   │  Next.js 15    │         │  Next.js 15    │         │  + seed        │
   │                │         │  PWA           │         │  + scraping loop (lifespan) │
   └───────┬────────┘         └────────┬───────┘         └───────┬────────┘
           │                          │                          │
           └──────────────────────────┼──────────────────────────┘
                                      │ HTTPS (Traefik + Let's Encrypt)
                                      ▼
                          ┌─────────────────────────────────┐
                          │   postgres (5432) · redis (6379)│
                          │   schema: lousa_main            │
                          └─────────────────────────────────┘
```

## URLs em produção

| Serviço | URL (Coolify) | Domínio custom |
|---|---|---|
| **API** | `https://<uuid>.2.25.218.138.sslip.io` | `api.lousa.pscode.ia.br` |
| **Web** | `https://<uuid>.2.25.218.138.sslip.io` | `web.lousa.pscode.ia.br` |
| **PWA** | `https://<uuid>.2.25.218.138.sslip.io` | `pwa.lousa.pscode.ia.br` |

> Coolify gera URL temporária `<uuid>.2.25.218.138.sslip.io` automaticamente.
> Pra usar domínios custom (`*.lousa.pscode.ia.br`), adicione FQDN no painel
> do resource (ver Passo 4 abaixo).

## Passo-a-passo

### 1. Criar projeto no Coolify

1. Acesse `http://2.25.218.138:8000`
2. **+ New Project** → Name: `SINDESTIVA-PE`, Description: `Lousa Digital · SINDESTIVA-PE`
3. **Alvo:** dois environments — `homolog` (branch `homolog`) e `production` (branch `main`).
4. **Legado (abaixo):** um único environment `production` + 1 resource Docker Compose.

### 2. Legado — 1 resource (Docker Compose)

No projeto criado (modo fallback, ver seção TARGET):

1. **+ New Resource** → tipo **"Docker Compose"** (não "Application")
2. **Source**: GitHub App (Coolify já tem) ou HTTPS + PAT (se repo privado)
   - **Repo**: `contatopscode/sindestiva-pe`
   - **Branch**: `main`
3. **Build Pack**: `dockercompose`
4. **Docker Compose Location**: `/infra/docker-compose.coolify.yml`
5. **Coolify clona o repo** + gera rede + injeta labels Traefik

> Se Coolify não conseguir clonar o repo privado, adicione PAT:
> Settings → Git → GitHub App → Authorize. Ou use HTTPS com token:
> URL: `https://<PAT>@github.com/contatopscode/sindestiva-pe.git`

### 3. Configurar env vars (Secrets)

Coolify lê o `.env` do resource. Crie `/data/coolify/proxy/sindestiva.env` (ou use UI Environment Variables):

```bash
# ----- Segurança -----
NEXTAUTH_SECRET=$(openssl rand -base64 32)        # JWT do NextAuth
ADMIN_SEED_TOKEN=$(openssl rand -base64 32)       # token admin pra /api/v1/admin/*
POSTGRES_PASSWORD=$(openssl rand -base64 24)       # senha forte do Postgres

# ----- Domínios -----
NEXTAUTH_URL=https://web.lousa.pscode.ia.br
NEXT_PUBLIC_API_URL=https://api.lousa.pscode.ia.br
CORS_ORIGINS=https://web.lousa.pscode.ia.br,https://pwa.lousa.pscode.ia.br

# ----- Banco -----
POSTGRES_USER=sindestiva
POSTGRES_DB=sindestiva
TZ=America/Recife

# ----- E-mail (Resend) -----
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM=SINDESTIVA-PE <noreply@pscode.ia.br>
OGMO_EMAIL=ogmo@pe.gov.br
OGMO_WEBHOOK_URL=

# ----- WhatsApp (Evolution API) -----
EVOLUTION_API_URL=https://evolution-evolution-api.vcli1q.easypanel.host
EVOLUTION_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EVOLUTION_INSTANCE=sindestiva

# ----- Push (FCM) -----
FCM_PROJECT_ID=sindestiva-push
FCM_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
FCM_CLIENT_EMAIL=firebase-adminsdk@sindestiva-push.iam.gserviceaccount.com

# ----- Scraper -----
SCRAPER_TPA_USERNAME=
SCRAPER_TPA_PASSWORD=
SCRAPER_ESCALANET_BASE_URL=http://www.ogmo-recife.org.br/EscalaNet
SCRAPER_INTERVAL_SECONDS=60

# ----- Sentry (opcional) -----
SENTRY_DSN=

# ----- Ambiente -----
APP_ENV=production
LOG_LEVEL=info
```

### 4. Configurar FQDNs (SSL automático)

Pra cada um dos 3 serviços públicos (api, web, pwa), adicione FQDN no Coolify:

1. Abra o resource
2. Settings → **Domains**
3. **Add Domain**:
   - API: `api.lousa.pscode.ia.br` (porta interna 8000)
   - Web: `web.lousa.pscode.ia.br` (porta interna 3000)
   - PWA: `pwa.lousa.pscode.ia.br` (porta interna 3001)
4. ✅ **Generate SSL** (Let's Encrypt via DNS-01 challenge do Cloudflare)

### 5. DNS no Cloudflare

Adicione/atualize CNAMEs:

| Tipo | Nome              | Valor                                  |
|------|-------------------|----------------------------------------|
| CNAME| `api.lousa`       | `2.25.218.138` (DNS-only, sem proxy)  |
| CNAME| `web.lousa`       | `2.25.218.138`                         |
| CNAME| `pwa.lousa`       | `2.25.218.138`                         |

> **DNS-only (nuvem cinza)** porque Coolify/Traefik gerencia SSL direto.
> Se deixar "Proxied" (nuvem laranja), Cloudflare interfere nos certs.

### 6. Deploy!

1. **Deploy** no painel do Coolify
2. Acompanhe os logs (`/data/coolify/.../logs/`)
3. Primeira execução:
   - Build das 5 imagens (web, pwa, api, scraper)
   - Postgres + Redis sobem
   - API roda `alembic upgrade head` + `seed_initial.py`
   - Web/PWA conectam na API
   - SSL é emitido (~30s)

### 7. Webhook GitHub (deploy automático)

Coolify gera webhook URL automaticamente (em Settings → Webhooks). Adicione no GitHub:

1. GitHub repo → Settings → Webhooks → **Add webhook**
2. **Payload URL**: `https://2.25.218.138:8000/api/v1/deploy/webhook/<uuid>/<token>`
3. **Content type**: `application/json`
4. **Events**: `Push` — no alvo, webhook em `main` (PROD) e outro em `homolog` (HOM)
5. ✅ Active

Push na branch configurada no resource → Coolify rebuilda automaticamente.

## Pós-deploy — verificação

```bash
# 1. API health
curl https://api.lousa.pscode.ia.br/health
# → {"aplicacao":"SINDESTIVA","status":"ok"}

# 2. Web carrega
curl -I https://web.lousa.pscode.ia.br
# → HTTP/2 200

# 3. PWA manifest
curl https://pwa.lousa.pscode.ia.br/manifest.webmanifest | jq
# → {"name":"Lousa Digital · TPA",...}

# 4. Scraping rodando (orquestração real = container `api`, NÃO `scraper`)
# Coolify → api service → Logs (structlog)
# Esperado a cada ~SCRAPER_INTERVAL_SECONDS (default 60):
#   scraping_job.ciclo_inicio → scraping_job.execucao (TPA+ESCALANET × DIURNO+NOTURNO)
#   scraping_service.upsert_escala_origem ... celulas=N ...
# Status público (sem auth):
curl -sS "https://api.lousa.pscode.ia.br/api/v1/scraping/status?limit=8" | jq '.total,.sucessos,.falhas'
# Lousa espelhada (sem auth):
curl -sS "https://api.lousa.pscode.ia.br/api/v1/lousa/public/preview?porto=RECIFE&turno=DIURNO" | jq '.snapshot,.stats.total_cells'
# Disparo manual (1 fonte × porto × turno):
curl -sS -X POST "https://api.lousa.pscode.ia.br/api/v1/scraping/disparar" \
  -H "Content-Type: application/json" \
  -d '{"fonte":"TPA","porto":"SUAPE","turno":"DIURNO"}'
# NOTA: o serviço `scraper` no compose ainda é placeholder Sprint 0
# (sindestiva-scraper só loga e sai). Ver services/scraper/README.md.

# 5. Login funciona
curl -X POST https://api.lousa.pscode.ia.br/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"paulo@pscode.ia.br","password":"sindestiva-dev-2026"}'
# → {"access_token":"...", ...}
```

## Custos (estimativa VPS)

| Serviço | Free tier | Custo (Hetzner CPX31) |
|---|---|---|
| VPS Coolify | — | ~R$ 100/mês (CPX31 4GB RAM) |
| Domínios | — | R$ 0 (Cloudflare free) |
| Resend (3k e-mails) | ✅ free | — |
| Evolution API | ✅ self-hosted (separado) | — |
| **Total MVP** | **~R$ 100/mês** | (vs ~R$ 80/mês Vercel+Render) |

Vantagem: custo fixo, sem surpresa de "free tier expirou".

## Pendências pós-deploy

- [ ] **Backup automático do Postgres**: `docker exec` + `pg_dump` cron (volumes Coolify)
- [ ] **Monitoramento**: Sentry SDK + alertas Discord/WhatsApp quando scraping falha
- [ ] **CORS**: confirmar `allow_origins` aceita os 2 domínios custom
- [ ] **Cookie domain**: ajustar `cookieOpts.domain=.pscode.ia.br` em produção (já feito em `apps/web/src/app/...`)
- [ ] **Rate limiting**: Traefik middleware ou FastAPI dependency

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| Build falha em `pnpm install` | Repo privado + sem PAT | Adicionar token GitHub no Coolify |
| `api` unhealthy após deploy | Migrations falharam | Ver logs do `api`; `alembic upgrade head` manual via Shell |
| 502 Bad Gateway | SSL não emitido ainda | Esperar 30-60s após primeiro deploy |
| Cookie não persiste entre domínios | Domain não é `.pscode.ia.br` | Configurar `cookieOpts.domain` no backend |
| Scraping TPA/Suape falha | Playwright sem Chromium | Verificar Dockerfile do scraper tem `libnss3` etc |
| EscalaNet/Recife 100% falha | DNS morto (escalanet.recife.gov.br) | P0.2 — feature flag pra desligar |
