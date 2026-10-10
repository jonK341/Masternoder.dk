"""Fire-and-forget micro-tx rewards from monetization flows."""
from __future__ import annotations

from typing import Any, Dict, Optional

# Internal credit sources -> micro-tx config source keys (data/mn2_micro_tx_config.json)
_MICRO_TX_SOURCE_MAP: Dict[str, str] = {
    "trophy_quest": "quest_complete",
    "quest_claim_streak": "quest_complete",
    "progression_quest": "quest_complete",
    "quest_reward": "quest_complete",
    "trophy_unlock": "quest_complete",
    "trophy_income": "staking_accrual",
    "battle": "game_win",
    "battle_win": "game_win",
    "battle_victory": "game_win",
    "battle_crypto_claim": "game_win",
    "starmap": "game_win",
    "starmap_claim": "game_win",
    "casino_spin": "casino_spin",
    "casino_win": "game_win",
    "game_win": "game_win",
    "shop_purchase": "shop_purchase",
    "shop_discord_promo": "shop_purchase",
    "mn2_shop_purchase": "shop_purchase",
    "referral_purchase_reward": "referral",
    "casino_referral": "referral",
    "creator_rating": "creator_rating",
    "creator_rating_earn": "creator_rating",
    "staking_reward": "staking_accrual",
    "mn2_staking_reward": "staking_accrual",
    "aggregator_mn2_earn": "aggregator_action",
    "podcast_listen": "aggregator_action",
    "compendium_read": "aggregator_action",
    "daily_login": "daily_login",
}

_MICRO_TX_BLOCK_CODES = frozenset({
    "daily_cap", "rate_limit", "source_denied", "auth_required", "disabled",
    "below_min", "above_max", "invalid_amount",
})


def _normalize_key(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "_").replace("-", "_")


def resolve_micro_tx_source(source: str) -> Optional[str]:
    """Map an internal MN2 credit source to a micro-tx allowed source, if any."""
    key = _normalize_key(source)
    if key in _MICRO_TX_SOURCE_MAP:
        return _MICRO_TX_SOURCE_MAP[key]
    try:
        from backend.services.mn2_micro_tx_service import get_config

        allowed = {_normalize_key(s) for s in (get_config().get("allowed_sources") or [])}
        if key in allowed:
            return key
    except Exception:
        pass
    return None


def try_micro_tx_reward(
    user_id: str,
    source: str,
    *,
    idempotency_key: Optional[str] = None,
    reason: str = "",
    amount_mn2: Optional[float] = None,
    metadata: Optional[dict] = None,
) -> Optional[Dict[str, Any]]:
    """Credit instant MN2 micro-reward; returns payout dict on success, else None."""
    uid = str(user_id or "").strip()
    if not uid:
        return None
    try:
        from backend.services.mn2_micro_tx_service import instant_payout

        result = instant_payout(
            user_id=uid,
            amount_mn2=amount_mn2,
            reason=reason,
            source=source,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )
        if result.get("success"):
            return result
    except Exception:
        pass
    return None


def _amount_fits_micro_tx(amount_mn2: Optional[float]) -> bool:
    try:
        from backend.services.mn2_micro_tx_service import get_config

        cfg = get_config()
        min_amt = float(cfg.get("min_amount_mn2") or 0)
        max_amt = float(cfg.get("max_amount_mn2") or 1.0)
        if amount_mn2 is None:
            return True
        amt = float(amount_mn2)
        return min_amt <= amt <= max_amt
    except Exception:
        return amount_mn2 is None


def credit_mn2_reward(
    user_id: str,
    amount_mn2: Optional[float] = None,
    *,
    source: str,
    reason: str = "",
    idempotency_key: Optional[str] = None,
    reference: Optional[str] = None,
    metadata: Optional[dict] = None,
    emit_event: bool = True,
) -> Dict[str, Any]:
    """
    Unified MN2 credit path: micro-tx instant_payout when source maps to config
    and amount is within micro-tx limits; otherwise direct unified_points + ledger.
    """
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err, "code": "auth_required"}
    uid = uid_or_err

    meta = dict(metadata or {})
    ref = (reference or idempotency_key or "").strip()
    if ref:
        meta.setdefault("reference", ref)

    amt = None if amount_mn2 is None else round(float(amount_mn2), 8)
    if amt is not None and amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}

    mtx_source = resolve_micro_tx_source(source)
    idem = (idempotency_key or reference or "").strip() or None

    if mtx_source and _amount_fits_micro_tx(amt):
        try:
            from backend.services.mn2_micro_tx_service import instant_payout

            result = instant_payout(
                user_id=uid,
                amount_mn2=amt,
                reason=reason or source,
                source=mtx_source,
                idempotency_key=idem,
                metadata=meta,
            )
            if result.get("success"):
                if emit_event:
                    try:
                        from backend.services.activity_events_service import emit

                        emit(
                            "game_mn2_reward",
                            user_id=uid,
                            channel="rewards",
                            text=f"+{result.get('amount_mn2')} MN2 ({source})",
                            payload={
                                "amount": result.get("amount_mn2"),
                                "source": source,
                                "micro_tx_source": mtx_source,
                                "reference": ref or idem,
                                "micro_tx": True,
                            },
                        )
                    except Exception:
                        pass
                return {
                    "success": True,
                    "amount": result.get("amount_mn2"),
                    "user_id": uid,
                    "source": source,
                    "micro_tx": True,
                    "payout_id": result.get("payout_id"),
                    "duplicate": result.get("duplicate"),
                    "mn2_balance": result.get("mn2_balance"),
                }
            if result.get("code") in _MICRO_TX_BLOCK_CODES:
                return result
        except Exception:
            pass

    if amt is None:
        return {"success": False, "error": "amount_required_for_direct_credit"}

    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    result = unified_points_db.add_points(
        uid, "mn2_balance", amt, source=source, metadata=meta,
    )
    if not result.get("success"):
        return result
    if result.get("duplicate"):
        return result

    try:
        append_entry(
            user_id=uid,
            entry_type=source,
            amount=amt,
            txid=ref or None,
            metadata=meta,
        )
    except Exception:
        pass

    if emit_event:
        try:
            from backend.services.activity_events_service import emit

            emit(
                "game_mn2_reward",
                user_id=uid,
                channel="game",
                text=f"+{amt} MN2 ({source})",
                payload={"amount": amt, "source": source, "reference": ref, "micro_tx": False},
            )
        except Exception:
            pass

    return {"success": True, "amount": amt, "user_id": uid, "source": source, "micro_tx": False}
