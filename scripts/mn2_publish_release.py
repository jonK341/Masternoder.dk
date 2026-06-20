#!/usr/bin/env python3
"""Tag + publish MasterNoder2 v1.2.3.0 GitHub release (after Linux build)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys

from mn2_release_config import (
    MAIN_COMMIT,
    MANIFEST_NAME,
    REPO,
    RELEASE_NOTES,
    TARGET_VERSION,
)


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=check)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sync_manifest_tarball_sha(tarball: str, manifest_path: str) -> str:
    tar_sha = _sha256(tarball)
    with open(manifest_path, encoding="utf-8") as f:
        doc = json.load(f)
    doc["tarball_sha256"] = tar_sha
    doc["tarball_name"] = os.path.basename(tarball)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print(f"Synced manifest tarball_sha256 = {tar_sha}")
    return tar_sha


def verify_tarball(tarball: str, manifest_path: str | None, *, sync: bool = False) -> int:
    """Pre-publish checks. Returns 0 on success."""
    size = os.path.getsize(tarball)
    if size < 100_000:
        print(f"Tarball suspiciously small ({size} bytes)", file=sys.stderr)
        return 1

    if not manifest_path:
        print("WARN: no --manifest; skipping RELEASE_MANIFEST.json checks")
        return 0

    if not os.path.isfile(manifest_path):
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    with open(manifest_path, encoding="utf-8") as f:
        doc = json.load(f)

    if doc.get("version") != TARGET_VERSION:
        print(f"Manifest version {doc.get('version')} != {TARGET_VERSION}", file=sys.stderr)
        return 1

    tar_sha = _sha256(tarball)
    expected = doc.get("tarball_sha256")
    if expected and tar_sha != expected:
        if sync:
            sync_manifest_tarball_sha(tarball, manifest_path)
        else:
            print(f"Tarball sha256 mismatch:\n  manifest: {expected}\n  actual:   {tar_sha}", file=sys.stderr)
            print("Fix: python scripts/mn2_publish_release.py --tarball ... --manifest ... --sync-manifest", file=sys.stderr)
            return 1

    print(f"Tarball OK ({size:,} bytes, sha256 {tar_sha[:16]}…)")
    for name, meta in (doc.get("binaries") or {}).items():
        print(f"  {name}: {meta.get('size', '?')} bytes")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Publish MN2 v1.2.3.0 GitHub release")
    p.add_argument("--tarball", required=True, help="Path to masternoder2d.tar.gz from mn2_build_release.sh")
    p.add_argument("--manifest", help="RELEASE_MANIFEST.json (default: alongside tarball)")
    p.add_argument("--skip-tag", action="store_true", help="Release only (tag already exists)")
    p.add_argument("--draft", action="store_true", help="Create as draft release")
    p.add_argument("--promote", action="store_true", help="Publish existing draft release (no upload)")
    p.add_argument("--verify", action="store_true", help="Verify tarball + manifest only; do not publish")
    p.add_argument("--sync-manifest", action="store_true",
                   help="Update manifest tarball_sha256 to match tarball (fixes double-tar bug)")
    args = p.parse_args()

    tarball = os.path.abspath(args.tarball)
    if not os.path.isfile(tarball):
        print(f"Tarball not found: {tarball}", file=sys.stderr)
        return 1

    manifest = args.manifest
    if not manifest:
        candidate = os.path.join(os.path.dirname(tarball), MANIFEST_NAME)
        if os.path.isfile(candidate):
            manifest = candidate
    manifest = os.path.abspath(manifest) if manifest else None

    if args.sync_manifest and manifest and os.path.isfile(manifest):
        sync_manifest_tarball_sha(tarball, manifest)

    if verify_tarball(tarball, manifest, sync=args.sync_manifest) != 0:
        return 1
    if args.verify:
        print("Verify-only mode — OK")
        return 0

    sha_path = tarball + ".sha256"
    assets = [tarball]
    if os.path.isfile(sha_path):
        assets.append(sha_path)
    if manifest and os.path.isfile(manifest):
        assets.append(manifest)

    if args.promote:
        _run(["gh", "release", "edit", TARGET_VERSION, "--repo", REPO, "--draft=false"])
        print(f"\nPromoted draft {TARGET_VERSION} to published")
        print("Verify: python scripts/mn2_release_status.py")
        return 0

    if not args.skip_tag:
        tag_exists = subprocess.run(
            ["gh", "api", f"repos/{REPO}/git/refs/tags/{TARGET_VERSION}"],
            capture_output=True,
        ).returncode == 0
        if tag_exists:
            print(f"Tag {TARGET_VERSION} already exists — skipping tag create")
        else:
            _run(
                [
                    "gh",
                    "api",
                    f"repos/{REPO}/git/refs",
                    "-f",
                    f"ref=refs/tags/{TARGET_VERSION}",
                    "-f",
                    f"sha={MAIN_COMMIT}",
                ]
            )

    rel_exists = subprocess.run(
        ["gh", "release", "view", TARGET_VERSION, "--repo", REPO],
        capture_output=True,
    ).returncode == 0

    if rel_exists:
        print(f"Release {TARGET_VERSION} exists — uploading assets")
        _run(["gh", "release", "upload", TARGET_VERSION, *assets, "--repo", REPO, "--clobber"])
    else:
        cmd = [
            "gh",
            "release",
            "create",
            TARGET_VERSION,
            *assets,
            "--repo",
            REPO,
            "--title",
            TARGET_VERSION,
            "--notes",
            RELEASE_NOTES,
        ]
        if args.draft:
            cmd.append("--draft")
        _run(cmd)

    size = os.path.getsize(tarball)
    draft_note = " (draft)" if args.draft else ""
    print(f"\nPublished {TARGET_VERSION}{draft_note} ({size:,} bytes)")
    if args.draft:
        print(f"Promote when ready: python scripts/mn2_publish_release.py --tarball {tarball} --promote")
    print("Verify: python scripts/mn2_release_status.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
