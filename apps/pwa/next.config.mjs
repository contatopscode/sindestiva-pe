import withPWAInit from "next-pwa";

const withPWA = withPWAInit({
  dest: "public",
  // Em dev, gera SW básico só pra servir manifest.json. Em prod, Sprint 3
  // detalha workboxOptions (Sprint 3 T3-01).
  disable: process.env.NODE_ENV === "development",
  reloadOnOnline: true,
  workboxOptions: {
    navigateFallback: "/inicio",
    navigateFallbackDenylist: [/^\/api\//],
  },
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@sindestiva/shared", "@sindestiva/ui"],
  experimental: {
    typedRoutes: true,
  },
};

export default withPWA(nextConfig);
