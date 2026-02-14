#!/bin/bash
set -euxo pipefail

APP="$1"
IMAGE="${IMAGE:-$APP:latest}"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR="$SCRIPT_DIR/.."

echo "Building Docker image $IMAGE"

# Copy workspace lock file for Docker build (needed by uv workspace)
cp "$ROOT_DIR/uv.lock" uv.lock
trap 'rm -f uv.lock' EXIT

docker build -t "$IMAGE" --platform=linux/amd64 .
