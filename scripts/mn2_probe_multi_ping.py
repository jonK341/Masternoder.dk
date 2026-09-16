#!/usr/bin/env python3
"""
Probe fleet multi-ping readiness: daemon version, ENABLED+activetime counts, optional RPC register.

Usage (server with RPC in .env):
  python scripts/mn2_probe_multi_ping.py
  python scripts/mn2_probe_multi_ping.py --register   # startmasternode all false (v1.3+)
  python scripts/mn2_probe_multi_ping.py --public     # public API only (no RPC)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE = os.environ.get("MN2_TEST_BASE", "https://masternoder.dk")


def public_snapshot() -> dict:
    import urllib.request

    with urllib.request.urlopen(f"{BASE}/api/mn2/masternode/service?fresh=1", timeout=45) as r:
        svc = json.loads(r.read())
    with urllib.request.urlopen(f"{BASE}/api/mn2/masternodes?fresh=1&limit=80", timeout=45) as r:
        net = json.loads(r.read())
    rows = net.get("list") or []
    enabled = [x for x in rows if str(x.get("status", "")).upper() == "ENABLED"]
    enabled_rising = [x for x in enabled if int(x.get("activetime") or 0) > 0]
    active_zero = sum(
        1
        for x in rows
        if str(x.get("status", "")).upper() == "ACTIVE" and int(x.get("activetime") or 0) == 0
    )
    daemon = svc.get("daemon") or {}
    return {
        "daemon_version": daemon.get("version"),
        "multi_ping_capable": daemon.get("multi_ping_capable"),
        "multi_ping_enabled": daemon.get("multi_ping_enabled"),
        "enabled_with_activetime": daemon.get("enabled_with_activetime"),
        "network_enabled": net.get("enabled"),
        "enabled_rows": len(enabled),
        "enabled_rising": len(enabled_rising),
        "active_activetime_zero": active_zero,
        "hosted": svc.get("hosted_count"),
        "platform_enabled_on_chain": svc.get("platform_enabled_on_chain"),
    }


def rpc_snapshot(register: bool) -> dict:
    from backend.services import mn2_masternode_service as mn
    from backend.services import mn2_rpc_client as rpc

    info = rpc.getinfo()
    ver = (info.get("result") or {}).get("version")
    out = {
        "rpc_ok": not info.get("error"),
        "version": ver,
        "multi_ping_capable": mn.daemon_supports_multi_ping(),
        "multi_ping_enabled": mn.multi_ping_enabled(),
    }
    if register and mn.multi_ping_enabled():
        mn._unlock_wallet()
        mn._unlock_collateral_utxos()
        r = rpc.startmasternode("all", False)
        out["register_all"] = {
            "error": r.get("error"),
            "result": r.get("result"),
        }
    elif register:
        out["register_all"] = {"skipped": True, "reason": "multi_ping not enabled or daemon < 1.3"}
    net = mn.network_masternodes(limit=80, fresh=True)
    rows = net.get("list") if isinstance(net.get("list"), list) else []
    out["enabled_with_activetime"] = mn._count_enabled_with_activetime(rows)
    out["network_enabled"] = net.get("enabled")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Probe MN2 fleet multi-ping readiness")
    p.add_argument("--public", action="store_true", help="Public API only (no local RPC)")
    p.add_argument("--register", action="store_true", help="RPC startmasternode all false (v1.3+)")
    args = p.parse_args()

    print("== MN2 multi-ping probe ==")
    if args.public:
        snap = public_snapshot()
        print(json.dumps(snap, indent=2))
    else:
        try:
            snap = rpc_snapshot(register=args.register)
            print(json.dumps(snap, indent=2))
        except Exception as exc:
            print(f"RPC probe failed: {exc}", file=sys.stderr)
            print("(try --public for live site API)", file=sys.stderr)
            return 1

    capable = bool(snap.get("multi_ping_capable"))
    enabled_flag = bool(snap.get("multi_ping_enabled"))
    rising = int(snap.get("enabled_rising") or snap.get("enabled_with_activetime") or 0)
    net_en = int(snap.get("network_enabled") or 0)

    print("\n== Assessment ==")
    if not capable:
        print("BLOCKED: daemon < v1.3.0 — build/deploy MasterNoder2 multi-ping binary first.")
        return 2
    if not enabled_flag:
        print("READY: v1.3+ detected — set ops.multi_ping_enabled=true after QA.")
        return 0
    if rising >= max(1, net_en - 1):
        print(f"PASS: multi-ping active ({rising} ENABLED with activetime > 0).")
        return 0
    print(f"WARN: multi-ping enabled but only {rising}/{net_en} ENABLED have activetime — run --register or alias start.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
