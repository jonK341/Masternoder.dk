#!/usr/bin/env python3
"""Rebuild Discord community fulfillment order list (wrapper → sync_community_ledger)."""
from __future__ import annotations

import sys
import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

_scripts = os.path.dirname(os.path.abspath(__file__))
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)
from sync_community_ledger import main

if __name__ == "__main__":
    raise SystemExit(main())
