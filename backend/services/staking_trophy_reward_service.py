"""Award block smiley trophies to staking interval winners (wallet v2 upgrade path)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "staking_trophy_reward_config.json")
_GRANTS_PATH = os.path.join(_BASE, "data", "staking_trophy_grants.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {
            "enabled": True,
            "winners_per_interval": 1,
            "min_reward_mn2": 0.001,
            "prefer_chain_tip_block": True,
        }
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"enabled": True, "winners_per_interval": 1, "min_reward_mn2": 0.001}


def _interval_already_granted(interval_id: str) -> bool:
    if not os.path.isfile(_GRANTS_PATH):
        return False
    try:
        with open(_GRANTS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("interval_id") == interval_id:
                    return True
    except Exception:
        pass
    return False


def _append_grant(row: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_GRANTS_PATH), exist_ok=True)
    with _LOCK:
        with open(_GRANTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")


def _pick_winners(
    rows: List[Dict[str, Any]],
    limit: int,
    min_reward: float,
    *,
    interval_id: str = "",
) -> List[Dict[str, Any]]:
    eligible = [
        r for r in rows
        if float(r.get("reward_mn2") or 0) >= min_reward and (r.get("user_id") or "").strip()
    ]
    eligible.sort(key=lambda r: float(r.get("reward_mn2") or 0), reverse=True)
    winners = eligible[: max(1, limit)]
    cfg = get_config()
    if cfg.get("team_pool_rotate") and winners and interval_id:
        try:
            from backend.services.mn2_staking_teams import get_team_for_user

            top = winners[0]
            uid = (top.get("user_id") or "").strip()
            team = get_team_for_user(uid) or {}
            member_ids = []
            for m in team.get("members") or []:
                mid = (m.get("user_id") if isinstance(m, dict) else m) or ""
                if mid:
                    member_ids.append(str(mid).strip())
            pool_rows = [r for r in eligible if (r.get("user_id") or "").strip() in member_ids]
            if len(pool_rows) > 1:
                idx = abs(hash(interval_id)) % len(pool_rows)
                winners[0] = {**pool_rows[idx], "team_pool_rotate": True, "team_id": team.get("team_id")}
        except Exception:
            pass
    return winners


def _find_grant_height(prefer_tip: bool) -> Optional[int]:
    from backend.services.block_mint_service import sync_block_height, _read_json, _MANIFEST_PATH

    sync = sync_block_height()
    tip = int(sync.get("block_height") or 0) if sync.get("success") else 0
    doc = _read_json(_MANIFEST_PATH, {"drops": {}})
    drops = doc.get("drops") or {}

    if prefer_tip and tip:
        row = drops.get(str(tip)) or {}
        if not row.get("claimed_by"):
            return tip

    for key in sorted(drops.keys(), key=lambda x: int(x), reverse=True):
        row = drops[key]
        if not row.get("claimed_by"):
            return int(row.get("height") or key)
    return tip if tip else None


def grant_staking_block_trophy(
    user_id: str,
    height: int,
    *,
    interval_id: str,
    reward_mn2: float = 0.0,
) -> Dict[str, Any]:
    """Grant an unclaimed block trophy to a staking winner (no MN2 charge)."""
    from backend.services.block_mint_service import claim_block_trophy_staking_reward

    return claim_block_trophy_staking_reward(
        user_id,
        int(height),
        interval_id=interval_id,
        reward_mn2=reward_mn2,
    )


def process_interval_winners(
    reward_rows: List[Dict[str, Any]],
    *,
    interval_id: str,
) -> Dict[str, Any]:
    """Pick staking interval winner(s) and grant block trophy editions."""
    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": True, "skipped": True, "reason": "disabled"}
    if not reward_rows or not interval_id:
        return {"success": True, "skipped": True, "reason": "no_rows"}

    if _interval_already_granted(interval_id):
        return {"success": True, "skipped": True, "reason": "already_granted", "interval_id": interval_id}

    winners = _pick_winners(
        reward_rows,
        int(cfg.get("winners_per_interval") or 1),
        float(cfg.get("min_reward_mn2") or 0.001),
        interval_id=interval_id,
    )
    if not winners:
        return {"success": True, "skipped": True, "reason": "no_eligible_winners"}

    height = _find_grant_height(bool(cfg.get("prefer_chain_tip_block", True)))
    if not height:
        return {"success": False, "error": "no_block_height_for_grant"}

    grants: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    used_heights: set[int] = set()

    for winner in winners:
        uid = (winner.get("user_id") or "").strip()
        grant_height = height
        if grant_height in used_heights:
            grant_height = _find_grant_height(False)
        if not grant_height or grant_height in used_heights:
            errors.append({"user_id": uid, "error": "no_unclaimed_block"})
            continue

        result = grant_staking_block_trophy(
            uid,
            grant_height,
            interval_id=interval_id,
            reward_mn2=float(winner.get("reward_mn2") or 0),
        )
        if result.get("success"):
            used_heights.add(grant_height)
            grant_row = {
                "interval_id": interval_id,
                "user_id": uid,
                "block_height": grant_height,
                "edition_key": result.get("edition_key"),
                "license_number": result.get("license_number"),
                "gif_url": result.get("gif_url"),
                "battle_stats": result.get("battle_stats"),
                "reward_mn2": float(winner.get("reward_mn2") or 0),
                "granted_at": _iso(),
                "per_edition_gif": bool((result.get("enrichment") or {}).get("gif_url")),
            }
            _append_grant(grant_row)
            grants.append(grant_row)
            if cfg.get("notify_wallet", True):
                try:
                    from backend.services.mn2_staking_notifications import on_staking_trophy_grant

                    on_staking_trophy_grant(uid, grant_row)
                except Exception:
                    pass
        else:
            errors.append({"user_id": uid, "error": result.get("error"), "height": grant_height})

    return {
        "success": bool(grants),
        "interval_id": interval_id,
        "granted": len(grants),
        "grants": grants,
        "errors": errors,
    }


def user_staking_trophy_grants(user_id: str, *, limit: int = 20) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    rows: List[Dict[str, Any]] = []
    if os.path.isfile(_GRANTS_PATH):
        try:
            with open(_GRANTS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if row.get("user_id") == uid:
                        rows.append(row)
        except Exception:
            pass
    rows.sort(key=lambda r: r.get("granted_at") or "", reverse=True)
    rows = rows[: max(1, min(limit, 100))]
    return {"success": True, "user_id": uid, "grants": rows, "count": len(rows)}
