#!/usr/bin/env bash
# Weekly QA cohort seed — invoked by the kitchcu-weekly-seed systemd timer.
#
# Seeds a fresh cohort for the current ISO week without touching earlier ones:
# 5 owners + kitchens with menus, 10 customers, 10 delivered+rated orders per
# kitchen (new and returning diners), this week's coupon/promotion (retiring the
# last cohort's), a tiffin plan, CRM refresh, growth suggestions, and a ticket.
#
# Safe to re-run: identifiers are derived from the ISO year+week, so a repeat run
# reuses the same accounts and only tops orders up to the target count.
#
# Manual run on the VM:
#   sudo systemctl start kitchcu-weekly-seed.service
#   journalctl -u kitchcu-weekly-seed --no-pager -n 100

set -euo pipefail

REPO_DIR="${CKAC_REPO_DIR:-/opt/ckac}"
STATE_DIR=/var/lib/ckac
LOG_FILE=/var/log/ckac-weekly-seed.log

mkdir -p "$STATE_DIR"

exec >>"$LOG_FILE" 2>&1
echo "=== weekly seed start: $(date -u) ==="

cd "$REPO_DIR"

# Only seed a stack that is genuinely ready — never on live-only / degraded.
ready=0
for i in $(seq 1 30); do
  ready_json="$(curl -sf http://127.0.0.1:18000/health/ready || true)"
  if echo "$ready_json" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"' \
    && echo "$ready_json" | grep -q '"identity"[[:space:]]*:[[:space:]]*true'; then
    ready=1
    break
  fi
  [ $((i % 6)) -eq 0 ] && echo "  waiting for gateway ($i/30): ${ready_json:-unreachable}"
  sleep 10
done

if [ "$ready" -ne 1 ]; then
  echo "Gateway not ready after ~5 min — weekly seed skipped." >&2
  echo "=== weekly seed end (skipped): $(date -u) ==="
  exit 0
fi

set -a
# shellcheck disable=SC1091
source infra/gcp-vm/.env
set +a

CKAC_GATEWAY_URL=http://127.0.0.1:18000 \
CKAC_SEED_WAIT_SEC=120 \
  python3 scripts/weekly_test_data.py --manifest "$STATE_DIR/weekly-cohort.json"

echo "=== weekly seed end: $(date -u) ==="
