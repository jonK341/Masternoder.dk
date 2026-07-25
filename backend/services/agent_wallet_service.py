"""Per-agent MN2 wallet balances for trader agents (internal ledger).

Option C / Phase 4: treasury address + funding config + dry-run status.
Live batch distribution is gated by ``agent_funding.live_distribute`` (default false)
and cold-wallet sign-off (MN2_OPS §8.6) for batches ≥100k MN2.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_WALLETS_FILE = os.path.join(_BASE, "data", "agent_wallets.json")
_TREASURY_FILE = os.path.join(_BASE, "data", "agent_treasury.json")
_MN2_CONFIG = os.path.join(_BASE, "data", "mn2_config.json")

TREASURY_POOL_USER = "agent_treasury"
_DEFAULT_PER_AGENT = 100_000.0
_DEFAULT_TRADER_COUNT = 6


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def list_wallets() -> List[Dict[str, Any]]:
    with _LOCK:
        store = _read(_WALLETS_FILE)
    agents = store.get("agents") if isinstance(store.get("agents"), dict) else store
    out = []
    for agent_id, row in (agents or {}).items():
        if isinstance(row, dict):
            out.append({"agent_id": agent_id, **row})
        else:
            out.append({"agent_id": agent_id, "mn2_balance": float(row or 0)})
    return out


def get_balance(agent_id: str) -> float:
    with _LOCK:
        store = _read(_WALLETS_FILE)
    agents = store.get("agents") if isinstance(store.get("agents"), dict) else store
    row = (agents or {}).get(agent_id)
    if isinstance(row, dict):
        return float(row.get("mn2_balance") or 0)
    return float(row or 0)


def credit(agent_id: str, amount: float, *, reference: str, source: str = "treasury") -> Dict[str, Any]:
    amt = float(amount or 0)
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}
    with _LOCK:
        store = _read(_WALLETS_FILE)
        if "agents" not in store or not isinstance(store["agents"], dict):
            store["agents"] = store if store and "agents" not in store else {}
            if "agents" not in store:
                store = {"agents": {}}
        agents = store["agents"]
        row = agents.setdefault(agent_id, {"mn2_balance": 0.0, "history": []})
        if not isinstance(row, dict):
            row = {"mn2_balance": float(row or 0), "history": []}
            agents[agent_id] = row
        row["mn2_balance"] = float(row.get("mn2_balance") or 0) + amt
        row.setdefault("history", []).append({
            "ts": _iso(), "amount": amt, "reference": reference, "source": source,
        })
        store["updated_at"] = _iso()
        _write(_WALLETS_FILE, store)
    return {"success": True, "agent_id": agent_id, "credited": amt, "balance": get_balance(agent_id)}


def get_treasury() -> Dict[str, Any]:
    with _LOCK:
        return _read(_TREASURY_FILE)


def load_agent_funding_config() -> Dict[str, Any]:
    """Merge mn2_config.agent_funding with agent_treasury.json (treasury file wins on overlap)."""
    cfg: Dict[str, Any] = {
        "per_agent_mn2": _DEFAULT_PER_AGENT,
        "trader_agent_count": _DEFAULT_TRADER_COUNT,
        "top_up": True,
        "live_distribute": False,
    }
    try:
        raw = _read(_MN2_CONFIG)
        block = raw.get("agent_funding") if isinstance(raw.get("agent_funding"), dict) else {}
        for k in ("per_agent_mn2", "trader_agent_count", "top_up", "live_distribute"):
            if k in block:
                cfg[k] = block[k]
    except Exception:
        pass
    treasury = get_treasury()
    for k in ("per_agent_mn2", "trader_agent_count", "top_up", "live_distribute", "address"):
        if k in treasury and treasury[k] is not None:
            cfg[k] = treasury[k]
    cfg["per_agent_mn2"] = float(cfg.get("per_agent_mn2") or _DEFAULT_PER_AGENT)
    cfg["trader_agent_count"] = int(cfg.get("trader_agent_count") or _DEFAULT_TRADER_COUNT)
    cfg["top_up"] = bool(cfg.get("top_up", True))
    cfg["live_distribute"] = bool(cfg.get("live_distribute", False))
    cfg["required_total_mn2"] = cfg["per_agent_mn2"] * cfg["trader_agent_count"]
    return cfg


def set_treasury_address(
    address: str,
    *,
    per_agent_mn2: Optional[float] = None,
    trader_count: Optional[int] = None,
    live_distribute: Optional[bool] = None,
) -> Dict[str, Any]:
    funding = load_agent_funding_config()
    per = float(per_agent_mn2 if per_agent_mn2 is not None else funding["per_agent_mn2"])
    count = int(trader_count if trader_count is not None else funding["trader_agent_count"])
    live = bool(live_distribute if live_distribute is not None else funding["live_distribute"])
    with _LOCK:
        prev = _read(_TREASURY_FILE)
        data = {
            **prev,
            "address": (address or "").strip(),
            "per_agent_mn2": per,
            "trader_agent_count": count,
            "top_up": bool(funding.get("top_up", True)),
            "live_distribute": live,
            "required_total_mn2": per * count,
            "updated_at": _iso(),
        }
        _write(_TREASURY_FILE, data)
    # Map into deposit scanner address book (reserved agent_treasury account).
    # Skip ephemeral/test addresses (Option C unit fixtures use short labels).
    if len(data.get("address") or "") >= 26:
        try:
            from backend.services import mn2_wallet_service as mws
            addrs = mws._load_addresses()
            entry = addrs.get(TREASURY_POOL_USER) if isinstance(addrs.get(TREASURY_POOL_USER), dict) else {}
            entry = dict(entry or {})
            entry["address"] = data["address"]
            entry["label"] = "agent-treasury"
            entry["updated_at"] = _iso()
            addrs[TREASURY_POOL_USER] = entry
            mws._save_addresses(addrs)
        except Exception:
            pass
    return {"success": True, **data}


def get_treasury_pool_balance() -> float:
    """In-app MN2 balance of the treasury pool account (scanner-credited)."""
    try:
        from backend.services.unified_points_database import unified_points_db
        result = unified_points_db.get_all_points(TREASURY_POOL_USER)
        points = (result or {}).get("points") or {}
        bal = float(points.get("mn2_balance") or 0)
        if bal == 0 and isinstance(points.get("systems"), dict):
            bal = float(points["systems"].get("mn2_balance") or 0)
        return bal
    except Exception:
        return 0.0


def trader_agent_ids(count: Optional[int] = None) -> List[str]:
    n = int(count if count is not None else load_agent_funding_config()["trader_agent_count"])
    return [f"trader_agent_{i + 1}" for i in range(max(0, n))]


def _funding_plan() -> Dict[str, Any]:
    """Compute per-agent gaps vs target (dry-run friendly)."""
    cfg = load_agent_funding_config()
    per = float(cfg["per_agent_mn2"])
    top_up = bool(cfg.get("top_up", True))
    pool = get_treasury_pool_balance()
    agents = []
    need_total = 0.0
    for aid in trader_agent_ids(int(cfg["trader_agent_count"])):
        bal = get_balance(aid)
        if top_up:
            gap = max(0.0, per - bal)
        else:
            gap = 0.0 if bal >= per else per
        need_total += gap
        agents.append({
            "agent_id": aid,
            "balance": bal,
            "target": per,
            "gap_mn2": gap,
            "would_credit": gap,
        })
    return {
        "config": cfg,
        "pool_balance_mn2": pool,
        "need_total_mn2": need_total,
        "pool_covers_need": pool + 1e-12 >= need_total,
        "agents": agents,
        "address": cfg.get("address") or get_treasury().get("address"),
    }


def treasury_status() -> Dict[str, Any]:
    """Dry-run status for ops: address, required total, pool, gaps, gates."""
    plan = _funding_plan()
    cfg = plan["config"]
    signoff = {"signed": False}
    try:
        from backend.services.treasury_signoff_service import get_signoff, assert_distribution_allowed
        signoff = get_signoff()
        block = assert_distribution_allowed(estimated_total_mn2=float(plan["need_total_mn2"]))
    except Exception as exc:
        block = f"signoff_check_error:{exc}"
    live = bool(cfg.get("live_distribute"))
    return {
        "success": True,
        "dry_run": True,
        "live_distribute": live,
        "distribution_armed": live and not block and plan["pool_covers_need"],
        "blocked_reason": None if (live and not block and plan["pool_covers_need"]) else (
            block
            or ("live_distribute_false" if not live else None)
            or ("insufficient_pool" if not plan["pool_covers_need"] else None)
        ),
        "address": plan.get("address"),
        "per_agent_mn2": cfg["per_agent_mn2"],
        "trader_agent_count": cfg["trader_agent_count"],
        "required_total_mn2": cfg["required_total_mn2"],
        "pool_balance_mn2": plan["pool_balance_mn2"],
        "need_total_mn2": plan["need_total_mn2"],
        "pool_covers_need": plan["pool_covers_need"],
        "agents": plan["agents"],
        "signoff": signoff,
        "policy": "MN2_OPS §8.6 — keep live_distribute false until cold-wallet sign-off",
    }


def distribute_agent_funding(*, dry_run: Optional[bool] = None, allow_live: bool = False) -> Dict[str, Any]:
    """Top each trader agent up to per_agent_mn2, debiting the treasury pool.

    Default is dry-run unless ``agent_funding.live_distribute`` is true (or allow_live).
    Never credits more than the pool; idempotent gap-only top-ups.
    """
    plan = _funding_plan()
    cfg = plan["config"]
    live_cfg = bool(cfg.get("live_distribute"))
    do_dry = True if dry_run is True else (False if (dry_run is False and (live_cfg or allow_live)) else (not live_cfg and not allow_live))

    if do_dry:
        status = treasury_status()
        status["success"] = True
        status["dry_run"] = True
        status["results"] = [
            {
                "agent_id": a["agent_id"],
                "would_credit": a["gap_mn2"],
                "skipped": a["gap_mn2"] <= 0,
                "reason": "already_funded" if a["gap_mn2"] <= 0 else "dry_run",
            }
            for a in plan["agents"]
        ]
        return status

    need = float(plan["need_total_mn2"])
    try:
        from backend.services.treasury_signoff_service import assert_distribution_allowed
        blocked = assert_distribution_allowed(estimated_total_mn2=need)
    except Exception as exc:
        blocked = str(exc)
    if blocked:
        return {"success": False, "error": blocked, "dry_run": False, "plan": plan}

    if not plan["pool_covers_need"]:
        return {
            "success": False,
            "error": "insufficient_treasury_pool",
            "pool_balance_mn2": plan["pool_balance_mn2"],
            "need_total_mn2": need,
        }

    from backend.services.unified_points_database import unified_points_db

    results = []
    debited = 0.0
    for a in plan["agents"]:
        gap = float(a["gap_mn2"])
        aid = a["agent_id"]
        if gap <= 0:
            results.append({"agent_id": aid, "skipped": True, "reason": "already_funded", "balance": a["balance"]})
            continue
        ref = f"treasury-fund:{aid}"
        # Debit pool first (Gate S idempotent reference).
        pool_ref = f"treasury-debit:{aid}:{ref}"
        debit = unified_points_db.add_points(
            TREASURY_POOL_USER,
            "mn2_balance",
            -gap,
            source="agent_treasury_distribute",
            metadata={"reference": pool_ref, "agent_id": aid},
        )
        if debit.get("duplicate"):
            results.append({"agent_id": aid, "skipped": True, "reason": "debit_duplicate", "balance": get_balance(aid)})
            continue
        if not debit.get("success"):
            results.append({"agent_id": aid, "success": False, "error": debit.get("error") or "pool_debit_failed"})
            break
        credited = credit(aid, gap, reference=ref, source="agent_treasury")
        try:
            from backend.services.mn2_ledger import append_entry
            append_entry(
                user_id=aid,
                entry_type="agent_treasury_funding",
                amount=gap,
                metadata={"reference": ref, "from": TREASURY_POOL_USER},
            )
        except Exception:
            pass
        try:
            from backend.services.activity_events_service import emit
            emit(
                "agent_treasury_funding",
                channel="agents",
                payload={"agent_id": aid, "amount": gap, "reference": ref},
            )
        except Exception:
            pass
        debited += gap
        results.append({**credited, "debited_from_pool": gap})

    try:
        from backend.services.admin_audit_service import log_action
        log_action(
            "agent_treasury_distribute",
            actor="distribute_agent_funding",
            payload={"debited": debited, "agents": len(results), "live": True},
        )
    except Exception:
        pass

    return {
        "success": True,
        "dry_run": False,
        "results": results,
        "debited_total_mn2": debited,
        "pool_balance_mn2": get_treasury_pool_balance(),
        "per_agent_mn2": cfg["per_agent_mn2"],
    }
