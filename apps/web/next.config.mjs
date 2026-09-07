/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@sindestiva/shared", "@sindestiva/ui"],
  // typedRoutes: desabilitado até resolver incompatibilidade com Next 15.5+.
  // Quando habilitado: rotas em `redirect()` exigem RouteImpl<string> (união complexa).
  // typedRoutes: true,
  // Sem output: 'export' porque PWA precisa de API routes pra auth.
  async rewrites() {
    // Proxy /__sindestiva/* → https://api.lousa.pscode.ia.br/api/v1/*
    // Por que: o cookie `sindestiva_token` é domain-scoped ao host
    // `web.lousa.pscode.ia.br`. Fazer o browser chamar `api.lousa...`
    // diretamente não leva o cookie (3rd party). Com o rewrite, a
    // request fica no mesmo host → cookie viaja automaticamente +
    // server-side passa o cookie no fetch pra API.
    //
    // OBS: nome começa com `__` (não-colide com /api/* do Next.js).
    const API = process.env.NEXT_PUBLIC_API_URL || "https://api.lousa.pscode.ia.br";
    return [
      {
        source: "/__sindestiva/:path*",
        destination: `${API}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
