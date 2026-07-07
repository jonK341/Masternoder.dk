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

from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for

from trader_app import store

from datetime import timedelta

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    # PyInstaller bundle: templates are added under <_MEIPASS>/trader_app/templates
    _TEMPLATES = os.path.join(getattr(sys, "_MEIPASS", APP_DIR), "trader_app", "templates")
else:
    _TEMPLATES = os.path.join(APP_DIR, "templates")
app = Flask(__name__, template_folder=_TEMPLATES)
app.secret_key = os.environ.get("TRADER_SECRET_KEY") or os.urandom(24)
# Session/cookie hardening + auto-lock after inactivity.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

# Brute-force protection: lock out an IP after repeated failed passcodes.
_LOGIN_FAILS: dict = {}
_LOCK_MAX = 5
_LOCK_WINDOW = 300  # seconds


def _login_locked(ip: str) -> bool:
    ent = _LOGIN_FAILS.get(ip)
    if not ent:
        return False
    import time as _t
    if _t.time() - ent[1] > _LOCK_WINDOW:
        _LOGIN_FAILS.pop(ip, None)
        return False
    return ent[0] >= _LOCK_MAX


_CONFIG_SOURCE = None  # path config.json was actually loaded from (or None)


def _config_paths() -> list:
    """Config search order (first hit wins):
      0) TRADER_CONFIG env (explicit path)
      1) next to the .exe   2) folder of argv[0]   3) bundled into the exe (_MEIPASS)
      4) current working dir  5) source dir
    """
    paths = []
    envp = (os.environ.get("TRADER_CONFIG") or "").strip()
    if envp:
        paths.append(envp)
    if getattr(sys, "frozen", False):
        try:
            paths.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "config.json"))
        except Exception:
            pass
    try:
        if sys.argv and sys.argv[0]:
            paths.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config.json"))
    except Exception:
        pass
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        paths.append(os.path.join(meipass, "config.json"))
    paths.append(os.path.join(os.getcwd(), "config.json"))
    paths.append(os.path.join(APP_DIR, "config.json"))
    seen, out = set(), []
    for p in paths:
        rp = os.path.abspath(p)
        if rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out


def _strip_jsonc(text: str) -> str:
    """Tolerantly strip // line comments (outside strings) and trailing commas so a
    lightly-commented config.json still parses. URLs like https:// inside quotes are kept.
    Also normalizes smart/curly quotes and non-breaking spaces that editors sometimes insert."""
    import re
    text = (text.replace("\u201c", '"').replace("\u201d", '"')
                .replace("\u2018", "'").replace("\u2019", "'")
                .replace("\u00a0", " ").replace("\ufeff", ""))
    out = []
    for line in text.splitlines():
        res, in_str, esc, i = [], False, False, 0
        while i < len(line):
            ch = line[i]
            if esc:
                res.append(ch); esc = False; i += 1; continue
            if ch == "\\":
                res.append(ch); esc = True; i += 1; continue
            if ch == '"':
                in_str = not in_str; res.append(ch); i += 1; continue
            if (not in_str) and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break  # rest of line is a comment
            res.append(ch); i += 1
        out.append("".join(res))
    # Repair malformed string values: `"KEY": bareword"` or `"KEY": bareword` -> `"KEY": "bareword"`.
    repaired = []
    for line in out:
        m = re.match(r'^(\s*"[^"]*"\s*:\s*)(.+?)(,?)\s*$', line)
        if m:
            prefix, val, comma = m.groups()
            v = val.strip()
            if v and v[0] not in '"{[-0123456789' and v not in ("true", "false", "null"):
                core = v.strip('"')
                if re.match(r'^[A-Za-z0-9_.\-/:+=@]+$', core):
                    line = prefix + '"' + core + '"' + comma
        repaired.append(line)
    joined = "\n".join(repaired)
    return re.sub(r",(\s*[}\]])", r"\1", joined)  # drop trailing commas


