#!/usr/bin/env bash
# Full platform seed — baseline + bulk/feature-volume + current weekly cohort.
# Idempotent. Does not wipe existing data.
#
# Local:  bash scripts/seed-all.sh
# Windows: .\scripts\seed-all.ps1
# GCP:    infra/gcp-vm/bulk-seed.sh → this file
#
# Optional env:
#   CKAC_GATEWAY_URL  CKAC_BULK_KITCHENS=30  CKAC_BULK_FULL=1
#   CKAC_BULK_MONTHS=6  CKAC_FEATURE_VOLUME=1  CKAC_SEED_EXTRAS=1
#   CKAC_WEEKLY_MANIFEST=/var/lib/ckac/weekly-cohort.json

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"
export CKAC_GATEWAY_URL="${CKAC_GATEWAY_URL:-http://127.0.0.1:18000}"
export CKAC_SEED_EXTRAS="${CKAC_SEED_EXTRAS:-1}"
export CKAC_FEATURE_VOLUME="${CKAC_FEATURE_VOLUME:-1}"
export CKAC_BULK_FULL="${CKAC_BULK_FULL:-1}"
export CKAC_BULK_MONTHS="${CKAC_BULK_MONTHS:-6}"

echo "=== kitchCU full seed ==="
echo "Gateway: $CKAC_GATEWAY_URL"

echo ""
echo "[1/3] Dev baseline (owners, kitchens, menu, sample orders)..."
python3 scripts/seed-dev-data.py

echo ""
echo "[2/3] Bulk + feature volume (every kitchen + diner, every module)..."
python3 scripts/seed-bulk-data.py

echo ""
echo "[3/3] Weekly QA cohort (current ISO week)..."
weekly=(python3 scripts/weekly_test_data.py)
if [ -n "${CKAC_WEEKLY_MANIFEST:-}" ]; then
  weekly+=(--manifest "$CKAC_WEEKLY_MANIFEST")
fi
"${weekly[@]}"

echo ""
echo "Full platform seed complete."
