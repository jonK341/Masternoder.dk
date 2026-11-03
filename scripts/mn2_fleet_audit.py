#!/usr/bin/env python3
"""
Audit masternode.conf vs hosting registry vs listmasternodes; optional provision or purge.

Run on the server from /var/www/html (RPC + data/mn2_masternode_hosts.json):

  python3 scripts/mn2_fleet_audit.py
  python3 scripts/mn2_fleet_audit.py --provision --limit 80
  python3 scripts/mn2_fleet_audit.py --purge-stale --apply
  python3 scripts/mn2_fleet_audit.py --remove-orphan-registry --apply

Default is read-only. Use --apply on destructive actions after reviewing dry-run output.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Set

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

from backend.services import mn2_masternode_service as mn  # noqa: E402


def _conf_aliases() -> List[str]:
    out: List[str] = []
    for row in mn._read_masternode_conf_entries():
        if row.get("kind") == "entry" and row.get("valid"):
            out.append(str(row["alias"]))
    return out


def _registry_alias_map(hosts: List[Dict[str, Any]]) -> Dict[str, str]:
    """host_id -> expected masternode.conf alias."""
    return {str(h.get("id")): mn._alias_from_host_id(str(h.get("id"))) for h in hosts if h.get("id")}


def _chain_rows() -> List[Dict[str, Any]]:
    net = mn.network_masternodes(limit=200, fresh=True)
    rows = net.get("list")
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)]


def audit() -> Dict[str, Any]:
    wait = mn._wait_for_rpc_ready()
    rpc_ok = wait is None
    aliases = _conf_aliases()
    hosts = mn.list_hosts(include_internal=True)
    by_status = Counter((h.get("status") or "unknown").lower() for h in hosts)
    reg_map = _registry_alias_map(hosts)
    reg_aliases: Set[str] = set(reg_map.values())
    conf_only = sorted(set(aliases) - reg_aliases)
    reg_only = sorted(reg_aliases - set(aliases))

    chain = _chain_rows() if rpc_ok else []
    chain_by_status = Counter(str(r.get("status") or "?").upper() for r in chain)
    enabled_rising = sum(
        1 for r in chain
        if str(r.get("status") or "").upper() == "ENABLED" and int(r.get("activetime") or 0) > 0
    )

    orphan_registry: List[str] = []
    for h in hosts:
        hid = str(h.get("id") or "")
        if not hid:
            continue
        st = (h.get("status") or "").lower()
        owner = (h.get("owner_user_id") or "").strip()
        if st == "provisioning" and not h.get("collateral_txid") and not owner:
            orphan_registry.append(hid)

    return {
        "rpc_ok": rpc_ok,
        "rpc_wait_error": wait,
        "masternode_conf_aliases": len(aliases),
        "registry_hosts": len(hosts),
        "registry_by_status": dict(by_status),
        "chain_total": len(chain),
        "chain_by_status": dict(chain_by_status),
        "enabled_with_activetime": enabled_rising,
        "conf_only_aliases": conf_only[:50],
        "conf_only_count": len(conf_only),
        "registry_alias_missing_from_conf": reg_only[:50],
        "registry_alias_missing_count": len(reg_only),
        "orphan_registry_ids": orphan_registry[:50],
        "orphan_registry_count": len(orphan_registry),
        "collateral_outputs": mn.list_collateral_outputs(),
        "service_status": mn.get_service_status(fresh=True) if rpc_ok else None,
    }


def provision_loop(limit: int, passes: int) -> List[Dict[str, Any]]:
    mn._unlock_wallet()
    mn._unlock_collateral_utxos()
    results: List[Dict[str, Any]] = []
    for i in range(max(1, passes)):
        results.append({"pass": i + 1, **mn.process_pending_hosts(limit=limit, skip_explorer=True)})
    results.append({"action": "bring_online", **mn.bring_rented_masternodes_online(limit=limit)})
    results.append({"action": "sync_ping", **mn.sync_ping_targets()})
    return results


def purge_stale(apply: bool, force_no_collateral: bool) -> Dict[str, Any]:
    cfg = mn.get_config()
    hours = float(cfg.get("stale_provisioning_hours") or 6)
    return mn.purge_stale_provisioning_hosts(
        max_age_hours=hours,
        force_no_collateral=force_no_collateral,
        dry_run=not apply,
    )


def remove_orphan_registry(apply: bool) -> Dict[str, Any]:
    report = audit()
    removed: List[str] = []
    for hid in report.get("orphan_registry_ids") or []:
        if apply:
            out = mn.remove_host(hid)
            if out.get("success"):
                removed.append(hid)
        else:
            removed.append(hid)
    out: Dict[str, Any] = {"dry_run": not apply, "count": len(removed)}
    out["removed" if apply else "would_remove"] = removed
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Audit MN2 fleet; provision or purge orphan registry rows")
    p.add_argument("--provision", action="store_true", help="Run provision-pending + bring-online + sync-ping")
    p.add_argument("--limit", type=int, default=80, help="Hosts per provision pass")
    p.add_argument("--passes", type=int, default=3, help="provision-pending repetitions")
    p.add_argument("--purge-stale", action="store_true", help="Drop old provisioning rows with no collateral")
    p.add_argument("--force-purge", action="store_true", help="Purge all no-collateral provisioning (any age)")
    p.add_argument("--remove-orphan-registry", action="store_true", help="Remove registry rows: provisioning, no collateral, no owner")
    p.add_argument("--apply", action="store_true", help="Execute purge/remove (default dry-run for those)")
    args = p.parse_args()

    report = audit()
    print(json.dumps(report, indent=2, default=str)[:120000])

    rc = 0
    if not report.get("rpc_ok"):
        print("\nWARN: RPC not ready — provision skipped until masternoder2d answers.", file=sys.stderr)
        rc = 1

    if args.provision:
        if not report.get("rpc_ok"):
            return rc
        print("\n== provision ==")
        prov = provision_loop(args.limit, args.passes)
        print(json.dumps(prov, indent=2, default=str)[:80000])
        print("\n== post-audit ==")
        print(json.dumps(audit(), indent=2, default=str)[:80000])

    if args.purge_stale:
        print("\n== purge-stale ==")
        print(json.dumps(purge_stale(args.apply, args.force_purge), indent=2))

    if args.remove_orphan_registry:
        print("\n== remove-orphan-registry ==")
        print(json.dumps(remove_orphan_registry(args.apply), indent=2))

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
