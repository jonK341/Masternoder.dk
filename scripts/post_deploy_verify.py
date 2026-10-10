#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optional post-deploy checks (not run by deploy.py).

- Full-line smoke: MUST hit the real deployed app (all blueprints: shop, monetization,
  MN2, points). Do not expect --full-line to pass against a Flask app that only
  registers shop_bp — use local pytest for that surface instead.

- Local pytest: exercises shop routes with a minimal in-process app; it does not
  prove monetization/MN2/points integration.

Environment:
  POST_DEPLOY_BASE_URL — origin for smoke (default https://masternoder.dk)

Usage:
  python scripts/post_deploy_verify.py
  python scripts/post_deploy_verify.py --base-url https://masternoder.dk
  python scripts/post_deploy_verify.py --smoke-only
  python scripts/post_deploy_verify.py --pytest-only
  python scripts/post_deploy_verify.py --pytest-only --pytest-include-slow
  python scripts/post_deploy_verify.py --list

CI / automation:
  Set POST_DEPLOY_BASE_URL for staging. deploy.py can run this after upload when
  DEPLOY_POST_VERIFY=1 (see deploy.py).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASE = os.environ.get("POST_DEPLOY_BASE_URL", "https://masternoder.dk").rstrip("/")

SHOP_UNIT_TESTS = [
    "tests/unit/test_11_shop_routes.py",
    "tests/unit/test_shop_api_line_checks.py",
    "tests/unit/test_shop_file_inventory.py",
    "tests/unit/test_shop_purchase_profile_flow.py",
    "tests/unit/test_shop_serial_service.py",
    "tests/unit/test_monetization_scr_export.py",
    "tests/unit/test_07_shop.py",
]


def _run(cmd: list[str], cwd: Path) -> int:
    print(f"$ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=str(cwd))
    return r.returncode


def main() -> int:
    p = argparse.ArgumentParser(description="Post-deploy smoke + optional shop pytest")
    p.add_argument("--base-url", default=DEFAULT_BASE, help="Origin for full-line smoke")
    p.add_argument("--smoke-only", action="store_true", help="Only run shop_v4_production_smoke --full-line")
    p.add_argument("--pytest-only", action="store_true", help="Only run shop unit tests locally")
    p.add_argument(
        "--pytest-include-slow",
        action="store_true",
        help="Include tests marked @pytest.mark.slow (e.g. full purchase flow); default skips them for speed",
    )
    p.add_argument("--list", action="store_true", dest="list_only", help="Print manual checklist and exit 0")
    p.add_argument("--discord", action="store_true", help="Run Discord Casino Bot post-deploy checks only")
    args = p.parse_args()

    if args.list_only:
        print("Manual post-deploy checklist:\n")
        print("  [ ] Services: uwsgi, uwsgi-vidgenerator, python-proxy, uwsgi-vidgenerator-5001 active")
        print("  [ ] Browser: https://masternoder.dk/vidgenerator/ hard refresh (Ctrl+F5)")
        print("  [ ] API: python scripts/shop_v4_production_smoke.py --full-line")
        print("        (requires production stack: monetization, MN2, points - not shop-only Flask)")
        print("  [ ] Optional: pytest shop unit tests (local minimal app; excludes slow by default)")
        print("        python scripts/post_deploy_verify.py --pytest-only")
        print("  [ ] If needed: GET /api/shop/payment-health and shop DB migration per deploy.py notes")
        print("  [ ] Discord Casino Bot: python scripts/discord_casino_bot_post_deploy.py")
        print("        See docs/DISCORD_CASINO_BOT.md — portal registration + register slash commands")
        return 0

    if args.discord:
        disc_script = ROOT / "scripts" / "discord_casino_bot_post_deploy.py"
        if not disc_script.is_file():
            print(f"Missing {disc_script}", file=sys.stderr)
            return 1
        return _run(
            [sys.executable, str(disc_script), "--base-url", args.base_url.rstrip("/")],
            ROOT,
        )

    if args.smoke_only and args.pytest_only:
        print("Use only one of --smoke-only or --pytest-only.", file=sys.stderr)
        return 2

    smoke_script = ROOT / "scripts" / "shop_v4_production_smoke.py"
    if not smoke_script.is_file():
        print(f"Missing {smoke_script}", file=sys.stderr)
        return 1

    base = args.base_url.rstrip("/")
    codes: list[int] = []

    if not args.pytest_only:
        codes.append(
            _run(
                [
                    sys.executable,
                    str(smoke_script),
                    "--full-line",
                    "--base-url",
                    base,
                ],
                ROOT,
            )
        )

    if not args.smoke_only:
        existing = [t for t in SHOP_UNIT_TESTS if (ROOT / t).is_file()]
        if not existing:
            print("No shop unit test files found; skipping pytest.", flush=True)
        else:
            py_args = [sys.executable, "-m", "pytest", "-q"]
            if not args.pytest_include_slow:
                py_args.extend(["-m", "not slow"])
            py_args.extend(existing)
            codes.append(_run(py_args, ROOT))

    return 0 if all(c == 0 for c in codes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
