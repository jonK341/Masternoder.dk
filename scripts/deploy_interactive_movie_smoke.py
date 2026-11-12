#!/usr/bin/env python3
"""Deploy interactive-movie files and smoke-test the live API."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from dotenv import load_dotenv

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

load_dotenv(".env")

FILES = (
    "backend/services/film_canvas_service.py",
    "backend/services/video_generator_service.py",
    "backend/routes/ai_providers_routes.py",
    "debugger/index.html",
)


def sh(ssh, cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    return code, out, err


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print("connected", auth)
    try:
        sftp = ssh.open_sftp()
        for rel in FILES:
            sftp.put(rel, "/var/www/html/" + rel)
            print("uploaded", rel)
        sftp.close()

        upsert = (
            "python3 - <<'PY'\n"
            "from pathlib import Path\n"
            "p = Path('/var/www/html/.env')\n"
            "text = p.read_text(encoding='utf-8', errors='replace')\n"
            "lines = text.splitlines(keepends=True)\n"
            "out = []\n"
            "seen = False\n"
            "keys = {'FAL_FORCE_QUEUE': '1', 'FAL_VIDEO_MODEL': 'fal-ai/minimax/video-01-live'}\n"
            "seen = set()\n"
            "for line in lines:\n"
            "    raw = line.strip()\n"
            "    replaced = False\n"
            "    for key, val in keys.items():\n"
            "        if raw.startswith(key + '='):\n"
            "            out.append(f'{key}={val}\\n')\n"
            "            seen.add(key)\n"
            "            replaced = True\n"
            "            break\n"
            "    if not replaced:\n"
            "        out.append(line)\n"
            "if out and not out[-1].endswith('\\n'):\n"
            "    out.append('\\n')\n"
            "for key, val in keys.items():\n"
            "    if key not in seen:\n"
            "        out.append(f'{key}={val}\\n')\n"
            "p.write_text(''.join(out), encoding='utf-8')\n"
            "print('fal queue defaults set')\n"
            "PY\n"
            "systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001\n"
            "sleep 6\n"
            "systemctl is-active uwsgi-vidgenerator\n"
        )
        code, out, err = sh(ssh, upsert, timeout=90)
        print(out.strip())
        if err.strip():
            print("[stderr]", err[:500])
        if code != 0:
            return code

        start_cmd = (
            "curl -sS -m 20 -H 'Content-Type: application/json' "
            "-d '{\"prompt\":\"short cinematic harbour neon rain loop for a control monitor\"}' "
            "http://127.0.0.1:5000/api/film-canvas/interactive-movie"
        )
        code, out, err = sh(ssh, start_cmd, timeout=40)
        print("start_raw", out[:400])
        start = json.loads(out)
        job = start.get("job_id")
        print("start", {k: start.get(k) for k in ("success", "job_id", "status", "message", "error")})
        if not job:
            return 1

        status = None
        for i in range(75):
            code, out, err = sh(
                ssh,
                "curl -sS -m 30 http://127.0.0.1:5000/api/film-canvas/interactive-movie/" + job,
                timeout=40,
            )
            status = json.loads(out)
            print(
                "poll",
                i,
                status.get("status"),
                status.get("progress"),
                status.get("message"),
                status.get("error"),
                status.get("video_url"),
            )
            if status.get("status") in ("completed", "failed"):
                break
            time.sleep(5)

        if not status or status.get("status") != "completed":
            return 2
        video_url = status.get("video_url")
        code, out, err = sh(
            ssh,
            "curl -sS -m 60 -o /tmp/im_smoke.mp4 -w '%{http_code} %{size_download}' "
            "http://127.0.0.1:5000" + video_url,
            timeout=90,
        )
        print("video", out.strip())
        return 0 if out.strip().startswith("200 ") else 3
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
