# SINDESTIVA-PE · Guia de deploy (Vercel + Render)

> Última atualização: 05/09/2026 · mesmo padrão usado em **Sinapse** (Suporte
> Gerencial, deploy em Vercel + Render).

## Arquitetura de produção

```
                          ┌─────────────────────────────────┐
                          │         VERCEL (frontend)       │
                          │   apps/web   → web.lousa.pscode │
                          │   apps/pwa   → pwa.lousa.pscode │
                          └────────────┬────────────────────┘
                                       │ HTTPS / JSON
                                       │ NEXT_PUBLIC_API_URL
                                       ▼
                          ┌─────────────────────────────────┐
                          │         RENDER (backend)         │
                          │  apps/api (Web Service)          │
                          │  services/scraper (Worker)       │
                          │  sindestiva-db (Postgres)        │
                          │  sindestiva-redis (Key Value)    │
                          └─────────────────────────────────┘
                                       ▲
                          ┌────────────┴────────────────────┐
                          │  TPA Tecnologia (SUAPE) — scraper│
                          │  Evolution API (WhatsApp)        │
                          │  Resend (e-mail OGMO)            │
                          │  FCM (push TPA)                  │
                          └─────────────────────────────────┘
```

## Domínios (post-deploy)

| Subdomínio              | Hospedagem | Serviço       |
|-------------------------|------------|---------------|
| `web.lousa.pscode.ia.br`| Vercel     | `apps/web`    |
| `pwa.lousa.pscode.ia.br`| Vercel     | `apps/pwa`    |
| `api.lousa.pscode.ia.br`| Render     | `apps/api`    |

URL padrão Render (antes de domínio custom): `https://sindestiva-api.onrender.com`.

## Passo-a-passo

### 1. Render (backend + infra)

1. Acesse https://dashboard.render.com/blueprints
2. **New Blueprint Instance** → conecte o repo `contatopscode/sindestiva-pe`
3. Render lê o `render.yaml` na raiz e provisiona:
   - `sindestiva-db` (Postgres, free 90d)
   - `sindestiva-redis` (Key Value, free permanente)
   - `sindestiva-api` (Web Service, free com cold start)
   - `sindestiva-scraper` (Background Worker, free permanente)
4. **Antes de aplicar**, configure as env vars sensitive via UI (depois do
   primeiro apply, em `Environment → Environment Variables`):
   - `EVOLUTION_API_KEY` — chave da Evolution API em `evolution-evolution-api.vcli1q.easypanel.host`
   - `RESEND_API_KEY` — criar conta em https://resend.com (free 3k/mês)
   - `FCM_PROJECT_ID`, `FCM_PRIVATE_KEY`, `FCM_CLIENT_EMAIL` — service account Firebase
   - `SENTRY_DSN` — opcional, monitoramento de erros
5. Após deploy da API, copiar a `connectionString` do Postgres e a `redisUrl`
   do Key Value. **Note o `external DATABASE URL`** para usar no Vercel
   (Vercel não acessa a rede interna do Render).
6. **Domínio custom** (opcional): em `sindestiva-api → Settings → Custom Domains`,
   adicionar `api.lousa.pscode.ia.br`. Render gera cert TLS automático via Let's Encrypt.
7. **Rodar migrations**: na primeira vez, abrir o Shell do `sindestiva-api` e rodar:
   ```bash
   uv run alembic upgrade head
   ```
   (Render expõe Shell no plano pago; no free, usar `render.yaml` `startCommand`
   custom ou um job de migrations separado — ver TODO abaixo.)

### 2. Vercel (frontend)

#### 2.1. `sindestiva-web` (Centro de Comando)

1. https://vercel.com/new → Importar `contatopscode/sindestiva-pe`
2. **Project Name**: `sindestiva-web`
3. **Framework Preset**: Next.js (auto-detectado)
4. **Root Directory**: `apps/web` (configurar manualmente — Vercel não
   detecta monorepos por padrão)
5. **Build Command** (vem do `vercel.json`): `cd ../.. && pnpm install --frozen-lockfile && pnpm turbo run build --filter=@sindestiva/web...`
6. **Environment Variables** (Production):
   - `NEXT_PUBLIC_API_URL` = `https://api.lousa.pscode.ia.br` (ou `https://sindestiva-api.onrender.com` até configurar domínio)
   - `NEXTAUTH_SECRET` = mesmo do Render (gerado por `openssl rand -base64 32`)
   - `NEXTAUTH_URL` = `https://web.lousa.pscode.ia.br`
