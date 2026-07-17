#!/usr/bin/env bash
# Build every kitchCU image ONE AT A TIME.
#
# Docker Compose >=2.37 delegates `build`/`up --build` to Buildx Bake, which
# ignores COMPOSE_PARALLEL_LIMIT and --parallel and always builds every
# requested target concurrently (docker/compose#13043, docker/for-win#14889).
# On an e2-small VM (2 vCPU / 2GB RAM) that means ~16 Python + 4 Node builds
# running at once -> OOM / disk pressure -> `failed to execute bake: exit
# status 100` or `context deadline exceeded`, even when services are grouped
# into smaller batches (each batch call is still one Bake invocation).
#
# The only reliable fix short of a bigger VM: pass exactly ONE service per
# `docker compose build` call so Bake has nothing left to parallelize.
# COMPOSE_BAKE=false is set too as defense in depth (works on Compose <=2.39;
# a future Compose release may drop it, but the one-service-at-a-time loop
# alone is sufficient regardless of builder).
#
# Usage: bash infra/gcp-vm/build-serial.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"
COMPOSE=(docker compose -f infra/gcp-vm/docker-compose.prod.yml --env-file infra/gcp-vm/.env)

export DOCKER_BUILDKIT=1
export COMPOSE_BAKE=false
export COMPOSE_PARALLEL_LIMIT=1

# Heaviest first (Python w/ compiled deps) so a failure surfaces early;
# web (Node) builds last since they are the most RAM-hungry (npm + vite).
SERVICES=(
  identity catalog order billing notification
  marketing ratings growth delivery learning community streaming
  gateway
  portal-web kitchen-web customer-web admin-web
)

for svc in "${SERVICES[@]}"; do
  echo "=== [build-serial] $svc ==="
  "${COMPOSE[@]}" build "$svc"
  # Reclaim BuildKit cache disk between builds — final tagged images are untouched.
  docker builder prune -f --filter until=1h >/dev/null 2>&1 || true
done

echo "=== [build-serial] all images built ==="
