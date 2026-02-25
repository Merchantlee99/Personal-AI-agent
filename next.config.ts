import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typedRoutes: true,
  // next lint is incompatible with the currently pinned ESLint major.
  // Use `npm run lint` (tsc gate) and skip build-time lint invocation.
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
