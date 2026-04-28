# MN2 plan review: from start to “wallets almost work” through production

Review of the MasterNoder2 (MN2) integration: original plan, what was built, current state, and what’s left for production.

---

## 1. Original plan (MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md)

- **Goal:** Use MN2 coins as currency on Masternoder.dk: wallets, balances, transactions, shop payment.
- **Model:** Custodial in-app MN2 balance (Option B). One backend wallet (daemon RPC); per-user deposit addresses; in-app `mn2_balance` in unified points; deposit → credit after N confirmations; withdraw via RPC; shop can deduct MN2.
- **Phases:**

| Phase | Scope | Deliverables |
|-------|--------|---------------|
| **1** | RPC + config | `mn2_rpc_client.py`, env/config for RPC URL and credentials; health check (`getblockcount`). |
| **2** | Balances + addresses | `mn2_wallet_service.py`; per-user deposit address; `GET /api/mn2/balance`, `GET /api/mn2/deposit-address`. |
| **3** | Ledger + deposits | Ledger storage; deposit scanner; credit `mn2_balance` and ledger; `GET /api/mn2/transactions`. |
| **4** | Withdrawals | `POST /api/mn2/withdraw`; validate, send via RPC, deduct balance, ledger. |
| **5** | Shop | MN2 price config; extend `shop_purchase` for `payment_method: "mn2"`; UI “Pay with MN2”. |
| **6** | UI | Wallet block on profile: balance, deposit address + QR, withdraw form, transaction list. |

Expanded plan (MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md) added: Chainz explorer links, ticker/price, testnet preference, fees, custody/RPC security, Phase 7 (ops: min/max withdrawal, Chainz fallback, scan/ops secrets), Phase 8 (on-chain order payment), Phase 9 (live price, withdrawal hardening).

---

## 2. What was implemented

### 2.1 Backend (Phases 1–6 + 7–9)

| Component | Status | Location |
|-----------|--------|----------|
| **RPC client** | Done | `backend/services/mn2_rpc_client.py` — `getblockcount`, `getnewaddress`, `getbalance`, `sendtoaddress`, `listtransactions`, etc.; env `MN2_RPC_URL`, `MN2_RPC_USER`, `MN2_RPC_PASSWORD`; 401/403 mapped to user-facing messages. |
| **Wallet service** | Done | `backend/services/mn2_wallet_service.py` — `get_or_create_deposit_address` (per-user + pool), `create_deposit_addresses(count)` for pool; uses RPC and `data/mn2_user_addresses.json`. |
| **Ledger** | Done | `backend/services/mn2_ledger.py` — append-only ledger; idempotency by txid; deposit/withdrawal/shop_payment. |
| **Deposit scanner** | Done | `backend/services/mn2_deposit_scanner.py` — `listtransactions`, match deposit addresses, credit after N confirmations; optional `MN2_SCAN_SECRET` for cron. |
| **MN2 routes** | Done | `backend/routes/mn2_routes.py` — balance, deposit-address, transactions, withdraw, scan-deposits, ops/create-addresses, order-payment (Phase 8), price (Phase 9). |
| **Shop MN2** | Done | `backend/routes/shop_routes.py` — `payment_method: "mn2"`; deduct `mn2_balance`, ledger, min/max withdrawal from config. |
| **Health** | Done | `backend/routes/health_routes.py` — `mn2_rpc` component (getblockcount); Chainz fallback when RPC down. |
| **Config** | Done | `data/mn2_config.json` — confirmations, withdrawal_fee, min/max withdrawal, coins_per_mn2, explorer_base_url, shop_revenue_address. |
| **Chainz** | Done | `backend/services/mn2_chainz.py` — ticker.usd (cached), explorer links; used in balance/price and health fallback. |

### 2.2 Frontend / UX

| Item | Status | Location |
|------|--------|----------|
| **Profile MN2 block** | Done | `profile/index.html` — balance, deposit address, QR, Copy, “Request address” / Retry, withdraw form, recent transactions, explorer links, shop revenue address when set. |
| **Shop “Pay with MN2”** | Done | Shop purchase with `payment_method: "mn2"`; balance check; price in MN2. |
| **Theme / landing MN2** | Done | “Pay with MasterNoder2” badge/link on theme_premium and root. |

### 2.3 Ops and docs

| Item | Status | Location |
|------|--------|----------|
| **Daemon setup** | Done | `docs/MN2_DAEMON_SETUP.md` — download, extract, config, start; fix 401; link to password/config steps. |
| **Password + config path** | Done | `docs/MN2_CONFIG_AND_PASSWORD_STEPS.md` — set password in `config/masternoder2.conf` and `.env`; deploy config; daemon `-datadir=/var/www/html/config`. |
| **Ops reference** | Done | `docs/MN2_OPS.md` — env vars, scanner cron, reconciliation. |
| **Deploy config + .env** | Done | `deploy.py` manifests: `config` (config folder), `mn2_env` (.env + systemd units); `deploy_all_and_restart_uwsgi.py` includes config + .env; systemd loads `.env` for uwsgi. |
| **Gaps / optional** | Documented | `docs/MN2_INTEGRATION_GAPS.md` — Phase 7 done; optional: set `MN2_SCAN_SECRET` / `MN2_OPS_SECRET` in production. |

---

## 3. Current state: “wallets almost work”

