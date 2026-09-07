/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@sindestiva/shared", "@sindestiva/ui"],
  // typedRoutes: desabilitado até resolver incompatibilidade com Next 15.5+.
  // typedRoutes: true,
};

export default nextConfig;
