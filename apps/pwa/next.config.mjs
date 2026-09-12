import withPWAInit from "next-pwa";

const withPWA = withPWAInit({
  dest: "public",
  // Em dev, desabilita pra evitar HMR quebrado. Em prod (NODE_ENV=production),
  // next-pwa gera /sw.js em public/.
  disable: process.env.NODE_ENV === "development",
  reloadOnOnline: true,
  // P0.5: rota raiz "/" enquanto as 4 abas (Início/Escala/Histórico/Perfil)
  // não existem — P0.3 implementa as rotas filhas.
  navigateFallback: "/",
  navigateFallbackDenylist: [/^\/api\//, /^\/manifest/, /^\/icon/, /^\/sw/],
  // P0.5: mantém SW no ciclo padrão do Workbox (skipWaiting/clientsClaim default).
  // P0.3 adiciona runtime caching pra /api/v1/lousa/public/* via custom worker.
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@sindestiva/shared", "@sindestiva/ui"],
  // Coolify/docker: gera output standalone. Em prod, o next-pwa gera
  // public/sw.js no build time ANTES do output standalone ser gerado,
  // então o SW é incluído automaticamente na imagem.
  output: "standalone",
};

export default withPWA(nextConfig);
