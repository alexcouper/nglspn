#!/bin/bash
# Usage: ./debug-docker.sh <image-id>
# Fill in PUSH_URL and TOKEN below before running.

PUSH_URL=""
TOKEN=""

IMAGE="${1:?Usage: ./debug-docker.sh <image-id>}"

exec docker run --rm \
    -e COCKPIT_LOGS_PUSH_URL="${PUSH_URL}" \
    -e COCKPIT_TOKEN="${TOKEN}" \
    -e OTEL_EXPORTER_OTLP_ENDPOINT="https://traces.cockpit.fr-par.scw.cloud" \
    -e OTEL_EXPORTER_OTLP_HEADERS="X-Token=${TOKEN}" \
    -e OTEL_SERVICE_NAME="debug-backend" \
    -e DEBUG=True \
    -p 8000:8000 \
    "$IMAGE"
