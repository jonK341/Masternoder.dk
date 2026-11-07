"""Move agent treasury MN2 to the hosting preferred wallet and fund collateral UTXOs."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.services.mn2_masternode_service import get_config

TREASURY_POOL_USER = "agent_treasury"
DEFAULT_PREFERRED_USER = "user_jon_ulrik"


def preferred_wallet_user_id() -> str:
    cfg = get_config()
    ops = cfg.get("ops") if isinstance(cfg.get("ops"), dict) else {}
    uid = str(ops.get("preferred_wallet_user_id") or DEFAULT_PREFERRED_USER).strip()
    return uid or DEFAULT_PREFERRED_USER


def _mn2_balance(user_id: str) -> float:
    from backend.services.unified_points_database import unified_points_db

    pts = unified_points_db.get_all_points(user_id).get("points") or {}
    if not isinstance(pts, dict):
        return 0.0
    bal = float(pts.get("mn2_balance") or 0)
    if bal <= 0 and isinstance(pts.get("systems"), dict):
        bal = float(pts["systems"].get("mn2_balance") or 0)
    return round(bal, 8)


def transfer_agent_treasury_to_preferred(
    amount_mn2: float,
    *,
    dry_run: bool = False,
    dest_user_id: Optional[str] = None,
    reference: str = "",
) -> Dict[str, Any]:
    """Debit agent_treasury and credit the hosting preferred wallet (ledger-only, idempotent ref)."""
    amt = round(float(amount_mn2 or 0), 8)
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}

    dest = (dest_user_id or preferred_wallet_user_id()).strip()
    if not dest:
        return {"success": False, "error": "preferred_wallet_user_id missing"}
    if dest == TREASURY_POOL_USER:
        return {"success": False, "error": "destination_same_as_treasury"}

    ref = (reference or f"hosting-treasury-transfer:{dest}:{amt}").strip()
    src_bal = _mn2_balance(TREASURY_POOL_USER)
    dest_before = _mn2_balance(dest)

    out: Dict[str, Any] = {
        "success": True,
        "dry_run": dry_run,
        "from_user": TREASURY_POOL_USER,
        "to_user": dest,
        "amount_mn2": amt,
        "reference": ref,
        "treasury_before_mn2": src_bal,
        "preferred_before_mn2": dest_before,
    }

    if src_bal < amt:
        return {
            **out,
            "success": False,
            "error": "insufficient_treasury_pool",
            "treasury_before_mn2": src_bal,
        }

    if dry_run:
        out["treasury_after_mn2"] = round(src_bal - amt, 8)
        out["preferred_after_mn2"] = round(dest_before + amt, 8)
        return out

    from backend.services.mn2_ledger import append_entry
    from backend.services.unified_points_database import unified_points_db

    meta = {"reference": ref, "from_user": TREASURY_POOL_USER, "to_user": dest, "purpose": "hosting_collateral"}
    debit = unified_points_db.add_points(
        TREASURY_POOL_USER,
        "mn2_balance",
        -amt,
        source="hosting_treasury_transfer_out",
        metadata=meta,
    )
    if debit.get("duplicate"):
        out["duplicate"] = True
        out["treasury_after_mn2"] = _mn2_balance(TREASURY_POOL_USER)
        out["preferred_after_mn2"] = _mn2_balance(dest)
        return out

    if not debit.get("success", True):
        return {**out, "success": False, "error": debit.get("error", "debit_failed")}

    credit = unified_points_db.add_points(
        dest,
        "mn2_balance",
        amt,
        source="hosting_treasury_transfer_in",
        metadata=meta,
    )
    if not credit.get("success", True):
        unified_points_db.add_points(
            TREASURY_POOL_USER,
            "mn2_balance",
            amt,
            source="hosting_treasury_transfer_rollback",
            metadata={**meta, "rollback": True},
        )
        return {**out, "success": False, "error": credit.get("error", "credit_failed")}

    append_entry(TREASURY_POOL_USER, "withdrawal", amt, metadata={**meta, "internal": True})
    append_entry(dest, "deposit", amt, metadata={**meta, "internal": True})

    out["treasury_after_mn2"] = _mn2_balance(TREASURY_POOL_USER)
    out["preferred_after_mn2"] = _mn2_balance(dest)
    return out


def fund_collateral_utxos(
    slots: int,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Create up to ``slots`` new exactly-collateral-sized UTXOs in the ops daemon wallet."""
    n = max(0, int(slots or 0))
    if n <= 0:
        return {"success": True, "skipped": True, "reason": "slots_zero", "funded": 0}

    cfg = get_config()
    collateral = float(cfg.get("collateral_mn2") or 5000.0)

    from backend.services.mn2_masternode_service import list_collateral_outputs, _send_collateral_utxo

    before = list_collateral_outputs()
    free_before = int(before.get("count") or 0) if before.get("success") else 0

    if dry_run:
        from backend.services import mn2_rpc_client as rpc

        bal_r = rpc.getbalance()
        balance = float(bal_r.get("result") or 0) if not bal_r.get("error") else 0.0
        needed = collateral * n
        return {
            "success": balance >= needed,
            "dry_run": True,
            "slots_requested": n,
            "collateral_mn2": collateral,
            "daemon_balance_mn2": balance,
            "needed_mn2": needed,
            "free_collateral_outputs_before": free_before,
        }

    created: List[Dict[str, Any]] = []
    errors: List[str] = []
    for _ in range(n):
        row = _send_collateral_utxo(collateral)
        if row.get("success"):
            created.append({"txid": row.get("txid"), "address": row.get("address")})
        else:
            errors.append(str(row.get("error") or "send_failed"))
            break

    after = list_collateral_outputs()
    free_after = int(after.get("count") or 0) if after.get("success") else free_before

    return {
        "success": len(created) > 0 and not errors,
        "slots_requested": n,
        "funded": len(created),
        "collateral_mn2": collateral,
        "created": created,
        "errors": errors,
        "free_collateral_outputs_before": free_before,
        "free_collateral_outputs_after": free_after,
    }
