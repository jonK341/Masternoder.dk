"""Singleton YouTube ingest: unix socket → ffmpeg → RTMP (survives multi-worker uWSGI)."""
from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
from typing import Optional

_BASE = os.environ.get("YT_INGEST_BASE") or "/var/www/html"
DATA_DIR = os.path.join(_BASE, "data")
SOCK_PATH = os.path.join(DATA_DIR, "youtube_ingest.sock")
PID_PATH = os.path.join(DATA_DIR, "youtube_ingest_daemon.pid")
LOG_PATH = os.path.join(DATA_DIR, "youtube_ingest_daemon.log")


def _log(msg: str) -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except OSError:
        pass


def _stream_key() -> str:
    return (os.environ.get("YOUTUBE_STREAM_KEY") or "").strip()


def _rtmp_url() -> str:
    key = _stream_key()
    if not key:
        return ""
    return f"rtmp://a.rtmp.youtube.com/live2/{key}"


def _ffmpeg_cmd() -> list[str]:
    ffm = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
    return [
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


def _drain_stderr(proc: subprocess.Popen) -> None:
    if not proc.stderr:
        return
    try:
        for line in proc.stderr:
            _log("[ffmpeg] " + line.decode("utf-8", errors="replace").rstrip())
    except Exception:
        pass


def main() -> int:
    key = _stream_key()
    if not key:
        _log("daemon exit: missing YOUTUBE_STREAM_KEY")
        return 1
    if not shutil.which("ffmpeg"):
        _log("daemon exit: ffmpeg not found")
        return 1

    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        os.unlink(SOCK_PATH)
    except FileNotFoundError:
        pass

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK_PATH)
    os.chmod(SOCK_PATH, 0o666)
    srv.listen(32)

    with open(PID_PATH, "w", encoding="utf-8") as pf:
        pf.write(str(os.getpid()))

    _log(f"daemon listening {SOCK_PATH} pid={os.getpid()}")

    proc: Optional[subprocess.Popen] = None
    write_lock = threading.Lock()

    def ensure_ffmpeg() -> Optional[subprocess.Popen]:
        nonlocal proc
        if proc is not None and proc.poll() is None:
            return proc
        if proc is not None:
            _log(f"ffmpeg exited code={proc.returncode}")
        try:
            proc = subprocess.Popen(
                _ffmpeg_cmd(),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            threading.Thread(target=_drain_stderr, args=(proc,), daemon=True).start()
            _log(f"ffmpeg started pid={proc.pid}")
        except Exception as exc:
            _log(f"ffmpeg start failed: {exc}")
            proc = None
        return proc

    def handle_conn(conn: socket.socket) -> None:
        try:
            p = ensure_ffmpeg()
            if not p or not p.stdin:
                return
            while True:
                chunk = conn.recv(262144)
                if not chunk:
                    break
                with write_lock:
                    if p.poll() is not None:
                        p = ensure_ffmpeg()
                        if not p or not p.stdin:
                            break
                    p.stdin.write(chunk)
                    p.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            _log(f"conn write error: {exc}")
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def shutdown(*_args) -> None:
        _log("daemon shutdown")
        try:
            srv.close()
        except OSError:
            pass
        if proc and proc.poll() is None:
            try:
                if proc.stdin:
                    proc.stdin.close()
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        try:
            os.unlink(SOCK_PATH)
        except FileNotFoundError:
            pass
        try:
            os.unlink(PID_PATH)
        except FileNotFoundError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handle_conn, args=(conn,), daemon=True).start()
    except OSError:
        shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
