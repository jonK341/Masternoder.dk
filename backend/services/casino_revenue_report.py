"""
Daily casino revenue rollup — house edge, jackpots, tournaments, rewards, big wins.

Sources:
- `logs/casino_ledger.db` — stakes / payouts / big-win counts
- `logs/casino_jackpot_ledger.jsonl` — contributions & awards
- `logs/casino_tournament_ledger.jsonl` — buy-ins & prize payouts
- `logs/casino_quest_claims.json` + quest config — reward coin grants (quests/bonuses)

Three currency rails only: coins, mn2, usd — never mn2_staked.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RAILS = ("coins", "mn2", "usd")


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _big_win_thresholds() -> Dict[str, float]:
    from backend.services.casino_social_service import _BIG_WIN_THRESHOLDS
    return dict(_BIG_WIN_THRESHOLDS)


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        pass
    return rows


def _quest_reward_map() -> Dict[str, int]:
    path = os.path.join(_ROOT, "data", "casino_config.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    rewards: Dict[str, int] = {}
    for q in (cfg.get("daily_quests") or []):
        if isinstance(q, dict) and q.get("id"):
            rewards[str(q["id"])] = int(q.get("reward_coins") or 0)
    for block in (cfg.get("rotating_daily_quests") or []):
        if not isinstance(block, dict):
            continue
        for q in (block.get("quests") or []):
            if isinstance(q, dict) and q.get("id"):
                rewards[str(q["id"])] = int(q.get("reward_coins") or 0)
    streak = cfg.get("quest_streak") if isinstance(cfg.get("quest_streak"), dict) else {}
    if streak.get("streak_3_day_bonus"):
        rewards["bonus_streak_3"] = int(streak.get("streak_3_day_bonus") or 0)
    if streak.get("daily_all_claimed_bonus"):
        rewards["bonus_all_daily"] = int(streak.get("daily_all_claimed_bonus") or 0)
    wc = cfg.get("weekly_challenge") if isinstance(cfg.get("weekly_challenge"), dict) else {}
    if wc.get("id"):
        rewards[str(wc["id"])] = int(wc.get("reward_coins") or 0)
    for lvl in ((cfg.get("progression") or {}).get("levels") or []):
        if isinstance(lvl, dict) and lvl.get("level"):
            rewards[f"level_{lvl['level']}"] = int(lvl.get("reward_coins") or 0)
    return rewards


def _reward_deductions_for_day(day: str) -> Dict[str, Any]:
    """Estimate coin grants from quest claims on a calendar day."""
    path = os.path.join(_log_dir(), "casino_quest_claims.json")
    reward_map = _quest_reward_map()
    total = 0
    claims = 0
    if not os.path.isfile(path):
        return {"reward_deductions_coins": 0, "quest_claims": 0}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {"reward_deductions_coins": 0, "quest_claims": 0}
    if not isinstance(data, dict):
        return {"reward_deductions_coins": 0, "quest_claims": 0}
    for _user, user_map in data.items():
        if not isinstance(user_map, dict):
            continue
        day_claims = user_map.get(day)
        if isinstance(day_claims, list):
            for qid in day_claims:
                claims += 1
                total += int(reward_map.get(str(qid), 0))
        bonus_day = ((user_map.get("_bonus") or {}).get(day)) or []
        if isinstance(bonus_day, list):
            for bid in bonus_day:
                claims += 1
                key = str(bid).replace("bonus_", "bonus_") if str(bid).startswith("bonus_") else f"bonus_{bid}"
                total += int(reward_map.get(key, reward_map.get(str(bid), 0)))
    return {"reward_deductions_coins": total, "quest_claims": claims}


def _ledger_day_stats(day: str) -> Dict[str, Dict[str, Any]]:
    """Per-rail bet stats for one UTC calendar day."""
    empty = {c: {
        "stakes": 0.0, "payouts": 0.0, "house_edge_profit": 0.0,
        "bets": 0, "wins": 0, "losses": 0, "equals": 0,
        "big_win_count": 0, "big_win_total": 0.0,
        "player_wins_net": 0.0, "player_losses_net": 0.0,
    } for c in _RAILS}
    db_path = os.path.join(_log_dir(), "casino_ledger.db")
    thresholds = _big_win_thresholds()
    if not os.path.isfile(db_path):
        return empty
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT currency, bet, payout, net, outcome
            FROM casino_bets
            WHERE substr(created_at, 1, 10) = ?
            """,
            (day,),
        )
        for row in cur.fetchall():
            c = str(row["currency"] or "coins").lower()
            if c not in empty:
                continue
            bet = float(row["bet"] or 0)
            payout = float(row["payout"] or 0)
            net = float(row["net"] or 0)
            bucket = empty[c]
            bucket["stakes"] += bet
            bucket["payouts"] += payout
            bucket["bets"] += 1
            outcome = str(row["outcome"] or "")
            if outcome == "win":
                bucket["wins"] += 1
            elif outcome == "loss":
                bucket["losses"] += 1
            else:
                bucket["equals"] += 1
            if net > 0:
                bucket["player_wins_net"] += net
            elif net < 0:
                bucket["player_losses_net"] += abs(net)
            thresh = thresholds.get(c, float("inf"))
            if net >= thresh:
                bucket["big_win_count"] += 1
                bucket["big_win_total"] += net
        conn.close()
    except Exception:
        pass
    for c in _RAILS:
        b = empty[c]
        b["house_edge_profit"] = round(b["stakes"] - b["payouts"], 8 if c == "mn2" else 2)
        b["stakes"] = round(b["stakes"], 8 if c == "mn2" else 2)
        b["payouts"] = round(b["payouts"], 8 if c == "mn2" else 2)
        b["player_wins_net"] = round(b["player_wins_net"], 8 if c == "mn2" else 2)
        b["player_losses_net"] = round(b["player_losses_net"], 8 if c == "mn2" else 2)
        b["big_win_total"] = round(b["big_win_total"], 8 if c == "mn2" else 2)
    return empty


