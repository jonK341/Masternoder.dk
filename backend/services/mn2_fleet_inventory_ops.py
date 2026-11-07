"""Platform fleet inventory: fund 5k collateral UTXOs and register hosts on-chain."""
from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

ProgressHook = Optional[Callable[[Dict[str, Any]], None]]

DEFAULT_HOST_PREFIX = "platform-mn"


def _emit(hook: ProgressHook, payload: Dict[str, Any]) -> None:
    if not hook:
        return
    try:
        hook(payload)
    except Exception:
        pass


def seed_platform_inventory_hosts(
    count: int,
    *,
    dry_run: bool = False,
    id_prefix: str = DEFAULT_HOST_PREFIX,
    owner_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Ensure ``count`` platform host rows exist (``queued``) for the provision pipeline."""
    from backend.services.mn2_masternode_service import (
        _count_slots_used,
        _load_hosts_doc,
        get_config,
        register_host,
    )

    target = max(0, int(count or 0))
    if target <= 0:
        return {"success": True, "skipped": True, "reason": "count_zero", "created": 0}

    cfg = get_config()
    max_nodes = int(cfg.get("max_hosted_nodes") or 500)
    doc = _load_hosts_doc()
    hosts: List[Dict[str, Any]] = list(doc.get("hosts") or [])
    existing_ids = {
        str(h.get("id") or "").strip()
        for h in hosts
        if isinstance(h, dict) and str(h.get("id") or "").strip()
    }
    slots_used = _count_slots_used(hosts)
    room = max(0, max_nodes - slots_used)

    planned: List[str] = []
    for i in range(1, target + 1):
        hid = f"{id_prefix}-{i}"
        if hid not in existing_ids:
            planned.append(hid)

    if dry_run:
        return {
            "success": room >= len(planned) or len(planned) == 0,
            "dry_run": True,
            "target_hosts": target,
            "would_create": len(planned),
            "slots_used": slots_used,
            "max_hosted_nodes": max_nodes,
            "slots_room": room,
        }

    created = 0
    errors: List[str] = []
    for hid in planned:
        if _count_slots_used(hosts) >= max_nodes:
            errors.append("max_hosted_nodes_reached")
            break
        row = register_host(
            {
                "id": hid,
                "label": f"Platform inventory {hid}",
                "status": "queued",
                "owner_user_id": owner_user_id,
                "notes": "Platform fleet inventory — auto-provision on-chain",
            }
        )
        if not row.get("success"):
            errors.append(f"{hid}:{row.get('error')}")
            break
        hosts.append(row.get("host") or {})
        created += 1

    return {
        "success": created == len(planned) and not errors,
        "target_hosts": target,
        "created": created,
        "skipped_existing": target - len(planned),
        "errors": errors,
        "hosted_count": _count_slots_used(hosts),
    }


def bootstrap_platform_fleet(
    target_collateral_utxos: int = 500,
    *,
    dry_run: bool = False,
    fund_only: bool = False,
    provision_only: bool = False,
    provision_batch: int = 50,
    max_provision_rounds: int = 400,
    unlock_every: int = 15,
    progress_hook: ProgressHook = None,
    progress_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fund up to ``target_collateral_utxos`` free 5k MN2 outputs, seed platform-mn-* hosts,
    and drain provisioning until nodes are on ``masternode.conf`` (and broadcast when confirmed).
    """
    from backend.services.mn2_hosting_treasury_ops import fund_collateral_utxos
    from backend.services.mn2_masternode_service import (
        activate_all_rented_masternodes,
        get_service_status,
        list_collateral_outputs,
        process_pending_hosts,
        rented_masternodes_snapshot,
    )

    target = max(0, int(target_collateral_utxos or 0))
    out: Dict[str, Any] = {
        "success": True,
        "target_collateral_utxos": target,
        "dry_run": dry_run,
        "fund": None,
        "seed": None,
        "provision_rounds": [],
        "activation": None,
        "status_before": get_service_status(fresh=True),
    }

    col = list_collateral_outputs()
    free = int(col.get("count") or 0) if col.get("success") else 0
    gap = max(0, target - free)
    out["collateral_free_before"] = free
    out["collateral_gap"] = gap

    def persist() -> None:
        if not progress_path:
            return
        try:
            os.makedirs(os.path.dirname(progress_path) or ".", exist_ok=True)
            with open(progress_path, "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=2)
        except OSError:
            pass

    if not provision_only:
        _emit(progress_hook, {"phase": "fund", "gap": gap, "free_before": free})
        fund_n = gap if fund_only or gap > 0 else 0
        if fund_n > 0 or dry_run:
            out["fund"] = fund_collateral_utxos(
                fund_n,
                dry_run=dry_run,
                unlock_every=unlock_every,
            )
        else:
            out["fund"] = {"success": True, "skipped": True, "reason": "already_at_target"}

    if dry_run and not provision_only:
        snap = rented_masternodes_snapshot()
        pending = len(snap.get("pending") or [])
        out["seed"] = seed_platform_inventory_hosts(
            target,
            dry_run=True,
        )
        out["note"] = "Dry-run only — no collateral sends or host writes."
        out["pending_hosts_before"] = pending
        persist()
        return out

    if fund_only:
        out["status_after"] = get_service_status(fresh=True)
        persist()
        return out

    _emit(progress_hook, {"phase": "seed", "target_hosts": target})
    out["seed"] = seed_platform_inventory_hosts(target, dry_run=False)

    batch = max(1, int(provision_batch or 50))
    rounds = max(1, int(max_provision_rounds or 1))
    for rnd in range(rounds):
        snap = rented_masternodes_snapshot()
        pending = snap.get("pending") or []
        if not pending:
            break
        _emit(
            progress_hook,
            {"phase": "provision", "round": rnd + 1, "pending": len(pending)},
        )
        try:
            batch_out = process_pending_hosts(limit=batch, skip_explorer=True, skip_ping=True)
        except Exception as exc:
            out["success"] = False
            out["error"] = str(exc)[:300]
            persist()
            return out
        round_info = {
            "round": rnd + 1,
            "pending_before": len(pending),
            "processed": int(batch_out.get("processed") or 0),
            "waiting_confirmations": batch_out.get("waiting_confirmations"),
        }
        out["provision_rounds"].append(round_info)
        persist()
        processed = int(batch_out.get("processed") or 0)
        if processed == 0:
            # Usually waiting for min collateral confirmations.
            time.sleep(30)
            continue
        time.sleep(3)

    _emit(progress_hook, {"phase": "activate"})
    out["activation"] = activate_all_rented_masternodes(
        batch_size=batch,
        max_rounds=min(rounds, 80),
        skip_explorer=True,
        progress_hook=progress_hook,
    )

    out["status_after"] = get_service_status(fresh=True)
    col2 = list_collateral_outputs()
    out["collateral_free_after"] = int(col2.get("count") or 0) if col2.get("success") else None
    persist()
    return out
