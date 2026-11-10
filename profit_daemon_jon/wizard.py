#!/usr/bin/env python3
"""First-run setup wizard for The Profit Daemon Jon (keys + paper/live)."""
from __future__ import annotations

import getpass
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ENV_PATH = os.path.join(ROOT, ".env")
EXAMPLE = os.path.join(ROOT, "profit_daemon_jon", ".env.example")


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or default


def _yes(prompt: str, default: bool = False) -> bool:
    d = "Y/n" if default else "y/N"
    val = input(f"{prompt} ({d}): ").strip().lower()
    if not val:
        return default
    return val in ("y", "yes", "1", "true")


def main() -> int:
    print("=" * 64)
    print("The Profit Daemon Jon — first-run setup wizard")
    print("=" * 64)
    lines = []
    if os.path.isfile(EXAMPLE):
        lines = open(EXAMPLE, encoding="utf-8").read().splitlines()
    else:
        lines = ["DAEMON_QUIET=1", "LITE_APP=1", "EXCHANGE_PROFIT_PROFILE=standard"]

    def set_kv(key: str, value: str) -> None:
        nonlocal lines
        found = False
        out = []
        for line in lines:
            if line.startswith(f"{key}=") or line.startswith(f"# {key}="):
                out.append(f"{key}={value}")
                found = True
            else:
                out.append(line)
        if not found:
            out.append(f"{key}={value}")
        lines = out

    mode = _ask("Mode: paper or live", "paper").lower()
    if mode not in ("paper", "live"):
        mode = "paper"
    set_kv("EXCHANGE_DAEMON_MODE", mode)
    set_kv("EXCHANGE_PROFIT_PROFILE", "standard" if mode == "paper" else "max")
    set_kv("EXCHANGE_ARBITRAGE_LIVE", "1" if mode == "live" else "0")
    set_kv("EXCHANGE_LIVE_PROFIT_MAX", "1" if mode == "live" else "0")

    # Offer credentials for every live-capable / ladder venue in the registry.
    try:
        from backend.services.exchange_registry_service import list_exchanges
        candidates = [
            r for r in list_exchanges()
            if r.get("live_trading") or r.get("ladder")
        ]
    except Exception:
        candidates = [
            {"id": "binance", "name": "Binance", "credentials_env": {
                "api_key": "BINANCE_API_KEY", "api_secret": "BINANCE_API_SECRET"}},
            {"id": "nonkyc", "name": "NonKYC", "credentials_env": {
                "api_key": "NONKYC_API_KEY", "api_secret": "NONKYC_API_SECRET"}},
        ]

    for row in candidates:
        name = row.get("name") or row.get("id")
        creds = row.get("credentials_env") or {}
        key_env = creds.get("api_key")
        secret_env = creds.get("api_secret")
        if not key_env or not secret_env:
            continue
        if _yes(f"Configure {name} API key/secret?", default=False):
            set_kv(str(key_env), _ask(str(key_env)))
            set_kv(str(secret_env), getpass.getpass(f"{secret_env}: "))
            pass_env = creds.get("api_passphrase")
            if pass_env and _yes(f"Configure {name} passphrase?", default=False):
                set_kv(str(pass_env), getpass.getpass(f"{pass_env}: "))

    if mode == "live":
        print("Live mode requires an encrypted vault key (Fernet).")
        vault = getpass.getpass("EXCHANGE_VAULT_KEY (required for live): ").strip()
        if not vault:
            print("Aborting: live unlock requires EXCHANGE_VAULT_KEY")
            return 2
        set_kv("EXCHANGE_VAULT_KEY", vault)
        set_kv("PROFIT_DAEMON_FORCE_VAULT", "1")

    set_kv("EXCHANGE_REDIS_URL", _ask("Redis URL", "redis://127.0.0.1:6379/0"))
    set_kv("EXCHANGE_METRICS_PORT", _ask("Metrics port", "9108"))
    set_kv("PROFIT_DAEMON_CONTROL_PORT", _ask("Local control port", "8787"))

    os.makedirs(ROOT, exist_ok=True)
    with open(ENV_PATH, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")
    print(f"Wrote {ENV_PATH}")
    print("Add more venues later via http://127.0.0.1:8787/ or data/exchanges_registry.json")
    print("Next: .venv/bin/python profit_daemon_jon/run.py --install-top25")
    print("      .venv/bin/python profit_daemon_jon/run.py --once --profile paper")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
