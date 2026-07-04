"""
PayPal REST API integration for real-money payments.
Uses Orders v2 API: create order → capture on approval.
Add PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_MODE to .env
"""
import os
import time
from typing import Dict, Optional

try:
    import requests
except ImportError:
    requests = None

_token_cache = {"token": None, "expires": 0}


def _get_base_url() -> str:
    mode = (os.environ.get("PAYPAL_MODE") or "").strip().lower()
    if mode == "live" or mode.startswith("live"):
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"


def get_access_token() -> Optional[str]:
    """Get OAuth 2.0 access token (cached)."""
    if _token_cache["token"] and time.time() < _token_cache["expires"]:
        return _token_cache["token"]
    if not requests:
        return None
    cid = os.environ.get("PAYPAL_CLIENT_ID", "")
    secret = os.environ.get("PAYPAL_CLIENT_SECRET", "")
    if not cid or not secret:
        return None
    base = _get_base_url()
    r = requests.post(
        f"{base}/v1/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        auth=(cid, secret),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    if r.status_code != 200:
        return None
    data = r.json()
    _token_cache["token"] = data.get("access_token")
    _token_cache["expires"] = time.time() + (data.get("expires_in", 0) - 60)
    return _token_cache["token"]


def create_order(
    amount: float,
    currency: str = "USD",
    item_name: str = "Shop Item",
    return_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> Dict:
    """
    Create a PayPal order. Returns order ID and approval URL.
    amount: price in dollars (e.g. 4.99)
    """
    if not requests:
        return {"success": False, "error": "requests library required"}
    token = get_access_token()
    if not token:
        cid = (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
        secret = (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
        if not cid or not secret:
            return {"success": False, "error": "PayPal credentials missing (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET)"}
        return {"success": False, "error": "PayPal authentication failed", "mode": os.environ.get("PAYPAL_MODE") or "sandbox"}

    base_url = os.environ.get("BASE_URL", "https://masternoder.dk")
    return_url = return_url or f"{base_url}/shop?paypal=success"
    cancel_url = cancel_url or f"{base_url}/shop?paypal=cancel"

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
                "description": item_name,
                "custom_id": (metadata or {}).get("item_id", ""),
            }
        ],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "brand_name": "MasterNoder",
        },
    }

    base = _get_base_url()
    r = requests.post(
        f"{base}/v2/checkout/orders",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json=payload,
        timeout=10,
    )
    if r.status_code not in (200, 201):
        return {"success": False, "error": r.text}

    data = r.json()
    links = {l["rel"]: l["href"] for l in data.get("links", [])}
    return {
        "success": True,
        "order_id": data.get("id"),
        "approve_url": links.get("approve"),
        "status": data.get("status"),
    }


