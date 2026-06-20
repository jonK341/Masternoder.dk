#!/bin/bash
# Drain pending webhook outbox entries.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python scripts/process_webhook_outbox.py --limit "${WEBHOOK_OUTBOX_LIMIT:-50}"
