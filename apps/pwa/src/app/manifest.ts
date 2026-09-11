// =============================================================================
// SINDESTIVA-PE · PWA manifest (Next.js App Router metadata route)
// Gera automaticamente /manifest.webmanifest em prod.
// Ver: https://nextjs.org/docs/app/api-reference/file-conventions/metadata/manifest
//
// P0.5 — Torna o PWA instalável (Add to Home Screen, splash, theme).
// Ícones são PNGs gerados a partir de public/icon-source.svg via ImageMagick.
// =============================================================================

import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    // P0.5 (code-review F-001): `id` identifica unicamente a aplicação pra
    // analytics de install (boa prática PWA — evita contagem duplicada quando
    // browser trata URLs com query strings diferentes como apps separados).
    id: "/?source=pwa",
    name: "Lousa Digital · TPA",
    short_name: "TPA",
    description:
      "App do Trabalhador Portuário Avulso — SINDESTIVA-PE. Veja sua escala, confirme presença e fale com o Fiscal.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#0a1929",
    theme_color: "#0a1929",
    lang: "pt-BR",
    dir: "ltr",
    categories: ["productivity", "business", "utilities"],
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/maskable-icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
