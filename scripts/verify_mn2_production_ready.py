#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-deploy check: .env MN2_RPC_* matches config/masternoder2.conf and RPC answers getblockcount.

Run from project root:
  python scripts/verify_mn2_production_ready.py
  python scripts/verify_mn2_production_ready.py --no-rpc   # file match only

Exit 0 if checks pass, 1 if mismatch or RPC failure.
"""
from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(_ROOT, ".env"))
    except ImportError:
        pass


def _parse_conf(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _check_match(conf: dict[str, str], env_user: str, env_pass: str) -> list[str]:
    issues: list[str] = []
    ru = (conf.get("rpcuser") or "").strip()
    rp = (conf.get("rpcpassword") or "").strip()
    if not ru and not rp:
        issues.append("config/masternoder2.conf missing or has no rpcuser/rpcpassword")
        return issues
    if env_user != ru:
        issues.append(f"rpcuser mismatch: .env MN2_RPC_USER={env_user!r} vs conf rpcuser={ru!r}")
    if env_pass != rp:
        issues.append("rpcpassword mismatch: MN2_RPC_PASSWORD does not equal rpcpassword in config/masternoder2.conf")
    if not env_user or not env_pass:
        issues.append("Set MN2_RPC_USER and MN2_RPC_PASSWORD in .env (must match daemon config)")
    return issues


def _try_rpc() -> tuple[bool, str]:
    try:
        import requests
    except ImportError:
        return False, "requests not installed; pip install requests"
    url = (os.environ.get("MN2_RPC_URL") or "").strip() or "http://127.0.0.1:9332"
    user = (os.environ.get("MN2_RPC_USER") or "").strip()
    password = (os.environ.get("MN2_RPC_PASSWORD") or "").strip()
    payload = {"jsonrpc": "1.0", "id": "verify", "method": "getblockcount", "params": []}
    try:
        r = requests.post(
            url,
            json=payload,
            auth=(user, password) if user or password else None,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
    except Exception as e:
        return False, str(e)
    if r.status_code == 401:
        return False, "HTTP 401 — MN2_RPC_USER / MN2_RPC_PASSWORD do not match the daemon"
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    try:
        data = r.json()
    except Exception:
        return False, "Invalid JSON from RPC"
    err = data.get("error")
    if err:
        return False, str(err)
    h = data.get("result")
    return True, f"getblockcount OK (height={h})"


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify MN2 .env vs masternoder2.conf and optional RPC")
    ap.add_argument("--no-rpc", action="store_true", help="Skip getblockcount (file checks only)")
    args = ap.parse_args()

    _load_dotenv()
    conf_path = os.path.join(_ROOT, "config", "masternoder2.conf")
    conf = _parse_conf(conf_path)

    env_user = (os.environ.get("MN2_RPC_USER") or "").strip()
    env_pass = (os.environ.get("MN2_RPC_PASSWORD") or "").strip()

    print("MN2 production readiness")
    print(f"  config: {conf_path} ({'found' if conf else 'missing/empty'})")
    print(f"  MN2_RPC_USER set: {bool(env_user)}")
    print(f"  MN2_RPC_PASSWORD set: {bool(env_pass)}")
    print()

    issues = _check_match(conf, env_user, env_pass)
    for msg in issues:
        print(f"  [FAIL] {msg}")
    if issues:
        print("\nFix: follow docs/MN2_CONFIG_AND_PASSWORD_STEPS.md — same rpcuser/rpcpassword in .env and config/masternoder2.conf, then deploy config + mn2_env.")
        return 1

    print("  [OK] rpcuser and rpcpassword match between .env and config/masternoder2.conf")

    if args.no_rpc:
        print("\n  (--no-rpc: skipped live RPC test)")
        return 0

    ok, detail = _try_rpc()
    if ok:
        print(f"  [OK] RPC: {detail}")
        return 0
    print(f"  [FAIL] RPC: {detail}")
    print("\nIf files match but RPC fails: start masternoder2d on this host, or fix MN2_RPC_URL; see docs/MN2_DAEMON_SETUP.md")
    return 1


if __name__ == "__main__":
    sys.exit(main())
