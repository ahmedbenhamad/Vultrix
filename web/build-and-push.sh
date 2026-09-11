#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Build and push Strix Console images to Docker Hub.
#   1. Start the Docker daemon
#   2. docker login          (enter your Docker Hub credentials yourself)
#   3. ./build-and-push.sh   (env: NAMESPACE, TAG, SKIP_PUSH=1)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

NAMESPACE="${NAMESPACE:-ahmedbenhamad}"
TAG="${TAG:-0.1.0}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND="${NAMESPACE}/strix-console-backend"
FRONTEND="${NAMESPACE}/strix-console-frontend"

echo "==> Building backend: ${BACKEND}"
docker build -t "${BACKEND}:${TAG}" -t "${BACKEND}:latest" "${HERE}/backend"

echo "==> Building frontend: ${FRONTEND}"
docker build -t "${FRONTEND}:${TAG}" -t "${FRONTEND}:latest" "${HERE}/frontend"

if [[ "${SKIP_PUSH:-0}" == "1" ]]; then
  echo "==> SKIP_PUSH=1 set. Images built locally, not pushed."
  exit 0
fi

echo "==> Pushing images to Docker Hub..."
docker push "${BACKEND}:${TAG}";  docker push "${BACKEND}:latest"
docker push "${FRONTEND}:${TAG}"; docker push "${FRONTEND}:latest"

echo "==> Done. Launch with: docker compose -f docker-compose.hub.yml up -d"
