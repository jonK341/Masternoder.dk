"""MN2 desktop wallet / daemon release catalog for the public download UI."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MANIFEST_PATH = os.path.join(_BASE, "dist", "RELEASE_MANIFEST.json")
TARGET_VERSION = "v1.3.0.0"
QT_FALLBACK_TAG = "v1.2.2.0"
RELEASE_BASE = f"https://github.com/jonK341/MasterNoder2/releases/download/{TARGET_VERSION}"
QT_FALLBACK_BASE = f"https://github.com/jonK341/MasterNoder2/releases/download/{QT_FALLBACK_TAG}"

# Qt GUI builds published on v1.2.2.0 until v1.3 Qt packages ship on GitHub releases.
QT_KNOWN: Dict[str, Dict[str, Any]] = {
    "MasterNoder2-qt-win.zip": {
        "sha256": "0686144133367ed1408c67a7344d17f6fbfdf5135351c0aeec5ae093b99ef83e",
        "size_bytes": 20553825,
        "fallback_tag": QT_FALLBACK_TAG,
    },
    "MasterNoder2-qt-linux.tar.gz": {
        "sha256": "0c6ba20f4bc50abcad037409fd7402d110c51dafd906abd3befcbfae0ac606cb",
        "size_bytes": 23559943,
        "fallback_tag": QT_FALLBACK_TAG,
    },
}


def _read_manifest() -> Dict[str, Any]:
    if not os.path.isfile(_MANIFEST_PATH):
        return {}
    try:
        with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _asset_url(filename: str) -> str:
    return f"{RELEASE_BASE.rstrip('/')}/{filename}"


def get_release_catalog() -> Dict[str, Any]:
    """Build download catalog for /wallets and GET /api/mn2/releases."""
    manifest = _read_manifest()
    version = (manifest.get("git_tag") or manifest.get("version") or TARGET_VERSION).lstrip("v")
    tag = f"v{version}" if not str(manifest.get("git_tag") or TARGET_VERSION).startswith("v") else (manifest.get("git_tag") or TARGET_VERSION)
    base = RELEASE_BASE
    if manifest.get("git_tag") and manifest["git_tag"] != TARGET_VERSION:
        base = f"https://github.com/jonK341/MasterNoder2/releases/download/{manifest['git_tag']}"

    tarball_sha = manifest.get("tarball_sha256")
    binaries = manifest.get("binaries") or {}
    qt_assets = manifest.get("qt_assets") if isinstance(manifest.get("qt_assets"), dict) else {}

    def _qt_meta(filename: str) -> Dict[str, Any]:
        known = dict(QT_KNOWN.get(filename) or {})
        man = qt_assets.get(filename) if isinstance(qt_assets.get(filename), dict) else {}
        known.update({k: v for k, v in man.items() if v is not None})
        return known

    def _qt_url(filename: str) -> tuple:
        meta = _qt_meta(filename)
        fb_tag = meta.get("fallback_tag") or QT_FALLBACK_TAG
        # v1.3.0.0 release ships daemon only — Qt downloads use last known GUI tag.
        if tag == TARGET_VERSION and filename.startswith("MasterNoder2-qt"):
            fb_base = f"https://github.com/jonK341/MasterNoder2/releases/download/{fb_tag}"
            return f"{fb_base.rstrip('/')}/{filename}", fb_tag
        return f"{base.rstrip('/')}/{filename}", tag

    downloads: List[Dict[str, Any]] = [
        {
            "id": "daemon_linux",
            "name": "MasterNoder2 Daemon",
            "platform": "Linux / WSL / VPS",
            "format": "tar.gz",
            "filename": "masternoder2d.tar.gz",
            "description": "Headless node for servers, staking, and RPC. Recommended for masternode operators and developers.",
            "recommended_for": ["Server hosting", "RPC / deposits", "Masternode fleet"],
            "url": f"{base.rstrip('/')}/masternoder2d.tar.gz",
            "sha256": tarball_sha,
            "size_bytes": None,
            "icon": "🖥️",
        },
        {
            "id": "qt_windows",
            "name": "MasterNoder2 Core (Qt)",
            "platform": "Windows 64-bit",
            "format": "zip",
            "filename": "MasterNoder2-qt-win.zip",
            "description": "Graphical wallet for Windows. Sync the chain, send/receive MN2, and run with server=1 for local RPC.",
            "recommended_for": ["Desktop users", "Visual wallet", "Windows without WSL"],
            "url": _qt_url("MasterNoder2-qt-win.zip")[0],
            "sha256": _qt_meta("MasterNoder2-qt-win.zip").get("sha256"),
            "size_bytes": _qt_meta("MasterNoder2-qt-win.zip").get("size_bytes"),
            "release_tag": _qt_url("MasterNoder2-qt-win.zip")[1],
            "icon": "🪟",
        },
        {
            "id": "qt_linux",
            "name": "MasterNoder2 Core (Qt)",
            "platform": "Linux desktop",
            "format": "tar.gz",
            "filename": "MasterNoder2-qt-linux.tar.gz",
            "description": "Graphical wallet for Linux desktops. Same features as the Windows build.",
            "recommended_for": ["Linux desktop", "GUI preference"],
            "url": _qt_url("MasterNoder2-qt-linux.tar.gz")[0],
            "sha256": _qt_meta("MasterNoder2-qt-linux.tar.gz").get("sha256"),
            "size_bytes": _qt_meta("MasterNoder2-qt-linux.tar.gz").get("size_bytes"),
            "release_tag": _qt_url("MasterNoder2-qt-linux.tar.gz")[1],
            "icon": "🐧",
        },
    ]

    cli = binaries.get("masternoder2-cli") or {}
    if cli.get("sha256"):
        downloads[0]["binaries_note"] = {
            "masternoder2d": (binaries.get("masternoder2d") or {}).get("sha256"),
            "masternoder2-cli": cli.get("sha256"),
        }

    return {
        "success": True,
        "version": tag,
        "release_base": base,
        "github_releases": "https://github.com/jonK341/MasterNoder2/releases",
        "built_at": manifest.get("built_at"),
        "git_sha": manifest.get("git_sha"),
        "downloads": downloads,
        "verify_hint": "After download, compare SHA256 with the value shown here or on the GitHub release page.",
        "docs": {
            "setup": "/docs/MN2_DAEMON_SETUP.md",
            "config_example": "config/masternoder2.conf.example",
            "network_peers": "/api/mn2/network-peers",
        },
        "network": {
            "p2p_port": 17646,
            "rpc_port": 9332,
            "peers_api": "/api/mn2/network-peers",
        },
    }
