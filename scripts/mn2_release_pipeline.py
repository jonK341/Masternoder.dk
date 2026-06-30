#!/usr/bin/env python3
"""Run the full MasterNoder2 v1.3 release pipeline (build -> publish -> verify -> promote -> upgrade).

Usage:
  # Full pipeline (system libs build — recommended on masternoder.dk VPS)
  python scripts/mn2_release_pipeline.py --ask-pass

  # Static depends build (slow; often fails Boost.Build on minimal VPS)
  python scripts/mn2_release_pipeline.py --ask-pass --depends

  # Same + push upstream C++ branch/tag (skips patch apply on future builds)
  python scripts/mn2_release_pipeline.py --ask-pass --push-upstream

  # Resume from a step
  python scripts/mn2_release_pipeline.py --ask-pass --from verify

  # Single step
  python scripts/mn2_release_pipeline.py --ask-pass --only build

Steps:
  1. build    — mn2_build_release_remote.py --ask-pass --fast --no-auto-depends (default)
  2. publish  — mn2_publish_release.py (draft, --skip-tag)
  3. verify   — mn2_release_status.py --tarball dist/…
  4. promote  — mn2_publish_release.py --promote
  5. upgrade  — mn2_daemon_upgrade_remote.py --ask-pass --apply --verify-post
  6. push     — optional: push external/MasterNoder2 branch + tag v1.3.0.0
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
DIST = os.path.join(ROOT, "dist")
TARBALL = os.path.join(DIST, "masternoder2d.tar.gz")
MANIFEST = os.path.join(DIST, "RELEASE_MANIFEST.json")

sys.path.insert(0, SCRIPTS)
from mn2_release_config import BASE_TAG, REPO, TARGET_VERSION  # noqa: E402

STEPS = ("build", "publish", "verify", "promote", "upgrade", "push")
UPSTREAM_BRANCH = "release/v1.3.0.0-multi-ping"
UPSTREAM_DIR = os.path.join(ROOT, "external", "MasterNoder2")


def _run(label: str, cmd: list[str], *, cwd: str | None = None) -> int:
    print(f"\n=== {label} ===")
    print("+", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd or ROOT)
    if proc.returncode != 0:
        print(f"\nFAILED: {label} (exit {proc.returncode})", file=sys.stderr)
    return proc.returncode


def _py(script: str, *args: str) -> list[str]:
    return [sys.executable, os.path.join(SCRIPTS, script), *args]


def step_build(ask_pass: bool, build_extra: list[str]) -> int:
    cmd = _py("mn2_build_release_remote.py")
    if ask_pass:
        cmd.append("--ask-pass")
    cmd.extend(build_extra)
    return _run("1/5 Build (remote Linux + pull dist/)", cmd)


def _resolve_build_extra(args: argparse.Namespace) -> list[str]:
    """Default to system libs on production VPS (depends boost often fails)."""
    extras = list(args.build_extra or [])
    if args.depends:
        return extras
    if "--fast" not in extras and "--auto-fast" not in extras:
        extras = ["--fast", *extras]
    if "--no-auto-depends" not in extras and "--auto-fast" not in extras:
        extras.append("--no-auto-depends")
    return extras


def step_publish() -> int:
    if not os.path.isfile(TARBALL):
        print(f"Tarball missing: {TARBALL}", file=sys.stderr)
        return 1
    manifest_args = ["--manifest", MANIFEST] if os.path.isfile(MANIFEST) else []
    return _run(
        "2/5 Publish (GitHub draft)",
        _py(
            "mn2_publish_release.py",
            "--tarball",
            TARBALL,
            *manifest_args,
            "--draft",
            "--skip-tag",
        ),
    )


def step_verify() -> int:
    return _run(
        "3/5 Verify (local tarball + release gate)",
        _py("mn2_release_status.py", "--tarball", TARBALL),
    )


def step_promote() -> int:
    return _run(
        "4/5 Promote (draft -> published)",
        _py("mn2_publish_release.py", "--tarball", TARBALL, "--promote"),
    )


def step_upgrade(ask_pass: bool) -> int:
    cmd = _py("mn2_daemon_upgrade_remote.py", "--apply", "--verify-post")
    if ask_pass:
        cmd.append("--ask-pass")
    return _run("5/5 Upgrade (remote daemon + post-verify)", cmd)


def step_push_upstream() -> int:
    if not os.path.isdir(os.path.join(UPSTREAM_DIR, ".git")):
        print(
            f"Optional push skipped: {UPSTREAM_DIR} is not a git clone.\n"
            f"  cd external && git clone https://github.com/{REPO}.git MasterNoder2",
            file=sys.stderr,
        )
        return 0
    rc = _run(
        f"Optional: push {UPSTREAM_BRANCH} + tag {TARGET_VERSION}",
        ["git", "push", "-u", "origin", f"HEAD:{UPSTREAM_BRANCH}"],
        cwd=UPSTREAM_DIR,
    )
    if rc != 0:
        return rc
    return _run(
        f"Optional: tag {TARGET_VERSION}",
        ["git", "push", "origin", f"HEAD:refs/tags/{TARGET_VERSION}"],
        cwd=UPSTREAM_DIR,
    )


def main() -> int:
    p = argparse.ArgumentParser(
        description=f"MasterNoder2 {TARGET_VERSION} release pipeline (build -> publish -> verify -> promote -> upgrade)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Equivalent manual commands:\n"
            "  1. python scripts/mn2_build_release_remote.py --ask-pass --fast --no-auto-depends\n"
            f"  2. python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz "
            f"--manifest dist/RELEASE_MANIFEST.json --draft --skip-tag\n"
            "  3. python scripts/mn2_release_status.py --tarball dist/masternoder2d.tar.gz\n"
            "  4. python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz --promote\n"
            "  5. python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply --verify-post\n"
            f"\nOptional: push MasterNoder2 branch {UPSTREAM_BRANCH} + tag {TARGET_VERSION} "
            f"(base {BASE_TAG}) with --push-upstream"
        ),
    )
    p.add_argument("--ask-pass", action="store_true", help="Pass --ask-pass to remote SSH scripts")
    p.add_argument(
        "--depends",
        action="store_true",
        help="Use static depends build (default: --fast --no-auto-depends system libs)",
    )
    p.add_argument(
        "--push-upstream",
        action="store_true",
        help=f"After upgrade, push external/MasterNoder2 branch {UPSTREAM_BRANCH} + tag {TARGET_VERSION}",
    )
    p.add_argument(
        "--from",
        dest="from_step",
        choices=STEPS,
        metavar="STEP",
        help="Start at this step (build|publish|verify|promote|upgrade|push)",
    )
    p.add_argument(
        "--only",
        dest="only_step",
        choices=STEPS,
        metavar="STEP",
        help="Run only this step",
    )
    p.add_argument(
        "--skip-promote",
        action="store_true",
        help="Stop after verify (leave GitHub release as draft)",
    )
    p.add_argument(
        "build_extra",
        nargs="*",
        help="Extra args forwarded to mn2_build_release_remote.py (e.g. --fast --no-auto-depends)",
    )
    args = p.parse_args()
    build_extra = _resolve_build_extra(args)

    if args.only_step:
        plan = [args.only_step]
    else:
        plan = ["build", "publish", "verify"]
        if not args.skip_promote:
            plan.extend(["promote", "upgrade"])
        if args.push_upstream:
            plan.append("push")
        if args.from_step:
            try:
                plan = plan[plan.index(args.from_step) :]
            except ValueError:
                plan = list(STEPS[STEPS.index(args.from_step) :])

    print(f"MasterNoder2 release pipeline {TARGET_VERSION}")
    print("Plan:", " -> ".join(plan))
    if "build" in plan:
        print("Build flags:", " ".join(build_extra))

    runners = {
        "build": lambda: step_build(args.ask_pass, build_extra),
        "publish": step_publish,
        "verify": step_verify,
        "promote": step_promote,
        "upgrade": lambda: step_upgrade(args.ask_pass),
        "push": step_push_upstream,
    }

    for name in plan:
        rc = runners[name]()
        if rc != 0:
            return rc

    print("\n=== Pipeline complete ===")
    if args.skip_promote:
        print("Draft published. Promote when ready:")
        print(f"  python scripts/mn2_release_pipeline.py --only promote")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
