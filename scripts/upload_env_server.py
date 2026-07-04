#!/usr/bin/env python3
"""Upload cleaned .env to production (strips local-only deploy keys)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

LOCAL_ONLY = frozenset({"DEPLOY_PASS", "DEPLOY_KEY_PATH", "DEPLOY_HOST", "DEPLOY_USER"})
SKIP_SECTION = "# === Local deploy only"
# Server-only ops keys — keep from remote .env when missing from upload bundle
PRESERVE_FROM_SERVER = (
    "PAYPAL_SUBSCRIPTION_PLAN_PRO",
    "PAYPAL_SUBSCRIPTION_PLAN_MN_HOST",
    "MONETIZATION_TIER_ENFORCEMENT",
    "AGENT_CASINO_SECRET",
    "COGS_ADMIN_REPORT_KEY",
    "AGENT_CRON_SECRET",
)


def _parse_env_keys(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


def merge_preserved_server_keys(content: str, remote_text: str) -> str:
    local = _parse_env_keys(content)
    remote = _parse_env_keys(remote_text)
    additions: list[str] = []
    for key in PRESERVE_FROM_SERVER:
        if local.get(key) or not remote.get(key):
            continue
        additions.append(f"{key}={remote[key]}")
    if not additions:
        return content
    base = content.rstrip("\n")
    return base + "\n\n# Preserved from server .env (ops keys not in local upload)\n" + "\n".join(additions) + "\n"


def build_server_env() -> str:
    lines = []
    skip_rest = False
    with open(".env", "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if SKIP_SECTION in line:
                skip_rest = True
                continue
            if skip_rest:
                continue
            if line.startswith("#") or not line.strip():
                lines.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            if key in LOCAL_ONLY:
                continue
            lines.append(line)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"


def main() -> int:
    content = build_server_env()
    var_count = sum(
        1 for l in content.splitlines() if l and not l.startswith("#") and "=" in l
    )
    print(f"Server .env: {var_count} variables")

    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        remote_env = ""
        try:
            with sftp.file("/var/www/html/.env", "r") as rf:
                remote_env = rf.read().decode("utf-8", errors="replace")
        except OSError:
            pass
        content = merge_preserved_server_keys(content, remote_env)
        with sftp.file("/var/www/html/.env", "w") as rf:
            rf.write(content)
        sftp.close()
        print("Uploaded /var/www/html/.env")

        for cmd in (
            "chmod 640 /var/www/html/.env && chown root:www-data /var/www/html/.env",
            "systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001",
        ):
            _, stdout, stderr = ssh.exec_command(cmd, timeout=90)
            err = stderr.read().decode().strip()
            code = stdout.channel.recv_exit_status()
            if code != 0:
                print(f"FAIL [{code}] {cmd}\n{err}")
                return 1
        print("Restarted uwsgi-vidgenerator services")
    finally:
        ssh.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
