#!/usr/bin/env python3
"""MN2 Private Control — standalone laptop app (owner-only).

A private, passcode-gated control panel + trading cockpit you run on your own machine
(whose IP can reach the exchanges). Tabs: Overview, Trading, Profit Monitor (AI),
Controls (daemon/bot/agents), Shop, Accounting, Security. It pulls signals/status from the
site's admin API and runs the local grid/market-maker bot.

Config (env or trader_app/config.json):
  TRADER_PASSCODE   required to unlock the app (owner-only). Default 'mn2-owner' if unset.
  SITE_URL          e.g. https://your-site.example   (site admin API for controls/signals)
  SITE_ADMIN_KEY    admin key for the site's /api/exchange/* + control endpoints
  TRADER_PORT       default 8800
Venue API keys are read as the main app does (env / encrypted vault). Paper by default;
set EXCHANGE_GRID_LIVE=1 + EXCHANGE_ARBITRAGE_LIVE=1 to trade for real.
"""
from __future__ import annotations

import json
import os
import sys
from functools import wraps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("LITE_APP", "1")
os.environ.setdefault("DAEMON_QUIET", "1")

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    # PyInstaller bundle: templates are added under <_MEIPASS>/trader_app/templates
    _TEMPLATES = os.path.join(getattr(sys, "_MEIPASS", APP_DIR), "trader_app", "templates")
else:
    _TEMPLATES = os.path.join(APP_DIR, "templates")
app = Flask(__name__, template_folder=_TEMPLATES)
app.secret_key = os.environ.get("TRADER_SECRET_KEY") or os.urandom(24)


def _cfg() -> dict:
    cfg = {}
    path = os.path.join(APP_DIR, "config.json")
    if os.path.isfile(path):
        try:
            cfg = json.load(open(path, encoding="utf-8"))
        except Exception:
            cfg = {}
    cfg["site_url"] = (os.environ.get("SITE_URL") or cfg.get("site_url") or "").rstrip("/")
    cfg["admin_key"] = os.environ.get("SITE_ADMIN_KEY") or cfg.get("admin_key") or ""
    return cfg


def _passcode() -> str:
    return os.environ.get("TRADER_PASSCODE") or "mn2-owner"


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **k):
        if not session.get("auth"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "locked"}), 401
            return redirect(url_for("login"))
        return fn(*a, **k)
    return wrapper


# ------------------------- site proxy (best-effort) -------------------------

def site_get(path: str, params: dict = None) -> dict:
    cfg = _cfg()
    if not cfg.get("site_url"):
        return {"available": False, "error": "SITE_URL not set"}
    try:
        import requests
        r = requests.get(cfg["site_url"] + path, params=params or {},
                         headers={"X-Exchange-Admin-Key": cfg.get("admin_key", "")}, timeout=8)
        try:
            return {"available": True, **(r.json() if isinstance(r.json(), dict) else {"data": r.json()})}
        except Exception:
            return {"available": True, "status": r.status_code}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def site_post(path: str, body: dict = None) -> dict:
    cfg = _cfg()
    if not cfg.get("site_url"):
        return {"available": False, "error": "SITE_URL not set"}
    try:
        import requests
        r = requests.post(cfg["site_url"] + path, json=body or {},
                          headers={"X-Exchange-Admin-Key": cfg.get("admin_key", "")}, timeout=12)
        try:
            return {"available": True, **(r.json() if isinstance(r.json(), dict) else {"data": r.json()})}
        except Exception:
            return {"available": True, "status": r.status_code}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


# ------------------------- auth -------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = (request.form.get("passcode") or "").strip()
        if code and code == _passcode():
            session["auth"] = True
            return redirect(url_for("index"))
        return render_template("login.html", error="Incorrect passcode.")
    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("dashboard.html")


# ------------------------- tab data -------------------------

def _local_signals():
    cfg = _cfg()
    if cfg.get("site_url"):
        s = site_get("/api/exchange/signals")
        if s.get("available") and s.get("signals") is not None:
            return s
    from backend.services.exchange_signals_service import get_signals
    return get_signals()


@app.route("/api/overview")
@login_required
def api_overview():
    from backend.services.exchange_signals_service import account_balances
    from backend.services.exchange_grid_bot_service import grid_status, grid_profit, grid_live_enabled
    return jsonify({
        "mode": "LIVE" if grid_live_enabled() else "paper",
        "site_url": _cfg().get("site_url") or "(local)",
        "balances": account_balances(),
        "grid": grid_status(),
        "profit": grid_profit(),
        "signals": _local_signals(),
    })


