/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@sindestiva/shared", "@sindestiva/ui"],
  // typedRoutes: desabilitado até resolver incompatibilidade com Next 15.5+.
  // Quando habilitado: rotas em `redirect()` exigem RouteImpl<string> (união complexa).
  // typedRoutes: true,
  // Sem output: 'export' porque PWA precisa de API routes pra auth.
};

export default nextConfig;
