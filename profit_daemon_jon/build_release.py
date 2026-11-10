#!/usr/bin/env python3
"""Build a standalone The Profit Daemon Jon binary with PyInstaller (onedir)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEP = os.pathsep
NAME = "TheProfitDaemonJon"


def _data(src_rel: str, dest_rel: str) -> str:
    return f"{os.path.join(ROOT, src_rel)}{SEP}{dest_rel}"


def main() -> int:
    try:
        import PyInstaller.__main__ as pyi
    except Exception:
        print("PyInstaller not installed. Run: pip install pyinstaller")
        return 1

    data_files = [
        "profit_daemon_jon/PRODUCT.json",
        "profit_daemon_jon/VERSION",
        "profit_daemon_jon/top25_technologies.json",
        "profit_daemon_jon/.env.example",
        "data/grafana/exchange_daemon_dashboard.json",
        "data/exchange_ladder_config.json",
        "systemd/masternoder-profit-daemon.service",
    ]
    args = [
        os.path.join(ROOT, "profit_daemon_jon", "run.py"),
        "--name", NAME,
        "--onedir", "--noconfirm", "--clean",
        "--paths", ROOT,
    ]
    for df in data_files:
        if os.path.exists(os.path.join(ROOT, df)):
            dest = os.path.dirname(df) or "."
            args += ["--add-data", _data(df, dest)]
    print("[build]", " ".join(args[:8]), "…")
    pyi.run(args)
    out = os.path.join(ROOT, "dist", NAME)
    print(f"[build] done -> {out}/")
    print(f"Run: {out}/{NAME} --status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
