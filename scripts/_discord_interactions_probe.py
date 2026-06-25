"""Local probe: DISCORD_PUBLIC_KEY shape + Ed25519 roundtrip (no secrets printed)."""
from __future__ import annotations

import json
import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), val)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    _load_dotenv(root / ".env")
    pk = (os.environ.get("DISCORD_PUBLIC_KEY") or "").strip()
    print("DISCORD_PUBLIC_KEY set:", bool(pk))
    print("DISCORD_PUBLIC_KEY len:", len(pk))
    if pk:
        print("DISCORD_PUBLIC_KEY hex chars:", all(c in "0123456789abcdefABCDEF" for c in pk))

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

    priv = Ed25519PrivateKey.generate()
    pub_hex = priv.public_key().public_bytes().hex()
    body = b"1719345678" + json.dumps({"type": 1}).encode()
    sig_hex = priv.sign(body).hex()
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(bytes.fromhex(sig_hex), body)
    print("ed25519 roundtrip: ok")

    if pk and len(pk) == 64:
        print("local portal key length OK (64 hex chars)")
    elif pk:
        print("WARNING: portal key length is not 64 hex chars — verification will fail")


if __name__ == "__main__":
    main()
