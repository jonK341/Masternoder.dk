#!/usr/bin/env python3
"""Check prod exchange / price-battle trade activity."""
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
from backend.services.exchange_price_battle_service import status, live_enabled, load_config
from backend.services import exchange_venue_api_service as vapi
from backend.services import crypto_exchange_service as ex
from backend.services.crypto_exchange_agent_service import list_agents

cfg = load_config()
s = status()
a = list_agents()
bals = vapi.parse_spot_balances('binance', dry_run=False, force_refresh=True)
spot_usd = earn_usd = 0.0
spot = {}
for k, v in (bals or {}).items():
    if not v or float(v) <= 0:
        continue
    is_earn = str(k).startswith('LD') and len(str(k)) > 2
    base = str(k)[2:] if is_earn else str(k)
    px = float(ex._price_usd(base) or (1.0 if base in ('USDC', 'USDT') else 0))
    u = float(v) * px
    if is_earn:
        earn_usd += u
    else:
        spot[k] = {'free': float(v), 'usd': round(u, 4)}
        spot_usd += u

def tail_jsonl(path, n=10):
    try:
        lines = open(path, encoding='utf-8').read().strip().splitlines()
        return len(lines), [json.loads(x) for x in lines[-n:]]
    except Exception:
        return 0, []

bn, buys = tail_jsonl(s.get('buys_log'), 10)
sn, sells = tail_jsonl(s.get('sells_log'), 10)
print(json.dumps({
    'price_battle_live': live_enabled(),
    'cfg': {k: cfg.get(k) for k in (
        'min_profit_bps', 'fee_buffer_bps', 'max_hold_sec',
        'buy_dip_only', 'dip_bps', 'position_usd'
    )},
    'open': s.get('open_count'),
    'tick': s.get('tick_count'),
    'last': s.get('last_tick'),
    'positions': s.get('open') or [],
    'buys_n': bn,
    'sells_n': sn,
    'buys': buys,
    'sells': sells,
    'churn_agents': a.get('enabled'),
    'spot_usd': round(spot_usd, 2),
    'earn_usd': round(earn_usd, 2),
    'total': round(spot_usd + earn_usd, 2),
    'spot_top': dict(sorted(spot.items(), key=lambda kv: -kv[1]['usd'])[:6]),
}))
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
        if line.startswith("{") and '"buys_n"' in line:
            try:
                data = json.loads(line)
                break
            except Exception:
                pass
    if not data:
        print(out[-2000:])
        print(err[-800:])
        ssh.close()
        return 1

    print(
        f"price_battle={'ON' if data['price_battle_live'] else 'OFF'} "
        f"churn_agents={'ON' if data['churn_agents'] else 'OFF'}"
    )
    c = data["cfg"]
    print(
        f"rules: pos=${c.get('position_usd')} tp={c.get('min_profit_bps')}bps+{c.get('fee_buffer_bps')}fee "
        f"max_hold={c.get('max_hold_sec')}s dip={c.get('buy_dip_only')}@{c.get('dip_bps')}bps"
    )
    print(f"capital ~${data['total']} (spot ${data['spot_usd']} + earn ${data['earn_usd']})")
    for k, row in data["spot_top"].items():
        print(f"  {k}: {row['free']} (~${row['usd']})")
    print(f"battle tick={data['tick']} last={data['last']} open={data['open']}")
    for p in data["positions"]:
        print(
            f"  HOLD {p.get('symbol')} qty={p.get('qty')} entry={p.get('entry_price')} "
            f"cost=${p.get('cost_usd')} since={p.get('bought_at')}"
        )
    print(f"logs: buys={data['buys_n']} sells={data['sells_n']}")
    if data["buys"]:
        print("recent buys:")
        for b in data["buys"][-5:]:
            print(
                f"  {b.get('ts')} BUY {b.get('symbol')} qty={b.get('qty')} "
                f"@ {b.get('entry_price')} cost=${b.get('cost_usd')} mode={b.get('mode')}"
            )
    if data["sells"]:
        print("recent sells:")
        for srow in data["sells"][-5:]:
            print(
                f"  {srow.get('ts')} SELL {srow.get('symbol')} @ {srow.get('exit_price')} "
                f"pnl=${srow.get('pnl_usd')} reason={srow.get('exit_reason')} mode={srow.get('mode')}"
            )
    else:
        print("recent sells: (none)")
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
