"""Profit intelligence — turn raw signals + positions into ranked recommendations and a
projected profit map, with an AI-style summary.

Pure/heuristic by default (fully testable, no network). If an LLM hook is configured
(``TRADER_LLM=1`` + the site's assist API, or an OpenAI key), ``ai_summary`` can call it;
otherwise it returns a transparent heuristic summary labelled "(heuristic)".
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


_FEE_FLOOR_BPS = 6.0     # rough taker fee floor a real edge must clear
_STRONG_BPS = 15.0
_CONSIDER_BPS = 8.0


def _clamp(v: float, lo: float, hi: float) -> float:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


def recommend(signals: List[Dict[str, Any]], *, order_size_usd: float = 10.0,
              cycles_per_day: int = 12,
              forum_intel: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Rank actionable signals by expected profit; attach recommendation, confidence, and risk.

    Improvements: input clamping, per-(type,symbol) dedup (best edge wins), a 0-100 confidence
    score, monthly projection, and a liquidity/venue risk flag.
    ``forum_intel`` (optional): {SYMBOL: {"sentiment": -1..1, "mentions": int}} to nudge scores.
    """
    forum_intel = forum_intel or {}
    order_size_usd = _clamp(order_size_usd, 1.0, 100000.0)
    cycles_per_day = int(_clamp(cycles_per_day, 1, 2000))

    best: Dict[tuple, Dict[str, Any]] = {}
    for s in signals or []:
        if not isinstance(s, dict) or not s.get("actionable"):
            continue
        sym = str(s.get("symbol") or "").upper()
        if not sym:
            continue
        is_arb = s.get("type") == "arbitrage"
        edge_bps = _clamp(s.get("net_bps") if is_arb else s.get("spread_bps") or 0, -10000, 100000)
        per_cycle = round(order_size_usd * (edge_bps / 10000.0), 6)
        daily = round(per_cycle * cycles_per_day, 4)
        fi = forum_intel.get(sym) or {}
        sentiment = _clamp(fi.get("sentiment") or 0, -1, 1)
        mentions = int(_clamp(fi.get("mentions") or 0, 0, 100000))
        score = edge_bps * (1 + 0.15 * sentiment) + min(mentions, 50) * 0.1
        # Confidence: how far above the fee floor, plus a small forum boost, 0-100.
        margin = edge_bps - _FEE_FLOOR_BPS
        confidence = int(round(_clamp(margin * 3.0 + min(mentions, 30) * 0.5 + sentiment * 10, 0, 100)))
        # Liquidity/venue risk heuristic: NonKYC/illiquid alt routes are higher risk.
        route_txt = (f"{s.get('buy_venue')}->{s.get('sell_venue')}" if is_arb else str(s.get("venue") or ""))
        risk = "high" if ("nonkyc" in route_txt.lower() or "xeggex" in route_txt.lower()) else "medium" if is_arb else "low"

        if edge_bps >= _STRONG_BPS and score >= _STRONG_BPS:
            rec, reason = "strong", f"{edge_bps:.1f} bps clears fees with margin"
        elif edge_bps >= _CONSIDER_BPS:
            rec, reason = "consider", f"{edge_bps:.1f} bps — thin after fees, size small"
        else:
            rec, reason = "skip", f"{edge_bps:.1f} bps below fee floor"
        if sentiment:
            reason += f"; forum {sentiment:+.2f} ({mentions} mentions)"
        if risk == "high":
            reason += "; illiquid venue — slippage risk"

        row = {
            "symbol": sym, "type": s.get("type"), "route": route_txt,
            "edge_bps": round(edge_bps, 2),
            "expected_per_cycle_usd": per_cycle,
            "projected_daily_usd": daily,
            "projected_monthly_usd": round(daily * 30, 2),
            "confidence": confidence, "risk": risk,
            "score": round(score, 2), "recommendation": rec, "reason": reason,
        }
        key = (row["type"], sym)
        if key not in best or row["edge_bps"] > best[key]["edge_bps"]:
            best[key] = row

    out = list(best.values())
    out.sort(key=lambda r: r["score"], reverse=True)
    return out


