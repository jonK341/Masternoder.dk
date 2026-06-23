"""Shared constants for MasterNoder2 release pipeline (v1.3.0.0 multi-ping)."""
from __future__ import annotations

REPO = "jonK341/MasterNoder2"
TARGET_VERSION = "v1.3.0.0"
BASE_TAG = "v1.2.3.0"
PATCH_REL = "docs/patches/mn2-daemon-v1.3.0-multi-ping.patch"
# Populated from RELEASE_MANIFEST.json after build; fallback for tag-only releases.
MAIN_COMMIT = "61caddbfd3c8f4465012d1033206501fb6690b14"
RELEASE_BASE = f"https://github.com/{REPO}/releases/download/{TARGET_VERSION}"
TARBALL_NAME = "masternoder2d.tar.gz"
MANIFEST_NAME = "RELEASE_MANIFEST.json"
RELEASE_URL = f"{RELEASE_BASE}/{TARBALL_NAME}"
MANIFEST_URL = f"{RELEASE_BASE}/{MANIFEST_NAME}"

BINARIES = ("masternoder2d", "masternoder2-cli", "masternoder2-tx")

RELEASE_NOTES = """MasterNoder2 v1.3.0.0 — multi-ping

- One daemon pings every registered masternode.conf alias (hosting fleet)
- `startmasternode alias|all|local` registers ping targets when `-mnmultiping=1`
- `ManageExtraPingTargets()` in the main ping cycle
- Version **1.3.0.0** (patch on v1.2.3.0 base until upstream tag ships)

Upgrade production (masternoder.dk):

```powershell
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply --verify-post
python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking
python scripts/mn2_probe_multi_ping.py --public
# After QA: set ops.multi_ping_enabled=true in data/mn2_masternode_config.json + deploy mn2_staking
```
"""
