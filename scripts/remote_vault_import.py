#!/usr/bin/env python3
"""Import venue API keys from server .env into encrypted vault (server-side)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

env_path = os.path.join(ROOT, ".env")
if os.path.isfile(env_path):
    for line in open(env_path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

from backend.services import exchange_secrets_vault_service as vault

venues = ["binance", "okx", "bybit", "nonkyc", "kucoin", "xeggex"]
imported = []
for vid in venues:
    key = os.environ.get(f"{vid.upper()}_API_KEY") or os.environ.get(f"{vid}_api_key")
    sec = os.environ.get(f"{vid.upper()}_API_SECRET") or os.environ.get(f"{vid}_api_secret")
    if key and sec:
        vault.set_secret(f"{vid}_api_key", key)
        vault.set_secret(f"{vid}_api_secret", sec)
        imported.append(vid)

print("vault_imported:", imported or "none")
print("encryption_available:", vault.encryption_available())
