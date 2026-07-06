#!/usr/bin/env bash
# Generate fresh AI-native content plans and optionally dispatch generator + livestream actions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPORT_JSON="${CONTENT_FACTORY_REPORT_JSON:-$ROOT/reports/trading_content/trading_content_report_latest.json}"
OUTDIR="${CONTENT_FACTORY_OUTPUT_DIR:-$ROOT/reports/ai_content_factory}"
API_BASE="${CONTENT_FACTORY_API_BASE:-http://127.0.0.1:5000}"
USER_ID="${CONTENT_FACTORY_USER_ID:-youtube_agent}"
LONG_COUNT="${CONTENT_FACTORY_LONG_COUNT:-1}"
SHORT_COUNT="${CONTENT_FACTORY_SHORT_COUNT:-3}"
CREATE_LIVE="${CONTENT_FACTORY_CREATE_LIVE_ON_GATE:-0}"
LIVE_START_HOURS="${CONTENT_FACTORY_LIVE_START_HOURS:-24}"
DRY_RUN="${CONTENT_FACTORY_DRY_RUN:-0}"

args=(
  "--report-json" "$REPORT_JSON"
  "--outdir" "$OUTDIR"
  "--api-base" "$API_BASE"
  "--user-id" "$USER_ID"
  "--long-count" "$LONG_COUNT"
  "--short-count" "$SHORT_COUNT"
  "--live-start-hours" "$LIVE_START_HOURS"
)

if [[ "$CREATE_LIVE" == "1" ]]; then
  args+=("--create-live-on-gate")
fi
if [[ "$DRY_RUN" == "1" ]]; then
  args+=("--dry-run")
fi

python3 scripts/ai_content_factory.py "${args[@]}" --print-json
