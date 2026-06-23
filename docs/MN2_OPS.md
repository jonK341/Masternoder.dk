# MN2 operations: daemon, env, scanner, reconciliation

Quick reference for running and maintaining the MN2 integration on the server.

---

## 1. Daemon

- **Install and start:** See [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) for download, config, and run.
- **Where:** Daemon runs on the **server** where the app is deployed (same host or reachable via `MN2_RPC_URL`).
- **Ports:** Mainnet RPC `9332`; testnet RPC `19332`. Set `rpcport` in `~/.masternoder2/masternoder2.conf` to match.

**Run command (production, config under web root):**

```bash
/path/to/masternoder2d -datadir=/var/www/html/config
```

Example if the binary is under `/opt`:

```bash
/opt/masternoder2d/masternoder2d -datadir=/var/www/html/config
```

Or: `cd /var/www/html && ./scripts/run_masternoder2d.sh` (set `MN2_BINARY` if the binary is not in `PATH`). **systemd:** `systemd/masternoder2d.service.example`.

**Default datadir (`~/.masternoder2/masternoder2.conf`):** the daemon must have **`server=1`** and valid **`rpcuser` / `rpcpassword`** (same as `.env`) or it often exits and never binds **9332**. Full steps: [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) (section *Production server — default datadir*).

**Deploy the script to the server:** it is included in the `mn2_env` manifest:

`python scripts/deploy.py mn2_env --upload-only` (files only, no uwsgi restart) or `python scripts/deploy.py mn2_env` (upload + restart uwsgi-vidgenerator).

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

**Recommended:** deploy the `mn2_env` manifest — it uploads `cron/mn2_scan_deposits.sh` and installs `/etc/cron.d/masternoder-mn2-scan` (every 5 minutes). Same as: `python scripts/deploy.py mn2_env`.

Alternatively, add a cron job by hand (e.g. every 5 minutes). **Do not paste the secret into crontab by hand** — read it from the same `.env` the app uses (`MN2_SCAN_SECRET` must match what uwsgi loads from `/var/www/html/.env`):

```bash
# Run MN2 deposit scanner every 5 minutes (token from deployed .env)
*/5 * * * * TOKEN=$(grep '^MN2_SCAN_SECRET=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"') && [ -n "$TOKEN" ] && curl -s -X POST -H "X-Scanner-Token: $TOKEN" "http://127.0.0.1:5000/api/mn2/scan-deposits" >/dev/null 2>&1
```

Install with `crontab -e` (as the user that can read `/var/www/html/.env`, usually **root**). If `MN2_SCAN_SECRET` is unset or empty in `.env`, the `TOKEN` test skips the curl call — set the variable in `.env` first (see local `.env` → deploy `mn2_env`).

If you set `MN2_SCAN_SECRET` in `.env`, the request must include that value in the `X-Scanner-Token` header or in `?token=...`. Otherwise the scanner endpoint returns 403.

**Production checklist:** After fixing RPC auth, confirm `components.mn2_rpc.status` is `healthy` on `GET /api/health/system` (not `auth_failed`). If you see `auth_failed`, the app’s `MN2_RPC_*` do not match the daemon — run `python scripts/verify_mn2_production_ready.py` locally before redeploying `config` + `mn2_env`.

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

## 8. Staking, on-ramp & P2P (daemon staking, rewards, reconcile, agents)

The staking system (plan: [MN2_STAKING_PLAN.md](MN2_STAKING_PLAN.md)) pools opted-in user MN2, earns **realized PoS yield** from the daemon, and distributes it weighted by stake × longevity × uptime × boost.

### 8.1 Make the daemon actually stake (sec.9)

In `masternoder2.conf`: `staking=1` / `enablestaking=1` (confirm exact keys for the MN2 build), and unlock the wallet **for staking only**:

```bash
masternoder2-cli walletpassphrase "<passphrase>" 0 true   # 0 = until restart, true = staking-only
```

Consolidate per-user deposit balances into the staking address (keep a small hot balance for withdrawals); the rest mints. **Health:** `GET /api/mn2/ops/stats` now returns `staking_health` (`status`, `staking_active`, `staking_weight`, `net_stake_weight`, `expected_time_to_reward_sec`, `mature_balance`, `immature_balance`) and a `pool` snapshot (`total_staked_mn2`, `dynamic_apr_percent`). `status: unreachable` = daemon down; `inactive` = wallet locked / not minting.

### 8.2 Hourly cron (rewards + holds + reconcile + agents)

