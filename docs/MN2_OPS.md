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

## 8.6 Agent treasury — cold-wallet policy (required before 600k MN2 distribution)

**Goal:** Custodial hot wallet on the server must never hold the full agent treasury at risk. Large distributions (e.g. 600k MN2 to trader agents) require a documented cold/hot split and sign-off.

| Rule | Detail |
|------|--------|
| **Hot wallet cap** | Keep only operational float on-server (staking pool + pending withdrawals + ≤7 days of expected agent top-ups). Document the cap in ops runbook. |
| **Cold storage** | Majority of treasury MN2 on addresses **not** on the web-server wallet (`ismine` check via `validateaddress`). Cold keys offline or on separate host. |
| **Distribution gate** | `POST /api/agents/treasury/distribute` requires `X-Ops-Secret` **and** recorded sign-off in `data/treasury_signoff.json` before any batch ≥100k MN2. |
| **Sign-off API** | `GET/POST /api/agents/treasury/sign-off` (ops-gated). `POST` body: `approver`, `cold_wallet_address`, optional `hot_cap_mn2`, `max_batch_mn2` (default 600000), `notes`, `require_reconcile_ok`. CLI: `python scripts/treasury_signoff.py --approver NAME --cold-wallet ADDR`. |
| **Reconcile snapshot** | `GET /api/agents/treasury/reconcile` — pre-flight ledger + daemon + staking conservation checks. |
| **Reconciliation** | Run `python scripts/mn2_reconcile.py` before and after each distribution; compare ledger + `unified_points` vs daemon `getbalance`. |
| **Rollback** | If distribute tx fails mid-batch, stop automation (`agent.automation_enabled: false`), preserve `logs/admin_audit.jsonl`, do not retry blindly. |
| **Sign-off checklist** | (1) Reconcile green · (2) Cold wallet address recorded · (3) Hot balance ≤ cap · (4) Backup of stakes/ledger · (5) Named approver + timestamp in audit log |

Until sign-off is recorded, `distribute_agent_funding()` returns `treasury_signoff_required` for batches ≥100k MN2.

---

## 10. Discord cross-roads (M8 #51–60)

Outbound webhooks only — **Gate S:** no custody on Discord; users link accounts and claim rewards on-site.

**Canonical doc:** [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md) · Trader market events: [MN2_TRADER_MARKET.md](MN2_TRADER_MARKET.md)

### 10.1 Environment

| Variable | Purpose |
|----------|---------|
| `DISCORD_WEBHOOK_URL` | Default webhook (all channels if no per-channel override) |
| `DISCORD_CHANNEL_ID_MARKET` | Optional dedicated webhook for `#market` |
| `DISCORD_CHANNEL_ID_CASINO` | Optional dedicated webhook for `#casino` |
| `DISCORD_OPS_SECRET` | Auth for cron + ops POST endpoints |
| `BASE_URL` | Links in embeds (default `https://masternoder.dk`) |
| `MARKET_DISCORD_MIN_MN2` | Min fill size to post to Discord (default `5`) |

### 10.2 Crons

Deploy via `python scripts/deploy.py mn2_staking --ask-pass` (uploads scripts under `cron/`).

Optional env + verify in one SSH session:

```powershell
# 1) Audit only — see what is missing
python scripts/mn2_ops_optionals_remote.py --ask-pass --audit

# 2) Bootstrap auto-secrets, crons, reload, smoke
python scripts/mn2_ops_optionals_remote.py --ask-pass --all

# 3) Or chain with next-ops (market crons + optionals)
python scripts/mn2_next_ops_remote.py --ask-pass --optionals
```

**Auto-generated on server** (if missing): `AGENT_CRON_SECRET`, `COGS_ADMIN_REPORT_KEY`.

**Still manual** (pass flags or edit server `.env`):

| Key | Flag / action |
|-----|----------------|
| `NOTIFY_ADMIN_EMAIL` | `--notify-email you@domain` |
| `NOTIFY_SMTP_*` | edit server `.env` |
| `LIVEKIT_*` | `--livekit-url` / `--livekit-api-key` / `--livekit-api-secret` |
| `DISCORD_CHANNEL_ID_MARKET` | `--discord-market-webhook https://discord.com/api/webhooks/...` |

**Deploy remember:** always ship `backend/services/monetization_config_service.py` with any `data/monetization_config.json` change (generator API tiers, `mobile_iap`, coin packs). It is in the `mn2_staking` manifest; minimal hotfix:

```powershell
python scripts/deploy.py --files backend/services/monetization_config_service.py --ask-pass
python scripts/apply_updates.py --ask-pass
```

| Script | Endpoint | Purpose |
|--------|----------|---------|
| `cron/discord_digest.sh` | `POST /api/discord/digest/run` | Daily platform news → `#announcements` |
| `cron/discord_activity_funnel.sh` | `POST /api/discord/m8/alert-funnel` | High-signal activity → `#activity` |
| `cron/discord_casino_fanout.sh` | `POST /api/discord/casino/fanout` | Casino wins → `#casino` |
| `cron/discord_market_fanout.sh` | `POST /api/discord/market/fanout` | Market fills + trader ticks → `#market` |

Example install (read secret from deployed `.env`):

```bash
chmod +x /var/www/html/cron/discord_market_fanout.sh
# Every 15 min — align with agents_trader.sh cadence
*/15 * * * * /var/www/html/cron/discord_market_fanout.sh
```

### 10.3 Manual smoke tests

