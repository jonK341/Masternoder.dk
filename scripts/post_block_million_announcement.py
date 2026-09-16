#!/usr/bin/env python3
"""Post Block 1,000,000 genesis trophy announcement to Discord #announcements."""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.services.trophy_milestone_announcement_service import (
    build_block_million_announcement_payload,
    post_block_million_announcement,
)


def main() -> int:
    force = "--force" in sys.argv
    dry = "--dry-run" in sys.argv
    payload = build_block_million_announcement_payload()
    if dry:
        print(json.dumps(payload, indent=2))
        return 0
    result = post_block_million_announcement(force=force)
    print(json.dumps(result, indent=2))
    discord = result.get("discord") or {}
    if discord.get("success"):
        return 0
    if discord.get("error") == "webhook_not_configured":
        print("\nWebhook not configured. Set DISCORD_WEBHOOK_URL or DISCORD_CHANNEL_ID_ANNOUNCEMENTS.", file=sys.stderr)
        print("Draft saved: data/discord_block_million_trophy_announcement.txt", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
