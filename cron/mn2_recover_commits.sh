#!/bin/bash
# Recover stale MN2 withdrawal balance commits (reserved but never finalized).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python scripts/mn2_recover_pending_commits.py --max-age-minutes "${MN2_COMMIT_MAX_AGE_MIN:-30}"
