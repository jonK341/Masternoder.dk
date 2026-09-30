"""Profit trade baselines — predicted vs executed rows for rotation, arb, fast_ext."""
from __future__ import annotations

import json
import os
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_BASELINE_PATH = os.path.join(ex._DATA_DIR, "profit_trade_baselines.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _parse_ts(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _read_baselines(*, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not os.path.isfile(_BASELINE_PATH):
        return []
    rows: List[Dict[str, Any]] = []
    with open(_BASELINE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    if limit and len(rows) > limit:
        return rows[-limit:]
    return rows


def record_baseline_trade(
    predicted: Dict[str, Any],
    executed: Dict[str, Any],
    *,
    source: str,
    route: Optional[Dict[str, Any]] = None,
    net_bps_at_exec: Optional[float] = None,
    realized_pnl_usd: Optional[float] = None,
    baseline_id: Optional[str] = None,
) -> str:
    """Append one baseline row linking prediction to execution outcome."""
    bid = baseline_id or _short_id()
    row: Dict[str, Any] = {
        "ts": _iso(),
        "baseline_id": bid,
        "source": str(source or "unknown"),
        "predicted": {
            "action_label": str(predicted.get("action_label") or predicted.get("label") or ""),
            "amount_usd": round(float(predicted.get("amount_usd") or 0), 2),
            "expected_unlock_bps": float(predicted.get("expected_unlock_bps") or predicted.get("priority_score") or 0),
            "top25_items": list(predicted.get("top25_items") or []),
        },
        "executed": {
            "success": bool(executed.get("success")),
            "mode": str(executed.get("mode") or ""),
            "fill_usd": round(float(executed.get("fill_usd") or executed.get("notional_usd") or 0), 2),
            "order_id": str(executed.get("order_id") or ""),
            "trade_id": str(executed.get("trade_id") or ""),
        },
        "route": {
            "agent_id": str((route or {}).get("agent_id") or ""),
            "symbol": str((route or {}).get("symbol") or ""),
            "buy_venue": str((route or {}).get("buy_venue") or ""),
            "sell_venue": str((route or {}).get("sell_venue") or ""),
        },
        "net_bps_at_exec": round(float(net_bps_at_exec), 2) if net_bps_at_exec is not None else None,
        "realized_pnl_usd": round(float(realized_pnl_usd), 4) if realized_pnl_usd is not None else None,
    }
    ex._append_jsonl(_BASELINE_PATH, row)
    try:
        from backend.services.exchange_profit_path_service import record_event

        record_event(
            phase="baseline",
            agent_id=row["route"]["agent_id"] or "profit_baseline",
            strategy=str(source),
            symbol=row["route"]["symbol"],
            mode=row["executed"]["mode"],
            decision="fill" if row["executed"]["success"] else "attempt",
            notional_usd=row["predicted"]["amount_usd"],
            execution={"baseline_id": bid, **row["executed"]},
            path_id=bid,
        )
    except Exception:
        pass
    try:
        from backend.services.exchange_profit_agent_skills_service import on_baseline_trade_event

        on_baseline_trade_event(row)
    except Exception:
        pass
    return bid


def list_baselines(
    *,
    hours: float = 168,
    source: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Return recent baseline rows filtered by age and optional source."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=float(hours))
    rows = _read_baselines()
    out: List[Dict[str, Any]] = []
    for row in reversed(rows):
        ts = _parse_ts(str(row.get("ts") or ""))
        if ts and ts < cutoff:
            continue
        if source and str(row.get("source") or "") != source:
            continue
        out.append(row)
        if len(out) >= max(1, int(limit)):
            break
    out.reverse()
    return {
        "success": True,
        "hours": hours,
        "source": source,
        "count": len(out),
        "baselines": out,
    }


def record_arb_baseline(
    opp: Dict[str, Any],
    exec_res: Dict[str, Any],
    *,
    source: str = "arb",
    agent_id: str = "",
) -> Optional[str]:
    """Record baseline row for spatial arb / fast_ext execution."""
    if not exec_res.get("success"):
        return None
    net_bps = float(opp.get("net_bps") or 0)
    buy_o = exec_res.get("buy_order") or {}
    sell_o = exec_res.get("sell_order") or {}
    mode = str(exec_res.get("mode") or "")
    profit = float(exec_res.get("est_profit_usd") or 0)
    if profit <= 0 and net_bps > 0:
        notional = float(exec_res.get("notional_usd") or opp.get("notional_usd") or 0)
        if notional > 0:
            profit = round(notional * net_bps / 10000.0, 6)
    stash = exec_res.get("stash") or {}
    if mode == "live" and profit > 0 and not (stash.get("success") and not stash.get("skipped")):
        try:
            from backend.services.exchange_treasury_service import load_config, stash_profit_usd

            if load_config().get("auto_stash_on_trade", True):
                trade_id = ":".join(
                    i for i in (
                        str(buy_o.get("order_id") or ""),
                        str(sell_o.get("order_id") or ""),
                    ) if i
                )
                stash_profit_usd(
                    profit,
                    source="live_arbitrage",
                    agent_id=agent_id,
                    mode="live",
                    meta={
                        "symbol": opp.get("symbol"),
                        "buy_venue": opp.get("buy_venue"),
                        "sell_venue": opp.get("sell_venue"),
                        "net_bps": net_bps,
                        "trade_id": trade_id,
                        "baseline_backfill": True,
                        "source_tick": source,
                    },
                )
        except Exception:
            pass
    return record_baseline_trade(
        predicted={
            "action_label": f"{opp.get('symbol')} {opp.get('buy_venue')}→{opp.get('sell_venue')}",
            "amount_usd": opp.get("notional_usd"),
            "expected_unlock_bps": net_bps,
            "top25_items": ["arb_exec_zero"] if source == "rotation" else [],
        },
        executed={
            "success": True,
            "mode": exec_res.get("mode"),
            "fill_usd": exec_res.get("notional_usd") or opp.get("notional_usd"),
            "order_id": str(buy_o.get("order_id") or buy_o.get("id") or ""),
            "trade_id": str(sell_o.get("order_id") or sell_o.get("id") or exec_res.get("executed_at") or ""),
        },
        source=source,
        route={
            "agent_id": agent_id,
            "symbol": str(opp.get("symbol") or ""),
            "buy_venue": str(opp.get("buy_venue") or ""),
            "sell_venue": str(opp.get("sell_venue") or ""),
        },
        net_bps_at_exec=net_bps,
        realized_pnl_usd=float(exec_res.get("est_profit_usd") or 0) or None,
    )


def baseline_summary(*, hours: float = 168) -> Dict[str, Any]:
    """Aggregate baseline stats — counts by source, success rate, predicted unlock."""
    data = list_baselines(hours=hours, limit=10000)
    rows = data.get("baselines") or []
    by_source: Counter = Counter()
    success_by_source: Counter = Counter()
    total_predicted_unlock = 0.0
    success_count = 0
    for row in rows:
        src = str(row.get("source") or "unknown")
        by_source[src] += 1
        pred = row.get("predicted") or {}
        total_predicted_unlock += float(pred.get("expected_unlock_bps") or 0)
        exec_block = row.get("executed") or {}
        if exec_block.get("success"):
            success_count += 1
            success_by_source[src] += 1
    total = len(rows)
    return {
        "success": True,
        "hours": hours,
        "total": total,
        "success_count": success_count,
        "success_rate_pct": round(100.0 * success_count / total, 1) if total else 0.0,
        "total_predicted_unlock_bps": round(total_predicted_unlock, 2),
        "by_source": {
            src: {
                "count": by_source[src],
                "success_count": success_by_source[src],
                "success_rate_pct": round(100.0 * success_by_source[src] / by_source[src], 1)
                if by_source[src]
                else 0.0,
            }
            for src in sorted(by_source.keys())
        },
    }
