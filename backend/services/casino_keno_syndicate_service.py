"""Keno syndicate — group ticket with escrow stakes and proportional win split (Wave 4)."""
from __future__ import annotations

import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import casino_service as cs


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _config() -> Dict[str, Any]:
    cfg = cs._load_config()
    block = cfg.get("keno_syndicate") if isinstance(cfg.get("keno_syndicate"), dict) else {}
    return {
        "enabled": bool(block.get("enabled", True)),
        "min_players": int(block.get("min_players") or 2),
        "max_players": int(block.get("max_players") or 8),
        "default_stake": float(block.get("default_stake") or 25),
    }


def _state_path() -> str:
    log_dir = cs._log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_keno_syndicates.json")


def _load() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.isfile(path):
        return {"syndicates": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("syndicates", {})
            return data
    except Exception:
        pass
    return {"syndicates": {}}


def _save(data: Dict[str, Any]) -> None:
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _public(s: Dict[str, Any]) -> Dict[str, Any]:
    members = []
    for m in (s.get("members") or {}).values():
        if isinstance(m, dict):
            members.append({
                "user_id": m.get("user_id"),
                "stake": m.get("stake"),
                "spots": m.get("spots") or [],
                "joined_at": m.get("joined_at"),
            })
    return {
        "syndicate_id": s.get("syndicate_id"),
        "host_id": s.get("host_id"),
        "status": s.get("status"),
        "currency": s.get("currency"),
        "stake_per_player": s.get("stake_per_player"),
        "min_players": s.get("min_players"),
        "max_players": s.get("max_players"),
        "member_count": len(members),
        "members": members,
        "combined_spots": s.get("combined_spots") or [],
        "created_at": s.get("created_at"),
        "drawn_at": s.get("drawn_at"),
        "result": s.get("result"),
    }


def create_syndicate(
    user_id: str,
    stake: float,
    *,
    currency: str = "coins",
    min_players: Optional[int] = None,
    max_players: Optional[int] = None,
) -> Dict[str, Any]:
    conf = _config()
    if not conf["enabled"]:
        return {"success": False, "error": "keno_syndicate_disabled"}
    currency = cs._normalize_currency(currency)
    stake_val = float(stake or conf["default_stake"])
    err = cs._validate_bet(user_id, stake_val, currency)
    if err:
        return {"success": False, "error": err}
    amount = cs._parse_bet_amount(stake_val, currency) or 0
    mn = int(min_players or conf["min_players"])
    mx = int(max_players or conf["max_players"])
    if mn < 2 or mx < mn:
        return {"success": False, "error": "Invalid player limits"}

    cs._apply_balance_delta(user_id, -amount, currency, "keno_syndicate", {"phase": "escrow", "role": "host"})
    sid = str(uuid.uuid4())
    syndicate = {
        "syndicate_id": sid,
        "host_id": user_id,
        "status": "open",
        "currency": currency,
        "stake_per_player": amount,
        "min_players": mn,
        "max_players": mx,
        "members": {
            user_id: {
                "user_id": user_id,
                "stake": amount,
                "spots": [],
                "joined_at": _iso(),
            }
        },
        "combined_spots": [],
        "created_at": _iso(),
    }
    data = _load()
    data["syndicates"][sid] = syndicate
    _save(data)
    pub = _public(syndicate)
    pub["invite_code"] = secrets.token_urlsafe(8)
    syndicate["invite_code"] = pub["invite_code"]
    data["syndicates"][sid] = syndicate
    _save(data)
    return {"success": True, "syndicate": pub}


def join_syndicate(
    user_id: str,
    syndicate_id: str,
    spots: List[int],
    *,
    invite_code: str = "",
) -> Dict[str, Any]:
    conf = _config()
    if not conf["enabled"]:
        return {"success": False, "error": "keno_syndicate_disabled"}
    try:
        picks = [int(x) for x in (spots or [])]
    except (TypeError, ValueError):
        return {"success": False, "error": "Invalid spots"}
    keno_conf = cs._keno_config()
    pool = keno_conf["pool"]
    max_spots = keno_conf["max_spots"]
    if not picks or len(picks) > max_spots:
        return {"success": False, "error": f"Pick 1–{max_spots} spots"}
    if len(set(picks)) != len(picks):
        return {"success": False, "error": "Duplicate spots not allowed"}
    if any(p < 1 or p > pool for p in picks):
        return {"success": False, "error": f"Spots must be 1–{pool}"}

    data = _load()
    s = data["syndicates"].get(syndicate_id)
    if not isinstance(s, dict):
        return {"success": False, "error": "Syndicate not found"}
    if s.get("status") != "open":
        return {"success": False, "error": "Syndicate is not open"}
    if invite_code and s.get("invite_code") and invite_code != s.get("invite_code"):
        return {"success": False, "error": "Invalid invite code"}
    members = s.get("members") or {}
    if user_id in members:
        return {"success": False, "error": "Already joined"}
    if len(members) >= int(s.get("max_players") or conf["max_players"]):
        return {"success": False, "error": "Syndicate is full"}

    currency = cs._normalize_currency(s.get("currency"))
    amount = cs._parse_bet_amount(s.get("stake_per_player"), currency) or 0
    err = cs._validate_bet(user_id, amount, currency)
    if err:
        return {"success": False, "error": err}
    cs._apply_balance_delta(user_id, -amount, currency, "keno_syndicate", {"phase": "escrow", "role": "member"})

    members[user_id] = {
        "user_id": user_id,
        "stake": amount,
        "spots": sorted(picks),
        "joined_at": _iso(),
    }
    s["members"] = members
    combined = sorted(set(sum((m.get("spots") or [] for m in members.values()), [])))
    s["combined_spots"] = combined
    data["syndicates"][syndicate_id] = s
    _save(data)

    auto_draw = len(members) >= int(s.get("max_players") or conf["max_players"])
    if auto_draw:
        return draw_syndicate(syndicate_id, user_id=user_id)
    return {"success": True, "syndicate": _public(s), "balance": cs._user_balance(user_id, currency)}


def draw_syndicate(syndicate_id: str, *, user_id: Optional[str] = None) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import keno as keno_engine

    data = _load()
    s = data["syndicates"].get(syndicate_id)
    if not isinstance(s, dict):
        return {"success": False, "error": "Syndicate not found"}
    if s.get("status") != "open":
        return {"success": False, "error": "Syndicate already drawn"}
    members = s.get("members") or {}
    if len(members) < int(s.get("min_players") or 2):
        return {"success": False, "error": "Not enough players yet"}
    host = s.get("host_id")
    if user_id and user_id != host:
        return {"success": False, "error": "Only the host can force draw"}

    currency = cs._normalize_currency(s.get("currency"))
    keno_conf = cs._keno_config()
    combined = sorted(set(s.get("combined_spots") or []))
    if not combined:
        return {"success": False, "error": "No spots selected"}

    proof = casino_rng.draw(syndicate_id)
    drawn = keno_engine.draw_numbers(proof["float"], keno_conf["pool"], keno_conf["draw"])
    hits = keno_engine.count_hits(combined, drawn)
    multiplier = keno_engine.payout_multiplier(len(combined), hits, keno_conf["pay_table"])

    total_stake = sum(float(m.get("stake") or 0) for m in members.values())
    gross_payout = cs._round_payout(total_stake * multiplier, currency)
    payouts: Dict[str, float] = {}
    for uid, m in members.items():
        share = float(m.get("stake") or 0) / total_stake if total_stake > 0 else 0
        payouts[uid] = cs._round_payout(gross_payout * share, currency)

    for uid, payout in payouts.items():
        if payout > 0:
            cs._apply_balance_delta(uid, payout, currency, "keno_syndicate", {
                "phase": "payout", "syndicate_id": syndicate_id, "share": round(payout / gross_payout, 4) if gross_payout else 0,
            })

    result = {
        "drawn": drawn,
        "combined_spots": combined,
        "hits": hits,
        "multiplier": multiplier,
        "total_stake": total_stake,
        "gross_payout": gross_payout,
        "payouts": payouts,
        "fairness": {
            "server_seed_hash": proof["server_seed_hash"],
            "client_seed": proof["client_seed"],
            "nonce": proof["nonce"],
        },
    }
    s["status"] = "drawn"
    s["drawn_at"] = _iso()
    s["result"] = result
    data["syndicates"][syndicate_id] = s
    _save(data)

    for uid, m in members.items():
        stake = float(m.get("stake") or 0)
        payout = payouts.get(uid) or 0
        row = {
            "bet_id": str(uuid.uuid4()),
            "user_id": uid,
            "game": "keno_syndicate",
            "bet": stake,
            "currency": currency,
            "outcome": "win" if payout > stake else ("push" if payout == stake else "loss"),
            "payout": payout,
            "net": cs._round_payout(payout - stake, currency),
            "details": {**result, "syndicate_id": syndicate_id, "role": "host" if uid == host else "member"},
            "created_at": _iso(),
            "exclude_leaderboard": False,
            "parent_bet_id": None,
            "double_step": 0,
        }
        cs._append_ledger(row)

    return {"success": True, "syndicate": _public(s), "result": result}


def list_syndicates(status: str = "open") -> Dict[str, Any]:
    data = _load()
    status = (status or "open").lower()
    rows = []
    for s in data["syndicates"].values():
        if not isinstance(s, dict):
            continue
        if status != "all" and s.get("status") != status:
            continue
        rows.append(_public(s))
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"success": True, "syndicates": rows, "count": len(rows)}


def get_syndicate(syndicate_id: str) -> Dict[str, Any]:
    data = _load()
    s = data["syndicates"].get(syndicate_id)
    if not isinstance(s, dict):
        return {"success": False, "error": "Syndicate not found"}
    return {"success": True, "syndicate": _public(s)}
