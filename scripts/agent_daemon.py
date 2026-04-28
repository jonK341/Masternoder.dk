#!/usr/bin/env python3
"""
Optional agent control daemon (runs beside uwsgi, not inside workers).

Why use this:
- In-process threads (AgentAutomation inside Flask) run once per uwsgi worker — duplicated work.
- Cron is minute-granularity only.
- This process POSTs to the app on a fixed interval so exactly one scheduler drives agents.

Alternatives (not implemented here):
- Celery/RQ workers — heavier, queue infra.
- Only cron + AGENT_CRON_SECRET — no sub-minute ticks; fine for many sites.

Env:
  AGENT_DAEMON_URL       default http://127.0.0.1:5000/api/agents/daemon/tick
  AGENT_DAEMON_INTERVAL_SEC  default 60
  AGENT_DAEMON_SECRET    preferred; else AGENT_CRON_SECRET from .env
  AGENT_DAEMON_ENV_FILE  optional path to .env (Linux: /var/www/html/.env)

Usage:
  python scripts/agent_daemon.py
  systemd: see systemd/masternoder-agent-daemon.service.example
"""
from __future__ import annotations

import os
import signal
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

_stop = False


def _load_dotenv_if_present(path: str) -> None:
    if not path or not os.path.isfile(path):
        return
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass


def _tick(url: str, token: str) -> tuple[int, str]:
    req = Request(
        url,
        data=b"{}",
        headers={
            "X-Agent-Daemon-Token": token,
            "Content-Type": "application/json",
        },
    )
    with urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.getcode(), body


def _handle_sig(_signum, _frame):
    global _stop
    _stop = True


def main() -> int:
    global _stop
    env_file = os.environ.get("AGENT_DAEMON_ENV_FILE", "")
    if env_file:
        _load_dotenv_if_present(env_file)
    elif os.path.isfile(os.path.join(BASE_DIR, ".env")):
        _load_dotenv_if_present(os.path.join(BASE_DIR, ".env"))

    url = os.environ.get("AGENT_DAEMON_URL", "http://127.0.0.1:5000/api/agents/daemon/tick").strip()
    try:
        interval = float(os.environ.get("AGENT_DAEMON_INTERVAL_SEC", "60"))
    except ValueError:
        interval = 60.0
    interval = max(1.0, min(3600.0, interval))

    token = (os.environ.get("AGENT_DAEMON_SECRET") or os.environ.get("AGENT_CRON_SECRET") or "").strip()
    if not token:
        print("[agent_daemon] Set AGENT_DAEMON_SECRET or AGENT_CRON_SECRET", file=sys.stderr)
        return 1

    signal.signal(signal.SIGTERM, _handle_sig)
    signal.signal(signal.SIGINT, _handle_sig)

    print(f"[agent_daemon] url={url} interval_sec={interval} (POST with X-Agent-Daemon-Token)")

    while not _stop:
        try:
            code, body = _tick(url, token)
            print(f"[agent_daemon] tick ok http={code} {body[:200]}")
        except HTTPError as e:
            print(f"[agent_daemon] HTTP {e.code}: {e.reason}", file=sys.stderr)
        except URLError as e:
            print(f"[agent_daemon] URL error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[agent_daemon] error: {e}", file=sys.stderr)

        for _ in range(int(interval * 10)):
            if _stop:
                break
            time.sleep(0.1)

    print("[agent_daemon] stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
