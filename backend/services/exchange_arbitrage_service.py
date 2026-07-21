"""Cross-venue margin scanner + paper arbitrage agents.

Computes the best buy/sell spread for each symbol across external venues (and the
internal exchange), nets out taker fees + transfer cost, and ranks profitable
opportunities. Paper agents "execute" the spread by crediting a per-agent profit
account — no real funds move until the live gates are satisfied.

Live trading gate: BOTH ``EXCHANGE_ARBITRAGE_LIVE=1`` AND a per-venue API key present
in the encrypted vault. This module never places real orders in Phase 1.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import external_exchange_connector_service as conn

_ACCOUNTS_DIR = os.path.join(ex._DATA_DIR, "agent_accounts")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def live_enabled() -> bool:
    cfg = conn.load_connectors_config()
    flag = cfg.get("live_env_flag") or "EXCHANGE_ARBITRAGE_LIVE"
    if str(os.environ.get(flag, "")).strip() != "1":
        return False
    try:
        from backend.services import mn2_spork_service as spork
        ok, _reason = spork.exchange_live_spork_ok()
        return ok
    except Exception:
        return True


def _effective_transfer_cost_bps(cfg: Dict[str, Any]) -> float:
    """Pre-funded inventory arb skips per-trade on-chain transfer — use lower cost in live mode."""
    if live_enabled():
        return float(cfg.get("prefunded_transfer_cost_bps") or cfg.get("transfer_cost_bps") or 20)
    return float(cfg.get("transfer_cost_bps") or 20)


def effective_min_margin_bps(cfg: Optional[Dict[str, Any]] = None) -> float:
    """Spatial arb threshold — env override aligns with fast rescan (EXCHANGE_FAST_MIN_BPS)."""
    cfg = cfg or conn.load_connectors_config()
    for key in ("EXCHANGE_ARB_MIN_BPS", "EXCHANGE_FAST_MIN_BPS"):
        env = os.environ.get(key, "").strip()
        if env:
            try:
                return float(env)
            except ValueError:
                pass
    return float(cfg.get("min_margin_bps") or 12)


def prepare_live_opportunity(
    opp: Dict[str, Any],
    *,
    configured_usd: float,
    buffer_pct: float = 0.03,
    min_live_usd: float = 10.0,
) -> Dict[str, Any]:
    """Scale notional to live balances and verify both arb legs can fund."""
    from backend.services import exchange_venue_api_service as vapi

    symbol = str(opp.get("symbol") or "").upper()
    buy_v = str(opp.get("buy_venue") or "")
    sell_v = str(opp.get("sell_venue") or "")
    buy_ask = float(opp.get("buy_ask") or 0)
    if buy_ask <= 0 or not symbol or not buy_v or not sell_v:
        return {"ok": False, "reason": "invalid_opportunity"}

    cap = vapi.max_funded_notional_usd(
        symbol, buy_v, sell_v, buy_ask, configured_usd=float(configured_usd), buffer_pct=buffer_pct,
    )
    scaled_notional = min(float(configured_usd), cap)
    if scaled_notional < min_live_usd:
        return {
            "ok": False,
            "reason": "insufficient_venue_balance",
            "max_funded_usd": round(cap, 2),
            "best": opp,
        }

    scaled = _scale_opportunity_notional(opp, scaled_notional)
    funding = vapi.opportunity_funded(scaled, buffer_pct=buffer_pct)
    if not funding.get("ok") and cap >= min_live_usd and scaled_notional > min_live_usd:
        for factor in (0.85, 0.7, 0.55):
            retry_notional = max(min_live_usd, round(scaled_notional * factor, 2))
            if retry_notional >= scaled_notional:
                continue
            scaled = _scale_opportunity_notional(opp, retry_notional)
            funding = vapi.opportunity_funded(scaled, buffer_pct=buffer_pct)
            if funding.get("ok"):
                break
    if not funding.get("ok"):
        return {
            "ok": False,
            "reason": "insufficient_venue_balance",
            "max_funded_usd": round(cap, 2),
            "funding": funding,
            "best": scaled,
        }
    return {
        "ok": True,
        "opportunity": scaled,
        "max_funded_usd": round(cap, 2),
        "funding": funding,
    }


def _live_api_ready_venues(venue_ids: List[str]) -> List[str]:
    """Drop venues whose private API fails (401, missing keys) during live scans."""
    if not live_enabled():
        return venue_ids
    from backend.services import exchange_venue_api_service as vapi
    ready: List[str] = []
    for vid in venue_ids:
        if vid == "internal":
            ready.append(vid)
            continue
        if not vapi.venue_has_credentials(vid):
            continue
        bal = vapi.get_account_balance(vid, dry_run=False)
        if bal.get("success"):
            ready.append(vid)
    return ready if len(ready) >= 2 or "internal" in ready else venue_ids


def _inventory_tradeable_symbols(
    venue_ids: List[str],
    symbols: List[str],
    *,
    min_quote_usd: float = 20.0,
    min_coin_usd: float = 12.0,
) -> List[str]:
    """Symbols where at least one venue can buy (quote) and one can sell (base coin)."""
    if not live_enabled():
        return symbols
    from backend.services import exchange_venue_api_service as vapi
    from backend.services.external_exchange_connector_service import fetch_ticker

    tradeable: List[str] = []
    external = [v for v in venue_ids if v != "internal"]
    for sym in symbols:
        can_buy = can_sell = False
        for vid in external:
            bals = vapi.parse_spot_balances(vid, dry_run=False)
            quote = vapi.venue_quote_asset(vid)
            if float(bals.get(quote) or 0) >= min_quote_usd:
                can_buy = True
            tick = fetch_ticker(vid, sym)
            mid = 0.0
            if tick and tick.get("bid"):
                mid = float(tick["bid"])
            coin = float(bals.get(sym) or 0)
            if mid > 0 and coin * mid >= min_coin_usd:
                can_sell = True
            elif coin >= 100 and sym in ("DOGE", "SHIB", "PEPE"):
                can_sell = True
        if can_buy and can_sell:
            tradeable.append(sym)
    return tradeable or symbols


def _internal_fee_bps() -> float:
    fees = (ex.load_config().get("fees") or {})
    return float(fees.get("taker_bps") or fees.get("taker") or 25)


def _account_path(agent_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(agent_id))
    return os.path.join(_ACCOUNTS_DIR, f"{safe}.json")


def read_account(agent_id: str) -> Dict[str, Any]:
    acct = ex._read_json(_account_path(agent_id), {})
    if not isinstance(acct, dict) or not acct:
        acct = {
            "agent_id": agent_id,
            "realized_profit_usd": 0.0,
            "trade_count": 0,
            "notional_traded_usd": 0.0,
            "by_venue": {},
            "wallet_label": "",
            "game_time_sec": 0,
            "ticks": 0,
            "agent_level": 1,
            "last_action": None,
            "created_at": _iso(),
        }
    return acct


def write_account(acct: Dict[str, Any]) -> None:
    ex._write_json(_account_path(acct["agent_id"]), acct)


def _prices_for_symbol(
    prices: Dict[str, Dict[str, Dict[str, float]]],
    symbol: str,
    venue_ids: List[str],
    vmap: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for vid in venue_ids:
        if vid == "internal":
            px = ex._price_usd(symbol)
            if px > 0:
                rows.append({"venue": "internal", "bid": px, "ask": px, "fee_bps": _internal_fee_bps()})
            continue
        t = (prices.get(vid) or {}).get(symbol)
        v = vmap.get(vid) or {}
        if t and t.get("bid", 0) > 0 and t.get("ask", 0) > 0:
            rows.append({
                "venue": vid,
                "bid": float(t["bid"]),
                "ask": float(t["ask"]),
                "fee_bps": float(v.get("fee_taker_bps") or 10),
            })
    return rows


def _best_opportunity(
    symbol: str,
    rows: List[Dict[str, Any]],
    *,
    transfer_cost_bps: float,
    notional_usd: float,
) -> Optional[Dict[str, Any]]:
    if len(rows) < 2:
        return None
    buy = min(rows, key=lambda r: r["ask"])      # cheapest place to buy
    sell = max(rows, key=lambda r: r["bid"])     # most expensive place to sell
    if buy["venue"] == sell["venue"] or buy["ask"] <= 0:
        return None
    gross_bps = (sell["bid"] - buy["ask"]) / buy["ask"] * 10000.0
    fee_bps = buy["fee_bps"] + sell["fee_bps"] + transfer_cost_bps
    net_bps = gross_bps - fee_bps
    return {
        "symbol": symbol,
        "buy_venue": buy["venue"],
        "buy_ask": round(buy["ask"], 8),
        "sell_venue": sell["venue"],
        "sell_bid": round(sell["bid"], 8),
        "gross_bps": round(gross_bps, 2),
        "fee_bps": round(fee_bps, 2),
        "net_bps": round(net_bps, 2),
        "notional_usd": round(notional_usd, 2),
        "est_profit_usd": round(notional_usd * net_bps / 10000.0, 4),
    }


_FORCE_ATTEMPT_MIN_BPS = 18.0


def _summarize_best_qualifying(
    actions: List[Dict[str, Any]],
    min_margin_bps: float,
) -> Dict[str, Any]:
    """Top agent by net_bps with threshold/funding context for ops logging."""
    best_action: Optional[Dict[str, Any]] = None
    best_nb = -999.0
    qualifying_pool: List[Dict[str, Any]] = []
    for action in actions:
        row = action.get("best") if isinstance(action.get("best"), dict) else {}
        nb = float(row.get("net_bps") or -999)
        if nb > best_nb:
            best_nb = nb
            best_action = action
        if nb >= min_margin_bps and float(row.get("est_profit_usd") or 0) > 0:
            qualifying_pool.append(action)
    if qualifying_pool:
        best_action = max(
            qualifying_pool,
            key=lambda a: float((a.get("best") or {}).get("net_bps") or 0),
        )
        best_nb = float((best_action.get("best") or {}).get("net_bps") or 0)
    elif best_nb < min_margin_bps:
        try:
            from backend.services.exchange_extended_profit_service import read_arb_threshold_state

            state = read_arb_threshold_state()
            state_net = float(state.get("best_net_bps") or 0)
            if state.get("ready") and state_net >= min_margin_bps:
                best_nb = state_net
                best_action = {
                    "agent_id": "arb_live_dual_farm",
                    "executed": False,
                    "reason": "global_threshold_ready",
                    "best": {
                        "symbol": state.get("top_symbol"),
                        "buy_venue": state.get("buy_venue"),
                        "sell_venue": state.get("sell_venue"),
                        "net_bps": state_net,
                        "est_profit_usd": float(state.get("est_profit_usd") or 0),
                    },
                }
        except Exception:
            pass
    if not best_action or best_nb < -900:
        return {
            "agent_id": None,
            "net_bps": None,
            "min_margin_bps": min_margin_bps,
            "funded": False,
            "qualifies": False,
            "reason": "no_scan",
        }
    row = best_action.get("best") or {}
    nb = float(row.get("net_bps") or 0)
    qualifies = nb >= min_margin_bps and float(row.get("est_profit_usd") or 0) > 0
    reason = str(
        best_action.get("reason")
        or (best_action.get("execution") or {}).get("error")
        or ""
    ).strip()
    funded = False
    if best_action.get("executed"):
        funded = True
    elif qualifies:
        if reason in ("insufficient_venue_balance", "insufficient_balance"):
            funded = False
        elif reason in ("below_threshold", "no_profitable_spread"):
            funded = False
        elif reason == "global_threshold_ready":
            from backend.services import exchange_venue_api_service as vapi
            sym = str(row.get("symbol") or "").upper()
            buy_v = str(row.get("buy_venue") or "")
            sell_v = str(row.get("sell_venue") or "")
            buy_ask = float(row.get("buy_ask") or 0)
            if sym and buy_v and sell_v and buy_ask > 0:
                cap = vapi.max_funded_notional_usd(
                    sym, buy_v, sell_v, buy_ask, configured_usd=100.0, buffer_pct=0.03,
                )
                funded = cap >= 10.0
            else:
                funded = True
        else:
            mf = best_action.get("max_funded_usd")
            funded = mf is None or float(mf or 0) >= 10.0
    return {
        "agent_id": best_action.get("agent_id"),
        "symbol": row.get("symbol"),
        "buy_venue": row.get("buy_venue"),
        "sell_venue": row.get("sell_venue"),
        "net_bps": round(nb, 2),
        "min_margin_bps": min_margin_bps,
        "funded": funded,
        "qualifies": qualifies,
        "reason": reason or None,
    }


def _attempt_global_best_live(
    actions: List[Dict[str, Any]],
    *,
    cfg: Dict[str, Any],
    min_margin_bps: float,
    default_notional: float,
    agent_id: str = "arb_live_dual_farm",
) -> Optional[Dict[str, Any]]:
    """Global scan + prepare_live_opportunity — same path as fast_arb_rescan."""
    if any(a.get("executed") for a in actions):
        return None
    force_floor = max(min_margin_bps, _FORCE_ATTEMPT_MIN_BPS)
    env_force = os.environ.get("EXCHANGE_ARB_FORCE_MIN_BPS", "").strip()
    if env_force:
        try:
            force_floor = max(min_margin_bps, float(env_force))
        except ValueError:
            pass

    summary = _summarize_best_qualifying(actions, min_margin_bps)
    top_nb = float(summary.get("net_bps") or 0)
    state_ready = False
    state_net = 0.0
    state: Dict[str, Any] = {}
    try:
        from backend.services.exchange_extended_profit_service import read_arb_threshold_state

        state = read_arb_threshold_state()
        state_net = float(state.get("best_net_bps") or 0)
        state_ready = bool(state.get("ready") and state_net >= min_margin_bps)
        if state_ready:
            top_nb = max(top_nb, state_net)
            force_floor = min(force_floor, min_margin_bps)
    except Exception:
        pass
    if not state_ready and top_nb < force_floor:
        return None

    agent_cfg = next(
        (a for a in (cfg.get("arbitrage_agents") or []) if isinstance(a, dict) and a.get("id") == agent_id),
        {},
    )
    venues = list(agent_cfg.get("venues") or ["binance", "nonkyc"])
    notional = float(agent_cfg.get("paper_trade_usd") or default_notional)

    from backend.services import exchange_venue_api_service as vapi
    vapi.refresh_venue_balances(venues, force=True)

    scan = scan_opportunities(venues=venues, notional_usd=notional)
    opps = [
        o for o in (scan.get("opportunities") or [])
        if float(o.get("net_bps") or 0) >= force_floor and float(o.get("est_profit_usd") or 0) > 0
    ]
    if not opps and state_ready:
        sym = str(state.get("top_symbol") or "").upper()
        buy_v = str(state.get("buy_venue") or "")
        sell_v = str(state.get("sell_venue") or "")
        if sym and buy_v and sell_v:
            sym_scan = scan_opportunities(
                symbols=[sym], venues=venues, notional_usd=notional,
            )
            for o in sym_scan.get("opportunities") or []:
                if str(o.get("symbol") or "").upper() == sym:
                    opps.append(dict(o))
            if not opps and state_net >= force_floor:
                buy_ask = 0.0
                try:
                    tick = conn.fetch_ticker(buy_v, sym)
                    if tick:
                        buy_ask = float(tick.get("ask") or tick.get("last") or 0)
                except Exception:
                    pass
                if buy_ask <= 0:
                    buy_ask = float(ex._price_usd(sym) or 0)
                opps.append({
                    "symbol": sym,
                    "buy_venue": buy_v,
                    "sell_venue": sell_v,
                    "net_bps": state_net,
                    "est_profit_usd": float(state.get("est_profit_usd") or 0.01),
                    "notional_usd": notional,
                    "buy_ask": buy_ask,
                    "sell_bid": buy_ask,
                })
    if not opps:
        seen: set = set()
        for action in actions:
            row = action.get("best")
            if not isinstance(row, dict):
                continue
            nb = float(row.get("net_bps") or 0)
            if nb < force_floor or float(row.get("est_profit_usd") or 0) <= 0:
                continue
            key = (row.get("symbol"), row.get("buy_venue"), row.get("sell_venue"))
            if key in seen:
                continue
            seen.add(key)
            opps.append(dict(row))
        opps.sort(key=lambda o: float(o.get("net_bps") or 0), reverse=True)
    if not opps:
        return {"executed": False, "forced_global": True, "reason": "no_qualifying_opps", "force_floor_bps": force_floor}

    from backend.services.exchange_live_execution_service import execute_spatial_arbitrage, book_agent_profit
    from backend.services.exchange_profit_path_service import record_execution, record_scan

    strategy = str(agent_cfg.get("strategy") or "spatial_arb")
    tick_mode = "live" if live_enabled() else "paper"

    for opp in opps[:3]:
        trade_opp = opp
        if live_enabled():
            prepared = prepare_live_opportunity(
                opp, configured_usd=notional, buffer_pct=0.03, min_live_usd=10.0,
            )
            if not prepared.get("ok"):
                continue
            trade_opp = prepared["opportunity"]
        path_id = record_scan(
            agent_id=agent_id, strategy=strategy, best=trade_opp,
            threshold_bps=min_margin_bps, mode=tick_mode, decision="attempt",
            notional_usd=float(trade_opp.get("notional_usd") or notional), venues=venues,
        )
        exec_res = execute_spatial_arbitrage(trade_opp, agent_id=agent_id)
        record_execution(
            path_id=path_id, agent_id=agent_id, opp=trade_opp, exec_res=exec_res,
            strategy=strategy, threshold_bps=min_margin_bps, venues=venues,
        )
        if exec_res.get("success"):
            try:
                from backend.services.exchange_profit_baseline_service import record_arb_baseline

                record_arb_baseline(trade_opp, exec_res, source="arb_force", agent_id=agent_id)
            except Exception:
                pass
        acct = book_agent_profit(agent_id, trade_opp, exec_res)
        action = acct.get("last_action") or {"agent_id": agent_id, "executed": exec_res.get("success")}
        if isinstance(action, dict):
            action["profit_path_id"] = path_id
            action["forced_global"] = True
            if not action.get("executed"):
                action["reason"] = str(exec_res.get("error") or "execution_failed")
        for i, existing in enumerate(actions):
            if existing.get("agent_id") == agent_id:
                actions[i] = action
                break
        else:
            actions.append(action)
        if exec_res.get("success"):
            return action
    return {
        "executed": False,
        "forced_global": True,
        "reason": "force_attempt_exhausted",
        "force_floor_bps": force_floor,
        "opp_count": len(opps),
    }


def _scale_opportunity_notional(opp: Dict[str, Any], notional_usd: float) -> Dict[str, Any]:
    old = float(opp.get("notional_usd") or 0)
    if old <= 0 or abs(old - notional_usd) < 0.01:
        return opp
    ratio = notional_usd / old
    scaled = dict(opp)
    scaled["notional_usd"] = round(notional_usd, 2)
    scaled["sized_notional_usd"] = round(notional_usd, 2)
    scaled["est_profit_usd"] = round(float(opp.get("est_profit_usd") or 0) * ratio, 4)
    return scaled


def scan_opportunities(
    symbols: Optional[List[str]] = None,
    venues: Optional[List[str]] = None,
    *,
    injected: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
    notional_usd: Optional[float] = None,
) -> Dict[str, Any]:
    cfg = conn.load_connectors_config()
    symbols = [str(s).upper() for s in (symbols or cfg.get("supported_symbols") or [])]
    vmap = conn._venue_map(cfg)
    venue_ids = venues or ([vid for vid, v in vmap.items() if v.get("enabled", True)] + ["internal"])
    venue_ids = _live_api_ready_venues(venue_ids)
    transfer_cost_bps = _effective_transfer_cost_bps(cfg)
    min_margin_bps = effective_min_margin_bps(cfg)
    notional = float(notional_usd or cfg.get("paper_trade_usd") or 250)

    fetched = conn.fetch_prices(
        symbols,
        [v for v in venue_ids if v != "internal"],
        injected=injected,
        use_cache=not live_enabled() if injected is None else False,
    )
    prices = fetched.get("prices") or {}

    opportunities: List[Dict[str, Any]] = []
    for sym in symbols:
        rows = _prices_for_symbol(prices, sym, venue_ids, vmap)
        opp = _best_opportunity(sym, rows, transfer_cost_bps=transfer_cost_bps, notional_usd=notional)
        if opp:
            opp["profitable"] = opp["net_bps"] >= min_margin_bps
            opportunities.append(opp)

    opportunities.sort(key=lambda o: o["net_bps"], reverse=True)
    return {
        "success": True,
        "scanned_at": _iso(),
        "source": fetched.get("source"),
        "min_margin_bps": min_margin_bps,
        "opportunity_count": len(opportunities),
        "profitable_count": sum(1 for o in opportunities if o["profitable"]),
        "opportunities": opportunities,
    }


def run_paper_tick(
    *,
    injected: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
    hot_symbols: Optional[List[str]] = None,
    active_agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Scan per-agent and credit paper profit for the best profitable opportunity."""
    cfg = conn.load_connectors_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "connectors_disabled"}
    vmap = conn._venue_map(cfg)
    transfer_cost_bps = _effective_transfer_cost_bps(cfg)
    min_margin_bps = effective_min_margin_bps(cfg)
    default_notional = float(cfg.get("paper_trade_usd") or 250)

    if live_enabled() and injected is None:
        from backend.services import exchange_venue_api_service as vapi
        venue_ids = [
            str(v["id"]) for v in (cfg.get("venues") or [])
            if isinstance(v, dict) and v.get("id") and v["id"] != "internal"
        ]
        vapi.refresh_venue_balances(venue_ids or ["binance", "nonkyc"], force=True)

    fetched = conn.fetch_prices(
        injected=injected,
        use_cache=not live_enabled() if injected is None else False,
    )
    prices = fetched.get("prices") or {}

    try:
        from backend.services.exchange_live_execution_service import sync_internal_prices_to_external_mid
        sync_internal_prices_to_external_mid(prices if not injected else None)
    except Exception:
        pass

    actions: List[Dict[str, Any]] = []

    for agent in cfg.get("arbitrage_agents") or []:
        if not isinstance(agent, dict):
            continue
        agent_id = str(agent.get("id") or "").strip()
        if not agent_id:
            continue
        if active_agent_id and agent_id != str(active_agent_id).strip():
            continue
        a_symbols = [str(s).upper() for s in (agent.get("symbols") or cfg.get("supported_symbols") or [])]
        try:
            from backend.services.exchange_profit_pair_search_service import resolve_agent_symbols

            a_symbols = resolve_agent_symbols(a_symbols, hot_symbols=hot_symbols)
        except Exception:
            pass
        a_venues = _live_api_ready_venues(list(agent.get("venues") or list(vmap.keys())))
        if live_enabled() and agent_id in ("arb_live_dual_farm", "arb_agent_meme"):
            a_symbols = _inventory_tradeable_symbols(a_venues, a_symbols)
        notional = float(agent.get("paper_trade_usd") or default_notional)

        best: Optional[Dict[str, Any]] = None
        for sym in a_symbols:
            rows = _prices_for_symbol(prices, sym, a_venues, vmap)
            opp = _best_opportunity(sym, rows, transfer_cost_bps=transfer_cost_bps, notional_usd=notional)
            if opp and (best is None or opp["net_bps"] > best["net_bps"]):
                best = opp

        acct = read_account(agent_id)
        acct["wallet_label"] = agent.get("wallet_label") or acct.get("wallet_label") or ""
        acct["ticks"] = int(acct.get("ticks") or 0) + 1
        acct["game_time_sec"] = int(acct.get("game_time_sec") or 0) + 3600
        acct["agent_level"] = 1 + int(acct.get("ticks") or 0) // 50
        from backend.services.exchange_profit_path_service import record_scan, record_execution
        strategy = str(agent.get("strategy") or "spatial_arb")
        tick_mode = "live" if live_enabled() else "paper"
        path_id = ""
        if best and best["net_bps"] >= min_margin_bps and best["est_profit_usd"] > 0:
            from backend.services.exchange_live_execution_service import execute_spatial_arbitrage, book_agent_profit
            trade_opp = best
            if live_enabled():
                prepared = prepare_live_opportunity(
                    best, configured_usd=notional, buffer_pct=0.03, min_live_usd=10.0,
                )
                if not prepared.get("ok"):
                    skip_reason = str(prepared.get("reason") or "insufficient_venue_balance")
                    path_id = record_scan(
                        agent_id=agent_id, strategy=strategy, best=prepared.get("best") or best,
                        threshold_bps=min_margin_bps, mode=tick_mode, decision="skip",
                        skip_reason=skip_reason, notional_usd=notional, venues=a_venues,
                    )
                    action = {
                        "agent_id": agent_id,
                        "executed": False,
                        "reason": skip_reason,
                        "best": prepared.get("best") or best,
                        "max_funded_usd": prepared.get("max_funded_usd"),
                        "funding": prepared.get("funding"),
                        "mode": "live",
                        "profit_path_id": path_id,
                    }
                    acct["last_action"] = action
                    write_account(acct)
                    actions.append(action)
                    continue
                trade_opp = prepared["opportunity"]
            path_id = record_scan(
                agent_id=agent_id, strategy=strategy, best=trade_opp,
                threshold_bps=min_margin_bps, mode=tick_mode, decision="attempt",
                notional_usd=float(trade_opp.get("notional_usd") or notional), venues=a_venues,
            )
            exec_res = execute_spatial_arbitrage(trade_opp, agent_id=agent_id)
            record_execution(
                path_id=path_id, agent_id=agent_id, opp=trade_opp, exec_res=exec_res,
                strategy=strategy, threshold_bps=min_margin_bps, venues=a_venues,
            )
            if exec_res.get("success"):
                try:
                    from backend.services.exchange_profit_baseline_service import record_arb_baseline

                    record_arb_baseline(trade_opp, exec_res, source="arb", agent_id=agent_id)
                except Exception:
                    pass
            acct = book_agent_profit(agent_id, trade_opp, exec_res)
            action = acct.get("last_action") or {"agent_id": agent_id, "executed": exec_res.get("success")}
            if isinstance(action, dict):
                action["profit_path_id"] = path_id
                if not action.get("executed"):
                    action["reason"] = str(
                        action.get("reason")
                        or (action.get("execution") or {}).get("error")
                        or "execution_failed"
                    )
        else:
            skip_reason = "no_profitable_spread"
            if best and best["net_bps"] < min_margin_bps:
                skip_reason = "below_threshold"
            path_id = record_scan(
                agent_id=agent_id, strategy=strategy, best=best,
                threshold_bps=min_margin_bps, mode=tick_mode, decision="skip",
                skip_reason=skip_reason, notional_usd=notional, venues=a_venues,
            )
            action = {"agent_id": agent_id, "executed": False, "reason": skip_reason,
                      "best": best, "mode": tick_mode, "profit_path_id": path_id}
            acct["last_action"] = action
        write_account(acct)
        actions.append(action)

    executed_count = sum(1 for a in actions if a.get("executed"))
    force_meta: Optional[Dict[str, Any]] = None
    if executed_count == 0:
        forced = _attempt_global_best_live(
            actions, cfg=cfg, min_margin_bps=min_margin_bps, default_notional=default_notional,
        )
        if forced:
            force_meta = forced if isinstance(forced, dict) else None
            if forced.get("executed"):
                executed_count = sum(1 for a in actions if a.get("executed"))

    best_qualifying = _summarize_best_qualifying(actions, min_margin_bps)

    global_best: Optional[Dict[str, Any]] = None
    for action in actions:
        row = action.get("best")
        if not isinstance(row, dict):
            continue
        nb = float(row.get("net_bps") or 0)
        if global_best is None or nb > float(global_best.get("net_bps") or 0):
            global_best = row
    try:
        from backend.services.exchange_extended_profit_service import write_arb_threshold_state

        write_arb_threshold_state(
            best=global_best, threshold_bps=min_margin_bps, source="exchange_arb_tick",
        )
    except Exception:
        pass

    out: Dict[str, Any] = {
        "success": True,
        "ticked_at": _iso(),
        "live": live_enabled(),
        "source": fetched.get("source"),
        "min_margin_bps": min_margin_bps,
        "best_qualifying": best_qualifying,
        "agent_count": len(actions),
        "executed_count": executed_count,
        "actions": actions,
        "force_attempt": force_meta,
    }
    if hot_symbols:
        out["hot_symbols"] = hot_symbols
    return out


