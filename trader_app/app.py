#!/usr/bin/env python3
"""Standalone laptop trader — local dashboard + trading loop.

Run this on a machine whose IP can reach the exchanges (your laptop). It:
  * pulls cross-trade SIGNALS from the site's profit daemon (/api/exchange/signals),
  * reads your real venue BALANCES (per venue / per asset),
  * runs the grid/market-maker bot locally and shows live stats + realized PnL,
  * lets you start/stop the bot and run ticks from a simple web UI.

Config (env or trader_app/config.json):
  SITE_URL          e.g. https://your-site.example   (omit to compute signals locally)
  SITE_ADMIN_KEY    admin key for the site's /api/exchange/* endpoints
  TRADER_PORT       default 8800
Venue API keys are read the same way the main app does (env / encrypted vault).
Paper by default; set EXCHANGE_GRID_LIVE=1 + EXCHANGE_ARBITRAGE_LIVE=1 to trade for real.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("LITE_APP", "1")
os.environ.setdefault("DAEMON_QUIET", "1")

from flask import Flask, jsonify, render_template, request

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "templates"))


def _cfg() -> dict:
    cfg = {}
    path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.isfile(path):
        try:
            cfg = json.load(open(path, encoding="utf-8"))
        except Exception:
            cfg = {}
    cfg["site_url"] = (os.environ.get("SITE_URL") or cfg.get("site_url") or "").rstrip("/")
    cfg["admin_key"] = os.environ.get("SITE_ADMIN_KEY") or cfg.get("admin_key") or ""
    return cfg


def _fetch_site_signals(cfg: dict) -> dict:
    if not cfg.get("site_url"):
        from backend.services.exchange_signals_service import get_signals
        return get_signals()
    try:
        import requests
        r = requests.get(cfg["site_url"] + "/api/exchange/signals",
                         headers={"X-Exchange-Admin-Key": cfg.get("admin_key", "")}, timeout=8)
        return r.json()
    except Exception as exc:
        return {"success": False, "error": str(exc), "signals": []}


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/overview")
def overview():
    cfg = _cfg()
    from backend.services.exchange_signals_service import account_balances
    from backend.services.exchange_grid_bot_service import grid_status, grid_profit, grid_live_enabled

    out = {
        "mode": "LIVE" if grid_live_enabled() else "paper",
        "site_url": cfg.get("site_url") or "(local)",
        "balances": account_balances(),
        "grid": grid_status(),
        "profit": grid_profit(),
        "signals": _fetch_site_signals(cfg),
    }
    return jsonify(out)


@app.route("/api/bot/enable", methods=["POST"])
def bot_enable():
    from backend.services.exchange_grid_bot_service import set_enabled
    data = request.get_json(silent=True) or {}
    return jsonify(set_enabled(bool(data.get("enabled"))))


@app.route("/api/bot/tick", methods=["POST"])
def bot_tick():
    from backend.services.exchange_grid_bot_service import run_all
    data = request.get_json(silent=True) or {}
    dry = data.get("dry_run")
    return jsonify(run_all(dry_run=bool(dry) if dry is not None else None))


if __name__ == "__main__":
    port = int(os.environ.get("TRADER_PORT", "8800"))
    print(f"Trader dashboard: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
