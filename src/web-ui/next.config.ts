import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const isDev = process.env.NODE_ENV === "development";

const apiUrl = process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "https://api.naglasupan.is";
const cdnUrl = process.env.NEXT_PUBLIC_CDN_URL || "https://cdn.naglasupan.is";
const cdnParsed = new URL(cdnUrl);
const cdnHostname = cdnParsed.hostname;
const cdnProtocol = cdnParsed.protocol.replace(":", "") as "http" | "https";
const cdnPort = cdnParsed.port || undefined;
const cdnOrigin = cdnParsed.origin;

// CSP placeholders — replaced at container startup by entrypoint.sh so a single
// image can run against any backend/CDN.  In dev we use the real values directly.
const cspApiUrl = isDev ? apiUrl : "__CSP_API_URL_PLACEHOLDER__";
const cspCdnUrl = isDev ? cdnUrl : "__CSP_CDN_URL_PLACEHOLDER__";

const securityHeaders = [
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      `img-src 'self' data: ${cspCdnUrl} https://*.s3.fr-par.scw.cloud${isDev ? ` ${cdnOrigin}` : ""}`,
      `connect-src 'self' ${cspApiUrl} ${cspCdnUrl} https://s3.fr-par.scw.cloud https://plausible.io${isDev ? " http://localhost:* http://127.0.0.1:*" : ""}`,
      "frame-ancestors 'none'",
    ].join("; "),
  },
  {
    key: "Strict-Transport-Security",
    value: "max-age=31536000; includeSubDomains",
  },
  {
    key: "X-Content-Type-Options",
    value: "nosniff",
  },
  {
    key: "X-Frame-Options",
    value: "DENY",
  },
  {
    key: "Referrer-Policy",
    value: "strict-origin-when-cross-origin",
  },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
];

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
        protocol: cdnProtocol,
        hostname: cdnHostname,
        ...(cdnPort ? { port: cdnPort } : {}),
      },
    ],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
};

export default withNextIntl(nextConfig);