Deployed by the `mn2_env` manifest: `cron/mn2_accrue_rewards.sh` + `/etc/cron.d/masternoder-mn2-accrue` (hourly). It reads the token from `/var/www/html/.env` (`MN2_OPS_SECRET`, falls back to `MN2_SCAN_SECRET`) and calls, in order:

1. `POST /api/mn2/staking/ops/accrue` — credit the interval's realized yield (idempotent per window).
2. `POST /api/mn2/onramp/ops/clear-matured` — release matured PayPal→MN2 holds (makes MN2 withdrawable).
3. `POST /api/mn2/p2p/ops/clear-matured` — release matured P2P buyer MN2 + seller payouts.
4. `POST /api/mn2/staking/ops/reconcile` — conservation check; **HTTP 409** = drift (logged to stderr for alerting).
5. `POST /api/agent/staking/ops/run-all` — drive autonomous staking personas one policy step.

### 8.3 Reconciliation / conservation invariant (sec.8)

`scripts/mn2_reconcile.py` now also prints the staking invariant (or hit `POST /api/mn2/staking/ops/reconcile` with an ops token). Hard checks (drift → 409 / non-zero exit):

- `rewards_rows_match_ledger` — Σ reward rows == Σ `staking_reward` ledger.
- `staked_matches_ledger` — live staked == Σ`stake` − Σ`unstake` (auto-compound emits `stake`).
- `onramp_purchase_match_ledger` / `onramp_clawback_match_ledger`.
- `p2p_escrow_conservation` — outstanding listing escrow == escrowed − returned − delivered.
- `no_pay_over_realized_yield` — only enforced in `reward_pool_mode: realized_yield` with realized data.

**On drift:** stop accrual (`agent.automation_enabled: false` won't stop accrual — set the cron off or `enabled: false` in `mn2_staking_config.json`), inspect `data/mn2_staking_rewards.jsonl`, `data/mn2_ledger.json`, `data/mn2_stakes.json`, and the on-ramp/P2P order stores, then correct before re-enabling.

### 8.4 Secrets & kill switches

| Variable | Purpose |
|----------|---------|
| `MN2_OPS_SECRET` (or `MN2_SCAN_SECRET`) | Gates all `/ops/*` endpoints (accrue, reconcile, clear-matured, run-all). |
| `AGENT_MN2_STAKING_SECRET` (or `AGENT_MN2_SHOP_SECRET`) | Gates the agent automation layer (`/api/agent/staking/execute` write verbs). Rotate independently. |

Config kill switches in `data/mn2_staking_config.json`: `enabled` (whole system), `p2p.enabled` (P2P market — **currently true**), `onramp.enabled` (on-ramp), `agent.automation_enabled` (autonomous personas only). Withdrawals of PayPal-purchased MN2 are blocked until their hold clears (`code: onramp_hold`).

### 8.5 Files

`data/mn2_staking_config.json`, `mn2_staking_terms.json`, `mn2_stakes.json`, `mn2_staking_reserve.json`, `mn2_staking_rewards.jsonl`, `mn2_onramp_orders.{json,jsonl}`, `mn2_p2p_{listings,orders,payouts}.json` + `mn2_p2p_events.jsonl`, `agent_staking_agents.json`, `mn2_staking_agent_activity.jsonl`. Back these up with the ledger.

---

## 9. References

- [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) — Install and run the daemon.
- [EXPLORER_REINSTALL_CHECKLIST.md](EXPLORER_REINSTALL_CHECKLIST.md) — Reinstall **iquidus** explorer for **camgirls.masternoder.dk** (Mongo, `settings.json`, PM2, nginx).
- [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md) — Full integration plan and phases.
- [MN2_SHOP_AND_ADDRESSES.md](MN2_SHOP_AND_ADDRESSES.md) — Shop revenue address and config.

## Waterfall merge order (split PRs #19–#27)

Recommended sequence when landing the `cursor/monetized-content-crypto` split off `main` (merge each PR only after the prior one is green and merged):

1. **#21** deploy-tooling — deploy manifests and SSH ask-pass
2. **#19** mn2-fleet-provision-ops — fleet provisioning, RPC, hosting alias repair
3. **#20** mn2-explorer-hub — explorer performance and masternodes tab
4. **#22** mn2-hosting-shop — shop checkout config and smoke scripts
5. **#23** docs-mn2-status — ops status, release build, env example
6. **#25** platform-page-shell — shared page-shell CSS (before pages that depend on it)
7. **#24** podcast-hub — podcast routes, services, UI
8. **#26** monetization-crypto-core — monetization platform core
9. **#27** split-leftovers — shop UI, rulebook assets, cogs/monetization route tweaks, P1 remote ops

Rebase later PRs onto updated `main` after each merge if GitHub reports conflicts.

