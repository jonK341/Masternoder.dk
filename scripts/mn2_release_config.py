"""Shared constants for MasterNoder2 release pipeline (v1.3.1.0 exchange sporks)."""
from __future__ import annotations

REPO = "jonK341/MasterNoder2"
TARGET_VERSION = "v1.3.1.0"
BASE_TAG = "v1.2.3.0"
PATCH_REL = "docs/patches/mn2-daemon-v1.3.0-multi-ping.patch"
EXTRA_PATCH_REL = "docs/patches/mn2-daemon-v1.3.1-exchange-sporks.patch"
# Populated from RELEASE_MANIFEST.json after build; fallback for tag-only releases.
MAIN_COMMIT = "61caddbfd3c8f4465012d1033206501fb6690b14"
RELEASE_BASE = f"https://github.com/{REPO}/releases/download/{TARGET_VERSION}"
TARBALL_NAME = "masternoder2d.tar.gz"
MANIFEST_NAME = "RELEASE_MANIFEST.json"
RELEASE_URL = f"{RELEASE_BASE}/{TARBALL_NAME}"
MANIFEST_URL = f"{RELEASE_BASE}/{MANIFEST_NAME}"

BINARIES = ("masternoder2d", "masternoder2-cli", "masternoder2-tx")

RELEASE_NOTES = """MasterNoder2 v1.3.1.0 — exchange / casino / payout sporks

- **SPORK_112_EXCHANGE_LIVE_TRADING** — network gate for live cross-venue exchange
- **SPORK_113_CASINO_REAL_MONEY** — casino real-money gate
- **SPORK_114_PAYOUT_LIVE** — live payout / sweep gate
- **SPORK_115_MAINTENANCE_MODE** — platform maintenance kill-switch
- Includes v1.3.0.0 multi-ping fleet (patches on v1.2.3.0 base)

Upgrade production (masternoder.dk):

```powershell
python scripts/mn2_daemon_upgrade_remote.py --apply --verify-post
python scripts/mn2_activate_spork_remote.py SPORK_112_EXCHANGE_LIVE_TRADING 1703122560
```
"""
