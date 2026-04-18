#!/usr/bin/env bash
# Build and run the web-ui with `next start` (production mode) against a
# local/LAN backend, emulating what entrypoint.sh does inside the container so
# CSP placeholders get substituted and the client bundle points at a reachable
# API URL. Useful for reproducing prod-only bugs on a phone over LAN without
# the Docker build cycle.
set -euo pipefail

cd "$(dirname "$0")/.."

# Pick API URL: explicit env > backend-port file > default.
if [ -n "${API_URL:-}" ]; then
  :
elif [ -f ../../.backend-port ]; then
  API_URL="http://localhost:$(cat ../../.backend-port)"
else
  API_URL="http://localhost:8000"
fi

CDN_URL="${CDN_URL:-https://cdn.naglasupan.is}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-3000}"

echo "Building with NEXT_PUBLIC_API_URL=$API_URL"
NEXT_PUBLIC_API_URL="$API_URL" npm run build

# macOS vs GNU sed in-place flag differ.
if sed --version >/dev/null 2>&1; then
  SED_INPLACE=(sed -i)
else
  SED_INPLACE=(sed -i '')
fi

echo "Substituting CSP + API URL placeholders (API=$API_URL, CDN=$CDN_URL)"
find .next -type f -name "*.js" -exec "${SED_INPLACE[@]}" \
  "s|__NEXT_PUBLIC_API_URL_PLACEHOLDER__|$API_URL|g" {} +

find .next -type f -name "routes-manifest.json" -exec "${SED_INPLACE[@]}" \
  -e "s|__CSP_API_URL_PLACEHOLDER__|$API_URL|g" \
  -e "s|__CSP_CDN_URL_PLACEHOLDER__|$CDN_URL|g" {} +

LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
if [ -n "$LAN_IP" ]; then
  echo "LAN URL: http://$LAN_IP:$PORT"
fi

echo "Starting next start on $HOST:$PORT"
exec npm run start -- -H "$HOST" -p "$PORT"
