#!/usr/bin/env bash
# Fresh wipe + rebuild on the EXISTING GCE VM. Does NOT change the static IP.
# Usage (on VM as root or via sudo):
#   cd /opt/ckac && sudo bash infra/gcp-vm/reset-fresh.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"
COMPOSE=(docker compose -f infra/gcp-vm/docker-compose.prod.yml --env-file infra/gcp-vm/.env)
SEED_MARKER=/var/lib/ckac/.bulk-seeded

echo "=== ckac reset-fresh: $(date -u) ==="
echo "Keeping VM + reserved static IP. Wiping containers, images, and DB volumes."

# Preserve .env secrets if present; otherwise fail clearly.
if [ ! -f infra/gcp-vm/.env ]; then
  echo "ERROR: infra/gcp-vm/.env missing. Re-run startup metadata write, or copy from .env.production.example." >&2
  exit 1
fi

# Force demo OTP path after wipe (seed + owner/customer 123456).
if grep -q '^APP_ENV=' infra/gcp-vm/.env; then
  sed -i 's/^APP_ENV=.*/APP_ENV=development/' infra/gcp-vm/.env
else
  echo 'APP_ENV=development' >> infra/gcp-vm/.env
fi

"${COMPOSE[@]}" down -v --remove-orphans || true
docker system prune -af --volumes || true

git fetch origin main
git reset --hard origin/main

# Re-apply APP_ENV after git reset (does not touch .env — .env is gitignored)
if grep -q '^APP_ENV=' infra/gcp-vm/.env; then
  sed -i 's/^APP_ENV=.*/APP_ENV=development/' infra/gcp-vm/.env
fi
rm -f "$SEED_MARKER"

echo "=== Building images in batches (avoids context deadline on e2-small) ==="
export COMPOSE_PARALLEL_LIMIT=2
export DOCKER_BUILDKIT=1
"${COMPOSE[@]}" build postgres redis minio
"${COMPOSE[@]}" build identity catalog order billing notification gateway
"${COMPOSE[@]}" build marketing ratings growth delivery learning community streaming
"${COMPOSE[@]}" build portal-web kitchen-web customer-web admin-web

echo "=== Starting stack ==="
"${COMPOSE[@]}" up -d

echo "=== Waiting for gateway /health/ready ==="
ready=0
for _ in $(seq 1 90); do
  if curl -sf http://127.0.0.1:18000/health/ready | grep -q '"status"'; then
    ready=1
    break
  fi
  sleep 10
done

if [ "$ready" -ne 1 ]; then
  echo "ERROR: gateway not ready after ~15 min. Check: docker compose ... ps / logs gateway" >&2
  "${COMPOSE[@]}" ps || true
  exit 1
fi

echo "=== Gateway ready — running bulk seed ==="
mkdir -p /var/lib/ckac
CKAC_GATEWAY_URL=http://127.0.0.1:18000 \
CKAC_BULK_KITCHENS="${CKAC_BULK_KITCHENS:-30}" \
CKAC_BULK_FULL="${CKAC_BULK_FULL:-1}" \
  python3 scripts/seed-bulk-data.py

touch "$SEED_MARKER"
echo "=== reset-fresh complete: $(date -u) ==="
echo "Demo: owner 9876543210 OTP 123456 · admin@kitchcu.com (ADMIN_PASSWORD from .env)"
