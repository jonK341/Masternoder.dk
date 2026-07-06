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
KEEP_FILES="${TRADING_CONTENT_KEEP_FILES:-30}"

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

# Keep stable "latest" copies for downstream agents (e.g., YouTube workflow).
latest_md="$(ls -1t "$OUTDIR"/trading_content_report_[0-9]*_[0-9]*.md 2>/dev/null | head -n 1 || true)"
latest_json="$(ls -1t "$OUTDIR"/trading_content_report_[0-9]*_[0-9]*.json 2>/dev/null | head -n 1 || true)"
if [[ -n "$latest_md" ]]; then
  cp -f "$latest_md" "$OUTDIR/trading_content_report_latest.md"
fi
if [[ -n "$latest_json" ]]; then
  cp -f "$latest_json" "$OUTDIR/trading_content_report_latest.json"
fi

# Retention cleanup: keep newest N generated timestamped files per extension.
if [[ "$KEEP_FILES" =~ ^[0-9]+$ ]] && [[ "$KEEP_FILES" -gt 0 ]]; then
  for ext in md json; do
    mapfile -t old_files < <(ls -1t "$OUTDIR"/trading_content_report_[0-9]*_[0-9]*.${ext} 2>/dev/null | awk "NR>${KEEP_FILES}")
    if [[ "${#old_files[@]}" -gt 0 ]]; then
      rm -f "${old_files[@]}"
    fi
  done
fi
