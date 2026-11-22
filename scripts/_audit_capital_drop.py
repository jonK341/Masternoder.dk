#!/usr/bin/env python3
"""Audit Binance capital: full balances, recent trades, deposits, withdraws."""
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
import json, os, time
os.environ.setdefault('DAEMON_QUIET','1')
os.environ.setdefault('LITE_APP','1')
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services import exchange_venue_api_service as vapi
from backend.services import crypto_exchange_service as ex
from backend.services.exchange_binance_withdraw_service import (
    list_deposit_history, get_spot_asset_free, binance_credentials
)
import urllib.parse, hmac, hashlib, requests

creds = binance_credentials()
key, secret = creds.get('api_key'), creds.get('api_secret')

def signed_get(path, params=None):
    params = dict(params or {})
    params['timestamp'] = int(time.time()*1000)
    params['recvWindow'] = 10000
    q = urllib.parse.urlencode(params)
    sig = hmac.new(secret.encode(), q.encode(), hashlib.sha256).hexdigest()
    url = f"https://api.binance.com{path}?{q}&signature={sig}"
    r = requests.get(url, headers={'X-MBX-APIKEY': key}, timeout=20)
    try:
        body = r.json()
    except Exception:
        body = r.text[:500]
    return r.status_code, body

# Full account balances including locked + LD*
st, acct = signed_get('/api/v3/account')
balances = []
total_usd = 0.0
if isinstance(acct, dict):
    for row in acct.get('balances') or []:
        free = float(row.get('free') or 0)
        locked = float(row.get('locked') or 0)
        if free <= 0 and locked <= 0:
            continue
        asset = row.get('asset')
        base = asset[2:] if str(asset).startswith('LD') and len(str(asset))>2 else asset
        px = float(ex._price_usd(base) or ex._price_usd(asset) or 0)
        if asset in ('USDC','USDT','BUSD','FDUSD'):
            px = 1.0
        if asset == 'EUR':
            px = 1.08
        if asset == 'DKK':
            px = 0.15
        usd = (free+locked)*px
        balances.append({'asset': asset, 'free': free, 'locked': locked, 'px': px, 'usd': round(usd,4)})
        total_usd += usd

balances.sort(key=lambda x: -x['usd'])

# Recent myTrades for main pairs since ~18h ago (approx since $74 status)
# Use income / trade list via userTrades for USDC pairs we know
pairs = ['BTCUSDC','XRPUSDC','ADAUSDC','DOGEUSDC','TRXUSDC','SOLUSDC','ETHUSDC','BNBUSDC','LTCUSDC','LINKUSDC']
trades = []
start_ms = int((time.time() - 20*3600) * 1000)
for pair in pairs:
    st2, body = signed_get('/api/v3/myTrades', {'symbol': pair, 'startTime': start_ms, 'limit': 50})
    if isinstance(body, list):
        for t in body:
            trades.append({
                'symbol': pair,
                'id': t.get('id'),
                'side': 'BUY' if t.get('isBuyer') else 'SELL',
                'qty': float(t.get('qty') or 0),
                'price': float(t.get('price') or 0),
                'quote': float(t.get('quoteQty') or 0),
                'commission': float(t.get('commission') or 0),
                'commissionAsset': t.get('commissionAsset'),
                'time': t.get('time'),
            })

trades.sort(key=lambda x: x.get('time') or 0)

buy_usd = sum(t['quote'] for t in trades if t['side']=='BUY')
sell_usd = sum(t['quote'] for t in trades if t['side']=='SELL')
fees = {}
for t in trades:
    a = t.get('commissionAsset') or '?'
    fees[a] = fees.get(a, 0) + float(t.get('commission') or 0)

# Deposit / withdraw history
st3, deps = signed_get('/sapi/v1/capital/deposit/hisrec', {'startTime': start_ms})
st4, wds = signed_get('/sapi/v1/capital/withdraw/history', {'startTime': start_ms})

# Flexible earn positions if any
st5, earn = signed_get('/sapi/v1/simple-earn/flexible/position', {'size': 100})

out = {
    'account_http': st,
    'spot_usd_est': round(total_usd, 2),
    'balances': balances[:40],
    'trades_20h': len(trades),
    'buy_usd_20h': round(buy_usd, 2),
    'sell_usd_20h': round(sell_usd, 2),
    'net_quote_flow': round(sell_usd - buy_usd, 2),
    'fees': {k: round(v, 8) for k,v in fees.items()},
    'recent_trades': trades[-25:],
    'deposits': deps if isinstance(deps, list) else {'raw': str(deps)[:300]},
    'withdraws': wds if isinstance(wds, list) else {'raw': str(wds)[:300]},
    'earn_http': st5,
    'earn': earn if isinstance(earn, (list, dict)) else str(earn)[:300],
}
print(json.dumps(out))
PY
"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")
    _, stdout, stderr = ssh.exec_command(REMOTE_PY, timeout=180)
    out = (stdout.read() or b"").decode(errors="replace")
    err = (stderr.read() or b"").decode(errors="replace")
    data = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and '"spot_usd_est"' in line:
            try:
                data = json.loads(line)
                break
            except Exception:
                pass
    if not data:
        print("FAILED to parse")
        print(out[-2000:])
        print(err[-1000:])
        ssh.close()
        return 1

    print(f"\n=== TOTAL SPOT+LOCKED ~${data['spot_usd_est']} ===")
    for b in data["balances"]:
        if b["usd"] >= 0.01 or b["free"] > 0 or b["locked"] > 0:
            print(f"  {b['asset']}: free={b['free']} locked={b['locked']} px={b['px']} ~${b['usd']}")

    print(f"\n=== TRADES last ~20h: {data['trades_20h']} ===")
    print(f"  bought ${data['buy_usd_20h']} | sold ${data['sell_usd_20h']} | sell-buy net ${data['net_quote_flow']}")
    print(f"  fees: {data['fees']}")
    for t in data["recent_trades"]:
        ts = datetime.fromtimestamp((t["time"] or 0) / 1000, tz=timezone.utc).isoformat()
        print(
            f"  {ts} {t['side']:4} {t['symbol']} qty={t['qty']} @ {t['price']} "
            f"quote=${t['quote']:.4f} fee={t['commission']}{t['commissionAsset']}"
        )

    print("\n=== DEPOSITS ===")
    deps = data["deposits"]
    if isinstance(deps, list):
        if not deps:
            print("  (none)")
        for d in deps[:20]:
            print(f"  {d}")
    else:
        print(f"  {deps}")

    print("\n=== WITHDRAWS ===")
    wds = data["withdraws"]
    if isinstance(wds, list):
        if not wds:
            print("  (none)")
        for w in wds[:20]:
            print(
                f"  {w.get('coin')} {w.get('amount')} status={w.get('status')} "
                f"addr={str(w.get('address') or '')[:12]}... id={w.get('id')}"
            )
    else:
        print(f"  {wds}")

    print("\n=== FLEXIBLE EARN ===")
    print(json.dumps(data.get("earn"), indent=2)[:2000])

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
