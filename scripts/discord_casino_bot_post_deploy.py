#!/usr/bin/env python3
"""Post-deploy checks for Discord Casino Controller bot (Gate S — on-site custody only)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

DEFAULT_BASE = os.environ.get("POST_DEPLOY_BASE_URL", "https://masternoder.dk").rstrip("/")

_ENV_KEYS = [
    "DISCORD_BOT_TOKEN",
    "DISCORD_APPLICATION_ID",
    "DISCORD_PUBLIC_KEY",
    "DISCORD_GUILD_ID",
]
_ENV_WEBHOOKS = [
    "DISCORD_CHANNEL_ID_CASINO",
    "DISCORD_CHANNEL_ID_ANNOUNCEMENTS",
    "DISCORD_CHANNEL_ID_GAME",
    "DISCORD_CHANNEL_ID_MARKET",
]

_REPO_FILES = [
    "backend/services/discord_controller_service.py",
    "backend/services/discord_play_site_service.py",
    "data/discord_controller_config.json",
    "data/discord_app_manifest.json",
    "data/casino_monetization_v13.json",
    "discord-play/index.html",
    "scripts/discord_register_commands.py",
    "scripts/casino_play_app_discord_spider.py",
]

_CRON_FILES = [
    "cron/discord_market_fanout.sh",
    "cron/discord_promo_rotator.sh",
    "cron/discord_game_fanout.sh",
]


def _get(url: str, timeout: int = 20) -> Tuple[int, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body[:500]
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw[:500]
    except Exception as exc:
        return 0, str(exc)


def _ok(label: str, detail: str = "") -> Dict[str, Any]:
    row = {"label": label, "pass": True}
    if detail:
        row["detail"] = detail
    return row


def _fail(label: str, detail: str = "") -> Dict[str, Any]:
    row = {"label": label, "pass": False}
    if detail:
        row["detail"] = detail
    return row


def run_checks(base_url: str, *, local_env: bool = True) -> Dict[str, Any]:
    base = base_url.rstrip("/")
    rows: List[Dict[str, Any]] = []

    for rel in _REPO_FILES:
        path = os.path.join(ROOT, rel)
        rows.append(_ok(f"repo:{rel}") if os.path.isfile(path) else _fail(f"repo:{rel}", "missing"))

    for rel in _CRON_FILES:
        path = os.path.join(ROOT, rel)
        rows.append(_ok(f"cron:{rel}") if os.path.isfile(path) else _fail(f"cron:{rel}", "missing locally"))

    if local_env:
        for key in _ENV_KEYS:
            val = (os.environ.get(key) or "").strip()
            rows.append(_ok(f"env:{key}") if val else _fail(f"env:{key}", "not set in .env"))
        for key in _ENV_WEBHOOKS:
            val = (os.environ.get(key) or "").strip()
            ok = val.startswith("https://discord.com/api/webhooks/")
            rows.append(_ok(f"env:{key}") if ok else _fail(f"env:{key}", "webhook URL missing or invalid"))

    code, data = _get(f"{base}/api/discord/interactions")
    if code == 200 and isinstance(data, dict) and data.get("service") == "discord_interactions":
        rows.append(_ok("api:interactions", "discord_interactions live"))
    else:
        rows.append(_fail("api:interactions", f"HTTP {code} — {str(data)[:120]}"))

    code, data = _get(f"{base}/api/discord/controller/status")
    if code == 200 and isinstance(data, dict) and data.get("success"):
        env_cfg = (data.get("env") or {}).get("configured") or {}
        bot_ok = data.get("bot_token_configured")
        if bot_ok is None:
            bot_ok = env_cfg.get("bot_token")
        pub_ok = data.get("public_key_configured")
        if pub_ok is None:
            pub_ok = env_cfg.get("public_key")
        rows.append(_ok("api:controller/status") if bot_ok else _fail("api:controller/status", "bot_token_configured=false"))
        rows.append(_ok("api:public_key") if pub_ok else _fail("api:public_key", "public_key_configured=false"))
    else:
        rows.append(_fail("api:controller/status", f"HTTP {code}"))

    code, data = _get(f"{base}/api/social/platforms/hub")
    if code == 200 and isinstance(data, dict):
        disc = next((p for p in (data.get("platforms") or []) if p.get("id") == "discord"), None)
        rows.append(_ok("api:platforms/discord") if disc else _fail("api:platforms/discord", "missing"))
    else:
        rows.append(_fail("api:platforms/hub", f"HTTP {code}"))

    code, _ = _get(f"{base}/discord-play/")
    rows.append(_ok("page:discord-play") if code == 200 else _fail("page:discord-play", f"HTTP {code}"))

    code, data = _get(f"{base}/api/discord/app/manifest")
    if code == 200 and isinstance(data, dict) and (data.get("activities") or data.get("commands")):
        n_cmd = len(data.get("commands") or [])
        n_act = len(data.get("activities") or [])
        rows.append(_ok("api:app/manifest", f"{n_act} activities · {n_cmd} slash commands in config"))
    else:
        rows.append(_fail("api:app/manifest", f"HTTP {code}"))

    try:
        from backend.services.discord_setup_service import list_slash_command_payloads

        cmds = list_slash_command_payloads()
        rows.append(_ok("register:command_payloads", f"{len(cmds)} commands ready") if cmds else _fail("register:command_payloads", "0 commands"))
    except Exception as exc:
        rows.append(_fail("register:command_payloads", str(exc)[:120]))

    try:
        from backend.services.discord_m8_streams import run_casino_play_app_spider_bot

        rows.append(_ok("spider:import", "run_casino_play_app_spider_bot available"))
    except Exception as exc:
        rows.append(_fail("spider:import", str(exc)[:120]))

    passed = sum(1 for r in rows if r.get("pass"))
    return {
        "success": passed == len(rows),
        "base_url": base,
        "passed": passed,
        "total": len(rows),
        "checks": rows,
        "manual_next": [
            "Developer Portal: Interactions URL https://masternoder.dk/api/discord/interactions",
            "Run: python scripts/discord_register_commands.py (or ops POST /api/discord/setup/register-commands)",
            "Discord smoke: /play -> /link CODE -> /playnow -> /earn -> bet on /discord-play/",
            "When Google Play is live: python scripts/casino_play_app_discord_spider.py",
        ],
    }


def print_report(report: Dict[str, Any]) -> None:
    print(f"\nDiscord Casino Bot post-deploy — {report.get('base_url')}")
    print(f"Result: {report.get('passed')}/{report.get('total')} checks passed\n")
    for row in report.get("checks") or []:
        mark = "PASS" if row.get("pass") else "FAIL"
        line = f"  [{mark}] {row.get('label')}"
        if row.get("detail"):
            line += f" — {row['detail']}"
        print(line)
    if not report.get("success"):
        print("\nManual steps (after code deploy):")
        for step in report.get("manual_next") or []:
            print(f"  - {step}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Discord Casino Controller post-deploy checks")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--json", action="store_true", help="JSON output only")
    parser.add_argument("--skip-env", action="store_true", help="Skip local .env key checks")
    args = parser.parse_args()
    report = run_checks(args.base_url, local_env=not args.skip_env)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
