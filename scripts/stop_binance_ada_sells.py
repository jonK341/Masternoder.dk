#!/usr/bin/env python3
"""Emergency: cancel ALL open Binance orders (esp. ADA sells) and keep Binance grid disabled.

Why: reset_open_orders('binance') only cancels tracked targets. Once Binance is in
disabled_venues, it has zero targets — so old resting sells keep filling.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import _load_deploy_env_from_dotenv, connect_deploy_ssh, require_deploy_pass

REMOTE_ROOT = "/var/www/html"
REMOTE_ENV = f"{REMOTE_ROOT}/.env"


def upsert_remote_key(ssh, key: str, value: str) -> str:
    safe_val = value.replace("'", "'\"'\"'")
    cmd = (
        f"test -f {REMOTE_ENV} || touch {REMOTE_ENV}; "
        f"if grep -q '^{key}=' {REMOTE_ENV}; then "
        f"  sed -i 's|^{key}=.*|{key}={safe_val}|' {REMOTE_ENV}; echo updated; "
        f"else echo '{key}={safe_val}' >> {REMOTE_ENV}; echo appended; fi"
    )
    _, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err and "updated" not in out and "appended" not in out:
        return f"err:{err[-200:]}"
    return out or "ok"


def main() -> int:
    _load_deploy_env_from_dotenv()
    if not (os.environ.get("DEPLOY_PASS") or "").strip():
        print("ERROR: DEPLOY_PASS unset")
        return 2

    # Ensure local config still disables Binance.
    cfg_path = os.path.join(ROOT, "data", "exchange_grid_bot_config.json")
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    disabled = {str(v).lower() for v in (cfg.get("disabled_venues") or [])}
    disabled.update({"binance", "xeggex"})
    cfg["disabled_venues"] = sorted(disabled)
    cfg["allow_sell_existing_inventory"] = False
    cfg["venue"] = "nonkyc"
    # Never seed Binance assets via legacy assets list.
    cfg["assets"] = []
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        tmp_remote = "/tmp/exchange_grid_bot_config.json"
        sftp.put(cfg_path, tmp_remote)
        sftp.close()
        mv = (
            f"cp {tmp_remote} {REMOTE_ROOT}/data/exchange_grid_bot_config.json && "
            f"chmod 644 {REMOTE_ROOT}/data/exchange_grid_bot_config.json && "
            f"wc -c {REMOTE_ROOT}/data/exchange_grid_bot_config.json"
        )
        _, stdout, stderr = ssh.exec_command(mv, timeout=30)
        print("uploaded grid config", stdout.read().decode().strip(), stderr.read().decode().strip())

        for key, val in (
            ("EXCHANGE_ROTATION_LIVE", "0"),
            ("EXCHANGE_ROTATION_AUTO", "0"),
        ):
            print(f"env {key}={val} ({upsert_remote_key(ssh, key, val)})")

        remote = r"""
cd /var/www/html
export DAEMON_QUIET=1 LITE_APP=1 EXCHANGE_ARBITRAGE_LIVE=1
python3 - <<'PY'
import json
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services import exchange_venue_api_service as vapi
from backend.services.exchange_grid_bot_service import (
    pause_venue, load_config, grid_targets, _read_state, _write_state, _key,
)

print('disabled_venues=', load_config().get('disabled_venues'))
print('binance_targets=', sum(1 for v,_ in grid_targets() if v=='binance'))

# 1) Cancel ALL open orders on Binance (empty symbol = all)
oo = vapi.get_open_orders('binance', '', dry_run=False)
body = oo.get('body')
orders = []
if isinstance(body, list):
    orders = body
elif isinstance(body, dict):
    orders = body.get('orders') or body.get('data') or []
if not orders and isinstance(oo.get('orders'), list):
    orders = oo.get('orders') or []
print('binance_open_fetch_ok=', oo.get('success'), 'status=', oo.get('status_code'), 'n=', len(orders))

cancelled = []
failed = []
ada_sells = 0
for o in orders:
    if not isinstance(o, dict):
        continue
    oid = o.get('orderId') or o.get('id') or o.get('_id')
    sym = str(o.get('symbol') or '')
    side = str(o.get('side') or '').upper()
    base = sym.replace('USDC','').replace('USDT','').replace('BUSD','') if sym else ''
    # Prefer explicit base from symbol like ADAUSDC
    if sym.endswith('USDC'):
        base = sym[:-4]
    elif sym.endswith('USDT'):
        base = sym[:-4]
    if base.upper() == 'ADA' and side == 'SELL':
        ada_sells += 1
    if not oid:
        continue
    # cancel_order needs a base asset or market; pass market=sym when present
    try:
        res = vapi.cancel_order('binance', base or 'ADA', str(oid), dry_run=False, market=sym or None)
        row = {'symbol': sym, 'side': side, 'order_id': oid, 'ok': bool(res.get('success')), 'status': res.get('status_code')}
        (cancelled if row['ok'] else failed).append(row)
    except Exception as exc:
        failed.append({'symbol': sym, 'side': side, 'order_id': oid, 'ok': False, 'error': str(exc)[:120]})

print('ada_sell_open_seen=', ada_sells)
print('cancelled=', len(cancelled))
print('failed=', len(failed))
for r in cancelled[:20]:
    print('  cancel_ok', r)
for r in failed[:10]:
    print('  cancel_fail', r)

# 2) Also cancel anything still tracked in grid state for binance:*
st = _read_state()
tracked_cancel = 0
for key, block in list(st.items()):
    if not isinstance(block, dict):
        continue
    if not str(key).startswith('binance:'):
        continue
    asset = str(key.split(':',1)[-1])
    for o in list(block.get('open_orders') or []):
        oid = o.get('order_id') or o.get('orderId')
        if not oid:
            continue
        try:
            vapi.cancel_order('binance', asset, str(oid), dry_run=False)
            tracked_cancel += 1
        except Exception:
            pass
    block['open_orders'] = []
    block['halted'] = True
    block['halt_reason'] = 'binance_disabled_manual'
    st[key] = block
_write_state(st)
print('tracked_binance_cancels=', tracked_cancel)

# 3) Pause Binance hard
print('pause', pause_venue('binance', reason='stop_ada_sells', manual=True))

# 4) Re-check open orders
oo2 = vapi.get_open_orders('binance', '', dry_run=False)
body2 = oo2.get('body')
orders2 = body2 if isinstance(body2, list) else (body2.get('orders') if isinstance(body2, dict) else []) or []
if not orders2 and isinstance(oo2.get('orders'), list):
    orders2 = oo2.get('orders') or []
sells_left = [o for o in orders2 if isinstance(o, dict) and str(o.get('side') or '').upper()=='SELL']
ada_left = [o for o in sells_left if 'ADA' in str(o.get('symbol') or '').upper()]
print('open_remaining=', len(orders2), 'sells_remaining=', len(sells_left), 'ada_sells_remaining=', len(ada_left))
for o in ada_left[:10]:
    print('  STILL', o.get('symbol'), o.get('side'), o.get('orderId') or o.get('id'), o.get('price'), o.get('origQty'))
PY
systemctl restart masternoder-profit-daemon.service
sleep 2
systemctl is-active masternoder-profit-daemon.service
"""
        _, stdout, stderr = ssh.exec_command(remote, timeout=180)
        print(stdout.read().decode(errors="replace").strip())
        err = stderr.read().decode(errors="replace").strip()
        if err:
            print("stderr:", err[-1500:])
        return stdout.channel.recv_exit_status()
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
