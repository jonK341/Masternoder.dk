#!/usr/bin/env python3
"""Generate SQL-backed trading reports optimized for content creation."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(ROOT, "instance", "database.db")
DEFAULT_OUTDIR = os.path.join(ROOT, "reports", "trading_content")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def _fetch_all(cur: sqlite3.Cursor, sql: str, params: Iterable[Any] = ()) -> List[sqlite3.Row]:
    cur.execute(sql, tuple(params))
    return cur.fetchall()


def _fetch_one(cur: sqlite3.Cursor, sql: str, params: Iterable[Any] = ()) -> sqlite3.Row:
    cur.execute(sql, tuple(params))
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("Expected one row from query.")
    return row


def collect_metrics(db_path: str, hours: int, top_n: int) -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    record_bounds = _fetch_one(
        cur,
        "SELECT MIN(ts) AS min_ts, MAX(ts) AS max_ts, COUNT(*) AS cnt FROM trading_records",
    )
    log_bounds = _fetch_one(
        cur,
        "SELECT MIN(ts) AS min_ts, MAX(ts) AS max_ts, COUNT(*) AS cnt FROM trading_logs",
    )

    latest_ts = _parse_iso_utc(record_bounds["max_ts"]) or _now_utc()
    window_start = latest_ts - timedelta(hours=hours)
    window_start_iso = window_start.isoformat().replace("+00:00", "Z")

    totals = _fetch_one(
        cur,
        """
        SELECT
          COUNT(*) AS trade_count,
          COALESCE(SUM(notional_usd), 0) AS notional_usd,
          COALESCE(SUM(fee_usd), 0) AS fee_usd,
          COALESCE(SUM(pnl_usd), 0) AS pnl_usd
        FROM trading_records
        """,
    )
    window = _fetch_one(
        cur,
        """
        SELECT
          COUNT(*) AS trade_count,
          COALESCE(SUM(notional_usd), 0) AS notional_usd,
          COALESCE(SUM(fee_usd), 0) AS fee_usd,
          COALESCE(SUM(pnl_usd), 0) AS pnl_usd
        FROM trading_records
        WHERE ts >= ?
        """,
        (window_start_iso,),
    )

    top_symbols = _fetch_all(
        cur,
        """
        SELECT symbol, COUNT(*) AS trades, COALESCE(SUM(notional_usd), 0) AS notional_usd
        FROM trading_records
        WHERE ts >= ?
        GROUP BY symbol
        ORDER BY trades DESC, notional_usd DESC
        LIMIT ?
        """,
        (window_start_iso, top_n),
    )
    top_users = _fetch_all(
        cur,
        """
        SELECT user_id, COUNT(*) AS trades, COALESCE(SUM(notional_usd), 0) AS notional_usd
        FROM trading_records
        WHERE ts >= ?
        GROUP BY user_id
        ORDER BY trades DESC, notional_usd DESC
        LIMIT ?
        """,
        (window_start_iso, top_n),
    )
    top_events = _fetch_all(
        cur,
        """
        SELECT event_type, COUNT(*) AS event_count
        FROM trading_logs
        WHERE ts >= ?
        GROUP BY event_type
        ORDER BY event_count DESC
        LIMIT ?
        """,
        (window_start_iso, top_n),
    )
    top_levels = _fetch_all(
        cur,
        """
        SELECT level, COUNT(*) AS event_count
        FROM trading_logs
        WHERE ts >= ?
        GROUP BY level
        ORDER BY event_count DESC
        """,
        (window_start_iso,),
    )
    daily = _fetch_all(
        cur,
        """
        SELECT DATE(ts) AS day, COUNT(*) AS trades, COALESCE(SUM(notional_usd), 0) AS notional_usd
        FROM trading_records
        GROUP BY DATE(ts)
        ORDER BY day DESC
        LIMIT 7
        """,
    )

    recent_trades = _fetch_all(
        cur,
        """
        SELECT ts, trade_id, user_id, symbol, side, notional_usd, fee_usd
        FROM trading_records
        ORDER BY ts DESC
        LIMIT ?
        """,
        (top_n,),
    )

    conn.close()

    symbol_counter = Counter()
    for row in top_symbols:
        symbol_counter[row["symbol"]] = int(row["trades"])

    warnings: List[str] = []
    info: List[str] = []
    if int(window["trade_count"]) == 0:
        warnings.append(f"No trades detected in the latest {hours}h window.")
    if int(log_bounds["cnt"] or 0) == 0:
        warnings.append("No trading logs found in `trading_logs`; content quality may be limited.")

    error_count = 0
    warning_count = 0
    for row in top_levels:
        level = str(row["level"] or "").lower()
        if level == "error":
            error_count = int(row["event_count"])
        if level == "warning":
            warning_count = int(row["event_count"])
    if error_count > 0:
        warnings.append(f"{error_count} error-level trading log events in the selected window.")
    elif warning_count > 0:
        info.append(f"{warning_count} warning-level trading log events in the selected window.")
    else:
        info.append("No warning/error-level log spikes detected in the selected window.")

    return {
        "generated_at": _now_utc().isoformat().replace("+00:00", "Z"),
        "db_path": db_path,
        "window_hours": hours,
        "window_start": window_start_iso,
        "window_end": latest_ts.isoformat().replace("+00:00", "Z"),
        "bounds": {
            "records_min_ts": record_bounds["min_ts"],
            "records_max_ts": record_bounds["max_ts"],
            "records_count": int(record_bounds["cnt"] or 0),
            "logs_min_ts": log_bounds["min_ts"],
            "logs_max_ts": log_bounds["max_ts"],
            "logs_count": int(log_bounds["cnt"] or 0),
        },
        "metrics_all_time": {
            "trade_count": int(totals["trade_count"] or 0),
            "notional_usd": float(totals["notional_usd"] or 0),
            "fee_usd": float(totals["fee_usd"] or 0),
            "pnl_usd": float(totals["pnl_usd"] or 0),
        },
        "metrics_window": {
            "trade_count": int(window["trade_count"] or 0),
            "notional_usd": float(window["notional_usd"] or 0),
            "fee_usd": float(window["fee_usd"] or 0),
            "pnl_usd": float(window["pnl_usd"] or 0),
        },
        "top_symbols_window": [dict(r) for r in top_symbols],
        "top_users_window": [dict(r) for r in top_users],
        "top_events_window": [dict(r) for r in top_events],
        "log_levels_window": [dict(r) for r in top_levels],
        "daily_series_recent": [dict(r) for r in daily],
        "recent_trades": [dict(r) for r in recent_trades],
        "warnings": warnings,
        "info": info,
        "symbol_counter": dict(symbol_counter),
    }


def build_content_pack(data: Dict[str, Any]) -> Dict[str, str]:
    m = data["metrics_window"]
    top_symbol = (data["top_symbols_window"][0]["symbol"] if data["top_symbols_window"] else "N/A")
    top_event = (data["top_events_window"][0]["event_type"] if data["top_events_window"] else "N/A")
    trades = int(m["trade_count"])
    notional = _fmt_money(float(m["notional_usd"]))
    fees = _fmt_money(float(m["fee_usd"]))
    window_label = f"last {data['window_hours']}h"

    key_bullets = [
        f"{trades:,} trades executed in the {window_label}.",
        f"Total traded notional reached {notional}, with estimated fees of {fees}.",
        f"Most active symbol: {top_symbol}.",
        f"Most frequent operational event: {top_event}.",
    ]
    if data["warnings"]:
        key_bullets.append("Risk flag: " + data["warnings"][0])

    x_post = (
        f"Trading update ({window_label}): {trades:,} trades, {notional} notional, "
        f"{fees} fees. Top symbol: {top_symbol}. Top event: {top_event}. "
        "Stack is now SQL-backed for faster reporting and content publishing. #trading #analytics"
    )
    linkedin = (
        f"Trading performance snapshot ({window_label})\n\n"
        f"- Volume: {trades:,} trades / {notional} notional\n"
        f"- Revenue signal: {fees} fees\n"
        f"- Market focus: {top_symbol}\n"
        f"- Ops signal: {top_event}\n\n"
        "We now run the report from structured SQL tables, which makes recurring publishing workflows "
        "faster, cleaner, and easier to verify."
    )
    newsletter = (
        f"In the {window_label}, the trading engine processed {trades:,} trades and "
        f"{notional} in notional volume, generating about {fees} in fees. "
        f"{top_symbol} led symbol activity, while {top_event} dominated the operational log stream. "
        "Reporting now runs directly from SQL records and logs, improving reliability for weekly recaps."
    )
    video_script = (
        "Hook: Here is the latest trading pulse in under 30 seconds.\n"
        f"Body: Over the {window_label}, we recorded {trades:,} trades and {notional} in volume. "
        f"Estimated fee generation came in at {fees}. {top_symbol} was the most active symbol. "
        f"On the operations side, {top_event} was the most frequent event.\n"
        "Close: The data now comes from a SQL reporting layer, so this update can be generated on demand."
    )

    return {
        "key_bullets": "\n".join(f"- {b}" for b in key_bullets),
        "x_post": x_post,
        "linkedin_post": linkedin,
        "newsletter_blurb": newsletter,
        "video_script_30s": video_script,
    }


def to_markdown(data: Dict[str, Any], content: Dict[str, str]) -> str:
    m_all = data["metrics_all_time"]
    m_win = data["metrics_window"]
    lines: List[str] = [
        "# Trading Content Report",
        "",
        f"- Generated at: `{data['generated_at']}`",
        f"- Database: `{data['db_path']}`",
        f"- Window: `{data['window_start']}` -> `{data['window_end']}` ({data['window_hours']}h)",
        "",
        "## Executive Summary",
        content["key_bullets"],
        "",
        "## Core Metrics",
        f"- All-time trades: `{m_all['trade_count']:,}`",
        f"- All-time notional: `{_fmt_money(m_all['notional_usd'])}`",
        f"- All-time fees: `{_fmt_money(m_all['fee_usd'])}`",
        f"- Window trades: `{m_win['trade_count']:,}`",
        f"- Window notional: `{_fmt_money(m_win['notional_usd'])}`",
        f"- Window fees: `{_fmt_money(m_win['fee_usd'])}`",
        "",
        "## Top Symbols (window)",
    ]
    if data["top_symbols_window"]:
        for row in data["top_symbols_window"]:
            lines.append(
                f"- `{row['symbol']}`: {int(row['trades']):,} trades, {_fmt_money(float(row['notional_usd'] or 0))} notional"
            )
    else:
        lines.append("- No symbol activity in selected window.")

    lines.extend(["", "## Top Events (window)"])
    if data["top_events_window"]:
        for row in data["top_events_window"]:
            lines.append(f"- `{row['event_type']}`: {int(row['event_count']):,} events")
    else:
        lines.append("- No events in selected window.")

    if data["warnings"]:
        lines.extend(["", "## Warnings"])
        for warning in data["warnings"]:
            lines.append(f"- {warning}")

    if data["info"]:
        lines.extend(["", "## Notes"])
        for info in data["info"]:
            lines.append(f"- {info}")

    lines.extend(
        [
            "",
            "## Content Pack",
            "",
            "### X Post",
            content["x_post"],
            "",
            "### LinkedIn Post",
            content["linkedin_post"],
            "",
            "### Newsletter Blurb",
            content["newsletter_blurb"],
            "",
            "### 30s Video Script",
            content["video_script_30s"],
            "",
        ]
    )
    return "\n".join(lines)


def save_outputs(output_dir: str, stem: str, markdown: str, json_payload: Dict[str, Any]) -> Tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    md_path = os.path.join(output_dir, f"{stem}.md")
    json_path = os.path.join(output_dir, f"{stem}.json")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown + "\n")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2, ensure_ascii=True)
        f.write("\n")
    return md_path, json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SQL-backed trading report for content creation.")
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to SQLite database file.")
    parser.add_argument("--hours", type=int, default=24, help="Trailing window size in hours.")
    parser.add_argument("--top", type=int, default=8, help="Top N symbols/users/events to include.")
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "both"),
        default="both",
        help="Output format printed to stdout.",
    )
    parser.add_argument("--save", action="store_true", help="Write markdown/json files to reports/trading_content.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTDIR, help="Directory used when --save is set.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.hours <= 0:
        raise SystemExit("--hours must be > 0")
    if args.top <= 0:
        raise SystemExit("--top must be > 0")
    if not os.path.isfile(args.db):
        raise SystemExit(f"Database file not found: {args.db}")

    data = collect_metrics(args.db, args.hours, args.top)
    content = build_content_pack(data)
    payload = {"report": data, "content_pack": content}
    markdown = to_markdown(data, content)

    if args.format in ("markdown", "both"):
        print(markdown)
    if args.format in ("json", "both"):
        if args.format == "both":
            print("\n--- JSON ---")
        print(json.dumps(payload, indent=2, ensure_ascii=True))

    if args.save:
        stamp = _now_utc().strftime("trading_content_report_%Y%m%d_%H%M%S")
        md_path, json_path = save_outputs(args.output_dir, stamp, markdown, payload)
        print(f"\nSaved markdown: {md_path}")
        print(f"Saved json: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
