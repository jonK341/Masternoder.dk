#!/usr/bin/env python3
"""Pause live venue agent trading on production immediately."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

CMD = r"""
cd /var/www/html && python3 - <<'PY'
import json
p = "data/crypto_exchange_config.json"
with open(p, encoding="utf-8") as f:
    cfg = json.load(f)
at = cfg.setdefault("agent_trading", {})
at["enabled"] = False
at["live_venue_trading"] = False
with open(p, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
print("paused enabled=", at["enabled"], "live_venue_trading=", at["live_venue_trading"])
PY
"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")
    _, stdout, stderr = ssh.exec_command(CMD, timeout=30)
    print((stdout.read() or b"").decode(errors="replace").strip())
    err = (stderr.read() or b"").decode(errors="replace").strip()
    if err:
        print(err[-400:])
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
