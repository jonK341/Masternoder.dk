"""Daemon-to-daemon matching grid on the MasterNoder internal exchange.

Cross-trade bots, arbitrage agents, extended-profit agents, and marketplace
user agents peer-fill on-platform: when one daemon wants to buy and another
wants to sell the same asset, the grid executes coordinated internal swaps and
credits mesh spread to the platform treasury.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import external_exchange_connector_service as conn


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_grid_config() -> Dict[str, Any]:
    from backend.services.exchange_treasury_service import load_config

    tre = load_config()
    agent_cfg = ex.load_config().get("agent_trading") if isinstance(ex.load_config().get("agent_trading"), dict) else {}
    return {
        "enabled": bool(tre.get("daemon_mesh_enabled", True)),
        "mesh_symbols": list(tre.get("mesh_symbols") or []),
        "max_matches": int(tre.get("grid_max_matches") or tre.get("mesh_max_matches") or 25),
        "rounds_per_tick": int(tre.get("grid_rounds_per_tick") or 4),
        "trade_mn2": float(tre.get("grid_trade_mn2") or agent_cfg.get("max_trade_mn2_per_tick") or 3.5),
        "include_arb_agents": bool(tre.get("grid_include_arb_agents", True)),
        "include_extended_agents": bool(tre.get("grid_include_extended_agents", True)),
        "include_marketplace_agents": bool(tre.get("grid_include_marketplace_agents", True)),
        "include_treasury_liquidity": bool(tre.get("grid_include_treasury_liquidity", True)),
        "intents_per_agent": int(tre.get("grid_intents_per_agent") or 2),
    }


def _tick_parity() -> int:
    try:
        from backend.services.crypto_exchange_agent_service import _read_state

        return int(_read_state().get("tick_count") or 0)
    except Exception:
        return 0


def _agent_side_intent(agent_id: str, tick_parity: int, *, asset_offset: int = 0) -> Dict[str, Any]:
    """Infer buy/sell intent from cross-trade rotation pattern."""
    from backend.services.crypto_exchange_agent_service import list_agents

    agents = {a["id"]: a for a in (list_agents().get("agents") or []) if a.get("id")}
    row = agents.get(agent_id)
    if not row:
        return {}
    assets = [str(a).upper() for a in (row.get("assets") or []) if str(a).upper() != "MN2"]
    if not assets:
        assets = ["USDC"]
    idx = (tick_parity + asset_offset) % len(assets)
    sym = assets[idx]
    holding = float((ex.get_wallet(agent_id).get("assets") or {}).get(sym) or 0)
    side = "sell" if holding > 0 and (tick_parity + asset_offset) % 2 == 1 else "buy"
    return {"agent_id": agent_id, "symbol": sym, "side": side, "kind": "cross_trade"}


def _arb_agent_intents(agent: Dict[str, Any], tick_parity: int, *, intents_per_agent: int) -> List[Dict[str, Any]]:
    agent_id = str(agent.get("id") or "").strip()
    if not agent_id:
        return []
    symbols = [str(s).upper() for s in (agent.get("symbols") or []) if s]
    if not symbols:
        return []
    out: List[Dict[str, Any]] = []
    for offset in range(max(1, intents_per_agent)):
        sym = symbols[(tick_parity + offset) % len(symbols)]
        side = "buy" if (tick_parity + offset) % 2 == 0 else "sell"
        out.append({"agent_id": agent_id, "symbol": sym, "side": side, "kind": "arb"})
    return out


def _extended_agent_intents(tick_parity: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from backend.services.exchange_extended_profit_service import load_config as load_ext

        cfg = load_ext()
        for name, strat in (cfg.get("strategies") or {}).items():
            if not isinstance(strat, dict) or not strat.get("enabled", True):
                continue
            agent_id = str(strat.get("agent_id") or "").strip()
            if not agent_id:
                continue
            symbols = [str(s).upper() for s in (strat.get("symbols") or []) if s]
            if not symbols and strat.get("loops"):
                first_loop = (strat.get("loops") or [[]])[0]
                symbols = [str(s).upper() for s in (first_loop or []) if s]
            if not symbols and name == "stablecoin_peg":
                symbols = ["USDC", "USDT"]
            if not symbols:
                symbols = ["USDC"]
            sym = symbols[tick_parity % len(symbols)]
            side = "buy" if tick_parity % 2 == 0 else "sell"
            out.append({"agent_id": agent_id, "symbol": sym, "side": side, "kind": "extended"})
    except Exception:
        pass
    return out


def _marketplace_agent_intents(tick_parity: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from backend.services import agent_marketplace_service as mkt
        from backend.services import external_exchange_connector_service as conn_svc

        symbols = list(conn_svc.load_connectors_config().get("supported_symbols") or ["BTC", "ETH", "USDC"])[:8]
        udir = mkt._USER_AGENTS_DIR
        if not os.path.isdir(udir):
            return out
        for name in os.listdir(udir):
            if not name.endswith(".json"):
                continue
            user_id = name[:-5]
            data = mkt._read_user_agents(user_id)
            for agent_id, agent in (data.get("agents") or {}).items():
                if not (agent or {}).get("enabled", True):
                    continue
                sym = symbols[(tick_parity + hash(agent_id) % len(symbols)) % len(symbols)]
                side = "buy" if tick_parity % 2 == 0 else "sell"
                out.append({
                    "agent_id": user_id,
                    "mesh_agent_id": f"{user_id}:{agent_id}",
                    "symbol": sym,
                    "side": side,
                    "kind": "marketplace",
                })
    except Exception:
        pass
    return out


def _treasury_liquidity_intents(tick_parity: int, symbols: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from backend.services.exchange_treasury_service import treasury_user_id
        from backend.services.exchange_sales_pool_service import sales_pool_user_id

        treasury = treasury_user_id()
        pool = sales_pool_user_id()
        for uid, kind in ((treasury, "treasury"), (pool, "sales_pool")):
            wallet = ex.get_wallet(uid)
            for sym in symbols:
                sym = str(sym).upper()
                holding = float((wallet.get("assets") or {}).get(sym) or 0)
                if holding <= 0:
                    if tick_parity % 2 == 0:
                        out.append({"agent_id": uid, "symbol": sym, "side": "buy", "kind": kind})
                    continue
                out.append({"agent_id": uid, "symbol": sym, "side": "sell", "kind": kind})
    except Exception:
        pass
    return out


def _collect_intents(*, grid_cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    grid_cfg = grid_cfg or load_grid_config()
    intents: List[Dict[str, Any]] = []
    tick = _tick_parity()
    per_agent = max(1, int(grid_cfg.get("intents_per_agent") or 2))

    try:
        from backend.services.crypto_exchange_agent_service import list_agents

        for a in list_agents().get("agents") or []:
            if not a.get("enabled", True):
                continue
            aid = str(a.get("id") or "").strip()
            if not aid:
                continue
            for offset in range(per_agent):
                it = _agent_side_intent(aid, tick, asset_offset=offset)
                if it:
                    intents.append(it)
    except Exception:
        pass

    if grid_cfg.get("include_arb_agents", True):
        cfg = conn.load_connectors_config()
        for agent in cfg.get("arbitrage_agents") or []:
            if not isinstance(agent, dict):
                continue
            intents.extend(_arb_agent_intents(agent, tick, intents_per_agent=per_agent))

    if grid_cfg.get("include_extended_agents", True):
        intents.extend(_extended_agent_intents(tick))

    if grid_cfg.get("include_marketplace_agents", True):
        intents.extend(_marketplace_agent_intents(tick))

    mesh_symbols = [str(s).upper() for s in (grid_cfg.get("mesh_symbols") or []) if s]
    if grid_cfg.get("include_treasury_liquidity", True):
        intents.extend(_treasury_liquidity_intents(tick, mesh_symbols or ["USDC", "USDT", "BTC", "ETH"]))

    return intents


def _partition_intents(intents: List[Dict[str, Any]]) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
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
    return buyers, sellers


def _execute_match(
    buyer: Dict[str, Any],
    seller: Dict[str, Any],
    sym: str,
    *,
    trade_mn2: float,
    treasury: str,
) -> Optional[Dict[str, Any]]:
    from backend.services.exchange_treasury_service import stash_profit_usd

    price = max(ex._price_usd(sym), 1e-9)
    mn2_price = max(ex._price_in_quote(sym, "MN2"), 1e-9)
    asset = ex._asset_map().get(sym) or {}
    min_trade = float(asset.get("min_trade") or 0)
    qty = round(max(trade_mn2 / mn2_price, min_trade), 8)
    if qty <= 0:
        return None

    buyer_id = str(buyer.get("agent_id") or "")
    seller_id = str(seller.get("agent_id") or "")
    if not buyer_id or not seller_id or buyer_id == seller_id:
        return None

    qid_s = uuid.uuid4().hex[:16]
    qid_b = uuid.uuid4().hex[:16]
    sell_res = ex.execute_swap(seller_id, qid_s, sym, "sell", qty, "MN2")
    if not sell_res.get("success"):
        return None
    buy_res = ex.execute_swap(buyer_id, qid_b, sym, "buy", qty, "MN2")
    if not buy_res.get("success"):
        return None

    spread_usd = round(qty * price * 0.001, 4)
    if spread_usd > 0:
        stash_profit_usd(
            spread_usd,
            source="daemon_mesh",
            agent_id=f"{buyer_id}:{seller_id}",
            mode="internal",
        )

    ex._audit(
        "daemon_mesh_match",
        user_id=treasury,
        amount_usd=spread_usd,
        symbol=sym,
        buyer=buyer_id,
        seller=seller_id,
    )
    return {
        "symbol": sym,
        "quantity": qty,
        "buyer": buyer_id,
        "seller": seller_id,
        "buyer_kind": buyer.get("kind"),
        "seller_kind": seller.get("kind"),
        "spread_usd": spread_usd,
    }


def _match_round(
    buyers: Dict[str, List[Dict[str, Any]]],
    sellers: Dict[str, List[Dict[str, Any]]],
    symbols: List[str],
    *,
    trade_mn2: float,
    treasury: str,
    max_matches: int,
    existing_count: int,
) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for sym in symbols:
        sym = str(sym).upper()
        bl = buyers.get(sym) or []
        sl = sellers.get(sym) or []
        while bl and sl and (existing_count + len(matches)) < max_matches:
            b, s = bl.pop(0), sl.pop(0)
            row = _execute_match(b, s, sym, trade_mn2=trade_mn2, treasury=treasury)
            if row:
                matches.append(row)
    return matches


def run_grid_tick(*, max_matches: Optional[int] = None) -> Dict[str, Any]:
    """Run the full agent grid: collect intents from all fleets and match in rounds."""
    from backend.services.exchange_treasury_service import treasury_user_id

    grid_cfg = load_grid_config()
    if not grid_cfg.get("enabled", True):
        return {"success": True, "skipped": True, "reason": "mesh_disabled"}

    cap = int(max_matches if max_matches is not None else grid_cfg.get("max_matches") or 25)
    rounds = max(1, int(grid_cfg.get("rounds_per_tick") or 4))
    trade_mn2 = float(grid_cfg.get("trade_mn2") or 3.5)

    intents = _collect_intents(grid_cfg=grid_cfg)
    buyers, sellers = _partition_intents(intents)
    mesh_symbols = [str(s).upper() for s in (grid_cfg.get("mesh_symbols") or []) if s]
    if not mesh_symbols:
        mesh_symbols = sorted(set(buyers) | set(sellers))

    treasury = treasury_user_id()
    all_matches: List[Dict[str, Any]] = []
    agents_involved: Set[str] = set()

    for _ in range(rounds):
        if len(all_matches) >= cap:
            break
        round_matches = _match_round(
            buyers,
            sellers,
            mesh_symbols,
            trade_mn2=trade_mn2,
            treasury=treasury,
            max_matches=cap,
            existing_count=len(all_matches),
        )
        for m in round_matches:
            agents_involved.add(str(m.get("buyer") or ""))
            agents_involved.add(str(m.get("seller") or ""))
        all_matches.extend(round_matches)

    mesh_profit_usd = round(sum(float(m.get("spread_usd") or 0) for m in all_matches), 4)
    by_kind: Dict[str, int] = {}
    for m in all_matches:
        for key in ("buyer_kind", "seller_kind"):
            k = str(m.get(key) or "unknown")
            by_kind[k] = by_kind.get(k, 0) + 1

    return {
        "success": True,
        "matched_at": _iso(),
        "match_count": len(all_matches),
        "mesh_profit_usd": mesh_profit_usd,
        "matches": all_matches,
        "intent_count": len(intents),
        "rounds_run": rounds,
        "agents_involved": len(agents_involved),
        "by_kind": by_kind,
        "grid_config": {
            "max_matches": cap,
            "rounds_per_tick": rounds,
            "trade_mn2": trade_mn2,
        },
    }


def run_mesh_tick(*, max_matches: int = 25) -> Dict[str, Any]:
    """Backward-compatible entry — delegates to the expanded grid tick."""
    return run_grid_tick(max_matches=max_matches)
