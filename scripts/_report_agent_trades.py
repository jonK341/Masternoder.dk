#!/usr/bin/env python3
"""Report recent exchange agent / price-battle trades on production."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_PY = r"""
cd /var/www/html && .venv/bin/python - <<'PY'
import json, os, time, urllib.parse, hmac, hashlib
os.environ.setdefault('DAEMON_QUIET','1')
os.environ.setdefault('LITE_APP','1')
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.exchange_price_battle_service import status as pb_status, live_enabled as pb_live
from backend.services.crypto_exchange_agent_service import list_agents
from backend.services.exchange_binance_withdraw_service import binance_credentials
from backend.services import crypto_exchange_service as ex
import requests

def read_jsonl(path, n=30):
    try:
        lines = open(path, encoding='utf-8').read().strip().splitlines()
        rows = []
        for ln in lines[-n:]:
            try:
                rows.append(json.loads(ln))
            except Exception:
                pass
        return len(lines), rows
    except Exception:
        return 0, []

pb = pb_status()
agents = list_agents()
bn, buys = read_jsonl(pb.get('buys_log'), 20)
sn, sells = read_jsonl(pb.get('sells_log'), 20)

# Internal exchange trades ledger (agent swaps / venue swaps)
trades_path = os.path.join(ex._DATA_DIR, 'trades.jsonl')
tn, trades = read_jsonl(trades_path, 40)
agent_ids = {str(a.get('id') or '') for a in (agents.get('agents') or [])}
agent_ids |= {'exchange_sales_pool', 'exchange_price_battle'}
agent_trades = [t for t in trades if str(t.get('user_id') or '') in agent_ids or str(t.get('type') or '') in ('venue_swap','swap')]

# Recent Binance fills (~24h)
creds = binance_credentials()
key, secret = creds.get('api_key'), creds.get('api_secret')
binance_fills = []
if key and secret:
    start_ms = int((time.time() - 24*3600) * 1000)
    pairs = ['BTCUSDC','XRPUSDC','ADAUSDC','DOGEUSDC','TRXUSDC','SOLUSDC','ETHUSDC','BNBUSDC','LTCUSDC','LINKUSDC']
    for pair in pairs:
        params = {'symbol': pair, 'startTime': start_ms, 'limit': 50, 'timestamp': int(time.time()*1000), 'recvWindow': 10000}
        q = urllib.parse.urlencode(params)
        sig = hmac.new(secret.encode(), q.encode(), hashlib.sha256).hexdigest()
        url = f'https://api.binance.com/api/v3/myTrades?{q}&signature={sig}'
        try:
            r = requests.get(url, headers={'X-MBX-APIKEY': key}, timeout=15)
            body = r.json()
            if isinstance(body, list):
                for t in body:
                    binance_fills.append({
                        'symbol': pair,
                        'side': 'BUY' if t.get('isBuyer') else 'SELL',
                        'qty': float(t.get('qty') or 0),
                        'price': float(t.get('price') or 0),
                        'quote': float(t.get('quoteQty') or 0),
                        'time': t.get('time'),
                        'id': t.get('id'),
                    })
        except Exception:
            pass
binance_fills.sort(key=lambda x: x.get('time') or 0)

agent_last = []
for a in agents.get('agents') or []:
    last = ((a.get('state') or {}).get('last_action') or {})
    agent_last.append({
        'id': a.get('id'),
        'enabled_cfg': a.get('enabled'),
        'ok': last.get('success'),
        'mode': last.get('mode'),
        'side': last.get('side'),
        'sym': last.get('symbol'),
        'usd': last.get('notional_usd'),
        'err': last.get('error'),
        'last_tick': ((a.get('state') or {}).get('last_tick')),
    })

print(json.dumps({
    'pb_live': pb_live(),
    'agents_enabled': agents.get('enabled'),
    'pb_open': pb.get('open') or [],
    'pb_tick': pb.get('tick_count'),
    'pb_last': pb.get('last_tick'),
    'buys_n': bn, 'sells_n': sn,
    'buys': buys, 'sells': sells,
    'agent_last': agent_last,
    'internal_trades_n': tn,
    'internal_agent_trades': agent_trades[-15:],
    'binance_fills_24h_n': len(binance_fills),
    'binance_fills_24h': binance_fills[-20:],
}))
PY
"""


def _ts(ms_or_iso):
    if ms_or_iso is None:
        return "?"
    if isinstance(ms_or_iso, (int, float)) and ms_or_iso > 1e11:
        return datetime.fromtimestamp(ms_or_iso / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    return str(ms_or_iso)


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"prod ({auth})")
    _, stdout, stderr = ssh.exec_command(REMOTE_PY, timeout=180)
    out = (stdout.read() or b"").decode(errors="replace")
    err = (stderr.read() or b"").decode(errors="replace")
    data = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and '"pb_live"' in line:
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

    print("\n=== MODE ===")
    print(f"price_battle={'ON' if data['pb_live'] else 'OFF'}  churn_agents={'ON' if data['agents_enabled'] else 'OFF'}")
    print(f"battle tick={data['pb_tick']} last={data['pb_last']} open={len(data['pb_open'])}")
    for p in data["pb_open"]:
        print(f"  HOLD {p.get('symbol')} qty={p.get('qty')} entry={p.get('entry_price')} cost=${p.get('cost_usd')} since={p.get('bought_at')}")

    print("\n=== PRICE BATTLE LOG (buys/sells) ===")
    print(f"buys={data['buys_n']} sells={data['sells_n']}")
    for b in data["buys"]:
        print(f"  {_ts(b.get('ts'))} BUY  {b.get('symbol'):4} qty={b.get('qty')} @ {b.get('entry_price')} ${b.get('cost_usd')} [{b.get('mode')}]")
    for srow in data["sells"]:
        print(
            f"  {_ts(srow.get('ts'))} SELL {srow.get('symbol'):4} @ {srow.get('exit_price')} "
            f"pnl=${srow.get('pnl_usd')} reason={srow.get('exit_reason')} [{srow.get('mode')}]"
        )
    if data["sells"]:
        pnl = sum(float(x.get("pnl_usd") or 0) for x in data["sells"])
        print(f"  realized pnl (logged sells): ${round(pnl, 4)}")

    print("\n=== CHURN AGENTS (last action) ===")
    for a in data["agent_last"]:
        print(
            f"  {a['id']}: ok={a['ok']} {a.get('mode')} {a.get('side')} {a.get('sym')} "
            f"${a.get('usd')} err={a.get('err')} last={a.get('last_tick')}"
        )

    print("\n=== BINANCE FILLS (last 24h, USDC pairs) ===")
    print(f"count={data['binance_fills_24h_n']}")
    for t in data["binance_fills_24h"]:
        print(
            f"  {_ts(t.get('time'))} {t.get('side'):4} {t.get('symbol'):8} "
            f"qty={t.get('qty')} @ {t.get('price')} quote=${round(float(t.get('quote') or 0), 4)}"
        )

    print("\n=== INTERNAL LEDGER (recent agent-ish) ===")
    for t in data["internal_agent_trades"][-10:]:
        print(
            f"  {t.get('ts')} {t.get('type')} {t.get('user_id')} {t.get('side')} "
            f"{t.get('symbol')} amt={t.get('amount')} ${t.get('usd_value')} venue={t.get('venue_id')} mode={t.get('mode')}"
        )
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
