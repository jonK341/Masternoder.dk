"""YouTube RTMP ingest without OBS — browser tab → ffmpeg → YouTube."""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_PROC: Optional[subprocess.Popen] = None
_STDIN_LOCK = threading.Lock()


def _stream_key() -> str:
    return (os.environ.get("YOUTUBE_STREAM_KEY") or "").strip()


def _rtmp_url() -> str:
    key = _stream_key()
    if not key:
        return ""
    return f"rtmp://a.rtmp.youtube.com/live2/{key}"


def ingest_status() -> Dict[str, Any]:
    running = False
    pid = None
    if _PROC is not None and _PROC.poll() is None:
        running = True
        pid = _PROC.pid
    return {
        "success": True,
        "ffmpeg_path": shutil.which("ffmpeg"),
        "stream_key_configured": bool(_stream_key()),
        "running": running,
        "pid": pid,
        "mode": "browser_webm_pipe",
        "obs_required": False,
    }


def stop_ingest() -> Dict[str, Any]:
    global _PROC
    with _LOCK:
        if _PROC is None:
            return {"success": True, "stopped": False, "reason": "not_running"}
        try:
            if _PROC.stdin:
                _PROC.stdin.close()
        except Exception:
            pass
        try:
            _PROC.terminate()
            _PROC.wait(timeout=8)
        except Exception:
            try:
                _PROC.kill()
            except Exception:
                pass
        _PROC = None
    return {"success": True, "stopped": True}


def start_ingest() -> Dict[str, Any]:
    """Start ffmpeg reading WebM chunks from stdin → YouTube RTMP."""
    global _PROC
    key = _stream_key()
    if not key:
        return {
            "success": False,
            "error": "missing_stream_key",
            "hint": "Add YOUTUBE_STREAM_KEY to server .env (Studio → Streamindstillinger → streamnøgle). Never commit the key.",
        }
    ffm = shutil.which("ffmpeg")
    if not ffm:
        return {
            "success": False,
            "error": "ffmpeg_not_found",
            "hint": "Install ffmpeg on the server or use browser-only Studio webcam go-live.",
        }

    with _LOCK:
        if _PROC is not None and _PROC.poll() is None:
            return {"success": True, "already_running": True, "pid": _PROC.pid}

        cmd = [
            ffm,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-f",
            "webm",
            "-i",
            "pipe:0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-maxrate",
            "4500k",
            "-bufsize",
            "9000k",
            "-pix_fmt",
            "yuv420p",
            "-g",
            "60",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-f",
            "flv",
            _rtmp_url(),
        ]
        try:
            _PROC = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except Exception as exc:
            _PROC = None
            return {"success": False, "error": str(exc)[:200]}

    return {
        "success": True,
        "pid": _PROC.pid if _PROC else None,
        "upload_path": "/api/exchange/fleet-stream/ingest/webm",
        "stop_path": "/api/exchange/fleet-stream/ingest/stop",
        "operator_steps": [
            "Click “Share monitor tab → YouTube” on the stream layout (browser capture).",
            "Pick the fleet monitor tab when Chrome asks what to share.",
            "When Studio shows video (not Ingen data), click Go live in YouTube Studio.",
        ],
    }


def write_webm_chunk(data: bytes) -> Dict[str, Any]:
    if not data:
        return {"success": False, "error": "empty_chunk"}
    if _PROC is None or _PROC.poll() is not None:
        started = start_ingest()
        if not started.get("success"):
            return started
    try:
        with _STDIN_LOCK:
            if _PROC and _PROC.stdin:
                _PROC.stdin.write(data)
                _PROC.stdin.flush()
    except Exception as exc:
        return {"success": False, "error": str(exc)[:160]}
    return {"success": True, "bytes": len(data)}


def no_obs_playbook() -> Dict[str, Any]:
    from backend.services.fleet_stream_chat_service import live_config

    live = live_config()
    rtmp = live.get("youtube_rtmp") if isinstance(live.get("youtube_rtmp"), dict) else {}
    st = ingest_status()
    return {
        "success": True,
        "obs_required": False,
        "recommended": "browser_tab_capture",
        "alternatives": [
            {
                "id": "browser_tab",
                "label": "Share monitor tab (built-in, no OBS)",
                "requires": ["YOUTUBE_STREAM_KEY on server", "ffmpeg on server", "Chrome/Edge tab capture"],
            },
            {
                "id": "youtube_webcam",
                "label": "YouTube Studio webcam go-live",
                "note": "Shows camera only — not the 5D monitor.",
            },
            {
                "id": "streamlabs",
                "label": "Streamlabs Desktop (free OBS replacement)",
                "url": "https://streamlabs.com/",
            },
        ],
        "rtmp_server": rtmp.get("server_url") or "rtmp://a.rtmp.youtube.com/live2",
        "ingest": st,
    }
