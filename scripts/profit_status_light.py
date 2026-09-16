#!/usr/bin/env python3
"""Lightweight profit status — delegates to profit_status_report.py --light."""
from __future__ import annotations

import runpy
import sys

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--light", *sys.argv[1:]]
    runpy.run_path("scripts/profit_status_report.py", run_name="__main__")