def _load_config_file() -> dict:
    global _CONFIG_SOURCE
    for p in _config_paths():
        if os.path.isfile(p):
            try:
                raw = open(p, encoding="utf-8").read()
            except Exception as exc:
                print(f"[config] could not read {p}: {exc}")
                continue
            try:
                cfg = json.loads(raw)
            except Exception:
                try:
                    cfg = json.loads(_strip_jsonc(raw))  # tolerate // comments / trailing commas
                    print(f"[config] {p} had comments/quirks — parsed leniently")
                except Exception as exc:
                    ln = getattr(exc, "lineno", None)
                    hint = ""
                    if ln:
                        lines = raw.splitlines()
                        if 1 <= ln <= len(lines):
                            hint = f"  <<< offending line {ln}: {lines[ln - 1]!r}"
                    print(f"[config] found {p} but could not parse even leniently: {exc}{hint}")
                    continue
            _CONFIG_SOURCE = p
            return cfg if isinstance(cfg, dict) else {}
    _CONFIG_SOURCE = None
    return {}


# Env keys the app + backend services read; config.json may supply any of them.
_CONFIG_ENV_KEYS = (
    "TRADER_PASSCODE", "SITE_URL", "SITE_ADMIN_KEY",
    "BINANCE_API_KEY", "BINANCE_API_SECRET",
    "NONKYC_API_KEY", "NONKYC_API_SECRET", "NONKYC_API_PASSPHRASE",
    "XEGGEX_API_KEY", "XEGGEX_API_SECRET", "XEGGEX_API_PASSPHRASE",
    "EXCHANGE_VAULT_KEY",
    "EXCHANGE_ARBITRAGE_LIVE", "EXCHANGE_GRID_LIVE",
    "EXCHANGE_PAYOUT_BINANCE_LIVE", "EXCHANGE_PAYOUT_NONKYC_LIVE",
    "MN2_SPORK_GATES",
)


def _bootstrap_env_from_config() -> None:
    """Populate os.environ from config.json so keys/passcode work without exporting env vars.
    Env vars already set take precedence over the file."""
    filecfg = _load_config_file()
    for k in _CONFIG_ENV_KEYS:
        v = filecfg.get(k)
        if v is not None and str(v) != "" and not os.environ.get(k):
            os.environ[k] = str(v)
    if _CONFIG_SOURCE:
        default_pc = (os.environ.get("TRADER_PASSCODE") or "mn2-owner") == "mn2-owner"
        print(f"[config] loaded config.json from: {_CONFIG_SOURCE} "
              f"(passcode {'DEFAULT' if default_pc else 'set from config'})")
    else:
        print("[config] no config.json found — using DEFAULTS (passcode 'mn2-owner'). "
              "Searched: " + " | ".join(_config_paths()))


_bootstrap_env_from_config()


def _cfg() -> dict:
    cfg = _load_config_file()
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
    import time as _t
    ip = request.remote_addr or "?"
    if request.method == "POST":
        if _login_locked(ip):
            return render_template("login.html", error="Too many attempts — wait a few minutes.")
        code = (request.form.get("passcode") or "").strip()
        if code and code == _passcode():
            _LOGIN_FAILS.pop(ip, None)
            session.permanent = True
            session["auth"] = True
            try:
                store.record_alert("login", "Owner unlocked the app", "info")
            except Exception:
                pass
            return redirect(url_for("index"))
        ent = _LOGIN_FAILS.get(ip)
        if not ent or _t.time() - ent[1] > _LOCK_WINDOW:
            ent = [0, _t.time()]
        ent[0] += 1
        _LOGIN_FAILS[ip] = ent
        try:
            store.record_alert("login_fail", f"Failed unlock attempt from {ip}", "warn")
        except Exception:
            pass
        left = max(0, _LOCK_MAX - ent[0])
        msg = "Incorrect passcode." + (f" {left} attempt(s) left." if left <= 2 else "")
        return render_template("login.html", error=msg)
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

import threading
import time as _time

