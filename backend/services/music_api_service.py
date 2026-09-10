"""
Music generation hook — Suno API (when keyed) + Replicate MusicGen fallback.

Priority:
  1. Suno-compatible API (SUNO_API_KEY + optional SUNO_API_BASE)
  2. Replicate meta/musicgen (REPLICATE_API_TOKEN)
  3. Caller falls back to TTS / tone in super_encoder_service

Suno hook uses the common unofficial REST shape:
  POST {base}/api/generate  →  poll GET {base}/api/get?ids=...
Configure SUNO_API_BASE e.g. https://your-suno-proxy.example (no trailing slash).
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

try:
    import requests as _requests
    _USE_REQUESTS = True
except ImportError:
    _USE_REQUESTS = False

POLL_INTERVAL = 8
MAX_POLL_SEC = 240
MUSICGEN_VERSION = "671ac645ce5e552cc63a54a2bbff63eae798772327169f0724096d944b5d0886c"


def _suno_key() -> str:
    return (os.environ.get("SUNO_API_KEY") or os.environ.get("SUNO_COOKIE") or "").strip()


def _suno_base() -> str:
    return (os.environ.get("SUNO_API_BASE") or "").strip().rstrip("/")


def _replicate_key() -> str:
    return (os.environ.get("REPLICATE_API_TOKEN") or "").strip()


def is_suno_available() -> bool:
    return bool(_suno_key() and _suno_base())


def is_replicate_music_available() -> bool:
    return bool(_replicate_key())


def _suno_status() -> Dict[str, Any]:
    key = _suno_key()
    base = _suno_base()
    missing = []
    if not key:
        missing.append("SUNO_API_KEY")
    if not base:
        missing.append("SUNO_API_BASE")
    return {
        "available": bool(key and base),
        "configured": bool(key and base),
        "base": base or None,
        "has_key": bool(key),
        "missing": missing,
        "setup": (
            "Set SUNO_API_KEY and SUNO_API_BASE in /var/www/html/.env, then restart uwsgi-vidgenerator. "
            "Use a Suno-compatible proxy (e.g. https://github.com/gcui-art/suno-api) — no official public API."
            if missing
            else None
        ),
    }


def get_music_provider_status() -> Dict[str, Any]:
    suno = _suno_status()
    replicate_ok = is_replicate_music_available()
    preferred = (
        "suno" if suno["available"]
        else "replicate_musicgen" if replicate_ok
        else "tts_fallback"
    )
    return {
        "success": True,
        "suno": suno,
        "replicate_musicgen": {"available": replicate_ok},
        "preferred": preferred,
        "fallback_chain": ["suno", "replicate_musicgen", "tts"],
    }


def _http_json(method: str, url: str, headers: dict, payload: Optional[dict] = None, timeout: int = 60) -> dict:
    if _USE_REQUESTS:
        if method.upper() == "POST":
            r = _requests.post(url, headers=headers, json=payload or {}, timeout=timeout)
        else:
            r = _requests.get(url, headers=headers, timeout=timeout)
        return r.json()
    body = json.dumps(payload or {}).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=body, method=method.upper())
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _download_url(url: str, dest_path: str) -> bool:
    try:
        if _USE_REQUESTS:
            r = _requests.get(url, timeout=120)
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(r.content)
        else:
            with urllib.request.urlopen(url, timeout=120) as resp:
                with open(dest_path, "wb") as f:
                    f.write(resp.read())
        return os.path.isfile(dest_path) and os.path.getsize(dest_path) > 500
    except Exception:
        return False


def _generate_suno(
    prompt: str,
    title: str,
    genre: str,
    dest_path: str,
    duration_sec: int = 60,
) -> Optional[str]:
    """Suno-compatible API generate + poll."""
    key = _suno_key()
    base = _suno_base()
    if not key or not base:
        return None
    tags = f"{genre}, {title}"[:200]
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if key.startswith("Bearer "):
        headers["Authorization"] = key
    try:
        gen = _http_json(
            "POST",
            f"{base}/api/generate",
            headers,
            {
                "prompt": prompt[:500],
                "title": title[:80],
                "tags": tags,
                "make_instrumental": False,
                "wait_audio": False,
            },
        )
        ids = []
        if isinstance(gen, list):
            ids = [g.get("id") for g in gen if isinstance(g, dict) and g.get("id")]
        elif isinstance(gen, dict):
            if gen.get("id"):
                ids = [gen["id"]]
            data = gen.get("data")
            if isinstance(data, list):
                ids = [d.get("id") for d in data if isinstance(d, dict) and d.get("id")]
        if not ids:
            return None

        deadline = time.time() + MAX_POLL_SEC
        audio_url = None
        while time.time() < deadline:
            time.sleep(POLL_INTERVAL)
            q = urllib.parse.urlencode({"ids": ",".join(ids[:2])})
            status = _http_json("GET", f"{base}/api/get?{q}", headers)
            rows = status if isinstance(status, list) else status.get("data") or [status]
            for row in rows:
                if not isinstance(row, dict):
                    continue
                st = (row.get("status") or "").lower()
                audio_url = row.get("audio_url") or row.get("video_url")
                if st in ("complete", "completed", "success") and audio_url:
                    break
                if row.get("metadata") and isinstance(row["metadata"], dict):
                    audio_url = audio_url or row["metadata"].get("audio_url")
            if audio_url:
                break
        if audio_url and _download_url(audio_url, dest_path):
            return dest_path
    except Exception:
        pass
    return None


def _replicate_post(api_key: str, payload: dict) -> dict:
    url = "https://api.replicate.com/v1/predictions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    return _http_json("POST", url, headers, payload)


def _replicate_get(api_key: str, prediction_id: str) -> dict:
    url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    return _http_json("GET", url, headers)


def _generate_replicate_musicgen(
    prompt: str,
    dest_path: str,
    duration_sec: int = 30,
) -> Optional[str]:
    api_key = _replicate_key()
    if not api_key:
        return None
    try:
        dur = max(5, min(30, int(duration_sec or 30)))
        pred = _replicate_post(api_key, {
            "version": MUSICGEN_VERSION,
            "input": {
                "prompt": prompt[:500],
                "duration": dur,
                "model_version": "stereo-large",
                "output_format": "mp3",
                "normalization_strategy": "peak",
            },
        })
        pred_id = pred.get("id")
        if not pred_id:
            return None
        deadline = time.time() + MAX_POLL_SEC
        output_url = None
        while time.time() < deadline:
            time.sleep(POLL_INTERVAL)
            row = _replicate_get(api_key, pred_id)
            st = (row.get("status") or "").lower()
            if st == "succeeded":
                out = row.get("output")
                if isinstance(out, str):
                    output_url = out
                elif isinstance(out, list) and out:
                    output_url = out[0]
                break
            if st in ("failed", "canceled"):
                return None
        if output_url and _download_url(output_url, dest_path):
            return dest_path
    except Exception:
        pass
    return None


def generate_music(
    prompt: str,
    title: str,
    genre: str,
    dest_path: str,
    duration_sec: int = 60,
) -> Dict[str, Any]:
    """
    Generate music file at dest_path.
    Returns { success, path, provider, error }.
    """
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    full_prompt = f"{title} — {genre} song. {prompt}"[:800]

    if is_suno_available():
        path = _generate_suno(full_prompt, title, genre, dest_path, duration_sec)
        if path:
            return {"success": True, "path": path, "provider": "suno"}

    if is_replicate_music_available():
        path = _generate_replicate_musicgen(full_prompt, dest_path, duration_sec)
        if path:
            return {"success": True, "path": path, "provider": "replicate_musicgen"}

    return {
        "success": False,
        "error": "No music API configured. Set SUNO_API_KEY+SUNO_API_BASE or REPLICATE_API_TOKEN.",
        "provider": None,
    }
