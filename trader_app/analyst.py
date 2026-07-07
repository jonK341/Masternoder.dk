"""Pre-trade Analyst — the 'last check before auto-trading'.

Aggregates gates, per-venue credentials + funding, grid config sanity, and current signals
into a readiness verdict plus a prioritized, human-readable 'what to do next' action list.
Pure function (no I/O) so it is fully testable; the route feeds it live inputs.
"""
from __future__ import annotations

from typing import Any, Dict, List

_QUOTE_BY_VENUE = {"binance": "USDC", "nonkyc": "USDT", "xeggex": "USDT"}
_MIN_QUOTE_USD = 10.0


def analyze(*, gates: Dict[str, Any], balances: Dict[str, Any], signals: Dict[str, Any],
            grid_status_data: Dict[str, Any], grid_config: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str, *, action: str = "", severity: str = "info") -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail, "severity": severity})
        if not ok and action:
            actions.append({"priority": 1 if severity == "block" else 2 if severity == "warn" else 3,
                            "action": action, "severity": severity})

    # 1) Live gates
    grid_live = bool(gates.get("grid_live"))
    add("Live gates enabled", grid_live,
        "grid LIVE" if grid_live else "paper mode",
        action="Set EXCHANGE_ARBITRAGE_LIVE=1 and EXCHANGE_GRID_LIVE=1 in config.json to trade real",
        severity="warn")

    # 2) Per-venue credentials + quote funding
    venues = (balances.get("venues") or {})
    funded_venue = False
    for v, row in venues.items():
        quote = _QUOTE_BY_VENUE.get(v, "USDT")
        if row.get("error"):
            add(f"{v} credentials", False, str(row.get("error")),
                action=f"Add {v.upper()}_API_KEY / {v.upper()}_API_SECRET to config.json", severity="warn")
            continue
        add(f"{v} credentials", True, "connected")
        qbal = 0.0
        for a in (row.get("assets") or []):
            if a.get("symbol") == quote:
                qbal = float(a.get("usd_value") or 0)
        ok = qbal >= _MIN_QUOTE_USD
        if ok:
            funded_venue = True
        add(f"{v} {quote} funded", ok, f"{quote} ${qbal:.2f}",
            action=f"Deposit {quote} to your {v} SPOT wallet (>= ${_MIN_QUOTE_USD:.0f}) so the grid can buy",
            severity="warn")

    # 3) Grid config sanity
    gc = grid_config or {}
    size = float(gc.get("order_size_usd") or 0)
    minn = float(gc.get("min_notional_usd") or 5)
    add("Order size >= min notional", size >= minn, f"size ${size:.2f} vs min ${minn:.2f}",
        action="Raise order_size_usd at/above min_notional_usd or orders get skipped", severity="warn")
    cap = float(gc.get("hard_loss_cap_usd") or 0)
    add("Hard loss cap set", cap > 0, f"cap ${cap:.2f}",
        action="Set hard_loss_cap_usd to bound downside (auto-halts the bot)", severity="warn")
    add("Assets configured", bool(gc.get("assets")), ", ".join(gc.get("assets") or []) or "none",
        action="Add at least one asset to grid config", severity="warn")

    # 4) Signals / opportunity
    sig_list = signals.get("signals") or []
    actionable = [s for s in sig_list if s.get("actionable")]
    add("Actionable signals now", len(actionable) > 0, f"{len(actionable)} actionable / {len(sig_list)} total",
        action="No fee-clearing edge right now — grid still books small wins in ranging markets",
        severity="info")

    # 5) Grid enabled
    enabled = bool((grid_status_data or {}).get("enabled"))
    add("Grid bot enabled", enabled, "enabled" if enabled else "disabled",
        action="Enable the grid bot (Trading tab -> Enable, or daemon --enable)", severity="warn")

    blockers = [c for c in checks if not c["ok"] and c["severity"] in ("warn", "block")]
    ready = len(blockers) == 0
    actions.sort(key=lambda a: a["priority"])

    if ready:
        next_step = ("All checks pass. Start the live loop: "
                     "python scripts/grid_bot_daemon.py --enable --interval 30")
        verdict = "ready_to_auto_trade"
    else:
        verdict = "blocked"
        next_step = actions[0]["action"] if actions else "Resolve the failing checks."

    return {
        "success": True,
        "verdict": verdict,
        "ready": ready,
        "funded_any_venue": funded_venue,
        "blocker_count": len(blockers),
        "checks": checks,
        "actions": actions,
        "next_step": next_step,
        "note": ("Cross-venue arbitrage is fee-dead at retail size; the grid/market-maker is the "
                 "real worker and only profits in ranging markets. This is a readiness check, "
                 "not a profit guarantee."),
    }
