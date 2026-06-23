#!/usr/bin/env python3
"""Remote MN2 daemon version audit + upgrade helper (when release assets exist)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

try:
    import dotenv

    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

import paramiko
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass
from mn2_release_config import MANIFEST_URL, RELEASE_URL, TARGET_VERSION


def release_asset_available(url: str = RELEASE_URL) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=25) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.URLError, OSError):
        return False


def sh(ssh, cmd: str, timeout: int = 180) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def audit_checks(web: str) -> list[tuple[str, str]]:
    return [
        ("systemd", "systemctl is-active masternoder2d 2>/dev/null || echo inactive"),
        (
            "binary",
            "/opt/masternoder2d/masternoder2d -version 2>/dev/null || masternoder2-cli -version 2>/dev/null || echo no-version",
        ),
        ("mnsync", "masternoder2-cli mnsync 2>/dev/null | head -c 200 || echo no-mnsync"),
        (
            "getstakinginfo",
            "masternoder2-cli getstakinginfo 2>/dev/null | head -c 400 || echo no-getstakinginfo",
        ),
        (
            "staking",
            f"cd {web} && ./venv/bin/python -c \"import json; from backend.services.mn2_rpc_client import getstakingstatus; print(json.dumps(getstakingstatus(), indent=2))\" 2>/dev/null || echo no-staking-rpc",
        ),
        ("health", "curl -s http://127.0.0.1:5000/api/mn2/health"),
        (
            "multi-ping-api",
            "curl -s http://127.0.0.1:5000/api/mn2/masternode/service | head -c 600",
        ),
    ]


def post_verify_checks(web: str) -> list[tuple[str, str, str]]:
    return [
        ("systemd-active", "systemctl is-active masternoder2d", "contains:active"),
        ("daemon-version", "/opt/masternoder2d/masternoder2d -version 2>&1 | head -1", "contains:1.3"),
        ("mnsync", "masternoder2-cli mnsync 2>&1 | head -c 200", "no_error"),
        ("getstakinginfo", "masternoder2-cli getstakinginfo 2>&1 | head -c 400", "no_error"),
        ("getnewaddress", "masternoder2-cli getnewaddress 2>&1 | head -1", "no_error"),
        ("health-json", "curl -sf http://127.0.0.1:5000/api/mn2/health", 'contains:"ok"'),
        (
            "staking-rpc",
            f"cd {web} && ./venv/bin/python -c \"from backend.services.mn2_rpc_client import getstakingstatus; s=getstakingstatus(); print('ok' if s else 'fail')\" 2>&1",
            "contains:ok",
        ),
    ]


def _check_output(out: str, rule: str) -> bool:
    text = out.strip()
    if not text or text.startswith("no-"):
        return False
    low = text.lower()
    if rule == "no_error":
        return "error" not in low and "connection refused" not in low
    if rule.startswith("contains:"):
        return rule.split(":", 1)[1] in text
    return True


def run_post_verify(ssh, web: str) -> bool:
    print("=== post-upgrade verification ===")
    ok = True
    for label, cmd, rule in post_verify_checks(web):
        out = sh(ssh, cmd, timeout=120)
        print(f"--- {label} ---")
        print(out)
        passed = _check_output(out, rule)
        if passed:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label}")
            ok = False
        print()
    return ok


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Audit daemon version on server; optional binary upgrade.")
    p.add_argument("--ask-pass", action="store_true")
    p.add_argument("--check-release", action="store_true", help="Only verify GitHub release asset (no SSH)")
    p.add_argument("--apply", action="store_true", help=f"Download and install {TARGET_VERSION} binary (maintenance window)")
    p.add_argument(
        "--verify-post",
        action="store_true",
        help="Run post-upgrade checks on server (no binary swap)",
    )
    args = p.parse_args()

    asset_ok = release_asset_available()
    manifest_ok = release_asset_available(MANIFEST_URL)
    print(f"Release asset {TARGET_VERSION}: {'available' if asset_ok else 'NOT FOUND'}")
    print(f"  {RELEASE_URL}")
    print(f"Manifest asset: {'available' if manifest_ok else 'optional / not uploaded'}")
    print(f"  {MANIFEST_URL}\n")

    if args.check_release:
        if not asset_ok:
            print("Build + publish first:")
            print("  python scripts/mn2_build_release_remote.py --ask-pass")
            print(
                "  python scripts/mn2_publish_release.py --tarball dist/masternoder2d.tar.gz "
                "--manifest dist/RELEASE_MANIFEST.json --draft --skip-tag"
            )
            return 1
        return 0

    if args.apply and not asset_ok:
        print(f"ERROR: Cannot --apply until {TARGET_VERSION} release asset exists on GitHub.", file=sys.stderr)
        print("Run: python scripts/mn2_release_status.py", file=sys.stderr)
        return 1

    host, user = deploy_host(), deploy_user()
    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=30)
    print(f"Connected {user}@{host}\n")

    web = "/var/www/html"

    if not args.apply and not args.verify_post:
        for label, cmd in audit_checks(web):
            print(f"=== {label} ===")
            print(sh(ssh, cmd, timeout=120))
            print()

    if args.verify_post:
        ok = run_post_verify(ssh, web)
        ssh.close()
        return 0 if ok else 1

    if args.apply:
        manifest_url = MANIFEST_URL if manifest_ok else ""
        print(f"=== upgrade {TARGET_VERSION} (stop → backup wallet → fetch → verify → install → start) ===")
        script = f"""
