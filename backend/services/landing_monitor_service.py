"""Landing-page live monitor — stats snapshot, specials, lightshow, effect explain."""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CACHE_PATH = os.path.join(_BASE, "data", "landing_monitor_cache.json")

BPM = 180
BEAT_MS = int(round(60_000 / BPM))  # ~333ms

LIGHTSHOWS: List[Dict[str, Any]] = [
    {
        "id": "pulse",
        "name": "Pulse Lightshow",
        "explain": "Smooth sine pulse locked to 180 BPM — each beat lifts intensity then eases out.",
        "safety": "Gentle; fine for most visitors.",
    },
    {
        "id": "wave",
        "name": "Wave Lightshow",
        "explain": "Horizontal color waves travel across the monitor on every eighth-note.",
        "safety": "Low flicker risk.",
    },
    {
        "id": "spectrum",
        "name": "Spectrum Lightshow",
        "explain": "Bars react to the generative AI music envelope at 180 BPM.",
        "safety": "Visual only; audio is opt-in.",
    },
    {
        "id": "chase",
        "name": "Chase Lightshow",
        "explain": "Nodes chase around the bezel — one step per beat for a club-style ring.",
        "safety": "Avoid if sensitive to moving lights.",
    },
    {
        "id": "rainbow",
        "name": "Rainbow Lightshow",
        "explain": "Hue rotates through the spectrum once every 16 bars (≈5.3s at 180 BPM).",
        "safety": "Colorful but not strobing.",
    },
]

