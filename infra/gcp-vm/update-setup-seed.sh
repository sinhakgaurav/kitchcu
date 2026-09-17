#!/usr/bin/env bash
# One shot on the GCE VM: pull main, rebuild images, start the stack, bulk-seed.
#
# Default keeps volumes/DB (migrations apply on container start). Pass --fresh
# to wipe containers + DB volumes first (same as reset-fresh.sh).
#
# From a laptop (always fetch first so this file exists on the VM):
#   gcloud compute ssh ckac-vm --zone=asia-south1-a --command="sudo bash -lc 'cd /opt/ckac && git fetch origin main && git reset --hard origin/main && bash infra/gcp-vm/update-setup-seed.sh'"
# Wipe + rebuild + seed:
#   gcloud compute ssh ckac-vm --zone=asia-south1-a --command="sudo bash -lc 'cd /opt/ckac && git fetch origin main && git reset --hard origin/main && bash infra/gcp-vm/update-setup-seed.sh --fresh'"
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"
COMPOSE=(docker compose -f infra/gcp-vm/docker-compose.prod.yml --env-file infra/gcp-vm/.env)
FRESH=0

for arg in "$@"; do
  case "$arg" in
    --fresh|-f) FRESH=1 ;;
    --already-updated) ;;
    *)
      echo "Unknown argument: $arg (supported: --fresh)" >&2
      exit 2
      ;;
  esac
done

echo "=== ckac update-setup-seed: $(date -u) fresh=${FRESH} ==="

if [ ! -f infra/gcp-vm/.env ]; then
  echo "ERROR: infra/gcp-vm/.env missing. Re-run startup metadata write, or copy from .env.production.example." >&2
  exit 1
fi

git fetch origin main
git reset --hard origin/main

if [ "$FRESH" -eq 1 ]; then
  echo "=== --fresh: wiping volumes then rebuild + seed ==="
  exec bash infra/gcp-vm/reset-fresh.sh
fi

echo "=== Building images ONE AT A TIME ==="
bash infra/gcp-vm/build-serial.sh

echo "=== Starting stack (images already built; volumes kept) ==="
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

echo "=== Installing seed systemd units ==="
install -m 0644 infra/gcp-vm/kitchcu-weekly-seed.service /etc/systemd/system/
install -m 0644 infra/gcp-vm/kitchcu-weekly-seed.timer /etc/systemd/system/
install -m 0644 infra/gcp-vm/kitchcu-bulk-seed.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now kitchcu-weekly-seed.timer

echo "=== Bulk seed (idempotent; does not wipe) ==="
mkdir -p /var/lib/ckac
bash infra/gcp-vm/bulk-seed.sh

echo "=== update-setup-seed complete: $(date -u) ==="
echo "Demo: owner 9876543210 OTP 123456 · admin@kitchcu.com (ADMIN_PASSWORD from .env)"
echo "Weekly timer: $(systemctl list-timers kitchcu-weekly-seed --no-pager --no-legend || true)"
