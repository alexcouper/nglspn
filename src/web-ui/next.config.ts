import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
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
