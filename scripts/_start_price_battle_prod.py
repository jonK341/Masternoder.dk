#!/usr/bin/env python3
"""Enable EXCHANGE_PRICE_BATTLE_LIVE on prod and start the daemon (screen/nohup)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = "/var/www/html"


def run(ssh, cmd: str, timeout: int = 60) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode(errors="replace").strip()
    err = (stderr.read() or b"").decode(errors="replace").strip()
    if err and not out:
        return f"ERR: {err[-800:]}"
    if err:
        return f"{out}\nERR: {err[-400:]}"
    return out


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")

    ensure = r"""
cd /var/www/html
ensure() {
  key="$1"; val="$2"
  if grep -q "^${key}=" .env 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" .env
  else
    echo "${key}=${val}" >> .env
  fi
}
ensure EXCHANGE_ARBITRAGE_LIVE 1
ensure EXCHANGE_PRICE_BATTLE_LIVE 1
# keep churn agents off
python3 - <<'PY'
import json
p="data/crypto_exchange_config.json"
with open(p,encoding="utf-8") as f: cfg=json.load(f)
at=cfg.setdefault("agent_trading",{})
at["enabled"]=False
at["live_venue_trading"]=False
pb=cfg  # no-op; price battle has own config file
with open(p,"w",encoding="utf-8") as f:
    json.dump(cfg,f,indent=2)
    f.write("\n")
print("churn_agents_off")
PY
# ensure price battle config enabled
python3 - <<'PY'
import json
p="data/exchange_price_battle_config.json"
with open(p,encoding="utf-8") as f: cfg=json.load(f)
cfg["enabled"]=True
with open(p,"w",encoding="utf-8") as f:
    json.dump(cfg,f,indent=2)
    f.write("\n")
print("price_battle_enabled", cfg.get("position_usd"), cfg.get("min_profit_bps"))
PY
echo flags_ok
"""
    print("--- ensure flags ---")
    print(run(ssh, ensure, timeout=30))

    # Stop any prior price-battle daemon, then start under nohup
    stop_start = r"""
cd /var/www/html
pkill -f 'scripts/exchange_price_battle_daemon.py' 2>/dev/null || true
sleep 1
mkdir -p logs
nohup .venv/bin/python scripts/exchange_price_battle_daemon.py --interval 120 \
  >> logs/price_battle_daemon.log 2>&1 &
echo "pid=$!"
sleep 2
# one forced tick to open first live position(s)
.venv/bin/python scripts/exchange_price_battle_daemon.py --once 2>&1 | tail -c 3500
echo '---'
pgrep -af 'exchange_price_battle_daemon' || echo 'daemon_not_listed'
tail -n 20 logs/price_battle_daemon.log 2>/dev/null || true
"""
    print("--- start + first tick ---")
    print(run(ssh, stop_start, timeout=180))

    verify = r"""
cd /var/www/html && .venv/bin/python - <<'PY'
import os
os.environ.setdefault('DAEMON_QUIET','1')
os.environ.setdefault('LITE_APP','1')
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.exchange_price_battle_service import status, live_enabled
st = status()
print('live_gate', live_enabled())
print('enabled', st.get('enabled'), 'open', st.get('open_count'), 'tick', st.get('tick_count'))
for p in st.get('open') or []:
    print('POS', p.get('id'), p.get('symbol'), 'qty', p.get('qty'),
          'entry', p.get('entry_price'), 'cost', p.get('cost_usd'), 'mode', p.get('mode'))
PY
"""
    print("--- status ---")
    print(run(ssh, verify, timeout=90))
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
