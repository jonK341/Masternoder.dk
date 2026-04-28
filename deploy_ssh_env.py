"""
SSH credentials for local deploy/maintenance scripts (paramiko).

Never hardcode passwords. Preferred: set DEPLOY_PASS in the environment (or a
local-only .env loaded by your shell — do not commit secrets).

If DEPLOY_PASS is unset and stdin is a TTY, deploy scripts prompt twice
(enter + confirm) so a mistyped password is caught before connecting.

Optional: DEPLOY_HOST (default masternoder.dk), DEPLOY_USER (default root).
"""
from __future__ import annotations

import getpass
import os
import sys


def deploy_host() -> str:
    return (os.environ.get("DEPLOY_HOST") or "masternoder.dk").strip()


def deploy_user() -> str:
    return (os.environ.get("DEPLOY_USER") or "root").strip()


def _load_deploy_pass_from_dotenv() -> None:
    """If DEPLOY_PASS is unset, set it from project .env (DEPLOY_PASS=...), if present."""
    if (os.environ.get("DEPLOY_PASS") or "").strip():
        return
    root = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(root, ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("DEPLOY_PASS="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        os.environ["DEPLOY_PASS"] = val
                    return
    except OSError:
        return


def require_deploy_pass() -> str:
    _load_deploy_pass_from_dotenv()
    v = (os.environ.get("DEPLOY_PASS") or "").strip()
    if v:
        return v
    if sys.stdin.isatty():
        host = deploy_host()
        user = deploy_user()
        first = getpass.getpass(f"SSH password for deploy ({user}@{host}): ")
        second = getpass.getpass("Confirm SSH password (re-enter): ")
        if first != second:
            print("Passwords do not match.", file=sys.stderr)
            raise SystemExit(1)
        if not first:
            print("Empty password.", file=sys.stderr)
            raise SystemExit(1)
        return first
    print(
        "DEPLOY_PASS is not set and this session is not interactive. "
        "Export DEPLOY_PASS or run deploy from a terminal for a password prompt.",
        file=sys.stderr,
    )
    raise SystemExit(1)