def _jackpot_day_stats(day: str) -> Dict[str, Any]:
    path = os.path.join(_log_dir(), "casino_jackpot_ledger.jsonl")
    contributions = 0.0
    awards = 0.0
    contrib_count = 0
    award_count = 0
    by_currency: Dict[str, Dict[str, float]] = {c: {"contributions": 0.0, "awards": 0.0} for c in _RAILS}
    for row in _read_jsonl(path):
        ts = str(row.get("created_at") or row.get("ts") or "")
        if not ts.startswith(day):
            continue
        kind = str(row.get("type") or row.get("event") or "")
        amount = float(row.get("amount") or 0)
        c = str(row.get("currency") or "coins").lower()
        if c not in by_currency:
            continue
        if kind in ("contribution", "contrib"):
            contributions += amount
            contrib_count += 1
            by_currency[c]["contributions"] += amount
        elif kind in ("award", "payout", "win"):
            awards += amount
            award_count += 1
            by_currency[c]["awards"] += amount
    return {
        "jackpot_contributions": round(contributions, 4),
        "jackpot_awards": round(awards, 4),
        "jackpot_contrib_events": contrib_count,
        "jackpot_award_events": award_count,
        "by_currency": by_currency,
    }


def _tournament_day_stats(day: str) -> Dict[str, Any]:
    path = os.path.join(_log_dir(), "casino_tournament_ledger.jsonl")
    buyins = 0.0
    payouts = 0.0
    buyin_count = 0
    payout_count = 0
    for row in _read_jsonl(path):
        ts = str(row.get("created_at") or row.get("ts") or "")
        if not ts.startswith(day):
            continue
        kind = str(row.get("type") or row.get("event") or "")
        amount = float(row.get("amount") or 0)
        if kind in ("buyin", "buy_in", "entry"):
            buyins += amount
            buyin_count += 1
        elif kind in ("payout", "prize", "award"):
            payouts += amount
            payout_count += 1
    return {
        "tournament_buyins": round(buyins, 4),
        "tournament_payouts": round(payouts, 4),
        "tournament_buyin_events": buyin_count,
        "tournament_payout_events": payout_count,
    }


def daily_report(day: Optional[str] = None) -> Dict[str, Any]:
    day = (day or _utc_today()).strip()[:10]
    rails = _ledger_day_stats(day)
    rewards = _reward_deductions_for_day(day)
    jackpots = _jackpot_day_stats(day)
    tournaments = _tournament_day_stats(day)

    summary_plus = sum(r["player_wins_net"] for r in rails.values())
    summary_minus = sum(r["player_losses_net"] for r in rails.values())
    summary_equals = sum(r["equals"] for r in rails.values())
    house_total = sum(r["house_edge_profit"] for r in rails.values())

    return {
        "success": True,
        "day": day,
        "by_currency": rails,
        "house_edge_profit_total": round(house_total, 4),
        "player_plusses": round(summary_plus, 4),
        "player_minuses": round(summary_minus, 4),
        "push_equals": summary_equals,
        "big_win_count": sum(r["big_win_count"] for r in rails.values()),
        "big_win_total": round(sum(r["big_win_total"] for r in rails.values()), 4),
        "reward_deductions": rewards,
        "jackpots": jackpots,
        "tournaments": tournaments,
        "net_house_after_rewards": round(
            house_total - float(rewards.get("reward_deductions_coins") or 0), 4
        ),
    }


def daily_reports(days: int = 7) -> Dict[str, Any]:
    safe_days = max(1, min(int(days or 7), 30))
    now = datetime.now(timezone.utc)
    reports = []
    for offset in range(safe_days - 1, -1, -1):
        day = (now - timedelta(days=offset)).strftime("%Y-%m-%d")
        reports.append(daily_report(day))
    return {"success": True, "days": safe_days, "reports": reports}


def today_summary() -> Dict[str, Any]:
    report = daily_report(_utc_today())
    report["summary"] = {
        "headline": f"House edge {report['house_edge_profit_total']} (all rails, stakes−payouts)",
        "big_wins": report["big_win_count"],
        "reward_coins_granted": (report.get("reward_deductions") or {}).get("reward_deductions_coins", 0),
        "jackpot_awards": (report.get("jackpots") or {}).get("jackpot_awards", 0),
        "tournament_payouts": (report.get("tournaments") or {}).get("tournament_payouts", 0),
    }
    return report
