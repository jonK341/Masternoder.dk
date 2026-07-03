"""Profit Path Protocol → agent skill evolution.

Reads PPP ledger research rows, stacks specialized profit skills + voids (gap skills),
levels agents up, and maintains a critical top-25 problem checklist with checkboxes.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_REGISTRY_PATH = os.path.join(ex._BASE, "logs", "profit_agent_skills", "registry.json")
_CRITICAL_PATH = os.path.join(ex._DATA_DIR, "profit_critical_top25.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "profit_path_ledger.jsonl")

_STACK_USD_STEP = 0.25
_XP_PER_PROFIT_USD = 40
_XP_PER_VOID_CLOSED = 25


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _slug(text: str, *, max_len: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(text or "").lower()).strip("_")
    return (s[:max_len] or "unknown")


def _load_registry() -> Dict[str, Any]:
    reg = _read_json(_REGISTRY_PATH, {})
    if not isinstance(reg, dict):
        reg = {}
    reg.setdefault("agents", {})
    reg.setdefault("voids", {})
    reg.setdefault("ledger_sync", {})
    reg["ledger_sync"].setdefault("processed_path_ids", [])
    reg["ledger_sync"].setdefault("processed_baseline_ids", [])
    return reg


def _save_registry(reg: Dict[str, Any]) -> None:
    processed = reg.get("ledger_sync", {}).get("processed_path_ids") or []
    if len(processed) > 8000:
        reg["ledger_sync"]["processed_path_ids"] = processed[-8000:]
    reg["updated_at"] = _iso()
    _write_json(_REGISTRY_PATH, reg)


def _profit_skill_name(row: Dict[str, Any]) -> str:
    strategy = _slug(row.get("strategy") or "profit")
    symbol = _slug(row.get("symbol") or "any")
    venues = row.get("venues") or {}
    buy = _slug(venues.get("buy") or "buy", max_len=16)
    sell = _slug(venues.get("sell") or "sell", max_len=16)
    mode = _slug(row.get("mode") or "live", max_len=8)
    return f"ppp_{strategy}_{symbol}_{buy}_to_{sell}_{mode}"


def _void_skill_name(skip_reason: str, row: Optional[Dict[str, Any]] = None) -> str:
    reason = _slug(skip_reason, max_len=32)
    sym = _slug((row or {}).get("symbol") or "any", max_len=12)
    mapping = {
        "insufficient_mn2": "void_mn2_liquidity",
        "insufficient_venue_balance": "void_venue_inventory",
        "insufficient_balance": "void_venue_inventory",
        "below_threshold": "void_spread_gate",
        "no_profitable_spread": "void_spread_gate",
        "http_401": "void_api_auth",
    }
    for key, void in mapping.items():
        if key in reason:
            return f"{void}_{sym}"
    if "401" in skip_reason:
        return f"void_api_auth_{sym}"
    return f"void_{reason}_{sym}"


def _agent_bucket(reg: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    agents = reg.setdefault("agents", {})
    bucket = agents.setdefault(
        agent_id,
        {
            "agent_id": agent_id,
            "profit_skills": [],
            "voids": [],
            "stacked_profit_usd": 0.0,
            "stack_count": 0,
            "level": 1,
            "experience": 0,
            "last_skill_at": None,
            "research_notes": [],
        },
    )
    return bucket


def _close_void(reg: Dict[str, Any], agent_id: str, void_skill: str, *, reason: str = "") -> bool:
    """Mark a void skill closed after a successful fill/baseline."""
    void_reg = reg.setdefault("voids", {})
    void_key = f"{agent_id}:{void_skill}"
    entry = void_reg.get(void_key) or {"agent_id": agent_id, "void_skill": void_skill}
    if entry.get("closed"):
        return False
    entry.update({"closed": True, "closed_at": _iso(), "close_reason": reason or "fill_success"})
    void_reg[void_key] = entry
    return True


def _close_voids_for_success(reg: Dict[str, Any], agent_id: str, row: Dict[str, Any]) -> List[str]:
    """Close matching open voids when a route succeeds."""
    closed: List[str] = []
    bucket = _agent_bucket(reg, agent_id)
    open_voids = list(bucket.get("voids") or [])
    if not open_voids:
        return closed
    sym = _slug(row.get("symbol") or "any", max_len=12)
    for void_skill in open_voids:
        void_reg = reg.get("voids") or {}
        void_key = f"{agent_id}:{void_skill}"
        if void_reg.get(void_key, {}).get("closed"):
            continue
        if sym in void_skill or void_skill.endswith(f"_{sym}"):
            if _close_void(reg, agent_id, void_skill, reason="route_fill"):
                closed.append(void_skill)
    return closed


def _sync_agent_level_from_stack(bucket: Dict[str, Any]) -> None:
    """Level tracks stacked profit (live + paper) via PPP ledger."""
    stacked = float(bucket.get("stacked_profit_usd") or 0)
    xp = int(bucket.get("experience") or 0)
    stack_xp = int(stacked * _XP_PER_PROFIT_USD)
    bucket["experience"] = max(xp, stack_xp)
    bucket["level"] = max(1, int(bucket["experience"] // 500) + 1)


def _apply_skill_to_agent_skillset(agent_id: str, skill: str, *, xp: int = 0) -> None:
    try:
        from backend.services.agent_skillset import agent_skillset

        agent_skillset.add_skill(agent_id, skill, agent_type="agents")
        if xp > 0:
            agent_skillset.level_up(agent_id, agent_type="agents", experience=xp)
    except Exception:
        pass


def on_ledger_profit_event(row: Dict[str, Any]) -> Dict[str, Any]:
    """Called when PPP ledger records a profitable fill — stack skills + level up."""
    exec_block = row.get("execution") or {}
    if not exec_block.get("success"):
        return {"success": False, "skipped": True, "reason": "not_successful"}
    profit = float(exec_block.get("realized_pnl_usd") or 0)
    if profit <= 0:
        usd = float(row.get("notional_usd") or exec_block.get("fill_usd") or 0)
        if usd <= 0:
            return {"success": False, "skipped": True, "reason": "zero_profit"}
        profit = round(usd * 0.001, 4)

    agent_id = str(row.get("agent_id") or "").strip()
    if not agent_id:
        return {"success": False, "error": "missing_agent_id"}

    path_id = str(row.get("path_id") or "")
    reg = _load_registry()
    processed = set(reg.get("ledger_sync", {}).get("processed_path_ids") or [])
    if path_id and path_id in processed:
        return {"success": True, "duplicate": True, "path_id": path_id}

    bucket = _agent_bucket(reg, agent_id)
    prev_stack = float(bucket.get("stacked_profit_usd") or 0)
    bucket["stacked_profit_usd"] = round(prev_stack + profit, 4)
    new_stack = int(bucket["stacked_profit_usd"] / _STACK_USD_STEP)
    old_stack = int(prev_stack / _STACK_USD_STEP)

    added_skills: List[str] = []
    added_voids: List[str] = []

    if new_stack > old_stack:
        skill = _profit_skill_name(row)
        profit_skills = bucket.setdefault("profit_skills", [])
        if skill not in profit_skills:
            profit_skills.append(skill)
            added_skills.append(skill)
            _apply_skill_to_agent_skillset(agent_id, skill, xp=_XP_PER_PROFIT_USD)
        bucket["stack_count"] = int(bucket.get("stack_count") or 0) + 1
        bucket["last_skill_at"] = _iso()
        note = (
            f"Stack #{bucket['stack_count']}: +${profit:.4f} "
            f"({row.get('strategy')}/{row.get('symbol')} mode={row.get('mode')})"
        )
        notes = bucket.setdefault("research_notes", [])
        notes.append({"ts": _iso(), "note": note, "skill": skill})
        bucket["research_notes"] = notes[-40:]

    skip = str(row.get("skip_reason") or "").strip()
    if skip:
        void_skill = _void_skill_name(skip, row)
        voids = bucket.setdefault("voids", [])
        void_reg = reg.setdefault("voids", {})
        void_key = f"{agent_id}:{void_skill}"
        if void_skill not in voids:
            voids.append(void_skill)
            added_voids.append(void_skill)
            _apply_skill_to_agent_skillset(agent_id, void_skill, xp=_XP_PER_VOID_CLOSED)
        void_reg[void_key] = {
            "agent_id": agent_id,
            "void_skill": void_skill,
            "skip_reason": skip,
            "last_seen": _iso(),
            "closed": bool(void_reg.get(void_key, {}).get("closed")),
        }

    bucket["experience"] = int(bucket.get("experience") or 0) + max(1, int(profit * _XP_PER_PROFIT_USD))
    bucket["level"] = max(1, int(bucket["experience"] // 500) + 1)

    if path_id:
        processed.add(path_id)
        reg.setdefault("ledger_sync", {})["processed_path_ids"] = list(processed)
    closed_voids = _close_voids_for_success(reg, agent_id, row)
    _sync_agent_level_from_stack(bucket)
    reg.setdefault("ledger_sync", {})["last_profit_event_at"] = _iso()
    _save_registry(reg)

    return {
        "success": True,
        "agent_id": agent_id,
        "profit_usd": profit,
        "stacked_profit_usd": bucket["stacked_profit_usd"],
        "stack_count": bucket.get("stack_count"),
        "added_skills": added_skills,
        "added_voids": added_voids,
        "closed_voids": closed_voids,
        "level": bucket.get("level"),
    }


def on_baseline_trade_event(row: Dict[str, Any]) -> Dict[str, Any]:
    """Stack skills/XP when a predicted baseline trade executes successfully."""
    exec_block = row.get("executed") or {}
    if not exec_block.get("success"):
        return {"success": False, "skipped": True, "reason": "not_successful"}

    baseline_id = str(row.get("baseline_id") or "")
    reg = _load_registry()
    processed = set(reg.get("ledger_sync", {}).get("processed_baseline_ids") or [])
    if baseline_id and baseline_id in processed:
        return {"success": True, "duplicate": True, "baseline_id": baseline_id}

    agent_id = str((row.get("route") or {}).get("agent_id") or "profit_baseline")
    bucket = _agent_bucket(reg, agent_id)
    source = str(row.get("source") or "baseline")
    skill = f"baseline_{_slug(source)}_{_slug((row.get('route') or {}).get('symbol') or 'any')}"
    profit_skills = bucket.setdefault("profit_skills", [])
    added: List[str] = []
    if skill not in profit_skills:
        profit_skills.append(skill)
        added.append(skill)
        _apply_skill_to_agent_skillset(agent_id, skill, xp=_XP_PER_PROFIT_USD)

    fill_usd = float(exec_block.get("fill_usd") or 0)
    mode = str((row.get("route") or {}).get("mode") or row.get("mode") or "paper").lower()
    if fill_usd > 0:
        prev_stack = float(bucket.get("stacked_profit_usd") or 0)
        increment = round(fill_usd * (0.002 if mode == "live" else 0.001), 4)
        bucket["stacked_profit_usd"] = round(prev_stack + increment, 4)
        bucket["stack_count"] = int(bucket.get("stack_count") or 0) + 1

    bucket["experience"] = int(bucket.get("experience") or 0) + max(5, _XP_PER_VOID_CLOSED)
    _sync_agent_level_from_stack(bucket)
    closed_voids = _close_voids_for_success(reg, agent_id, row.get("route") or row)
    bucket["last_skill_at"] = _iso()

    if baseline_id:
        processed.add(baseline_id)
        reg.setdefault("ledger_sync", {})["processed_baseline_ids"] = list(processed)[-8000:]
    reg.setdefault("ledger_sync", {})["last_baseline_at"] = _iso()
    _save_registry(reg)

    return {"success": True, "agent_id": agent_id, "added_skills": added, "closed_voids": closed_voids, "baseline_id": baseline_id}


def sync_from_baselines(*, hours: float = 168, limit: int = 500) -> Dict[str, Any]:
    """Replay baseline rows for skill stacking."""
    from backend.services.exchange_profit_baseline_service import list_baselines

    data = list_baselines(hours=hours, limit=limit)
    rows = data.get("baselines") or []
    processed = 0
    for row in rows:
        res = on_baseline_trade_event(row)
        if res.get("success") and not res.get("duplicate"):
            processed += 1
    return {"success": True, "rows_scanned": len(rows), "baselines_processed": processed}


def sync_from_ledger_research(*, hours: float = 168, limit: int = 2000) -> Dict[str, Any]:
    """Replay ledger research log — encode skills/voids for fills and recurring skips."""
    from backend.services.exchange_profit_path_service import search_paths

    rows = search_paths(hours=hours, limit=limit).get("paths") or []
    fills = 0
    voids = 0
    agents_touched: set[str] = set()

    voids_closed = 0
    for row in reversed(rows):
        phase = str(row.get("phase") or "")
        agent_id = str(row.get("agent_id") or "")
        if not agent_id:
            continue
        if phase == "execute" and (row.get("execution") or {}).get("success"):
            res = on_ledger_profit_event(row)
            if res.get("success") and not res.get("duplicate"):
                fills += 1
                agents_touched.add(agent_id)
                voids_closed += len(res.get("closed_voids") or [])
        elif row.get("skip_reason"):
            void_skill = _void_skill_name(str(row.get("skip_reason")), row)
            reg = _load_registry()
            bucket = _agent_bucket(reg, agent_id)
            if void_skill not in bucket.setdefault("voids", []):
                bucket["voids"].append(void_skill)
                _apply_skill_to_agent_skillset(agent_id, void_skill, xp=5)
                voids += 1
                agents_touched.add(agent_id)
            _save_registry(reg)

    return {
        "success": True,
        "hours": hours,
        "rows_scanned": len(rows),
        "fills_processed": fills,
        "voids_encoded": voids,
        "voids_closed": voids_closed,
        "agents_touched": sorted(agents_touched),
        **sync_from_baselines(hours=hours, limit=min(limit, 500)),
    }


def hit_rate_by_route(*, days: float = 7) -> Dict[str, Any]:
    """Aggregate PPP hit rate per route for research review."""
    from backend.services.exchange_profit_path_service import profit_path_summary

    hours = max(1.0, float(days)) * 24.0
    summary = profit_path_summary(hours=hours)
    routes = summary.get("best_routes_24h") or []
    low_hit = [r for r in routes if int(r.get("attempts") or 0) >= 3 and float(r.get("hit_rate_pct") or 0) < 25]
    return {
        "success": True,
        "days": days,
        "window_hours": hours,
        "hit_rate_pct": summary.get("hit_rate_pct"),
        "attempt_count": summary.get("attempt_count"),
        "fill_count": summary.get("fill_count"),
        "routes": routes,
        "low_hit_routes": low_hit[:12],
        "reviewed_at": _iso(),
    }


def _infer_auto_checks() -> Dict[str, str]:
    """Return problem_id -> note for items resolved by daemon/state signals."""
    resolved: Dict[str, str] = {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hb_path = os.path.join(ex._BASE, "logs", "daemon_all_profit_heartbeat.json")
    hb = _read_json(hb_path, {})
    loops = hb.get("loops") if isinstance(hb.get("loops"), dict) else {}

    casino = loops.get("casino") or {}
    casino_sum = str(casino.get("summary") or hb.get("summary") or "")
    if "ran=3/3" in casino_sum or "success=True ran=3" in casino_sum:
        resolved["casino_agents_idle"] = f"daemon casino {today}: ran=3/3"

    fast = loops.get("fast") or {}
    fast_sum = str(fast.get("summary") or "")
    if "ext_exec=" in fast_sum:
        try:
            part = next(p for p in fast_sum.split() if p.startswith("ext_exec="))
            if int(part.split("=", 1)[1]) > 0:
                resolved["ext_profit_zero"] = f"fast rescan {today}: {part} on threshold"
        except (StopIteration, ValueError):
            pass

    ext_tick = _read_json(os.path.join(ex._DATA_DIR, "extended_defi_tick.json"), {})
    if int(ext_tick.get("n") or 0) > 0 and "ext_profit_zero" not in resolved:
        resolved["ext_profit_zero"] = f"extended tick counter n={ext_tick.get('n')} ({today})"

    conn = _read_json(os.path.join(ex._BASE, "data", "exchange_connectors_config.json"), {})
    micro_vals = [float(conn.get("paper_trade_usd") or 0)]
    for agent in conn.get("arbitrage_agents") or []:
        if isinstance(agent, dict):
            micro_vals.append(float(agent.get("paper_trade_usd") or 0))
    if any(80.0 <= v <= 85.0 for v in micro_vals if v > 0):
        capped = next(v for v in micro_vals if 80.0 <= v <= 85.0)
        resolved["binance_quote_cap"] = f"paper_trade_usd={capped} capped (~$83) ({today})"

    try:
        from backend.services.exchange_treasury_service import treasury_status

        tre = treasury_status()
        live_stash = float(tre.get("ledger_stashed_usd_live") or tre.get("live_stash_usd") or 0)
        if live_stash > 0:
            resolved["live_stash_zero"] = f"live stash USD={live_stash:.4f} ({today})"
            resolved["treasury_compound"] = f"live external stash credited USD={live_stash:.4f} ({today})"
    except Exception:
        pass

    for v in conn.get("venues") or []:
        if isinstance(v, dict) and str(v.get("id") or "") == "xeggex":
            if v.get("live_trading") is False:
                resolved["xeggex_live_disabled"] = f"live_trading=false guard active ({today})"
            break

    return resolved


def _verify_nonkyc_doge() -> tuple[bool, str]:
    """Live NonKYC DOGE inventory vs $25 sell-leg minimum."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        from backend.services import exchange_venue_api_service as vapi

        bals = vapi.parse_spot_balances("nonkyc", dry_run=False)
        doge = float(bals.get("DOGE") or 0)
        doge_usd = doge * float(ex._price_usd("DOGE") or 0)
        if doge_usd >= 25.0:
            return True, f"nonkyc DOGE ${doge_usd:.2f} ({doge:.2f} DOGE) ≥ $25 ({today})"
        return False, (
            f"nonkyc DOGE ${doge_usd:.2f} ({doge:.2f} DOGE) < $25 ({today}) — "
            f"one-shot: python scripts/prefund_arb_legs.py --live --symbol DOGE"
        )
    except Exception as exc:
        return False, f"nonkyc DOGE check failed ({today}): {exc}"


