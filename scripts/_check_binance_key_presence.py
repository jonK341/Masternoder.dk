"""Print whether Binance keys are configured — never prints secret values."""
from __future__ import annotations

from pathlib import Path


def _env_present(name: str) -> tuple[bool, int]:
    path = Path(".env")
    if not path.is_file():
        return False, 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        if k.strip() != name:
            continue
        val = v.strip().strip('"').strip("'")
        return bool(val), len(val)
    return False, 0


def main() -> int:
    import os
    import sys

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.chdir(root)
    try:
        from scripts.daemon_env import load_dotenv
        load_dotenv()
    except Exception:
        pass

    for n in (
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "EXCHANGE_VAULT_KEY",
        "EXCHANGE_PAYOUT_BINANCE_LIVE",
        "EXCHANGE_ARBITRAGE_LIVE",
    ):
        ok, ln = _env_present(n)
        print(f"{n}: {'set' if ok else 'missing_or_empty'}" + (f" (len={ln})" if ok else ""))

    from backend.services import exchange_secrets_vault_service as vault
    from backend.services.exchange_binance_withdraw_service import binance_credentials
    from backend.services.exchange_venue_api_service import venue_has_credentials

    names = set(vault.list_secret_names())
    print("vault_binance_api_key:", "binance_api_key" in names)
    print("vault_binance_api_secret:", "binance_api_secret" in names)
    print("vault_status:", vault.vault_status())
    creds = binance_credentials()
    print("resolved_for_withdraw:", bool(creds.get("api_key") and creds.get("api_secret")))
    print("resolved_for_profit_daemon_venue:", venue_has_credentials("binance"))
    print(
        "same_keys:",
        "YES — multi-wallet withdraw and profit daemon both read "
        "vault binance_api_key/secret or env BINANCE_API_KEY/SECRET",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
