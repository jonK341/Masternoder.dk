# MN2 Micro-Transactions / Instant Rewards

Instant in-app MN2 credits for small rewards (shop, casino, quests, login, etc.) without a chain transaction per payout.

## Architecture

```
Reward trigger (shop / casino / quest / cron)
        │
        ▼
 instant_payout()  or  POST /api/mn2/micro-tx/payout
        │
        ├── validate source, min/max, daily cap, rate limit
        ├── idempotency key (dedupe retries)
        ├── unified_points_db.add_points(mn2_balance)
        ├── mn2_ledger.append_entry(micro_tx_reward)
        └── audit log (logs/mn2_micro_tx/ledger.jsonl)
```

Balances update immediately in the user's wallet UI via existing `mn2_balance` / unified points.

## Python integration (preferred in-process)

```python
from backend.services.mn2_micro_tx_service import instant_payout

result = instant_payout(
    user_id="user_abc123",
    amount_mn2=0.0001,          # optional if source has default in config
    reason="Quest wave-2 complete",
    source="quest_complete",
    idempotency_key="quest:w2:user_abc123:2026-09-10",
)
if result.get("success"):
    print(result["mn2_balance"], result["amount_mn2"])
```

## HTTP API

### POST `/api/mn2/micro-tx/payout`

Auth: `X-MN2-Callback-Token` (MN2_CALLBACK_SECRET) or `X-Ops-Token` (MN2_OPS_SECRET).

```json
{
  "user_id": "user_abc123",
  "amount_mn2": 0.0001,
  "reason": "Casino spin win",
  "source": "casino_spin",
  "idempotency_key": "spin:abc123:round-99"
}
```

Response (200):

```json
{
  "success": true,
  "payout_id": "mtx-…",
  "amount_mn2": 0.0001,
  "mn2_balance": 1.23456789,
  "instant": true,
  "idempotency_key": "spin:abc123:round-99"
}
```

### GET `/api/mn2/micro-tx/stats`

- User: session or `?user_id=`
- Platform: `?scope=platform` (ops auth)

### GET `/api/mn2/micro-tx/config`

Public limits and allowed sources.

## Frontend hook

Include `static/js/mn2-micro-tx.js` or call directly:

```javascript
await window.MN2MicroTx?.payout({
  source: 'daily_login',
  reason: 'Daily login bonus',
  idempotency_key: `login:${userId}:${new Date().toISOString().slice(0, 10)}`,
});
await window.MN2MicroTx?.refreshBalance();
```

Server-side triggers should use `instant_payout()` — the JS helper is for authenticated flows that proxy through your backend callback token.

## Config

`data/mn2_micro_tx_config.json` — min/max amounts, daily cap, allowed sources, default amounts per source.

## Ops / batch sweep

Optional nightly cron marks users whose in-app balance exceeds `batch_sweep.threshold_mn2` for treasury review. Does not auto-withdraw on-chain.

```bash
curl -X POST -H "X-Ops-Token: $MN2_OPS_SECRET" \
  http://127.0.0.1:5000/api/mn2/micro-tx/ops/batch-sweep
```

Cron: `cron/mn2_micro_tx_batch.sh` → `/etc/cron.d/masternoder-mn2-micro-tx`

## Deploy

```bash
python scripts/deploy.py mn2_staking
```

Manifest includes micro-tx service, routes, config, and cron scripts.
