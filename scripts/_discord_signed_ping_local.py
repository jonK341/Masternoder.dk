"""Verify signed Discord PING against interactions route."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from flask import Flask


def main() -> None:
    priv = Ed25519PrivateKey.generate()
    pub_hex = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    os.environ["DISCORD_PUBLIC_KEY"] = pub_hex

    from backend.routes.discord_routes import discord_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(discord_bp)
    client = app.test_client()

    body = json.dumps({"type": 1}, separators=(",", ":"))
    ts = "1719345678"
    sig = priv.sign((ts + body).encode()).hex()
    r = client.post(
        "/api/discord/interactions",
        data=body,
        content_type="application/json",
        headers={"X-Signature-Ed25519": sig, "X-Signature-Timestamp": ts},
    )
    print("signed PING:", r.status_code, r.get_json())

    r2 = client.get("/api/discord/interactions")
    print("GET:", r2.status_code, r2.get_data(as_text=True)[:120])


if __name__ == "__main__":
    main()