- **Working (when RPC is reachable and auth is correct):**
  - Health: `mn2_rpc` in `/api/health/system` (or Chainz fallback).
  - Balance: `GET /api/mn2/balance` returns `mn2_balance`, coins_per_mn2, optional USD price.
  - Deposit address: `GET /api/mn2/deposit-address` returns per-user address (or assigns from pool / creates via RPC).
  - Transactions: `GET /api/mn2/transactions` returns ledger with explorer links.
  - Withdraw: `POST /api/mn2/withdraw` (with min/max and optional verification).
  - Shop: purchase with MN2; ledger and balance updated.
  - Profile: MN2 block shows balance, deposit address + QR, withdraw, history; “Request address” when missing.
  - Ops: create-addresses, scan-deposits (with optional token), ops/stats.

- **Blocking production (why “almost”):**
  - **RPC authentication (401):** On the server, the app’s `MN2_RPC_USER` / `MN2_RPC_PASSWORD` must match the daemon’s `rpcuser` / `rpcpassword`. If they don’t (or `.env` isn’t loaded by uwsgi), deposit-address and any RPC call return “Wallet RPC authentication failed” and no address is shown.
  - **Daemon not using project config:** Daemon must use the same credentials as the app. Either run with `-datadir=/var/www/html/config` so it reads `/var/www/html/config/masternoder2.conf`, or copy that file to `~/.masternoder2/` on the server.
  - **Scanner not running:** Deposits are only credited when the scanner runs (cron or manual). Production needs cron e.g. every 5 min with `MN2_SCAN_SECRET` set and token in the request.

So: code path is “wallets work”; production is blocked by server-side RPC credentials and daemon config path, plus scanner cron.

---

## 4. Path to production (end-to-end)

| # | Step | Reference |
|---|------|-----------|
| 1 | Set `rpcpassword` in `config/masternoder2.conf` (local); set same in `.env` as `MN2_RPC_PASSWORD`; `MN2_RPC_USER=mn2rpc`. | [MN2_CONFIG_AND_PASSWORD_STEPS.md](MN2_CONFIG_AND_PASSWORD_STEPS.md) |
| 2 | Deploy config and .env: `python scripts/deploy.py config` then `python scripts/deploy.py mn2_env` (or full deploy). | [MN2_CONFIG_AND_PASSWORD_STEPS.md](MN2_CONFIG_AND_PASSWORD_STEPS.md), [deploy.py](../scripts/deploy.py) |
| 3 | On server: run daemon with `-datadir=/var/www/html/config` (or copy `config/masternoder2.conf` to `~/.masternoder2/`). Restart daemon after any config change. | [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md), [MN2_CONFIG_AND_PASSWORD_STEPS.md](MN2_CONFIG_AND_PASSWORD_STEPS.md) |
| 4 | Ensure uwsgi loads `.env`: systemd unit has `EnvironmentFile=-/var/www/html/.env`. Restart: `systemctl restart uwsgi-vidgenerator`. | [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) |
| 5 | Verify RPC: `curl -u mn2rpc:PASSWORD -d '{"jsonrpc":"1.0","id":"1","method":"getblockcount","params":[]}' -H "Content-Type: application/json" http://127.0.0.1:9332`. | [MN2_CONFIG_AND_PASSWORD_STEPS.md](MN2_CONFIG_AND_PASSWORD_STEPS.md) |
| 6 | Verify app: `python scripts/test_deposit_address_api.py user_jon_ulrik` → “Deposit address: OK (real address)”. Profile page shows address. | [test_deposit_address_api.py](../scripts/test_deposit_address_api.py) |
| 7 | Enable scanner: set `MN2_SCAN_SECRET` in `.env` on server; add cron: `*/5 * * * * curl -s -X POST -H "X-Scanner-Token: $SECRET" "http://127.0.0.1:5000/api/mn2/scan-deposits"`. | [MN2_OPS.md](MN2_OPS.md) |
| 8 | (Optional) Pre-create addresses: `POST /api/mn2/ops/create-addresses?count=10` (with ops auth) or run `scripts/mn2_create_deposit_addresses.py` on server. | [mn2_wallet_service.py](../backend/services/mn2_wallet_service.py), [MN2_OPS.md](MN2_OPS.md) |

---

## 5. Summary

- **Plan:** Phases 1–6 (RPC, wallet, ledger, scanner, withdraw, shop, UI) plus 7–9 (ops, on-chain order payment, price) are defined and implemented in code and docs.
- **“Wallets almost work”:** All user-facing flows (balance, deposit address, transactions, withdraw, shop with MN2, profile block) work when the backend can talk to the MN2 daemon with valid credentials.
- **Production blocker:** Server-side RPC auth (`.env` with correct `MN2_RPC_USER` / `MN2_RPC_PASSWORD` loaded by uwsgi) and daemon config (same credentials, via `/config` or `~/.masternoder2`). After that, enable the deposit scanner (cron + optional `MN2_SCAN_SECRET`) so incoming MN2 is credited.

**Unblocking aids in-repo:** Run `python scripts/verify_mn2_production_ready.py` before deploy to confirm `.env` matches `config/masternoder2.conf`. On the server, `GET /api/health/system` includes `components.mn2_rpc.status`: `healthy`, `auth_failed` (wrong credentials — fix `.env` / daemon), or `unreachable` (daemon down or wrong URL). Example daemon unit: `systemd/masternoder2d.service.example` (`-datadir=/var/www/html/config`).

Follow [MN2_CONFIG_AND_PASSWORD_STEPS.md](MN2_CONFIG_AND_PASSWORD_STEPS.md) and [MN2_OPS.md](MN2_OPS.md) to close the gap and run MN2 in production.
