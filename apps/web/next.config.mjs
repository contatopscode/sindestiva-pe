/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@sindestiva/shared", "@sindestiva/ui"],
  experimental: {
    typedRoutes: true,
  },
  // Sem output: 'export' porque PWA precisa de API routes pra auth
};

export default nextConfig;
