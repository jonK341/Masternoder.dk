#!/usr/bin/env python3
"""Mirror wallet-v1.3.0.0 assets onto jonK341/MasterNoder2 Latest (v1.3.1.0).

Requires GH_TOKEN / MN2_RELEASE_TOKEN with contents:write on MasterNoder2.
Downloads from the platform wallet GitHub release and uploads with --clobber.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from mn2_release_config import (  # noqa: E402
    DOWNLOAD_TAG,
    RELEASE_BASE,
    REPO,
    TARGET_VERSION,
)

ASSETS = (
    "masternoder2d.tar.gz",
    "masternoder2d.tar.gz.sha256",
    "RELEASE_MANIFEST.json",
    "MasterNoder2-qt-linux.tar.gz",
    "MasterNoder2-qt-linux.tar.gz.sha256",
    "MasterNoder2-qt-win.zip",
    "MasterNoder2-qt-win.zip.sha256",
    "QT_RELEASE_MANIFEST.json",
    "dk.masternoder.MasterNoder2.flatpak",
    "dk.masternoder.MasterNoder2.flatpak.sha256",
    "FLATPAK_RELEASE_MANIFEST.json",
    "MasterNoder2-v1.3.0.0-source.tar.gz",
    "MasterNoder2-v1.3.0.0-source.tar.gz.sha256",
)


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    p = argparse.ArgumentParser(description="Mirror wallet release assets to MasterNoder2")
    p.add_argument("--source-tag", default=DOWNLOAD_TAG)
    p.add_argument("--dest-tag", default=TARGET_VERSION, help="MasterNoder2 release tag (default Latest target)")
    p.add_argument("--dest-repo", default=REPO)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    source_base = f"{RELEASE_BASE}" if args.source_tag == DOWNLOAD_TAG else (
        RELEASE_BASE.replace(DOWNLOAD_TAG, args.source_tag)
    )
    # RELEASE_BASE already includes DOWNLOAD_TAG; rebuild if overridden.
    if args.source_tag != DOWNLOAD_TAG:
        from mn2_release_config import DOWNLOAD_REPO

        source_base = f"https://github.com/{DOWNLOAD_REPO}/releases/download/{args.source_tag}"

    with tempfile.TemporaryDirectory(prefix="mn2-mirror-") as tmp:
        paths: list[str] = []
        for name in ASSETS:
            url = f"{source_base}/{name}"
            dest = os.path.join(tmp, name)
            print(f"GET {url}")
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception as exc:
                print(f"skip {name}: {exc}")
                continue
            if os.path.getsize(dest) < 8:
                print(f"skip {name}: tiny file")
                continue
            paths.append(dest)
        if not paths:
            print("No assets downloaded", file=sys.stderr)
            return 1
        if args.dry_run:
            print(f"dry-run: would upload {len(paths)} files to {args.dest_repo}@{args.dest_tag}")
            return 0
        _run(
            [
                "gh",
                "release",
                "upload",
                args.dest_tag,
                *paths,
                "--repo",
                args.dest_repo,
                "--clobber",
            ]
        )
        print(f"Mirrored {len(paths)} assets → https://github.com/{args.dest_repo}/releases/tag/{args.dest_tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
