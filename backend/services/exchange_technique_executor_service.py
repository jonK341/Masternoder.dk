"""Technique executor — turn pbook's scored techniques into live actions.

Wired into the hunter arm (and callable from pbook / cron). Applies a safe
ordered stack: residual-edge gate → funding techniques → size-to-funded →
optional quote-bridge, then hands a prepared opportunity back for execution.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services.exchange_profit_order_book_service import (
    LEG_TECHNIQUES,
    _apply_technique,
    score_techniques_for_deal,
)

_STATE_PATH = os.path.join(ex._DATA_DIR, "technique_executor_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "technique_executor_ledger.jsonl")

# Live-executable techniques (others stay advisory / post-trade).
_EXEC_ORDER = (
    "profit_floor_kill",
    "stale_route_cooldown",
    "recheck_regime_deweight",  # residual-edge gate
    "prefund_buy_quote",
    "prefund_sell_inventory",
    "quote_bridge_rotation",
    "size_to_funded",
    "micro_split_fills",
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cfg_float(key: str, default: float) -> float:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def executor_enabled() -> bool:
    raw = os.environ.get("TECH_EXECUTOR_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def residual_edge_bps(net_bps: float, mid_skew_bps: float) -> float:
    """Legacy raw residue (net − |mid_skew|). Prefer ``cutting_edge`` for decisions."""
    return float(net_bps or 0) - abs(float(mid_skew_bps or 0))


def _micro_spread_bps(ask: float, bid: float) -> float:
    a = float(ask or 0)
    b = float(bid or 0)
    if a <= 0 or b <= 0 or a < b:
        return 0.0
    mid = (a + b) / 2.0
    if mid <= 0:
        return 0.0
    return (a - b) / mid * 10000.0


def cutting_edge(
    *,
    net_bps: float,
    mid_skew_bps: float = 0.0,
    buy_ask: float = 0.0,
    buy_bid: float = 0.0,
    sell_ask: float = 0.0,
    sell_bid: float = 0.0,
    est_profit_usd: float = 0.0,
    fire_floor_bps: Optional[float] = None,
    latch_min_bps: Optional[float] = None,
    min_profit_usd: Optional[float] = None,
) -> Dict[str, Any]:
    """One score, three bands — simpler cutting edge for fire / latch / skip.

    ``cut_bps = net − max(0, |skew| − local_noise)`` where local_noise is the
    average half micro-spread on both venues. We only penalize mid-skew *beyond*
    each book's own spread, so tight books keep more edge and phantoms still die.

    Bands:
    * ``fire``  — cut clears floor and profit clears dust → taker path
    * ``latch`` — net still fat but cut thin → wait / maker
    * ``skip``  — neither
    """
    net = float(net_bps or 0)
    skew = abs(float(mid_skew_bps or 0))
    buy_micro = _micro_spread_bps(buy_ask, buy_bid)
    sell_micro = _micro_spread_bps(sell_ask, sell_bid)
    # Average half-spread across venues = noise already inside mid_skew.
    local_noise = 0.5 * (0.5 * buy_micro + 0.5 * sell_micro)
    penalized_skew = max(0.0, skew - local_noise)
    cut = net - penalized_skew
    fire_floor = float(
        fire_floor_bps if fire_floor_bps is not None else _cfg_float("TECH_RESIDUAL_EDGE_BPS", 12.0)
    )
    latch_min = float(
        latch_min_bps if latch_min_bps is not None else _cfg_float("CUTTING_LATCH_MIN_BPS", 25.0)
    )
    min_profit = float(
        min_profit_usd if min_profit_usd is not None else _cfg_float("TECH_EXEC_MIN_PROFIT_USD", 0.02)
    )
    profit = float(est_profit_usd or 0)
    tight = buy_micro <= _cfg_float("CUTTING_TIGHT_MICRO_BPS", 40.0) and sell_micro <= _cfg_float(
        "CUTTING_TIGHT_MICRO_BPS", 40.0
    )
    # Slightly softer floor when both books are tight (less phantom risk).
    effective_floor = fire_floor * (0.75 if tight else 1.0)

    # Profit gate only when a real estimate is present (unknown → don't block band).
    profit_ok = True if profit <= 0 else profit >= min_profit
    if cut >= effective_floor and profit_ok and net > 0:
        band = "fire"
        reason = None
    elif net >= latch_min and cut < effective_floor:
        band = "latch"
        reason = "thin_cut_wait_skew"
    else:
        band = "skip"
        reason = "phantom_skew_no_residual" if cut < effective_floor else "below_profit_floor"

    return {
        "ok": band == "fire",
        "band": band,
        "cut_bps": round(cut, 2),
        "residual_bps": round(cut, 2),  # alias for older callers
        "floor_bps": round(effective_floor, 2),
        "fire_floor_bps": fire_floor,
        "net_bps": round(net, 2),
        "mid_skew_bps": round(skew, 2),
        "local_noise_bps": round(local_noise, 2),
        "buy_micro_bps": round(buy_micro, 2),
        "sell_micro_bps": round(sell_micro, 2),
        "tight_books": tight,
        "est_profit_usd": round(profit, 6),
        "reason": reason,
    }


def residual_edge_ok(
    *,
    net_bps: float,
    mid_skew_bps: float,
    floor_bps: Optional[float] = None,
    buy_ask: float = 0.0,
    buy_bid: float = 0.0,
    sell_ask: float = 0.0,
    sell_bid: float = 0.0,
    est_profit_usd: float = 0.0,
) -> Dict[str, Any]:
    """Compat wrapper — fire band of ``cutting_edge``."""
    return cutting_edge(
        net_bps=net_bps,
        mid_skew_bps=mid_skew_bps,
        buy_ask=buy_ask,
        buy_bid=buy_bid,
        sell_ask=sell_ask,
        sell_bid=sell_bid,
        est_profit_usd=est_profit_usd,
        fire_floor_bps=floor_bps,
    )


def narrow_cutting_edge(
    opps: Sequence[Dict[str, Any]],
    *,
    top_n: Optional[int] = None,
    bands: Sequence[str] = ("fire", "latch"),
) -> List[Dict[str, Any]]:
    """Score + keep only the sharpest few deals (default top 3 fire/latch)."""
    n = int(top_n if top_n is not None else _cfg_float("CUTTING_EDGE_TOP_N", 3.0))
    n = max(1, n)
    want = {str(b) for b in bands}
    scored: List[Dict[str, Any]] = []
    for opp in opps:
        if not isinstance(opp, dict):
            continue
        edge = cutting_edge(
            net_bps=float(opp.get("net_bps") or 0),
            mid_skew_bps=float(opp.get("mid_skew_bps") or 0),
            buy_ask=float(opp.get("buy_ask") or 0),
            buy_bid=float(opp.get("buy_bid") or 0),
            sell_ask=float(opp.get("sell_ask") or 0),
            sell_bid=float(opp.get("sell_bid") or 0),
            est_profit_usd=float(opp.get("est_profit_usd") or 0),
        )
        row = dict(opp)
        row["cutting_edge"] = edge
        row["cut_bps"] = edge["cut_bps"]
        row["residual_bps"] = edge["cut_bps"]
        row["edge_band"] = edge["band"]
        if edge["band"] in want:
            scored.append(row)
    scored.sort(
        key=lambda o: (
            1 if o.get("edge_band") == "fire" else 0,
            float(o.get("cut_bps") or -999),
            float(o.get("est_profit_usd") or 0),
        ),
        reverse=True,
    )
    return scored[:n]


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "executor"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _load_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _save_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _funding_snapshot(opp: Dict[str, Any], *, min_live_usd: float) -> Dict[str, Any]:
    prepared = arb.prepare_live_opportunity(
        opp,
        configured_usd=float(opp.get("notional_usd") or 15.0),
        buffer_pct=0.03,
        min_live_usd=min_live_usd,
    )
    return {
        "ok": bool(prepared.get("ok")),
        "reason": prepared.get("reason"),
        "max_funded_usd": prepared.get("max_funded_usd"),
        "requested_usd": prepared.get("requested_usd"),
        "prepared": prepared,
    }


def execute_techniques_for_opportunity(
    opp: Dict[str, Any],
    *,
    agent_id: str = "arb_tech_executor",
    raise_symbols: Optional[Sequence[str]] = None,
    mid_skew_bps: float = 0.0,
    min_bps: Optional[float] = None,
    min_profit: Optional[float] = None,
    max_techniques: int = 3,
    force: bool = False,
) -> Dict[str, Any]:
    """Run the live technique stack for one opportunity (hunter / pbook / cron)."""
    if not executor_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "executor_disabled"}

    min_bps_v = float(min_bps if min_bps is not None else _cfg_float("TECH_EXEC_MIN_BPS", 12.0))
    min_profit_v = float(min_profit if min_profit is not None else _cfg_float("TECH_EXEC_MIN_PROFIT_USD", 0.02))
    min_live = _cfg_float("TECH_EXEC_MIN_LIVE_USD", 10.0)
    symbols = list(raise_symbols or [])
    if opp.get("symbol"):
        symbols = [str(opp["symbol"]).upper()] + [s for s in symbols if s != str(opp["symbol"]).upper()]

    edge = cutting_edge(
        net_bps=float(opp.get("net_bps") or 0),
        mid_skew_bps=float(mid_skew_bps or opp.get("mid_skew_bps") or 0),
        buy_ask=float(opp.get("buy_ask") or 0),
        buy_bid=float(opp.get("buy_bid") or 0),
        sell_ask=float(opp.get("sell_ask") or 0),
        sell_bid=float(opp.get("sell_bid") or 0),
        est_profit_usd=float(opp.get("est_profit_usd") or min_profit_v),
        fire_floor_bps=_cfg_float("TECH_RESIDUAL_EDGE_BPS", 12.0),
        min_profit_usd=min_profit_v,
    )
    funding = _funding_snapshot(opp, min_live_usd=min_live)
    scored = score_techniques_for_deal(
        opp,
        funding=funding,
        state=_load_state(),
        min_bps=min_bps_v,
        min_profit=min_profit_v,
        mid_skew_bps=float(edge["mid_skew_bps"]),
    )

    out: Dict[str, Any] = {
        "success": False,
        "executor": True,
        "scanned_at": _iso(),
        "symbol": opp.get("symbol"),
        "route": f"{opp.get('buy_venue')}→{opp.get('sell_venue')}",
        "cutting_edge": edge,
        "residual_edge": edge,
        "funding_before": {
            "ok": funding.get("ok"),
            "max_funded_usd": funding.get("max_funded_usd"),
            "reason": funding.get("reason"),
        },
        "techniques_scored": [
            {"id": t.get("id"), "recommend": t.get("recommend"), "priority": t.get("priority")}
            for t in scored[:8]
        ],
        "applied": [],
        "opportunity": dict(opp),
        "ready": False,
        "skip_reason": None,
    }

    # Hard gates — fire only; latch/skip hand off without applying funding stack.
    if edge.get("band") != "fire":
        out["skip_reason"] = str(edge.get("reason") or edge.get("band") or "not_fire")
        out["edge_band"] = edge.get("band")
        _append(
            "skip",
            cut_bps=edge.get("cut_bps"),
            residual_bps=edge.get("residual_bps"),
            floor_bps=edge.get("floor_bps"),
            net_bps=edge.get("net_bps"),
            mid_skew_bps=edge.get("mid_skew_bps"),
            band=edge.get("band"),
            reason=out["skip_reason"],
        )
        return out

    floor_kill = next((t for t in scored if t.get("id") == "profit_floor_kill" and t.get("recommend")), None)
    if floor_kill:
        out["skip_reason"] = "profit_floor_kill"
        _append("skip", reason=out["skip_reason"])
        return out

    cooldown = next((t for t in scored if t.get("id") == "stale_route_cooldown" and t.get("recommend")), None)
    if cooldown:
        out["skip_reason"] = "stale_route_cooldown"
        _append("skip", reason=out["skip_reason"])
        return out

    # Apply recommended executable techniques in priority order.
    applied_n = 0
    for tech in scored:
        if applied_n >= max(1, int(max_techniques)):
            break
        tid = str(tech.get("id") or "")
        if tid not in _EXEC_ORDER or not tech.get("recommend"):
            continue
        if tid in ("profit_floor_kill", "stale_route_cooldown", "recheck_regime_deweight"):
            continue  # already gated
        if tid == "micro_split_fills":
            # Annotate only — hunter sizes clips at exec time.
            out["applied"].append({"technique": tid, "success": True, "skipped": True, "reason": "annotate_split"})
            out["opportunity"]["micro_split"] = True
            out["opportunity"]["clip_usd"] = _cfg_float("TECH_MICRO_CLIP_USD", 8.0)
            applied_n += 1
            continue

        result = _apply_technique(tid, out["opportunity"], agent_id=agent_id, raise_symbols=symbols)
        row = {"technique": tid, **(result if isinstance(result, dict) else {"result": result})}
        out["applied"].append(row)
        applied_n += 1
        _append("apply", technique=tid, success=bool(result.get("success")), skipped=bool(result.get("skipped")))
        if result.get("success") and not result.get("skipped") and tid in (
            "prefund_buy_quote", "prefund_sell_inventory", "quote_bridge_rotation",
        ):
            time.sleep(0.8)

    # Re-prepare after funding techniques.
    funding_after = _funding_snapshot(out["opportunity"], min_live_usd=min_live)
    out["funding_after"] = {
        "ok": funding_after.get("ok"),
        "max_funded_usd": funding_after.get("max_funded_usd"),
        "reason": funding_after.get("reason"),
    }
    if funding_after.get("ok"):
        prepared = funding_after.get("prepared") or {}
        trade = prepared.get("opportunity") or out["opportunity"]
        # Size-to-funded annotation
        if any(a.get("technique") == "size_to_funded" for a in out["applied"]):
            max_f = float(funding_after.get("max_funded_usd") or trade.get("notional_usd") or 0)
            if max_f > 0:
                trade = dict(trade)
                trade["notional_usd"] = min(float(trade.get("notional_usd") or max_f), max_f)
        out["opportunity"] = trade
        out["ready"] = True
        out["success"] = True
        out["skip_reason"] = None
    else:
        out["skip_reason"] = str(funding_after.get("reason") or "still_unfunded")
        out["success"] = any(bool(a.get("success")) for a in out["applied"])

    state = _load_state()
    state["updated_at"] = _iso()
    state["last"] = {
        "symbol": out.get("symbol"),
        "ready": out.get("ready"),
        "skip_reason": out.get("skip_reason"),
        "applied": [a.get("technique") for a in out.get("applied") or []],
        "residual_bps": edge.get("residual_bps"),
    }
    state["exec_count"] = int(state.get("exec_count") or 0) + 1
    _save_state(state)
    return out


def run_technique_executor_tick(*, force: bool = False) -> Dict[str, Any]:
    """Cron / daemon tick: take pbook top (or hunter board) and execute techniques."""
    if not executor_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "executor_disabled", "limb": "executor"}

    book = ex._read_json(os.path.join(ex._DATA_DIR, "profit_order_book.json"), {})
    top5 = book.get("top5") if isinstance(book, dict) else None
    top = top5[0] if isinstance(top5, list) and top5 and isinstance(top5[0], dict) else None
    if not top:
        board = ex._read_json(os.path.join(ex._DATA_DIR, "spread_hunter_board.json"), {})
        gaps = board.get("gaps") if isinstance(board, dict) else None
        top = gaps[0] if isinstance(gaps, list) and gaps and isinstance(gaps[0], dict) else None

    if not top:
        return {
            "success": True,
            "limb": "executor",
            "skip_reason": "no_top_deal",
            "summary": "ready=no skip=no_top_deal",
        }

    opp = {
        "symbol": top.get("symbol"),
        "buy_venue": top.get("buy_venue"),
        "sell_venue": top.get("sell_venue"),
        "buy_ask": top.get("buy_ask"),
        "sell_bid": top.get("sell_bid"),
        "notional_usd": top.get("notional_usd") or 15.0,
        "net_bps": top.get("net_bps"),
        "est_profit_usd": top.get("est_profit_usd"),
        "mid_skew_bps": top.get("mid_skew_bps"),
        "profitable": True,
    }
    res = execute_techniques_for_opportunity(
        opp,
        agent_id=(os.environ.get("TECH_EXECUTOR_AGENT_ID") or "arb_tech_executor").strip(),
        mid_skew_bps=float(top.get("mid_skew_bps") or 0),
        force=force,
    )
    techs = ",".join(a.get("technique") or "?" for a in (res.get("applied") or [])[:3]) or "-"
    summary = (
        f"ready={'yes' if res.get('ready') else 'no'} "
        f"sym={res.get('symbol') or '?'} "
        f"resid={((res.get('residual_edge') or {}).get('residual_bps'))} "
        f"tech={techs}"
    )
    if res.get("skip_reason"):
        summary += f" skip={res['skip_reason']}"
    res["summary"] = summary
    res["limb"] = "executor"
    return res


def technique_catalog() -> List[Dict[str, Any]]:
    return list(LEG_TECHNIQUES)