def combine_profit(signals: List[Dict[str, Any]], grid_state: Dict[str, Any], *,
                   order_size_usd: float = 10.0, cycles_per_day: int = 12) -> Dict[str, Any]:
    """Combine live signals (projected) with grid state (realized) into one profit map."""
    realized = 0.0
    realized_by_market: Dict[str, float] = {}
    for k, s in (grid_state or {}).items():
        r = float(s.get("realized_pnl_usd") or 0)
        realized += r
        realized_by_market[k] = round(r, 6)

    recs = recommend(signals, order_size_usd=order_size_usd, cycles_per_day=cycles_per_day)
    projected_daily = round(sum(r["projected_daily_usd"] for r in recs if r["recommendation"] != "skip"), 4)

    sources = []
    for r in recs:
        if r["recommendation"] == "skip":
            continue
        sources.append({"source": f"{r['type']}:{r['symbol']}", "route": r["route"],
                        "projected_daily_usd": r["projected_daily_usd"], "recommendation": r["recommendation"]})
    sources.sort(key=lambda x: x["projected_daily_usd"], reverse=True)

    return {
        "generated_at": _iso(),
        "realized_pnl_usd": round(realized, 6),
        "realized_by_market": realized_by_market,
        "projected_daily_usd": projected_daily,
        "projected_monthly_usd": round(projected_daily * 30, 2),
        "sources": sources,
        "actionable_count": len(sources),
    }


def ai_summary(profit_map: Dict[str, Any], recs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Human-readable 'where is my profit' summary. LLM when configured, else heuristic."""
    realized = float(profit_map.get("realized_pnl_usd") or 0)
    proj = float(profit_map.get("projected_daily_usd") or 0)
    proj_m = float(profit_map.get("projected_monthly_usd") or proj * 30)
    top = recs[0] if recs else None
    top3 = ", ".join(f"{r['symbol']} {r['edge_bps']:.0f}bps" for r in recs[:3]) if recs else "none"
    heuristic = (
        f"Realized so far: ${realized:.2f}. Projected ~${proj:.2f}/day (~${proj_m:.0f}/mo) from "
        f"{profit_map.get('actionable_count', 0)} actionable setup(s). "
        + (f"Best now: {top['symbol']} ({top['route']}) {top['edge_bps']:.1f} bps, "
           f"{top['confidence']}% confidence, {top['risk']} risk — {top['recommendation']}. "
           if top else "No actionable edge right now. ")
        + f"Top setups: {top3}. "
        + "Grid/MM books small wins in ranging markets and loses in trends; arbitrage only "
          "fires when a spread clears fees."
    )
    if os.environ.get("TRADER_LLM", "").strip() in ("1", "true", "yes"):
        try:
            text = _llm_summary(profit_map, recs)
            if text:
                return {"source": "llm", "summary": text}
        except Exception:
            pass
    return {"source": "heuristic", "summary": heuristic}


def _llm_summary(profit_map: Dict[str, Any], recs: List[Dict[str, Any]]) -> Optional[str]:
    """Optional LLM call via the site's assist API (best-effort)."""
    site = (os.environ.get("SITE_URL") or "").rstrip("/")
    key = os.environ.get("SITE_ADMIN_KEY") or ""
    if not site:
        return None
    try:
        import requests
        prompt = (f"Summarize trading profit for the owner in 2 sentences. Realized "
                  f"${profit_map.get('realized_pnl_usd')}, projected daily "
                  f"${profit_map.get('projected_daily_usd')}. Top setups: "
                  f"{[r['symbol'] + ' ' + str(r['edge_bps']) + 'bps' for r in recs[:3]]}.")
        r = requests.post(site + "/api/assist/copy",
                          headers={"X-Exchange-Admin-Key": key, "Content-Type": "application/json"},
                          json={"kind": "summary", "prompt": prompt}, timeout=8)
        j = r.json()
        return j.get("text") or j.get("copy") or j.get("result")
    except Exception:
        return None
