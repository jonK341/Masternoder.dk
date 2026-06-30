"""Plinko battle and mines duel — PvP escrow duels (Wave 3). Friend challenge links (Wave 4)."""
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


def _invites_path() -> str:
    log_dir = cs._log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_duel_invites.json")


def _load_invites() -> Dict[str, str]:
    path = _invites_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_invites(data: Dict[str, str]) -> None:
    try:
        with open(_invites_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def create_invite_token(duel_id: str) -> str:
    token = secrets.token_urlsafe(12)
    invites = _load_invites()
    invites[token] = duel_id
    _save_invites(invites)
    return token


def invite_url(token: str) -> str:
    base = os.environ.get("BASE_URL", "https://masternoder.dk").rstrip("/")
    return f"{base}/casino/?duel={token}"


def resolve_invite_token(token: str) -> Dict[str, Any]:
    """Look up duel by invite token — checks game duels then pvp duels."""
    token = (token or "").strip()
    if not token:
        return {"success": False, "error": "Missing token"}
    invites = _load_invites()
    duel_id = invites.get(token)
    if not duel_id:
        data = _load()
        for d in data["duels"].values():
            if isinstance(d, dict) and d.get("invite_token") == token:
                duel_id = d.get("duel_id")
                break
    if not duel_id:
        pvp = cs._load_duels()
        for d in pvp.values():
            if isinstance(d, dict) and d.get("invite_token") == token:
                duel_id = d.get("duel_id")
                break
    if not duel_id:
        return {"success": False, "error": "Invite not found or expired"}

    data = _load()
    duel = data["duels"].get(duel_id)
    if isinstance(duel, dict):
        pub = {k: v for k, v in duel.items() if k not in ("challenger_choice", "mine_positions", "result")}
        pub["invite_token"] = token
        pub["invite_url"] = invite_url(token)
        pub["duel_source"] = "game"
        return {"success": True, "duel": pub, "invite_token": token, "invite_url": pub["invite_url"]}

    pvp = cs._load_duels()
    duel = pvp.get(duel_id)
    if isinstance(duel, dict):
        pub = {k: v for k, v in duel.items() if k != "challenger_choice"}
        pub["invite_token"] = token
        pub["invite_url"] = invite_url(token)
        pub["duel_source"] = "pvp"
        return {"success": True, "duel": pub, "invite_token": token, "invite_url": pub["invite_url"]}
    return {"success": False, "error": "Duel not found"}


def _duels_path() -> str:
    log_dir = cs._log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_game_duels.json")


def _load() -> Dict[str, Any]:
    path = _duels_path()
    if not os.path.isfile(path):
        return {"duels": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("duels", {})
            return data
    except Exception:
        pass
    return {"duels": {}}


def _save(data: Dict[str, Any]) -> None:
    try:
        with open(_duels_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _duel_rake() -> float:
    cfg = cs._load_config()
    social = cfg.get("pvp") if isinstance(cfg.get("pvp"), dict) else {}
    return float(social.get("rake_percent") or 5.0) / 100.0


def _mines_duel_config() -> Dict[str, Any]:
    cfg = cs._load_config()
    block = cfg.get("mines_duel") if isinstance(cfg.get("mines_duel"), dict) else {}
    return {
        "enabled": bool(block.get("enabled", True)),
        "tiles": int(block.get("tiles") or 25),
        "mines": int(block.get("mines") or 3),
    }


def _settle_duel_pot(
    duel_id: str,
    duel: Dict[str, Any],
    winner_id: Optional[str],
    result_detail: Dict[str, Any],
    game_type: str,
) -> Dict[str, Any]:
    """Pay winner or split on tie; ledger both players."""
    from backend.services import casino_competition_service

    challenger = duel["challenger_id"]
    acceptor = duel.get("acceptor_id")
    if not acceptor:
        return {"success": False, "error": "duel_not_accepted"}
    currency = cs._normalize_currency(duel.get("currency"))
    amount = cs._parse_bet_amount(duel.get("bet"), currency) or 0
    pot = amount * 2
    rake = round(pot * _duel_rake(), 8 if currency == "mn2" else 2)
    prize = cs._round_payout(pot - rake, currency)
    outcome = "push"
    if winner_id:
        cs._apply_balance_delta(winner_id, prize, currency, "pvp_duel", {"phase": "payout", "duel_id": duel_id})
        outcome = "win"
    else:
        half = cs._round_payout((pot - rake) / 2, currency)
        cs._apply_balance_delta(challenger, half, currency, "pvp_duel", {"phase": "refund", "duel_id": duel_id})
        cs._apply_balance_delta(acceptor, half, currency, "pvp_duel", {"phase": "refund", "duel_id": duel_id})
        prize = half

    for uid, role in ((challenger, "challenger"), (acceptor, "acceptor")):
        if winner_id:
            net = prize - amount if winner_id == uid else -amount
            row_outcome = "win" if winner_id == uid else "loss"
            payout = prize if winner_id == uid else 0
        else:
            net = prize - amount
            row_outcome = "push"
            payout = prize
        row = {
            "bet_id": str(uuid.uuid4()),
            "user_id": uid,
            "game": game_type,
            "bet": amount,
            "currency": currency,
            "outcome": row_outcome,
            "payout": payout,
            "net": net,
            "details": {**result_detail, "duel_id": duel_id, "role": role, "game_type": game_type},
            "created_at": _iso(),
            "exclude_leaderboard": False,
            "parent_bet_id": None,
            "double_step": 0,
        }
        cs._append_ledger(row)

    loser = None
    if winner_id:
        loser = acceptor if winner_id == challenger else challenger
    try:
        casino_competition_service.on_duel_settled(winner_id, loser, challenger, acceptor)
    except Exception:
        pass

    return {
        "success": True,
        "duel_id": duel_id,
        "winner_id": winner_id,
        "prize": prize if winner_id else None,
        "rake": rake,
        "outcome": outcome,
        "details": result_detail,
    }


def create_plinko_battle(
    user_id: str,
    bet: float,
    *,
    risk: str = "medium",
    currency: str = "coins",
) -> Dict[str, Any]:
    currency = cs._normalize_currency(currency)
    err = cs._validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = cs._parse_bet_amount(bet, currency) or 0
    risk = (risk or "medium").strip().lower()
    conf = cs._plinko_config()
    if risk not in conf["risk_tables"]:
        return {"success": False, "error": f"risk must be one of {sorted(conf['risk_tables'].keys())}"}
    cs._apply_balance_delta(user_id, -amount, currency, "pvp_duel", {"phase": "escrow", "role": "challenger"})
    duel_id = str(uuid.uuid4())
    duel = {
        "duel_id": duel_id,
        "game": "plinko_battle",
        "bet": amount,
        "currency": currency,
        "risk": risk,
        "challenger_id": user_id,
        "acceptor_id": None,
        "status": "open",
        "created_at": _iso(),
    }
    data = _load()
    data["duels"][duel_id] = duel
    _save(data)
    token = create_invite_token(duel_id)
    duel["invite_token"] = token
    return {"success": True, "duel": {k: v for k, v in duel.items()}, "invite_token": token, "invite_url": invite_url(token)}


def accept_plinko_battle(user_id: str, duel_id: str) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import plinko as plinko_engine

    data = _load()
    duel = data["duels"].get(duel_id)
    if not isinstance(duel, dict):
        return {"success": False, "error": "Duel not found"}
    if duel.get("game") != "plinko_battle":
        return {"success": False, "error": "Not a plinko battle duel"}
    if duel.get("status") != "open":
        return {"success": False, "error": "Duel is not open"}
    if duel.get("challenger_id") == user_id:
        return {"success": False, "error": "Cannot accept your own duel"}

    currency = cs._normalize_currency(duel.get("currency"))
    amount = cs._parse_bet_amount(duel.get("bet"), currency) or 0
    err = cs._validate_bet(user_id, amount, currency)
    if err:
        return {"success": False, "error": err}
    cs._apply_balance_delta(user_id, -amount, currency, "pvp_duel", {"phase": "escrow", "role": "acceptor"})

    conf = cs._plinko_config()
    risk = str(duel.get("risk") or "medium")
    table = conf["risk_tables"][risk]
    challenger = duel["challenger_id"]
    proof_c = casino_rng.draw(challenger)
    proof_a = casino_rng.draw(user_id)
    res_c = plinko_engine.play(proof_c["float"], conf["rows"], table)
    res_a = plinko_engine.play(proof_a["float"], conf["rows"], table)
    bin_c = int(res_c["bin"])
    bin_a = int(res_a["bin"])
    winner_id = None
    if bin_c > bin_a:
        winner_id = challenger
    elif bin_a > bin_c:
        winner_id = user_id

    result_detail = {
        "risk": risk,
        "rows": conf["rows"],
        "challenger": {"bin": bin_c, "multiplier": res_c["multiplier"], "path": res_c["path"]},
        "acceptor": {"bin": bin_a, "multiplier": res_a["multiplier"], "path": res_a["path"]},
        "fairness": {
            "challenger": {
                "server_seed_hash": proof_c["server_seed_hash"],
                "client_seed": proof_c["client_seed"],
                "nonce": proof_c["nonce"],
            },
            "acceptor": {
                "server_seed_hash": proof_a["server_seed_hash"],
                "client_seed": proof_a["client_seed"],
                "nonce": proof_a["nonce"],
            },
        },
    }

    duel["status"] = "resolved"
    duel["acceptor_id"] = user_id
    duel["winner_id"] = winner_id
    duel["resolved_at"] = _iso()
    duel["result"] = result_detail
    data["duels"][duel_id] = duel
    _save(data)

    settled = _settle_duel_pot(duel_id, duel, winner_id, result_detail, "plinko_battle")
    settled["balance"] = cs._user_balance(user_id, currency)
    return settled


def list_game_duels(game: str = "plinko_battle", status: str = "open") -> Dict[str, Any]:
    data = _load()
    status = (status or "open").lower()
    game = (game or "").strip().lower()
    rows: List[Dict[str, Any]] = []
    for d in data["duels"].values():
        if not isinstance(d, dict):
            continue
        if game and d.get("game") != game:
            continue
        if status != "all" and d.get("status") != status:
            continue
        rows.append({k: v for k, v in d.items() if k != "result"})
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"success": True, "duels": rows, "count": len(rows)}


def create_mines_duel(user_id: str, bet: float, currency: str = "coins") -> Dict[str, Any]:
    conf = _mines_duel_config()
    if not conf["enabled"]:
        return {"success": False, "error": "mines_duel_disabled"}
    currency = cs._normalize_currency(currency)
    err = cs._validate_bet(user_id, bet, currency)
    if err:
        return {"success": False, "error": err}
    amount = cs._parse_bet_amount(bet, currency) or 0
    cs._apply_balance_delta(user_id, -amount, currency, "pvp_duel", {"phase": "escrow", "role": "challenger"})
    duel_id = str(uuid.uuid4())
    duel = {
        "duel_id": duel_id,
        "game": "mines_duel",
        "bet": amount,
        "currency": currency,
        "tiles": conf["tiles"],
        "mine_count": conf["mines"],
        "challenger_id": user_id,
        "acceptor_id": None,
        "status": "open",
        "turn": None,
        "revealed": [],
        "picks": {},
        "mine_positions": None,
        "created_at": _iso(),
    }
    data = _load()
    data["duels"][duel_id] = duel
    _save(data)
    token = create_invite_token(duel_id)
    duel["invite_token"] = token
    return {"success": True, "duel": duel, "invite_token": token, "invite_url": invite_url(token)}


def accept_mines_duel(user_id: str, duel_id: str) -> Dict[str, Any]:
    from backend.services import casino_rng
    from backend.services.engines import mines as mines_engine

    data = _load()
    duel = data["duels"].get(duel_id)
    if not isinstance(duel, dict):
        return {"success": False, "error": "Duel not found"}
    if duel.get("game") != "mines_duel":
        return {"success": False, "error": "Not a mines duel"}
    if duel.get("status") != "open":
        return {"success": False, "error": "Duel is not open"}
    if duel.get("challenger_id") == user_id:
        return {"success": False, "error": "Cannot accept your own duel"}

    currency = cs._normalize_currency(duel.get("currency"))
    amount = cs._parse_bet_amount(duel.get("bet"), currency) or 0
    err = cs._validate_bet(user_id, amount, currency)
    if err:
        return {"success": False, "error": err}
    cs._apply_balance_delta(user_id, -amount, currency, "pvp_duel", {"phase": "escrow", "role": "acceptor"})

    proof = casino_rng.draw(duel_id)
    tiles = int(duel.get("tiles") or 25)
    mine_count = int(duel.get("mine_count") or 3)
    positions = mines_engine.mine_positions(proof["float"], tiles, mine_count)

    duel["acceptor_id"] = user_id
    duel["status"] = "live"
    duel["turn"] = duel["challenger_id"]
    duel["picks"] = {duel["challenger_id"]: 0, user_id: 0}
    duel["mine_positions"] = positions
    duel["fairness"] = {
        "server_seed_hash": proof["server_seed_hash"],
        "client_seed": proof["client_seed"],
        "nonce": proof["nonce"],
    }
    duel["started_at"] = _iso()
    data["duels"][duel_id] = duel
    _save(data)
    return {
        "success": True,
        "duel_id": duel_id,
        "status": "live",
        "turn": duel["turn"],
        "tiles": tiles,
        "mine_count": mine_count,
        "revealed_count": 0,
    }


def pick_mines_duel_tile(user_id: str, duel_id: str, tile: int) -> Dict[str, Any]:
    data = _load()
    duel = data["duels"].get(duel_id)
    if not isinstance(duel, dict):
        return {"success": False, "error": "Duel not found"}
    if duel.get("game") != "mines_duel":
        return {"success": False, "error": "Not a mines duel"}
    if duel.get("status") != "live":
        return {"success": False, "error": "Duel is not live"}
    if duel.get("turn") != user_id:
        return {"success": False, "error": "Not your turn"}

    try:
        idx = int(tile)
    except (TypeError, ValueError):
        return {"success": False, "error": "Invalid tile"}
    tiles = int(duel.get("tiles") or 25)
    if idx < 0 or idx >= tiles:
        return {"success": False, "error": "Tile out of range"}

    revealed: List[int] = list(duel.get("revealed") or [])
    if idx in revealed:
        return {"success": False, "error": "Tile already picked"}

    positions = duel.get("mine_positions") or []
    revealed.append(idx)
    duel["revealed"] = revealed

    if idx in positions:
        winner_id = duel["acceptor_id"] if user_id == duel["challenger_id"] else duel["challenger_id"]
        duel["status"] = "resolved"
        duel["winner_id"] = winner_id
        duel["resolved_at"] = _iso()
        duel["loser_id"] = user_id
        data["duels"][duel_id] = duel
        _save(data)
        result_detail = {
            "hit_mine": True,
            "tile": idx,
            "loser_id": user_id,
            "revealed": revealed,
            "fairness": duel.get("fairness"),
        }
        settled = _settle_duel_pot(duel_id, duel, winner_id, result_detail, "mines_duel")
        settled["hit_mine"] = True
        settled["revealed"] = revealed
        return settled

    picks = duel.get("picks") if isinstance(duel.get("picks"), dict) else {}
    picks[user_id] = int(picks.get(user_id) or 0) + 1
    duel["picks"] = picks
    other = duel["acceptor_id"] if user_id == duel["challenger_id"] else duel["challenger_id"]
    duel["turn"] = other

    data["duels"][duel_id] = duel
    _save(data)
    return {
        "success": True,
        "duel_id": duel_id,
        "status": "live",
        "safe": True,
        "tile": idx,
        "turn": duel["turn"],
        "revealed": revealed,
    }


def list_mines_duels(status: str = "open") -> Dict[str, Any]:
    return list_game_duels("mines_duel", status=status)


def get_mines_duel(duel_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    data = _load()
    duel = data["duels"].get(duel_id)
    if not isinstance(duel, dict):
        return {"success": False, "error": "Duel not found"}
    pub = {k: v for k, v in duel.items() if k != "mine_positions"}
    pub["revealed"] = list(duel.get("revealed") or [])
    pub["revealed_count"] = len(pub["revealed"])
    if duel.get("status") == "resolved" and user_id and user_id in (duel.get("challenger_id"), duel.get("acceptor_id")):
        pub["mine_positions"] = duel.get("mine_positions")
    return {"success": True, "duel": pub}
