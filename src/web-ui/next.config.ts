import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 2592000,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.s3.fr-par.scw.cloud",
      },
      {
        protocol: "https",
        hostname: "cdn.naglasupan.is",
      },
    ],
  },
};

export default nextConfig;
