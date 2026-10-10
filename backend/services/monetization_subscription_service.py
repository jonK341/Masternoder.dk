"""
PayPal Subscriptions: bindings (subscription_id → user + plan), webhook idempotency, monthly grant.

Flow:
1. Client completes PayPal subscription checkout and obtains subscription id (I-…).
2. POST /api/monetization/subscription/bind with { subscription_id, plan_id } (session user).
3. PayPal sends PAYMENT.SALE.COMPLETED for each billing cycle → we verify webhook, grant credits.

Optional: BILLING.SUBSCRIPTION.ACTIVATED may include custom_id / custom (subscriber) to auto-bind.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List

from backend.services.monetization_config_service import get_subscription_plan, reload_monetization_config


def _log_dir() -> str:
    base = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "logs",
    )
    return os.path.join(base, "monetization")


def _bindings_path() -> str:
    return os.path.join(_log_dir(), "subscription_bindings.json")


def _processed_events_path() -> str:
    return os.path.join(_log_dir(), "paypal_webhook_processed_ids.jsonl")


def _load_bindings() -> Dict[str, Any]:
    path = _bindings_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_bindings(data: Dict[str, Any]) -> None:
    path = _bindings_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def save_subscription_binding(
    subscription_id: str,
    user_id: str,
    plan_id: str,
) -> Dict[str, Any]:
    """Persist I-… → user + PayPal plan id (P-…)."""
    sid = (subscription_id or "").strip()
    uid = (user_id or "").strip()
    pid = (plan_id or "").strip()
    if not sid or not uid or not pid:
        return {"success": False, "error": "subscription_id, user_id, and plan_id required"}
    data = _load_bindings()
    data[sid] = {
        "user_id": uid,
        "plan_id": pid,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_bindings(data)
    return {"success": True, "subscription_id": sid}


def get_binding(subscription_id: str) -> Optional[Dict[str, Any]]:
    return _load_bindings().get((subscription_id or "").strip())


def list_bindings_for_user(user_id: str) -> List[Dict[str, Any]]:
    """All I-… bindings for a user (newest updated_at first)."""
    uid = (user_id or "").strip()
    if not uid:
        return []
    data = _load_bindings()
    out: List[Dict[str, Any]] = []
    for sid, row in data.items():
        if not isinstance(row, dict):
            continue
        if str(row.get("user_id") or "").strip() != uid:
            continue
        out.append({
            "subscription_id": sid,
            "plan_id": row.get("plan_id"),
            "updated_at": row.get("updated_at"),
        })
    out.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    return out


def list_all_bound_user_ids() -> List[str]:
    """Distinct user ids with an active subscription binding."""
    data = _load_bindings()
    seen: set = set()
    out: List[str] = []
    for row in data.values():
        if not isinstance(row, dict):
            continue
        uid = str(row.get("user_id") or "").strip()
        if uid and uid.lower() != "default_user" and uid not in seen:
            seen.add(uid)
            out.append(uid)
    return out


def _event_already_processed(event_id: str) -> bool:
    eid = (event_id or "").strip()
    if not eid:
        return False
    path = _processed_events_path()
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if row.get("id") == eid:
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


def _mark_event_processed(event_id: str, extra: Optional[Dict[str, Any]] = None) -> None:
    eid = (event_id or "").strip()
    if not eid:
        return
    path = _processed_events_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    row = {"id": eid, "ts": datetime.now(timezone.utc).isoformat()}
    if extra:
        row.update(extra)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _coins_from_generation_credits(credits: float) -> int:
    """Align with coin-pack-s: 100 coins ↔ 0.25 generation credits → 400 coins per credit."""
    try:
        c = float(credits or 0)
    except (TypeError, ValueError):
        c = 0.0
    return max(0, int(round(c * 400)))


def _apply_tier_from_plan(user_id: str, tier: Optional[str]) -> None:
    t = (tier or "").strip().lower()
    if t not in ("creator", "pro"):
        return
    try:
        from backend.services.user_onboarding import user_onboarding

        if not user_onboarding:
            return
        prof = user_onboarding.get_user_profile(user_id)
        if not prof:
            return
        prefs = prof.get("preferences")
        if isinstance(prefs, str):
            prefs = json.loads(prefs or "{}")
        if not isinstance(prefs, dict):
            prefs = {}
        prefs["monetization_tier"] = t
        user_onboarding.update_user_profile(user_id, {"preferences": prefs})
    except Exception:
        pass


def _grant_subscription_cycle(
    *,
    user_id: str,
    subscription_id: str,
    plan_id: str,
    event_id: str,
    amount_usd: float,
    currency: str,
) -> Dict[str, Any]:
    reload_monetization_config()
    pinfo = get_subscription_plan(plan_id)

    monthly_credits = pinfo.get("monthly_generation_credits")
    try:
        mgen = float(monthly_credits) if monthly_credits is not None else 0.0
    except (TypeError, ValueError):
        mgen = 0.0

    monthly_coins = pinfo.get("monthly_coins_granted")
    try:
        mcoins = int(monthly_coins) if monthly_coins is not None else _coins_from_generation_credits(mgen)
    except (TypeError, ValueError):
        mcoins = _coins_from_generation_credits(mgen)

    tier = (pinfo.get("tier") or "").strip().lower() or None

    result: Dict[str, Any] = {
        "granted": False,
        "user_id": user_id,
        "subscription_id": subscription_id,
        "plan_id": plan_id,
        "generation_credits": mgen,
        "coins_granted": 0,
    }

    try:
        from backend.services.unified_points_database import unified_points_db

        if unified_points_db and mcoins > 0:
            unified_points_db.add_points(
                user_id=user_id,
                point_type="coins",
                amount=float(mcoins),
                source="paypal_subscription",
                metadata={
                    "subscription_id": subscription_id,
                    "plan_id": plan_id,
                    "webhook_event_id": event_id,
                    "generation_credits": mgen,
                },
            )
            result["coins_granted"] = mcoins
            result["granted"] = True
    except Exception:
        pass

    if tier:
        _apply_tier_from_plan(user_id, tier)

    try:
        from backend.services.monetization_ledger_service import append_payment_event

        append_payment_event(
            provider="paypal_subscription",
            user_id=user_id,
            order_id=event_id,
            capture_id=None,
            amount_usd=float(amount_usd or 0),
            currency=currency or "USD",
            item_id=plan_id,
            item_name=str(pinfo.get("label") or plan_id),
            coins_granted=int(result.get("coins_granted") or 0),
            generation_credits_granted=float(mgen),
            subscription_id=subscription_id,
            extra={"webhook_event_id": event_id, "paypal_plan_id": plan_id},
        )
    except Exception:
        pass

    try:
        from backend.services.unified_points_sync import unified_points_sync_device

        unified_points_sync_device.record_domain_sync("paypal_subscription")
    except Exception:
        pass

    return result


def process_paypal_webhook_event(body: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """
    Returns (json_dict, http_status). Always use 200 for PayPal on handled errors
    (after logging) only if we must avoid retries — PayPal retries 4xx/5xx.
    Duplicate events: 200 + duplicate flag.
    """
    event_id = (body.get("id") or "").strip()
    event_type = (body.get("event_type") or "").strip()

    if not event_id:
        return {"success": False, "error": "missing_event_id"}, 400

    if _event_already_processed(event_id):
        return {"success": True, "duplicate": True, "event_id": event_id}, 200

    # ------------------------------------------------------------------
    # BILLING.SUBSCRIPTION.ACTIVATED — optional auto-bind via custom_id
    # ------------------------------------------------------------------
    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        resource = body.get("resource") or {}
        sub_id = (resource.get("id") or "").strip()
        plan = resource.get("plan_id") or (resource.get("plan") or {}).get("id")
        plan_id = (plan or "").strip()
        custom = (
            resource.get("custom_id")
            or resource.get("custom")
            or (resource.get("custom") if isinstance(resource.get("custom"), str) else None)
        )
        uid = (custom or "").strip() if custom else ""
        if sub_id and plan_id and uid and uid.lower() not in ("default_user",):
            save_subscription_binding(sub_id, uid, plan_id)
        _mark_event_processed(event_id, {"event_type": event_type})
        return {"success": True, "handled": "subscription_activated", "event_id": event_id}, 200

    # ------------------------------------------------------------------
    # BILLING.SUBSCRIPTION.CANCELLED — downgrade tier to creator (best effort)
    # ------------------------------------------------------------------
    if event_type == "BILLING.SUBSCRIPTION.CANCELLED":
        resource = body.get("resource") or {}
        sub_id = (resource.get("id") or "").strip()
        b = get_binding(sub_id) if sub_id else None
        uid = (b or {}).get("user_id")
        if uid:
            _apply_tier_from_plan(str(uid), "creator")
        _mark_event_processed(event_id, {"event_type": event_type})
        return {"success": True, "handled": "subscription_cancelled", "event_id": event_id}, 200

    # ------------------------------------------------------------------
    # PAYMENT.SALE.COMPLETED — recurring charge; grant monthly entitlements
    # ------------------------------------------------------------------
    if event_type == "PAYMENT.SALE.COMPLETED":
        resource = body.get("resource") or {}
        subscription_id = (resource.get("billing_agreement_id") or "").strip()
        amount_obj = resource.get("amount") or {}
        try:
            amount_usd = float(amount_obj.get("total") or resource.get("amount_total") or 0)
        except (TypeError, ValueError):
            amount_usd = 0.0
        currency = (amount_obj.get("currency") or resource.get("currency_code") or "USD") or "USD"

        state = (resource.get("state") or "").upper()
        if state and state != "COMPLETED":
            _mark_event_processed(event_id, {"event_type": event_type, "skipped": "not_completed"})
            return {"success": True, "skipped": True, "reason": "sale_not_completed"}, 200

        user_id = ""
        plan_id = ""

        b = get_binding(subscription_id) if subscription_id else None
        if b:
            user_id = str(b.get("user_id") or "").strip()
            plan_id = str(b.get("plan_id") or "").strip()

        if not user_id:
            # Some integrations pass custom on the sale
            cust = resource.get("custom") or resource.get("custom_id") or ""
            user_id = str(cust).strip()

        if not user_id or user_id.lower() == "default_user":
            _mark_event_processed(event_id, {"event_type": event_type, "skipped": "no_user"})
            return {"success": True, "skipped": True, "reason": "no_bound_user"}, 200

        if not plan_id and subscription_id:
            try:
                from backend.services.paypal_service import get_billing_subscription

                sub = get_billing_subscription(subscription_id)
                if sub.get("success"):
                    plan_id = str(sub.get("plan_id") or "").strip()
            except Exception:
                pass

        if not plan_id:
            _mark_event_processed(event_id, {"event_type": event_type, "skipped": "no_plan"})
            return {"success": True, "skipped": True, "reason": "unknown_plan_bind_subscription"}, 200

        out = _grant_subscription_cycle(
            user_id=user_id,
            subscription_id=subscription_id or "unknown",
            plan_id=plan_id,
            event_id=event_id,
            amount_usd=amount_usd,
            currency=str(currency),
        )
        _mark_event_processed(event_id, {"event_type": event_type, **out})
        return {"success": True, "handled": "payment_sale_completed", "event_id": event_id, **out}, 200

    # Other event types: acknowledge to avoid endless retries if we subscribe to many
    _mark_event_processed(event_id, {"event_type": event_type, "note": "ignored"})
    return {"success": True, "ignored": True, "event_type": event_type}, 200
