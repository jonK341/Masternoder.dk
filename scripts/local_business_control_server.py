#!/usr/bin/env python3
"""Local Business Control bridge on the laptop (default port 8800).

Serves a small API so the site Business Control page can drive Windows cmd
daemons (grid bot, profit live, Flask dev server) from the owner's browser.

Start:  python scripts/local_business_control_server.py
        scripts\\run_local_business_control.cmd
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

PORT = int(os.environ.get("LOCAL_BUSINESS_CONTROL_PORT", "8800"))
HOST = os.environ.get("LOCAL_BUSINESS_CONTROL_HOST", "127.0.0.1")

_PROCS: Dict[str, subprocess.Popen] = {}
_LOCK = threading.Lock()

CMD_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "unified_trading",
        "title": "Unified trading (all bots)",
        "script": "scripts/run_unified_trading_daemon.cmd",
        "args_default": [],
        "log": "logs/local_unified_trading.log",
    },
    {
        "id": "grid_bot",
        "title": "Grid only (legacy)",
        "script": "scripts/run_grid_bot_daemon.cmd",
        "args_default": ["--interval", "30"],
        "log": "logs/local_grid_bot_daemon.log",
    },
    {
        "id": "profit_live",
        "title": "ALL profit (live)",
        "script": "scripts/run_all_profit_live.cmd",
        "args_default": [],
        "log": "logs/local_all_profit_live.log",
    },
    {
        "id": "profit_max",
        "title": "ALL profit (max) — alias unified",
        "script": "scripts/run_unified_trading_daemon.cmd",
        "args_default": [],
        "log": "logs/local_all_profit_max.log",
    },
    {
        "id": "casino_agents",
        "title": "Casino agent daemon",
        "script": "scripts/run_casino_agent_daemon.cmd",
        "args_default": [],
        "log": "logs/local_casino_agents.log",
    },
    {
        "id": "site_agents",
        "title": "Site agent daemon",
        "script": "scripts/run_site_agent_daemon.cmd",
        "args_default": [],
        "log": "logs/local_site_agents.log",
    },
    {
        "id": "flask_dev",
        "title": "Flask dev server (5000)",
        "script": "start_server.bat",
        "args_default": [],
        "log": "logs/local_flask_dev.log",
    },
]


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, X-Exchange-Admin-Key")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _tail_file(path: Path, lines: int = 80) -> str:
    if not path.is_file():
        return ""
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(data[-max(1, lines):])
    except OSError:
        return ""


def _start_job(job_id: str, extra_args: Optional[List[str]] = None) -> Dict[str, Any]:
    meta = next((j for j in CMD_CATALOG if j["id"] == job_id), None)
    if not meta:
        return {"success": False, "error": "unknown_job", "job_id": job_id}
    script = ROOT / str(meta["script"])
    if not script.is_file():
        return {"success": False, "error": "script_missing", "path": str(script)}
    log_path = ROOT / str(meta["log"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    args = list(meta.get("args_default") or [])
    if extra_args:
        args.extend(extra_args)
    with _LOCK:
        old = _PROCS.pop(job_id, None)
        if old and old.poll() is None:
            try:
                old.terminate()
            except OSError:
                pass
        cmd = ["cmd.exe", "/c", str(script)] + args if os.name == "nt" else ["bash", str(script)] + args
        if os.name != "nt" and script.suffix == ".cmd":
            cmd = [sys.executable, str(ROOT / "scripts" / "grid_bot_daemon.py")] if job_id == "grid_bot" else cmd
        log_f = open(log_path, "a", encoding="utf-8")
        log_f.write(f"\n--- start {_iso()} {cmd}\n")
        log_f.flush()
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=log_f,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
        except OSError as exc:
            log_f.close()
            return {"success": False, "error": str(exc)}
        _PROCS[job_id] = proc
    return {"success": True, "job_id": job_id, "pid": proc.pid, "log": str(log_path), "started_at": _iso()}


def _stop_job(job_id: str) -> Dict[str, Any]:
    with _LOCK:
        proc = _PROCS.pop(job_id, None)
    if not proc:
        return {"success": True, "job_id": job_id, "stopped": False, "note": "not_running"}
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
    return {"success": True, "job_id": job_id, "stopped": True}


def _status() -> Dict[str, Any]:
    jobs = []
    with _LOCK:
        for j in CMD_CATALOG:
            proc = _PROCS.get(j["id"])
            running = proc is not None and proc.poll() is None
            jobs.append({
                "id": j["id"],
                "title": j["title"],
                "script": j["script"],
                "running": running,
                "pid": proc.pid if running and proc else None,
                "log_tail": _tail_file(ROOT / str(j["log"]), 12),
            })
    grid_state = {}
    try:
        sys.path.insert(0, str(ROOT))
        from backend.services.exchange_grid_bot_service import grid_status
        grid_state = grid_status()
    except Exception as exc:
        grid_state = {"error": str(exc)}
    profit_pulse = _read_profit_pulse()
    return {
        "success": True,
        "host": HOST,
        "port": PORT,
        "repo_root": str(ROOT),
        "updated_at": _iso(),
        "jobs": jobs,
        "grid": grid_state,
        "profit_pulse": profit_pulse,
    }


def _read_profit_pulse() -> Dict[str, Any]:
    hb = ROOT / "logs" / "daemon_all_profit_heartbeat.json"
    if not hb.is_file():
        return {}
    try:
        return json.loads(hb.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _profit_broadcast(message: str, *, delta_usd: float = 0.0) -> Dict[str, Any]:
    out_path = LOG_DIR / "profit_youtube_broadcast.jsonl"
    row = {"ts": _iso(), "message": message, "delta_usd": delta_usd}
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    try:
        sys.path.insert(0, str(ROOT))
        from backend.services.profit_daemon_news_service import maybe_publish_custom_news
        maybe_publish_custom_news(message, featured=delta_usd > 0)
    except Exception:
        pass
    return {"success": True, "broadcast": row}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Exchange-Admin-Key")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/health"):
            return _json_response(self, 200, {"success": True, "service": "local-business-control", "port": PORT})
        if path == "/api/local/status":
            return _json_response(self, 200, _status())
        if path == "/api/local/catalog":
            return _json_response(self, 200, {"success": True, "jobs": CMD_CATALOG})
        if path == "/api/local/log":
            qs = parse_qs(urlparse(self.path).query)
            job = (qs.get("job") or [""])[0]
            meta = next((j for j in CMD_CATALOG if j["id"] == job), None)
            if not meta:
                return _json_response(self, 404, {"success": False, "error": "unknown_job"})
            text = _tail_file(ROOT / str(meta["log"]), int((qs.get("lines") or ["120"])[0]))
            return _json_response(self, 200, {"success": True, "job": job, "log": text})
        if path == "/api/local/profit-broadcasts":
            text = _tail_file(LOG_DIR / "profit_youtube_broadcast.jsonl", 30)
            lines = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
            return _json_response(self, 200, {"success": True, "items": lines})
        return _json_response(self, 404, {"success": False, "error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8") if n else "{}"
        try:
            body = json.loads(raw or "{}")
        except json.JSONDecodeError:
            body = {}
        if path == "/api/local/start":
            return _json_response(self, 200, _start_job(str(body.get("job_id") or ""), body.get("args")))
        if path == "/api/local/stop":
            return _json_response(self, 200, _stop_job(str(body.get("job_id") or "")))
        if path == "/api/local/grid-tick":
            try:
                sys.path.insert(0, str(ROOT))
                from backend.services.exchange_grid_bot_service import run_all
                res = run_all(dry_run=body.get("paper"))
                return _json_response(self, 200, {"success": True, "result": res})
            except Exception as exc:
                return _json_response(self, 500, {"success": False, "error": str(exc)})
        if path == "/api/local/broadcast-profit":
            msg = str(body.get("message") or "Profit tick gain")
            delta = float(body.get("delta_usd") or 0)
            return _json_response(self, 200, _profit_broadcast(msg, delta_usd=delta))
        return _json_response(self, 404, {"success": False, "error": "not_found"})


def main() -> int:
    os.chdir(ROOT)
    print(f"[local-business-control] http://{HOST}:{PORT}/  repo={ROOT}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[local-business-control] stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
