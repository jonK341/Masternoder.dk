"""Shared constants for MasterNoder2 v1.2.3.0 release pipeline."""
from __future__ import annotations

REPO = "jonK341/MasterNoder2"
TARGET_VERSION = "v1.2.3.0"
MAIN_COMMIT = "61caddbfd3c8f4465012d1033206501fb6690b14"
RELEASE_BASE = f"https://github.com/{REPO}/releases/download/{TARGET_VERSION}"
TARBALL_NAME = "masternoder2d.tar.gz"
MANIFEST_NAME = "RELEASE_MANIFEST.json"
RELEASE_URL = f"{RELEASE_BASE}/{TARBALL_NAME}"
MANIFEST_URL = f"{RELEASE_BASE}/{MANIFEST_NAME}"

BINARIES = ("masternoder2d", "masternoder2-cli", "masternoder2-tx")

RELEASE_NOTES = """MasterNoder2 v1.2.3.0

- mnsync MNW deadlock fix (small-network / single-masternode sync)
- getstakinginfo RPC alias for getstakingstatus (explorer + app health)

Upgrade production (masternoder.dk):

```powershell
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --verify-post
```
"""