7. **Domains** (Settings → Domains): adicionar `web.lousa.pscode.ia.br`

#### 2.2. `sindestiva-pwa` (TPA App)

Repetir o processo acima com:
- **Project Name**: `sindestiva-pwa`
- **Root Directory**: `apps/pwa`
- **NEXTAUTH_URL** = `https://pwa.lousa.pscode.ia.br`
- **Domains**: `pwa.lousa.pscode.ia.br`

### 3. DNS

Adicionar no Cloudflare (zona `pscode.ia.br`):

| Tipo | Nome              | Valor                            |
|------|-------------------|----------------------------------|
| CNAME| `web.lousa`       | `cname.vercel-dns.com`           |
| CNAME| `pwa.lousa`       | `cname.vercel-dns.com`           |
| CNAME| `api.lousa`       | `sindestiva-api.onrender.com`    |

(Vercel gera o CNAME exato depois do primeiro deploy — copiar de
`Project → Settings → Domains`.)

## Pós-deploy — verificação

```bash
# 1. API health
curl https://api.lousa.pscode.ia.br/health
# → {"aplicacao": "SINDESTIVA", "status": "ok"}

# 2. Web carrega
curl -I https://web.lousa.pscode.ia.br
# → HTTP/2 200

# 3. Scraper está rodando
# Render Dashboard → sindestiva-scraper → Logs
# Esperado: "scraping_service.upsert_escala_origem celulas=226 ..."

# 4. DB tem dados
psql $DATABASE_URL -c "SELECT COUNT(*) FROM lousa_main.lousa_alocacao;"
# → 226 (depois de 1 ciclo do scraper)
```

## Custos (free tier)

| Serviço              | Free tier                 | Custo se exceder |
|----------------------|---------------------------|------------------|
| Vercel (2 projetos)  | Ilimitado p/ hobby        | $20/mês por seat |
| Render Postgres      | 90 dias, 1GB              | $7/mês após 90d  |
| Render Key Value     | 25MB, permanente          | $10/mês p/ 1GB   |
| Render Web Service   | 750h/mês, sleep após 15min| $7/mês p/ starter |
| Render Worker        | 750h/mês, permanente      | $7/mês p/ starter |
| Resend               | 3k e-mails/mês            | $20/mês p/ 50k   |
| Evolution API        | Self-hosted (Sem custo)   | —                |
| **Total MVP**        | **R$ 0/mês (free 90d)**   | **~$40/mês**     |

## Pendências pós-deploy

- [ ] **Migrations Alembic em produção**: criar um `sindestiva-migrations` Job
  no Render que roda `alembic upgrade head` antes da API subir. Alternativa:
  usar `releaseCommand` no `render.yaml` (executa antes do CMD).
- [ ] **Domínios customizados**: configurar após primeiro deploy.
- [ ] **Backup automático do Postgres**: Render faz daily snapshot ($1/GB/mês).
- [ ] **CORS**: ajustar `allow_origins` no FastAPI para aceitar `web.lousa.pscode.ia.br`
  e `pwa.lousa.pscode.ia.br` (e Vercel preview URLs em dev).
- [ ] **Monitoramento**: Sentry SDK já está nas deps, só falta `SENTRY_DSN`.

## Troubleshooting

| Sintoma                                       | Causa provavel                    | Fix |
|-----------------------------------------------|-----------------------------------|-----|
| `sindestiva-api` 502                          | Cold start (free tier sleep)      | Primeiro request após 15min demora ~30s |
| `psycopg.OperationalError: connection refused`| `DATABASE_URL` errado             | Verificar `sindestiva-db` connectionString no Render |
| `redis.exceptions.ConnectionError`            | `REDIS_URL` errado                | Verificar `sindestiva-redis` redisUrl |
| `next-auth` JWT inválido entre web e api      | `NEXTAUTH_SECRET` diferente       | Mesmo secret em Render + Vercel |
| CORS bloqueia                                 | Origin não está em `allow_origins`| Adicionar domínio custom à config do FastAPI |
