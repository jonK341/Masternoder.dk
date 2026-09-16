"""Agent treasury cold-wallet sign-off (MN2_OPS §8.6).

Records named approver + checklist before batch agent funding (600k MN2 / 6×100k).
Distribution via distribute_agent_funding() is blocked until sign-off is on file.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SIGNOFF_FILE = os.path.join(_BASE, "data", "treasury_signoff.json")
_BATCH_THRESHOLD_MN2 = 100_000.0
_MAX_BATCH_MN2 = 600_000.0


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read() -> Dict[str, Any]:
    if not os.path.isfile(_SIGNOFF_FILE):
        return {}
    try:
        with open(_SIGNOFF_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_SIGNOFF_FILE), exist_ok=True)
    tmp = _SIGNOFF_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _SIGNOFF_FILE)


def reconcile_snapshot() -> Dict[str, Any]:
    """Best-effort pre-sign-off reconcile (ledger + optional RPC + staking conservation)."""
    out: Dict[str, Any] = {"ts": _iso(), "ok": True, "checks": []}
    root = _BASE
    ledger_path = os.path.join(root, "data", "mn2_ledger.json")
    try:
        if os.path.isfile(ledger_path):
            with open(ledger_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data.get("entries", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            dep = sum(float(e.get("amount") or 0) for e in entries if e.get("type") == "deposit")
            wdr = sum(float(e.get("amount") or 0) for e in entries if e.get("type") == "withdrawal")
            shop = sum(float(e.get("amount") or 0) for e in entries if e.get("type") == "shop_payment")
            ledger_net = round(dep - wdr - shop, 8)
            out["ledger_net_mn2"] = ledger_net
            out["checks"].append({"name": "ledger_loaded", "ok": True})
        else:
            out["checks"].append({"name": "ledger_loaded", "ok": False, "error": "missing ledger"})
            out["ok"] = False
    except Exception as exc:
        out["checks"].append({"name": "ledger_loaded", "ok": False, "error": str(exc)})
        out["ok"] = False

    try:
        from backend.services.mn2_rpc_client import getbalance
        r = getbalance()
        if r.get("error"):
            out["checks"].append({"name": "daemon_balance", "ok": False, "error": r.get("error")})
        else:
            wallet = float(r.get("result") or 0)
            out["wallet_balance_mn2"] = wallet
            ln = out.get("ledger_net_mn2")
            if ln is not None and abs(float(ln) - wallet) > 0.0001:
                out["checks"].append({
                    "name": "ledger_wallet_match",
                    "ok": False,
                    "diff": round(float(ln) - wallet, 8),
                })
                out["ok"] = False
            else:
                out["checks"].append({"name": "ledger_wallet_match", "ok": True})
    except Exception as exc:
        out["checks"].append({"name": "daemon_balance", "ok": False, "error": str(exc)})

    try:
        from backend.services.mn2_staking_reconcile_service import reconcile
        rep = reconcile()
        staking_ok = bool(rep.get("ok"))
        out["staking_conservation_ok"] = staking_ok
        out["checks"].append({"name": "staking_conservation", "ok": staking_ok})
        if not staking_ok:
            out["ok"] = False
            out["staking_failed"] = rep.get("failed_checks")
    except Exception as exc:
        out["checks"].append({"name": "staking_conservation", "ok": False, "error": str(exc)})

    return out


def get_signoff() -> Dict[str, Any]:
    with _LOCK:
        data = _read()
    if not data.get("signed"):
        return {"success": True, "signed": False, "signoff": None}
    return {"success": True, "signed": True, "signoff": data}


def is_signed_off() -> bool:
    return bool(_read().get("signed"))


def record_signoff(
    *,
    approver: str,
    cold_wallet_address: str,
    hot_cap_mn2: Optional[float] = None,
    max_batch_mn2: float = _MAX_BATCH_MN2,
    notes: str = "",
    require_reconcile_ok: bool = False,
) -> Dict[str, Any]:
    """Record treasury cold-wallet sign-off. Idempotent replace of prior sign-off."""
    approver = (approver or "").strip()
    cold = (cold_wallet_address or "").strip()
    if not approver:
        return {"success": False, "error": "approver required"}
    if not cold:
        return {"success": False, "error": "cold_wallet_address required"}

    cold_valid = None
    try:
        from backend.services.mn2_rpc_client import validateaddress
        r = validateaddress(cold)
        if not r.get("error") and isinstance(r.get("result"), dict):
            res = r["result"]
            if res.get("isvalid") and res.get("ismine") is False:
                cold_valid = True
            elif res.get("isvalid") and res.get("ismine") is True:
                return {
                    "success": False,
                    "error": "cold_wallet_address must not be owned by the hot server wallet (ismine=false)",
                }
            elif not res.get("isvalid"):
                return {"success": False, "error": "cold_wallet_address invalid per daemon"}
    except Exception:
        cold_valid = None  # RPC down — allow with warning

    snap = reconcile_snapshot()
    if require_reconcile_ok and not snap.get("ok"):
        return {"success": False, "error": "reconcile_not_green", "reconcile": snap}

    from backend.services.agent_wallet_service import get_treasury, get_treasury_pool_balance
    treasury = get_treasury()

    row = {
        "signed": True,
        "approver": approver,
        "signed_at": _iso(),
        "cold_wallet_address": cold,
        "cold_wallet_validated_off_hot": cold_valid,
        "hot_cap_mn2": float(hot_cap_mn2) if hot_cap_mn2 is not None else None,
        "max_batch_mn2": float(max_batch_mn2),
        "treasury_hot_address": treasury.get("address"),
        "treasury_pool_balance_mn2": get_treasury_pool_balance(),
        "per_agent_mn2": treasury.get("per_agent_mn2") or 100000,
        "trader_agent_count": treasury.get("trader_agent_count") or 6,
        "notes": (notes or "").strip(),
        "reconcile_snapshot": snap,
        "checklist": {
            "reconcile_green": snap.get("ok"),
            "cold_wallet_recorded": True,
            "hot_balance_within_cap": True if hot_cap_mn2 is None else get_treasury_pool_balance() <= float(hot_cap_mn2),
            "backup_reminder": "Operator confirms stakes/ledger backup taken",
            "named_approver": True,
        },
    }

    with _LOCK:
        _write(row)

    try:
        from backend.services.admin_audit_service import log_action
        log_action(
            "treasury_cold_wallet_signoff",
            actor=approver,
            payload={
                "cold_wallet_prefix": cold[:12],
                "max_batch_mn2": max_batch_mn2,
                "reconcile_ok": snap.get("ok"),
            },
        )
    except Exception:
        pass

    return {"success": True, "signoff": row}


def assert_distribution_allowed(*, estimated_total_mn2: float) -> Optional[str]:
    """Return error message if distribute must not proceed, else None."""
    if estimated_total_mn2 <= 0:
        return None
    if estimated_total_mn2 > _MAX_BATCH_MN2:
        return f"batch exceeds max {_MAX_BATCH_MN2} MN2"
    if estimated_total_mn2 >= _BATCH_THRESHOLD_MN2 and not is_signed_off():
        return "treasury_signoff_required — POST /api/agents/treasury/sign-off before batch ≥100k MN2"
    if is_signed_off():
        signoff = _read()
        cap = signoff.get("max_batch_mn2")
        if cap is not None and estimated_total_mn2 > float(cap):
            return f"batch exceeds signed max_batch_mn2 ({cap})"
    return None
