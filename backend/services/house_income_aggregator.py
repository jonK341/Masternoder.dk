"""
House income aggregation — casino house edge, rake, deposits, exchange→casino cashflow.

Rails (coins / mn2 / usd) stay separate. Virtual coins are never folded into USD P&L.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


def _root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_root(), "logs")


def _casino_db() -> str:
    return os.path.join(_log_dir(), "casino_ledger.db")


def _cashflow_path() -> str:
    return os.path.join(_log_dir(), "casino_cashflow.jsonl")


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _since_cutoff(since_hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=since_hours)


def _empty_rail() -> Dict[str, float]:
    return {
        "total_bet": 0.0,
        "total_payout": 0.0,
        "house_edge": 0.0,
        "bets": 0,
        "rake": 0.0,
        "rebates": 0.0,
    }


def _arena_state() -> Dict[str, Any]:
    path = os.path.join(_root(), "data", "arena_state.json")
    if not os.path.isfile(path):
        return {"events": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"events": {}}
    except Exception:
        return {"events": {}}


def append_cashflow_event(event: Dict[str, Any]) -> None:
    """Best-effort durable cashflow event (MN2 buy-in, etc.)."""
    if not isinstance(event, dict):
        return
    row = dict(event)
    row.setdefault("at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    try:
        os.makedirs(_log_dir(), exist_ok=True)
        with open(_cashflow_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _summarize_casino_sqlite(since_iso: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    by_currency: Dict[str, Dict[str, Any]] = {}
    by_game: Dict[str, Dict[str, Dict[str, Any]]] = {}
    db_path = _casino_db()
    if not os.path.isfile(db_path):
        return by_currency, by_game
    try:
        conn = sqlite3.connect(db_path, timeout=3.0)
        conn.row_factory = sqlite3.Row
        try:
            agg = conn.execute(
                """
                SELECT currency, game,
                       SUM(bet) AS total_bet,
                       SUM(payout) AS total_payout,
                       COUNT(*) AS bets
                FROM casino_bets
                WHERE created_at >= ?
                GROUP BY currency, game
                """,
                (since_iso,),
            )
            for row in agg.fetchall():
                c = str(row["currency"] or "coins").lower()
                g = str(row["game"] or "unknown")
                total_bet = float(row["total_bet"] or 0)
                total_payout = float(row["total_payout"] or 0)
                house = round(total_bet - total_payout, 8)
                bets = int(row["bets"] or 0)
                rail = by_currency.setdefault(c, _empty_rail())
                rail["total_bet"] = round(rail["total_bet"] + total_bet, 8)
                rail["total_payout"] = round(rail["total_payout"] + total_payout, 8)
                rail["house_edge"] = round(rail["house_edge"] + house, 8)
                rail["bets"] = int(rail["bets"] + bets)
                slot = by_game.setdefault(g, {}).setdefault(c, _empty_rail())
                slot["total_bet"] = round(slot["total_bet"] + total_bet, 8)
                slot["total_payout"] = round(slot["total_payout"] + total_payout, 8)
                slot["house_edge"] = round(slot["house_edge"] + house, 8)
                slot["bets"] = int(slot["bets"] + bets)

            detail_cur = conn.execute(
                """
                SELECT currency, game, details
                FROM casino_bets
                WHERE created_at >= ?
                """,
                (since_iso,),
            )
            for row in detail_cur.fetchall():
                c = str(row["currency"] or "coins").lower()
                g = str(row["game"] or "unknown")
                try:
                    details = json.loads(row["details"] or "{}")
                except Exception:
                    details = {}
                if not isinstance(details, dict):
                    continue
                rake = float(details.get("rake") or details.get("rake_amount") or 0)
                rebate = float(details.get("rebate") or details.get("trophy_rebate") or 0)
                if rake:
                    by_currency.setdefault(c, _empty_rail())["rake"] = round(
                        by_currency[c]["rake"] + rake, 8
                    )
                    by_game.setdefault(g, {}).setdefault(c, _empty_rail())["rake"] = round(
                        by_game[g][c]["rake"] + rake, 8
                    )
                if rebate:
                    by_currency.setdefault(c, _empty_rail())["rebates"] = round(
                        by_currency[c]["rebates"] + rebate, 8
                    )
                    by_game.setdefault(g, {}).setdefault(c, _empty_rail())["rebates"] = round(
                        by_game[g][c]["rebates"] + rebate, 8
                    )
        finally:
            conn.close()
    except Exception:
        return by_currency, by_game
    return by_currency, by_game


def _summarize_casino_jsonl(cutoff: datetime) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Fallback when SQLite mirror is empty/missing."""
    by_currency: Dict[str, Dict[str, Any]] = {}
    by_game: Dict[str, Dict[str, Any]] = {}
    path = os.path.join(_log_dir(), "casino_bets.jsonl")
    if not os.path.isfile(path):
        return by_currency, by_game
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                ts = _parse_ts(row.get("created_at") or row.get("at") or row.get("ts"))
                if ts is None or ts < cutoff:
                    continue
                c = str(row.get("currency") or "coins").lower()
                g = str(row.get("game") or "unknown")
                bet = float(row.get("bet") or 0)
                payout = float(row.get("payout") or 0)
                house = round(bet - payout, 8)
                rail = by_currency.setdefault(c, _empty_rail())
                rail["total_bet"] = round(rail["total_bet"] + bet, 8)
                rail["total_payout"] = round(rail["total_payout"] + payout, 8)
                rail["house_edge"] = round(rail["house_edge"] + house, 8)
                rail["bets"] = int(rail["bets"] + 1)
                slot = by_game.setdefault(g, {}).setdefault(c, _empty_rail())
                slot["total_bet"] = round(slot["total_bet"] + bet, 8)
                slot["total_payout"] = round(slot["total_payout"] + payout, 8)
                slot["house_edge"] = round(slot["house_edge"] + house, 8)
                slot["bets"] = int(slot["bets"] + 1)
                details = row.get("details") if isinstance(row.get("details"), dict) else {}
                rake = float(details.get("rake") or details.get("rake_amount") or 0)
                rebate = float(details.get("rebate") or details.get("trophy_rebate") or 0)
                if rake:
                    rail["rake"] = round(rail["rake"] + rake, 8)
                    slot["rake"] = round(slot["rake"] + rake, 8)
                if rebate:
                    rail["rebates"] = round(rail["rebates"] + rebate, 8)
                    slot["rebates"] = round(slot["rebates"] + rebate, 8)
    except OSError:
        pass
    return by_currency, by_game


