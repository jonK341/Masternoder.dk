#!/usr/bin/env python3
"""Configure the MN2 Discord channel from the terminal."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass


def _print(data: dict) -> int:
    print(json.dumps(data, indent=2, default=str))
    return 0 if data.get("success") is not False else 1


def cmd_show(_args: argparse.Namespace) -> int:
    from backend.services.discord_mn2_channel_service import get_config, resolve_webhook

    cfg = get_config()
    cfg["webhook_resolved"] = bool(resolve_webhook())
    cfg["bot_token_configured"] = bool(os.environ.get("DISCORD_BOT_TOKEN"))
    return _print({"success": True, **cfg})


def cmd_set_channel(args: argparse.Namespace) -> int:
    from backend.services.discord_mn2_channel_service import set_channel_id

    return _print(set_channel_id(args.channel_id))


def cmd_set_topic(args: argparse.Namespace) -> int:
    from backend.services.discord_mn2_channel_service import set_topic

    return _print(set_topic(args.topic, apply_discord=args.apply))


def cmd_set_stream(args: argparse.Namespace) -> int:
    from backend.services.discord_mn2_channel_service import set_stream

    enabled = args.action == "on"
    return _print(set_stream(args.stream, enabled))


def cmd_set_webhook(args: argparse.Namespace) -> int:
    from backend.services.discord_mn2_channel_service import set_webhook_url

    return _print(set_webhook_url(args.url))


def cmd_test_post(_args: argparse.Namespace) -> int:
    from backend.services.discord_mn2_channel_service import test_post

    return _print(test_post())


def cmd_post_info(args: argparse.Namespace) -> int:
    from backend.services.discord_mn2_channel_service import post_info_digest

    return _print(post_info_digest(force=args.force))


def cmd_reload(args: argparse.Namespace) -> int:
    from backend.services.discord_mn2_channel_service import reload_channel

    return _print(reload_channel(apply_topic=not args.skip_topic, post_pinned=not args.skip_pinned))


def main() -> int:
    parser = argparse.ArgumentParser(description="MN2 Discord channel configuration")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("show", help="Show current MN2 channel config").set_defaults(func=cmd_show)

    p_ch = sub.add_parser("set-channel", help="Set numeric Discord channel ID (for topic sync)")
    p_ch.add_argument("channel_id", help="Discord channel snowflake ID")
    p_ch.set_defaults(func=cmd_set_channel)

    p_top = sub.add_parser("set-topic", help="Set channel topic text")
    p_top.add_argument("topic", help="Topic string (max 1024 chars)")
    p_top.add_argument("--apply", action="store_true", help="PATCH topic via Discord Bot API")
    p_top.set_defaults(func=cmd_set_topic)

    p_wh = sub.add_parser("set-webhook", help="Set MN2 webhook URL in JSON config")
    p_wh.add_argument("url", help="Full Discord webhook URL")
    p_wh.set_defaults(func=cmd_set_webhook)

    p_stream = sub.add_parser("set-stream", help="Enable/disable a fan-out stream")
    p_stream.add_argument("stream", choices=["casino", "game", "market", "generator", "mn2_ledger", "social"])
    p_stream.add_argument("action", choices=["on", "off"])
    p_stream.set_defaults(func=cmd_set_stream)

    sub.add_parser("test-post", help="Send a test embed to the MN2 webhook").set_defaults(func=cmd_test_post)

    p_info = sub.add_parser("post-info", help="Post MN2 hub status digest")
    p_info.add_argument("--force", action="store_true", help="Ignore digest hour gate")
    p_info.set_defaults(func=cmd_post_info)

    p_reload = sub.add_parser("reload", help="Reload config, sync topic, repost pinned info")
    p_reload.add_argument("--skip-topic", action="store_true", help="Do not PATCH Discord channel topic")
    p_reload.add_argument("--skip-pinned", action="store_true", help="Do not post pinned_info embed")
    p_reload.set_defaults(func=cmd_reload)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
