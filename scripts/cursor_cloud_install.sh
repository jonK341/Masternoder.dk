#!/usr/bin/env bash
# Cloud Agent environment bootstrap (idempotent). Run from repository root.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install openai moviepy imageio-ffmpeg
.venv/bin/pip install flake8
mkdir -p output uploads instance logs .pytest-tmp-local
