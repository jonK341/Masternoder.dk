"""Prod USDC->USDT: buy fixed 500 USDT for exchange_sales_pool."""
import base64, json, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, _load_deploy_env_from_dotenv

BUY_USDT = 500.0
REMOTE_PY = f'''
import json
import uuid
from backend.services import crypto_exchange_service as ex
from backend.services.exchange_sales_pool_service import sales_pool_status, sales_pool_user_id

def slim(st):
    return {{"pool_assets": st.get("pool_assets"), "pool_gaps": st.get("pool_gaps")}}

uid = sales_pool_user_id()
before = sales_pool_status()
bp = before.get("pool_assets") or {{}}
usdc = float(bp.get("USDC") or 0)
buy_amt = {BUY_USDT}

swap_result = {{"skipped": True, "reason": "zero_amount"}}
if buy_amt > 0:
    q = ex.quote_swap(uid, "USDT", "buy", buy_amt, "USDC")
    if not q.get("success"):
        swap_result = {{"success": False, "phase": "quote", "buy_amount_usdt": buy_amt, "quote": q, "usdc_before": usdc}}
    else:
        cost = float(q.get("quote_cost") or 0) + float(q.get("fee_quote") or 0)
        if usdc < cost * 0.999:
            swap_result = {{"success": False, "phase": "precheck", "buy_amount_usdt": buy_amt, "usdc_before": usdc, "estimated_cost_usdc": cost, "quote_summary": {{"quote_cost": q.get("quote_cost"), "fee_quote": q.get("fee_quote")}}}}
        else:
            qid = q.get("quote_id") or uuid.uuid4().hex[:16]
            res = ex.execute_swap(uid, qid, "USDT", "buy", buy_amt, "USDC")
            swap_result = {{
                "success": bool(res.get("success")),
                "phase": "execute",
                "buy_amount_usdt": buy_amt,
                "usdc_before": usdc,
                "quote_summary": {{"quote_cost": q.get("quote_cost"), "fee_quote": q.get("fee_quote"), "price_quote": q.get("price_quote")}},
                "execute": {{k: v for k, v in res.items() if k not in ("wallet",)}},
            }}

after = sales_pool_status()
ap = after.get("pool_assets") or {{}}
delta = {{}}
for s in sorted(set(bp) | set(ap)):
    b, a = float(bp.get(s) or 0), float(ap.get(s) or 0)
    if abs(a - b) > 1e-12:
        delta[s] = {{"before": b, "after": a, "delta": round(a - b, 12)}}

usdt_after = float(ap.get("USDT") or 0)
gaps_after = after.get("pool_gaps") or {{}}
print(json.dumps({{
    "host": "masternoder.dk",
    "pool_user": uid,
    "target_buy_usdt": buy_amt,
    "before": slim(before),
    "swap": swap_result,
    "after": slim(after),
    "pool_delta": delta,
    "usdt_after": usdt_after,
    "usdt_gap_after": gaps_after.get("USDT"),
    "gaps_before": before.get("pool_gaps"),
    "gaps_after": gaps_after,
}}, indent=2))
'''

WEB = "/var/www/html"

def main():
    _load_deploy_env_from_dotenv()
    pw = (os.environ.get("DEPLOY_PASS") or "").strip()
    ssh, auth, _ = connect_deploy_ssh(pw if pw else None)
    print(f"Connected to {deploy_user()}@{deploy_host()} via {auth}", file=sys.stderr)
    b64 = base64.b64encode(REMOTE_PY.encode()).decode()
    cmd = f"cd {WEB} && PYTHONPATH={WEB} python3 -c \"import base64; exec(base64.b64decode('{b64}').decode())\""
    _, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    if err.strip():
        print(err, file=sys.stderr)
    print(out)
    ssh.close()
    return 0 if out.strip().startswith("{") else 1

if __name__ == "__main__":
    raise SystemExit(main())
