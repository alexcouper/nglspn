#!/bin/sh
set -e

# Replace placeholders with actual runtime values
if [ -n "$API_URL" ]; then
  find /app/.next -type f -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_API_URL_PLACEHOLDER__|$API_URL|g" {} +
fi

if [ -n "$MAINTENANCE_BYPASS_SECRET" ]; then
  find /app/.next -type f -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_MAINTENANCE_BYPASS_SECRET_PLACEHOLDER__|$MAINTENANCE_BYPASS_SECRET|g" {} +
fi

# Start the server
exec node server.js
