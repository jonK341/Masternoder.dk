#!/usr/bin/env python3
"""Prod status: capital (spot+earn) + price battle positions."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_PY = r"""
cd /var/www/html && .venv/bin/python - <<'PY'
import json, os
os.environ.setdefault('DAEMON_QUIET','1')
os.environ.setdefault('LITE_APP','1')
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services import exchange_venue_api_service as vapi
from backend.services import crypto_exchange_service as ex
from backend.services.exchange_arbitrage_service import live_enabled
from backend.services.exchange_binance_withdraw_service import binance_withdraw_live_enabled
from backend.services.exchange_live_execution_service import venue_live_ready
from backend.services.exchange_price_battle_service import status as pb_status, live_enabled as pb_live
from backend.services.crypto_exchange_agent_service import list_agents
from backend.services.exchange_stable_markets_service import paper_mode_enabled

bals = vapi.parse_spot_balances('binance', dry_run=False, force_refresh=True)
spot, earn = {}, {}
spot_usd = earn_usd = 0.0
for k, v in (bals or {}).items():
    if not v or float(v) <= 0:
        continue
    is_earn = str(k).startswith('LD') and len(str(k)) > 2
    base = str(k)[2:] if is_earn else str(k)
    px = float(ex._price_usd(base) or ex._price_usd(k) or (1.0 if base in ('USDC','USDT') else 0))
    if base == 'EUR': px = 1.08
    if base == 'DKK': px = 0.15
    u = float(v) * px
    row = {'free': float(v), 'usd': round(u, 4)}
    if is_earn:
        earn[k] = row
        earn_usd += u
    else:
        spot[k] = row
        spot_usd += u

agents = list_agents()
pb = pb_status()
out = {
  'gates': {
    'arb': live_enabled(),
    'wd': binance_withdraw_live_enabled(),
    'binance': venue_live_ready('binance'),
    'paper': paper_mode_enabled(),
    'agents_on': agents.get('enabled'),
    'price_battle_live': pb_live(),
  },
  'total_usd': round(spot_usd + earn_usd, 2),
  'spot_usd': round(spot_usd, 2),
  'earn_usd': round(earn_usd, 2),
  'spot': spot,
  'earn': {k:v for k,v in earn.items() if v['usd'] >= 0.05},
  'price_battle': {
    'open': pb.get('open_count'),
    'tick': pb.get('tick_count'),
    'last': pb.get('last_tick'),
    'positions': pb.get('open') or [],
  },
}
# recent sells count
sells_path = pb.get('sells_log') or ''
buys_path = pb.get('buys_log') or ''
sells = buys = 0
try:
    with open(sells_path, encoding='utf-8') as f:
        sells = sum(1 for line in f if line.strip())
except Exception:
    pass
try:
    with open(buys_path, encoding='utf-8') as f:
        buys = sum(1 for line in f if line.strip())
except Exception:
    pass
out['price_battle']['buys_logged'] = buys
out['price_battle']['sells_logged'] = sells
print(json.dumps(out))
PY
"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"prod ({auth})")
    _, stdout, stderr = ssh.exec_command(REMOTE_PY, timeout=120)
    out = (stdout.read() or b"").decode(errors="replace")
    err = (stderr.read() or b"").decode(errors="replace")
    data = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and '"total_usd"' in line:
            try:
                data = json.loads(line)
                break
            except Exception:
                pass
    if not data:
        print(out[-1500:])
        print(err[-500:])
        ssh.close()
        return 1

    g = data["gates"]
    print(
        f"gates: arb={g['arb']} wd={g['wd']} binance={g['binance']} "
        f"paper={g['paper']} churn_agents={g['agents_on']} price_battle={g['price_battle_live']}"
    )
    print(f"capital TOTAL ~${data['total_usd']} (spot ~${data['spot_usd']} + earn ~${data['earn_usd']})")
    print("spot:")
    for k, row in sorted(data["spot"].items(), key=lambda kv: -kv[1]["usd"]):
        if row["usd"] >= 0.01:
            print(f"  {k}: {row['free']} (~${row['usd']})")
    if data.get("earn"):
        print("earn:")
        for k, row in sorted(data["earn"].items(), key=lambda kv: -kv[1]["usd"])[:8]:
            print(f"  {k}: {row['free']} (~${row['usd']})")

    pb = data["price_battle"]
    print(
        f"price battle: open={pb['open']} tick={pb['tick']} last={pb['last']} "
        f"buys_log={pb['buys_logged']} sells_log={pb['sells_logged']}"
    )
    for p in pb.get("positions") or []:
        entry = float(p.get("entry_price") or 0)
        target = entry * 1.014  # ~100bps + 40 fee buffer
        print(
            f"  HOLD {p.get('symbol')} qty={p.get('qty')} entry={entry} "
            f"cost=${p.get('cost_usd')} target~{round(target,6)} mode={p.get('mode')}"
        )
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
