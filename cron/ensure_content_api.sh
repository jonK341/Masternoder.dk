#!/usr/bin/env bash
# Ensure content/generator API is reachable before running content pipeline.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_BASE="${CONTENT_FACTORY_API_BASE:-http://127.0.0.1:5000}"
HEALTH_URL="${API_BASE%/}/api/health"
WAIT_SEC="${CONTENT_API_WAIT_SEC:-45}"
SYSTEMD_UNIT="${CONTENT_API_SYSTEMD_UNIT:-}"
SESSION_NAME="${CONTENT_API_TMUX_SESSION:-content-api-server}"
START_CMD="${CONTENT_API_START_CMD:-python3 \"$ROOT/run.py\"}"

tmux_bin="$(command -v tmux || true)"
tmux_conf="/exec-daemon/tmux.portal.conf"
tmux_has_conf=0
if [[ -n "$tmux_bin" && -f "$tmux_conf" ]]; then
  tmux_has_conf=1
fi

curl_ok() {
  curl -fsS "$HEALTH_URL" >/dev/null 2>&1
}

wait_for_api() {
  local end=$((SECONDS + WAIT_SEC))
  while (( SECONDS < end )); do
    if curl_ok; then
      return 0
    fi
    sleep 2
  done
  return 1
}

run_tmux() {
  if [[ "$tmux_has_conf" == "1" ]]; then
    "$tmux_bin" -f "$tmux_conf" "$@"
  else
    "$tmux_bin" "$@"
  fi
}

echo "[ensure_content_api] checking $HEALTH_URL"
if curl_ok; then
  echo "[ensure_content_api] API already healthy"
  exit 0
fi

echo "[ensure_content_api] API down; attempting recovery"

if [[ -n "$SYSTEMD_UNIT" ]] && command -v systemctl >/dev/null 2>&1; then
  echo "[ensure_content_api] trying systemd restart: $SYSTEMD_UNIT"
  systemctl restart "$SYSTEMD_UNIT" || true
  if wait_for_api; then
    echo "[ensure_content_api] API recovered via systemd"
    exit 0
  fi
fi

if [[ -n "$tmux_bin" ]]; then
  echo "[ensure_content_api] trying tmux session start: $SESSION_NAME"
  run_tmux has-session -t "=$SESSION_NAME" 2>/dev/null || \
    run_tmux new-session -d -s "$SESSION_NAME" -c "$ROOT" -- "${SHELL:-bash}" -lc "$START_CMD"
  if wait_for_api; then
    echo "[ensure_content_api] API recovered via tmux-started process"
    exit 0
  fi
fi

echo "[ensure_content_api] failed to recover API at $HEALTH_URL"
exit 2