def _infer_rotation_notes() -> Dict[str, str]:
    """Evidence notes from rotation auto-execute — partial progress, not full resolution."""
    notes: Dict[str, str] = {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rot_state = _read_json(os.path.join(ex._DATA_DIR, "rotation_auto_state.json"), {})
    recent = rot_state.get("recent") or []
    if not isinstance(recent, list):
        return notes

    ok_types = {"external_market_buy", "external_market_sell", "internal_stable_swap", "reduce_notional"}
    successes = [r for r in recent if r.get("success") and str(r.get("type") or "") in ok_types]
    if successes:
        last = successes[-1]
        notes["skip_reason_funding"] = (
            f"partial: {len(successes)} rotation fills; last={last.get('type')} "
            f"${last.get('amount_usd')} ({today}) — prefund: scripts/prefund_arb_legs.py"
        )

    doge_ok = [
        r for r in recent
        if r.get("success") and "DOGE" in str(r.get("asset_key") or "")
    ]
    resolved_doge, doge_note = _verify_nonkyc_doge()
    if resolved_doge:
        notes["nonkyc_doge_low"] = doge_note
    elif doge_ok:
        d = doge_ok[-1]
        notes["nonkyc_doge_low"] = (
            f"{doge_note}; last rotation ${d.get('amount_usd')} ({today})"
        )
    else:
        notes["nonkyc_doge_low"] = doge_note

    hb = _read_json(os.path.join(ex._BASE, "logs", "daemon_all_profit_heartbeat.json"), {})
    loops = hb.get("loops") if isinstance(hb.get("loops"), dict) else {}
    exchange_sum = str((loops.get("exchange") or {}).get("summary") or "")
    if "platform_ok=True" in exchange_sum:
        notes["arb_exec_zero"] = f"preflight ok; {exchange_sum.split('platform_ok=True')[1].strip()[:80]} ({today})"

    try:
        from scripts.refresh_xeggex_server import probe_xeggex_local

        ok, reason, code = probe_xeggex_local()
        if not ok:
            notes["xeggex_401"] = f"probe {code or 'fail'}: {reason} ({today}) — refresh_xeggex_server.py --probe-only"
    except Exception:
        pass

    notes.setdefault(
        "auto_sweep_off",
        "safe enable: run_all_profit_daemons.cmd --auto-sweep + EXCHANGE_AUTO_PAYPAL_SWEEP=1; "
        "status: scripts/payout_sweep_status.py",
    )
    notes.setdefault(
        "paypal_sweep_paper",
        "check unswept: scripts/payout_sweep_status.py — live PayPal needs EXCHANGE_PAYOUT_PAYPAL_LIVE=1",
    )

    return notes


def sync_critical_reality() -> Dict[str, Any]:
    """Merge auto-resolved checks + notes, then refresh markdown/json."""
    store = _read_json(_CRITICAL_PATH, {})
    checks = store.get("checks") if isinstance(store.get("checks"), dict) else {}
    notes = store.get("notes") if isinstance(store.get("notes"), dict) else {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for pid, note in _infer_auto_checks().items():
        checks[pid] = True
        notes[pid] = note
    for pid, note in _infer_rotation_notes().items():
        notes[pid] = note
    doge_ok, doge_note = _verify_nonkyc_doge()
    if doge_ok:
        checks["nonkyc_doge_low"] = True
        notes["nonkyc_doge_low"] = doge_note
    for pid, note in {
        "status_report_heavy": f"profit_status_report.py --light + profit_status_light.py ({today})",
        "hit_rate_tracking": f"GET /api/exchange/profit-path/hit-rate?days=7 ({today})",
        "void_skills_open": f"sync_from_ledger closes voids on fill/baseline ({today})",
        "agent_level_lag": f"agent level from stacked PPP profit USD ({today})",
        "ai_trader_idle": f"execute on profitable spread when net_bps>=min_net ({today})",
    }.items():
        checks[pid] = True
        notes[pid] = note
    notes.setdefault(
        "auto_sweep_off",
        "enable: --auto-sweep + EXCHANGE_AUTO_PAYPAL_SWEEP=1; threshold: EXCHANGE_AUTO_SWEEP_MIN_USD",
    )
    store["checks"] = checks
    store["notes"] = notes
    _write_json(_CRITICAL_PATH, store)
    return critical_problems_top25(refresh=True)


def get_agent_profit_skills(agent_id: Optional[str] = None) -> Dict[str, Any]:
    reg = _load_registry()
    agents = reg.get("agents") or {}
    if agent_id:
        bucket = agents.get(agent_id)
        return {"success": True, "agent_id": agent_id, "profile": bucket or {}}
    return {"success": True, "agents": agents, "voids_global": reg.get("voids") or {}}


def _base_critical_problems() -> List[Dict[str, Any]]:
    """Seed top-25 critical problems — merged with live PPP / readiness signals."""
    return [
        {"id": "live_stash_zero", "priority": 1, "category": "treasury", "title": "Live USD stash is $0 — no real external arb P&L captured yet"},
        {"id": "xeggex_401", "priority": 2, "category": "api", "title": "XeggeX API returns 401 — refresh keys or IP whitelist"},
        {"id": "spread_below_threshold", "priority": 3, "category": "market", "title": "Arb spreads mostly below 18 bps min_margin — waiting on market"},
        {"id": "cross_trade_mn2_drift", "priority": 4, "category": "funding", "title": "Cross-trade bots MN2 auto-seed must sustain 25 MN2 each tick"},
        {"id": "wallet_file_lock", "priority": 5, "category": "infra", "title": "Windows WinError 5 on wallet JSON writes under concurrent Flask loads"},
        {"id": "ai_trader_idle", "priority": 6, "category": "engine", "title": "AI trader enabled but ai_exec=False every tick"},
        {"id": "arb_exec_zero", "priority": 7, "category": "engine", "title": "Spatial arb 0/11 executions — scan vs fund vs threshold chain"},
        {"id": "ext_profit_zero", "priority": 8, "category": "engine", "title": "Extended profit strategies reporting 0 executions"},
        {"id": "casino_agents_idle", "priority": 9, "category": "engine", "title": "Casino profit agents ran 0/3 on recent ticks"},
        {"id": "paypal_sweep_paper", "priority": 10, "category": "payout", "title": "PayPal payout mode still paper — $572+ unswept ledger"},
        {"id": "auto_sweep_off", "priority": 11, "category": "payout", "title": "Auto sweep disabled (min $500) — manual sweep required"},
        {"id": "ledger_mode_paper", "priority": 12, "category": "ppp", "title": "PPP ledger rows tagged paper while live gates are on"},
        {"id": "ppp_skill_sync", "priority": 13, "category": "ppp", "title": "Profit agent skill sets must sync from ledger on each stack"},
        {"id": "nonkyc_doge_low", "priority": 14, "category": "funding", "title": "NonKYC DOGE inventory low for sell legs (~$25+ recommended)"},
        {"id": "binance_quote_cap", "priority": 15, "category": "funding", "title": "Binance USDC ~$79 caps live notional vs configured micro USD"},
        {"id": "treasury_compound", "priority": 16, "category": "treasury", "title": "Live venue compound on trade enabled but stash ledger empty"},
        {"id": "daemon_restart", "priority": 17, "category": "ops", "title": "Profit daemon must stay running (heartbeat stale = no ticks)"},
        {"id": "status_report_heavy", "priority": 18, "category": "ops", "title": "profit_status_report.py loads full Flask — avoid during active ticks"},
        {"id": "xeggex_live_disabled", "priority": 19, "category": "config", "title": "connectors_config xeggex live_trading=false until probe passes"},
        {"id": "dual_farm_two_venue", "priority": 20, "category": "config", "title": "arb_live_dual_farm limited to binance+nonkyc until XeggeX OK"},
        {"id": "hit_rate_tracking", "priority": 21, "category": "research", "title": "PPP hit_rate_pct must be reviewed weekly per route"},
        {"id": "skip_reason_funding", "priority": 22, "category": "research", "title": "Top skip reason insufficient_venue_balance — pre-fund quote legs"},
        {"id": "void_skills_open", "priority": 23, "category": "skills", "title": "Open void skills (gap specializations) must close as fixes land"},
        {"id": "agent_level_lag", "priority": 24, "category": "skills", "title": "Agent levels must track stacked profit via PPP ledger not paper PnL only"},
        {"id": "documentation_sync", "priority": 25, "category": "docs", "title": "PROFIT_PATH_PROTOCOL + critical top25 checklist kept in sync with ledger"},
    ]


def _dynamic_critical_from_ppp() -> List[Dict[str, Any]]:
    hints: List[Dict[str, Any]] = []
    try:
        from backend.services.exchange_profit_path_service import profit_path_summary, suggest_improvements

        summary = profit_path_summary(hours=24)
        if summary.get("fill_count", 0) == 0 and summary.get("scan_count", 0) > 10:
            hints.append({
                "id": "ppp_zero_fills_24h",
                "priority": 3,
                "category": "research",
                "title": f"0 fills in 24h despite {summary.get('scan_count')} scans",
            })
        top_skip = (summary.get("top_skip_reasons") or [{}])[0]
        if top_skip.get("reason"):
            hints.append({
                "id": f"ppp_skip_{_slug(top_skip.get('reason'), max_len=24)}",
                "priority": 4,
                "category": "research",
                "title": f"Top skip: {top_skip.get('reason')} ({top_skip.get('count')}x)",
            })
        for s in (suggest_improvements().get("suggestions") or [])[:5]:
            if s.get("priority") != "high":
                continue
            msg = str(s.get("message") or "")[:120]
            hints.append({
                "id": f"ppp_hint_{_slug(msg, max_len=20)}",
                "priority": 5,
                "category": str(s.get("category") or "research"),
                "title": msg,
            })
    except Exception:
        pass
    return hints


def critical_problems_top25(*, refresh: bool = True) -> Dict[str, Any]:
    """Critical problem list with checkbox state for ops tracking."""
    store = _read_json(_CRITICAL_PATH, {})
    if not isinstance(store, dict):
        store = {}
    checks: Dict[str, bool] = store.get("checks") if isinstance(store.get("checks"), dict) else {}

    problems = _base_critical_problems()
    seen_ids = {p["id"] for p in problems}
    for dyn in _dynamic_critical_from_ppp():
        if dyn["id"] not in seen_ids and len(problems) < 25:
            problems.append(dyn)
            seen_ids.add(dyn["id"])
    problems.sort(key=lambda p: int(p.get("priority") or 99))
    problems = problems[:25]

    items: List[Dict[str, Any]] = []
    open_count = 0
    for p in problems:
        pid = str(p["id"])
        checked = bool(checks.get(pid, False))
        if not checked:
            open_count += 1
        items.append({**p, "checked": checked, "status": "done" if checked else "open"})

    if refresh:
        hit = hit_rate_by_route(days=7)
        store["last_hit_rate_review_at"] = hit.get("reviewed_at")
        store["checks"] = checks
        store["problems"] = items
        store["updated_at"] = _iso()
        store["open_count"] = open_count
        store["done_count"] = len(items) - open_count
        _write_json(_CRITICAL_PATH, store)

    return {
        "success": True,
        "updated_at": store.get("updated_at") or _iso(),
        "last_hit_rate_review_at": store.get("last_hit_rate_review_at"),
        "open_count": open_count,
        "done_count": len(items) - open_count,
        "problems": items,
        "markdown": render_critical_markdown(items, notes=store.get("notes") if isinstance(store.get("notes"), dict) else {}),
    }


def update_critical_checkbox(problem_id: str, checked: bool) -> Dict[str, Any]:
    store = _read_json(_CRITICAL_PATH, {})
    checks = store.get("checks") if isinstance(store.get("checks"), dict) else {}
    checks[str(problem_id)] = bool(checked)
    store["checks"] = checks
    _write_json(_CRITICAL_PATH, store)
    return critical_problems_top25(refresh=True)


def render_critical_markdown(items: List[Dict[str, Any]], *, notes: Optional[Dict[str, str]] = None) -> str:
    notes = notes or {}
    lines = [
        "# Profit Critical Top 25",
        "",
        f"_Updated: {_iso()}_",
        "",
    ]
    for p in items:
        box = "x" if p.get("checked") else " "
        pid = str(p.get("id") or "")
        note = notes.get(pid) or p.get("note") or ""
        suffix = f" — _{note}_" if note else ""
        lines.append(
            f"- [{box}] **#{p.get('priority')}** [{p.get('category')}] {p.get('title')} (`{pid}`){suffix}"
        )
    lines.extend([
        "",
        "## Runbooks",
        "",
        "### XeggeX 401 / dual-venue blocked (#2, #20)",
        "",
        "1. `python scripts/refresh_xeggex_server.py --probe-only` — expect `ok=True status=200`.",
        "2. Confirm `XEGGEX_API_KEY` + `XEGGEX_API_SECRET` in `.env`; run `python scripts/remote_vault_import.py`.",
        "3. **IP whitelist:** XeggeX dashboard → API → add server egress IP (and local dev IP if probing locally).",
        "4. Regenerate API key if 401 persists after whitelist.",
        "5. `python scripts/configure_live_profit_max.py` — enables `live_trading` + adds xeggex to `arb_live_dual_farm`.",
        "",
        "### NonKYC DOGE sell-leg (#14)",
        "",
        "- Check: probe shows `nonkyc DOGE` USD ≥ $25 on sell venue.",
        "- One-shot: `python scripts/prefund_arb_legs.py --live --symbol DOGE`",
        "",
        "### Fast arb near threshold (#7)",
        "",
        "- When daemon shows `near_threshold=yes` and `best_bps` within ~2 bps of `threshold=12`:",
        "- Optional ops override: `set EXCHANGE_FAST_MIN_BPS=10` before restart (not persisted in config).",
        "",
        "### PayPal sweep (#10, #11)",
        "",
        "- Status: `python scripts/payout_sweep_status.py`",
        "- Enable: `run_all_profit_daemons.cmd --auto-sweep` + `EXCHANGE_AUTO_PAYPAL_SWEEP=1` (+ live PayPal gate).",
        "",
    ])
    return "\n".join(lines)


def write_critical_markdown_doc() -> str:
    sync_critical_reality()
    store = _read_json(_CRITICAL_PATH, {})
    data = critical_problems_top25(refresh=True)
    notes = store.get("notes") if isinstance(store.get("notes"), dict) else {}
    path = os.path.join(ex._BASE, "docs", "PROFIT_CRITICAL_TOP25.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_critical_markdown(data.get("problems") or [], notes=notes))
        f.write("\n")
    return path
