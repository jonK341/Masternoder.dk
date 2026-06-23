"""
Casino tournaments — time-boxed, real-money-capable prize competitions.

Each tournament has a single currency rail (coins / mn2 / usd), a house-seeded
prize pool grown by real-money buy-ins, and a scoring window. Players join by
paying the buy-in (real-money rails go through the same security gate as bets);
their score is the cumulative net result of their bets in that currency during
the window. When the window closes the pool is split among the top finishers per
a configurable prize structure and credited through the normal balance path.

Everything is ledgered to `logs/casino_tournament_ledger.jsonl` (seed / buyin /
payout) and the per-tournament pool satisfies

    house_seed + buyins_collected - paid_out == leftover (>= 0)

which `reconcile()` verifies. State lives in `logs/casino_tournaments.json`.
Daily templates auto-recreate so there is always a live competition to join.
"""
from __future__ import annotations

import json
import os
import secrets
import hashlib
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()


def _cs():
    from backend.services import casino_service
    return casino_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _utcnow()).isoformat()


def _log_dir() -> str:
    return _cs()._log_dir()


def _state_path() -> str:
    d = _log_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "casino_tournaments.json")


def _ledger_path() -> str:
    d = _log_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "casino_tournament_ledger.jsonl")


def _config() -> Dict[str, Any]:
    cfg = _cs()._load_config()
    tc = cfg.get("tournaments") if isinstance(cfg.get("tournaments"), dict) else {}
    split = tc.get("prize_split") if isinstance(tc.get("prize_split"), list) else [0.5, 0.3, 0.2]
    templates = tc.get("templates") if isinstance(tc.get("templates"), list) else []
    return {
        "enabled": bool(tc.get("enabled")),
        "scoring": (tc.get("scoring") or "net"),
        "prize_split": [float(x) for x in split],
        "rake": float(tc.get("rake") or 0.0),
        "auto_recreate": bool(tc.get("auto_recreate", True)),
        "templates": [t for t in templates if isinstance(t, dict)],
    }


