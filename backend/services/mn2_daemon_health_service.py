"""MN2 daemon (masternoder2d) health probes for cron, agents, and ops."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _log_probe(payload: Dict[str, Any]) -> str:
    d = os.path.join(BASE_DIR, "logs", "mn2_daemon")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "health_probes.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path


def probe_daemon(*, extended: bool = False) -> Dict[str, Any]:
    """
    Test masternoder2d RPC: block height, connections, wallet, mempool.
    Never raises; suitable for cron and agent settlement.
    """
    from backend.services.mn2_rpc_client import health_check, getconnectioncount, getwalletinfo

    out: Dict[str, Any] = {
        "success": True,
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "rpc_url_set": bool((os.environ.get("MN2_RPC_URL") or "").strip()),
    }
    hc = health_check()
    out["health"] = hc
    out["healthy"] = hc.get("status") == "healthy"

    if extended and out["healthy"]:
        try:
            cc = getconnectioncount()
            if not cc.get("error"):
                out["connections"] = cc.get("result")
        except Exception:
            pass
        try:
            wi = getwalletinfo()
            if not wi.get("error") and isinstance(wi.get("result"), dict):
                res = wi["result"]
                out["wallet"] = {
                    "balance": res.get("balance"),
                    "unconfirmed_balance": res.get("unconfirmed_balance"),
                    "txcount": res.get("txcount"),
                }
        except Exception:
            pass

    if not out["healthy"]:
        out["success"] = False
        out["error"] = hc.get("error") or hc.get("status")

    _log_probe(out)
    return out
