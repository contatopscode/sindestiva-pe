# syntax=docker/dockerfile:1.7
# =============================================================================
# SINDESTIVA-PE · Web Dockerfile (Centro de Comando)
#
# Multi-stage build pro Next.js 15 standalone output.
# Imagem final: ~150 MB (vs ~1 GB se copiasse .next inteiro).
#
# Decisões:
#  - `node:22-alpine` (matches .nvmrc = 22).
#  - `output: 'standalone'` no next.config.mjs gera server.js + .next/static
#    separadamente — copiamos só o necessário pra imagem final.
#  - Usuário não-root (`nextjs` uid 1001) — hardening básico.
#  - Health check via wget (Alpine não tem curl).
#  - Standalone copia `node_modules` filtrado — não precisamos do pnpm na final.
# =============================================================================

# ----- Stage 1: deps (cache layer) -----
FROM node:22-alpine AS deps

ENV PNPM_HOME="/pnpm" \
    PATH="/pnpm:$PATH"
RUN corepack enable && corepack prepare pnpm@10 --activate

WORKDIR /app

# Copia manifestos do monorepo PRIMEIRO (cache: deps só mudam se mudar)
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/shared/package.json ./packages/shared/package.json
COPY packages/ui/package.json ./packages/ui/package.json

# Instala deps do workspace web (com deps transitivas dos packages)
RUN pnpm install --frozen-lockfile --filter=@sindestiva/web...

# ----- Stage 2: builder -----
FROM deps AS builder

WORKDIR /app

# Copia código fonte
COPY apps/web ./apps/web
COPY packages ./packages

# Build via Turbo (respeita cache config do turbo.json)
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm turbo run build --filter=@sindestiva/web...

# ----- Stage 3: runner (imagem final, mais enxuta) -----
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0

# Cria usuário não-root
RUN addgroup --system sindestiva-web \
    && adduser -D -H -u 1001 -G sindestiva-web sindestiva-web

# Copia output standalone (server.js + node_modules filtrado)
COPY --from=builder --chown=sindestiva-web:sindestiva-web /app/apps/web/.next/standalone ./
COPY --from=builder --chown=sindestiva-web:sindestiva-web /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=sindestiva-web:sindestiva-web /app/apps/web/public ./apps/web/public

USER sindestiva-web
EXPOSE 3000

# Health check (Alpine não tem curl; wget vem built-in)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3000/ || exit 1

CMD ["node", "apps/web/server.js"]
