"""Sync prod agent wallets, force sales-pool sweep locally, push wallets back."""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, _load_deploy_env_from_dotenv

WEB = "/var/www/html"
LOCAL_WALLETS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "crypto_exchange",
    "wallets",
)
REMOTE_WALLET_NAMES = [
    "exchange_agent_casino_liquidity.json",
    "exchange_agent_layer1_scout.json",
    "exchange_agent_stable_router.json",
]


def remote_wallet_assets(ssh, name: str) -> dict:
    path = f"{WEB}/data/crypto_exchange/wallets/{name}"
    _, o, _ = ssh.exec_command(f"cat {path}", timeout=30)
    raw = o.read().decode()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_error": "invalid_json", "raw": raw[:500]}


def main() -> int:
    _load_deploy_env_from_dotenv()
    pw = (os.environ.get("DEPLOY_PASS") or "").strip()
    if not pw:
        print("ERROR: DEPLOY_PASS not set", file=sys.stderr)
        return 2

    from backend.services.exchange_sales_pool_service import (
        sales_pool_status,
        run_sales_pool_tick,
    )

    os.makedirs(LOCAL_WALLETS, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup = LOCAL_WALLETS + f".backup_{stamp}"
    if os.path.isdir(LOCAL_WALLETS):
        shutil.copytree(LOCAL_WALLETS, backup, dirs_exist_ok=True)

    ssh, auth, _ = connect_deploy_ssh(pw)
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})", file=sys.stderr)

    before_remote = {}
    for name in REMOTE_WALLET_NAMES:
        before_remote[name] = remote_wallet_assets(ssh, name)
        local_path = os.path.join(LOCAL_WALLETS, name)
        with open(local_path, "w", encoding="utf-8") as fh:
            json.dump(before_remote[name], fh, indent=2)
            fh.write("\n")

    # Pull sales pool wallet if present on prod
    pool_name = "exchange_sales_pool.json"
    pool_remote = remote_wallet_assets(ssh, pool_name)
    if "_error" not in pool_remote:
        with open(os.path.join(LOCAL_WALLETS, pool_name), "w", encoding="utf-8") as fh:
            json.dump(pool_remote, fh, indent=2)
            fh.write("\n")

    before = sales_pool_status()
    tick = run_sales_pool_tick(force=True)
    after = sales_pool_status()

    sftp = ssh.open_sftp()
    push_names = REMOTE_WALLET_NAMES + [pool_name]
    for name in push_names:
        local_path = os.path.join(LOCAL_WALLETS, name)
        if not os.path.isfile(local_path):
            continue
        remote_path = f"{WEB}/data/crypto_exchange/wallets/{name}"
        sftp.put(local_path, remote_path)
    sftp.close()
    ssh.close()

    transfers = [
        {"symbol": t.get("symbol"), "amount": t.get("amount"), "from_agent": t.get("agent_id")}
        for t in (tick.get("transfers") or [])
        if t.get("success")
    ]
    failed = [t for t in (tick.get("transfers") or []) if not t.get("success")]

    bp = before.get("pool_assets") or {}
    ap = after.get("pool_assets") or {}
    syms = sorted(set(bp) | set(ap) | set(before.get("pool_gaps") or {}) | set(after.get("pool_gaps") or {}))
    delta = {}
    for s in syms:
        b, a = float(bp.get(s) or 0), float(ap.get(s) or 0)
        if abs(a - b) > 1e-15:
            delta[s] = {"before": b, "after": a, "delta": round(a - b, 12)}

    out = {
        "environment": "prod_wallets_synced_via_ssh",
        "remote_before_wallets": before_remote,
        "before": {
            "pool_assets": before.get("pool_assets"),
            "pool_gaps": before.get("pool_gaps"),
            "agents": before.get("source_agents"),
        },
        "tick": {k: v for k, v in tick.items() if k != "status"},
        "transfers": transfers,
        "errors": failed,
        "after": {
            "pool_assets": after.get("pool_assets"),
            "pool_gaps": after.get("pool_gaps"),
            "agents": after.get("source_agents"),
            "last_transfer_at": after.get("last_transfer_at"),
            "transfer_count": after.get("transfer_count"),
        },
        "comparison": {
            "pool_delta": delta,
            "gaps_before": before.get("pool_gaps"),
            "gaps_after": after.get("pool_gaps"),
        },
        "local_wallet_backup": backup,
        "note": "exchange_sales_pool_service.py not on prod app tree; sweep ran locally against synced wallet JSON then pushed back.",
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
