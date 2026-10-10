# MN2 operations: daemon, env, scanner, reconciliation

Quick reference for running and maintaining the MN2 integration on the server.

---

## 1. Daemon

- **Install and start:** See [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) for download, config, and run.
- **Where:** Daemon runs on the **server** where the app is deployed (same host or reachable via `MN2_RPC_URL`).
- **Ports:** Mainnet RPC `9332`; testnet RPC `19332`. Set `rpcport` in `~/.masternoder2/masternoder2.conf` to match.

---

## 2. Environment variables

In the app’s `.env` on the server (see `.env.example`):

| Variable | Required | Description |
|----------|----------|-------------|
| `MN2_RPC_URL` | Yes (or defaults) | e.g. `http://127.0.0.1:9332`. Overrides network default. |
| `MN2_RPC_USER` | Yes | Must match `rpcuser` in daemon `masternoder2.conf`. |
| `MN2_RPC_PASSWORD` | Yes | Must match `rpcpassword` in daemon config. |
| `MN2_NETWORK` | No | `mainnet` (default) or `testnet`. Used only when `MN2_RPC_URL` is not set: mainnet → port 9332, testnet → port 19332. |
| `MN2_PROFILE_LOG` | No | Set to `1` to log each RPC call to `logs/mn2_rpc.jsonl` (method, duration_ms, ok). |
| `MN2_SCAN_SECRET` | No | If set, `POST /api/mn2/scan-deposits` requires `X-Scanner-Token: <value>` header or `?token=<value>` to match. Use in production so only cron (or your runner) can trigger the scanner. |

---

## 3. Deposit scanner

The scanner credits user balances when MN2 is received at their deposit addresses (after N confirmations). It does **not** run automatically; you must trigger it periodically.

### Option A: Cron

On the server, add a cron job (e.g. every 5 minutes):

```bash
# Run MN2 deposit scanner every 5 minutes (adjust URL and token if you set MN2_SCAN_SECRET)
*/5 * * * * curl -s -X POST -H "X-Scanner-Token: YOUR_MN2_SCAN_SECRET" "http://127.0.0.1:5000/api/mn2/scan-deposits" > /dev/null 2>&1
```

If you set `MN2_SCAN_SECRET` in `.env`, the request must include that value in the `X-Scanner-Token` header or in `?token=...`. Otherwise the scanner endpoint returns 403.

### Option B: Manual

```bash
curl -X POST "http://YOUR_SERVER/api/mn2/scan-deposits"
```

### Logs

When the scanner runs, it can log to `logs/mn2_deposit_scanner.jsonl` (one JSON object per run: `start`, `end`, `duration_s`, `txs_checked`, `credits_applied`, `error`). Ensure the `logs` directory exists and is writable.

---

## 4. Reconciliation (ledger vs wallet)

Periodically check that the sum of in-app balances (ledger) is consistent with the daemon wallet balance.

- **Ledger:** `data/mn2_ledger.json` — entries with `type`: `deposit`, `withdrawal`, `shop_payment`.
- **Wallet:** RPC `getbalance` — total balance of the daemon wallet.

**Idea:** Sum over ledger: `total_deposits - total_withdrawals - total_shop_payments` ≈ sum of all users’ `mn2_balance` (from unified points). That sum should be ≤ daemon `getbalance` (daemon holds the coins; ledger is our bookkeeping). If you move MN2 out of the hot wallet (e.g. to cold or shop revenue address), ledger sum can exceed the hot wallet balance; then compare ledger net to (hot wallet + known external moves).

### Simple check (manual)

1. **Ledger net (deposits − withdrawals − shop_payment):**
   - Parse `data/mn2_ledger.json`, sum `amount` for `type=deposit`, subtract sum for `type=withdrawal` and `type=shop_payment`.

2. **Daemon balance:**
   - `curl -u user:pass -d '{"jsonrpc":"1.0","id":"mn2","method":"getbalance","params":[]}' -H "Content-Type: application/json" http://127.0.0.1:9332`

3. **User balances sum:**
   - Sum of `mn2_balance` over all users (from your points/store). This should match the ledger net.

You can script step 1 and 2 (and optionally 3) and alert if ledger net and wallet balance diverge beyond a small tolerance (e.g. fees or rounding).

---

## 5. Withdrawal verification (Phase 10)

If you set `withdrawal_requires_verification: true` in `data/mn2_config.json`, only users in the verified list can withdraw. The list is stored in `data/mn2_verified_users.json` (created on first add). Manage it by:

- **Ops API** (requires `MN2_OPS_SECRET` or `MN2_SCAN_SECRET` when set):
  - `GET /api/mn2/ops/verified-users` — list verified user_ids
  - `POST /api/mn2/ops/verify-user` — body `{ "user_id": "USER_ID", "action": "add" }` or `"action": "remove"`
- **File:** Edit `data/mn2_verified_users.json` (structure: `{"user_ids": ["id1", "id2"]}`).

Balance API returns `withdrawal_verified: true|false` when the gate is enabled so the UI can show a message and disable the withdraw button for unverified users.

---

## 6. Backup

- **Daemon:** Backup `~/.masternoder2/` (especially `wallet.dat` and `masternoder2.conf`). Do not commit `masternoder2.conf` with real passwords (use `.gitignore`).
- **App:** Backup `data/mn2_ledger.json`, `data/mn2_user_addresses.json`, and `data/mn2_config.json` with the rest of your app data.

---

## 7. References

- [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) — Install and run the daemon.
- [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md) — Full integration plan and phases.
- [MN2_SHOP_AND_ADDRESSES.md](MN2_SHOP_AND_ADDRESSES.md) — Shop revenue address and config.
