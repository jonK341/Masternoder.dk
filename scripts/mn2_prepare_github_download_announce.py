#!/usr/bin/env python3
"""
Prepare GitHub download-page readiness + Discord announcement for MN2 releases.

Does NOT compile the daemon (that lives in external/MasterNoder2). It:
  1. Reads DOWNLOAD_TAG / RELEASE_BASE from mn2_release_config.py
  2. Checks whether GitHub release assets exist (gh api)
  3. Writes a Discord announcement markdown draft
  4. Optionally posts via discord_service when --post and assets are ready

Compile checklist (run on a build host with the MasterNoder2 tree):

  python scripts/mn2_release_pipeline.py --help
  # or stepwise:
  bash scripts/mn2_build_release.sh
  bash scripts/mn2_build_qt_release.sh
  python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz --manifest dist/RELEASE_MANIFEST.json --qt-assets

Usage:
  python scripts/mn2_prepare_github_download_announce.py
  python scripts/mn2_prepare_github_download_announce.py --post
  python scripts/mn2_prepare_github_download_announce.py --dry-run-post
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mn2_release_config import (  # noqa: E402
    DOWNLOAD_REPO,
    DOWNLOAD_TAG,
    PROFIT_DAEMON_JON_URL,
    PUBLIC_VERSION,
    RELEASE_BASE,
    RELEASE_PAGE_URL,
    SOURCE_TARBALL_NAME,
    TARBALL_NAME,
)

REQUIRED_ASSETS = (
    TARBALL_NAME,
    "RELEASE_MANIFEST.json",
    "MasterNoder2-qt-linux.tar.gz",
    "MasterNoder2-qt-win.zip",
    "QT_RELEASE_MANIFEST.json",
    SOURCE_TARBALL_NAME,
)

# Extended packages — linked in Discord when present; do not block READY.
EXTENDED_ASSETS = (
    "dk.masternoder.MasterNoder2.flatpak",
    "FLATPAK_RELEASE_MANIFEST.json",
    "MasterNoder2-wallet-android.apk",
    "ANDROID_RELEASE_MANIFEST.json",
)

ANNOUNCE_DIR = ROOT / "docs" / "announcements"


def _gh_json(args: list[str]) -> dict | list | None:
    try:
        out = subprocess.check_output(["gh", *args], stderr=subprocess.DEVNULL, text=True)
        return json.loads(out)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None


def release_asset_names() -> tuple[bool, list[str], str]:
    data = _gh_json(["api", f"repos/{DOWNLOAD_REPO}/releases/tags/{DOWNLOAD_TAG}"])
    if not isinstance(data, dict):
        return False, [], f"GitHub release {DOWNLOAD_TAG} not found (or gh unavailable)"
    assets = data.get("assets") or []
    names = [str(a.get("name") or "") for a in assets if isinstance(a, dict)]
    missing = [n for n in REQUIRED_ASSETS if n not in names]
    ready = len(missing) == 0
    note = "all required assets present" if ready else ("missing: " + ", ".join(missing))
    return ready, names, note


def build_discord_payload(*, ready: bool, asset_note: str, present: list[str] | None = None) -> dict:
    present_set = set(present or [])
    core_links = "\n".join(f"• [{name}]({RELEASE_BASE}/{name})" for name in REQUIRED_ASSETS)
    extra = [n for n in EXTENDED_ASSETS if n in present_set]
    extra_links = (
        "\n".join(f"• [{name}]({RELEASE_BASE}/{name})" for name in extra)
        if extra
        else "• (Flatpak / Android not uploaded yet)"
    )
    status = "READY" if ready else "PENDING BUILD"
    body = (
        f"**The new wallet has arrived** — and **The Profit Daemon Jon** is released.\n\n"
        f"MasterNoder2 **{PUBLIC_VERSION}** wallet & daemon packages are live ({status}).\n"
        f"Platform UI **9.2.6.5** paints on-chain balance and creates deposit addresses.\n\n"
        f"**Wallet release:** {RELEASE_PAGE_URL}\n"
        f"**Profit Daemon Jon:** {PROFIT_DAEMON_JON_URL}\n"
        f"**Asset check:** {asset_note}\n\n"
        f"**Core downloads**\n{core_links}\n\n"
        f"**Extended**\n{extra_links}\n\n"
        f"Site portal: /wallets\n"
        f"Spork gates 112/114 stay OFF until an operator signs them."
    )
    return {
        "id": f"mn2-release-{DOWNLOAD_TAG}-downloads",
        "title": "The new wallet has arrived — Profit Daemon Jon is released",
        "description": body[:4000],
        "url": RELEASE_PAGE_URL,
        "color": 0x00D4FF if ready else 0xFFAA00,
    }


def write_announcement(payload: dict, *, ready: bool, names: list[str], note: str) -> Path:
    ANNOUNCE_DIR.mkdir(parents=True, exist_ok=True)
    path = ANNOUNCE_DIR / f"mn2-{DOWNLOAD_TAG}-discord.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = (
        f"# Discord announcement — MasterNoder2 {PUBLIC_VERSION}\n\n"
        f"Generated: {ts}\n"
        f"Ready: **{ready}** ({note})\n"
        f"Assets seen: {', '.join(names) if names else '(none)'}\n\n"
        f"## Embed title\n\n{payload['title']}\n\n"
        f"## Embed body\n\n{payload['description']}\n\n"
        f"## Operator notes\n\n"
        f"Full release notes live in `scripts/mn2_release_config.py` (`RELEASE_NOTES`).\n"
        f"Do not paste deploy hostnames into this draft.\n"
    )
    path.write_text(md, encoding="utf-8")
    return path


def maybe_post(payload: dict, *, do_post: bool, dry_run: bool) -> dict:
    if dry_run:
        return {"success": True, "dry_run": True, "payload": payload}
    if not do_post:
        return {"success": True, "skipped": True, "reason": "pass --post to send"}
    # Import app discord helper only when posting.
    sys.path.insert(0, str(ROOT))
    from backend.services.discord_service import post_message

    channel = os.environ.get("MN2_RELEASE_DISCORD_CHANNEL", "platform_news")
    return post_message(channel, payload, message_id=payload["id"])


def main() -> int:
    p = argparse.ArgumentParser(description="Prepare MN2 GitHub download Discord announcement")
    p.add_argument("--post", action="store_true", help="Post to Discord when assets are ready")
    p.add_argument("--dry-run-post", action="store_true", help="Print post payload without sending")
    p.add_argument("--force-post", action="store_true", help="Post even if assets are incomplete")
    args = p.parse_args()

    ready, names, note = release_asset_names()
    payload = build_discord_payload(ready=ready, asset_note=note, present=names)
    path = write_announcement(payload, ready=ready, names=names, note=note)
    print(f"Announcement draft: {path}")
    print(f"Release {DOWNLOAD_TAG}: ready={ready} ({note})")

    if args.post and not ready and not args.force_post:
        print("Refusing --post until all required assets exist (use --force-post to override).", file=sys.stderr)
        return 2

    result = maybe_post(payload, do_post=args.post, dry_run=args.dry_run_post)
    print(json.dumps({k: result.get(k) for k in ("success", "skipped", "dry_run", "duplicate", "message_id", "reason") if k in result or result.get(k) is not None}, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
