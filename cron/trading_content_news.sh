#!/usr/bin/env bash
# Generate SQL-backed trading content report and publish a news item.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DB_PATH="${TRADING_CONTENT_DB_PATH:-$ROOT/instance/database.db}"
WINDOW_HOURS="${TRADING_CONTENT_WINDOW_HOURS:-24}"
TOP_N="${TRADING_CONTENT_TOP_N:-8}"
OUTDIR="${TRADING_CONTENT_OUTPUT_DIR:-$ROOT/reports/trading_content}"
CHANNEL="${TRADING_CONTENT_NEWS_CHANNEL:-exchange}"
HREF="${TRADING_CONTENT_NEWS_HREF:-/news/}"

python3 scripts/trading_content_report.py \
  --db "$DB_PATH" \
  --hours "$WINDOW_HOURS" \
  --top "$TOP_N" \
  --save \
  --format markdown \
  --output-dir "$OUTDIR" \
  --publish-news \
  --news-channel "$CHANNEL" \
  --news-href "$HREF"
