"""
Agent-driven MN2 settlement across game, battle, quests, generator, aggregator, and casino.
Runs on cron to reconcile pending rewards, auto-claim eligible battle crypto, and optionally
push chain payouts for accumulated ledger events.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _log_dir() -> str:
    d = os.path.join(BASE_DIR, "logs", "mn2_settlement")
    os.makedirs(d, exist_ok=True)
    return d


def _append_log(name: str, payload: Dict[str, Any]) -> str:
    path = os.path.join(_log_dir(), name)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def _settle_battle_crypto(*, dry_run: bool = False, max_claims: int = 50) -> Dict[str, Any]:
    """Auto-claim eligible battle crypto options for users with pending cooldowns cleared."""
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
            if claimed_for_user:
                out["users"] += 1
        if not dry_run and out["claims"]:
            _save_battle_v2_state(data)
    except Exception as e:
        out["errors"].append(str(e)[:300])
    return out


def _scan_chain_payout_queue(*, max_payouts: int = 25) -> Dict[str, Any]:
    """Push pending in-app rewards to on-chain wallets when chain payouts are enabled."""
    out: Dict[str, Any] = {"payouts": 0, "skipped": 0, "errors": []}
    try:
        from backend.services.mn2_chain_rewards_service import chain_payouts_enabled, payout_reward_on_chain
        from backend.services.mn2_ledger import get_entries_by_user

        if not chain_payouts_enabled():
            out["skipped"] = -1
            return out

        # Collect recent reward entries not yet chain-paid (metadata.chain_paid != true)
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
    max_chain_payouts: int = 25,
) -> Dict[str, Any]:
    """
    Run settlement across named systems: battle, game, chain, all.
    Intended for agent cron and ops endpoints.
    """
    active = [s.strip().lower() for s in (systems or ["all"])]
    if "all" in active:
        active = ["battle", "chain", "scan", "masternodes"]

    result: Dict[str, Any] = {
        "success": True,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "systems": active,
        "results": {},
        "errors": {},
    }

    if "battle" in active:
        try:
            result["results"]["battle"] = _settle_battle_crypto(dry_run=dry_run, max_claims=max_battle_claims)
        except Exception as e:
            result["errors"]["battle"] = str(e)[:300]
            result["success"] = False

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
