# MasterNoder2 (MN2) crypto integration plan

Use **MasterNoder2** coins as currency on Masternoder.dk: wallets, balances, transactions, and shop payment. Source: [github.com/jonK341/MasterNoder2](https://github.com/jonK341/MasterNoder2).

---

## 1. MasterNoder2 overview (from source)

- **What it is:** Full-node cryptocurrency (C++), SHA256CSM algorithm, PoW + staking, 330+ masternodes. Coins are “MN2” / MasterNoder.
- **Interaction:** JSON-RPC over HTTP (Bitcoin/Dash-style). Daemon: `masternoder2d` (or similar), CLI: `masternoder2-cli`.
- **Relevant repo layout:**
  - `src/rpc/` — RPC server, blockchain, rawtransaction, masternode, mining, misc
  - `src/wallet/` — wallet logic
  - `src/httprpc.cpp` — HTTP RPC transport
- **Typical RPC commands** (infer from Bitcoin/Dash; confirm in `src/rpc/server.cpp`, `src/rpc/misc.cpp`, wallet RPCs):
  - `getbalance` — wallet balance
  - `getnewaddress` — new receive address
  - `sendtoaddress <address> <amount>` — send MN2
  - `listtransactions` — history
  - `gettransaction <txid>` — tx details
  - `getblockcount` / `getblockhash` — chain sync
- **Network:** Mainnet (and possibly testnet). Default RPC port and credentials are in the daemon config (e.g. `masternoder2.conf`); confirm in repo `contrib/` or `share/` if present.

---

## 2. Current Masternoder.dk currency model

- **Unified points:** `backend/services/unified_points_database.py` — file-backed + optional DB; `get_all_points(user_id)` returns e.g. `coins`, `game_points`, `level`, `systems`, etc.
- **Shop:** `backend/routes/shop_routes.py` — `get_shop_currency` uses `coins`; `shop_purchase` deducts `coins` (or other point types) via `unified_points_db.add_points(..., amount=-cost)`.
- **Other:** PayPal buys “coin packs” that credit in-app `coins`; no blockchain today.

---

## 3. Integration options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. MN2 as second currency (on-chain only)** | User pays by sending MN2 to a site deposit address; backend watches chain and credits “mn2_balance” or “coins” when tx confirms. | Non-custodial, no hot wallet. | Confirmations delay; need address per user or per-deposit; more chain logic. |
| **B. Custodial in-app MN2** | Backend runs a wallet (or connects to MN2 RPC); each user has an internal “MN2 balance”; deposits = incoming tx → credit; spend = backend sends MN2 out. | Instant balance and spend; simple UX. | Custody risk; RPC/wallet ops and security. |
| **C. Hybrid** | User links external MN2 address; “balance” = RPC balance of that address (read-only) or we credit only after confirmed deposit to a deposit address we control. | Flexible. | Read-only: can’t “spend” from user’s wallet from the site; or same as A if we use deposit addresses. |

**Recommendation:** Start with **B (custodial)** for MVP: one backend wallet, user “MN2 balance” stored in unified points (e.g. `mn2_balance`). Deposits by sending to a single deposit address (or per-user sub-address if the chain supports it); backend wallet or RPC sends payouts. Later add **A** (direct on-chain payment to merchant address) for optional “pay with MN2” at checkout without pre-deposit.

---

## 4. Wallets

### 4.1 Backend wallet (custodial)

- **Where:** Dedicated server or secure process running MasterNoder2 daemon with wallet enabled, or a single wallet instance used only for site operations.
- **Source:** Build from [MasterNoder2](https://github.com/jonK341/MasterNoder2) (see `INSTALL`, `doc/`); run `masternoder2d` with `-server -rpcuser=... -rpcpassword=...` (or config file). Use only for:
  - One or more **deposit addresses** (e.g. `getnewaddress` per user or one shared).
  - **Sending** MN2 (withdrawals, rewards, or internal moves).
- **Security:** RPC over localhost or VPN only; strong `rpcpassword`; optional `rpcallowip`; backup wallet.dat; consider multi-sig or cold storage for large balances.

### 4.2 User “wallet” on the page

- **In-app balance:** Stored in unified points as `mn2_balance` (or keep using `coins` and treat MN2 as one way to “buy coins”). No private keys on the site.
- **Deposit:** User is shown a **deposit address** (and optional QR). That address is either:
  - A **per-user address** (backend calls RPC `getnewaddress` once per user, stores in `data/mn2_user_addresses.json` or DB), or
  - A **shared address** with **memo/comment** (if supported) or **unique amount** to identify the user (not ideal).
- **Withdrawal:** User requests payout to their external MN2 address; backend checks balance, sends via RPC `sendtoaddress`, then deducts `mn2_balance` and records the tx.

### 4.3 Data model (minimal)

- **File or DB:** e.g. `data/mn2_wallet_config.json`:
  - `deposit_address` (if single) or `rpc_url`, `rpc_user`, `rpc_password` (or env vars).
- **Per user:** `data/mn2_user_addresses.json` or a table:
  - `user_id` → `deposit_address` (and optionally `last_credited_block` or `last_txid`).
- **Ledger (recommended):** Append-only log of deposits/withdrawals: `user_id`, `type` (deposit|withdrawal|shop_payment|reward), `amount`, `txid` (if any), `created_at`, `metadata` (e.g. item_id). Used for support and reconciliation.

---

## 5. Transactions

### 5.1 Deposit (external MN2 → in-app balance)

1. User gets deposit address (from backend).
2. User sends MN2 from their own wallet to that address.
3. Backend **scans** for incoming payments:
   - Either **wallet RPC** `listtransactions` (with filter by address if available) or
   - **Block/chain scan** (getblock, decode tx, match output address).
4. On N confirmations (e.g. 6), backend:
   - Credits `mn2_balance` in unified points (or `unified_points_db.add_points(user_id, 'mn2_balance', amount, source='mn2_deposit', metadata={txid, ...})`).
   - Appends to ledger.
   - Optionally notifies user (email/in-app).

### 5.2 Withdrawal (in-app balance → external address)

1. User submits external MN2 address and amount.
2. Backend validates address (RPC `validateaddress` if available).
3. Check `mn2_balance >= amount + fee`.
4. RPC `sendtoaddress <address> <amount>`.
5. On success: deduct balance, append ledger with txid, return txid to user.

### 5.3 Shop payment (MN2)

1. At checkout, user can choose “Pay with MN2” (in addition to coins/PayPal).
2. Backend converts item price to MN2 (fixed rate or external price feed — see 7.1).
3. If `mn2_balance >= price_mn2`: deduct `mn2_balance`, apply purchase (same as current `shop_purchase`), append ledger (type `shop_payment`).
4. If not enough balance: show “Deposit MN2” or “Pay with coins/PayPal”.

---

## 6. API and backend services

### 6.1 MN2 RPC client (Python)

- **New module:** e.g. `backend/services/mn2_rpc_client.py`.
- **Actions:** HTTP JSON-RPC to `http://127.0.0.1:PORT/` (or env `MN2_RPC_URL`). Methods:
  - `getbalance()`, `getnewaddress()`, `sendtoaddress(addr, amount)`, `listtransactions(count, skip)`, `gettransaction(txid)`, `getblockcount()`, `validateaddress(addr)` (if present in MasterNoder2).
- **Reference:** Implementations in MasterNoder2 are in `src/rpc/`; exact method names may differ — check `src/rpc/server.cpp` / `src/rpc/misc.cpp` and wallet RPC registration.

### 6.2 MN2 wallet service (app layer)

- **New module:** e.g. `backend/services/mn2_wallet_service.py`.
- **Responsibilities:**
  - Get or create deposit address for `user_id`.
  - Credit/deduct `mn2_balance` (via unified_points_db).
  - Record ledger entries.
  - Call MN2 RPC for sends and (if needed) for scanning incoming txs.

### 6.3 New/updated HTTP endpoints

- `GET /api/mn2/balance` — current user’s MN2 balance (from unified points).
- `GET /api/mn2/deposit-address` — deposit address for current user.
- `POST /api/mn2/withdraw` — body: `{ "address": "...", "amount": 1.5 }`; returns txid or error.
- `GET /api/mn2/transactions` — list ledger for current user (and optionally txids for chain explorer).
- **Shop:** Extend `shop_purchase` to accept `payment_method: "mn2"` and use `mn2_balance` and MN2 price (see 7.1).

---

## 7. Pricing and display

### 7.1 MN2 price for shop

- **Option A:** Fixed rate in config, e.g. 1 MN2 = X in-app coins or 1 MN2 = Y USD (for display).
- **Option B:** External price feed (e.g. Coingecko/CMC API for “MasterNoder” or ticker); cache and use for “price in MN2” at checkout.
- **Recommendation:** Config-driven rate first; add feed later. Store in e.g. `data/mn2_config.json`: `coin_per_mn2` or `usd_per_mn2`.

### 7.2 UI (page)

- **Profile or “Wallet”:** Show MN2 balance, deposit address (+ QR), “Withdraw” form, last transactions.
- **Shop:** Show item price in “coins” and “MN2” (if enabled); “Pay with MN2” at checkout when balance sufficient.
- **Theme_premium / landing:** Optional “Pay with MasterNoder2” badge and link to wallet/deposit.

---

## 8. Security and ops

- **RPC:** Never expose daemon RPC to the internet; backend only, localhost or internal network.
- **Secrets:** RPC user/password in env (e.g. `MN2_RPC_USER`, `MN2_RPC_PASSWORD`, `MN2_RPC_URL`).
- **Withdrawals:** Rate limit per user; optional min/max amount and KYC if needed later.
- **Deposit scanning:** Run as cron or background task; lock to avoid double-credit (e.g. by txid in ledger).
- **Reconciliation:** Periodically compare ledger sum vs wallet balance and investigate discrepancies.

---

## 9. Implementation order (phases)

| Phase | Scope | Deliverables |
|-------|--------|---------------|
| **1** | RPC + config | `mn2_rpc_client.py`, env/config for RPC URL and credentials; health check (e.g. `getblockcount`). |
| **2** | Balances + addresses | `mn2_wallet_service.py`; per-user deposit address storage; `GET /api/mn2/balance`, `GET /api/mn2/deposit-address`. |
| **3** | Ledger + deposits | Ledger storage (file or DB); deposit scanner (RPC or block scan); credit `mn2_balance` and ledger; `GET /api/mn2/transactions`. |
| **4** | Withdrawals | `POST /api/mn2/withdraw`; validation, send via RPC, deduct balance, ledger. |
| **5** | Shop | MN2 price config; extend `shop_purchase` for `payment_method: "mn2"`; UI: “Pay with MN2” and balance in shop. |
| **6** | UI | Wallet block on profile (or dedicated page): balance, deposit address + QR, withdraw form, transaction list. |

---

## 10. Block explorer and expanded plan

- **Public block explorer:** [Chainz CryptoID — MasterNoder2](https://chainz.cryptoid.info/mn2/) (blocks, rich list, addresses, transactions). Use for user-facing “View on explorer” links (tx, address).
- **Expanded plan:** For block explorer API usage, solutions to open points, multiple perspectives (technical, UX, security, ops, product), and a synthesis, see **[MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md)**.

---

## 11. MasterNoder2 source references

- Repo: [github.com/jonK341/MasterNoder2](https://github.com/jonK341/MasterNoder2)
- RPC: `src/rpc/server.cpp`, `src/rpc/misc.cpp`, `src/rpc/rawtransaction.cpp`; wallet RPCs in `src/wallet/` (or under `src/rpc/`).
- Build/run: `INSTALL`, `configure.ac`, `Makefile.am`; default ports and config in `contrib/` or `share/` if present.
- Confirm exact RPC method names and parameters (e.g. `getbalance`, `sendtoaddress`) in the repo before coding the Python RPC client.

---

## 12. Open points

- **Ticker/symbol:** Confirm official ticker (e.g. MN2) and decimal places (e.g. 8) from MasterNoder2 docs or chain params.
- **Testnet:** Prefer testnet for development; mainnet only after testing.
- **InstantSend:** If MasterNoder2 supports InstantSend, consider accepting 0-conf for small amounts (optional, higher risk).
- **Fees:** Deduct network fee from user on withdraw or absorb; document policy.

---

## 13. Conclusions

- **Feasibility:** Using MasterNoder2 as an on-page currency is feasible. The chain exposes standard Bitcoin-style JSON-RPC; the app already has a unified points store and a shop that deducts balances. Adding an MN2 balance and deposit/withdraw/shop flows is a bounded backend and UI task.
- **Recommended path:** Start with a custodial in-app MN2 balance (Phase 1–4), then add shop payment (Phase 5) and wallet UI (Phase 6). Defer on-chain-only (non-custodial) payment at checkout until the custodial flow is stable.
- **Risk:** Custody and RPC security are the main risks. Mitigate with strict RPC access (localhost/internal only), env-based credentials, rate limits on withdrawals, and a clear ledger for reconciliation.
- **Scope control:** Keep the first release minimal: one deposit address per user (or one shared address with a deposit scanner), fixed or config-driven MN2 price for the shop, and no external price feed until the core flow works.
- **Outcome:** Once implemented, users can fund their account with MN2, see balance and history on the page, pay for shop items with MN2, and withdraw to an external address. The plan is enough to implement MN2 as a currency on the page using the MasterNoder2 daemon RPC and the existing unified points and shop flow.
