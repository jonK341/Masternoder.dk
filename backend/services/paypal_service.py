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
        return {"success": False, "error": "PayPal authentication failed"}

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
        return {"success": False, "error": "PayPal authentication failed"}

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
        return {"success": False, "error": "PayPal authentication failed"}

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
        return {"success": False, "error": "PayPal authentication failed"}

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
