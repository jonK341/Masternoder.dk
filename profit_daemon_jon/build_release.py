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
        "profit_daemon_jon/README.md",
        "profit_daemon_jon/docs/INSTALL_5MIN.md",
        "data/exchanges_registry.json",
        "data/exchange_connectors_config.json",
        "data/exchange_venue_api_config.json",
        "data/exchange_ladder_config.json",
        "data/exchange_cross_trade_config.json",
        "data/exchange_maker_config.json",
        "data/grafana/exchange_daemon_dashboard.json",
        "systemd/masternoder-profit-daemon.service",
    ]
    hidden = [
        "backend.services.exchange_registry_service",
        "backend.services.exchange_ladder_service",
        "backend.services.exchange_ladder_strategy_improve",
        "backend.services.exchange_maker_quote_service",
        "backend.services.exchange_cross_trade_service",
        "backend.services.external_exchange_connector_service",
        "backend.services.exchange_venue_api_service",
        "backend.services.profit_daemon_jon_product_service",
        "profit_daemon_jon.control_panel",
        "profit_daemon_jon.wizard",
        "scripts.all_profit_daemons",
        "scripts.cross_trade_limit_tick",
        "scripts.exchange_sales_report",
    ]
    args = [
        os.path.join(ROOT, "profit_daemon_jon", "run.py"),
        "--name", NAME,
        "--onedir", "--noconfirm", "--clean",
        "--paths", ROOT,
    ]
    for mod in hidden:
        args += ["--hidden-import", mod]
    for df in data_files:
        if os.path.exists(os.path.join(ROOT, df)):
            dest = os.path.dirname(df) or "."
            args += ["--add-data", _data(df, dest)]
    print("[build]", " ".join(args[:10]), "…")
    pyi.run(args)
    out = os.path.join(ROOT, "dist", NAME)
    print(f"[build] done -> {out}/")
    print(f"Run: {out}/{NAME} --status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
