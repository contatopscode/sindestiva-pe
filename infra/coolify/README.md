# Coolify · checklist SINDESTIVA-PE

> Complemento do [`DEPLOY.md`](../../DEPLOY.md) (seção **Arquitetura alvo**).
> HOM antes de PROD · branch `homolog` · apps separados.

## Projeto Coolify

- [ ] Projeto `SINDESTIVA-PE` com environments `homolog` e `production`
- [ ] HOM: source Git → branch **`homolog`**
- [ ] PROD: source Git → branch **`main`**
- [ ] Webhooks GitHub separados por branch (deploy automático)

## Applications / databases (por environment)

| Componente | Tipo sugerido | Build / imagem | Porta exposta | FQDN (exemplo HOM) | FQDN (exemplo PROD) |
|---|---|---|---|---|---|
| Postgres | Database ou app `postgres:17-alpine` | imagem oficial + `infra/postgres/init.sql` | 5432 (interno) | — | — |
| Redis | App `redis:7-alpine` | imagem oficial | 6379 (interno) | — | — |
| API | Application (Dockerfile) | `apps/api/Dockerfile` · contexto = **raiz do repo** | **8000** | `api.hom.lousa.pscode.ia.br` | `api.lousa.pscode.ia.br` |
| Web | Application | `apps/web/Dockerfile` · contexto = raiz | **3000** | `web.hom.lousa.pscode.ia.br` | `web.lousa.pscode.ia.br` |
| PWA | Application | `apps/pwa/Dockerfile` · contexto = raiz | **3001** | `pwa.hom.lousa.pscode.ia.br` | `pwa.lousa.pscode.ia.br` |

- [ ] Rede interna: API resolve `postgres` e `redis` pelos hostnames do Coolify (ajustar `DATABASE_URL_*` / `REDIS_URL`)
- [ ] **Não** publicar FQDN para Postgres/Redis
- [ ] **Não** deployar `services/scraper` no alvo — scraping no **lifespan da API**

## Variáveis de ambiente (nomes — sem valores)

Copiar por app; valores em secrets do Coolify (nunca commitar).

### Postgres (resource DB)

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `TZ`

### Redis

- `TZ` (opcional)

### API (`api`)

- `DATABASE_URL_ASYNC`, `DATABASE_URL_SYNC`
- `REDIS_URL`
- `NEXTAUTH_SECRET`, `NEXTAUTH_URL`
- `CORS_ORIGINS`
- `ADMIN_SEED_TOKEN`
- `RESEND_API_KEY`, `RESEND_FROM`, `OGMO_EMAIL`, `OGMO_WEBHOOK_URL`
- `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE`
- `FCM_PROJECT_ID`, `FCM_PRIVATE_KEY`, `FCM_CLIENT_EMAIL`
- `SCRAPER_TPA_USERNAME`, `SCRAPER_TPA_PASSWORD`, `SCRAPER_ESCALANET_BASE_URL`
- `SENTRY_DSN` (opcional)
- `APP_ENV`, `LOG_LEVEL`, `TZ`

### Web (`web`)

- `NEXT_PUBLIC_API_URL` → URL pública da API do mesmo environment
- `NEXTAUTH_SECRET`, `NEXTAUTH_URL` → URL pública do **web**
- `NODE_ENV`, `HOSTNAME`, `PORT` (`3000`)

### PWA (`pwa`)

- `NEXT_PUBLIC_API_URL`
- `NODE_ENV`, `HOSTNAME`, `PORT` (`3001`)

## DNS (Cloudflare)

- [ ] HOM: `api` / `web` / `pwa` → `*.hom.lousa.pscode.ia.br` (DNS-only, sem proxy laranja)
- [ ] PROD: `api` / `web` / `pwa` → `*.lousa.pscode.ia.br`

## Pós-deploy (smoke)

- [ ] `GET /health` na API
- [ ] Login fiscal (web → API)
- [ ] Centro de Comando carrega lousa (scraping: logs do container **api**, não worker separado)

## Legado

- [ ] `infra/docker-compose.coolify.yml` permanece no repo (compose único, inclui serviço `scraper` opcional)
- [ ] Usar só para bootstrap local ou emergência se o modelo multi-app falhar
