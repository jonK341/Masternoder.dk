#!/usr/bin/env python3
"""Audit deploy manifest coverage against git branch changes.

Usage:
  python scripts/audit_deploy_manifest.py
  python scripts/audit_deploy_manifest.py create_app_release static_pages
  python scripts/audit_deploy_manifest.py --base origin/main create_app_release
  python scripts/audit_deploy_manifest.py --fail-on-missing create_app_release
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, List, Set

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from deploy import MANIFESTS, _merge_manifest_files  # noqa: E402

# Dev/ops paths — not uploaded by feature deploy manifests
_SKIP_EXACT = frozenset({
    ".gitignore",
    "docs/DEPLOY_CREATE_APP_RELEASE.md",
    "scripts/deploy.py",
    "scripts/deploy_all_and_restart_uwsgi.py",
    "scripts/audit_deploy_manifest.py",
})

_SKIP_PREFIXES = (
    "tests/",
    ".github/",
    ".cursor/",
)


def _git_branch_files(base_ref: str) -> Set[str]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=_ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=_ROOT,
            text=True,
        )
    return {line.strip() for line in out.splitlines() if line.strip()}


def _should_deploy(path: str) -> bool:
    if path in _SKIP_EXACT:
        return False
    return not any(path.startswith(prefix) for prefix in _SKIP_PREFIXES)


def _missing_on_disk(files: Iterable[str]) -> List[str]:
    missing = []
    for rel in files:
        if not (_ROOT / rel).is_file():
            missing.append(rel)
    return missing


def audit(manifest_names: List[str], base_ref: str) -> int:
    unknown = [m for m in manifest_names if m not in MANIFESTS]
    if unknown:
        print(f"Unknown manifest(s): {', '.join(unknown)}")
        print("Known:", ", ".join(sorted(MANIFESTS.keys())))
        return 2

    branch_files = _git_branch_files(base_ref)
    deploy_files = set(_merge_manifest_files(manifest_names))
    required = {p for p in branch_files if _should_deploy(p)}
    missing_from_manifest = sorted(required - deploy_files)
    extra_runtime = sorted(deploy_files - branch_files)

    disk_missing = _missing_on_disk(deploy_files)

    print("=== Deploy manifest audit ===\n")
    print(f"Base ref:              {base_ref}")
    print(f"Manifests:             {', '.join(manifest_names)}")
    print(f"Branch changed files:  {len(branch_files)}")
    print(f"Should deploy:         {len(required)}")
    print(f"Deploy manifest files: {len(deploy_files)}")
    print(f"Missing on disk:       {len(disk_missing)}\n")

    if missing_from_manifest:
        print(f"MISSING from manifest ({len(missing_from_manifest)}):")
        for path in missing_from_manifest:
            print(f"  - {path}")
        print()
    else:
        print("OK: All runtime branch files are in the deploy manifest.\n")

    skipped = sorted(branch_files - required)
    if skipped:
        print(f"Skipped (dev/ops only, {len(skipped)}):")
        for path in skipped:
            print(f"  - {path}")
        print()

    if disk_missing:
        print(f"MISSING on disk ({len(disk_missing)}):")
        for path in disk_missing[:30]:
            print(f"  - {path}")
        if len(disk_missing) > 30:
            print(f"  ... and {len(disk_missing) - 30} more")
        print()

    solo = set(_merge_manifest_files([manifest_names[0]])) if len(manifest_names) == 1 else None
    if solo is not None and manifest_names[0] != "static_pages":
        solo_gap = sorted(required - solo)
        print(f"=== {manifest_names[0]} alone ({len(solo)} files) ===")
        if solo_gap:
            print(f"Would miss {len(solo_gap)} branch runtime file(s) without static_pages:")
            for path in solo_gap[:15]:
                print(f"  - {path}")
            if len(solo_gap) > 15:
                print(f"  ... and {len(solo_gap) - 15} more")
        else:
            print("OK: manifest alone covers all branch runtime files.")
        print()

    if missing_from_manifest or disk_missing:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit deploy manifest vs branch changes")
    parser.add_argument(
        "manifests",
        nargs="*",
        default=["create_app_release", "static_pages"],
        help="Manifest names (default: create_app_release static_pages)",
    )
    parser.add_argument("--base", default="origin/main", help="Git base ref (default: origin/main)")
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit 1 if any runtime branch file is missing from manifest",
    )
    args = parser.parse_args()
    code = audit(args.manifests, args.base)
    if args.fail_on_missing and code != 0:
        return code
    if not args.fail_on_missing and code == 1:
        # Still report gaps but only fail on disk-missing when not strict
        branch_files = _git_branch_files(args.base)
        deploy_files = set(_merge_manifest_files(args.manifests))
        required = {p for p in branch_files if _should_deploy(p)}
        if not (required - deploy_files) and not _missing_on_disk(deploy_files):
            return 0
    return code


if __name__ == "__main__":
    raise SystemExit(main())
