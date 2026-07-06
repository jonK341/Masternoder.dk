#!/usr/bin/env bash
# Master content pipeline:
# 1) Trading content report + platform news
# 2) AI content factory (new long-form + shorts plans/jobs)
# 3) YouTube agent package/upload/live actions
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG_DIR="${CONTENT_PIPELINE_LOG_DIR:-$ROOT/logs}"
mkdir -p "$LOG_DIR"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
RUN_LOG="$LOG_DIR/content_pipeline_${STAMP}.log"
LATEST_LOG="$LOG_DIR/content_pipeline_latest.log"

# Default behavior: continue even if a stage fails, and report status summary.
FAIL_FAST="${CONTENT_PIPELINE_FAIL_FAST:-0}"

echo "[$(date -u +%FT%TZ)] content_pipeline_master start" | tee -a "$RUN_LOG"
echo "ROOT=$ROOT" | tee -a "$RUN_LOG"

stage_run() {
  local name="$1"
  shift
  echo "" | tee -a "$RUN_LOG"
  echo "=== STAGE: ${name} ===" | tee -a "$RUN_LOG"
  echo "CMD: $*" | tee -a "$RUN_LOG"
  if "$@" >>"$RUN_LOG" 2>&1; then
    echo "RESULT: ${name}=ok" | tee -a "$RUN_LOG"
    return 0
  fi
  echo "RESULT: ${name}=failed" | tee -a "$RUN_LOG"
  return 1
}

stage_ok=0
stage_fail=0

run_stage() {
  if stage_run "$@"; then
    stage_ok=$((stage_ok + 1))
  else
    stage_fail=$((stage_fail + 1))
    if [[ "$FAIL_FAST" == "1" ]]; then
      echo "FAIL_FAST=1 -> exiting pipeline" | tee -a "$RUN_LOG"
      return 1
    fi
  fi
  return 0
}

# Stage 1: refresh trading report + publish news
run_stage "trading_content_news" bash "$ROOT/cron/trading_content_news.sh" || true

# Stage 2: build new AI content plans/jobs (and optional live-gate trigger)
run_stage "ai_content_factory" bash "$ROOT/cron/ai_content_factory.sh" || true

# Stage 3: package/upload/live operations for YouTube
run_stage "youtube_content_agent" bash "$ROOT/cron/youtube_content_agent.sh" || true

echo "" | tee -a "$RUN_LOG"
echo "[$(date -u +%FT%TZ)] content_pipeline_master done ok=${stage_ok} failed=${stage_fail}" | tee -a "$RUN_LOG"
cp -f "$RUN_LOG" "$LATEST_LOG"

if [[ "$stage_fail" -gt 0 ]]; then
  exit 2
fi
exit 0
