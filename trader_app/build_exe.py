#!/usr/bin/env python3
"""Build a standalone MN2 Private Control executable with PyInstaller.

Run on the OS you want the binary for (Windows -> .exe, macOS -> .app/bin, Linux -> bin):

    pip install pyinstaller
    python trader_app/build_exe.py

Output: dist/MN2PrivateControl/ (onedir) with the launcher inside. Run it, then open
http://127.0.0.1:8800 and unlock with your TRADER_PASSCODE. Set SITE_URL / SITE_ADMIN_KEY /
venue keys as environment variables (or trader_app/config.json) before launching.

Note: a Windows .exe can only be produced by running this script ON Windows (PyInstaller
does not cross-compile). Same script, run on each target OS.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEP = os.pathsep  # ';' on Windows, ':' elsewhere — PyInstaller --add-data separator


def _data(src_rel: str, dest_rel: str) -> str:
    return f"{os.path.join(ROOT, src_rel)}{SEP}{dest_rel}"


def main() -> int:
    try:
        import PyInstaller.__main__ as pyi
    except Exception:
        print("PyInstaller not installed. Run: pip install pyinstaller")
        return 1

    # Config JSONs the backend services read at runtime (relative to repo root).
    data_files = [
        "data/exchange_grid_bot_config.json",
        "data/exchange_venue_api_config.json",
        "data/exchange_connectors_config.json",
        "data/crypto_exchange_config.json",
        "data/exchange_sales_pool_config.json",
    ]
    args = [
        os.path.join(ROOT, "trader_app", "app.py"),
        "--name", "MN2PrivateControl",
        "--onedir", "--noconfirm", "--clean",
        "--paths", ROOT,
        "--add-data", _data("trader_app/templates", "trader_app/templates"),
    ]
    for df in data_files:
        if os.path.isfile(os.path.join(ROOT, df)):
            args += ["--add-data", _data(df, os.path.dirname(df) or ".")]
    # Embed the user's config.json into the build if present, so the exe "compiles with your
    # settings" (passcode + keys). A config.json next to the exe still overrides this at runtime.
    if os.path.isfile(os.path.join(ROOT, "trader_app", "config.json")):
        args += ["--add-data", _data("trader_app/config.json", ".")]
        print("[build] embedding trader_app/config.json into the executable")
    else:
        print("[build] NOTE: no trader_app/config.json found — exe will use defaults "
              "(passcode 'mn2-owner'). Create it from config.example.json to embed your settings.")
    for mod in (
        "backend.services.exchange_grid_bot_service",
        "backend.services.exchange_signals_service",
        "backend.services.exchange_venue_api_service",
        "backend.services.exchange_arbitrage_service",
        "backend.services.external_exchange_connector_service",
        "backend.services.crypto_exchange_service",
        "backend.services.exchange_secrets_vault_service",
        "trader_app.intelligence",
        "requests",
    ):
        args += ["--hidden-import", mod]

    print("PyInstaller args:\n  " + "\n  ".join(args))
    pyi.run(args)
    print("\nDone. Launch: dist/MN2PrivateControl/MN2PrivateControl"
          + (".exe" if sys.platform.startswith("win") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
