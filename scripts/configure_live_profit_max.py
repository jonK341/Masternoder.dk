#!/usr/bin/env python3
"""One-shot: tune configs + env for maximum real live profit → platform treasury stash."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

from scripts.daemon_env import load_dotenv, live_status


def _ensure_env_flag(key: str, value: str) -> None:
    path = os.path.join(ROOT, ".env")
    lines: list[str] = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    found = False
    out: list[str] = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out).rstrip() + "\n")
    os.environ[key] = value


def _write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _import_vault_keys() -> list[str]:
    load_dotenv()
    if not os.environ.get("EXCHANGE_VAULT_KEY", "").strip():
        fb = os.environ.get("AGENT_CASINO_SECRET", "").strip()
        if fb:
            _ensure_env_flag("EXCHANGE_VAULT_KEY", fb)
            load_dotenv()
    from backend.services import exchange_secrets_vault_service as vault

    imported: list[str] = []
    for vid in ("binance", "nonkyc", "xeggex", "okx", "bybit", "kucoin"):
        key = (os.environ.get(f"{vid.upper()}_API_KEY") or "").strip()
        sec = (os.environ.get(f"{vid.upper()}_API_SECRET") or "").strip()
        if key and sec:
            vault.set_secret(f"{vid}_api_key", key)
            vault.set_secret(f"{vid}_api_secret", sec)
            imported.append(vid)
    return imported


def _probe_xeggex() -> tuple[bool, str]:
    """Balance probe after vault import — confirms keys work (not 401)."""
    from backend.services.exchange_venue_api_service import get_account_balance, venue_has_credentials

    if not venue_has_credentials("xeggex"):
        return False, "no_credentials_in_vault"
    try:
        res = get_account_balance("xeggex", dry_run=False)
    except Exception as exc:
        return False, str(exc)
    code = int(res.get("status_code") or 0)
    if res.get("success") and code == 200:
        return True, "ok"
    err = res.get("error") or res.get("body") or "probe_failed"
    return False, f"http_{code}:{err}"


def _live_dual_venues(xeggex_ok: bool) -> list[str]:
    venues = ["binance", "nonkyc"]
    if xeggex_ok:
        venues.append("xeggex")
    return venues


def _tune_connectors(*, xeggex_ok: bool = False, xeggex_reason: str = "") -> None:
    path = os.path.join(ROOT, "data", "exchange_connectors_config.json")
    micro = float(os.environ.get("EXCHANGE_LIVE_MICRO_USD", "75"))
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg["mode"] = "live"
    cfg["min_margin_bps"] = 14
    cfg["transfer_cost_bps"] = 14
    cfg["prefunded_transfer_cost_bps"] = 6
    cfg["price_cache_ttl_sec"] = 15
    cfg["paper_trade_usd"] = micro
    binance_quote = (os.environ.get("BINANCE_QUOTE") or "USDC").strip().upper()
    for v in cfg.get("venues") or []:
        if not isinstance(v, dict):
            continue
        vid = str(v.get("id") or "")
        if vid == "binance":
            v["quote"] = binance_quote
        elif vid == "xeggex":
            if xeggex_ok:
                v["live_trading"] = True
                v["note"] = "Live trading enabled — balance API probe returned 200."
            else:
                v["live_trading"] = False
                v["note"] = f"Excluded from live arb ({xeggex_reason or 'API probe failed'})."
    dual_venues = _live_dual_venues(xeggex_ok)
    for agent in cfg.get("arbitrage_agents") or []:
        if not isinstance(agent, dict):
            continue
        aid = str(agent.get("id") or "")
        if aid == "arb_live_dual_farm":
            agent["venues"] = list(dual_venues)
            agent["paper_trade_usd"] = max(micro, 75.0)
            agent["symbols"] = ["DOGE", "XRP", "LTC", "SOL", "ETH", "BTC", "AVAX", "LINK"]
        elif aid == "arb_agent_internal":
            agent["venues"] = ["binance", "nonkyc", "xeggex", "internal"]
            agent["paper_trade_usd"] = 400.0
        elif aid in ("arb_agent_btc_eth", "arb_agent_meme"):
            venues = list(agent.get("venues") or [])
            for v in ("binance", "nonkyc", "xeggex"):
                if v not in venues:
                    venues.insert(0, v)
            agent["venues"] = venues
    _write_json(path, cfg)


def _tune_extended_profit(*, xeggex_ok: bool = False) -> None:
    path = os.path.join(ROOT, "data", "exchange_extended_profit_config.json")
    micro = float(os.environ.get("EXCHANGE_LIVE_MICRO_USD", "75"))
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    strategies = cfg.setdefault("strategies", {})
    dual = strategies.setdefault("live_dual_venue", {})
    dual.update({
        "enabled": True,
        "venues": _live_dual_venues(xeggex_ok),
        "symbols": ["DOGE", "XRP", "LTC", "SOL", "ETH", "BTC", "AVAX", "LINK", "TRX"],
        "min_net_bps": 12,
        "notional_usd": max(micro, 75.0),
        "max_executions_per_tick": 2,
    })
    fast = strategies.setdefault("fast_arb_rescan", {})
    fast.update({
        "enabled": True,
        "min_net_bps": 12,
        "notional_usd": max(micro, 75.0),
        "venues": ["binance", "nonkyc", "xeggex", "okx", "bybit"],
        "note": "Ops may lower threshold via EXCHANGE_FAST_MIN_BPS env (not written to config).",
    })
    meme = strategies.setdefault("meme_momentum", {})
    meme.update({
        "enabled": True,
        "venues": ["binance", "nonkyc", "xeggex"],
        "min_net_bps": 16,
        "notional_usd": 200,
    })
    cfg.setdefault("profiles", {})["max"] = {
        "strategies": [
            "live_dual_venue",
            "fast_arb_rescan",
            "stablecoin_peg",
            "meme_momentum",
            "payments_spread",
            "triangular_paper",
            "defi_rotation",
        ]
    }
    _write_json(path, cfg)


def _tune_ai_trader() -> None:
    path = os.path.join(ROOT, "data", "exchange_ai_trading_config.json")
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg.update({
        "min_ai_score": 42,
        "min_net_bps": 14,
        "paper_trade_usd": max(float(os.environ.get("EXCHANGE_LIVE_MICRO_USD", "75")), 75.0),
        "capital_usd": 500,
        "venues": [
            "binance", "nonkyc", "xeggex", "okx", "bybit", "kucoin",
            "coinbase", "bitfinex", "gateio", "bitstamp", "cryptocom",
        ],
    })
    _write_json(path, cfg)


def _tune_profit_path_and_pair_search() -> None:
    path = os.path.join(ROOT, "data", "crypto_exchange", "profit_path_protocol.json")
    cfg: dict = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    cfg["rotation_live_enabled"] = True
    cfg["rotation_auto_execute"] = True
    cfg["profit_pair_search"] = {
        "enabled": True,
        "top_n": 16,
        "catalog_venues": ["binance", "nonkyc", "xeggex"],
        "min_live_net_bps": 10.0,
        "ledger_weight": 0.5,
        "live_weight": 0.5,
    }
    _write_json(path, cfg)


def _tune_treasury_and_payout() -> None:
    tpath = os.path.join(ROOT, "data", "exchange_treasury_config.json")
    with open(tpath, encoding="utf-8") as fh:
        tc = json.load(fh)
    tc["auto_stash_on_trade"] = True
    tc["auto_paypal_sweep"] = True
    tc["sync_internal_to_external_mid"] = True
    _write_json(tpath, tc)

    ppath = os.path.join(ROOT, "data", "crypto_exchange", "payout_config.json")
    payout = {}
    if os.path.isfile(ppath):
        with open(ppath, encoding="utf-8") as fh:
            payout = json.load(fh)
    payout["auto_sweep"] = False
    payout["min_sweep_usd"] = 500.0
    _write_json(ppath, payout)

    tpath = os.path.join(ROOT, "data", "exchange_treasury_config.json")
    if os.path.isfile(tpath):
        with open(tpath, encoding="utf-8") as fh:
            treasury = json.load(fh)
        treasury["auto_paypal_sweep"] = False
        _write_json(tpath, treasury)


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Tune configs + env for live profit max")
    p.add_argument("--fast", action="store_true", help="Apply env/config only; skip slow treasury/live_status report")
    args = p.parse_args()

    load_dotenv()
    _ensure_env_flag("EXCHANGE_ARBITRAGE_LIVE", "1")
    _ensure_env_flag("EXCHANGE_ROTATION_LIVE", "1")
    _ensure_env_flag("EXCHANGE_PROFIT_PAIR_SEARCH", "1")
    _ensure_env_flag("EXCHANGE_PAYOUT_PAYPAL_LIVE", "1")
    _ensure_env_flag("EXCHANGE_PAYOUT_BINANCE_LIVE", "1")
    _ensure_env_flag("EXCHANGE_PROFIT_PROFILE", "max")
    _ensure_env_flag("EXCHANGE_LIVE_PROFIT_MAX", "1")
    _ensure_env_flag("EXCHANGE_LIVE_MICRO_USD", os.environ.get("EXCHANGE_LIVE_MICRO_USD", "75"))
    _ensure_env_flag("BINANCE_QUOTE", os.environ.get("BINANCE_QUOTE", "USDC"))
    _ensure_env_flag("EXCHANGE_AUTO_PAYPAL_SWEEP", os.environ.get("EXCHANGE_AUTO_PAYPAL_SWEEP", "0"))
    _ensure_env_flag("EXCHANGE_FORCE_IPV4", os.environ.get("EXCHANGE_FORCE_IPV4", "1"))

    imported = _import_vault_keys()
    xeggex_ok, xeggex_reason = _probe_xeggex()
    _tune_connectors(xeggex_ok=xeggex_ok, xeggex_reason=xeggex_reason)
    _tune_extended_profit(xeggex_ok=xeggex_ok)
    _tune_ai_trader()
    _tune_profit_path_and_pair_search()
    _tune_treasury_and_payout()

    if args.fast:
        print("=== Live profit MAX configured (fast) ===")
        print(f"Vault keys imported: {imported or '(none — add API keys to .env)'}")
        print(f"XeggeX API probe: ok={xeggex_ok} reason={xeggex_reason}")
        print("Run: python3 scripts/mn2_live_pack_verify.py")
        return 0

    try:
        from backend.services.exchange_binance_time_service import sync_binance_time
        clock = sync_binance_time()
    except Exception as exc:
        clock = {"success": False, "error": str(exc)}

    try:
        from backend.services.exchange_treasury_service import treasury_status

        treasury = treasury_status()
    except Exception as exc:
        treasury = {"error": str(exc), "ledger_stashed_usd": 0}

    try:
        st = live_status()
    except Exception as exc:
        st = {"success": False, "error": str(exc)}
    print("=== Live profit MAX configured ===")
    print(f"Vault keys imported: {imported or '(none — add API keys to .env)'}")
    print(f"XeggeX API probe: ok={xeggex_ok} reason={xeggex_reason}")
    print(f"Binance clock: {clock}")
    print(f"Live readiness: venues={st.get('live_venue_count')} external_arb={st.get('can_trade_external')}")
    print(f"Treasury stash (USD): {treasury.get('ledger_stashed_usd', treasury.get('error', '?'))}")
    print(f"Payout ready_to_sweep: {st.get('ready_to_sweep')}")
    print("\nRestart profit daemon:")
    print("  .\\scripts\\run_all_profit_daemons.cmd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
