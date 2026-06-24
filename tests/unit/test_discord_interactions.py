"""Discord interaction signature verification."""
from __future__ import annotations

import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from flask import Flask, request


def test_verify_interaction_ping_roundtrip():
    app = Flask(__name__)
    private_key = Ed25519PrivateKey.generate()
    public_hex = private_key.public_key().public_bytes_raw().hex()
    body = json.dumps({"type": 1}).encode("utf-8")
    ts = "1719225600"
    sig = private_key.sign(ts.encode("utf-8") + body).hex()

    with app.test_request_context(
        "/api/discord/interactions",
        method="POST",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature-Timestamp": ts,
            "X-Signature-Ed25519": sig,
        },
    ):
        from backend.services.discord_signature_service import verify_interaction_request

        ok, err = verify_interaction_request(request, public_key_hex=public_hex)
        assert ok is True
        assert err is None
