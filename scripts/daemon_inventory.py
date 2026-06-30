#!/usr/bin/env python3
"""Inventory of daemons, platform bots, and agent fleets (read-only status)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _section(title: str, body: dict) -> dict:
    return {"title": title, **body}


def collect() -> dict:
    out: dict = {"success": True, "repo_root": ROOT, "sections": []}

    try:
        from scripts.daemon_env import live_status
        out["live"] = live_status()
    except Exception as exc:
        out["live"] = {"error": str(exc)}

    # --- Exchange platform bots (control board) ---
    try:
        from backend.services.trading_bots_control_service import business_overview
        ob = business_overview()
        out["sections"].append(_section("exchange_control_board", {
            "kill_switch": ob.get("kill_switch"),
            "supervisors": ob.get("supervisors") or [],
            "bot_count": (ob.get("totals") or {}).get("bot_count"),
            "total_realized_pnl_usd": (ob.get("totals") or {}).get("total_realized_pnl_usd"),
        }))
    except Exception as exc:
        out["sections"].append(_section("exchange_control_board", {"error": str(exc)}))

    # --- Arbitrage paper agents ---
    try:
        from backend.services.exchange_arbitrage_service import agent_accounts, live_enabled
        arb = agent_accounts()
        out["sections"].append(_section("arbitrage_agents", {
            "live_gate": live_enabled(),
            "agent_count": arb.get("agent_count"),
            "total_profit_usd": arb.get("total_realized_profit_usd"),
            "agents": [{"id": a.get("agent_id"), "profit": a.get("realized_profit_usd"),
                          "trades": a.get("trade_count")} for a in (arb.get("accounts") or [])],
        }))
    except Exception as exc:
        out["sections"].append(_section("arbitrage_agents", {"error": str(exc)}))

    # --- AI multi-venue trader ---
    try:
        from backend.services.exchange_ai_trading_service import ai_trading_status
        out["sections"].append(_section("ai_market_trader", ai_trading_status()))
    except Exception as exc:
        out["sections"].append(_section("ai_market_trader", {"error": str(exc)}))

    # --- Internal cross-trade agents ---
    try:
        from backend.services.crypto_exchange_agent_service import list_agents
        cross = list_agents()
        out["sections"].append(_section("cross_trade_agents", {
            "enabled": cross.get("enabled"),
            "daemon_interval_sec": cross.get("daemon_interval_sec"),
            "tick_count": cross.get("tick_count"),
            "agents": [{"id": a.get("id"), "name": a.get("name"), "enabled": a.get("enabled")}
                       for a in (cross.get("agents") or [])],
        }))
    except Exception as exc:
        out["sections"].append(_section("cross_trade_agents", {"error": str(exc)}))

    # --- User marketplace bots ---
    try:
        from backend.services import agent_marketplace_service as mkt
        udir = mkt._USER_AGENTS_DIR
        users = []
        if os.path.isdir(udir):
            for name in os.listdir(udir):
                if name.endswith(".json"):
                    users.append(name[:-5])
        out["sections"].append(_section("marketplace_user_bots", {
            "user_count": len(users),
            "user_ids": users[:20],
        }))
    except Exception as exc:
        out["sections"].append(_section("marketplace_user_bots", {"error": str(exc)}))

    # --- Casino autonomous agents ---
    try:
        from backend.services import casino_agents_service as casino
        models = casino.list_models()
        agents = casino.list_agents()
        out["sections"].append(_section("casino_agents", {
            "model_count": len(models.get("models") or []),
            "agent_count": len(agents.get("agents") or []),
            "models": [m.get("model_id") for m in (models.get("models") or [])],
            "agents": [a.get("agent_id") for a in (agents.get("agents") or [])],
        }))
    except Exception as exc:
        out["sections"].append(_section("casino_agents", {"error": str(exc)}))

    # --- Python daemon scripts (local runners) ---
    out["daemon_scripts"] = [
        {"id": "exchange_master", "script": "scripts/exchange_master_daemon.py",
         "role": "All exchange bots + user marketplace ticks + auto-renewals (+ optional sweep)",
         "needs_flask": False, "default_interval_sec": 300},
        {"id": "exchange_arbitrage", "script": "scripts/exchange_arbitrage_daemon.py",
         "role": "Cross-venue arbitrage paper agents only", "needs_flask": False, "default_interval_sec": 120},
        {"id": "crypto_exchange_agent", "script": "scripts/crypto_exchange_agent_daemon.py",
         "role": "Internal cross-trade agents only", "needs_flask": False, "default_interval_sec": 300},
        {"id": "ai_trading", "script": "(inside exchange_master via run_all_bots)",
         "role": "AI multi-venue trader", "needs_flask": False},
        {"id": "casino_agent", "script": "scripts/casino_agent_daemon.py",
         "role": "Autonomous casino betting agents (Nova, Luna, ...)", "needs_flask": False, "default_interval_sec": 300},
        {"id": "site_agent", "script": "scripts/agent_daemon.py",
         "role": "POST /api/agents/daemon/tick (site automation)", "needs_flask": True, "default_interval_sec": 60},
        {"id": "mn2_blockchain", "script": "scripts/run_masternoder2d.sh (Linux) / .ps1 (Windows->bash)",
         "role": "MN2 wallet RPC — deposits, staking, masternode", "needs_flask": False, "server_only": True},
        {"id": "production_agents", "script": "scripts/production_agent_runner.py",
         "role": "Legacy DB player-behavior sim (20 agents) — dev/staging only", "needs_flask": True},
        {"id": "keep_agents_alive", "script": "scripts/keep_agents_alive.py",
         "role": "Legacy behavior loop — dev/staging only", "needs_flask": True},
    ]

    return out


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="List daemons, bots, and agent fleets")
    p.add_argument("--json", action="store_true", help="Print JSON only")
    args = p.parse_args()
    data = collect()
    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("=" * 72)
    print("MasterNoder — daemons, bots & agents inventory")
    print("=" * 72)
    for sec in data.get("sections") or []:
        title = sec.pop("title", "?")
        print(f"\n## {title}")
        if "error" in sec:
            print(f"  ERROR: {sec['error']}")
            continue
        for k, v in sec.items():
            if isinstance(v, (list, dict)) and len(str(v)) > 120:
                print(f"  {k}: ({len(v)} items)")
            else:
                print(f"  {k}: {v}")

    print("\n## Local daemon runners (scripts/)")
    for d in data.get("daemon_scripts") or []:
        flask = " [needs Flask]" if d.get("needs_flask") else ""
        srv = " [server/Linux]" if d.get("server_only") else ""
        print(f"  - {d['id']}: {d['script']}{flask}{srv}")
        print(f"      {d.get('role', '')}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
