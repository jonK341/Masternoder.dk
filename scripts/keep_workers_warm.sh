#!/bin/bash
# Keep uWSGI workers resident/warm on the small (2-vCPU/1.6GB) box.
#
# Why: with 2 workers and continuous background daemon load, a worker that has
# been idle for a bit gets its pages reclaimed/swapped. The next request then
# faults everything back in and takes multiple seconds (or times out). Touching
# the app every ~20s keeps both workers hot, so real requests stay fast.
#
# Runs from cron every minute; loops 3 times (t=0,20,40s) to cover the minute.
# All requests are localhost with short timeouts, so cost is negligible.
set -u
HEALTH="http://127.0.0.1:5000/api/health"
WARM_PATHS=(
  "http://127.0.0.1:5000/api/forum/feed?limit=10"
  "http://127.0.0.1:5000/api/forum/stats"
)

for round in 1 2 3; do
  # Fire several concurrent health hits so the round-robin touches both workers.
  for _ in 1 2 3 4; do
    curl -s -m 8 -o /dev/null "$HEALTH" &
  done
  wait
  # Keep the forum code paths warm too.
  for u in "${WARM_PATHS[@]}"; do
    curl -s -m 8 -o /dev/null "$u" 2>/dev/null || true
  done
  [ "$round" -lt 3 ] && sleep 20
done
exit 0