def capture_order(order_id: str) -> Dict:
    """Capture payment after user approves."""
    if not requests:
        return {"success": False, "error": "requests library required"}
    token = get_access_token()
    if not token:
        cid = (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
        secret = (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
        if not cid or not secret:
            return {"success": False, "error": "PayPal credentials missing (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET)"}
        return {"success": False, "error": "PayPal authentication failed", "mode": os.environ.get("PAYPAL_MODE") or "sandbox"}

    base = _get_base_url()
    r = requests.post(
        f"{base}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json={},
        timeout=10,
    )
    if r.status_code not in (200, 201):
        return {"success": False, "error": r.text}

    data = r.json()
    status = data.get("status")
    purchase = (data.get("purchase_units") or [{}])[0]
    capture = (purchase.get("payments", {}).get("captures") or [{}])[0]
    return {
        "success": status == "COMPLETED",
        "order_id": order_id,
        "status": status,
        "capture_id": capture.get("id"),
        "amount": capture.get("amount", {}).get("value"),
        "currency": capture.get("amount", {}).get("currency_code"),
    }


def create_billing_subscription(
    plan_id: str,
    *,
    custom_id: Optional[str] = None,
    return_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
) -> Dict:
    """
    POST /v1/billing/subscriptions — user must open approve_url (rel=approve).
    custom_id is echoed on the subscription (webhooks / dashboard); use internal user_id.
    """
    if not requests:
        return {"success": False, "error": "requests library required"}
    pid = (plan_id or "").strip()
    if not pid:
        return {"success": False, "error": "missing plan_id"}
    token = get_access_token()
    if not token:
        cid = (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
        secret = (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
        if not cid or not secret:
            return {"success": False, "error": "PayPal credentials missing (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET)"}
        return {"success": False, "error": "PayPal authentication failed", "mode": os.environ.get("PAYPAL_MODE") or "sandbox"}

    base_url = os.environ.get("BASE_URL", "https://masternoder.dk").strip().rstrip("/")
    if base_url.endswith("/vidgenerator"):
        base_url = base_url.rsplit("/vidgenerator", 1)[0]
    return_url = return_url or f"{base_url}/shop?paypal_subscription=return"
    cancel_url = cancel_url or f"{base_url}/shop?paypal_subscription=cancel"

    payload: Dict = {
        "plan_id": pid,
        "application_context": {
            "brand_name": "MasterNoder",
            "locale": "en-US",
            "shipping_preference": "NO_SHIPPING",
            "user_action": "SUBSCRIBE_NOW",
            "payment_method": {
                "payer_selected": "PAYPAL",
                "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED",
            },
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }
    if custom_id:
        payload["custom_id"] = str(custom_id)[:127]

    base = _get_base_url()
    r = requests.post(
        f"{base}/v1/billing/subscriptions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Prefer": "return=representation",
        },
        json=payload,
        timeout=20,
    )
    if r.status_code not in (200, 201):
        return {"success": False, "error": r.text or str(r.status_code)}

    data = r.json()
    links = {l.get("rel"): l.get("href") for l in (data.get("links") or [])}
    return {
        "success": True,
        "subscription_id": data.get("id"),
        "status": data.get("status"),
        "approve_url": links.get("approve"),
        "raw": data,
    }


def get_billing_subscription(subscription_id: str) -> Dict:
    """
    GET /v1/billing/subscriptions/{id} — used when webhook has user but plan_id missing.
    """
    if not requests:
        return {"success": False, "error": "requests library required"}
    sid = (subscription_id or "").strip()
    if not sid:
        return {"success": False, "error": "missing subscription_id"}
    token = get_access_token()
    if not token:
        cid = (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
        secret = (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
        if not cid or not secret:
            return {"success": False, "error": "PayPal credentials missing (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET)"}
        return {"success": False, "error": "PayPal authentication failed", "mode": os.environ.get("PAYPAL_MODE") or "sandbox"}

    base = _get_base_url()
    r = requests.get(
        f"{base}/v1/billing/subscriptions/{sid}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        timeout=15,
    )
    if r.status_code != 200:
        return {"success": False, "error": r.text}
    data = r.json()
    plan = data.get("plan_id") or (data.get("plan") or {}).get("id")
    return {
        "success": True,
        "subscription_id": data.get("id"),
        "plan_id": plan,
        "status": data.get("status"),
        "raw": data,
    }


def ensure_pro_subscription_plan(
    *,
    name: str = "Pro monthly",
    price_usd: float = 19.99,
    product_name: str = "MasterNoder Pro",
) -> Dict:
    """
    Create catalog product + billing plan via PayPal REST API when plan env is unset.
    Returns plan_id (P-…) on success.
    """
    if not requests:
        return {"success": False, "error": "requests library required"}
    token = get_access_token()
    if not token:
        cid = (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
        secret = (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
        if not cid or not secret:
            return {"success": False, "error": "PayPal credentials missing (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET)"}
        return {"success": False, "error": "PayPal authentication failed", "mode": os.environ.get("PAYPAL_MODE") or "sandbox"}

    base = _get_base_url()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Prefer": "return=representation",
    }

    prod_payload = {
        "name": product_name[:127],
        "type": "SERVICE",
        "category": "SOFTWARE",
        "description": "MasterNoder Pro subscription — generator credits and premium caps.",
    }
    r = requests.post(f"{base}/v1/catalogs/products", headers=headers, json=prod_payload, timeout=20)
    if r.status_code not in (200, 201):
        return {"success": False, "error": r.text or str(r.status_code), "step": "create_product"}
    product_id = (r.json() or {}).get("id")
    if not product_id:
        return {"success": False, "error": "missing product_id", "step": "create_product"}

    plan_payload = {
        "product_id": product_id,
        "name": name[:127],
        "description": "Monthly Pro subscription for MasterNoder.dk",
        "billing_cycles": [
            {
                "frequency": {"interval_unit": "MONTH", "interval_count": 1},
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": 0,
                "pricing_scheme": {
                    "fixed_price": {"value": f"{float(price_usd):.2f}", "currency_code": "USD"},
                },
            }
        ],
        "payment_preferences": {
            "auto_bill_outstanding": True,
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3,
        },
    }
    r = requests.post(f"{base}/v1/billing/plans", headers=headers, json=plan_payload, timeout=20)
    if r.status_code not in (200, 201):
        return {"success": False, "error": r.text or str(r.status_code), "step": "create_plan", "product_id": product_id}
    plan_id = (r.json() or {}).get("id")
    if not plan_id:
        return {"success": False, "error": "missing plan_id", "step": "create_plan", "product_id": product_id}

    r = requests.post(f"{base}/v1/billing/plans/{plan_id}/activate", headers=headers, json={}, timeout=20)
    if r.status_code not in (200, 204):
        err_text = r.text or str(r.status_code)
        if "PLAN_STATUS_INVALID" in err_text:
            return {
                "success": True,
                "plan_id": plan_id,
                "product_id": product_id,
                "price_usd": float(price_usd),
                "mode": os.environ.get("PAYPAL_MODE") or "sandbox",
                "note": "plan_already_active",
            }
        return {
            "success": False,
            "error": err_text,
            "step": "activate_plan",
            "plan_id": plan_id,
            "product_id": product_id,
        }

    return {
        "success": True,
        "plan_id": plan_id,
        "product_id": product_id,
        "price_usd": float(price_usd),
        "mode": os.environ.get("PAYPAL_MODE") or "sandbox",
    }


def create_payout(
    receiver_email: str,
    amount_usd: float,
    *,
    currency: str = "USD",
    note: str = "MasterNoder exchange profit",
    sender_batch_id: Optional[str] = None,
) -> Dict:
    """Send funds to a PayPal account via Payouts API (requires Payouts enabled on the app)."""
    if not requests:
        return {"success": False, "error": "requests library required"}
    email = (receiver_email or "").strip()
    if not email or "@" not in email:
        return {"success": False, "error": "invalid_receiver_email"}
    amt = round(float(amount_usd or 0), 2)
    if amt < 0.01:
        return {"success": False, "error": "amount_too_small"}

    token = get_access_token()
    if not token:
        cid = (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
        secret = (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
        if not cid or not secret:
            return {"success": False, "error": "PayPal credentials missing (PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET)"}
        return {"success": False, "error": "PayPal authentication failed", "mode": os.environ.get("PAYPAL_MODE") or "sandbox"}

    import uuid

    batch_id = (sender_batch_id or f"mn2-profit-{uuid.uuid4().hex[:16]}")[:127]
    payload = {
        "sender_batch_header": {
            "sender_batch_id": batch_id,
            "email_subject": "MasterNoder profit payout",
            "email_message": "You received a profit payout from MasterNoder exchange trading.",
        },
        "items": [
            {
                "recipient_type": "EMAIL",
                "amount": {"value": f"{amt:.2f}", "currency_code": currency.upper()},
                "receiver": email,
                "note": (note or "")[:255],
                "sender_item_id": batch_id,
            }
        ],
    }
    base = _get_base_url()
    r = requests.post(
        f"{base}/v1/payments/payouts",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json=payload,
        timeout=30,
    )
    if r.status_code not in (200, 201):
        return {"success": False, "error": r.text or str(r.status_code), "status_code": r.status_code}

    data = r.json()
    batch = data.get("batch_header") or {}
    return {
        "success": True,
        "payout_batch_id": batch.get("payout_batch_id") or data.get("batch_header", {}).get("payout_batch_id"),
        "batch_status": batch.get("batch_status"),
        "sender_batch_id": batch_id,
        "amount_usd": amt,
        "receiver_email": email,
        "mode": os.environ.get("PAYPAL_MODE") or "sandbox",
    }
