"""Daemon-to-daemon matching on the MasterNoder internal exchange.

Cross-trade bots and arbitrage agents peer-fill on-platform: when one daemon wants
to buy and another wants to sell the same asset, the mesh executes coordinated
internal swaps and credits mesh spread to the platform treasury.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import external_exchange_connector_service as conn


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _agent_side_intent(agent_id: str, tick_parity: int) -> Dict[str, Any]:
    """Infer buy/sell intent from cross-trade rotation pattern."""
    from backend.services.crypto_exchange_agent_service import list_agents
    agents = {a["id"]: a for a in (list_agents().get("agents") or []) if a.get("id")}
    row = agents.get(agent_id)
    if not row:
        return {}
    assets = [str(a).upper() for a in (row.get("assets") or []) if str(a).upper() != "MN2"]
    if not assets:
        assets = ["USDC"]
    sym = assets[tick_parity % len(assets)]
    holding = float((ex.get_wallet(agent_id).get("assets") or {}).get(sym) or 0)
    side = "sell" if holding > 0 and tick_parity % 2 == 1 else "buy"
    return {"agent_id": agent_id, "symbol": sym, "side": side, "kind": "cross_trade"}


def _collect_intents() -> List[Dict[str, Any]]:
    intents: List[Dict[str, Any]] = []
    try:
        from backend.services.crypto_exchange_agent_service import list_agents, _read_state
        state = _read_state()
        tick = int(state.get("tick_count") or 0)
        for a in list_agents().get("agents") or []:
            if not a.get("enabled", True):
                continue
            it = _agent_side_intent(str(a["id"]), tick)
            if it:
                intents.append(it)
    except Exception:
        pass

    cfg = conn.load_connectors_config()
    for agent in cfg.get("arbitrage_agents") or []:
        if not isinstance(agent, dict) or not agent.get("id"):
            continue
        acct = arb.read_account(str(agent["id"]))
        last = acct.get("last_action") or {}
        if last.get("executed") and last.get("symbol"):
            buy_v = last.get("buy_venue")
            sell_v = last.get("sell_venue")
            if buy_v == "internal":
                intents.append({"agent_id": agent["id"], "symbol": last["symbol"], "side": "buy", "kind": "arb"})
            elif sell_v == "internal":
                intents.append({"agent_id": agent["id"], "symbol": last["symbol"], "side": "sell", "kind": "arb"})
    return intents


def run_mesh_tick(*, max_matches: int = 5) -> Dict[str, Any]:
    from backend.services.exchange_treasury_service import load_config, stash_profit_usd, treasury_user_id

    cfg = load_config()
    if not cfg.get("daemon_mesh_enabled", True):
        return {"success": True, "skipped": True, "reason": "mesh_disabled"}

    intents = _collect_intents()
    buyers: Dict[str, List[Dict[str, Any]]] = {}
    sellers: Dict[str, List[Dict[str, Any]]] = {}
    for it in intents:
        sym = str(it.get("symbol") or "").upper()
        if not sym:
            continue
        if it.get("side") == "buy":
            buyers.setdefault(sym, []).append(it)
        elif it.get("side") == "sell":
            sellers.setdefault(sym, []).append(it)

    treasury = treasury_user_id()
    matches: List[Dict[str, Any]] = []
    mesh_profit_usd = 0.0

    for sym in cfg.get("mesh_symbols") or list(set(buyers) | set(sellers)):
        sym = str(sym).upper()
        bl = buyers.get(sym) or []
        sl = sellers.get(sym) or []
        while bl and sl and len(matches) < max_matches:
            b, s = bl.pop(0), sl.pop(0)
            price = max(ex._price_usd(sym), 1e-9)
            mn2_price = max(ex._price_in_quote(sym, "MN2"), 1e-9)
            trade_mn2 = min(5.0, max(1.0, float(ex.load_config().get("agent_trading", {}).get("max_trade_mn2_per_tick") or 2.5)))
            qty = round(trade_mn2 / mn2_price, 8)
            if qty <= 0:
                continue

            qid_b = uuid.uuid4().hex[:16]
            qid_s = uuid.uuid4().hex[:16]
            sell_res = ex.execute_swap(s["agent_id"], qid_s, sym, "sell", qty, "MN2")
            if not sell_res.get("success"):
                continue
            buy_res = ex.execute_swap(b["agent_id"], qid_b, sym, "buy", qty, "MN2")
            if not buy_res.get("success"):
                continue

            spread_usd = round(qty * price * 0.001, 4)
            mesh_profit_usd += spread_usd
            if spread_usd > 0:
                stash_profit_usd(spread_usd, source="daemon_mesh", agent_id=f"{b['agent_id']}:{s['agent_id']}", mode="internal")

            matches.append({
                "symbol": sym,
                "quantity": qty,
                "buyer": b["agent_id"],
                "seller": s["agent_id"],
                "spread_usd": spread_usd,
            })
            ex._audit("daemon_mesh_match", user_id=treasury, amount_usd=spread_usd,
                      symbol=sym, buyer=b["agent_id"], seller=s["agent_id"])

    return {
        "success": True,
        "matched_at": _iso(),
        "match_count": len(matches),
        "mesh_profit_usd": round(mesh_profit_usd, 4),
        "matches": matches,
        "intent_count": len(intents),
    }
