"""YouTube RTMP ingest without OBS — browser tab → ffmpeg → YouTube."""
from __future__ import annotations

import fcntl
import os
import shutil
import signal
import socket
import subprocess
import threading
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_PROC: Optional[subprocess.Popen] = None
_STDIN_LOCK = threading.Lock()

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA = os.path.join(_BASE, "data")
_DAEMON_LOCK = os.path.join(_DATA, "youtube_ingest_daemon.lock")
_DAEMON_PID = os.path.join(_DATA, "youtube_ingest_daemon.pid")
_DAEMON_SOCK = os.path.join(_DATA, "youtube_ingest.sock")
_USE_DAEMON = os.environ.get("YT_INGEST_IN_PROCESS", "").strip().lower() not in ("1", "true", "yes")


def _stream_key() -> str:
    return (os.environ.get("YOUTUBE_STREAM_KEY") or "").strip()


def _rtmp_url() -> str:
    key = _stream_key()
    if not key:
        return ""
    return f"rtmp://a.rtmp.youtube.com/live2/{key}"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_daemon_pid() -> Optional[int]:
    try:
        with open(_DAEMON_PID, encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _daemon_running() -> bool:
    pid = _read_daemon_pid()
    if pid and _pid_alive(pid):
        return os.path.exists(_DAEMON_SOCK)
    return False


def _start_daemon_locked() -> Dict[str, Any]:
    os.makedirs(_DATA, exist_ok=True)
    if _daemon_running():
        return {"success": True, "daemon_pid": _read_daemon_pid(), "already_running": True}

    key = _stream_key()
    if not key:
        return {
            "success": False,
            "error": "missing_stream_key",
            "hint": "Add YOUTUBE_STREAM_KEY to server .env (Studio → Streamindstillinger → streamnøgle). Never commit the key.",
        }
    if not shutil.which("ffmpeg"):
        return {
            "success": False,
            "error": "ffmpeg_not_found",
            "hint": "Install ffmpeg on the server or use browser-only Studio webcam go-live.",
        }

    env = os.environ.copy()
    env["YT_INGEST_BASE"] = _BASE
    log_path = os.path.join(_DATA, "youtube_ingest_daemon.log")
    try:
        logf = open(log_path, "a", encoding="utf-8")
    except OSError:
        logf = subprocess.DEVNULL  # type: ignore[assignment]

    py = os.environ.get("YT_INGEST_PYTHON") or shutil.which("python3") or "/usr/bin/python3"

    subprocess.Popen(
        [py, "-m", "backend.services.youtube_ingest_daemon"],
        cwd=_BASE,
        env=env,
        stdout=logf if logf != subprocess.DEVNULL else subprocess.DEVNULL,
        stderr=logf if logf != subprocess.DEVNULL else subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(40):
        if _daemon_running():
            return {"success": True, "daemon_pid": _read_daemon_pid(), "mode": "unix_socket_daemon"}
    return {
        "success": False,
        "error": "daemon_start_timeout",
        "hint": "Check data/youtube_ingest_daemon.log on the server.",
    }


def ensure_daemon() -> Dict[str, Any]:
    if not _USE_DAEMON:
        return {"success": True, "mode": "in_process"}
    os.makedirs(_DATA, exist_ok=True)
    lockf = open(_DAEMON_LOCK, "a+", encoding="utf-8")
    try:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        return _start_daemon_locked()
    finally:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
        lockf.close()


def stop_daemon() -> Dict[str, Any]:
    pid = _read_daemon_pid()
    if not pid or not _pid_alive(pid):
        return {"success": True, "stopped": False, "reason": "not_running"}
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        return {"success": False, "error": str(exc)[:120]}
    return {"success": True, "stopped": True, "daemon_pid": pid}


def _send_chunk_to_daemon(data: bytes) -> Dict[str, Any]:
    started = ensure_daemon()
    if not started.get("success"):
        return started
    if not os.path.exists(_DAEMON_SOCK):
        return {"success": False, "error": "ingest_socket_missing"}
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(30.0)
        sock.connect(_DAEMON_SOCK)
        sock.sendall(data)
        sock.close()
    except OSError as exc:
        return {"success": False, "error": f"socket_send:{exc}"[:160]}
    return {"success": True, "bytes": len(data), "via": "daemon"}


def ingest_status() -> Dict[str, Any]:
    if _USE_DAEMON:
        running = _daemon_running()
        pid = _read_daemon_pid() if running else None
        mode = "unix_socket_daemon"
    else:
        running = False
        pid = None
        if _PROC is not None and _PROC.poll() is None:
            running = True
            pid = _PROC.pid
        mode = "browser_webm_pipe"
    return {
        "success": True,
        "ffmpeg_path": shutil.which("ffmpeg"),
        "stream_key_configured": bool(_stream_key()),
        "running": running,
        "pid": pid,
        "mode": mode,
        "obs_required": False,
        "socket_path": _DAEMON_SOCK if _USE_DAEMON else None,
    }


def stop_ingest() -> Dict[str, Any]:
    global _PROC
    if _USE_DAEMON:
        return stop_daemon()
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
    """Start ingest (daemon + ffmpeg) before browser begins sending WebM chunks."""
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

    if _USE_DAEMON:
        res = ensure_daemon()
        if not res.get("success"):
            return res
        st = ingest_status()
        return {
            "success": True,
            "pid": st.get("pid"),
            "mode": st.get("mode"),
            "upload_path": "/api/exchange/fleet-stream/ingest/webm",
            "stop_path": "/api/exchange/fleet-stream/ingest/stop",
            "operator_steps": [
                "Click “Share monitor tab → YouTube” on the stream layout (browser capture).",
                "Pick the fleet monitor tab when Chrome asks what to share.",
                "When Studio shows video (not Ingen data), click Go live in YouTube Studio.",
            ],
        }

    with _LOCK:
        if _PROC is not None and _PROC.poll() is None:
            return {"success": True, "already_running": True, "pid": _PROC.pid}

        cmd = [
            ffm,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-fflags",
            "+genpts",
            "-probesize",
            "32M",
            "-analyzeduration",
            "5M",
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
    if _USE_DAEMON:
        if not _daemon_running():
            started = start_ingest()
            if not started.get("success"):
                return started
        return _send_chunk_to_daemon(data)

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
