#!/usr/bin/env python3
"""
Prepare GitHub download-page readiness + Discord announcement for MN2 releases.

Does NOT compile the daemon (that lives in external/MasterNoder2). It:
  1. Reads TARGET_VERSION from mn2_release_config.py
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
    RELEASE_BASE,
    RELEASE_NOTES,
    REPO,
    TARGET_VERSION,
    TARBALL_NAME,
)

REQUIRED_ASSETS = (
    TARBALL_NAME,
    "RELEASE_MANIFEST.json",
    "MasterNoder2-qt-linux.tar.gz",
    "MasterNoder2-qt-win.zip",
    "QT_RELEASE_MANIFEST.json",
)

ANNOUNCE_DIR = ROOT / "docs" / "announcements"


def _gh_json(args: list[str]) -> dict | list | None:
    try:
        out = subprocess.check_output(["gh", *args], stderr=subprocess.DEVNULL, text=True)
        return json.loads(out)
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None


def release_asset_names() -> tuple[bool, list[str], str]:
    data = _gh_json(["api", f"repos/{REPO}/releases/tags/{TARGET_VERSION}"])
    if not isinstance(data, dict):
        return False, [], f"GitHub release {TARGET_VERSION} not found (or gh unavailable)"
    assets = data.get("assets") or []
    names = [str(a.get("name") or "") for a in assets if isinstance(a, dict)]
    missing = [n for n in REQUIRED_ASSETS if n not in names]
    ready = len(missing) == 0
    note = "all required assets present" if ready else ("missing: " + ", ".join(missing))
    return ready, names, note


def build_discord_payload(*, ready: bool, asset_note: str) -> dict:
    links = "\n".join(f"• [{name}]({RELEASE_BASE}/{name})" for name in REQUIRED_ASSETS)
    status = "READY" if ready else "PENDING BUILD"
    body = (
        f"**MasterNoder2 {TARGET_VERSION} — wallet & daemon downloads ({status})**\n\n"
        f"Platform UI **9.2.6.5** now paints **on-chain** balance and creates deposit addresses "
        f"so website users feed the network with real receive paths.\n\n"
        f"**GitHub release:** https://github.com/{REPO}/releases/tag/{TARGET_VERSION}\n"
        f"**Asset check:** {asset_note}\n\n"
        f"**Downloads**\n{links}\n\n"
        f"**Compile (when source updates)**\n"
        f"1. `bash scripts/mn2_build_release.sh` → daemon tarball + `RELEASE_MANIFEST.json`\n"
        f"2. `bash scripts/mn2_build_qt_release.sh` → Linux/Windows Qt + `QT_RELEASE_MANIFEST.json`\n"
        f"3. `python scripts/mn2_publish_release.py --tarball … --manifest … --qt-assets`\n"
        f"4. Re-run this script with `--post` once assets are live.\n\n"
        f"Site portal: /wallets\n"
        f"Spork gates 112/114 stay OFF until an operator signs them."
    )
    return {
        "id": f"mn2-release-{TARGET_VERSION}-downloads",
        "title": f"MasterNoder2 {TARGET_VERSION} downloads",
        "description": body[:4000],
        "url": f"https://github.com/{REPO}/releases/tag/{TARGET_VERSION}",
        "color": 0x00D4FF if ready else 0xFFAA00,
    }


def write_announcement(payload: dict, *, ready: bool, names: list[str], note: str) -> Path:
    ANNOUNCE_DIR.mkdir(parents=True, exist_ok=True)
    path = ANNOUNCE_DIR / f"mn2-{TARGET_VERSION}-discord.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = (
        f"# Discord announcement — MasterNoder2 {TARGET_VERSION}\n\n"
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
    payload = build_discord_payload(ready=ready, asset_note=note)
    path = write_announcement(payload, ready=ready, names=names, note=note)
    print(f"Announcement draft: {path}")
    print(f"Release {TARGET_VERSION}: ready={ready} ({note})")

    if args.post and not ready and not args.force_post:
        print("Refusing --post until all required assets exist (use --force-post to override).", file=sys.stderr)
        return 2

    result = maybe_post(payload, do_post=args.post, dry_run=args.dry_run_post)
    print(json.dumps({k: result.get(k) for k in ("success", "skipped", "dry_run", "duplicate", "message_id", "reason") if k in result or result.get(k) is not None}, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
