#!/bin/bash
set -euxo pipefail

APP="$1"
IMAGE="${IMAGE:-$APP:latest}"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$( cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd )

echo "Building Docker image $IMAGE"

docker build -t "$IMAGE" --platform=linux/amd64 -f "$ROOT_DIR/src/$APP/Dockerfile" "$ROOT_DIR"
