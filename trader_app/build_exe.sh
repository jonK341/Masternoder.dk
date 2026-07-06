#!/usr/bin/env bash
# Build MN2 Private Control into a standalone binary, handling PEP 668
# ("externally-managed-environment") by using a dedicated build virtualenv.
#
#   bash trader_app/build_exe.sh
#
# Requires python3 + venv. On Debian/Ubuntu first: sudo apt install -y python3-venv python3-full
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.build-venv"

echo "[build] repo root: $ROOT"
if [ ! -x "$VENV/bin/python" ]; then
  echo "[build] creating build venv at $VENV"
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip >/dev/null
echo "[build] installing build deps (pyinstaller, flask, requests, cryptography)…"
"$VENV/bin/python" -m pip install --quiet pyinstaller flask requests cryptography
echo "[build] running PyInstaller…"
"$VENV/bin/python" "$ROOT/trader_app/build_exe.py"
echo "[build] done -> $ROOT/dist/MN2PrivateControl/"