# Non-blocking cache: a background thread refreshes the slow calls (signals scan ~seconds,
# venue balances), and all request handlers read the cache instantly so the UI never waits.
_cache: dict = {}
_cache_lock = threading.Lock()
_REFRESH_INTERVAL = 30.0


def _cache_get(key: str):
    with _cache_lock:
        ent = _cache.get(key)
    return ent[1] if ent else None


def _cache_set(key: str, val) -> None:
    with _cache_lock:
        _cache[key] = (_time.time(), val)


def _local_signals():
    cfg = _cfg()
    if cfg.get("site_url"):
        s = site_get("/api/exchange/signals")
        if s.get("available") and s.get("signals") is not None:
            return s
    from backend.services.exchange_signals_service import get_signals
    return get_signals()


def _balances_cached():
    return _cache_get("balances") or {"success": True, "venues": {}, "total_usd": 0.0, "warming": True}


def _signals_cached():
    return _cache_get("signals") or {"success": True, "signals": [], "warming": True}


def _health_cached():
    return _cache_get("health") or {"available": None}


def _refresh_once() -> None:
    from backend.services.exchange_signals_service import account_balances
    try:
        _cache_set("balances", account_balances())
    except Exception:
        pass
    try:
        _cache_set("signals", _local_signals())
    except Exception:
        pass
    try:
        if _cfg().get("site_url"):
            _cache_set("health", site_get("/api/exchange/health"))
    except Exception:
        pass


def _refresher() -> None:
    while True:
        _refresh_once()
        _time.sleep(_REFRESH_INTERVAL)


threading.Thread(target=_refresher, daemon=True).start()


_prev_halts = set()


@app.route("/api/overview")
@login_required
def api_overview():
    from backend.services.exchange_grid_bot_service import grid_status, grid_profit, grid_live_enabled
    from trader_app.intelligence import combine_profit
    bals = _balances_cached()
    grid = grid_status()
    profit = grid_profit()
    sig = _signals_cached()
    pmap = combine_profit(sig.get("signals") or [], grid.get("state") or {})
    # Record equity/PnL snapshot for sparkline/history; raise alerts on new halts.
    try:
        store.record_snapshot(bals.get("total_usd"), profit.get("realized_pnl_usd"),
                              pmap.get("projected_daily_usd"))
        halted_now = {k for k, s in (grid.get("state") or {}).items() if s.get("halted")}
        for k in halted_now - _prev_halts:
            reason = (grid["state"][k] or {}).get("halt_reason")
            store.record_alert("halt", f"{k} halted: {reason}", "warn")
        _prev_halts.clear(); _prev_halts.update(halted_now)
    except Exception:
        pass
    return jsonify({
        "mode": "LIVE" if grid_live_enabled() else "paper",
        "site_url": _cfg().get("site_url") or "(local)",
        "balances": bals, "grid": grid, "profit": profit, "signals": sig,
        "projected_daily_usd": pmap.get("projected_daily_usd"),
    })


@app.route("/api/history")
@login_required
def api_history():
    return jsonify({"success": True,
                    "history": store.history(int(request.args.get("limit") or 200)),
                    "stats": store.equity_stats()})


@app.route("/api/alerts")
@login_required
def api_alerts():
    return jsonify({"success": True, "alerts": store.alerts(int(request.args.get("limit") or 50))})


@app.route("/api/health")
@login_required
def api_health():
    from backend.services.exchange_grid_bot_service import grid_live_enabled
    cfg = _cfg()
    site_ok = None
    if cfg.get("site_url"):
        h = _health_cached()
        site_ok = h.get("available")
    return jsonify({"success": True, "site_reachable": site_ok, "site_url": cfg.get("site_url") or "(local)",
                    "live": grid_live_enabled(), "checked_at": store._iso()})


@app.route("/api/config/save", methods=["POST"])
@login_required
def api_config_save():
    from backend.services.exchange_grid_bot_service import save_config
    return jsonify({"success": True, "config": save_config(request.get_json(silent=True) or {})})


