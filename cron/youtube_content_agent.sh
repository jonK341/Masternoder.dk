#!/usr/bin/env bash
# YouTube content agent runner: builds package and optionally uploads/schedules live event.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REPORT_JSON="${YOUTUBE_REPORT_JSON:-$ROOT/reports/trading_content/trading_content_report_latest.json}"
OUTDIR="${YOUTUBE_AGENT_OUTPUT_DIR:-$ROOT/reports/youtube_agent}"
CLIENT_SECRETS="${YOUTUBE_CLIENT_SECRETS_FILE:-$ROOT/config/youtube_client_secrets.json}"
TOKEN_FILE="${YOUTUBE_TOKEN_FILE:-$ROOT/config/youtube_token.json}"
CHANNEL_NAME="${YOUTUBE_CHANNEL_NAME:-MasterNoder}"
VIDEO_FILE="${YOUTUBE_VIDEO_FILE:-}"
ENABLE_UPLOAD="${YOUTUBE_ENABLE_UPLOAD:-0}"
ENABLE_LIVE="${YOUTUBE_ENABLE_LIVE:-0}"
LIVE_START_HOURS="${YOUTUBE_LIVE_START_HOURS:-24}"

args=(
  "--report-json" "$REPORT_JSON"
  "--outdir" "$OUTDIR"
  "--client-secrets" "$CLIENT_SECRETS"
  "--token-file" "$TOKEN_FILE"
  "--channel-name" "$CHANNEL_NAME"
)

if [[ "$ENABLE_UPLOAD" == "1" ]]; then
  args+=("--upload")
  if [[ -n "$VIDEO_FILE" ]]; then
    args+=("--video-file" "$VIDEO_FILE")
  fi
fi

if [[ "$ENABLE_LIVE" == "1" ]]; then
  args+=("--create-live" "--live-start-hours" "$LIVE_START_HOURS")
fi

python3 scripts/youtube_channel_agent.py "${args[@]}"
