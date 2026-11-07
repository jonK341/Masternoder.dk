"""Credit leased / hosted masternode rewards to renters when on-chain ``lastpaid`` advances."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

_LOCK = threading.Lock()
_STATE_FILE = "mn2_masternode_renter_rewards_state.json"


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _state_path() -> str:
    return os.path.join(_base(), "data", _STATE_FILE)


def _read_state() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.isfile(path):
        return {"hosts": {}}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {"hosts": {}}
    except Exception:
        return {"hosts": {}}


def _write_state(data: Dict[str, Any]) -> None:
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def _rewards_cfg() -> Dict[str, Any]:
    from backend.services.mn2_masternode_service import get_config

    cfg = get_config()
    block = cfg.get("renter_rewards") if isinstance(cfg.get("renter_rewards"), dict) else {}
    fee = float(cfg.get("hosting_fee_percent") or 0)
    platform_fee = float(block.get("platform_fee_percent") if block.get("platform_fee_percent") is not None else fee)
    return {
        "enabled": bool(block.get("enabled", True)),
        "reward_mn2_per_payout": float(block.get("reward_mn2_per_payout") or 0),
        "use_block_subsidy": bool(block.get("use_block_subsidy", True)),
        "masternode_share_of_block": float(block.get("masternode_share_of_block") or 0.5),
        "platform_fee_percent": max(0.0, min(100.0, platform_fee)),
        "fallback_reward_mn2": float(block.get("fallback_reward_mn2") or 8.0),
    }


def _parse_lastpaid(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _reward_for_block_height(height: int, rcfg: Dict[str, Any]) -> float:
    fixed = float(rcfg.get("reward_mn2_per_payout") or 0)
    if fixed > 0:
        return fixed
    if rcfg.get("use_block_subsidy") and height > 0:
        try:
            from backend.services.mn2_rpc_client import _call

            r = _call("getblocksubsidy", [int(height)])
            if isinstance(r, dict) and not r.get("error"):
                res = r.get("result")
                if isinstance(res, (int, float)):
                    base = float(res)
                elif isinstance(res, dict):
                    base = float(res.get("masternode") or res.get("pos") or res.get("proof-of-stake") or 0)
                else:
                    base = 0.0
                if base > 0:
                    return base * float(rcfg.get("masternode_share_of_block") or 0.5)
        except Exception:
            pass
    return float(rcfg.get("fallback_reward_mn2") or 8.0)


def _net_payout(gross: float, rcfg: Dict[str, Any]) -> float:
    fee_pct = float(rcfg.get("platform_fee_percent") or 0)
    return round(max(0.0, gross * (1.0 - fee_pct / 100.0)), 8)


def seed_renter_reward_baseline(host_id: str) -> Dict[str, Any]:
    """Record current on-chain ``lastpaid`` when a host is leased so past payouts are not credited."""
    hid = str(host_id or "").strip()
    if not hid:
        return {"success": False, "error": "host_id required"}
    from backend.services import mn2_masternode_service as mn

    doc = mn._load_hosts_doc()
    host = next((h for h in (doc.get("hosts") or []) if isinstance(h, dict) and h.get("id") == hid), None)
    if not host:
        return {"success": False, "error": "host_not_found"}
    owner = str(host.get("owner_user_id") or "").strip()
    if not owner:
        return {"success": False, "error": "no_owner"}

    chain = mn.network_masternodes(limit=2000, fresh=True)
    chain_rows = chain.get("list") if isinstance(chain.get("list"), list) else []
    on_chain = mn._match_on_chain(host, chain_rows)
    lastpaid = _parse_lastpaid((on_chain or {}).get("lastpaid"))
    if lastpaid is None:
        return {"success": False, "error": "no_on_chain_match", "host_id": hid}

    with _LOCK:
        state = _read_state()
        host_state: Dict[str, Any] = dict(state.get("hosts") or {})
        row = host_state.get(hid) if isinstance(host_state.get(hid), dict) else {}
        if _parse_lastpaid(row.get("lastpaid")) is not None:
            return {
                "success": True,
                "host_id": hid,
                "already_seeded": True,
                "lastpaid": row.get("lastpaid"),
            }
        host_state[hid] = {
            **row,
            "lastpaid": lastpaid,
            "total_credited_mn2": float(row.get("total_credited_mn2") or 0),
            "seeded_at_lease": True,
        }
        state["hosts"] = host_state
        _write_state(state)

    hosts = list(doc.get("hosts") or [])
    idx = next((i for i, h in enumerate(hosts) if h.get("id") == hid), None)
    if idx is not None:
        hosts[idx] = {**hosts[idx], "rewards_lastpaid": lastpaid, "owner_user_id": owner}
        mn._save_hosts_doc(hosts)

    return {"success": True, "host_id": hid, "lastpaid": lastpaid, "owner_user_id": owner}


def accrue_renter_rewards(*, limit: int = 500, dry_run: bool = False) -> Dict[str, Any]:
    """
    For each active host with ``owner_user_id``, match on-chain masternode row and
    when ``lastpaid`` block height increases, credit the renter's in-app MN2 balance.
    """
    rcfg = _rewards_cfg()
    if not rcfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "renter_rewards_disabled"}

    from backend.services import mn2_masternode_service as mn

    chain = mn.network_masternodes(limit=2000, fresh=True)
    chain_rows = chain.get("list") if isinstance(chain.get("list"), list) else []

    with _LOCK:
        state = _read_state()
        host_state: Dict[str, Any] = dict(state.get("hosts") or {})
        credits: List[Dict[str, Any]] = []
        scanned = 0
        skipped_no_owner = 0
        skipped_no_match = 0

        doc = mn._load_hosts_doc()
        hosts: List[Dict[str, Any]] = list(doc.get("hosts") or [])
        host_by_id = {str(h.get("id") or ""): h for h in hosts if isinstance(h, dict) and h.get("id")}

        for hid, host in host_by_id.items():
            if scanned >= max(1, int(limit or 500)):
                break
            owner = str(host.get("owner_user_id") or "").strip()
            if not owner:
                skipped_no_owner += 1
                continue
            st = (host.get("status") or "").lower()
            if st not in ("active", "provisioning"):
                continue
            scanned += 1
            on_chain = mn._match_on_chain(host, chain_rows)
            if not on_chain:
                skipped_no_match += 1
                continue
            lastpaid = _parse_lastpaid(on_chain.get("lastpaid"))
            if lastpaid is None:
                skipped_no_match += 1
                continue

            row = host_state.get(hid) if isinstance(host_state.get(hid), dict) else {}
            prev = _parse_lastpaid(row.get("lastpaid"))
            if prev is None:
                if not dry_run:
                    host_state[hid] = {**row, "lastpaid": lastpaid, "total_credited_mn2": float(row.get("total_credited_mn2") or 0)}
                continue
            if lastpaid <= prev:
                continue

            gross = _reward_for_block_height(lastpaid, rcfg)
            amount = _net_payout(gross, rcfg)
            if amount <= 0:
                continue
            ref = f"masternode-payout:{hid}:{lastpaid}"
            credit_row = {
                "host_id": hid,
                "owner_user_id": owner,
                "lastpaid": lastpaid,
                "previous_lastpaid": prev,
                "amount_mn2": amount,
                "reference": ref,
            }
            if dry_run:
                credit_row["dry_run"] = True
                credits.append(credit_row)
                continue

            from backend.services.game_mn2_rewards import credit_mn2

            paid = credit_mn2(
                owner,
                amount,
                source="masternode_hosting_payout",
                reference=ref,
                metadata={"host_id": hid, "lastpaid": lastpaid, "gross_mn2": gross},
            )
            if not paid.get("success") and not paid.get("duplicate"):
                credit_row["error"] = paid.get("error")
                credits.append(credit_row)
                continue
            total = float(row.get("total_credited_mn2") or 0) + (0 if paid.get("duplicate") else amount)
            host_state[hid] = {
                **row,
                "lastpaid": lastpaid,
                "total_credited_mn2": round(total, 8),
                "last_credit_reference": ref,
            }
            credit_row["credited"] = not paid.get("duplicate")
            credit_row["duplicate"] = bool(paid.get("duplicate"))
            credits.append(credit_row)

            # Mirror totals on host registry for UI
            idx = next((i for i, h in enumerate(hosts) if h.get("id") == hid), None)
            if idx is not None:
                hosts[idx] = {
                    **hosts[idx],
                    "rewards_lastpaid": lastpaid,
                    "rewards_total_mn2": round(total, 8),
                    "owner_user_id": owner,
                }

        if not dry_run and (credits or host_state != state.get("hosts")):
            state["hosts"] = host_state
            _write_state(state)
            if any(c.get("credited") for c in credits):
                mn._save_hosts_doc(hosts)

    total_paid = round(sum(float(c.get("amount_mn2") or 0) for c in credits if c.get("credited")), 8)
    return {
        "success": True,
        "dry_run": dry_run,
        "scanned": scanned,
        "skipped_no_owner": skipped_no_owner,
        "skipped_no_match": skipped_no_match,
        "payouts_credited": sum(1 for c in credits if c.get("credited")),
        "total_mn2_credited": total_paid,
        "credits": credits[:50],
    }


def renter_rewards_summary(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    from backend.services import mn2_masternode_service as mn

    state = _read_state().get("hosts") or {}
    hosts = [h for h in (mn.list_hosts(include_internal=True) or []) if h.get("owner_user_id") == uid]
    rows: List[Dict[str, Any]] = []
    total = 0.0
    for h in hosts:
        hid = str(h.get("id") or "")
        st = state.get(hid) if isinstance(state.get(hid), dict) else {}
        credited = float(st.get("total_credited_mn2") or h.get("rewards_total_mn2") or 0)
        total += credited
        rows.append(
            {
                "host_id": hid,
                "label": h.get("label"),
                "status": h.get("status"),
                "rewards_total_mn2": credited,
                "rewards_lastpaid": st.get("lastpaid") or h.get("rewards_lastpaid"),
            }
        )
    return {"success": True, "user_id": uid, "hosts": rows, "rewards_total_mn2": round(total, 8)}