def _paypal_deposits(cutoff: datetime) -> Dict[str, Any]:
    path = os.path.join(_log_dir(), "casino_paypal_deposits.json")
    count = 0
    usd = 0.0
    bonus_usd = 0.0
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for row in (data.get("captured") or {}).values():
                if not isinstance(row, dict):
                    continue
                ts = _parse_ts(row.get("captured_at") or row.get("created_at") or row.get("at"))
                if ts is None or ts < cutoff:
                    continue
                count += 1
                usd += float(row.get("amount_usd") or 0)
                bonus_usd += float(row.get("bonus_usd") or 0)
        except Exception:
            pass
    return {
        "count": count,
        "amount_usd": round(usd, 2),
        "bonus_usd": round(bonus_usd, 2),
    }


def _mn2_buyins(cutoff: datetime) -> Dict[str, Any]:
    count = 0
    price_mn2 = 0.0
    credit_usd = 0.0
    path = _cashflow_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    if str(row.get("type") or "") != "mn2_buyin":
                        continue
                    ts = _parse_ts(row.get("at") or row.get("created_at") or row.get("ts"))
                    if ts is None or ts < cutoff:
                        continue
                    count += 1
                    price_mn2 += float(row.get("price_mn2") or 0)
                    credit_usd += float(row.get("casino_usd_credit") or row.get("casino_usd_credited") or 0)
        except OSError:
            pass
    return {
        "count": count,
        "price_mn2": round(price_mn2, 8),
        "casino_usd_credit": round(credit_usd, 2),
    }


def _exchange_to_casino(cutoff: datetime) -> Dict[str, Any]:
    path = os.path.join(_root(), "data", "crypto_exchange", "audit_log.jsonl")
    count = 0
    amount_usd = 0.0
    casino_coins = 0
    if not os.path.isfile(path):
        return {"count": 0, "amount_usd": 0.0, "casino_coins": 0}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                if str(row.get("action") or "") != "exchange_profit_cashout":
                    continue
                data = row.get("data") if isinstance(row.get("data"), dict) else {}
                dest = str(data.get("destination") or "").lower()
                if dest != "casino_coins":
                    continue
                ts = _parse_ts(row.get("ts") or row.get("at"))
                if ts is None or ts < cutoff:
                    continue
                usd = float(row.get("amount_usd") or 0)
                count += 1
                amount_usd += usd
                casino_coins += int(round(usd * 100))
    except OSError:
        pass
    return {
        "count": count,
        "amount_usd": round(amount_usd, 2),
        "casino_coins": casino_coins,
    }


