"""Discord interactions endpoint (PING/PONG + optional signature verify)."""
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from flask import Flask


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("DISCORD_PUBLIC_KEY", raising=False)
    from backend.routes.discord_routes import discord_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(discord_bp)
    return app.test_client()


def test_interactions_ping_pong(client):
    r = client.post(
        "/api/discord/interactions",
        data=json.dumps({"type": 1}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json() == {"type": 1}


def test_interactions_rejects_invalid_json(client):
    r = client.post(
        "/api/discord/interactions",
        data="not-json",
        content_type="application/json",
    )
    assert r.status_code == 400


def test_interactions_requires_signature_when_public_key_set(client, monkeypatch):
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", "a" * 64)
    r = client.post(
        "/api/discord/interactions",
        data=json.dumps({"type": 1}),
        content_type="application/json",
    )
    assert r.status_code == 401
    assert r.get_json().get("error") == "missing_signature_headers"


def test_interactions_accepts_signed_ping(client, monkeypatch):
    priv = Ed25519PrivateKey.generate()
    pub_hex = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", pub_hex)
    body = json.dumps({"type": 1}, separators=(",", ":"))
    ts = "1719345678"
    sig = priv.sign((ts + body).encode()).hex()
    r = client.post(
        "/api/discord/interactions",
        data=body,
        content_type="application/json",
        headers={"X-Signature-Ed25519": sig, "X-Signature-Timestamp": ts},
    )
    assert r.status_code == 200
    assert r.get_json() == {"type": 1}


def test_interactions_public_key_accepts_0x_prefix(client, monkeypatch):
    priv = Ed25519PrivateKey.generate()
    pub_hex = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", f"0x{pub_hex}")
    body = json.dumps({"type": 1}, separators=(",", ":"))
    ts = "1719345678"
    sig = priv.sign((ts + body).encode()).hex()
    r = client.post(
        "/api/discord/interactions",
        data=body,
        content_type="application/json",
        headers={"X-Signature-Ed25519": sig, "X-Signature-Timestamp": ts},
    )
    assert r.status_code == 200
    assert r.get_json() == {"type": 1}
