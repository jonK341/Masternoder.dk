#!/bin/bash
# MN2/USDT/USDC pool agent — one tick (seed MN2, sweep agent stables, rebalance pool).
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export DAEMON_QUIET=1
export OUTPUT_DIR="${OUTPUT_DIR:-/tmp/mn2-output}"
export UPLOAD_DIR="${UPLOAD_DIR:-/tmp/mn2-uploads}"
python3 scripts/mn2_pool_agent_tick.py
