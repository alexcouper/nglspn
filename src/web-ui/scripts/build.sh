#!/bin/bash
set -euxo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
APP_DIR="$SCRIPT_DIR/.."
ROOT_DIR="$APP_DIR/../.."

IMAGE="${IMAGE:-web-ui:latest}"

BUILD_ARGS=()
if [ -n "${API_URL:-}" ]; then
  BUILD_ARGS+=(--build-arg "API_URL=${API_URL}")
fi

echo "Building Docker image $IMAGE"
docker build -t "$IMAGE" --platform=linux/amd64 ${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"} "$APP_DIR"
