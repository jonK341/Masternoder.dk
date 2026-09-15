"""
Agent-driven MN2 settlement across game, battle, quests, generator, aggregator, casino,
staking, exchange, and the masternoder2d daemon. Runs on cron; records agent activity.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_AGENT_MAP = {
    "daemon": "monitoring_agent",
    "battle": "battle_strategy_agent",
    "chain": "monitoring_agent",
    "scan": "monitoring_agent",
    "aggregator": "analytics_agent",
    "generator": "content_generator_agent",
    "casino": "workflow_agent",
    "staking": "workflow_agent",
    "reconcile": "security_agent",
    "activity": "ai_intelligence_agent",
    "masternodes": "monitoring_agent",
    "shop": "workflow_agent",
    "micro": "monitoring_agent",
}

_CRON_ACTIONS = (
    "monitor_move",
    "progress_refresh",
    "intel_loaded",
    "monitor_battle_complete",
    "interaction",
)


def _log_dir() -> str:
    d = os.path.join(BASE_DIR, "logs", "mn2_settlement")
    os.makedirs(d, exist_ok=True)
    return d


def _append_log(name: str, payload: Dict[str, Any]) -> str:
    path = os.path.join(_log_dir(), name)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def _record_agent_activity(
    system: str,
    action: str,
    *,
    user_id: str = "platform_mn2",
    xp: int = 3,
    points: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    agent_id = _AGENT_MAP.get(system, "monitoring_agent")
    try:
        from backend.services.agent_db_service import agent_db_service
        agent_db_service.record_agent_activity(
            user_id=user_id,
            agent_id=agent_id,
            action=action,
            skill="mn2_settlement",
            xp_gained=xp,
            points_gained=points,
            metadata={"system": system, "cron": True, **(metadata or {})},
        )
    except Exception:
        pass
    try:
        from backend.services.activity_events_service import emit
        emit(
            "agent_mn2_settlement",
            user_id=user_id,
            channel="agents",
            text=f"{agent_id}: {action}",
            payload={"system": system, "action": action, **(metadata or {})},
        )
    except Exception:
        pass


def _discover_active_user_ids(limit: int = 40) -> List[str]:
    """Collect user_ids from battle, aggregator, ledger, and agent wallets."""
    seen: set = set()
    out: List[str] = []

    def add(uid: Any) -> None:
        u = str(uid or "").strip()
        if not u or u.startswith("pool_") or u in ("agent_treasury", "platform_treasury"):
            return
        if u in seen:
            return
        seen.add(u)
        out.append(u)

    try:
        from backend.routes.battle_routes import _load_battle_v2_state
        data = _load_battle_v2_state()
        for uid in (data.get("users") or {}).keys():
            add(uid)
    except Exception:
        pass

    try:
        from backend.services.aggregator_mn2_service import _load_awards
        users = (_load_awards().get("users") or {})
        for uid in users.keys():
            add(uid)
    except Exception:
        pass

    try:
        from backend.services.mn2_ledger import _load_entries
        for e in reversed(_load_entries()):
            add(e.get("user_id"))
            if len(out) >= limit:
                break
    except Exception:
        pass

    if not out:
        add("default_user")
    return out[:limit]


def _test_daemon(*, extended: bool = True) -> Dict[str, Any]:
    from backend.services.mn2_daemon_health_service import probe_daemon
    result = probe_daemon(extended=extended)
    if result.get("healthy"):
        _record_agent_activity("daemon", "daemon_health_ok", metadata=result.get("health"))
    else:
        _record_agent_activity("daemon", "daemon_health_fail", metadata={"error": result.get("error")})
    return result


def _settle_aggregator_rewards(*, max_users: int = 20) -> Dict[str, Any]:
    out: Dict[str, Any] = {"awards": 0, "users": 0, "errors": []}
    try:
        from backend.services.aggregator_mn2_service import award_for_action
        users = _discover_active_user_ids(limit=max_users)
        for uid in users:
            for action in _CRON_ACTIONS[:2]:
                res = award_for_action(uid, action, meta={"cron": True, "agent": "analytics_agent"})
                if res.get("mn2_awarded", 0) > 0:
                    out["awards"] += 1
                    _record_agent_activity(
                        "aggregator",
                        f"aggregator_{action}",
                        user_id=uid,
                        points=float(res.get("mn2_awarded") or 0),
                        metadata=res,
                    )
            out["users"] += 1
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def _settle_generator_rewards(*, max_users: int = 10) -> Dict[str, Any]:
    out: Dict[str, Any] = {"credits": 0, "errors": []}
    try:
        from backend.services.game_mn2_rewards import credit_mn2
        from backend.services.generator_mn2_service import get_generator_config
        cfg = get_generator_config()
        if not cfg.get("enabled", True):
            out["skipped"] = "disabled"
            return out
        earn = float(cfg.get("earn_on_finish_mn2") or 0.005)
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        for uid in _discover_active_user_ids(limit=max_users):
            ref = f"gen-cron:{uid}:{day}"
            cr = credit_mn2(
                uid,
                earn,
                source="generator_mn2",
                reference=ref,
                metadata={"cron": True, "agent": "content_generator_agent"},
            )
            if cr.get("success") and not cr.get("duplicate"):
                out["credits"] += 1
                _record_agent_activity(
                    "generator",
                    "generator_finish_bonus",
                    user_id=uid,
                    points=earn,
                    metadata=cr,
                )
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def _settle_casino_agents(*, dry_run: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ran": 0, "errors": []}
    try:
        from backend.services.casino_agents_service import run_all
        res = run_all(dry_run=dry_run)
        out.update(res)
        if res.get("ran"):
            _record_agent_activity(
                "casino",
                "casino_agents_run_all",
                metadata={"ran": res.get("ran"), "dry_run": dry_run},
                xp=5,
            )
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def _settle_staking_agents(*, dry_run: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {"ran": 0, "errors": []}
    try:
        from backend.services.mn2_staking_agents_service import run_all
        res = run_all(dry_run=dry_run)
        out.update(res)
        if res.get("ran"):
            _record_agent_activity(
                "staking",
                "staking_agents_run_all",
                metadata={"ran": res.get("ran"), "dry_run": dry_run},
                xp=4,
            )
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def _settle_reconcile() -> Dict[str, Any]:
    out: Dict[str, Any] = {"ok": False, "errors": []}
    try:
        from backend.services.mn2_staking_reconcile_service import reconcile
        res = reconcile()
        out["ok"] = bool(res.get("ok", False))
        out["result"] = res
        _record_agent_activity("reconcile", "mn2_staking_reconcile", metadata=res)
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def _burst_agent_activity(*, max_events: int = 12) -> Dict[str, Any]:
    out: Dict[str, Any] = {"events": 0}
    systems = list(_AGENT_MAP.keys())
    users = _discover_active_user_ids(limit=8)
    for i, system in enumerate(systems):
        if out["events"] >= max_events:
            break
        uid = users[i % len(users)] if users else "platform_mn2"
        _record_agent_activity(
            system,
            f"mn2_tx_tick_{system}",
            user_id=uid,
            xp=2,
            metadata={"tick": i, "burst": True},
        )
        out["events"] += 1
    return out


def _settle_battle_crypto(*, dry_run: bool = False, max_claims: int = 50) -> Dict[str, Any]:
    out: Dict[str, Any] = {"claims": 0, "users": 0, "errors": []}
    try:
        from backend.routes.battle_routes import (
            _load_battle_v2_state,
            _battle_crypto_options,
            _battle_crypto_progress,
            _crypto_requirement_met,
            _seconds_until,
            _battle_crypto_reward_amount,
            _utc_now,
            _battle_v2_user_state,
            _save_battle_v2_state,
        )
        from backend.services.game_mn2_rewards import credit_mn2
        from datetime import timedelta

        data = _load_battle_v2_state()
        options = _battle_crypto_options()
        for user_id, user_state in (data.get("users") or {}).items():
            if not user_id or user_id.startswith("pool_"):
                continue
            crypto = (user_state or {}).get("crypto") or {}
            claimed_for_user = 0
            for option in options:
                if out["claims"] >= max_claims:
                    break
                option_id = option.get("id")
                if not option_id:
                    continue
                progress = _battle_crypto_progress(user_id)
                if not _crypto_requirement_met(option, progress):
                    continue
                option_state = (crypto.get("options") or {}).get(option_id) or {}
                if _seconds_until(option_state.get("next_claim_at")) > 0:
                    continue
                if dry_run:
                    out["claims"] += 1
                    claimed_for_user += 1
                    continue
                amount = _battle_crypto_reward_amount(option, progress)
                ref = f"battle-auto:{user_id}:{option_id}:{_utc_now().strftime('%Y%m%d%H')}"
                cr = credit_mn2(
                    user_id,
                    amount,
                    source="battle_crypto_claim",
                    reference=ref,
                    metadata={"option_id": option_id, "option_name": option.get("name"), "cron": True},
                )
                if not cr.get("success") and not cr.get("duplicate"):
                    out["errors"].append(f"{user_id}:{option_id}:{cr.get('error')}")
                    continue
                now = _utc_now()
                next_claim_at = (now + timedelta(seconds=int(option.get("cooldown_sec", 0) or 0))).isoformat()
                us = _battle_v2_user_state(data, user_id)
                c = us.setdefault("crypto", {"total_mn2_earned": 0, "claims": [], "options": {}})
                os_ = c.setdefault("options", {}).setdefault(option_id, {})
                os_["last_claim_at"] = now.isoformat()
                os_["next_claim_at"] = next_claim_at
                os_["claims_count"] = int(os_.get("claims_count", 0) or 0) + 1
                c["total_mn2_earned"] = round(float(c.get("total_mn2_earned", 0) or 0) + amount, 8)
                c.setdefault("claims", []).append(
                    {"option_id": option_id, "amount_mn2": amount, "claimed_at": now.isoformat(), "cron": True}
                )
                out["claims"] += 1
                claimed_for_user += 1
                _record_agent_activity(
                    "battle",
                    "battle_crypto_auto_claim",
                    user_id=user_id,
                    points=amount,
                    metadata={"option_id": option_id, "cron": True},
                )
            if claimed_for_user:
                out["users"] += 1
        if not dry_run and out["claims"]:
            _save_battle_v2_state(data)
        if out["claims"]:
            _record_agent_activity("battle", "battle_settlement_batch", metadata=out)
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def _settle_shop_agents(*, dry_run: bool = False, max_purchases: int = 6) -> Dict[str, Any]:
    out: Dict[str, Any] = {"purchases": 0, "errors": []}
    try:
        from backend.services.agent_shop_tick_service import run_agent_shop_tick
        res = run_agent_shop_tick(max_purchases=max_purchases, dry_run=dry_run)
        out.update(res)
        if res.get("purchases"):
            _record_agent_activity(
                "shop",
                "agent_shop_tick",
                metadata={"purchases": res.get("purchases"), "dry_run": dry_run},
                xp=4,
            )
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def _settle_micro_transactions(*, dry_run: bool = False, max_txs: int = 80) -> Dict[str, Any]:
    out: Dict[str, Any] = {"attempted": 0, "on_chain": 0, "errors": []}
    try:
        from backend.services.mn2_micro_transactions_service import run_micro_transaction_burst
        res = run_micro_transaction_burst(max_txs=max_txs, dry_run=dry_run)
        out.update(res)
        if res.get("on_chain") or res.get("in_app_only"):
            _record_agent_activity(
                "chain",
                "micro_transaction_burst",
                metadata={
                    "attempted": res.get("attempted"),
                    "on_chain": res.get("on_chain"),
                    "dry_run": dry_run,
                },
                xp=6,
            )
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def _scan_chain_payout_queue(*, max_payouts: int = 25) -> Dict[str, Any]:
    out: Dict[str, Any] = {"payouts": 0, "skipped": 0, "errors": []}
    try:
        from backend.services.mn2_chain_rewards_service import chain_payouts_enabled, payout_reward_on_chain

        if not chain_payouts_enabled():
            out["skipped"] = -1
            return out

        from backend.services.mn2_ledger import _load_entries

        reward_types = {
            "battle_crypto_claim",
            "game_mn2_reward",
            "generator_mn2",
            "aggregator_mn2",
            "staking_reward",
            "quest_reward",
            "casino_reward",
        }
        seen_refs = set()
        for e in reversed(_load_entries()):
            if out["payouts"] >= max_payouts:
                break
            t = (e.get("type") or "").strip()
            if t not in reward_types and not t.endswith("_reward"):
                continue
            meta = e.get("metadata") or {}
            if meta.get("chain_paid"):
                continue
            ref = (meta.get("reference") or e.get("txid") or "").strip()
            if not ref or ref in seen_refs:
                continue
            seen_refs.add(ref)
            uid = (e.get("user_id") or "").strip()
            if not uid:
                continue
            try:
                amt = float(e.get("amount") or 0)
            except (TypeError, ValueError):
                continue
            if amt <= 0:
                continue
            res = payout_reward_on_chain(uid, amt, source=t, reference=ref, metadata=meta)
            if res.get("skipped"):
                out["skipped"] += 1
            elif res.get("success"):
                out["payouts"] += 1
                meta["chain_paid"] = True
                meta["chain_txid"] = res.get("txid")
            else:
                out["errors"].append(f"{uid}:{res.get('error')}")
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def run_mn2_ecosystem_settlement(
    *,
    systems: Optional[List[str]] = None,
    dry_run: bool = False,
    max_battle_claims: int = 50,
    max_chain_payouts: int = 60,
) -> Dict[str, Any]:
    """Run settlement across named systems. Intended for agent cron and ops endpoints."""
    active = [s.strip().lower() for s in (systems or ["all"])]
    if "all" in active:
        active = [
            "daemon", "battle", "aggregator", "generator", "casino", "staking",
            "shop", "micro", "chain", "scan", "reconcile", "activity", "masternodes",
        ]

    result: Dict[str, Any] = {
        "success": True,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "systems": active,
        "results": {},
        "errors": {},
    }

    if "daemon" in active:
        try:
            result["results"]["daemon"] = _test_daemon()
            if not result["results"]["daemon"].get("healthy"):
                result["warnings"] = result.get("warnings", {})
                result["warnings"]["daemon"] = result["results"]["daemon"].get("error") or "unhealthy"
        except Exception as e:
            result["errors"]["daemon"] = str(e)[:300]

    if "battle" in active:
        try:
            result["results"]["battle"] = _settle_battle_crypto(dry_run=dry_run, max_claims=max_battle_claims)
        except Exception as e:
            result["errors"]["battle"] = str(e)[:300]
            result["success"] = False

    if "aggregator" in active:
        try:
            result["results"]["aggregator"] = _settle_aggregator_rewards()
        except Exception as e:
            result["errors"]["aggregator"] = str(e)[:300]

    if "generator" in active:
        try:
            result["results"]["generator"] = _settle_generator_rewards()
        except Exception as e:
            result["errors"]["generator"] = str(e)[:300]

    if "casino" in active and not dry_run:
        try:
            result["results"]["casino"] = _settle_casino_agents(dry_run=False)
        except Exception as e:
            result["errors"]["casino"] = str(e)[:300]

    if "staking" in active and not dry_run:
        try:
            result["results"]["staking"] = _settle_staking_agents(dry_run=False)
        except Exception as e:
            result["errors"]["staking"] = str(e)[:300]

    if "reconcile" in active:
        try:
            result["results"]["reconcile"] = _settle_reconcile()
        except Exception as e:
            result["errors"]["reconcile"] = str(e)[:300]

    if "activity" in active:
        try:
            result["results"]["activity"] = _burst_agent_activity()
        except Exception as e:
            result["errors"]["activity"] = str(e)[:300]

    if "shop" in active and not dry_run:
        try:
            result["results"]["shop"] = _settle_shop_agents(dry_run=False)
        except Exception as e:
            result["errors"]["shop"] = str(e)[:300]

    if "micro" in active:
        try:
            result["results"]["micro"] = _settle_micro_transactions(dry_run=dry_run, max_txs=80)
        except Exception as e:
            result["errors"]["micro"] = str(e)[:300]

    if "chain" in active:
        try:
            result["results"]["chain"] = _scan_chain_payout_queue(max_payouts=max_chain_payouts)
        except Exception as e:
            result["errors"]["chain"] = str(e)[:300]
            result["success"] = False

    if "scan" in active:
        try:
            from backend.services.mn2_deposit_scanner import run_scanner
            result["results"]["deposit_scan"] = run_scanner()
        except Exception as e:
            result["errors"]["scan"] = str(e)[:300]
            result["success"] = False

    if "masternodes" in active:
        try:
            from backend.services.mn2_masternode_service import (
                bring_rented_masternodes_online,
                rented_masternodes_snapshot,
            )
            if dry_run:
                result["results"]["masternodes"] = rented_masternodes_snapshot()
            else:
                result["results"]["masternodes"] = bring_rented_masternodes_online()
        except Exception as e:
            result["errors"]["masternodes"] = str(e)[:300]

    if result["errors"]:
        result["success"] = False

    _append_log("settlement_runs.jsonl", result)
    return result
