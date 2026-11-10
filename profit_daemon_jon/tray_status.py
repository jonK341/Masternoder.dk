#!/usr/bin/env python3
"""Desktop status / tray helper — thin wrapper over the local control panel."""
from __future__ import annotations

from profit_daemon_jon.control_panel import main

__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
