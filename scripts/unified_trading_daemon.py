#!/usr/bin/env python3
"""Unified trading daemon — one process for all trading bots.

Runs in a single OS process:
  - Exchange master (arb, AI, cross-trade, extended, fleet via control board)
  - Grid market-maker bot (Binance / NonKYC targets)
  - Stuck inventory strategy (scan → recalc → patch grid config)
  - Casino profit agents
  - Portal activity → micro MN2 on-chain batches (paper unless live)

Prefer this entry over separate grid + profit + casino daemons.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("UNIFIED_TRADING_DAEMON", "1")
os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def _load_trader_config_env() -> None:
    """Same env bootstrap as grid_bot_daemon (API keys from trader_app/config.json)."""
    import json
    import re

    def _loose(text):
        text = (text.replace("\u201c", '"').replace("\u201d", '"')
                    .replace("\u2018", "'").replace("\u2019", "'")
                    .replace("\u00a0", " ").replace("\ufeff", ""))
        out = []
        for line in text.splitlines():
            res, in_str, esc, i = [], False, False, 0
            while i < len(line):
                ch = line[i]
                if esc:
                    res.append(ch); esc = False; i += 1; continue
                if ch == "\\":
                    res.append(ch); esc = True; i += 1; continue
                if ch == '"':
                    in_str = not in_str; res.append(ch); i += 1; continue
                if (not in_str) and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    break
                res.append(ch); i += 1
            out.append("".join(res))
        repaired = []
        for line in out:
            m = re.match(r'^(\s*"[^"]*"\s*:\s*)(.+?)(,?)\s*$', line)
            if m:
                prefix, val, comma = m.groups()
                v = val.strip()
                if v and v[0] not in '"{[-0123456789' and v not in ("true", "false", "null"):
                    core = v.strip('"')
                    if re.match(r'^[A-Za-z0-9_.\-/:+=@]+$', core):
                        line = prefix + '"' + core + '"' + comma
            repaired.append(line)
        return re.sub(r",(\s*[}\]])", r"\1", "\n".join(repaired))

    for p in (os.path.join(ROOT, "trader_app", "config.json"), os.path.join(os.getcwd(), "config.json")):
        if os.path.isfile(p):
            try:
                raw = open(p, encoding="utf-8").read()
                try:
                    cfg = json.loads(raw)
                except Exception:
                    cfg = json.loads(_loose(raw))
            except Exception:
                return
            for k in (
                "BINANCE_API_KEY", "BINANCE_API_SECRET",
                "NONKYC_API_KEY", "NONKYC_API_SECRET", "NONKYC_API_PASSPHRASE",
                "XEGGEX_API_KEY", "XEGGEX_API_SECRET", "XEGGEX_API_PASSPHRASE",
                "EXCHANGE_VAULT_KEY", "EXCHANGE_ARBITRAGE_LIVE", "EXCHANGE_GRID_LIVE",
                "MN2_RPC_URL", "MN2_RPC_USER", "MN2_RPC_PASSWORD", "MN2_MICRO_CHAIN_LIVE",
                "MN2_MICRO_CHAIN_ADDRESS",
            ):
                v = cfg.get(k)
                if v not in (None, "") and not os.environ.get(k):
                    os.environ[k] = str(v)
            print(f"[unified] loaded trader config: {p}")
            return


def main() -> int:
    try:
        from scripts.daemon_env import load_dotenv
        load_dotenv()
    except Exception:
        pass
    _load_trader_config_env()
    from scripts.all_profit_daemons import main as apd_main
    return apd_main()


if __name__ == "__main__":
    raise SystemExit(main())
