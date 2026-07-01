#!/usr/bin/env python3
"""
CLI for Pro copy assist (titles, descriptions, forum posts).

Usage:
  python scripts/copy_assist.py list
  python scripts/copy_assist.py generate --kind video_title --subject "Nature doc"
  python scripts/copy_assist.py generate --kind product_description --subject "MN2 pack" --json

Set MONETIZATION_FORCE_TIER=pro for local testing without a Pro subscription.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.services.copy_assist_service import _cli_main


if __name__ == "__main__":
    raise SystemExit(_cli_main())
