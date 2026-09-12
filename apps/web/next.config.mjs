/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@sindestiva/shared", "@sindestiva/ui"],
  // Coolify/docker: gera output standalone (~10x menor que .next inteiro).
  // Habilita copiar só `server.js` + `static/` na imagem final.
  output: "standalone",
  // typedRoutes: desabilitado até resolver incompatibilidade com Next 15.5+.
  // typedRoutes: true,
};

export default nextConfig;
