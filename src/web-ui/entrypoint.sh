#!/bin/sh
set -e

# Replace placeholders with actual runtime values in JS bundles
if [ -n "$API_URL" ]; then
  find /app/.next -type f -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_API_URL_PLACEHOLDER__|$API_URL|g" {} +
fi


# Replace CSP placeholders in the routes manifest so the Content-Security-Policy
# header matches the actual backend/CDN for this deployment.
CSP_API_URL="${API_URL:-https://api.naglasupan.is}"
CSP_CDN_URL="${CDN_URL:-https://cdn.naglasupan.is}"

find /app/.next -type f -name "routes-manifest.json" -exec sed -i \
  -e "s|__CSP_API_URL_PLACEHOLDER__|$CSP_API_URL|g" \
  -e "s|__CSP_CDN_URL_PLACEHOLDER__|$CSP_CDN_URL|g" \
  {} +

# Start the server
exec node server.js
