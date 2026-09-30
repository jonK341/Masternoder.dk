import json
from backend.services.exchange_sales_pool_service import (
    sales_pool_status,
    run_sales_pool_tick,
    list_agent_wallet_balances,
)

def slim_status(st):
    return {
        "pool_assets": st.get("pool_assets"),
        "pool_gaps": st.get("pool_gaps"),
        "last_transfer_at": st.get("last_transfer_at"),
        "transfer_count": st.get("transfer_count"),
    }

def agent_summary(st):
    out = []
    for a in st.get("source_agents") or []:
        out.append({
            "agent_id": a.get("agent_id"),
            "assets": a.get("assets"),
            "transferable": a.get("transferable"),
        })
    return out

before = sales_pool_status()
print("=== BEFORE ===")
print(json.dumps({"pool": slim_status(before), "agents": agent_summary(before)}, indent=2))

tick = run_sales_pool_tick(force=True)
after = sales_pool_status()

print("\n=== TICK RESULT ===")
tick_out = {k: v for k, v in tick.items() if k != "status"}
print(json.dumps(tick_out, indent=2, default=str))

print("\n=== AFTER ===")
print(json.dumps({"pool": slim_status(after), "agents": agent_summary(after)}, indent=2))

transfers = [t for t in (tick.get("transfers") or []) if t.get("success")]
failed = [t for t in (tick.get("transfers") or []) if not t.get("success")]

print("\n=== TRANSFERS THIS RUN ===")
print(json.dumps([{"symbol": t.get("symbol"), "amount": t.get("amount"), "from_agent": t.get("agent_id")} for t in transfers], indent=2))
if failed:
    print("\n=== TRANSFER ERRORS ===")
    print(json.dumps(failed, indent=2))

before_pool = before.get("pool_assets") or {}
after_pool = after.get("pool_assets") or {}
all_syms = sorted(set(before_pool) | set(after_pool) | set(before.get("pool_gaps") or {}) | set(after.get("pool_gaps") or {}))
pool_delta = {}
for s in all_syms:
    b = float(before_pool.get(s) or 0)
    a = float(after_pool.get(s) or 0)
    if abs(a - b) > 1e-15:
        pool_delta[s] = {"before": b, "after": a, "delta": round(a - b, 12)}
print("\n=== COMPARISON ===")
print(json.dumps({"pool_delta": pool_delta, "gaps_before": before.get("pool_gaps"), "gaps_after": after.get("pool_gaps"), "skipped": tick.get("skipped"), "reason": tick.get("reason")}, indent=2))
