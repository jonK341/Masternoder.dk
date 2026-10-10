"""Verify Discord interaction requests (Ed25519) per Discord API docs."""
from __future__ import annotations

import os
from typing import Optional, Tuple

from flask import Request


def _public_key_bytes(hex_key: str) -> Optional[bytes]:
    key = (hex_key or "").strip()
    if not key:
        return None
    try:
        return bytes.fromhex(key)
    except ValueError:
        return None


def verify_interaction_request(
    request: Request,
    *,
    public_key_hex: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Return (ok, error_message).
    Uses raw body + X-Signature-Timestamp + X-Signature-Ed25519 headers.
    """
    pub = (public_key_hex or os.environ.get("DISCORD_PUBLIC_KEY") or "").strip()
    if not pub:
        return False, "DISCORD_PUBLIC_KEY not configured"

    sig = (request.headers.get("X-Signature-Ed25519") or "").strip()
    ts = (request.headers.get("X-Signature-Timestamp") or "").strip()
    if not sig or not ts:
        return False, "missing_signature_headers"

    body = request.get_data(cache=True)
    if body is None:
        body = b""

    pk_bytes = _public_key_bytes(pub)
    if not pk_bytes or len(pk_bytes) != 32:
        return False, "invalid_public_key"

    sig_bytes = _public_key_bytes(sig)
    if not sig_bytes or len(sig_bytes) != 64:
        return False, "invalid_signature"

    message = ts.encode("utf-8") + body
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        Ed25519PublicKey.from_public_bytes(pk_bytes).verify(sig_bytes, message)
        return True, None
    except Exception:
        return False, "signature_verification_failed"
