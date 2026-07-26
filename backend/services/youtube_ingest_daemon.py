"""Singleton YouTube ingest: unix socket → ffmpeg → RTMP (survives multi-worker uWSGI)."""
from __future__ import annotations

import os
import queue
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from typing import Optional

_BASE = os.environ.get("YT_INGEST_BASE") or "/var/www/html"
DATA_DIR = os.path.join(_BASE, "data")
SOCK_PATH = os.path.join(DATA_DIR, "youtube_ingest.sock")
PID_PATH = os.path.join(DATA_DIR, "youtube_ingest_daemon.pid")
LOG_PATH = os.path.join(DATA_DIR, "youtube_ingest_daemon.log")
STATS_PATH = os.path.join(DATA_DIR, "youtube_ingest_stats.json")

EBML_MAGIC = b"\x1aE\xdf\xa3"
_PROC_LOCK = threading.Lock()


def _log(msg: str) -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except OSError:
        pass


def _write_stats(payload: dict) -> None:
    try:
        import json

        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f)
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
        "+genpts+discardcorrupt",
        "-probesize",
        "32M",
        "-analyzeduration",
        "5M",
        "-f",
        "matroska",
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
        "-ar",
        "48000",
        "-f",
        "flv",
        _rtmp_url(),
    ]


class IngestEngine:
    def __init__(self) -> None:
        self.proc: Optional[subprocess.Popen] = None
        self.need_init = True
        self.bytes_in = 0
        self.chunks_in = 0
        self.last_chunk_at: Optional[float] = None
        self.ffmpeg_started_at: Optional[float] = None
        self._q: queue.Queue[Optional[bytes]] = queue.Queue(maxsize=256)
        self._stderr_thread: Optional[threading.Thread] = None
        threading.Thread(target=self._writer_loop, daemon=True).start()

    def _drain_stderr(self) -> None:
        if not self.proc or not self.proc.stderr:
            return
        try:
            for line in self.proc.stderr:
                _log("[ffmpeg] " + line.decode("utf-8", errors="replace").rstrip())
        except Exception:
            pass

    def _kill_ffmpeg(self) -> None:
        if self.proc is None:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=4)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        code = self.proc.poll()
        if code:
            _log(f"ffmpeg exited code={code}")
        self.proc = None
        self.need_init = True

    def _start_ffmpeg(self) -> bool:
        with _PROC_LOCK:
            if self.proc is not None and self.proc.poll() is None:
                return True
            self._kill_ffmpeg()
            try:
                self.proc = subprocess.Popen(
                    _ffmpeg_cmd(),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                self.need_init = True
                self.ffmpeg_started_at = time.time()
                self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
                self._stderr_thread.start()
                _log(f"ffmpeg started pid={self.proc.pid}")
                return True
            except Exception as exc:
                _log(f"ffmpeg start failed: {exc}")
                self.proc = None
                return False

    def _strip_to_init(self, data: bytes) -> bytes:
        if not self.need_init:
            return data
        idx = data.find(EBML_MAGIC)
        if idx < 0:
            return b""
        self.need_init = False
        return data[idx:]

    def _writer_loop(self) -> None:
        while True:
            data = self._q.get()
            if data is None:
                break
            if not data:
                continue
            if not self._start_ffmpeg():
                continue
            data = self._strip_to_init(data)
            if not data:
                continue
            try:
                assert self.proc and self.proc.stdin
                self.proc.stdin.write(data)
                self.proc.stdin.flush()
                self.bytes_in += len(data)
                self.chunks_in += 1
                self.last_chunk_at = time.time()
                _write_stats(
                    {
                        "bytes_in": self.bytes_in,
                        "chunks_in": self.chunks_in,
                        "last_chunk_at": self.last_chunk_at,
                        "ffmpeg_pid": self.proc.pid if self.proc else None,
                        "need_init": self.need_init,
                    }
                )
            except (BrokenPipeError, OSError) as exc:
                _log(f"stdin write error: {exc}")
                self._kill_ffmpeg()

    def enqueue(self, data: bytes) -> None:
        try:
            self._q.put(data, timeout=15)
        except queue.Full:
            _log("chunk queue full — dropping data (browser sending too fast)")

    def reset_pipeline(self) -> None:
        with _PROC_LOCK:
            self._kill_ffmpeg()
        self.bytes_in = 0
        self.chunks_in = 0
        self.need_init = True
        drained = 0
        while True:
            try:
                self._q.get_nowait()
                drained += 1
            except queue.Empty:
                break
        if drained:
            _log(f"reset_pipeline drained {drained} queued chunks")


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
    srv.listen(64)

    with open(PID_PATH, "w", encoding="utf-8") as pf:
        pf.write(str(os.getpid()))

    engine = IngestEngine()
    _log(f"daemon listening {SOCK_PATH} pid={os.getpid()} profile={os.environ.get('YOUTUBE_STREAM_KEY_PROFILE','')}")

    def handle_conn(conn: socket.socket) -> None:
        try:
            buf = bytearray()
            while True:
                chunk = conn.recv(262144)
                if not chunk:
                    break
                buf.extend(chunk)
            if buf:
                engine.enqueue(bytes(buf))
        except OSError as exc:
            _log(f"conn read error: {exc}")
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def shutdown(*_args) -> None:
        _log("daemon shutdown")
        engine.reset_pipeline()
        try:
            srv.close()
        except OSError:
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

    # Control socket for reset (single byte 'R')
    ctrl_path = SOCK_PATH + ".ctl"
    try:
        os.unlink(ctrl_path)
    except FileNotFoundError:
        pass
    ctrl = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    ctrl.bind(ctrl_path)
    os.chmod(ctrl_path, 0o666)
    ctrl.listen(8)

    def ctrl_loop() -> None:
        while True:
            try:
                c, _ = ctrl.accept()
                with c:
                    cmd = c.recv(8)
                    if cmd.startswith(b"R"):
                        engine.reset_pipeline()
                        _log("pipeline reset via ctl")
            except OSError:
                break

    threading.Thread(target=ctrl_loop, daemon=True).start()

    try:
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handle_conn, args=(conn,), daemon=True).start()
    except OSError:
        shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
