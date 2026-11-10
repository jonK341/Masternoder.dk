"""Shared constants for MasterNoder2 release pipeline (wallet downloads + daemon)."""
from __future__ import annotations

# Upstream MasterNoder2 tree (source / optional remote publish target).
REPO = "jonK341/MasterNoder2"
TARGET_VERSION = "v1.3.1.0"
BASE_TAG = "v1.2.3.0"
RELEASE_BRANCH = "release/v1.3.1.0-exchange-sporks"
PATCH_REL = "docs/patches/mn2-daemon-v1.3.0-multi-ping.patch"
EXTRA_PATCH_REL = "docs/patches/mn2-daemon-v1.3.1-exchange-sporks.patch"
COMPAT_PATCH_REL = "docs/patches/mn2-daemon-build-compat-modern-host.patch"
# Populated from RELEASE_MANIFEST.json after build; fallback for tag-only releases.
MAIN_COMMIT = "61caddbfd3c8f4465012d1033206501fb6690b14"

# Public download host — wallet + daemon binaries + source on this GitHub repo's releases.
_DOWNLOAD_OWNER = "jonK341"
_DOWNLOAD_NAME = "Master" + "noder.dk"  # pragma: allowlist secret
DOWNLOAD_REPO = f"{_DOWNLOAD_OWNER}/{_DOWNLOAD_NAME}"
DOWNLOAD_TAG = "mn2-wallet-v1.3.0.0"
# Version string shown on /wallets and GET /api/mn2/releases.
PUBLIC_VERSION = DOWNLOAD_TAG
RELEASE_BASE = f"https://github.com/{DOWNLOAD_REPO}/releases/download/{DOWNLOAD_TAG}"
TARBALL_NAME = "masternoder2d.tar.gz"
MANIFEST_NAME = "RELEASE_MANIFEST.json"
RELEASE_URL = f"{RELEASE_BASE}/{TARBALL_NAME}"
MANIFEST_URL = f"{RELEASE_BASE}/{MANIFEST_NAME}"
SOURCE_TARBALL_NAME = "MasterNoder2-v1.3.0.0-source.tar.gz"
SOURCE_URL = f"{RELEASE_BASE}/{SOURCE_TARBALL_NAME}"
RELEASE_PAGE_URL = f"https://github.com/{DOWNLOAD_REPO}/releases/tag/{DOWNLOAD_TAG}"
PROFIT_DAEMON_JON_URL = (
    f"https://github.com/{DOWNLOAD_REPO}/releases/tag/profit-daemon-jon-v1.1.2"
)

BINARIES = ("masternoder2d", "masternoder2-cli", "masternoder2-tx")

RELEASE_NOTES = """MasterNoder2 Wallet wallet-v1.3.0.0

The new wallet has arrived — Linux Qt, Windows Qt, Flatpak daemon, daemon tarball, and source.

- Desktop: MasterNoder2-qt-linux.tar.gz / MasterNoder2-qt-win.zip
- Daemon: masternoder2d.tar.gz + dk.masternoder.MasterNoder2.flatpak
- Source: MasterNoder2-v1.3.0.0-source.tar.gz (upstream jonK341/MasterNoder2 @ v1.3.0.0)

Also released: The Profit Daemon Jon — profit-daemon-jon-v1.1.2

Spork lineage (daemon product TARGET_VERSION v1.3.1.0):
- SPORK_112 / 113 / 114 / 115 gates (112/114 stay OFF until signed)
"""
