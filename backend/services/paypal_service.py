"""
PayPal REST API integration for real-money payments.
Uses Orders v2 API: create order → capture on approval.
Add PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_MODE to .env
"""
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None

_token_cache = {"token": None, "expires": 0}
_SHOP_ORDERS_LOCK = threading.Lock()
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SHOP_ORDERS_PATH = os.path.join(_ROOT, "data", "paypal_shop_orders.json")


def _get_base_url() -> str:
    mode = (os.environ.get("PAYPAL_MODE") or "").strip().lower()
    if mode == "live" or mode.startswith("live"):
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"


def _approval_url(links: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """PayPal Checkout returns rel=approve (legacy) or rel=payer-action (current)."""
    by_rel: Dict[str, str] = {}
    for item in links or []:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("rel") or "").strip().lower()
        href = item.get("href")
        if rel and href:
            by_rel[rel] = str(href)
    return by_rel.get("approve") or by_rel.get("payer-action") or by_rel.get("payer_action")


def _issues_from_response(r) -> List[str]:
    issues: List[str] = []
    try:
        data = r.json() if r is not None else {}
    except Exception:
        return issues
    if not isinstance(data, dict):
        return issues
    for detail in data.get("details") or []:
        if isinstance(detail, dict) and detail.get("issue"):
            issues.append(str(detail.get("issue")))
    return issues