def agent_accounts() -> Dict[str, Any]:
    cfg = conn.load_connectors_config()
    accounts: List[Dict[str, Any]] = []
    total_profit = 0.0
    for agent in cfg.get("arbitrage_agents") or []:
        if not isinstance(agent, dict) or not agent.get("id"):
            continue
        acct = read_account(str(agent["id"]))
        acct["name"] = agent.get("name") or agent["id"]
        total_profit += float(acct.get("realized_profit_usd") or 0)
        accounts.append(acct)
    return {
        "success": True,
        "agent_count": len(accounts),
        "total_realized_profit_usd": round(total_profit, 6),
        "accounts": accounts,
    }


def run_rebalance_tick(*, imbalance_ratio: float = 2.0) -> Dict[str, Any]:
    """Scan credentialed venue quote balances and flag cross-venue rebalance needs."""
    from backend.services import exchange_venue_api_service as vapi

    cfg = conn.load_connectors_config()
    venue_ids = [
        str(v["id"]) for v in (cfg.get("venues") or [])
        if isinstance(v, dict) and v.get("id") and v["id"] != "internal"
    ]
    quotes: List[Dict[str, Any]] = []
    for vid in venue_ids:
        if not vapi.venue_has_credentials(vid):
            continue
        bals = vapi.parse_spot_balances(vid, dry_run=False)
        quote = vapi.venue_quote_asset(vid)
        free = float(bals.get(quote) or 0)
        quotes.append({"venue_id": vid, "quote_asset": quote, "free_quote": round(free, 4)})

    if len(quotes) < 2:
        return {
            "success": True,
            "skipped": True,
            "reason": "need_two_credentialed_venues",
            "venues": quotes,
        }

    amounts = [q["free_quote"] for q in quotes if q["free_quote"] > 0]
    if not amounts:
        return {"success": True, "skipped": True, "reason": "no_quote_inventory", "venues": quotes}

    avg = sum(amounts) / len(amounts)
    rich = max(quotes, key=lambda q: q["free_quote"])
    poor = min(quotes, key=lambda q: q["free_quote"])
    ratio = (rich["free_quote"] / poor["free_quote"]) if poor["free_quote"] > 0 else float("inf")
    move_usd = round(max(0.0, rich["free_quote"] - avg), 4)
    rebalance_needed = ratio >= imbalance_ratio and move_usd >= 10.0
    result = {
        "success": True,
        "live": live_enabled(),
        "rebalance_needed": rebalance_needed,
        "imbalance_ratio": round(ratio, 4) if ratio != float("inf") else None,
        "target_quote_per_venue": round(avg, 4),
        "suggested_move_usd": move_usd if rebalance_needed else 0.0,
        "from_venue": rich if rebalance_needed else None,
        "to_venue": poor if rebalance_needed else None,
        "venues": quotes,
        "ticked_at": _iso(),
    }
    if rebalance_needed:
        ex._audit(
            "arb_rebalance_tick",
            from_venue=rich["venue_id"],
            to_venue=poor["venue_id"],
            move_usd=move_usd,
            ratio=round(ratio, 4),
        )
        if not live_enabled() and "internal" in {rich["venue_id"], poor["venue_id"]}:
            try:
                from backend.services.exchange_live_execution_service import _internal_swap
                sym = "USDC" if rich["quote_asset"] in ("USDC", "USDT") else rich["quote_asset"]
                qty = round(move_usd / max(1.0, avg), 8)
                swap = _internal_swap("platform_treasury", sym, "sell" if rich["venue_id"] == "internal" else "buy", qty)
                result["internal_swap"] = swap
                result["swap_attempted"] = True
            except Exception as exc:
                result["internal_swap"] = {"success": False, "error": str(exc)}
    return result


def arbitrage_overview() -> Dict[str, Any]:
    from backend.services import exchange_secrets_vault_service as vault
    venues = conn.list_venues()
    accounts = agent_accounts()
    return {
        "success": True,
        "live": live_enabled(),
        "mode": venues.get("mode"),
        "venue_count": venues.get("venue_count"),
        "agent_count": accounts.get("agent_count"),
        "total_realized_profit_usd": accounts.get("total_realized_profit_usd"),
        "vault": vault.vault_status(),
    }
