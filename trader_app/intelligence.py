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


def recommend(signals: List[Dict[str, Any]], *, order_size_usd: float = 10.0,
              cycles_per_day: int = 12,
              forum_intel: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Rank actionable signals by expected profit; attach a recommendation + reason.

    ``forum_intel`` (optional): {SYMBOL: {"sentiment": -1..1, "mentions": int}} to nudge scores.
    """
    forum_intel = forum_intel or {}
    out: List[Dict[str, Any]] = []
    for s in signals or []:
        if not isinstance(s, dict) or not s.get("actionable"):
            continue
        sym = str(s.get("symbol") or "").upper()
        edge_bps = float(s.get("net_bps") if s.get("type") == "arbitrage" else s.get("spread_bps") or 0)
        # Expected profit per executed cycle, and a rough daily projection.
        per_cycle = round(order_size_usd * (edge_bps / 10000.0), 6)
        daily = round(per_cycle * cycles_per_day, 4)
        fi = forum_intel.get(sym) or {}
        sentiment = float(fi.get("sentiment") or 0)
        mentions = int(fi.get("mentions") or 0)
        # Score blends edge with forum sentiment (small nudge) and a mentions confidence.
        score = edge_bps * (1 + 0.15 * sentiment) + min(mentions, 50) * 0.1
        if edge_bps >= 15 and score >= 15:
            rec, reason = "strong", f"{edge_bps:.1f} bps edge clears fees with margin"
        elif edge_bps >= 8:
            rec, reason = "consider", f"{edge_bps:.1f} bps edge — thin after fees, size small"
        else:
            rec, reason = "skip", f"{edge_bps:.1f} bps edge below fee floor"
        if sentiment:
            reason += f"; forum sentiment {sentiment:+.2f} ({mentions} mentions)"
        out.append({
            "symbol": sym, "type": s.get("type"),
            "route": (f"{s.get('buy_venue')}->{s.get('sell_venue')}" if s.get("type") == "arbitrage"
                      else s.get("venue")),
            "edge_bps": round(edge_bps, 2),
            "expected_per_cycle_usd": per_cycle,
            "projected_daily_usd": daily,
            "score": round(score, 2),
            "recommendation": rec, "reason": reason,
        })
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
    top = recs[0] if recs else None
    heuristic = (
        f"Realized so far: ${realized:.2f}. Projected ~${proj:.2f}/day from "
        f"{profit_map.get('actionable_count', 0)} actionable setup(s). "
        + (f"Best right now: {top['symbol']} ({top['route']}) at {top['edge_bps']:.1f} bps "
           f"— {top['recommendation']}. " if top else "No actionable edge right now. ")
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
