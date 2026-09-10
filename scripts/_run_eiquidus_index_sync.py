#!/usr/bin/env python3
"""Run eiquidus index sync and verify MN2 explorer health."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
EXPLORER=/var/www/explorer
cd "$EXPLORER" || exit 2

echo '========== EIQUIDUS INDEX SYNC =========='
date -u

echo '== pre-check =='
systemctl is-active mongod masternoder2d 2>/dev/null
pm2 list 2>/dev/null | grep explorer || true
curl -sS -m 8 http://127.0.0.1:3000/ext/getmoneysupply | head -c 80; echo
curl -sS -m 8 http://127.0.0.1:3000/ext/getlasttxsajax/0 | head -c 120; echo

echo '== cron =='
cat /etc/cron.d/eiquidus 2>/dev/null || echo '(no /etc/cron.d/eiquidus)'

echo '== sync scripts =='
ls -la scripts/sync.js scripts/sync 2>/dev/null | head -5

echo '== run index update (background, log to /var/log/eiquidus-index-sync.log) =='
LOG=/var/log/eiquidus-index-sync.log
if pgrep -f 'scripts/sync.js index update' >/dev/null 2>&1; then
  echo 'sync already running'
else
  nohup node scripts/sync.js index update >>"$LOG" 2>&1 &
  echo "sync_pid=$!"
fi
sleep 5
tail -20 "$LOG" 2>/dev/null || echo '(no log yet)'

echo '== also run richlist if available =='
node scripts/sync.js richlist update >>"$LOG" 2>&1 &
sleep 3
tail -8 "$LOG" 2>/dev/null

echo '== ext probes =='
curl -sS -m 15 -o /dev/null -w 'supply=%{http_code}\n' http://127.0.0.1:3000/ext/getmoneysupply
curl -sS -m 15 -o /dev/null -w 'ajax=%{http_code}\n' http://127.0.0.1:3000/ext/getlasttxsajax/0
curl -sS -m 15 http://127.0.0.1:3000/ext/getaddresslist?page=0 2>/dev/null | head -c 200; echo
ENDSCRIPT"""


def _get_json(url: str) -> tuple[int, dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EiquidusSyncCheck/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace"))
        except Exception:
            body = {"error": str(e)}
        return e.code, body
    except Exception as exc:
        return -1, {"error": str(exc)}


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=120)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(b"\n")
    if err.strip():
        sys.stdout.buffer.write(err[:500].encode("utf-8", errors="replace"))

    print("\n--- Waiting 30s for sync progress ---")
    time.sleep(30)

    code, health = _get_json("https://masternoder.dk/api/mn2/health")
    print(f"\nMN2 health HTTP {code}")
    print(f"  overall status: {health.get('status')}")
    probe = (health.get("components") or {}).get("explorer_probe") or {}
    detail = probe.get("detail") or {}
    checks = detail.get("checks") or {}
    rich = checks.get("rich_list") or {}
    print(f"  explorer_probe: {probe.get('status')}")
    print(f"  rich_list ok: {rich.get('ok')} synced: {rich.get('index_synced')}")
    print(f"  rich_list note: {rich.get('note', '')[:120]}")

    code2, _ = _get_json("https://camgirls.masternoder.dk/ext/getmoneysupply")
    print(f"\ncamgirls supply: HTTP {code2}")

    ok = health.get("status") == "healthy"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