def _arena_house(cutoff: datetime) -> Dict[str, float]:
    arena_house: Dict[str, float] = {}
    state = _arena_state()
    for ev in (state.get("events") or {}).values():
        if not isinstance(ev, dict):
            continue
        ts = _parse_ts(ev.get("at") or ev.get("created_at") or ev.get("ts") or ev.get("settled_at"))
        if ts is not None and ts < cutoff:
            continue
        # If no timestamp, include (legacy rows) — still better than ignoring all filters
        c = str(ev.get("currency") or "coins").lower()
        ht = float(ev.get("house_take") or 0)
        arena_house[c] = round(arena_house.get(c, 0) + ht, 8)
    return arena_house


def summarize(since_hours: int = 24, venue: str = "all") -> Dict[str, Any]:
    since_hours = max(1, min(int(since_hours or 24), 24 * 30))
    cutoff = _since_cutoff(since_hours)
    since_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
    venue = (venue or "all").strip().lower()
    if venue not in ("all", "casino", "arena"):
        venue = "all"

    casino_by_currency: Dict[str, Dict[str, Any]] = {}
    by_game: Dict[str, Dict[str, Any]] = {}
    if venue in ("all", "casino"):
        casino_by_currency, by_game = _summarize_casino_sqlite(since_iso)
        if not casino_by_currency:
            casino_by_currency, by_game = _summarize_casino_jsonl(cutoff)

    arena_house: Dict[str, float] = {}
    if venue in ("all", "arena"):
        arena_house = _arena_house(cutoff)

    total_house: Dict[str, float] = {}
    if venue in ("all", "casino"):
        for c, v in casino_by_currency.items():
            total_house[c] = round(
                float(v.get("house_edge", 0)) + (arena_house.get(c, 0) if venue == "all" else 0),
                8,
            )
    if venue in ("all", "arena"):
        for c, v in arena_house.items():
            if venue == "arena":
                total_house[c] = round(v, 8)
            elif c not in total_house:
                total_house[c] = round(v, 8)

    paypal = _paypal_deposits(cutoff) if venue in ("all", "casino") else {"count": 0, "amount_usd": 0.0, "bonus_usd": 0.0}
    mn2_buyins = _mn2_buyins(cutoff) if venue in ("all", "casino") else {"count": 0, "price_mn2": 0.0, "casino_usd_credit": 0.0}
    exchange_bridge = _exchange_to_casino(cutoff) if venue in ("all", "casino") else {
        "count": 0, "amount_usd": 0.0, "casino_coins": 0,
    }

    usd_rail = casino_by_currency.get("usd") or _empty_rail()
    financial = {
        "house_edge_usd": round(float(usd_rail.get("house_edge") or 0), 2),
        "rake_usd": round(float(usd_rail.get("rake") or 0), 2),
        "rebates_usd": round(float(usd_rail.get("rebates") or 0), 2),
        "paypal_deposits_usd": paypal.get("amount_usd") or 0.0,
        "mn2_buyin_credit_usd": mn2_buyins.get("casino_usd_credit") or 0.0,
        "exchange_cashout_usd": exchange_bridge.get("amount_usd") or 0.0,
        "note": "USD-only financial slice. Coins and MN2 stay on their rails.",
    }
    financial["net_ops_usd"] = round(
        float(financial["house_edge_usd"])
        + float(financial["rake_usd"])
        - float(financial["rebates_usd"])
        + float(financial["paypal_deposits_usd"]),
        2,
    )

    return {
        "success": True,
        "since_hours": since_hours,
        "since_iso": since_iso,
        "venue": venue,
        "casino": casino_by_currency if venue in ("all", "casino") else {},
        "by_game": by_game if venue in ("all", "casino") else {},
        "arena_house_take": arena_house if venue in ("all", "arena") else {},
        "combined_house": total_house,
        "cashflow": {
            "paypal_deposits": paypal,
            "mn2_buyins": mn2_buyins,
            "exchange_to_casino": exchange_bridge,
        },
        "financial_usd": financial,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