set -e
MANIFEST_URL='{manifest_url}'
RELEASE_URL='{RELEASE_URL}'

systemctl stop masternoder2d || true
cp /var/www/html/config/wallet.dat /root/wallet.dat.bak.$(date +%Y%m%d_%H%M) 2>/dev/null || true

mkdir -p /opt/masternoder2d && cd /tmp
rm -rf mn2-upgrade-* masternoder2d.tar.gz masternoder2d RELEASE_MANIFEST.json

curl -fsSL -o masternoder2d.tar.gz "$RELEASE_URL" || {{ echo 'Release asset not found'; exit 1; }}
if [[ -n "$MANIFEST_URL" ]]; then
  curl -fsSL -o RELEASE_MANIFEST.json "$MANIFEST_URL" || echo 'WARN: manifest download failed'
fi

if [[ -f RELEASE_MANIFEST.json ]]; then
  EXPECTED=$(python3 -c "import json; print(json.load(open('RELEASE_MANIFEST.json'))['tarball_sha256'])")
  ACTUAL=$(sha256sum masternoder2d.tar.gz | awk '{{print $1}}')
  if [[ "$EXPECTED" != "$ACTUAL" ]]; then
    echo "Tarball sha256 mismatch: expected $EXPECTED got $ACTUAL"
    exit 1
  fi
  echo "Tarball sha256 verified"
fi

tar -xzf masternoder2d.tar.gz
PKG=$(find . -type d -name masternoder2d | head -1)
test -n "$PKG" || PKG=.
DAEMON=$(find "$PKG" -name masternoder2d -type f | head -1)
CLI=$(find "$PKG" -name masternoder2-cli -type f | head -1)
TX=$(find "$PKG" -name masternoder2-tx -type f | head -1)
test -n "$DAEMON" || {{ echo 'masternoder2d binary not in tarball'; exit 1; }}

cp "$DAEMON" /opt/masternoder2d/masternoder2d
chmod +x /opt/masternoder2d/masternoder2d
if [[ -n "$CLI" ]]; then
  cp "$CLI" /usr/local/bin/masternoder2-cli 2>/dev/null || cp "$CLI" /opt/masternoder2d/masternoder2-cli
  chmod +x /usr/local/bin/masternoder2-cli 2>/dev/null || chmod +x /opt/masternoder2d/masternoder2-cli
fi
if [[ -n "$TX" ]]; then
  cp "$TX" /usr/local/bin/masternoder2-tx 2>/dev/null || true
  chmod +x /usr/local/bin/masternoder2-tx 2>/dev/null || true
fi

if [[ -f RELEASE_MANIFEST.json ]]; then
  INSTALLED=$(sha256sum /opt/masternoder2d/masternoder2d | awk '{{print $1}}')
  EXPECTED_BIN=$(python3 -c "import json; print(json.load(open('RELEASE_MANIFEST.json'))['binaries']['masternoder2d']['sha256'])")
  if [[ "$INSTALLED" != "$EXPECTED_BIN" ]]; then
    echo "Installed daemon sha256 mismatch"
    exit 1
  fi
  echo "Installed daemon sha256 verified"
fi

systemctl start masternoder2d
sleep 15
masternoder2-cli -datadir=/var/www/html/config startmasternode local false 2>/dev/null || true
"""
        print(sh(ssh, script, timeout=600))
        ok = run_post_verify(ssh, web)
        ssh.close()
        return 0 if ok else 1

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
