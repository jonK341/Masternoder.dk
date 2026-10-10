#!/usr/bin/env python3
"""Human-readable status report for live profit daemons, treasury, and engines."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _line(title: str, body: Any = None) -> str:
    if body is not None:
        return f"  {title}: {body}"
    return f"  {title}"


def _section(title: str, lines: List[str]) -> str:
    return f"\n## {title}\n" + "\n".join(lines)


def collect() -> Dict[str, Any]:
    from scripts.daemon_env import live_status, daemon_mode_label
    from backend.services.exchange_treasury_service import treasury_status
    from backend.services.exchange_payout_service import payout_status
    from backend.services.trading_bots_control_service import business_overview
    from backend.services.exchange_arbitrage_service import agent_accounts, scan_opportunities
    from backend.services.crypto_exchange_agent_service import list_agents
    from backend.services.exchange_ai_trading_service import ai_trading_status
    from backend.services import casino_agents_service as casino_agents

    live = live_status()
    treasury = treasury_status()
    payout = payout_status()
    board = business_overview()
    arb = agent_accounts()
    scan = scan_opportunities(
        symbols=["BTC", "ETH", "SOL", "XRP", "DOGE"],
        venues=["binance", "nonkyc", "xeggex"],
        notional_usd=500,
    )
    opps = scan.get("opportunities") or []
    best = opps[0] if opps else {}
    cross = list_agents()
    ai = ai_trading_status()

    hb_path = os.path.join(ROOT, "logs", "daemon_all_profit_heartbeat.json")
    heartbeat = None
    if os.path.isfile(hb_path):
        try:
            with open(hb_path, encoding="utf-8") as f:
                heartbeat = json.load(f)
        except Exception:
            pass

    daemon_running = False
    try:
        import subprocess
        out = subprocess.check_output(
            ['powershell', '-NoProfile', '-Command',
             "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | "
             "Where-Object { $_.CommandLine -match 'all_profit_daemons' } | Measure-Object | "
             "Select-Object -ExpandProperty Count"],
            text=True, timeout=8, cwd=ROOT,
        ).strip()
        daemon_running = out not in ("", "0")
    except Exception:
        pass

    return {
        "generated_at": _iso(),
        "mode_label": daemon_mode_label(),
        "env_profile": os.environ.get("EXCHANGE_PROFIT_PROFILE", "max"),
        "live_profit_max": os.environ.get("EXCHANGE_LIVE_PROFIT_MAX", "0"),
        "daemon_running": daemon_running,
        "heartbeat": heartbeat,
        "live": live,
        "treasury": treasury,
        "payout": payout,
        "control_board": board,
        "arb": arb,
        "market": {
            "best_bps": best.get("net_bps"),
            "best_symbol": best.get("symbol"),
            "buy_venue": best.get("buy_venue"),
            "sell_venue": best.get("sell_venue"),
            "profitable_count": scan.get("profitable_count"),
            "min_margin_bps": scan.get("min_margin_bps"),
        },
        "venue_balances": _venue_balances(),
        "cross_trade": cross,
        "ai": ai,
        "casino_agents": len((casino_agents.list_agents().get("agents") or [])),
    }


def _venue_balances() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        from backend.services.exchange_binance_withdraw_service import get_spot_asset_free, get_binance_buy_quote_asset
        from backend.services.exchange_venue_api_service import (
            get_account_balance, venue_has_credentials, parse_spot_balances, venue_quote_asset,
        )

        if venue_has_credentials("binance"):
            quote = get_binance_buy_quote_asset()
            b = get_spot_asset_free(quote, skip_live_gate=True)
            bals = parse_spot_balances("binance", dry_run=False) if b.get("success") else {}
            rows.append({
                "venue": "binance",
                "quote": quote,
                "quote_free": b.get("free"),
                "usdc_free": bals.get("USDC") or b.get("free") if quote == "USDC" else bals.get("USDC"),
                "usdt_free": bals.get("USDT"),
                "doge_free": bals.get("DOGE"),
                "ok": b.get("success"),
                "note": f"buy leg uses {quote}",
            })
        for vid in ("nonkyc", "xeggex"):
            if not venue_has_credentials(vid):
                rows.append({"venue": vid, "ok": False, "note": "no API keys"})
                continue
            r = get_account_balance(vid, dry_run=False)
            bals = parse_spot_balances(vid, dry_run=False) if r.get("success") else {}
            rows.append({
                "venue": vid,
                "ok": r.get("success"),
                "status_code": r.get("status_code"),
                "quote": venue_quote_asset(vid),
                "usdt_free": bals.get("USDT"),
                "doge_free": bals.get("DOGE"),
                "note": r.get("error") or "account OK",
            })
    except Exception as exc:
        rows.append({"venue": "?", "ok": False, "note": str(exc)})
    return rows


def format_report(data: Dict[str, Any]) -> str:
    lines: List[str] = [
        "=" * 72,
        "MasterNoder — LIVE PROFIT STATUS REPORT",
        f"Generated: {data.get('generated_at')}",
        "=" * 72,
    ]

    # Daemon
    d_lines = [
        _line("Process running", "yes" if data.get("daemon_running") else "NO — start run_all_profit_daemons.cmd"),
        _line("Profile", data.get("env_profile")),
        _line("Live profit MAX", data.get("live_profit_max")),
    ]
    hb = data.get("heartbeat")
    if hb:
        d_lines.append(_line("Last heartbeat", f"{hb.get('updated_at')} [{hb.get('loop')}] {hb.get('summary')}"))
    else:
        d_lines.append(_line("Last heartbeat", "none"))
    lines.append(_section("Daemon", d_lines))

    # Live gates
    live = data.get("live") or {}
    l_lines = [
        _line("Mode", live.get("mode")),
        _line("Arbitrage live gate", live.get("live_gate")),
        _line("Live venues credentialed", live.get("live_venue_count")),
        _line("External arb ready", live.get("can_trade_external")),
        _line("PayPal payout live", live.get("paypal_payout_live")),
    ]
    lines.append(_section("Live gates", l_lines))

    # Market
    mkt = data.get("market") or {}
    best_bps = mkt.get("best_bps")
    m_lines = [
        _line("Min margin required", f"{mkt.get('min_margin_bps')} bps"),
        _line("Best spread now", f"{best_bps} bps ({mkt.get('best_symbol')}: {mkt.get('buy_venue')} -> {mkt.get('sell_venue')})"),
        _line("Profitable opportunities", mkt.get("profitable_count")),
    ]
    if best_bps is not None and float(best_bps) < float(mkt.get("min_margin_bps") or 18):
        m_lines.append(_line("Arb status", "WAITING - spreads below margin (normal)"))
    else:
        m_lines.append(_line("Arb status", "EDGE AVAILABLE - live trades should fire on next tick"))
    lines.append(_section("Market scan (Binance + NonKYC + XeggeX)", m_lines))

    vb_lines = []
    for row in data.get("venue_balances") or []:
        vid = row.get("venue", "?")
        if vid == "binance":
            q = row.get("quote") or "USDC"
            vb_lines.append(_line(
                vid,
                f"ok={row.get('ok')} {q}=${row.get('quote_free', '-')} "
                f"DOGE={row.get('doge_free', '-')} {row.get('note', '')}",
            ))
        elif vid == "nonkyc":
            vb_lines.append(_line(
                vid,
                f"ok={row.get('ok')} USDT=${row.get('usdt_free', '-')} "
                f"DOGE={row.get('doge_free', '-')} {row.get('note', '')}",
            ))
        else:
            vb_lines.append(_line(vid, f"ok={row.get('ok')} {row.get('note', '')}"))
    if vb_lines:
        lines.append(_section("Live venue balances (required for real trades)", vb_lines))

    # Treasury
    tr = data.get("treasury") or {}
    t_lines = [
        _line("Treasury wallet", tr.get("treasury_user_id")),
        _line("MN2 balance", tr.get("mn2_balance")),
        _line("Total stashed (USD ledger)", tr.get("ledger_stashed_usd")),
        _line("  - paper stashed", tr.get("ledger_stashed_usd_paper")),
        _line("  - LIVE stashed", tr.get("ledger_stashed_usd_live", 0)),
        _line("Auto-stash on trade", tr.get("auto_stash_on_trade")),
    ]
    lines.append(_section("Treasury stash", t_lines))

    # Payout
    pay = data.get("payout") or {}
    pcfg_path = os.path.join(ROOT, "data", "crypto_exchange", "payout_config.json")
    last_sweep = None
    if os.path.isfile(pcfg_path):
        try:
            with open(pcfg_path, encoding="utf-8") as f:
                last_sweep = json.load(f).get("last_sweep")
        except Exception:
            pass
    p_lines = [
        _line("Payout mode", pay.get("mode")),
        _line("Destination", pay.get("destination")),
        _line("PayPal email", (pay.get("paypal") or {}).get("email")),
        _line("Auto sweep", pay.get("auto_sweep")),
        _line("Min sweep USD", pay.get("min_sweep_usd")),
        _line("Net unswept USD", pay.get("net_unswept_usd")),
        _line("PayPal sweepable USD", pay.get("paypal_sweepable_usd")),
        _line("Ready to sweep", pay.get("ready_to_sweep")),
        _line("Swept total USD", pay.get("swept_total_usd")),
    ]
    if last_sweep:
        p_lines.append(_line("Last sweep", f"${last_sweep.get('amount_usd')} to {last_sweep.get('receiver_email')} ({last_sweep.get('mode')}) @ {last_sweep.get('ts')}"))
    lines.append(_section("PayPal / payout", p_lines))

    # Engines
    board = data.get("control_board") or {}
    totals = board.get("totals") or {}
    arb = data.get("arb") or {}
    cross = data.get("cross_trade") or {}
    ai = data.get("ai") or {}
    e_lines = [
        _line("Kill switch", board.get("kill_switch")),
        _line("Platform bots", totals.get("bot_count")),
        _line("Platform PnL (USD)", totals.get("total_realized_pnl_usd")),
        _line("Arb agents", f"{arb.get('agent_count')} (profit ${arb.get('total_realized_profit_usd')})"),
        _line("Cross-trade bots", f"{len(cross.get('agents') or [])} enabled, tick #{cross.get('tick_count')}"),
        _line("AI trader", f"enabled={ai.get('enabled')} min_score={ai.get('min_ai_score')}"),
        _line("Casino agents", data.get("casino_agents")),
    ]
    lines.append(_section("Profit engines", e_lines))

    # Actions
    actions = []
    if not data.get("daemon_running"):
        actions.append("Start daemon: .\\scripts\\run_all_profit_daemons.cmd")
    if float(tr.get("ledger_stashed_usd_live") or 0) == 0:
        actions.append("Live USD stash is $0 - need positive spreads AND funded venue wallets")
    bal = data.get("venue_balances") or []
    binance = next((b for b in bal if b.get("venue") == "binance"), {})
    nonkyc = next((b for b in bal if b.get("venue") == "nonkyc"), {})
    b_quote = str(binance.get("quote") or "USDC").upper()
    b_stable = float(binance.get("quote_free") or binance.get("usdc_free") or 0)
    if binance.get("ok") and b_stable < 20:
        actions.append(f"BLOCKER: Binance {b_quote} balance low (${b_stable:.2f}) — need quote for buy leg")
    n_usdt = float(nonkyc.get("usdt_free") or 0)
    if nonkyc.get("ok") and n_usdt < 20:
        actions.append(f"BLOCKER: NonKYC USDT low (${n_usdt:.2f})")
    b_doge = float(binance.get("doge_free") or 0)
    n_doge = float(nonkyc.get("doge_free") or 0)
    if b_doge < 100 and n_doge < 100:
        actions.append("Hold DOGE on both venues for sell legs (~$25+ each side recommended)")
    xeg = next((b for b in bal if b.get("venue") == "xeggex"), {})
    if xeg.get("ok") is False and xeg.get("status_code") == 401:
        actions.append("Fix XeggeX API keys (401 Unauthorized) or remove from live farm")
    if best_bps is not None and float(best_bps) < 0:
        actions.append(f"Current best spread {best_bps} bps - no live arb until market moves")
    if not actions:
        actions.append("System healthy — monitor [all-profit] logs for live_trades=N")
    lines.append(_section("Recommended actions", [_line(a) for a in actions]))

    lines.append("\n" + "=" * 72)
    lines.append("Re-run: python scripts/profit_status_report.py")
    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Live profit system status report")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text")
    parser.add_argument("--save", action="store_true", help="Write to logs/profit_status_report.txt")
    args = parser.parse_args()

    from scripts.daemon_env import load_dotenv
    load_dotenv()
    data = collect()

    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        text = format_report(data)
        print(text)
        if args.save:
            os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
            path = os.path.join(ROOT, "logs", "profit_status_report.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            print(f"\nSaved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
