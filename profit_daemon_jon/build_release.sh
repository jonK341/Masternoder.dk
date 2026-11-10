#!/usr/bin/env bash
# Build The Profit Daemon Jon standalone binary (Linux/macOS).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.build-venv"
echo "[build] The Profit Daemon Jon — root=$ROOT"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV/bin/python" -m pip install --quiet -r "$ROOT/profit_daemon_jon/requirements.txt" pyinstaller
"$VENV/bin/python" "$ROOT/profit_daemon_jon/build_release.py"
# Convenience copy of VERSION into dist folder
mkdir -p "$ROOT/dist/TheProfitDaemonJon"
cp -f "$ROOT/profit_daemon_jon/VERSION" "$ROOT/dist/TheProfitDaemonJon/VERSION" 2>/dev/null || true
cp -f "$ROOT/profit_daemon_jon/README.md" "$ROOT/dist/TheProfitDaemonJon/README.md" 2>/dev/null || true
echo "[build] artifact ready under dist/TheProfitDaemonJon/ — upload to GitHub Releases"
