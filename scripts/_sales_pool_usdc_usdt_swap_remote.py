"""One-shot prod USDC->USDT swap for exchange_sales_pool."""
from __future__ import annotations

import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, _load_deploy_env_from_dotenv

REMOTE_PY = r'''
import json
import uuid
from backend.services import crypto_exchange_service as ex
from backend.services.exchange_sales_pool_service import sales_pool_status, sales_pool_user_id

def slim(st):
    return {
        "pool_assets": st.get("pool_assets"),
        "pool_gaps": st.get("pool_gaps"),
    }

uid = sales_pool_user_id()
before = sales_pool_status()
gaps = before.get("pool_gaps") or {}
usdt_gap = float(gaps.get("USDT") or 0)
# Target ~450-490 USDT received; close most of gap with small buffer
if usdt_gap <= 0:
    buy_amt = 0.0
else:
    buy_amt = round(min(490.0, max(450.0, usdt_gap - 5.0)), 4)
    if buy_amt > usdt_gap:
        buy_amt = round(usdt_gap, 4)

swap_result = {"skipped": True, "reason": "no_usdt_gap", "usdt_gap": usdt_gap}
if buy_amt > 0:
    q = ex.quote_swap(uid, "USDT", "buy", buy_amt, "USDC")
    if not q.get("success"):
        swap_result = {"success": False, "phase": "quote", "buy_amount_usdt": buy_amt, "quote": q}
    else:
        qid = q.get("quote_id") or uuid.uuid4().hex[:16]
        res = ex.execute_swap(uid, qid, "USDT", "buy", buy_amt, "USDC")
        swap_result = {
            "success": bool(res.get("success")),
            "phase": "execute",
            "buy_amount_usdt": buy_amt,
            "quote_summary": {
                "quote_cost": q.get("quote_cost"),
                "fee_quote": q.get("fee_quote"),
                "price_quote": q.get("price_quote"),
            },
            "execute": {k: v for k, v in res.items() if k not in ("wallet",)},
        }

after = sales_pool_status()
bp = before.get("pool_assets") or {}
ap = after.get("pool_assets") or {}
delta = {}
for s in sorted(set(bp) | set(ap)):
    b, a = float(bp.get(s) or 0), float(ap.get(s) or 0)
    if abs(a - b) > 1e-12:
        delta[s] = {"before": b, "after": a, "delta": round(a - b, 12)}

print(json.dumps({
    "host": "masternoder.dk",
    "pool_user": uid,
    "before": slim(before),
    "swap": swap_result,
    "after": slim(after),
    "pool_delta": delta,
    "gaps_before": gaps,
    "gaps_after": after.get("pool_gaps"),
}, indent=2))
'''

WEB = "/var/www/html"


def main() -> int:
    _load_deploy_env_from_dotenv()
    pw = (os.environ.get("DEPLOY_PASS") or "").strip()
    ssh, auth, _ = connect_deploy_ssh(pw if pw else None)
    print(f"Connected to {deploy_user()}@{deploy_host()} via {auth}", file=sys.stderr)
    b64 = base64.b64encode(REMOTE_PY.encode()).decode()
    cmd = f"cd {WEB} && PYTHONPATH={WEB} python3 -c \"import base64; exec(base64.b64decode('{b64}').decode())\""
    _, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    # Redact anything that looks like a secret in stderr
    if err.strip():
        safe_err = err
        for key in ("DEPLOY_PASS", "password", "PASSWORD", "secret", "SECRET", "api_key"):
            if key.lower() in safe_err.lower():
                safe_err = "[stderr omitted — may contain sensitive data]"
                break
        print(safe_err, file=sys.stderr)
    print(out)
    ssh.close()
    return 0 if out.strip().startswith("{") else 1


if __name__ == "__main__":
    raise SystemExit(main())