SPECIALS: List[Dict[str, Any]] = [
    {
        "id": "wallet",
        "title": "New wallet arrived",
        "body": "Linux + Windows Qt, Flatpak daemon, and source on GitHub Latest.",
        "href": "/wallets",
        "cta": "Open wallets",
    },
    {
        "id": "profit-jon",
        "title": "Profit Daemon Jon",
        "body": "24/7 profit loops — download the desktop daemon and watch the live monitor.",
        "href": "/profit/",
        "cta": "Profit monitor",
    },
    {
        "id": "generator",
        "title": "AI video generator",
        "body": "Spin a clip from the flagship generator — music + lightshow keep the lobby warm.",
        "href": "/generator",
        "cta": "Start generator",
    },
    {
        "id": "battle",
        "title": "Battle arena",
        "body": "Climb the ladder while the 180 BPM lobby pulse keeps score energy high.",
        "href": "/battle",
        "cta": "Enter battle",
    },
    {
        "id": "mn2",
        "title": "Pay with MN2",
        "body": "On-chain balance on the site — deposit, shop, stake, and casino rails.",
        "href": "/shop",
        "cta": "Shop MN2",
    },
]


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_cache() -> Dict[str, Any]:
    if not os.path.isfile(_CACHE_PATH):
        return {}
    try:
        with open(_CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_cache(payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    tmp = _CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, _CACHE_PATH)


def _price_from_disk() -> Any:
    for rel in (
        "data/mn2_price_cache.json",
        "data/mn2_network_snapshot.json",
        "data/landing_monitor_cache.json",
    ):
        path = os.path.join(_BASE, rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            if not isinstance(doc, dict):
                continue
            for key in ("mn2_usd_price", "price"):
                val = doc.get(key)
                if isinstance(val, (int, float)):
                    return float(val)
            stats = doc.get("stats") if isinstance(doc.get("stats"), dict) else {}
            val = stats.get("mn2_usd_price")
            if isinstance(val, (int, float)):
                return float(val)
        except Exception:
            continue
    return None


def _collect_stats() -> Dict[str, Any]:
    """Fast stats only — no external HTTP; RPC uses a hard short timeout."""
    stats: Dict[str, Any] = {
        "total_videos": 0,
        "total_users": 0,
        "total_achievements": 0,
        "total_battles": 0,
        "mn2_usd_price": _price_from_disk(),
        "daemon_ok": None,
    }
    try:
        from flask import has_app_context
        from src.db.models import Documentary, UserProfile

        if has_app_context():
            stats["total_videos"] = int(Documentary.query.count())
            try:
                stats["total_users"] = int(UserProfile.query.count())
            except Exception:
                pass
    except Exception:
        pass
    try:
        from backend.services.quick_battle_system import quick_battle

        battle_stats = quick_battle.get_user_battle_stats("default_user") or {}
        stats["total_battles"] = int(battle_stats.get("total_battles") or 0)
    except Exception:
        pass
    try:
        from backend.services import mn2_rpc_client as rpc

        info = rpc.getblockcount(timeout_sec=0.4) or {}
        stats["daemon_ok"] = info.get("error") is None and info.get("result") is not None
        if stats["daemon_ok"]:
            stats["block_height"] = info.get("result")
    except Exception:
        stats["daemon_ok"] = None
    return stats


def _pick_rotating(items: List[Dict[str, Any]], period_sec: float) -> Dict[str, Any]:
    if not items:
        return {}
    idx = int(time.time() // max(1.0, period_sec)) % len(items)
    return dict(items[idx])


def refresh_snapshot(*, force: bool = False) -> Dict[str, Any]:
    """Rebuild cache. Safe to call from cron every ~5s."""
    with _LOCK:
        cached = _read_cache()
        age = time.time() - float(cached.get("epoch") or 0)
        if not force and cached and age < 4.0:
            return cached

        lightshow = _pick_rotating(LIGHTSHOWS, 12.0)
        special = _pick_rotating(SPECIALS, 8.0)

        actions_blob: Dict[str, Any] = {"actions": [], "learning": {}, "reel": []}
        try:
            from backend.services import landing_monitor_actions_service as acts

            # Keep the monitor synchronized with platform activity.
            acts.sync_from_activity(limit=30)
            listed = acts.list_actions(limit=12)
            learn = acts.learning_snapshot()
            reel = acts.build_reel(limit=16, prefer_unplayed=True)
            actions_blob = {
                "actions": listed.get("actions") or [],
                "learning": (learn.get("learning") or {}),
                "reel": reel.get("reel") or [],
                "reel_count": reel.get("count") or 0,
            }
            # If a reel scene is waiting, prefer its category FX on the live bezel.
            if actions_blob["reel"]:
                head = actions_blob["reel"][0]
                fx = head.get("fx") if isinstance(head.get("fx"), dict) else {}
                lid = fx.get("lightshow")
                if lid:
                    lightshow = next((x for x in LIGHTSHOWS if x.get("id") == lid), lightshow)
                    lightshow = dict(lightshow)
                    lightshow["explain"] = fx.get("explain") or lightshow.get("explain")
                    lightshow["name"] = fx.get("title") or lightshow.get("name")
        except Exception:
            pass

        payload = {
            "success": True,
            "epoch": time.time(),
            "updated_at": _iso(),
            "refresh_ms": 5000,
            "bpm": BPM,
            "beat_ms": BEAT_MS,
            "stats": _collect_stats(),
            "special": special,
            "specials": SPECIALS,
            "lightshow": lightshow,
            "lightshows": LIGHTSHOWS,
            "effect_explain": {
                "title": lightshow.get("name") or "Lightshow",
                "body": lightshow.get("explain") or "",
                "safety": lightshow.get("safety") or "",
                "bpm": BPM,
            },
            "music": {
                "mode": "ai_generative_180",
                "label": "AI generative lobby (180 BPM)",
                "opt_in": True,
                "bpm": BPM,
                "bars": 4,
                "scale": ["A3", "C4", "E4", "G4", "A4", "C5"],
                "explain": "Browser-side generative synth — no upload; starts only after you tap Play music.",
            },
            "actions": actions_blob.get("actions") or [],
            "learning": actions_blob.get("learning") or {},
            "reel": actions_blob.get("reel") or [],
            "reel_count": actions_blob.get("reel_count") or 0,
        }
        _write_cache(payload)
        return payload


def get_snapshot(*, max_age_sec: float = 8.0) -> Dict[str, Any]:
    cached = _read_cache()
    age = time.time() - float(cached.get("epoch") or 0)
    if not cached or age > max_age_sec:
        return refresh_snapshot(force=True)
    cached["success"] = True
    cached["cache_age_sec"] = round(age, 2)
    return cached
