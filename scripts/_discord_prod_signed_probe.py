"""POST signed PING to production using local DISCORD_PUBLIC_KEY + generated private key.

Only valid if we had Discord's private key — instead signs with a throwaway key
to prove prod rejects wrong keys, then signs using a keypair where we set
local PUBLIC key... can't sign with public key only.

This script loads local PUBLIC key and uses it to verify prod requires sig.
For end-to-end: generate keypair, but prod has fixed PUBLIC key — so we read
local .env PUBLIC key and attempt prod POST with signature derived from...
We need the matching private key which we don't have.

Instead: sign with Ed25519PrivateKey.generate() — expect 401 invalid_signature on prod.
Then document that prod signature gate is active.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[1]


def _local_public_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DISCORD_PUBLIC_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _signed_post(url: str, priv: Ed25519PrivateKey, body: str, ts: str = "1719345678") -> requests.Response:
    sig = priv.sign((ts + body).encode()).hex()
    return requests.post(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature-Ed25519": sig,
            "X-Signature-Timestamp": ts,
        },
        timeout=20,
    )


def main() -> None:
    url = "https://masternoder.dk/api/discord/interactions"
    body = json.dumps({"type": 1}, separators=(",", ":"))

    # Wrong key -> must be 401
    wrong = Ed25519PrivateKey.generate()
    r1 = _signed_post(url, wrong, body)
    print("wrong_key:", r1.status_code, r1.text[:120])

    pub = _local_public_key()
    print("local_public_fp:", hashlib.sha256(pub.encode()).hexdigest()[:16] if pub else "unset")

    # We cannot sign with Discord's private key from local public key alone.
    # If local .env PUBLIC key matches Discord portal AND server, Discord verification should work.
    print("note: Discord portal must match server DISCORD_PUBLIC_KEY exactly")


if __name__ == "__main__":
    main()