```bash
SECRET=$(grep '^DISCORD_OPS_SECRET=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
curl -s http://127.0.0.1:5000/api/discord/status | jq
curl -s -X POST -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/discord/market/fanout | jq
curl -s -X POST -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/discord/m8/alert-funnel | jq
curl -s "http://127.0.0.1:5000/api/discord/support/faq?q=market" | jq
```

### 10.4 Health

- `GET /api/mn2/health` → `components.discord_outbox` (success rate, recent posts)
- Staking monitor → Health Ops Hub tile (`mn2-staking-monitor.js`)
- Outbox log: `logs/discord_outbox.jsonl` (created on first post)

### 10.5 Troubleshooting

**`unauthorized` on fan-out endpoints**

Discord ops routes accept `MN2_OPS_SECRET`, `DISCORD_OPS_SECRET`, or `ADMIN_OPS_SECRET` (same as trader market). Cron scripts read the first match from `/var/www/html/.env` via `cron/mn2_read_ops_secret.sh`.

```bash
# Use MN2_OPS_SECRET if DISCORD_OPS_SECRET is unset
SECRET=$(grep -E '^(MN2_OPS_SECRET|DISCORD_OPS_SECRET|ADMIN_OPS_SECRET)=' /var/www/html/.env | head -1 | cut -d= -f2- | tr -d '\r"')
curl -s -X POST -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/discord/market/fanout | jq
```

**`market discord fanout failed` from cron**

Cron does not load `.env` automatically — use the updated scripts (they source `mn2_read_ops_secret.sh`). After deploy:

```bash
chmod +x /var/www/html/cron/mn2_read_ops_secret.sh
/var/www/html/cron/discord_market_fanout.sh
```

**Duplicate crontab lines**

```bash
crontab -l | sort -u | crontab -
crontab -l | grep discord_market
```

**`discord_outbox.jsonl` missing**

Normal until the first successful (or attempted) webhook post. Run fan-out once; then `tail logs/discord_outbox.jsonl`.

**`webhook_not_configured` in outbox**

Set `DISCORD_WEBHOOK_URL` in `.env` and restart uWSGI (`touch /var/www/html/.uwsgi_touch_reload`).

---

## 10. Masternode hosting (50 slots + PayPal)

**Explorer UI:** `/explorer?tab=masternodes` — slot meter, fleet cards, PayPal checkout (**$4.99/slot**, max 5 per order). Purchase is **fully automated**: PayPal capture → slot reserved → collateral locked → masternode started (cron retries until live).

**Config:** `data/mn2_masternode_config.json` (`max_hosted_nodes: 50`, `auto_provision: true`, `paypal.price_usd_per_slot: 4.99`). Registry: `data/mn2_masternode_hosts.json` (not in deploy manifest — server file is preserved).

**Env (automation):**

| Variable | Purpose |
|----------|---------|
| `MN2_WALLET_PASSPHRASE` | Unlock wallet for `masternode start` (staking-only unlock) |
| `MN2_MASTERNODE_BROADCAST_IP` | Public IP in masternode.conf (falls back to `ops.external_ip`) |
| `MN2_MASTERNODE_PORT` | P2P port for masternode line (default `9333` in config) |

**Public API**

| Endpoint | Purpose |
|----------|---------|
| `GET /api/mn2/masternode/service` | Capacity, fleet, network, PayPal pricing |
| `GET /api/mn2/masternode/checkout/config` | Checkout limits |
| `POST /api/mn2/masternode/checkout/quote` | Reserve slot count |
| `POST /api/mn2/masternode/checkout/order` | Create PayPal order → `approve_url` |
| `POST /api/mn2/masternode/checkout/capture` | After PayPal return — auto-provisions slot(s) |
| `POST /api/mn2/masternode/webhook` | PayPal webhook — capture + provision without browser |
| `POST /api/mn2/masternode/provision-pending` | Cron/ops — retry hosts still provisioning |

**Ops (X-Ops-Secret / MN2_OPS_SECRET)**

```bash
curl -s -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/mn2/masternode/hosts | jq
curl -s -X POST -H "Content-Type: application/json" -H "X-Ops-Secret: $SECRET" \
  -d '{"id":"platform-mn-2","label":"Fleet #2","status":"queued"}' \
  http://127.0.0.1:5000/api/mn2/masternode/hosts
```

**Deploy + seed from workstation**

```powershell
python scripts/deploy.py mn2_staking --ask-pass
python scripts/mn2_seed_platform_hosts_remote.py --ask-pass
```

**On-chain enable (per node):** each masternode needs a **10,000 MN2** collateral UTXO. Check availability:

```bash
curl -s -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/mn2/masternode/collateral-outputs | jq
```

Then split/send collateral, add `masternode.conf` entries, and `masternode start` / broadcast. **Paid slots auto-run this** when `auto_provision: true` (default); cron `mn2_masternode_provision.sh` retries every 2 minutes.

**PayPal webhook:** point PayPal Notifications to `https://masternoder.dk/api/mn2/masternode/webhook` (or reuse on-ramp webhook URL if you multiplex events). Requires `PAYPAL_WEBHOOK_ID` in `.env`.

---

## 9. References

- [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) — Install and run the daemon.
- [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md) — Discord integration map and cross-road backlog.
- [MN2_TRADER_MARKET.md](MN2_TRADER_MARKET.md) — Internal order book + trader agents.
- [EXPLORER_REINSTALL_CHECKLIST.md](EXPLORER_REINSTALL_CHECKLIST.md) — Reinstall **iquidus** explorer for **camgirls.masternoder.dk** (Mongo, `settings.json`, PM2, nginx).
- [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md) — Full integration plan and phases.
- [MN2_SHOP_AND_ADDRESSES.md](MN2_SHOP_AND_ADDRESSES.md) — Shop revenue address and config.
