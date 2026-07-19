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

echo "=== Building images ONE AT A TIME (Bake ignores parallel limits and OOMs e2-small) ==="
bash infra/gcp-vm/build-serial.sh

echo "=== Starting stack (images already built) ==="
"${COMPOSE[@]}" up -d --no-build

echo "=== Waiting for /health/ready status=ok AND identity:true ==="
ready=0
for i in $(seq 1 90); do
  ready_json="$(curl -sf http://127.0.0.1:18000/health/ready || true)"
  if echo "$ready_json" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' \
    && echo "$ready_json" | grep -q '"identity"[[:space:]]*:[[:space:]]*true'; then
    sleep 10
    ready_json="$(curl -sf http://127.0.0.1:18000/health/ready || true)"
    if echo "$ready_json" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' \
      && echo "$ready_json" | grep -q '"identity"[[:space:]]*:[[:space:]]*true'; then
      ready=1
      echo "Stack ready: $ready_json"
      break
    fi
  fi
  if [ $((i % 6)) -eq 0 ]; then
    echo "  still waiting ($i/90): ${ready_json:-unreachable}"
    "${COMPOSE[@]}" ps identity billing catalog || true
  fi
  sleep 10
done

if [ "$ready" -ne 1 ]; then
  echo "ERROR: identity/core not ready after ~15 min." >&2
  "${COMPOSE[@]}" ps || true
  "${COMPOSE[@]}" logs --tail=80 identity || true
  exit 1
fi

echo "=== Gateway ready — running bulk seed ==="
mkdir -p /var/lib/ckac
# Export ADMIN_* / POSTGRES_* from compose .env so seed can login as the bootstrapped admin
# (GCP uses admin@kitchcu.com + metadata password — not the local demo@kitchcu.dev defaults).
set -a
# shellcheck disable=SC1091
source infra/gcp-vm/.env
set +a
CKAC_GATEWAY_URL=http://127.0.0.1:18000 \
CKAC_BULK_KITCHENS="${CKAC_BULK_KITCHENS:-30}" \
CKAC_BULK_FULL="${CKAC_BULK_FULL:-1}" \
  python3 scripts/seed-bulk-data.py

touch "$SEED_MARKER"
echo "=== reset-fresh complete: $(date -u) ==="
echo "Demo: owner 9876543210 OTP 123456 · admin@kitchcu.com (ADMIN_PASSWORD from .env)"
