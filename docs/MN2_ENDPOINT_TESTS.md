# MN2 endpoint tests

## Run

From project root:

```bash
python scripts/test_mn2_all_endpoints.py [user_id]
```

Environment:

| Variable | Default | Purpose |
|----------|---------|---------|
| `BASE_URL` | `https://masternoder.dk` | Target site |
| `USER_ID` / argv | `user_jon_ulrik` | Query `user_id` for balance, deposit-address, transactions |
| `MN2_SCAN_TOKEN` | (or `MN2_SCAN_SECRET` from local `.env`) | If production sets `MN2_SCAN_SECRET`, set this to the same value to test `scan-deposits` and ops with auth |

Also:

```bash
python scripts/test_deposit_address_api.py user_jon_ulrik
```

## What is exercised

| Check | Method | Path |
|-------|--------|------|
| System health + `mn2_rpc` | GET | `/api/health/system` |
| Public price | GET | `/api/mn2/price` |
| Balance | GET | `/api/mn2/balance?user_id=…` |
| Deposit address | GET | `/api/mn2/deposit-address?user_id=…` |
| Ledger list | GET | `/api/mn2/transactions?user_id=…` |
| Profile HTML | GET | `/profile` |
| On-chain order payment | POST | `/api/mn2/order-payment` (body: `item_id`, `quantity`, `user_id`) |
| Order status | GET | `/api/mn2/order-payment/status?payment_ref=…` |
| Withdraw validation | POST | `/api/mn2/withdraw` (invalid address; no real send) |
| Ops stats | GET | `/api/mn2/ops/stats` |
| Verified users | GET | `/api/mn2/ops/verified-users` |
| Pool addresses | GET | `/api/mn2/ops/create-addresses?count=1` |
| Deposit scanner | POST | `/api/mn2/scan-deposits` |

## Interpreting failures

- **`Connection refused` on `127.0.0.1:9332`** — `masternoder2d` is not running on the app server, or not listening on the port in `MN2_RPC_URL`. Start the daemon; match `config/masternoder2.conf` / `-datadir` with `.env` `MN2_RPC_*`.
- **Health `503` with `degraded_fallback`** — Local RPC failed but Chainz fallback may still show a block height; overall health can be 503 while price/deposit-address still work if addresses are served from pool/file.
- **`GET /api/mn2/ops/create-addresses` returns non-JSON 500** — Deploy latest `backend/routes/mn2_routes.py` (wrapped in try/except so RPC/persist errors return JSON 200 + `success: false`).
- **`POST /api/mn2/scan-deposits` → 403** — Set `MN2_SCAN_TOKEN` to the server’s `MN2_SCAN_SECRET` (or leave secret unset only in dev).
- **Deposit address works but scanner/order-payment fail** — Address may come from **pool** (`pool_*` in `data/mn2_user_addresses.json`) without live RPC; new pool entries and on-chain flows still need the daemon.

## After code changes

Deploy backend routes, then restart uwsgi:

```bash
python scripts/deploy.py --files backend/routes/mn2_routes.py
# or include mn2_routes in your usual manifest
```