_PRESETS = {
    "conservative": {"grid_levels": 2, "grid_step_pct": 0.008, "order_size_usd": 5.0,
                     "max_inventory_usd": 10.0, "hard_loss_cap_usd": 3.0},
    "balanced": {"grid_levels": 3, "grid_step_pct": 0.004, "order_size_usd": 6.0,
                 "max_inventory_usd": 15.0, "hard_loss_cap_usd": 5.0},
    "aggressive": {"grid_levels": 5, "grid_step_pct": 0.0025, "order_size_usd": 8.0,
                   "max_inventory_usd": 30.0, "hard_loss_cap_usd": 10.0},
}


@app.route("/api/config/preset", methods=["POST"])
@login_required
def api_config_preset():
    from backend.services.exchange_grid_bot_service import save_config
    name = str((request.get_json(silent=True) or {}).get("preset") or "")
    if name not in _PRESETS:
        return jsonify({"success": False, "error": "unknown_preset", "presets": list(_PRESETS)})
    store.record_alert("config", f"Applied '{name}' grid preset", "info")
    return jsonify({"success": True, "preset": name, "config": save_config(_PRESETS[name])})


@app.route("/api/export/<what>.csv")
@login_required
def api_export(what):
    from backend.services.exchange_grid_bot_service import grid_status
    if what == "history":
        rows = store.history(1000)
        csv_txt = store.to_csv(rows, ["ts", "total_usd", "realized", "projected_daily"])
    elif what == "positions":
        rows = []
        for k, s in (grid_status().get("state") or {}).items():
            rows.append({"market": k, "inventory_base": s.get("inventory_base"),
                         "avg_cost_usd": s.get("avg_cost_usd"), "realized_pnl_usd": s.get("realized_pnl_usd"),
                         "max_drawdown_usd": s.get("max_drawdown_usd"),
                         "open_orders": s.get("open_orders"), "halted": s.get("halted")})
        csv_txt = store.to_csv(rows, ["market", "inventory_base", "avg_cost_usd", "realized_pnl_usd",
                                      "max_drawdown_usd", "open_orders", "halted"])
    elif what == "alerts":
        rows = store.alerts(500)
        csv_txt = store.to_csv(rows, ["ts", "level", "kind", "message"])
    else:
        return jsonify({"success": False, "error": "unknown_export"}), 400
    return Response(csv_txt, mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={what}.csv"})


@app.route("/api/trading")
@login_required
def api_trading():
    from backend.services.exchange_grid_bot_service import load_config
    from trader_app.intelligence import recommend
    cfg = load_config()
    sig = _signals_cached()
    recs = recommend(sig.get("signals") or [], order_size_usd=float(cfg.get("order_size_usd") or 10.0))
    return jsonify({"success": True, "signals": sig.get("signals") or [], "recommendations": recs,
                    "grid_config": {k: cfg.get(k) for k in ("venue", "assets", "grid_levels",
                                    "grid_step_pct", "order_size_usd", "max_inventory_usd",
                                    "hard_loss_cap_usd", "allow_sell_existing_inventory", "venues")}})


@app.route("/api/grid/rank")
@login_required
def api_grid_rank():
    """Profit-ranked candidate pairs (measured edge from ledger + live arb, net of fees)."""
    from backend.services.exchange_grid_bot_service import rank_profit_pairs
    try:
        min_score = float(request.args.get("min_score") or 3.0)
    except (TypeError, ValueError):
        min_score = 3.0
    ranked = rank_profit_pairs(include_live=True, min_score=min_score)
    return jsonify({"success": True, "min_score": min_score, "count": len(ranked), "pairs": ranked})


@app.route("/api/grid/cross-diff")
@login_required
def api_grid_cross_diff():
    """Cross-venue price differences (spatial arb) across Binance/NonKYC/XeggeX for common pairs."""
    from backend.services.exchange_grid_bot_service import scan_cross_venue_differences
    try:
        min_bps = float(request.args.get("min_bps") or 0.0)
    except (TypeError, ValueError):
        min_bps = 0.0
    return jsonify(scan_cross_venue_differences(min_net_bps=min_bps))


@app.route("/api/grid/cross-trade")
@login_required
def api_grid_cross_trade():
    """Cross-venue auto-trader status + recent executions (audit trail)."""
    from backend.services.exchange_cross_trade_service import status
    return jsonify(status())


@app.route("/api/grid/cross-trade/preview")
@login_required
def api_grid_cross_trade_preview():
    """Which cross-venue differences are actually executable now (both legs pre-funded)."""
    from backend.services.exchange_cross_trade_service import preview
    try:
        min_bps = float(request.args.get("min_bps") or 0.0)
    except (TypeError, ValueError):
        min_bps = 0.0
    return jsonify(preview(min_net_bps=min_bps))


@app.route("/api/profit-monitor")
@login_required
def api_profit_monitor():
    from backend.services.exchange_grid_bot_service import grid_status, load_config
    from trader_app.intelligence import recommend, combine_profit, ai_summary
    cfg = load_config()
    sig = _signals_cached()
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


@app.route("/api/analyst")
@login_required
def api_analyst():
    from backend.services.exchange_grid_bot_service import grid_status, load_config, grid_live_enabled
    from trader_app.analyst import analyze
    gs = grid_status()
    return jsonify(analyze(
        gates={"grid_live": grid_live_enabled()},
        balances=_balances_cached(),
        signals=_signals_cached(),
        grid_status_data=gs,
        grid_config=load_config(),
    ))


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
    if action == "grid_kill":
        from backend.services.exchange_grid_bot_service import set_enabled
        store.record_alert("kill", "Kill switch: grid bot disabled", "warn")
        return jsonify(set_enabled(False))
    if action == "grid_autoselect":
        from backend.services.exchange_grid_bot_service import autoselect_profit_pairs
        try:
            min_score = float(data.get("min_score") or 3.0)
        except (TypeError, ValueError):
            min_score = 3.0
        res = autoselect_profit_pairs(min_score=min_score, include_live=True, apply=True)
        if res.get("applied"):
            store.record_alert("grid", f"Added profit-ranked pairs ({res.get('targets_total')} targets)", "info")
        return jsonify(res)
    if action == "grid_add_cross":
        from backend.services.exchange_grid_bot_service import autoselect_cross_venue_pairs
        try:
            min_bps = float(data.get("min_bps") or 5.0)
        except (TypeError, ValueError):
            min_bps = 5.0
        res = autoselect_cross_venue_pairs(min_net_bps=min_bps, apply=True)
        if res.get("applied"):
            store.record_alert("grid", f"Added cross-venue pairs ({res.get('targets_total')} targets)", "info")
        return jsonify(res)
    if action == "cross_trade_enable":
        from backend.services.exchange_cross_trade_service import set_enabled, cross_trade_live_enabled
        on = bool(data.get("enabled"))
        r = set_enabled(on)
        store.record_alert("cross_trade", f"Cross-venue auto-trader {'ENABLED' if on else 'disabled'} "
                           f"(live={cross_trade_live_enabled()})", "warn" if on else "info")
        return jsonify(r)
    if action == "cross_trade_run":
        from backend.services.exchange_cross_trade_service import run_once
        # Manual one-shot search+execute. Paper unless both live gates are on.
        return jsonify(run_once(force=True))
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
    # Shop flow snapshot from real site endpoints.
    return jsonify({
        "success": True,
        "analytics": site_get("/api/shop/analytics"),
        "payment_health": site_get("/api/shop/payment-health"),
        "integration_health": site_get("/api/shop/integration-health"),
        "note": "Shop flow snapshot (analytics + payment/integration health) from the site. "
                "Set SITE_URL + admin key to populate.",
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
        "config_loaded_from": _CONFIG_SOURCE or "(none — using defaults)",
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
