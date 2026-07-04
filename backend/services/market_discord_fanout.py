"""Off-request fan-out: market channel activity_events → Discord #market (Gate S)."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EVENTS = os.path.join(_BASE, "logs", "activity_events.jsonl")
_CURSOR = os.path.join(_BASE, "logs", "market_discord_cursor.json")

_MARKET_EVENT_TYPES = frozenset({
    "p2p_market_fill",
    "p2p_market_order",
    "trader_market_tick",
    "exchange_rental_start",
    "casino_mn2_big_win",
    "bridge_cross_highlight",
})


def _min_mn2() -> float:
    try:
        return float(os.environ.get("MARKET_DISCORD_MIN_MN2", "5"))
    except (TypeError, ValueError):
        return 5.0


def _load_cursor() -> int:
    if not os.path.isfile(_CURSOR):
        return 0
    try:
        with open(_CURSOR, "r", encoding="utf-8") as f:
            return int(json.load(f).get("line") or 0)
    except Exception:
        return 0


def _save_cursor(line: int) -> None:
    os.makedirs(os.path.dirname(_CURSOR), exist_ok=True)
    with _LOCK:
        tmp = _CURSOR + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"line": line}, f)
        os.replace(tmp, _CURSOR)


def _read_new_events() -> tuple[List[Dict[str, Any]], int]:
    if not os.path.isfile(_EVENTS):
        return [], _load_cursor()
    start = _load_cursor()
    rows: List[Dict[str, Any]] = []
    line_no = 0
    with open(_EVENTS, "r", encoding="utf-8") as f:
        for line in f:
            line_no += 1
            if line_no <= start:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("channel") != "market":
                continue
            et = row.get("type") or ""
            if et not in _MARKET_EVENT_TYPES:
                continue
            rows.append(row)
    return rows, line_no


def _embed_for_event(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    base_url = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    market_url = f"{base_url}/explorer?tab=market"
    et = row.get("type") or ""
    payload = row.get("payload") or {}
    min_mn2 = _min_mn2()

    if et == "p2p_market_fill":
        mn2 = float(payload.get("mn2") or 0)
        if mn2 < min_mn2:
            return None
        coins = payload.get("coins")
        buyer = payload.get("buyer") or "buyer"
        seller = payload.get("seller") or "seller"
        if str(buyer).startswith("trader_agent_"):
            buyer = buyer.replace("_", " ")
        if str(seller).startswith("trader_agent_"):
            seller = seller.replace("_", " ")
        return {
            "embeds": [{
                "title": "Market fill",
                "description": (
                    f"**{mn2:.4f} MN2** @ **{coins} coins** total\n"
                    f"{seller} → {buyer}\n\n"
                    f"[Open order book]({market_url})\n\n"
                    "_Custodial in-app market — not financial advice._"
                ),
                "color": 0x00FF88,
            }],
        }

    if et == "trader_market_tick":
        trades = int(payload.get("trades") or 0)
        if trades <= 0:
            return None
        agents = payload.get("agents") or 6
        return {
            "embeds": [{
                "title": "Trader fleet tick",
                "description": (
                    f"**{trades}** cross-trade(s) across **{agents}** trader agents.\n\n"
                    f"[Market tab]({market_url})\n\n"
                    "_Liquidity bot activity — rewards stay on-site._"
                ),
                "color": 0x5865F2,
            }],
        }

    if et == "p2p_market_order":
        side = payload.get("side") or "order"
        mn2 = float(payload.get("mn2_amount") or payload.get("remaining_mn2") or 0)
        if side != "sell" or mn2 < min_mn2:
            return None
        price = payload.get("price_coins_per_mn2")
        uid = payload.get("user_id") or "trader"
        if str(uid).startswith("trader_agent_"):
            uid = uid.replace("_", " ")
        return {
            "embeds": [{
                "title": "New sell listing",
                "description": (
                    f"**{uid}** listed **{mn2:.4f} MN2** @ **{price} coins/MN2**\n\n"
                    f"[Trade on market]({market_url})"
                ),
                "color": 0xFEE75C,
            }],
        }

    if et == "exchange_rental_start":
        name = payload.get("name") or "Exchange bot"
        days = payload.get("days") or 7
        price = float(payload.get("price_mn2") or 0)
        return {
            "embeds": [{
                "title": "🤖 New exchange rental",
                "description": (
                    f"**{name}** — **{days} days** @ **{price:.0f} MN2**\n\n"
                    f"[Rent your bot]({base_url}/exchange#cex-control-center)\n\n"
                    "_Paper trading — try before you buy._"
                ),
                "color": 0x7C3AED,
            }],
        }

    if et == "casino_mn2_big_win":
        net = float(payload.get("net") or 0)
        game = payload.get("game") or "casino"
        return {
            "embeds": [{
                "title": "🎰 MN2 casino win",
                "description": (
                    f"**{net:.4f} MN2** net on **{game}**\n\n"
                    f"[Play MN2 tables]({base_url}/casino/)\n\n"
                    "_Shared MN2 wallet with exchange rentals._"
                ),
                "color": 0xF59E0B,
            }],
        }

    if et == "bridge_cross_highlight":
        return {
            "embeds": [{
                "title": payload.get("title") or "Bridge highlight",
                "description": payload.get("description") or "",
                "color": 0xA855F7,
            }],
        }

    return None


def _embed_bridge_combined(rental: Dict[str, Any], win: Dict[str, Any]) -> Dict[str, Any]:
    base_url = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    exchange_url = f"{base_url}/exchange#cex-control-center"
    casino_url = f"{base_url}/casino/"
    rp = rental.get("payload") or {}
    wp = win.get("payload") or {}
    lines = [
        f"🤖 **{rp.get('name') or 'Exchange rental'}** — {rp.get('days', '?')}d @ {float(rp.get('price_mn2') or 0):.0f} MN2",
        f"🎰 **MN2 win** — {float(wp.get('net') or 0):.4f} MN2 on **{wp.get('game') or 'casino'}**",
        "",
        f"[Agent control]({exchange_url}) · [Casino]({casino_url})",
        "_Exchange ↔ Casino bridge — paper profit + MN2 play._",
    ]
    return {"embeds": [{"title": "Trader + High roller pulse", "description": "\n".join(lines), "color": 0xA855F7}]}


def run_fanout(*, dry_run: bool = False) -> Dict[str, Any]:
    """Process new market channel activity events → Discord #market."""
    rows, end_line = _read_new_events()
    posted: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []

    from backend.services.discord_service import post_message

    rental_row = next((r for r in rows if r.get("type") == "exchange_rental_start"), None)
    win_row = next((r for r in rows if r.get("type") == "casino_mn2_big_win"), None)
    combined_ref = None
    if rental_row and win_row and not dry_run:
        combined = _embed_bridge_combined(rental_row, win_row)
        combined_ref = f"bridge-combined:{rental_row.get('ts')}:{win_row.get('ts')}"
        result = post_message("market", combined, message_id=combined_ref)
        if result.get("success"):
            posted.append(combined_ref)

    for row in rows:
        et = row.get("type") or "event"
        ts = row.get("ts") or ""
        if rental_row and win_row and et in ("exchange_rental_start", "casino_mn2_big_win"):
            skipped.append(et)
            continue
        bet_id = (row.get("payload") or {}).get("order_id") or (row.get("payload") or {}).get("ref")
        msg_id = f"market-fanout:{et}:{bet_id or ts}"
        embed = _embed_for_event(row)
        if embed is None:
            skipped.append(et)
            continue
        if dry_run:
            posted.append(f"dry:{msg_id}")
            continue
        result = post_message("market", embed, message_id=msg_id)
        if result.get("success"):
            posted.append(msg_id)
        else:
            errors.append(result.get("error") or "post_failed")

    if not dry_run:
        _save_cursor(end_line)

    return {
        "success": True,
        "processed": len(rows),
        "posted": len(posted),
        "skipped": len(skipped),
        "errors": errors,
        "cursor_line": end_line,
    }
