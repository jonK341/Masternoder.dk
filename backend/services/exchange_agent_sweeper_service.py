"""Feature 7: sweep agent wallet alts into exchange_sales_pool."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_ops_service import load_config
from backend.services.exchange_sales_pool_service import load_config as load_sales_cfg, sales_pool_user_id, transfer_to_sales_pool

_STATE_PATH = os.path.join(ex._DATA_DIR, "agent_sweeper_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "agent_sweeper_ledger.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _asset_usd(symbol: str, amount: float) -> float:
    sym = (symbol or "").strip().upper()
    if sym == "MN2":
        return float(amount or 0) * ex._mn2_usd()
    return float(amount or 0) * ex._price_usd(sym)


def run_agent_sweeper(*, force: bool = False) -> Dict[str, Any]:
    cfg = load_config()
    sweep_cfg = cfg.get("sweeper") or {}
    if not sweep_cfg.get("enabled", True) and not force:
        return {"success": True, "skipped": True, "reason": "disabled"}

    min_usd = float(sweep_cfg.get("min_transfer_usd") or 10.0)
    sales_cfg = load_sales_cfg()
    agent_ids = list(sweep_cfg.get("source_agent_ids") or sales_cfg.get("source_agent_ids") or [])
    pool_uid = sales_pool_user_id()
    transfers: List[Dict[str, Any]] = []

    for agent_id in agent_ids:
        wallet = ex.get_wallet(agent_id)
        assets = wallet.get("assets") or {}
        for sym, raw_amt in assets.items():
            sym_u = str(sym).upper()
            if sym_u in ("USDT", "USDC"):
                continue
            amt = float(raw_amt or 0)
            usd = _asset_usd(sym_u, amt)
            if usd < min_usd:
                continue
            try:
                ex._adjust_balance(agent_id, sym_u, -amt)
                ex._adjust_balance(pool_uid, sym_u, amt)
                row = {
                    "ts": _iso(),
                    "from_agent": agent_id,
                    "to_pool": pool_uid,
                    "symbol": sym_u,
                    "amount": amt,
                    "usd_value": round(usd, 2),
                }
                ex._append_jsonl(_LEDGER_PATH, row)
                transfers.append(row)
            except Exception as exc:
                transfers.append({
                    "from_agent": agent_id,
                    "symbol": sym_u,
                    "success": False,
                    "error": str(exc),
                })

    sales_sweep = transfer_to_sales_pool(force=force)
    state = ex._read_json(_STATE_PATH, {})
    state["last_run_at"] = _iso()
    state["transfer_count"] = int(state.get("transfer_count") or 0) + len(transfers)
    ex._write_json(_STATE_PATH, state)

    return {
        "success": True,
        "agent_transfers": transfers,
        "sales_pool_sweep": sales_sweep,
        "transfer_count": len(transfers),
    }
