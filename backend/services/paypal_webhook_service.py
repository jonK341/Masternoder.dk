"""
Verify PayPal webhook signatures (Notifications API).

Requires PAYPAL_WEBHOOK_ID from the PayPal developer dashboard (same app as client id).
Optional PAYPAL_WEBHOOK_BYPASS=1 for local testing only (never in production).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    requests = None

from backend.services.paypal_service import _get_base_url, get_access_token


def verify_paypal_webhook_signature(
    headers: Any,
    webhook_event: Dict[str, Any],
) -> bool:
    """
    POST body of the incoming webhook is webhook_event.
    Headers must include PayPal-Transmission-* (see PayPal webhook docs).
    """
    if not requests:
        return False

    bypass = (os.environ.get("PAYPAL_WEBHOOK_BYPASS") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if bypass:
        return True

    wid = (os.environ.get("PAYPAL_WEBHOOK_ID") or "").strip()
    if not wid:
        return False

    h = headers or {}

    def _hdr(*names: str) -> Optional[str]:
        for n in names:
            v = h.get(n)
            if v:
                return v
        return None

    transmission_id = _hdr("PayPal-Transmission-Id", "Paypal-Transmission-Id")
    transmission_time = _hdr("PayPal-Transmission-Time", "Paypal-Transmission-Time")
    cert_url = _hdr("PayPal-Cert-Url", "Paypal-Cert-Url")
    auth_algo = _hdr("PayPal-Auth-Algo", "Paypal-Auth-Algo")
    transmission_sig = _hdr("PayPal-Transmission-Sig", "Paypal-Transmission-Sig")

    if not all([transmission_id, transmission_time, cert_url, auth_algo, transmission_sig]):
        return False

    token = get_access_token()
    if not token:
        return False

    payload = {
        "transmission_id": transmission_id,
        "transmission_time": transmission_time,
        "cert_url": cert_url,
        "auth_algo": auth_algo,
        "transmission_sig": transmission_sig,
        "webhook_id": wid,
        "webhook_event": webhook_event,
    }

    base = _get_base_url()
    r = requests.post(
        f"{base}/v1/notifications/verify-webhook-signature",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json=payload,
        timeout=15,
    )
    if r.status_code != 200:
        return False
    try:
        data = r.json()
    except Exception:
        return False
    return (data.get("verification_status") or "").upper() == "SUCCESS"
