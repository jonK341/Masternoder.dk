#!/usr/bin/env bash
# Per-boot local paths for Flask dev (no long-running server here).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/output" "$ROOT/uploads" "$ROOT/instance" "$ROOT/logs" "$ROOT/.pytest-tmp-local"
