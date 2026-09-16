"""Masked audit of DISCORD_* / CASINO_DISCORD_* in local .env (no secrets printed)."""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, ".env")


def _status(key: str, value: str) -> str:
    if not value:
        return "empty"
    if "SECRET" in key or "TOKEN" in key:
        return "set (masked)"
    if "WEBHOOK" in key or key.startswith("DISCORD_CHANNEL_ID_"):
        if value.startswith("https://discord.com/api/webhooks/") or value.startswith(
            "https://discordapp.com/api/webhooks/"
        ):
            return "set (webhook URL, masked)"
        if re.fullmatch(r"\d+", value):
            return "set (numeric ID only — needs full webhook URL)"
        return "set (masked)"
    if key == "DISCORD_PUBLIC_KEY":
        return "set (public key, masked)" if len(value) >= 32 else "set (masked)"
    if key == "DISCORD_GUILD_ID":
        return "set (guild ID, masked)"
    return "set (masked)"


def main() -> int:
    if not os.path.isfile(ENV_PATH):
        print("ENV_FILE=missing")
        return 0
    print("ENV_FILE=present")
    found: dict[str, str] = {}
    with open(ENV_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, raw = line.partition("=")
            key = key.strip()
            if not (key.startswith("DISCORD_") or key.startswith("CASINO_DISCORD_")):
                continue
            value = raw.strip().strip('"').strip("'")
            found[key] = value
    if not found:
        print("(no DISCORD_* or CASINO_DISCORD_* lines found)")
        return 0
    for key in sorted(found):
        print(f"{key}={_status(key, found[key])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
