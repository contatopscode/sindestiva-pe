# @sindestiva/pwa

> PWA do TPA — SINDESTIVA-PE · Next.js 15 + next-pwa
>
> **Status:** Sprint 0 (PWA stub) + P0.5 entregue (instalável).
> Sprint 3 (P0.3) implementa as 4 abas + login.

---

## Rodar localmente

```bash
# Pré-requisitos verificados no monorepo raiz:
#   - Node 22+ (.nvmrc)
#   - pnpm 10+ (corepack enable && corepack prepare pnpm@10 --activate)
#   - API rodando em http://localhost:8000 (ou NEXT_PUBLIC_API_URL apontando
#     pra staging/prod — apps/pwa/page.tsx usa o .onrender.com como default)

pnpm dev:pwa    # sobe só o PWA em http://localhost:3001
pnpm dev        # sobe web + pwa + api em paralelo (do monorepo raiz)
```

Em dev, o **service worker é desabilitado** (`disable: NODE_ENV === "development"` no `next.config.mjs`) pra evitar HMR quebrado. Em prod (`pnpm build && pnpm start`), `sw.js` + `manifest.webmanifest` são gerados via Workbox.

---

## Regenerar ícones

Os ícones PNG são gerados a partir dos SVGs fonte via **ImageMagick**:

```bash
cd apps/pwa/public

# Ícone padrão (192, 512, apple-touch 180, favicon 32)
convert -background none -density 300 -resize 192x192 icon-source.svg icon-192.png
convert -background none -density 300 -resize 512x512 icon-source.svg icon-512.png
convert -background none -density 300 -resize 180x180 icon-source.svg apple-touch-icon.png
convert -background none -density 300 -resize 32x32   icon-source.svg favicon.ico

# Ícone maskable (Android 12+ adaptive — safe zone 80%)
convert -background none -density 300 -resize 512x512 icon-maskable-source.svg maskable-icon-512.png
```

### Paleta de cores

| Token | Hex | Uso |
|---|---|---|
| `--bg-deep` | `#061321` | Fundo gradiente (bottom) |
| `--bg-base` | `#0a1929` | Theme color do PWA + body |
| `--accent-gold` | `#d4a574` | Âncora + accents |

> Mudar a paleta exige atualizar **3 lugares**: `globals.css` (variáveis CSS), `viewport.themeColor` em `layout.tsx`, e `manifest.ts` (`background_color` + `theme_color`).

---

## Testar offline

1. `pnpm build && pnpm start` (service worker só liga em prod)
2. Abrir `http://localhost:3001` no Chrome
3. DevTools → Application → Service Workers → confirmar `sw.js` registrado
4. DevTools → Network → marcar "Offline"
5. Recarregar — assets estáticos (HTML/CSS/JS) devem servir do cache. `/api/v1/*` retorna erro (esperado — IndexedDB sync vem no P0.3).

---

## PWA instalado

Para validar que a instalação funciona de verdade:
- **Android Chrome**: banner "Adicionar à tela inicial" aparece automaticamente. Confirmar ícone + splash azul-portuário.
- **iOS Safari**: "Compartilhar → Adicionar à Tela de Início". Sem prompt nativo, mas funciona.
- **Lighthouse PWA score**: deve ser ≥ 90 (target do P0.5).

---

## Próximos passos

- **P0.3** (Sprint C): implementar 4 abas (Início/Escala/Histórico/Perfil) + login TPA + IndexedDB
- **P0.4** (Sprint B): auth unificada NextAuth (gate no `/login` WEB também)

Refs: `SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md` §16 e `DIAGNOSTICO-FUNCIONAL-2026-09-07.md` §6.3.
