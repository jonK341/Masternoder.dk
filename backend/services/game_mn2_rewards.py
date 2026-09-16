"""Unified MN2 reward path for game, battle, quests, and starmap."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services.activity_events_service import emit


def credit_mn2(
    user_id: str,
    amount: float,
    *,
    source: str,
    reference: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err}
    user_id = uid_or_err
    amt = float(amount or 0)
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}

    meta = dict(metadata or {})
    meta["reference"] = reference
    meta["source"] = source

    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    chain_txid = None
    chain_address = None
    try:
        from backend.services.mn2_chain_rewards_service import chain_payouts_enabled, payout_reward_on_chain

        if chain_payouts_enabled():
            chain_res = payout_reward_on_chain(
                user_id,
                amt,
                source=source,
                reference=reference,
                metadata=meta,
            )
            if chain_res.get("txid"):
                chain_txid = chain_res["txid"]
                chain_address = chain_res.get("address")
                meta["chain_paid"] = True
                meta["chain_txid"] = chain_txid
    except Exception:
        pass

    result = unified_points_db.add_points(
        user_id, "mn2_balance", amt, source=source, metadata=meta,
    )
    if not result.get("success"):
        return result
    if result.get("duplicate"):
        return result

    ledger_txid = chain_txid or reference
    append_entry(
        user_id=user_id,
        entry_type=source,
        amount=amt,
        txid=ledger_txid,
        address=chain_address,
        metadata=meta,
    )
    emit(
        "game_mn2_reward",
        user_id=user_id,
        channel="game",
        text=f"+{amt} MN2 ({source})",
        payload={"amount": amt, "source": source, "reference": reference, "chain_txid": chain_txid},
    )

    out = {"success": True, "amount": amt, "user_id": user_id, "source": source, "instant": True}
    if chain_txid:
        out["chain_txid"] = chain_txid
        out["on_chain"] = True
    return out
