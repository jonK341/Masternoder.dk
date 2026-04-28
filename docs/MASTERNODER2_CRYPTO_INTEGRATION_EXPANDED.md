# MasterNoder2 crypto integration — expanded plan, perspectives & synthesis

This document expands [MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md](MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md) with: (1) block explorer integration, (2) concrete solutions, (3) multiple perspectives, (4) **monetization**, (5) **profiling**, (6) **prerequisites and completion checklist** (Phase 1 first), and (7) a synthesis and decision summary.

**Contents:** 1 [Block explorer](#1-block-explorer-chainz-cryptoid-mn2) · 2 [Open points](#2-solutions-to-open-points-from-original-plan-11) · 3 [Risks](#3-solutions-for-risks-from-original-plan-12) · 4 [Perspectives](#4-perspectives-brainstorm) · 5 [Monetization](#5-monetization) · 6 [Profiling](#6-profiling-and-observability) · 7 [Chainz by phase](#7-integration-of-chainz-into-implementation-phases) · 8 [Prerequisites](#8-prerequisites-and-whats-needed-to-complete-integration) (§8.4 [Account vs MN2 binding](#84-account-identity-vs-mn2-address-binding)) · 9 [Synthesis](#9-synthesis-and-decisions) · 10 [References](#10-references)

---

## 1. Block explorer: Chainz CryptoID (MN2)

**Explorer:** [https://chainz.cryptoid.info/mn2/](https://chainz.cryptoid.info/mn2/)

**What it provides (from explorer):**
- Latest blocks, rich list (top 1000 addresses), wealth distribution, hashrate, masternode count (~117k), extraction share.
- Public, read-only view of the MN2 chain — no custody, no RPC needed for *display* of chain state.

**API (Chainz):** [https://chainz.cryptoid.info/api.dws](https://chainz.cryptoid.info/api.dws)

- **Root for MN2:** `https://chainz.cryptoid.info/mn2/api.dws`
- **Rate limit:** 1 request every 10 seconds (no key); with free API key, some endpoints get live data and no cache delay.
- **Useful for Masternoder.dk:**

| Use case | Chainz API | Notes |
|----------|------------|--------|
| Link tx/address in UI | Build URLs only | `https://chainz.cryptoid.info/mn2/tx.dws?txid=...`, address pages for “View on explorer”. No API call. |
| Show MN2/USD price in UI | `?q=ticker.usd` | Optional; can replace or supplement config-driven rate. Cache 5–15 min to respect rate limit. |
| Verify address balance (read-only) | `?q=getbalance&a=ADDR` | Optional fallback if own RPC is down; 6h delay without key, live with key. |
| Block height / sync check | `?q=getblockcount` | Optional health check if daemon RPC unavailable. |
| Tx details for support | `?q=txinfo&t=TXID` | Link from ledger to explorer; optional server-side fetch for “confirmations” in UI. |

**Explorer URL patterns:** Put explorer base in config (e.g. `explorer_base_url`); build tx and address links from it (e.g. `tx.dws?txid=...` per Chainz). Keeps links consistent and easy to change.

**Decisions to fold into the plan:**
- **Always:** Use explorer **links** for every txid and deposit/withdrawal address (improves trust and support).
- **Optional (Phase 2+):** Use Chainz for **ticker.usd** with caching (e.g. 10 min) to show “MN2 price” and “item price in MN2” without running a price feed yourself.
- **Optional:** Request a free [API key](https://chainz.cryptoid.info/api.key.dws) to get live `getbalance` / no delay when you need to double-check an address (e.g. support).

---

## 2. Solutions to open points (from original plan — Open points)

| Open point | Solution | Rationale |
|------------|----------|-----------|
| **Ticker/symbol & decimals** | Assume **MN2**, **8 decimals** (Bitcoin-style) until confirmed in [MasterNoder2](https://github.com/jonK341/MasterNoder2) (chain params or docs). Store in `data/mn2_config.json`: `ticker: "MN2", decimals: 8`. | Keeps code consistent; one-place change when confirmed. |
| **Testnet** | Prefer **testnet for all dev/staging**; mainnet only for production. Add env `MN2_NETWORK=testnet|mainnet` and use corresponding RPC port/config in `masternoder2.conf`. | Reduces risk of spending real coins during development. |
| **InstantSend** | **Defer.** Do not rely on 0-conf for crediting. Use same N-conf rule (e.g. 6) for all deposits. Revisit only if MasterNoder2 documents InstantSend and you explicitly want “instant” credit for small amounts. | Keeps rules simple and avoids double-spend/rollback risk. |
| **Fees** | **Policy:** Deduct network fee from withdrawal amount (user receives `amount - fee`). Fee: either (1) fixed in config (e.g. 0.001 MN2) or (2) `estimatesmartfee` / equivalent from RPC if available. Document in UI: “Network fee: X MN2”. | Clear UX and no hidden cost; config allows tuning without code change. |

---

## 3. Solutions for risks (from original plan — Security/Conclusions)

| Risk | Mitigation |
|------|------------|
| **Custody** | Single hot wallet for site ops only; keep small balance; document cold storage procedure for reserves; consider time-locked or multi-sig for large holdings later. |
| **RPC security** | RPC only on localhost or internal network; strong `rpcpassword`; credentials in env (`MN2_RPC_*`); no RPC on public IP. |
| **Double-credit on deposits** | Ledger keyed by `txid`; before crediting, check `txid` not already in ledger; use a single background scanner process with lock. |
| **Withdrawal abuse** | Rate limit (e.g. N withdrawals per user per day); min/max amount in config; optional CAPTCHA or 2FA for large withdrawals later. |
| **Reconciliation** | Daily/weekly job: sum ledger `deposit - withdrawal - shop_payment` vs wallet balance; alert on mismatch; keep ledger append-only. |

---

## 4. Perspectives (brainstorm)

### 4.1 Technical

- **RPC vs explorer API:** Primary source of truth = own daemon RPC (balances, sends, `listtransactions`). Chainz = links + optional price/health. Avoid depending on Chainz for critical path (rate limit, availability).
- **Deposit matching:** Prefer **per-user deposit addresses** (one `getnewaddress` per user, store in DB/file). Avoid “one shared address + amount tagging” (fragile, bad UX).
- **Scanner:** One cron or background task that runs every 1–5 min: `listtransactions` (or block scan if needed), filter by our deposit addresses, for each new tx with ≥N confirmations and txid not in ledger → credit and append ledger. Use idempotency (txid) and locking.
- **Stack:** Keep `mn2_rpc_client.py` thin (HTTP JSON-RPC); put business logic in `mn2_wallet_service.py` (addresses, ledger, unified_points_db).

### 4.2 UX

- **Trust:** Show “View on explorer” for every tx and deposit address (Chainz links). Display confirmations for pending deposits.
- **Clarity:** One “Wallet” or “MN2” section: balance, deposit (address + QR), withdraw form, history with explorer links. Shop: show “Pay with MN2” and price in MN2 when balance is sufficient.
- **Errors:** Clear messages: “Insufficient balance”, “Invalid address”, “Network fee: X MN2”, “Allow up to 6 confirmations for deposits”.

### 4.3 Security

- **Secrets:** No RPC credentials in repo; env only; optional secrets manager in production.
- **Withdrawals:** Validate address format (and RPC `validateaddress` if available); max amount and rate limits; log all withdrawals with user_id, address, amount, txid.
- **Deposits:** Credit only after N confirmations; never trust 0-conf for balance credit.

### 4.4 Ops

- **Health:** Health check = RPC `getblockcount` (and optionally Chainz `getblockcount` as fallback). Alert if daemon down or out of sync.
- **Backup:** Backup `wallet.dat` and ledger store; document restore procedure.
- **Monitoring:** Log deposit/withdrawal events; metric for “pending deposits” (unconfirmed txs to our addresses).

### 4.5 Product

- **MVP:** Custodial in-app MN2 balance + deposit + withdraw + shop payment. No external “pay with MN2 at checkout” (non-custodial) in v1.
- **Later:** Optional external price feed (Chainz `ticker.usd` or other) for “live” MN2 price; optional “Pay with MN2” at checkout by sending to a merchant address (Option A in original plan).

### 4.6 Compliance / Legal

- **Disclaimer:** Show standard crypto disclaimers (volatility, not financial advice, finality of transactions). Link to Terms/ToS.
- **KYC/AML:** Defer unless required by jurisdiction or volume; document “we may introduce limits or KYC later” in ToS if needed.

---

## 5. Monetization

How MN2 fits into site revenue and product strategy:

| Lever | Description | Notes |
|-------|-------------|--------|
| **Shop payment in MN2** | Users spend MN2 on items (themes, boosters, game time, etc.). Site receives value in MN2; can hold, convert, or use for rewards. | Primary integration; same flow as coins, different currency. |
| **Optional spread/fee** | Small margin on “MN2 → in-app coins” ). Withdrawal *network* fee is separate, user-paid (§2 Fees). | Config-driven; document in ToS. |
| **MN2 as top-up** | Users deposit MN2 to get “coins” or direct MN2 balance; increases engagement and retention. | Complements PayPal coin packs. |
| **Branding** | “Pay with MasterNoder2” differentiates the site and aligns with the coin community (masternode holders). | Marketing and trust. |
| **Future: rewards / staking** | Optional: reward users in MN2 for activity; or promote MN2 staking/masternode info. | Defer to post-MVP. |

**Recommendation:** Ship Phase 5 (shop with MN2) with config-driven MN2 price; track MN2 volume and conversion. Add explicit “MN2 monetization” metrics later (e.g. MN2 received, MN2 spent in shop, withdrawal volume).

---

## 6. Profiling and observability

What to profile and where to expose it, so the integration is observable and debuggable:

| Area | What to profile | Where | When (phase) |
|------|-----------------|--------|--------------|
| **RPC calls** | Latency per call (`getbalance`, `getnewaddress`, `sendtoaddress`, `listtransactions`, `getblockcount`); success/failure. | Log in `mn2_rpc_client`: e.g. `logs/mn2_rpc.jsonl` or structured logger; optional `duration_ms`, `method`, `ok`. | 1 |
| **Health check** | MN2 RPC health (reachable, block height); optional Chainz fallback latency. | `GET /api/health/system`: add component `mn2_rpc` with `status`, `block_height`, `latency_ms`. | 1 |
| **Deposit scanner** | Run duration; txs processed; credits applied; errors (e.g. RPC timeout). | Background task log or `logs/mn2_deposit_scanner.jsonl`; one line per run: `start`, `end`, `duration_s`, `txs_checked`, `credits_applied`, `error`. | 3 |
| **Withdrawal** | Time from request to `sendtoaddress` success; amount; txid. | Ledger already records; add optional `withdrawal_duration_ms` in log or ledger metadata for support. | 4 |
| **Balance/address APIs** | Response time for `GET /api/mn2/balance`, `GET /api/mn2/deposit-address`. | Application logs or lightweight metrics; alert if p99 > threshold. | 2 |
| **Errors** | Count of RPC errors, invalid addresses, insufficient balance, double-credit attempts. | Existing `error_logging` or dedicated `logs/mn2_errors.json`; use for reconciliation and alerts. | 1+ |

**Concrete additions:**

- **Phase 1:** In `mn2_rpc_client.py`, wrap each RPC call with timing; log method, duration_ms, and success/failure. Add optional `MN2_PROFILE_LOG=1` or log path in env. Expose MN2 in `/api/health/system`: try `getblockcount`, set `mn2_rpc: { status, block_height?, latency_ms?, error? }`; do not fail overall health if MN2 is down (degraded only).
- **Phase 3:** Deposit scanner writes a single structured log line per run (or appends to a small rotating file).
- **Later:** Optional dashboard or admin endpoint that aggregates last N scanner runs and last N RPC call latencies.

---

## 7. Integration of Chainz into implementation phases

| Phase | Addition |
|-------|----------|
| **1** | Health: optional `getblockcount` from Chainz as fallback if RPC fails. |
| **2** | None (addresses from own RPC). |
| **3** | Ledger stores `txid`; all tx links in API responses use `https://chainz.cryptoid.info/mn2/tx.dws?txid=...`. |
| **4** | Withdrawal success response includes `explorer_tx_url` (same base + txid). |
| **5** | Optional: Chainz `ticker.usd` (cached) for “Price: X USD per MN2” and “Item: Y MN2”. |
| **6** | UI: “View on explorer” for address and every tx; optional “MN2 price” from Chainz if implemented. |

---

## 8. Prerequisites and what's needed to complete integration

Priority: **Phase 1 first**. Below: (A) Phase 1 scope and dependencies, (B) full-integration checklist.

### 8.1 Phase 1 scope (do first)

| # | Item | Owner / location | Done? |
|---|------|------------------|--------|
| 1 | **MN2 daemon** | Ops / server | Run `masternoder2d` **on the deployment server** (same host as the backend). RPC enabled; confirm port and credentials. Prefer testnet for dev. See docs/MN2_DAEMON_SETUP.md. |
| 2 | **Env vars** | `.env` (and `.env.example`) | `MN2_RPC_URL`, `MN2_RPC_USER`, `MN2_RPC_PASSWORD`, optional `MN2_NETWORK`, optional `MN2_PROFILE_LOG=1`. |
| 3 | **Config file** | `data/mn2_config.json` (or env-only) | `ticker`, `decimals`, optional `confirmations`, `withdrawal_fee`, `explorer_base_url`. Default RPC port: confirm in MasterNoder2 repo (e.g. contrib/share). |
| 4 | **RPC client** | `backend/services/mn2_rpc_client.py` | HTTP JSON-RPC to `MN2_RPC_URL`; time and log calls when profiling enabled. |
| 5 | **Health** | `backend/routes/health_routes.py` | In `system_health()`, add component `mn2_rpc`: getblockcount, status, block_height, latency_ms; degraded if unreachable. |
| 6 | **Profiling** | `mn2_rpc_client.py` + logs | Log each RPC call (method, duration_ms, ok) to `logs/mn2_rpc.jsonl` when enabled. |

*Phase 1 "Done?" column: use for implementation tracking; leave unchecked until each item is in place.*

Phase 1 deliverable: RPC client works, health check reports MN2 RPC status, profiling captures RPC latency.

### 8.1.1 Next steps (after daemon is responding)

Phase 1 is complete when the daemon runs on the server and `/api/health/system` shows `mn2_rpc.status: "healthy"`. Then:

| Phase | What to do | Key deliverables |
|-------|------------|------------------|
| **2** | Balances + addresses | Add `mn2_balance` to unified points and `get_all_points()`. Create `mn2_wallet_service.py`: get_or_create_deposit_address (RPC `getnewaddress`), store user_id → address (e.g. `data/mn2_user_addresses.json`). Add `GET /api/mn2/balance`, `GET /api/mn2/deposit-address` (auth required). |
| **3** | Ledger + deposits | Append-only ledger (file or DB); deposit scanner (cron/background): `listtransactions`, match deposit addresses, credit after N confirmations, idempotency by txid. `GET /api/mn2/transactions`. Explorer links for tx/address. |
| **4** | Withdrawals | `POST /api/mn2/withdraw`: validate address (RPC), check balance, `sendtoaddress`, deduct `mn2_balance`, append ledger, return txid; rate limit. |
| **5** | Shop | MN2 price in config; extend shop_purchase for `payment_method: "mn2"`; deduct `mn2_balance`, ledger. |
| **6** | UI | Wallet block (profile or page): balance, deposit address + QR, withdraw form, transaction list; “Pay with MN2” in shop. |

Start with **Phase 2**: wallet service + per-user deposit address + API routes + `mn2_balance` in points.

### 8.2 Full integration checklist (all phases)

| Area | What's needed | Phase |
|------|----------------|-------|
| **Unified points** | Support **mn2_balance**; in `get_all_points()` include **mn2_balance** in `points` (top-level and systems). | 2 |
| **Per-user addresses** | Storage user_id to deposit_address; get_or_create_deposit_address via RPC getnewaddress. | 2 |
| **Ledger** | Append-only store; idempotency by txid for deposits. | 3 |
| **Deposit scanner** | Background job; single process + lock; profiling. | 3 |
| **Withdrawal** | Validate, send, deduct, ledger, explorer link; rate limit. | 4 |
| **Shop** | payment_method "mn2"; deduct mn2_balance, ledger. | 5 |
| **API routes** | GET balance, deposit-address, transactions; POST withdraw; auth. | 2–4 |
| **Explorer links** | Tx and address links to Chainz MN2. | 3–6 |
| **UI** | Wallet block and shop Pay with MN2. Deposit address + QR (generate QR server-side or via lib, e.g. segno/qrcode). Shop revenue address shown in MN2 Wallet (Shop + Profile) when set in config. | 6 |

### 8.3 Other things to complete integration

- **Unified points:** Add explicit `mn2_balance` in `get_all_points()` (top-level and systems).
- **Account resolution:** MN2 endpoints use same user resolution as shop.
- **Auth:** All `/api/mn2/*` require authenticated user.
- **Rate limiting:** Apply to POST withdraw.
- **Secrets:** Env or secrets manager only.
- **Testnet:** Set `MN2_NETWORK=testnet` in `.env` (or `MN2_RPC_URL=http://127.0.0.1:19332`); daemon uses `rpcport=19332` for testnet. See [MN2_OPS.md](MN2_OPS.md).
- **Documentation:** [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) (daemon), [MN2_OPS.md](MN2_OPS.md) (env, scanner, reconciliation).
- **Agent parity:** MN2 actions are exposed via the same REST API (GET balance, deposit-address, transactions; POST withdraw). See [AGENTS_MN2.md](AGENTS_MN2.md) for agent/automation use.
- **Phase 7 (optionals):** Min/max withdrawal in config; Chainz health fallback (getblockcount) and ticker.usd (cached); "Pay with MN2" badge on theme_premium and landing; withdrawal_duration_ms in ledger; admin GET /api/mn2/ops/stats; scripts/mn2_reconcile.py; MN2_SCAN_SECRET / MN2_OPS_SECRET for scan and ops. See [MN2_INTEGRATION_GAPS.md](MN2_INTEGRATION_GAPS.md).

### 8.4 Account identity vs MN2 address binding

**Question:** Should the site account be *bound* to an MN2 address (address = identity), or should user account control stay separate (session/auth) with MN2 only as a funding method?

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **A. Account bound to MN2 address** | Identity = one MN2 address. Login e.g. by “Sign in with MN2” (message signing to prove ownership), or account is permanently tied to the deposit address we assign. | Crypto-native; one address = one identity; aligns with masternode/MN2 community. | Key loss = account loss unless we add recovery; “login with MN2” requires wallet in browser or app; new users without MN2 can’t sign up. |
| **B. Account control separate (recommended)** | Account = existing session/auth (e.g. session, OAuth). MN2 is a *funding method*: we assign a deposit address per user (from our wallet); they can withdraw to any external address they enter. No “this account *is* this MN2 address.” | Works for users who don’t have MN2 yet; familiar login/recovery; one account, many devices; MN2 is additive. | MN2 is not the primary identity; “Pay with MasterNoder2” is payment, not login. |
| **C. Hybrid** | Keep B, but let user *optionally link* an external MN2 address (prove ownership by signing). Use for: default withdrawal address, or “Login with MN2” as 2FA or alternative login. | Best of both: normal signup + option to bind/link MN2 later. | More build: message-signing flow, link storage, optional login path. |

**Recommendation:** **B (account control separate)** for MVP. Keep existing user/session/auth; MN2 is “how you fund and pay,” not “who you are.” We still **assign** one deposit address per user (our custodial wallet), so deposits are correctly attributed; we do **not** require or store “your” external MN2 address as account identity. If later you want crypto-native login or “linked MN2 address” (e.g. default withdraw or sign-in with MN2), add **C** as an optional layer (link address + optional “Login with MN2”) without changing the core model.

### 8.5 Phase 8: Non-custodial pay at checkout

User can pay with MN2 **on-chain** without pre-depositing: at checkout they choose “Pay on-chain (MN2)”, receive a **unique address and amount**, send MN2 from their wallet; after N confirmations the scanner matches the payment to the order and fulfils it (inventory + ledger). Implemented via: `mn2_order_payment_service` (create order payment, getnewaddress per order, pending/expires), scanner extension (receive to order address → confirm + fulfil, do not credit user balance), API `POST /api/mn2/order-payment` and `GET /api/mn2/order-payment/status`, and shop UI “Pay on-chain” with QR + status poll.

### 8.6 Phase 9: Live price feed and withdrawal hardening

- **Price:** GET /api/mn2/price returns mn2_usd_price (Chainz ticker, cached), coins_per_mn2, last_updated_iso. Balance endpoint includes mn2_usd_price_updated_iso when available. Shop and wallet UI show approximate USD next to MN2 amounts when price is set.
- **Withdrawal caps:** In data/mn2_config.json, optional max_withdrawal_per_day (count) and max_withdrawal_amount_per_day (total MN2 per 24h per user). Withdraw route enforces both when set; ledger provides sum_withdrawals_since for amount cap.

### 8.7 Phase 10: Withdrawal verification gate (KYC placeholder)

- When withdrawal_requires_verification is true in mn2_config.json, only users in the verified list (data/mn2_verified_users.json) can withdraw. Withdraw returns 403 and code verification_required otherwise.
- Balance endpoint returns withdrawal_verified (true/false) when the gate is enabled so UI can show a message and disable the withdraw button for unverified users.
- Ops API: GET /api/mn2/ops/verified-users (list), POST /api/mn2/ops/verify-user (body: user_id, action=add|remove); both require MN2_OPS_SECRET or MN2_SCAN_SECRET when set. No full KYC flow; verified list is maintained manually or via ops API.

---

## 9. Synthesis and decisions

### 9.1 What we're building (recap)

- **MN2 as in-app currency:** Users deposit MN2 to a site-controlled address, see balance and history, pay in the shop with MN2, and withdraw to an external address. All driven by backend RPC + unified points (`mn2_balance`) and a single ledger.

### 9.2 Block explorer role

- **Chainz [MN2 explorer](https://chainz.cryptoid.info/mn2/)**: use for **links only** in MVP (tx, address). Optionally use **Chainz API** for ticker (price) and health fallback, with rate limit and caching. Do not use Chainz for critical balance or send logic.

### 9.3 Path

1. **Phases 1–4 (original plan):** RPC client → addresses + balance + ledger + deposits → withdrawals. Add **explorer URLs** wherever we show a txid or address.
2. **Phase 5:** Shop payment with MN2; price from config first, optional Chainz `ticker.usd` later.
3. **Phase 6:** Wallet UI (balance, deposit address + QR, withdraw, history) with "View on explorer" on every tx and address.
4. **Phase 7:** Optional enhancements (min/max withdrawal, Chainz fallback + ticker.usd, "Pay with MN2" badge on theme_premium and landing, withdrawal_duration_ms in ledger, admin ops/stats, reconciliation script, scan/ops secrets). See [MN2_INTEGRATION_GAPS.md](MN2_INTEGRATION_GAPS.md).
5. **Phase 8:** Non-custodial pay at checkout — user gets a unique address + amount and sends MN2 on-chain; scanner matches payment and fulfils order (see §8.5).
6. **Phase 9:** Live price feed and withdrawal hardening — GET /api/mn2/price (mn2_usd_price, last_updated_iso); balance returns mn2_usd_price_updated_iso; configurable max_withdrawal_per_day and max_withdrawal_amount_per_day; shop and wallet UI show "≈ X USD" when price available.
7. **Phase 10:** Withdrawal verification gate — config withdrawal_requires_verification; verified list in data/mn2_verified_users.json; withdraw returns 403 when not verified; balance returns withdrawal_verified; ops API to list/add/remove verified users; shop and profile UI show message and disable withdraw when unverified.

**Status:** Phases 1–10 complete.

### 9.4 Resolved choices

- **Custodial (Option B)** for MVP.
- **Account control separate from MN2:** User identity = existing session/auth; MN2 is a funding method. We assign one deposit address per user (our wallet); we do not bind account to a user-owned MN2 address for login. Optional “link MN2 address” or “Login with MN2” can be added later (see §8.4).
- **Per-user deposit addresses** (no shared-address tagging).
- **N confirmations (e.g. 6)** for crediting; no 0-conf.
- **Fee on user** for withdrawals; amount and method in config.
- **Ledger keyed by txid** to prevent double-credit; single scanner with lock.
- **Ticker/decimals:** MN2, 8 decimals until repo confirms.
- **Testnet** for dev/staging; mainnet only in production.

### 9.5 Outcome

With this expansion, the plan has: (1) a defined role for the existing [Chainz MN2 explorer](https://chainz.cryptoid.info/mn2/) and its API, (2) concrete solutions for open points and risks, (3) multiple perspectives to avoid blind spots, (4) **monetization** and **profiling** so revenue and observability are explicit, (5) **prerequisites and Phase 1–first checklist** so nothing blocks the first deliverable, and (6) a single synthesis that keeps the original phased implementation intact and adds explorer integration and optional price/health from Chainz.

---

## 10. References

- Original plan: [MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md](MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md)
- Shop and addresses: [MN2_SHOP_AND_ADDRESSES.md](MN2_SHOP_AND_ADDRESSES.md) (which address the shop uses; optional `shop_revenue_address`)
- Ops: [MN2_OPS.md](MN2_OPS.md) (daemon, env, scanner, reconciliation)
- Agent parity: [AGENTS_MN2.md](AGENTS_MN2.md) (MN2 API for automation and agents)
- Gaps and optional items: [MN2_INTEGRATION_GAPS.md](MN2_INTEGRATION_GAPS.md) (what’s missing vs plan; scan-deposits protection, optional features)
- MasterNoder2: [github.com/jonK341/MasterNoder2](https://github.com/jonK341/MasterNoder2)
- MN2 block explorer: [chainz.cryptoid.info/mn2/](https://chainz.cryptoid.info/mn2/)
- Chainz API: [chainz.cryptoid.info/api.dws](https://chainz.cryptoid.info/api.dws)
