"""
SSH credentials for local deploy/maintenance scripts (paramiko).

Never hardcode passwords. Preferred: set DEPLOY_PASS in the environment (or a
local-only .env loaded by your shell — do not commit secrets).

If DEPLOY_PASS is unset and stdin is a TTY, deploy scripts prompt twice
(enter + confirm) so a mistyped password is caught before connecting.

If DEPLOY_PASS from .env is wrong and stdin is a TTY, connect_deploy_ssh
prompts once (getpass) and retries before exiting. Use --ask-pass to force
a prompt and ignore .env (no auto-retry after that prompt).

Optional:
  DEPLOY_HOST (default masternoder.dk)
  DEPLOY_USER (default root)
  DEPLOY_KEY_PATH — private key file (tried before password when set or ~/.ssh/id_ed25519 exists)
"""
from __future__ import annotations

import getpass
import os
import sys
from typing import Optional, Tuple

import paramiko


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


def require_deploy_pass(*, force_prompt: bool = False) -> str:
    if force_prompt:
        os.environ.pop("DEPLOY_PASS", None)
        os.environ["_DEPLOY_ASK_PASS"] = "1"
    else:
        _load_deploy_pass_from_dotenv()
    v = (os.environ.get("DEPLOY_PASS") or "").strip()
    if v and not force_prompt:
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

def _default_key_paths() -> list:
    paths = []
    env_key = (os.environ.get("DEPLOY_KEY_PATH") or "").strip()
    if env_key:
        paths.append(os.path.expanduser(env_key))
    home = os.path.expanduser("~/.ssh")
    for name in ("id_ed25519", "id_rsa", "id_ecdsa", "id_ed25519_deploy"):
        p = os.path.join(home, name)
        if p not in paths:
            paths.append(p)
    return [p for p in paths if os.path.isfile(p)]


def _password_connect(
    host: str,
    user: str,
    password: str,
    *,
    timeout: int,
) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        host, username=user, password=password, timeout=timeout,
        look_for_keys=False, allow_agent=False,
    )
    return ssh


def _try_ssh_key_auth(
    host: str,
    user: str,
    *,
    timeout: int = 30,
) -> Optional[Tuple[paramiko.SSHClient, str]]:
    """Try SSH agent and key files. Returns (client, label) or None."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            host,
            username=user,
            timeout=timeout,
            look_for_keys=True,
            allow_agent=True,
        )
        return ssh, "agent:ssh-agent"
    except paramiko.AuthenticationException:
        pass
    except Exception:
        pass

    for key_path in _default_key_paths():
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                host,
                username=user,
                key_filename=key_path,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=True,
            )
            return ssh, f"key:{key_path}"
        except paramiko.AuthenticationException:
            continue
        except Exception:
            continue
    return None


def connect_deploy_ssh(
    password: Optional[str] = None,
    *,
    timeout: int = 30,
) -> Tuple[paramiko.SSHClient, str, Optional[str]]:
    """Connect to deploy host. Tries SSH keys first, then password.

    Returns (client, auth_method, password_used). password_used is set only for
    password auth (None when connected via SSH key).
    """
    host = deploy_host()
    user = deploy_user()
    key_result = _try_ssh_key_auth(host, user, timeout=timeout)
    if key_result:
        return key_result[0], key_result[1], None
    if not password:
        password = require_deploy_pass()
    try:
        return _password_connect(host, user, password, timeout=timeout), "password", password
    except paramiko.AuthenticationException as exc:
        used_ask_pass = bool(os.environ.get("_DEPLOY_ASK_PASS"))
        if sys.stdin.isatty() and not used_ask_pass and not os.environ.get("_DEPLOY_AUTH_RETRIED"):
            os.environ["_DEPLOY_AUTH_RETRIED"] = "1"
            os.environ.pop("DEPLOY_PASS", None)
            retry_pw = getpass.getpass(
                f"SSH password for deploy ({user}@{host}) [auth failed, retry]: "
            )
            if retry_pw:
                try:
                    return (
                        _password_connect(host, user, retry_pw, timeout=timeout),
                        "password",
                        retry_pw,
                    )
                except paramiko.AuthenticationException:
                    pass
        os.environ.pop("_DEPLOY_AUTH_RETRIED", None)
        print_auth_help(host, user, used_ask_pass=used_ask_pass)
        raise SystemExit(1) from exc


def print_auth_help(host: str, user: str, *, used_ask_pass: bool = False) -> None:
    print("\n" + "=" * 60, file=sys.stderr)
    print("SSH AUTHENTICATION FAILED", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Target: {user}@{host}", file=sys.stderr)
    if used_ask_pass:
        print("  --ask-pass was used: the password you typed was rejected by the server.", file=sys.stderr)
        print("  (.env DEPLOY_PASS was cleared for the prompt — not a stale .env read.)", file=sys.stderr)
    else:
        print("  DEPLOY_PASS from .env / environment was rejected.", file=sys.stderr)
    print(file=sys.stderr)
    print("  Fix (recommended — passwordless):", file=sys.stderr)
    print("    python scripts/setup_deploy_ssh_key.py --ask-pass", file=sys.stderr)
    print("  Or update password:", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)