@app.route("/api/trading")
@login_required
def api_trading():
    from backend.services.exchange_grid_bot_service import load_config
    from trader_app.intelligence import recommend
    cfg = load_config()
    sig = _local_signals()
    recs = recommend(sig.get("signals") or [], order_size_usd=float(cfg.get("order_size_usd") or 10.0))
    return jsonify({"success": True, "signals": sig.get("signals") or [], "recommendations": recs,
                    "grid_config": {k: cfg.get(k) for k in ("venue", "assets", "grid_levels",
                                    "grid_step_pct", "order_size_usd", "max_inventory_usd", "hard_loss_cap_usd")}})


@app.route("/api/profit-monitor")
@login_required
def api_profit_monitor():
    from backend.services.exchange_grid_bot_service import grid_status, load_config
    from trader_app.intelligence import recommend, combine_profit, ai_summary
    cfg = load_config()
    sig = _local_signals()
    state = (grid_status().get("state") or {})
    recs = recommend(sig.get("signals") or [], order_size_usd=float(cfg.get("order_size_usd") or 10.0))
    pmap = combine_profit(sig.get("signals") or [], state,
                          order_size_usd=float(cfg.get("order_size_usd") or 10.0))
    return jsonify({"success": True, "profit_map": pmap, "recommendations": recs,
                    "ai": ai_summary(pmap, recs)})


@app.route("/api/controls")
@login_required
def api_controls():
    return jsonify({
        "success": True,
        "control_board": site_get("/api/exchange/control-board/overview"),
        "agents": site_get("/api/exchange/live-watch/owner", {"limit": 40}),
        "payout": site_get("/api/exchange/payout/status"),
    })


@app.route("/api/controls/action", methods=["POST"])
@login_required
def api_controls_action():
    data = request.get_json(silent=True) or {}
    action = str(data.get("action") or "")
    # Local grid controls
    if action == "grid_enable":
        from backend.services.exchange_grid_bot_service import set_enabled
        return jsonify(set_enabled(bool(data.get("enabled"))))
    if action == "grid_tick":
        from backend.services.exchange_grid_bot_service import run_all
        return jsonify(run_all(dry_run=True))
    # Site controls (proxied)
    routes = {
        "run_all_bots": ("/api/exchange/control-board/run", {}),
        "toggle_bot": ("/api/exchange/control-board/bot", {"bot_id": data.get("bot_id"), "enabled": data.get("enabled")}),
        "kill_switch": ("/api/exchange/control-board/kill-switch", {"on": data.get("on")}),
        "daemon_tick": ("/api/exchange/control-board/run", {}),
    }
    if action in routes:
        path, body = routes[action]
        return jsonify(site_post(path, body))
    return jsonify({"success": False, "error": "unknown_action"})


@app.route("/api/shop")
@login_required
def api_shop():
    # Best-effort shop flow snapshot from the site admin API.
    return jsonify({
        "success": True,
        "revenue": site_get("/api/exchange/control-board/overview"),
        "shop_health": site_get("/api/shop/admin/summary"),
        "note": "Shop flow controls proxy the site admin API; configure SITE_URL + admin key.",
    })


@app.route("/api/accounting")
@login_required
def api_accounting():
    from backend.services.exchange_grid_bot_service import grid_profit
    return jsonify({
        "success": True,
        "grid_realized": grid_profit(),
        "payout": site_get("/api/exchange/payout/status"),
        "treasury": site_get("/api/exchange/treasury/status"),
        "fiat_valuation": site_get("/api/exchange/fiat/valuation"),
    })


@app.route("/api/security")
@login_required
def api_security():
    from backend.services.exchange_grid_bot_service import grid_live_enabled
    live_gates = {
        "EXCHANGE_ARBITRAGE_LIVE": bool(os.environ.get("EXCHANGE_ARBITRAGE_LIVE", "").strip() in ("1", "true", "yes")),
        "EXCHANGE_GRID_LIVE": grid_live_enabled(),
        "EXCHANGE_PAYOUT_BINANCE_LIVE": bool(os.environ.get("EXCHANGE_PAYOUT_BINANCE_LIVE", "").strip() in ("1", "true", "yes")),
    }
    try:
        from backend.services import exchange_secrets_vault_service as vault
        vstat = vault.vault_status()
    except Exception as exc:
        vstat = {"error": str(exc)}
    return jsonify({
        "success": True,
        "app_locked_by_passcode": True,
        "passcode_is_default": _passcode() == "mn2-owner",
        "site_admin_key_set": bool(_cfg().get("admin_key")),
        "live_gates": live_gates,
        "vault": vstat,
        "recommendations": [
            "Set a strong TRADER_PASSCODE (env) — do not use the default.",
            "Keep EXCHANGE_*_LIVE flags off until you intend to trade real funds.",
            "Store venue keys in the encrypted vault (EXCHANGE_VAULT_KEY), not plaintext.",
        ],
    })


if __name__ == "__main__":
    port = int(os.environ.get("TRADER_PORT", "8800"))
    print(f"MN2 Private Control: http://127.0.0.1:{port}  (passcode-gated)")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