def _round(amount: float, currency: str) -> float:
    if currency == "mn2":
        return round(amount, 8)
    if currency == "usd":
        return round(amount, 2)
    return float(int(amount))


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: Dict[str, Any]) -> None:
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _append_tledger(row: Dict[str, Any]) -> None:
    try:
        with open(_ledger_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _last_revealed_seed(state: Dict[str, Any], template_id: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Previous ended cup server seed for chained fairness."""
    if not template_id:
        return None, None
    ended = [
        t for t in state.values()
        if isinstance(t, dict) and t.get("template_id") == template_id and t.get("status") == "ended"
    ]
    ended.sort(key=lambda t: t.get("ended_at") or "", reverse=True)
    for t in ended:
        rev = t.get("fairness_revealed") or t.get("fairness") or {}
        seed = rev.get("server_seed")
        if seed:
            return str(seed), str(t.get("id") or "")
    return None, None


def _fairness_seed(state: Dict[str, Any], template_id: Optional[str]) -> Dict[str, Any]:
    prev_seed, prev_tid = _last_revealed_seed(state, template_id)
    if prev_seed:
        server_seed = hashlib.sha256(f"{prev_seed}|{template_id or 'cup'}|chain-v1".encode("utf-8")).hexdigest()
        chain = {
            "prev_tournament_id": prev_tid,
            "prev_seed_hash": hashlib.sha256(prev_seed.encode("utf-8")).hexdigest(),
            "genesis": False,
        }
    else:
        server_seed = secrets.token_hex(32)
        chain = {"genesis": True}
    return {
        "server_seed": server_seed,
        "server_seed_hash": hashlib.sha256(server_seed.encode("utf-8")).hexdigest(),
        "client_seed": "masternoder-tournament-v1",
        "nonce": 0,
        "chain": chain,
    }


def _tie_break_score(t: Dict[str, Any], user_id: str, score: float, joined_at: str) -> float:
    """Deterministic tie-break using committed tournament fairness seed."""
    fair = t.get("fairness") or {}
    seed = fair.get("server_seed")
    if not seed:
        return score
    try:
        from backend.services.casino_rng import hmac_float
        nonce = int(fair.get("nonce") or 0)
        uid_hash = hashlib.sha256(str(user_id).encode()).hexdigest()[:8]
        jitter = hmac_float(seed, fair.get("client_seed") or "tournament", nonce + int(uid_hash, 16) % 100000)
        return score + jitter * 1e-9
    except Exception:
        return score


def _create_from_template(tpl: Dict[str, Any], conf: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    currency = (tpl.get("currency") or "coins").lower()
    house_seed = float(tpl.get("house_seed") or 0)
    duration = float(tpl.get("duration_hours") or 24)
    start = _utcnow()
    end = start + timedelta(hours=duration)
    tid = f"{tpl.get('id') or 'cup'}-{start.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    t = {
        "id": tid,
        "template_id": tpl.get("id"),
        "name": tpl.get("name") or "Tournament",
        "currency": currency,
        "buy_in": float(tpl.get("buy_in") or 0),
        "house_seed": house_seed,
        "prize_split": conf["prize_split"],
        "scoring": conf["scoring"],
        "status": "running",
        "start_at": _iso(start),
        "end_at": _iso(end),
        "pool": house_seed,
        "buyins_collected": 0.0,
        "paid_out": 0.0,
        "entries": {},
        "results": [],
        "fairness": _fairness_seed(state, tpl.get("id")),
    }
    _append_tledger({"type": "seed", "tournament_id": tid, "currency": currency,
                     "amount": house_seed, "pool_after": house_seed, "at": _iso()})
    return t


def _ensure_templates(state: Dict[str, Any], conf: Dict[str, Any]) -> bool:
    if not conf["enabled"] or not conf["auto_recreate"]:
        return False
    changed = False
    for tpl in conf["templates"]:
        tpl_id = tpl.get("id")
        if not tpl_id:
            continue
        has_live = any(
            isinstance(t, dict) and t.get("template_id") == tpl_id and t.get("status") == "running"
            for t in state.values()
        )
        if not has_live:
            t = _create_from_template(tpl, conf, state)
            state[t["id"]] = t
            changed = True
    return changed


def _rank_entries(t: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = t.get("entries") or {}
    rows = []
    for uid, e in entries.items():
        if not isinstance(e, dict):
            continue
        rows.append({
            "user_id": uid,
            "score": float(e.get("score") or 0.0),
            "games": int(e.get("games") or 0),
            "joined_at": e.get("joined_at") or "",
            "_sort_score": _tie_break_score(t, uid, float(e.get("score") or 0.0), e.get("joined_at") or ""),
        })
    rows.sort(key=lambda r: (-r["_sort_score"], r["joined_at"]))
    for i, r in enumerate(rows):
        r.pop("_sort_score", None)
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


def _finalize(t: Dict[str, Any]) -> None:
    currency = t.get("currency") or "coins"
    pool = float(t.get("pool") or 0)
    split = t.get("prize_split") or [0.5, 0.3, 0.2]
    ranked = _rank_entries(t)
    results: List[Dict[str, Any]] = []
    paid = 0.0
    for i, r in enumerate(ranked):
        prize = _round(pool * split[i], currency) if i < len(split) else 0.0
        if prize > 0:
            try:
                _cs()._apply_balance_delta(
                    r["user_id"], prize, currency, "tournament",
                    {"phase": "prize", "tournament_id": t.get("id"), "rank": r["rank"]},
                )
            except Exception:
                prize = 0.0
            if prize > 0:
                paid += prize
                _append_tledger({"type": "payout", "tournament_id": t.get("id"),
                                 "currency": currency, "user_id": r["user_id"],
                                 "rank": r["rank"], "amount": prize, "at": _iso()})
        results.append({"rank": r["rank"], "user_id": r["user_id"],
                        "score": r["score"], "prize": prize})
    t["paid_out"] = _round(paid, currency)
    t["results"] = results
    t["status"] = "ended"
    t["ended_at"] = _iso()
    try:
        from backend.services.casino_social_service import on_tournament_end, on_tournament_prize
        on_tournament_end(
            tournament_id=t.get("id") or "",
            title=t.get("title") or "Casino tournament",
            currency=currency,
            pool=pool,
            winner_count=len([r for r in results if float(r.get("prize") or 0) > 0]),
        )
        for r in results:
            if float(r.get("prize") or 0) > 0:
                on_tournament_prize(
                    user_id=r.get("user_id") or "",
                    tournament_id=t.get("id") or "",
                    rank=int(r.get("rank") or 0),
                    prize=float(r.get("prize") or 0),
                    currency=currency,
                )
    except Exception:
        pass
    fair = t.get("fairness") or {}
    if fair.get("server_seed"):
        t["fairness_revealed"] = {
            "server_seed": fair.get("server_seed"),
            "server_seed_hash": fair.get("server_seed_hash"),
            "client_seed": fair.get("client_seed"),
            "nonce": fair.get("nonce"),
            "chain": fair.get("chain"),
        }


def _maybe_finalize(state: Dict[str, Any]) -> bool:
    changed = False
    now = _utcnow()
    for t in state.values():
        if not isinstance(t, dict) or t.get("status") != "running":
            continue
        try:
            end = datetime.fromisoformat(t.get("end_at"))
        except Exception:
            continue
        if now >= end:
            _finalize(t)
            changed = True
    return changed


def _public(t: Dict[str, Any], user_id: Optional[str], top: int = 10) -> Dict[str, Any]:
    currency = t.get("currency") or "coins"
    ranked = _rank_entries(t)
    results_by_uid = {r["user_id"]: r for r in (t.get("results") or [])}
    board = []
    for r in ranked[:top]:
        row = {"rank": r["rank"], "user_id": r["user_id"], "score": r["score"], "games": r["games"]}
        if r["user_id"] in results_by_uid:
            row["prize"] = results_by_uid[r["user_id"]].get("prize")
        board.append(row)
    your_entry = None
    if user_id and user_id in (t.get("entries") or {}):
        mine = next((r for r in ranked if r["user_id"] == user_id), None)
        if mine:
            your_entry = {"rank": mine["rank"], "score": mine["score"], "games": mine["games"]}
            if user_id in results_by_uid:
                your_entry["prize"] = results_by_uid[user_id].get("prize")
    fair_pub = None
    if t.get("fairness_revealed"):
        fair_pub = t.get("fairness_revealed")
    elif isinstance(t.get("fairness"), dict):
        fair_pub = {
            "server_seed_hash": t["fairness"].get("server_seed_hash"),
            "client_seed": t["fairness"].get("client_seed"),
            "chain": t["fairness"].get("chain"),
        }
    return {
        "id": t.get("id"),
        "name": t.get("name"),
        "currency": currency,
        "buy_in": t.get("buy_in"),
        "status": t.get("status"),
        "start_at": t.get("start_at"),
        "end_at": t.get("end_at"),
        "prize_pool": _round(float(t.get("pool") or 0), currency),
        "prize_split": t.get("prize_split"),
        "scoring": t.get("scoring"),
        "entrants": len(t.get("entries") or {}),
        "joined": bool(user_id and user_id in (t.get("entries") or {})),
        "your_entry": your_entry,
        "leaderboard": board,
        "results": t.get("results") or [],
        "fairness": fair_pub,
    }


def list_tournaments(user_id: Optional[str] = None) -> Dict[str, Any]:
    conf = _config()
    if not conf["enabled"]:
        return {"success": True, "enabled": False, "tournaments": []}
    with _LOCK:
        state = _load_state()
        changed = _maybe_finalize(state)
        changed = _ensure_templates(state, conf) or changed
        if changed:
            _save_state(state)
        live = [t for t in state.values() if isinstance(t, dict) and t.get("status") == "running"]
        ended = [t for t in state.values() if isinstance(t, dict) and t.get("status") == "ended"]
        live.sort(key=lambda t: t.get("end_at") or "")
        ended.sort(key=lambda t: t.get("ended_at") or "", reverse=True)
        out = [_public(t, user_id) for t in live] + [_public(t, user_id) for t in ended[:5]]
    return {"success": True, "enabled": True, "tournaments": out}


def get_tournament(tournament_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    conf = _config()
    with _LOCK:
        state = _load_state()
        changed = _maybe_finalize(state)
        if changed:
            _save_state(state)
        t = state.get(tournament_id)
        if not isinstance(t, dict):
            return {"success": False, "error": "Tournament not found"}
        pub = _public(t, user_id, top=50)
    return {"success": True, "tournament": pub}


def join_tournament(user_id: str, tournament_id: str) -> Dict[str, Any]:
    conf = _config()
    if not conf["enabled"]:
        return {"success": False, "error": "Tournaments are disabled"}
    if not user_id or str(user_id).strip().lower() == "default_user":
        return {"success": False, "error": "Create an account first", "code": "ACCOUNT_REQUIRED"}

    with _LOCK:
        state = _load_state()
        _maybe_finalize(state)
        _ensure_templates(state, conf)
        t = state.get(tournament_id)
        if not isinstance(t, dict):
            return {"success": False, "error": "Tournament not found"}
        if t.get("status") != "running":
            return {"success": False, "error": "Tournament is not open for entries"}
        if user_id in (t.get("entries") or {}):
            return {"success": False, "error": "Already joined", "code": "ALREADY_JOINED"}

        currency = t.get("currency") or "coins"
        buy_in = float(t.get("buy_in") or 0)
        err = _charge_buyin(user_id, currency, buy_in, tournament_id)
        if err:
            return {"success": False, "error": err}

        if buy_in > 0:
            t["buyins_collected"] = float(t.get("buyins_collected") or 0) + buy_in
            t["pool"] = float(t.get("pool") or 0) + buy_in
            _append_tledger({"type": "buyin", "tournament_id": tournament_id, "currency": currency,
                             "user_id": user_id, "amount": buy_in, "pool_after": t["pool"], "at": _iso()})
        t.setdefault("entries", {})[user_id] = {
            "score": 0.0, "buy_in_paid": buy_in, "games": 0, "joined_at": _iso(),
        }
        _save_state(state)
        pub = _public(t, user_id, top=50)
    return {"success": True, "tournament": pub, "balance": _cs()._user_balance(user_id, currency)}


def _charge_buyin(user_id: str, currency: str, amount: float, tournament_id: str) -> Optional[str]:
    cs = _cs()
    currency = cs._normalize_currency(currency)
    if amount <= 0:
        return None
    if currency in ("mn2", "usd"):
        try:
            from flask import has_request_context, request
            from backend.services.account_security_service import check_real_money_action
            token = None
            if has_request_context():
                data = request.get_json(silent=True) or {}
                token = data.get("verification_token") or data.get("security_token")
            sec_err = check_real_money_action(user_id, verification_token=token)
            if sec_err:
                return sec_err
        except Exception:
            pass
    if cs._user_balance(user_id, currency) < amount:
        return f"Insufficient {cs._currency_label(currency)} for the buy-in"
    cs._apply_balance_delta(user_id, -amount, currency, "tournament",
                            {"phase": "buyin", "tournament_id": tournament_id})
    return None


def record_bet(row: Dict[str, Any]) -> None:
    """Add a settled bet's net (or wager) to any running tournament the user is in."""
    if not isinstance(row, dict) or row.get("exclude_leaderboard"):
        return
    conf = _config()
    if not conf["enabled"]:
        return
    user_id = row.get("user_id")
    if not user_id:
        return
    currency = (row.get("currency") or "coins").lower()
    scoring = conf["scoring"]
    try:
        delta = float(row.get("net") or 0) if scoring == "net" else float(row.get("bet") or 0)
    except (TypeError, ValueError):
        return
    with _LOCK:
        state = _load_state()
        changed = False
        for t in state.values():
            if not isinstance(t, dict) or t.get("status") != "running":
                continue
            if (t.get("currency") or "coins") != currency:
                continue
            entry = (t.get("entries") or {}).get(user_id)
            if not isinstance(entry, dict):
                continue
            entry["score"] = float(entry.get("score") or 0.0) + delta
            entry["games"] = int(entry.get("games") or 0) + 1
            changed = True
        if changed:
            _save_state(state)


def reconcile() -> Dict[str, Any]:
    with _LOCK:
        state = _load_state()
    report: Dict[str, Any] = {"success": True, "ok": True, "tournaments": {}}
    for tid, t in state.items():
        if not isinstance(t, dict):
            continue
        currency = t.get("currency") or "coins"
        total_in = float(t.get("house_seed") or 0) + float(t.get("buyins_collected") or 0)
        paid = float(t.get("paid_out") or 0)
        leftover = total_in - paid
        tol = 1.0 if currency == "coins" else 1e-6
        ok = leftover >= -tol and (t.get("status") != "running" or abs(leftover - float(t.get("pool") or 0)) <= tol)
        report["tournaments"][tid] = {
            "total_in": round(total_in, 8),
            "paid_out": round(paid, 8),
            "leftover": round(leftover, 8),
            "ok": ok,
        }
        if not ok:
            report["ok"] = False
    return report


def verify_fairness(tournament_id: str) -> Dict[str, Any]:
    """Verify committed hash and optional seed chain for a tournament cup."""
    with _LOCK:
        state = _load_state()
        t = state.get(tournament_id)
        if not isinstance(t, dict):
            return {"success": False, "error": "Tournament not found"}
        fair = dict(t.get("fairness_revealed") or t.get("fairness") or {})
    seed = fair.get("server_seed")
    committed = fair.get("server_seed_hash")
    if not committed:
        return {"success": False, "error": "No fairness commitment on tournament"}
    if not seed:
        return {
            "success": True,
            "revealed": False,
            "committed_hash": committed,
            "client_seed": fair.get("client_seed"),
            "chain": fair.get("chain"),
            "status": t.get("status"),
        }
    hash_ok = hashlib.sha256(str(seed).encode("utf-8")).hexdigest() == committed
    chain_ok = True
    chain_detail: Dict[str, Any] = {}
    chain = fair.get("chain") or {}
    if chain.get("prev_tournament_id") and not chain.get("genesis"):
        prev_tid = chain.get("prev_tournament_id")
        prev = state.get(prev_tid) if isinstance(state, dict) else None
        if isinstance(prev, dict):
            prev_fair = prev.get("fairness_revealed") or prev.get("fairness") or {}
            prev_seed = prev_fair.get("server_seed")
            if prev_seed:
                expected = hashlib.sha256(
                    f"{prev_seed}|{t.get('template_id') or 'cup'}|chain-v1".encode("utf-8")
                ).hexdigest()
                chain_ok = str(seed) == expected
                chain_detail = {
                    "prev_tournament_id": prev_tid,
                    "expected_seed": expected,
                    "prev_seed_hash": chain.get("prev_seed_hash"),
                }
            else:
                chain_ok = False
                chain_detail = {"error": "Previous cup seed not yet revealed"}
        else:
            chain_ok = False
            chain_detail = {"error": "Previous cup not found"}
    return {
        "success": hash_ok and chain_ok,
        "revealed": True,
        "hash_ok": hash_ok,
        "chain_ok": chain_ok,
        "server_seed_hash": committed,
        "client_seed": fair.get("client_seed"),
        "chain": chain,
        "chain_detail": chain_detail,
        "status": t.get("status"),
    }