def _api_headers(token: str, request_id: Optional[str] = None) -> Dict[str, str]:
    """Prefer: return=representation so capture/create include full capture amounts."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Prefer": "return=representation",
    }
    if request_id:
        headers["PayPal-Request-Id"] = str(request_id)[:108]
    return headers


def _first_purchase_unit(data: Dict[str, Any]) -> Dict[str, Any]:
    units = data.get("purchase_units") or []
    if isinstance(units, list) and units and isinstance(units[0], dict):
        return units[0]
    return {}


def _first_capture(purchase: Dict[str, Any]) -> Dict[str, Any]:
    payments = purchase.get("payments") if isinstance(purchase.get("payments"), dict) else {}
    captures = payments.get("captures") or []
    if isinstance(captures, list) and captures and isinstance(captures[0], dict):
        return captures[0]
    return {}


def _capture_payload_from_order(data: Dict[str, Any], order_id: str) -> Dict[str, Any]:
    status = data.get("status")
    purchase = _first_purchase_unit(data)
    capture = _first_capture(purchase)
    amount = capture.get("amount") if isinstance(capture.get("amount"), dict) else {}
    if not amount.get("value"):
        pu_amount = purchase.get("amount") if isinstance(purchase.get("amount"), dict) else {}
        if pu_amount.get("value"):
            amount = pu_amount
    capture_status = str(capture.get("status") or "").upper()
    order_status = str(status or "").upper()
    completed = order_status == "COMPLETED" or capture_status == "COMPLETED"
    if capture_status == "PENDING":
        completed = False
    return {
        "success": bool(completed),
        "order_id": order_id,
        "status": status,
        "capture_status": capture.get("status") or status,
        "capture_id": capture.get("id"),
        "amount": amount.get("value"),
        "currency": amount.get("currency_code"),
    }


def _read_shop_orders() -> Dict[str, Any]:
    if not os.path.isfile(_SHOP_ORDERS_PATH):
        return {}
    try:
        with open(_SHOP_ORDERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_shop_orders(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_SHOP_ORDERS_PATH), exist_ok=True)
    tmp = _SHOP_ORDERS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _SHOP_ORDERS_PATH)


def remember_shop_order(order_id: str, payload: Dict[str, Any]) -> None:
    oid = str(order_id or "").strip()
    if not oid:
        return
    with _SHOP_ORDERS_LOCK:
        rows = _read_shop_orders()
        row = dict(payload or {})
        row["order_id"] = oid
        row["updated_at"] = time.time()
        rows[oid] = row
        _write_shop_orders(rows)


def get_pending_shop_order(order_id: str) -> Optional[Dict[str, Any]]:
    oid = str(order_id or "").strip()
    if not oid:
        return None
    with _SHOP_ORDERS_LOCK:
        row = _read_shop_orders().get(oid)
    return dict(row) if isinstance(row, dict) else None


def update_shop_order(order_id: str, **fields: Any) -> None:
    oid = str(order_id or "").strip()
    if not oid:
        return
    with _SHOP_ORDERS_LOCK:
        rows = _read_shop_orders()
        row = dict(rows.get(oid) or {})
        row["order_id"] = oid
        row.update(fields)
        row["updated_at"] = time.time()
        rows[oid] = row
        _write_shop_orders(rows)


def mark_shop_order_captured(order_id: str, capture_id: Optional[str] = None) -> None:
    fields: Dict[str, Any] = {"status": "captured"}
    if capture_id:
        fields["capture_id"] = capture_id
    update_shop_order(order_id, **fields)


def list_pending_shop_orders() -> List[Dict[str, Any]]:
    with _SHOP_ORDERS_LOCK:
        rows = _read_shop_orders()
    out: List[Dict[str, Any]] = []
    for oid, row in rows.items():
        if not isinstance(row, dict):
            continue
        status = str(row.get("status") or "").lower()
        if status in ("captured", "fulfilled", "expired", "voided"):
            continue
        item = dict(row)
        item["order_id"] = item.get("order_id") or oid
        out.append(item)
    return out


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

    unit: Dict[str, Any] = {
        "amount": {"currency_code": currency, "value": f"{float(amount):.2f}"},
        "description": str(item_name or "Shop Item")[:127],
    }
    meta = dict(metadata or {})
    custom_id = str(meta.get("custom_id") or meta.get("item_id") or "").strip()
    if custom_id:
        unit["custom_id"] = custom_id[:127]

    experience = {
        "return_url": return_url,
        "cancel_url": cancel_url,
        "brand_name": "MasterNoder",
        "shipping_preference": "NO_SHIPPING",
        "user_action": "PAY_NOW",
        "landing_page": "NO_PREFERENCE",
    }
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [unit],
        "application_context": experience,
    }

    base = _get_base_url()
    r = requests.post(
        f"{base}/v2/checkout/orders",
        headers=_api_headers(token),
        json=payload,
        timeout=30,
    )
    if r.status_code not in (200, 201):
        return {"success": False, "error": r.text}

    try:
        data = r.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    oid = data.get("id")
    approve_url = _approval_url(data.get("links") or [])
    if oid:
        try:
            remember_shop_order(str(oid), {
                "status": str(data.get("status") or "CREATED").lower(),
                "amount": float(amount),
                "currency": currency,
                "item_name": item_name,
                "item_id": meta.get("item_id") or "",
                "user_id": meta.get("user_id") or "",
                "metadata": meta,
                "approve_url": approve_url,
            })
        except Exception:
            pass
    return {
        "success": True,
        "order_id": oid,
        "approve_url": approve_url,
        "status": data.get("status"),
    }


def get_checkout_order(order_id: str) -> Dict:
    """GET /v2/checkout/orders/{id} — used when capture reports already captured."""
    if not requests:
        return {"success": False, "error": "requests library required"}
    oid = str(order_id or "").strip()
    if not oid:
        return {"success": False, "error": "missing order_id"}
    token = get_access_token()
    if not token:
        return {"success": False, "error": "PayPal authentication failed"}
    base = _get_base_url()
    r = requests.get(
        f"{base}/v2/checkout/orders/{oid}",
        headers=_api_headers(token),
        timeout=30,
    )
    if r.status_code != 200:
        return {"success": False, "error": r.text, "status_code": r.status_code}
    try:
        data = r.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return {"success": True, "order_id": data.get("id") or oid, "status": data.get("status"), "raw": data}


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

    oid = str(order_id or "").strip()
    if not oid:
        return {"success": False, "error": "missing order_id"}
    base = _get_base_url()
    r = requests.post(
        f"{base}/v2/checkout/orders/{oid}/capture",
        headers=_api_headers(token, request_id=f"cap-{oid}"),
        json={},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        return _recover_failed_capture(oid, r)

    try:
        data = r.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    return _capture_payload_from_order(data, oid)


_AWAITING_PAYER = {"CREATED", "PAYER_ACTION_REQUIRED", "SAVED"}
_DEAD_ORDER = {"VOIDED", "EXPIRED", "DECLINED"}
_FINISHABLE = {"APPROVED", "COMPLETED"}


def _recover_failed_capture(oid: str, r) -> Dict[str, Any]:
    issues = _issues_from_response(r)
    text = (r.text or "").upper()
    already = (
        "ORDER_ALREADY_CAPTURED" in issues
        or "CAPTURE_ALREADY_EXISTS" in issues
        or "ORDER_ALREADY_CAPTURED" in text
        or "CAPTURE_ALREADY_EXISTS" in text
    )
    existing = get_checkout_order(oid)
    raw = existing.get("raw") if existing.get("success") else None
    paypal_status = str((raw or {}).get("status") or existing.get("status") or "").upper()
    if already or paypal_status == "COMPLETED":
        if isinstance(raw, dict):
            out = _capture_payload_from_order(raw, oid)
            if out.get("capture_id") or str(out.get("status") or "").upper() == "COMPLETED":
                out["success"] = True
                out["already_captured"] = True
                return out
        return {
            "success": True,
            "already_captured": True,
            "order_id": oid,
            "status": paypal_status or "COMPLETED",
        }
    if "ORDER_NOT_APPROVED" in issues or paypal_status in _AWAITING_PAYER:
        return {
            "success": False,
            "error": r.text,
            "code": "ORDER_NOT_APPROVED",
            "paypal_status": paypal_status or "NOT_APPROVED",
            "outcome": "awaiting_payer",
            "order_id": oid,
        }
    return {"success": False, "error": r.text, "paypal_status": paypal_status or None, "order_id": oid}


def finish_checkout_order(order_id: str) -> Dict[str, Any]:
    """Capture an APPROVED checkout (or recover COMPLETED) so PayPal actually pays out."""
    oid = str(order_id or "").strip()
    if not oid:
        return {"success": False, "error": "missing order_id"}
    existing = get_checkout_order(oid)
    if not existing.get("success"):
        return {
            "success": False,
            "error": existing.get("error") or "lookup_failed",
            "status_code": existing.get("status_code"),
            "order_id": oid,
            "outcome": "missing",
        }
    st = str(existing.get("status") or "").upper()
    if st in _AWAITING_PAYER:
        return {"success": False, "outcome": "awaiting_payer", "paypal_status": st, "order_id": oid}
    if st in _DEAD_ORDER:
        update_shop_order(oid, status="expired", paypal_status=st)
        return {"success": False, "outcome": "expired", "paypal_status": st, "order_id": oid}
    if st in _FINISHABLE:
        cap = capture_order(oid)
        cap["paypal_status"] = st
        cap["outcome"] = "captured" if cap.get("success") else "capture_failed"
        if cap.get("success"):
            mark_shop_order_captured(oid, cap.get("capture_id"))
        return cap
    return {"success": False, "outcome": "skipped", "paypal_status": st, "order_id": oid}


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
