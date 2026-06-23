#!/usr/bin/env python3
"""Public check: masternode status + activetime from live API."""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "https://masternoder.dk"


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=45) as r:
        return json.loads(r.read())


def fmt_seconds(sec) -> str:
    try:
        s = int(sec)
    except (TypeError, ValueError):
        return str(sec)
    if s <= 0:
        return "0 (no ping)"
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{s}s (~{h}h {m}m)"


def _print_rpc_hint(payload: dict, *, label: str = "rpc_error") -> None:
    err = payload.get("rpc_error") or (payload.get("network") or {}).get("rpc_error")
    if err:
        print(f"  {label}: {err[:320]}")


def main() -> int:
    print("== On-chain masternodes (/api/mn2/masternodes) ==")
    net = get("/api/mn2/masternodes?fresh=1&limit=50")
    print(f"total={net.get('total')}  enabled={net.get('enabled')}")
    if int(net.get("total") or 0) == 0:
        _print_rpc_hint(net)
    active_zero = enabled_with_time = 0
    for i, x in enumerate(net.get("list") or [], 1):
        st = str(x.get("status") or "?").upper()
        act = x.get("activetime", 0)
        if st == "ACTIVE" and int(act or 0) == 0:
            active_zero += 1
        if st == "ENABLED":
            enabled_with_time += 1
        addr = str(x.get("addr") or "")[:42]
        print(
            f"  {i:2}. {st:8} activetime={fmt_seconds(act):>22}  "
            f"rank={x.get('rank')}  {addr}"
        )
    print(f"--- ACTIVE with activetime=0: {active_zero}  ENABLED: {enabled_with_time} ---")

    print("\n== Masternode service (/api/mn2/masternode/service) ==")
    svc = get("/api/mn2/masternode/service?fresh=1")
    network = svc.get("network") or {}
    daemon = svc.get("daemon") or {}
    print(
        f"network total={network.get('total')} enabled={network.get('enabled')}  "
        f"daemon mnsync={daemon.get('mnsync')} staking_active={daemon.get('staking_active')}"
    )
    if int(network.get("total") or 0) == 0:
        _print_rpc_hint(svc)

    print("\n== Scheduled activation (repo / server) ==")
    print("  cron: */2 * * * *  mn2_masternode_provision.sh  (retry paid slots, not ping)")
    print("  boot: mn2-fleet-autostart.service  (local + alias after masternoder2d)")
    print("  ping: daemon internal loop after startmasternode local + masternode=1")

    return 0


if __name__ == "__main__":
    sys.exit(main())
