#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-deploy readiness bundle: RPC auth, optional reconcile, conservation gate, generation health.

  python scripts/verify_mn2_production_ready.py
  python scripts/verify_mn2_production_ready.py --no-rpc
  python scripts/verify_mn2_production_ready.py --with-reconcile --with-conservation --json-report
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


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


def _check_reconcile() -> tuple[bool, str, dict]:
    try:
        from backend.services.mn2_staking_reconcile_service import reconcile

        r = reconcile()
        ok = bool(r.get("ok"))
        detail = f"staking reconcile {'OK' if ok else 'FAIL: ' + ', '.join(r.get('failed_checks') or [])}"
        return ok, detail, r
    except Exception as e:
        return False, str(e), {}


def _check_conservation() -> tuple[bool, str, dict]:
    try:
        from backend.services.mn2_conservation_gate import conservation_gate

        r = conservation_gate()
        ok = r.get("verdict") == "green"
        detail = f"conservation gate verdict={r.get('verdict')}"
        return ok, detail, r
    except Exception as e:
        return False, str(e), {}


def _check_generation() -> tuple[bool, str, dict]:
    try:
        from backend.services.video_generator_service import _check_generation_services

        ok, msg, detail = _check_generation_services()
        return ok, msg or ("generation ready" if ok else "generation not ready"), detail
    except Exception as e:
        return False, str(e), {}


def _check_casino_tournaments() -> tuple[bool, str, dict]:
    try:
        from backend.services import casino_tournaments

        r = casino_tournaments.reconcile()
        ok = bool(r.get("ok", True))
        return ok, f"casino tournaments reconcile {'OK' if ok else 'FAIL'}", r
    except Exception as e:
        return False, str(e), {}


def main() -> int:
    ap = argparse.ArgumentParser(description="MN2 deploy readiness bundle")
    ap.add_argument("--no-rpc", action="store_true", help="Skip getblockcount")
    ap.add_argument("--with-reconcile", action="store_true", help="Run mn2_staking_reconcile")
    ap.add_argument("--with-conservation", action="store_true", help="Run full conservation gate")
    ap.add_argument("--with-generation-health", action="store_true", help="Check video generator preflight")
    ap.add_argument("--with-casino-invariant", action="store_true", help="Check casino tournament pools")
    ap.add_argument("--full", action="store_true", help="Enable all optional checks")
    ap.add_argument("--json-report", action="store_true", help="Write logs/deploy_readiness_<ts>.json")
    args = ap.parse_args()

    if args.full:
        args.with_reconcile = True
        args.with_conservation = True
        args.with_generation_health = True
        args.with_casino_invariant = True

    _load_dotenv()
    report: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": [],
        "ok": True,
    }

    conf_path = os.path.join(_ROOT, "config", "masternoder2.conf")
    conf = _parse_conf(conf_path)
    env_user = (os.environ.get("MN2_RPC_USER") or "").strip()
    env_pass = (os.environ.get("MN2_RPC_PASSWORD") or "").strip()

    print("MN2 deploy readiness bundle")
    print(f"  config: {conf_path} ({'found' if conf else 'missing/empty'})")
    print()

    issues = _check_match(conf, env_user, env_pass)
    for msg in issues:
        print(f"  [FAIL] rpc config: {msg}")
        report["checks"].append({"name": "rpc_config", "ok": False, "detail": msg})
    if issues:
        report["ok"] = False
        if args.json_report:
            _write_report(report)
        return 1

    print("  [OK] rpcuser/rpcpassword match .env and config/masternoder2.conf")
    report["checks"].append({"name": "rpc_config", "ok": True})

    if not args.no_rpc:
        ok, detail = _try_rpc()
        print(f"  {'[OK]' if ok else '[FAIL]'} RPC: {detail}")
        report["checks"].append({"name": "rpc_live", "ok": ok, "detail": detail})
        if not ok:
            report["ok"] = False
    else:
        print("  (--no-rpc: skipped live RPC)")
        report["checks"].append({"name": "rpc_live", "ok": True, "skipped": True})

    if args.with_reconcile:
        ok, detail, raw = _check_reconcile()
        print(f"  {'[OK]' if ok else '[FAIL]'} {detail}")
        report["checks"].append({"name": "staking_reconcile", "ok": ok, "detail": detail, "raw": raw})
        if not ok:
            report["ok"] = False

    if args.with_casino_invariant:
        ok, detail, raw = _check_casino_tournaments()
        print(f"  {'[OK]' if ok else '[FAIL]'} {detail}")
        report["checks"].append({"name": "casino_tournaments", "ok": ok, "detail": detail, "raw": raw})
        if not ok:
            report["ok"] = False

    if args.with_conservation:
        ok, detail, raw = _check_conservation()
        print(f"  {'[OK]' if ok else '[WARN/FAIL]'} {detail}")
        report["checks"].append({"name": "conservation_gate", "ok": ok, "detail": detail, "raw": raw})
        if not ok:
            report["ok"] = False

    if args.with_generation_health:
        ok, detail, raw = _check_generation()
        print(f"  {'[OK]' if ok else '[WARN]'} generation: {detail}")
        report["checks"].append({"name": "generation_health", "ok": ok, "detail": detail, "raw": raw})
        # generation health is warning-only for deploy exit code unless --full
        if not ok and args.full:
            report["ok"] = False

    if args.json_report:
        path = _write_report(report)
        print(f"\n  Report: {path}")

    if report["ok"]:
        print("\n  All required checks passed.")
        return 0
    print("\n  One or more checks failed.")
    return 1


def _write_report(report: dict) -> str:
    log_dir = os.path.join(_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(log_dir, f"deploy_readiness_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return path


if __name__ == "__main__":
    sys.exit(main())
