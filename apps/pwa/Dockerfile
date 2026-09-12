# syntax=docker/dockerfile:1.7
# =============================================================================
# SINDESTIVA-PE · PWA Dockerfile (TPA)
#
# Multi-stage build pro Next.js 15 PWA + standalone output.
# Imagem final: ~150 MB. Inclui /sw.js (gerado por next-pwa em build).
#
# NOTA sobre next-pwa: ele gera public/sw.js e public/workbox-*.js DURANTE
# o `next build`. Como o output standalone copia `public/` no stage final,
# o SW vai junto na imagem.
#
# Decisões:
#  - Mesma estrutura do apps/web/Dockerfile (consistência).
#  - `output: 'standalone'` no next.config.mjs.
#  - `navigateFallback: '/'` — SW tenta fallback pra raiz.
# =============================================================================

# ----- Stage 1: deps -----
FROM node:22-alpine AS deps

ENV PNPM_HOME="/pnpm" \
    PATH="/pnpm:$PATH"
RUN corepack enable && corepack prepare pnpm@10 --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json ./
COPY apps/pwa/package.json ./apps/pwa/package.json
COPY packages/shared/package.json ./packages/shared/package.json
COPY packages/ui/package.json ./packages/ui/package.json

RUN pnpm install --frozen-lockfile --filter=@sindestiva/pwa...

# ----- Stage 2: builder -----
FROM deps AS builder

WORKDIR /app

COPY apps/pwa ./apps/pwa
COPY packages ./packages

# NEXT_PUBLIC_* é embutido no bundle no `next build` — precisa existir no builder.
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build: next-pwa gera sw.js + manifest.webmanifest dentro do .next/standalone
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm turbo run build --filter=@sindestiva/pwa...

# ----- Stage 3: runner -----
FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3001 \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0

RUN addgroup --system sindestiva-pwa \
    && adduser -D -H -u 1001 -G sindestiva-pwa sindestiva-pwa

# Standalone output (já inclui sw.js gerado por next-pwa em public/)
COPY --from=builder --chown=sindestiva-pwa:sindestiva-pwa /app/apps/pwa/.next/standalone ./
COPY --from=builder --chown=sindestiva-pwa:sindestiva-pwa /app/apps/pwa/.next/static ./apps/pwa/.next/static
COPY --from=builder --chown=sindestiva-pwa:sindestiva-pwa /app/apps/pwa/public ./apps/pwa/public

USER sindestiva-pwa
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3001/manifest.webmanifest || exit 1

CMD ["node", "apps/pwa/server.js"]
