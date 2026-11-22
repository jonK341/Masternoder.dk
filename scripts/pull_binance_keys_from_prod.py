#!/usr/bin/env python3
"""Copy Binance API keys + live flags from production .env into local .env.

Never prints secret values — only presence / lengths.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deploy_ssh_env import connect_deploy_ssh, _load_deploy_env_from_dotenv

KEYS = (
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "EXCHANGE_ARBITRAGE_LIVE",
    "EXCHANGE_PAYOUT_BINANCE_LIVE",
    "EXCHANGE_PAYOUT_BINANCE_ADDRESS",
    "EXCHANGE_PAYOUT_BINANCE_NETWORK",
    "BINANCE_QUOTE",
)

REMOTE = r"""
import json
from pathlib import Path
wanted = %s
out = {}
for path in (Path(".env"), Path("vidgenerator/.env")):
    if not path.is_file():
        continue
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        if k not in wanted:
            continue
        val = v.strip().strip('"').strip("'")
        if val and k not in out:
            out[k] = val
print(json.dumps(out))
""" % (repr(list(KEYS)),)


def _upsert_env(path: Path, updates: dict[str, str]) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    lines = raw.splitlines()
    seen: set[str] = set()
    changed: list[str] = []
    out_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        matched = False
        for key, val in updates.items():
            # Match active or commented forms: KEY=... or # KEY=...
            if re.match(rf"^#?\s*{re.escape(key)}=", stripped):
                out_lines.append(f"{key}={val}")
                seen.add(key)
                changed.append(key)
                matched = True
                break
        if not matched:
            out_lines.append(line)
    for key, val in updates.items():
        if key not in seen:
            out_lines.append(f"{key}={val}")
            changed.append(key)
    text = "\n".join(out_lines)
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    return changed


def main() -> int:
    os.chdir(ROOT)
    _load_deploy_env_from_dotenv()
    print("Connecting to production…")
    ssh, auth, _ = connect_deploy_ssh(None)
    b64 = base64.b64encode(REMOTE.encode()).decode()
    cmd = (
        "cd /var/www/html && PYTHONPATH=/var/www/html python3 -c "
        f"\"import base64; exec(base64.b64decode('{b64}').decode())\""
    )
    _, stdout, stderr = ssh.exec_command(cmd, timeout=90)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace").strip()
    ssh.close()
    if err:
        print("STDERR:", err[:400], file=sys.stderr)
    try:
        payload = json.loads(out.strip().splitlines()[-1] if out.strip() else "{}")
    except Exception:
        print("Failed to parse production response.", file=sys.stderr)
        print(out[:300], file=sys.stderr)
        return 1

    if not payload.get("BINANCE_API_KEY") or not payload.get("BINANCE_API_SECRET"):
        print("Production did not return both BINANCE_API_KEY and BINANCE_API_SECRET.")
        for k in KEYS:
            v = payload.get(k)
            if v is None:
                print(f"  {k}: missing")
            else:
                print(f"  {k}: set (len={len(v)})")
        print(f"AUTH: {auth}")
        return 2

    # Ensure live flags exist; keep production values when set.
    updates = {
        "BINANCE_API_KEY": payload["BINANCE_API_KEY"],
        "BINANCE_API_SECRET": payload["BINANCE_API_SECRET"],
        "EXCHANGE_ARBITRAGE_LIVE": payload.get("EXCHANGE_ARBITRAGE_LIVE") or "1",
        "EXCHANGE_PAYOUT_BINANCE_LIVE": payload.get("EXCHANGE_PAYOUT_BINANCE_LIVE") or "1",
    }
    for opt in ("EXCHANGE_PAYOUT_BINANCE_ADDRESS", "EXCHANGE_PAYOUT_BINANCE_NETWORK", "BINANCE_QUOTE"):
        if payload.get(opt):
            updates[opt] = payload[opt]

    env_path = ROOT / ".env"
    changed = _upsert_env(env_path, updates)
    print(f"Updated local .env ({env_path}) — auth={auth}")
    for k in changed:
        print(f"  wrote {k} (len={len(updates[k])})")
    print("Secrets were not printed. Re-run: python scripts/_check_binance_key_presence.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
