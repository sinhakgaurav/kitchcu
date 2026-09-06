#!/usr/bin/env bash
# One-shot GCP bulk seeder — owners, kitchens, menus, orders, extras.
# Idempotent. Does not wipe existing data. Safe to re-run.
#
# Invoked by:
#   startup.sh (first boot when metadata run-seed=1)
#   sudo systemctl start kitchcu-bulk-seed.service
#   sudo bash /opt/ckac/infra/gcp-vm/bulk-seed.sh
#
# Optional env (defaults match first-boot demo VM):
#   CKAC_BULK_KITCHENS=30  CKAC_BULK_FULL=1  CKAC_BULK_ORDERS=250

set -euo pipefail

REPO_DIR="${CKAC_REPO_DIR:-/opt/ckac}"
STATE_DIR=/var/lib/ckac
LOG_FILE=/var/log/ckac-bulk-seed.log
SEED_MARKER="${CKAC_BULK_SEED_MARKER:-$STATE_DIR/.bulk-seeded}"

mkdir -p "$STATE_DIR"
exec >>"$LOG_FILE" 2>&1
echo "=== bulk seed start: $(date -u) ==="

cd "$REPO_DIR"

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
      echo "Stack ready for bulk seed: $ready_json"
      break
    fi
  fi
  [ $((i % 6)) -eq 0 ] && echo "  waiting for gateway ($i/90): ${ready_json:-unreachable}"
  sleep 10
done

if [ "$ready" -ne 1 ]; then
  echo "Gateway not ready after ~15 min — bulk seed skipped." >&2
  echo "=== bulk seed end (skipped): $(date -u) ==="
  exit 1
fi

set -a
# shellcheck disable=SC1091
source infra/gcp-vm/.env
set +a

CKAC_GATEWAY_URL="${CKAC_GATEWAY_URL:-http://127.0.0.1:18000}" \
CKAC_SEED_WAIT_SEC="${CKAC_SEED_WAIT_SEC:-120}" \
CKAC_BULK_KITCHENS="${CKAC_BULK_KITCHENS:-30}" \
CKAC_BULK_FULL="${CKAC_BULK_FULL:-1}" \
  python3 scripts/seed-bulk-data.py

touch "$SEED_MARKER"
echo "=== bulk seed end: $(date -u) ==="
