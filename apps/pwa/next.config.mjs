import withPWAInit from "next-pwa";

const withPWA = withPWAInit({
  dest: "public",
  cacheOnFrontEndNav: true,
  aggressiveFrontEndNavCaching: true,
  reloadOnOnline: true,
  disable: false, // Em dev, false gera o SW. Em prod build, true gera manifest.
  workboxOptions: {
    // Será detalhado em Sprint 3 (T3-01)
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
