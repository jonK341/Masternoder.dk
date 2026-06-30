"""Stash trading-bot profit on the MasterNoder exchange (platform treasury wallet).

Converts realized USD P&L into MN2 (or shop coins) and credits the configured
``treasury_user_id`` custodial wallet — the on-platform profit pile.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.services import crypto_exchange_service as ex

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_treasury_config.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "treasury_stash_ledger.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def treasury_user_id() -> str:
    return str(load_config().get("treasury_user_id") or "platform_treasury")


def stash_profit_usd(
    amount_usd: float,
    *,
    source: str,
    agent_id: str = "",
    mode: str = "paper",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Credit platform treasury on MasterNoder exchange."""
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "treasury_disabled"}
    amount_usd = float(amount_usd or 0)
    if amount_usd < float(cfg.get("min_stash_usd") or 0.01):
        return {"success": True, "skipped": True, "reason": "below_min", "amount_usd": amount_usd}

    uid = treasury_user_id()
    quote = str(cfg.get("stash_quote") or "MN2").upper()
    mn2_usd = max(ex._mn2_usd(), 1e-9)

    try:
        if quote == "MN2":
            mn2_amt = round(amount_usd / mn2_usd, 8)
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(
                uid,
                "mn2_balance",
                mn2_amt,
                source=source,
                metadata={
                    "reference": f"treasury-stash:{source}:{agent_id}",
                    "amount_usd": amount_usd,
                    "mode": mode,
                    **(meta or {}),
                },
            )
            credited = {"quote": "MN2", "amount": mn2_amt}
        elif quote == "COINS":
            from backend.services.unified_points_database import unified_points_db
            mn2_cfg = ex._read_json(os.path.join(ex._BASE, "data", "mn2_config.json"), {})
            cpm = float(mn2_cfg.get("coins_per_mn2") or 100)
            coins = round(amount_usd / mn2_usd * cpm, 2)
            unified_points_db.add_points(
                uid,
                "coins",
                coins,
                source=source,
                metadata={"reference": f"treasury-stash:{source}", "amount_usd": amount_usd, "mode": mode},
            )
            credited = {"quote": "COINS", "amount": coins}
        else:
            return {"success": False, "error": "unsupported_stash_quote"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    row = {
        "ts": _iso(),
        "treasury_user_id": uid,
        "amount_usd": round(amount_usd, 6),
        "credited": credited,
        "source": source,
        "agent_id": agent_id,
        "mode": mode,
    }
    ex._append_jsonl(_LEDGER_PATH, row)
    ex._audit("treasury_stash", user_id=uid, amount_usd=amount_usd, source=source,
              agent_id=agent_id, mode=mode, credited=credited)

    if bool(cfg.get("auto_paypal_sweep", True)):
        try:
            from backend.services.exchange_payout_service import payout_status, execute_sweep
            st = payout_status()
            if st.get("ready_to_sweep") and st.get("destination") == "paypal":
                execute_sweep()
        except Exception:
            pass

    return {"success": True, **row}


def treasury_status(mode: Optional[str] = None) -> Dict[str, Any]:
    cfg = load_config()
    uid = treasury_user_id()
    from backend.services.unified_points_database import unified_points_db
    pts = (unified_points_db.get_all_points(uid).get("points") or {})
    wallet = ex.get_wallet(uid)
    ledger_rows = 0
    stashed_usd = 0.0
    stashed_paper_usd = 0.0
    stashed_live_usd = 0.0
    mode_filter = (mode or "").strip().lower() or None
    if os.path.isfile(_LEDGER_PATH):
        try:
            with open(_LEDGER_PATH, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    import json
                    row = json.loads(line)
                    row_mode = str(row.get("mode") or "paper").lower()
                    amount = float(row.get("amount_usd") or 0)
                    if mode_filter and row_mode != mode_filter:
                        continue
                    ledger_rows += 1
                    stashed_usd += amount
                    if row_mode == "live":
                        stashed_live_usd += amount
                    else:
                        stashed_paper_usd += amount
        except Exception:
            pass
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "treasury_user_id": uid,
        "stash_quote": cfg.get("stash_quote"),
        "auto_stash_on_trade": bool(cfg.get("auto_stash_on_trade", True)),
        "daemon_mesh_enabled": bool(cfg.get("daemon_mesh_enabled", True)),
        "mn2_balance": float(pts.get("mn2_balance") or 0),
        "coins": float(pts.get("coins") or 0),
        "exchange_assets": wallet.get("assets") or {},
        "ledger_entries": ledger_rows,
        "ledger_stashed_usd": round(stashed_usd, 4),
        "ledger_stashed_usd_paper": round(stashed_paper_usd, 4),
        "ledger_stashed_usd_live": round(stashed_live_usd, 4),
        "mode_filter": mode_filter,
        "fee_allocation": cfg.get("fee_allocation") if isinstance(cfg.get("fee_allocation"), dict) else {},
    }
