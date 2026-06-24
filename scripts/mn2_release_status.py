#!/usr/bin/env python3
"""Check MasterNoder2 release readiness (tag, GitHub asset, local tarball)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request

from mn2_release_config import (
    BASE_TAG,
    MANIFEST_NAME,
    MANIFEST_URL,
    PATCH_REL,
    REPO,
    RELEASE_URL,
    TARGET_VERSION,
)


def _gh_json(args: list) -> dict | list | None:
    try:
        out = subprocess.check_output(["gh"] + args, stderr=subprocess.DEVNULL, text=True)
        return json.loads(out) if out.strip() else None
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return None


def _head_ok(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.HTTPError, urllib.error.URLError, OSError):
        pass
    try:
        req = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status in (200, 206)
    except (urllib.error.URLError, OSError):
        return False


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_local_tarball(tarball: str, manifest_path: str | None) -> bool:
    print(f"\nLocal tarball: {tarball}")
    if not os.path.isfile(tarball):
        print("  exists: False")
        return False

    size = os.path.getsize(tarball)
    print(f"  size: {size:,} bytes")
    tar_sha = _sha256(tarball)
    print(f"  sha256: {tar_sha}")

    if not manifest_path:
        manifest_path = os.path.join(os.path.dirname(tarball), MANIFEST_NAME)
    if os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            doc = json.load(f)
        expected = doc.get("tarball_sha256")
        if expected:
            match = expected == tar_sha
            print(f"  manifest tarball_sha256: {'OK' if match else 'MISMATCH'}")
            if not match:
                print(f"    expected: {expected}")
                return False
        print(f"  manifest version: {doc.get('version')} git_sha: {str(doc.get('git_sha', ''))[:12]}")
        if doc.get("patch_applied"):
            print(f"  patch: {doc.get('base_tag')} + {doc.get('patch_file')}")
        binaries = list((doc.get("binaries") or {}).keys())
        print(f"  manifest binaries: {', '.join(binaries) or 'none'}")
    else:
        print(f"  manifest: not found ({manifest_path})")

    try:
        with tarfile.open(tarball, "r:gz") as tf:
            names = tf.getnames()
        has_d = any(n.endswith("masternoder2d/masternoder2d") or n == "masternoder2d" for n in names)
        has_cli = any("masternoder2-cli" in n for n in names)
        has_tx = any("masternoder2-tx" in n for n in names)
        has_manifest = any("RELEASE_MANIFEST.json" in n for n in names)
        print(f"  tarball contents: daemon={has_d} cli={has_cli} tx={has_tx} manifest={has_manifest}")
    except tarfile.TarError as e:
        print(f"  tarball read error: {e}")
        return False

    return size >= 100_000


def main() -> int:
    p = argparse.ArgumentParser(description=f"MN2 {TARGET_VERSION} release gate checks")
    p.add_argument("--tarball", help="Local masternoder2d.tar.gz path to verify")
    p.add_argument("--manifest", help="RELEASE_MANIFEST.json (default: alongside tarball)")
    args = p.parse_args()

    print(f"=== MasterNoder2 {TARGET_VERSION} release status ===\n")

    tag = _gh_json(["api", f"repos/{REPO}/git/refs/tags/{TARGET_VERSION}"])
    print(f"Git tag {TARGET_VERSION}: {'yes' if tag else 'MISSING (patch build OK with --skip-tag)'}")

    branch = _gh_json(["api", f"repos/{REPO}/git/refs/heads/release/v1.3.0.0-multi-ping"])
    print(f"Branch release/v1.3.0.0-multi-ping: {'yes' if branch else 'not pushed'}")

    patch_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), PATCH_REL.replace("/", os.sep))
    print(f"Site patch {PATCH_REL}: {'yes' if os.path.isfile(patch_path) else 'MISSING'}")

    rel = _gh_json(["release", "view", TARGET_VERSION, "--repo", REPO, "--json", "name,isDraft,assets"])
    draft = False
    if rel:
        draft = bool(rel.get("isDraft"))
        assets = [a.get("name") for a in (rel.get("assets") or [])]
        draft_label = " (DRAFT)" if draft else ""
        print(f"GitHub release: yes{draft_label} (assets: {', '.join(assets) or 'none'})")
        has_manifest = MANIFEST_NAME in assets
        print(f"  manifest asset: {'yes' if has_manifest else 'missing'}")
    else:
        latest = _gh_json(["release", "view", "--repo", REPO, "--json", "tagName"])
        lat = (latest or {}).get("tagName", "?")
        print(f"GitHub release {TARGET_VERSION}: MISSING (latest published: {lat})")

    asset_ok = _head_ok(RELEASE_URL)
    manifest_ok = _head_ok(MANIFEST_URL)
    published_ready = asset_ok and not draft
    print(f"Tarball URL reachable: {'yes' if asset_ok else 'NO — build + publish first'}")
    print(f"  {RELEASE_URL}")
    print(f"Manifest URL reachable: {'yes' if manifest_ok else 'no (optional until uploaded)'}")
    print(f"  {MANIFEST_URL}")
    if asset_ok and draft:
        print("\nNote: release exists as DRAFT — promote before production --apply:")
        print("  python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz --promote")

    local_ok = True
    if args.tarball:
        local_ok = verify_local_tarball(
            os.path.abspath(args.tarball),
            os.path.abspath(args.manifest) if args.manifest else None,
        )

    print("\n=== Next steps ===")
    if published_ready:
        print("  python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply")
        print("  python scripts/mn2_daemon_upgrade_remote.py --ask-pass --verify-post")
        print("  python scripts/mn2_probe_multi_ping.py --public")
    else:
        print("  All-in-one:  python scripts/mn2_release_pipeline.py --ask-pass")
        print("  (optional)   python scripts/mn2_release_pipeline.py --ask-pass --push-upstream")
        print("  1. Build:    python scripts/mn2_build_release_remote.py --ask-pass")
        print(
            "  2. Publish:  python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz "
            "--manifest dist/RELEASE_MANIFEST.json --draft --skip-tag"
        )
        print("  3. Verify:   python scripts/mn2_release_status.py --tarball dist/masternoder2d.tar.gz")
        print("  4. Promote:  python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz --promote")
        print("  5. Upgrade:  python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply --verify-post")
        print(f"\n  Optional: push MasterNoder2 branch + tag {TARGET_VERSION} (base {BASE_TAG}) to skip patch apply.")

    gate = published_ready and (local_ok if args.tarball else True)
    return 0 if gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
