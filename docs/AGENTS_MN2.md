# MN2 agent parity — API actions for automation

So that **agents and automation** can do the same MN2 flows as users in the UI, all MN2 actions are available over the same REST API. Use these with `user_id` (query or body) as the app does for session/user resolution.

**Base URL:** Your app root (e.g. `https://masternoder.dk` or `http://localhost:5000`). Paths also work under `/vidgenerator` if mounted there.

---

## 1. Get balance

**GET** `/api/mn2/balance?user_id=USER_ID`

Returns the user’s in-app MN2 balance and shop rate.

**Response (200):**
```json
{
  "success": true,
  "user_id": "USER_ID",
  "mn2_balance": 1.5,
  "coins_per_mn2": 100,
  "shop_revenue_address": "JNKz...",
  "shop_revenue_explorer_url": "https://...",
  "mn2_usd_price": 0.01234567
}
```
`mn2_usd_price` is optional (from Chainz ticker, cached); omit if unavailable.

---

## 2. Get deposit address

**GET** `/api/mn2/deposit-address?user_id=USER_ID`

Returns (or creates) the user’s MN2 deposit address and explorer link.

**Response (200):**
```json
{
  "success": true,
  "user_id": "USER_ID",
  "deposit_address": "MN2_ADDRESS",
  "explorer_address_url": "https://chainz.cryptoid.info/mn2/address.dws?addr=..."
}
```

---

## 3. List transactions

**GET** `/api/mn2/transactions?user_id=USER_ID&limit=50`

Returns ledger entries for the user (deposits, withdrawals, shop payments) with explorer links for txids.

**Response (200):**
```json
{
  "success": true,
  "user_id": "USER_ID",
  "transactions": [
    {
      "type": "deposit",
      "amount": 1.0,
      "txid": "...",
      "explorer_tx_url": "https://...",
      "created_at": "2026-03-18T12:00:00Z"
    }
  ]
}
```

---

## 4. Withdraw

**POST** `/api/mn2/withdraw`  
**Content-Type:** `application/json`

**Body:**
```json
{
  "user_id": "USER_ID",
  "address": "MN2_RECIPIENT_ADDRESS",
  "amount": 1.5
}
```

A network fee (e.g. 0.001 MN2) is deducted from the amount; the user receives `amount - fee`. Rate limit applies (e.g. max N withdrawals per user per 24h).

**Response (200):**
```json
{
  "success": true,
  "txid": "...",
  "explorer_tx_url": "https://...",
  "amount_sent": 1.499,
  "fee": 0.001
}
```

**Errors:** 400 (invalid address, insufficient balance), 429 (rate limit).

---

## 5. Run deposit scanner (ops)

**POST** `/api/mn2/scan-deposits`

Runs the deposit scanner once (credits incoming MN2 to users after confirmations). No body required. If `MN2_SCAN_SECRET` is set, send `X-Scanner-Token: <secret>` or `?token=<secret>`.

---

## 6. Create on-chain order payment (Phase 8)

**POST** `/api/mn2/order-payment`  
**Content-Type:** `application/json`

**Body:** `{ "user_id": "USER_ID", "item_id": "ITEM_ID", "quantity": 1 }`

Creates a unique address and amount for paying with MN2 on-chain (no pre-deposit). User sends the exact MN2 amount to the returned address; after N confirmations the scanner fulfils the order.

**Response (200):** `{ "success": true, "payment_ref": "...", "address": "MN2_ADDR", "amount_mn2": 0.5, "expires_at": "ISO", "item_id": "...", "quantity": 1, "explorer_address_url": "..." }`

**GET** `/api/mn2/order-payment/status?payment_ref=REF`

Returns `{ "success": true, "status": "pending"|"confirmed"|"fulfilled"|"expired", "address", "amount_mn2", "txid", "explorer_tx_url", ... }`. Poll until `status === "fulfilled"`.

---

## 7. Get MN2 price (Phase 9)

**GET** `/api/mn2/price`

Returns current MN2/USD price (Chainz, cached) and coins_per_mn2. No auth required.

**Response (200):** `{ "success": true, "mn2_usd_price": 0.01234, "last_updated_iso": "2026-03-18T12:00:00Z", "coins_per_mn2": 100 }` (mn2_usd_price and last_updated_iso omitted if unavailable)

---

## 8. Withdrawal verification (Phase 10)

When the app is configured with withdrawal_requires_verification (mn2_config.json), GET /api/mn2/balance returns **withdrawal_verified**: true or false. If false, POST /api/mn2/withdraw returns 403 with error "Withdrawal requires account verification" and code "verification_required". Ops can manage the verified list: GET /api/mn2/ops/verified-users (list user_ids), POST /api/mn2/ops/verify-user with body { "user_id": "USER_ID", "action": "add" | "remove" } (requires ops token).

---

## 9. Ops stats (admin)

**GET** `/api/mn2/ops/stats`

Returns last scanner runs and RPC call summary (from logs). If `MN2_OPS_SECRET` or `MN2_SCAN_SECRET` is set, send `X-Ops-Token` or `X-Scanner-Token` or `?token=`.

**Response (200):** `{ "success": true, "scanner_runs": [...], "rpc_calls_summary": { "last_100_ok": N, "last_100_total": N } }`

---

## 10. Staking (parity layer)

All staking actions a user takes in the wallet UI are plain HTTP with `user_id`, so any agent has parity. Consent (terms) must be recorded **before** the first `stake`.

| Action | Method | Path | Notes |
|--------|--------|------|-------|
| Status | GET | `/api/mn2/staking/status?user_id=...` | Balance, staked, APR, longevity tier, multipliers, rig/uptime, terms |
| Accept terms | POST | `/api/mn2/staking/accept-terms` | `{user_id, version?}` — required before staking |
| Stake | POST | `/api/mn2/staking/stake` | `{user_id, amount}` — moves balance → pool (min/max + consent) |
| Unstake | POST | `/api/mn2/staking/unstake` | `{user_id, amount}` — instant, internal move |
| Auto-compound | POST | `/api/mn2/staking/auto-compound` | `{user_id, enabled}` |
| Rig heartbeat | POST | `/api/mn2/staking/work` | `{user_id, proof?, nonce?}` — participation/uptime signal |
| Calculator | GET | `/api/mn2/staking/calculator?amount=&days=&uptime=&boost=` | Projection, no side effects |
| Rewards table | GET | `/api/mn2/staking/rewards-table?user_id=...&format=csv?` | Per-interval history (+ CSV) |
| Monitor | GET | `/api/mn2/staking/monitor?limit=...` | Anonymized pool processes + aggregates (incl. `agent_staked_mn2`, `agent_actions_24h`) |
| Network overview | GET | `/api/mn2/network-overview` | Explorer + pool + on-ramp + P2P stats (public) |
| On-ramp (Model A) | POST | `/api/mn2/onramp/{quote,order,capture}` | PayPal→MN2, KYC caps + hold window |
| P2P (Model B) | GET/POST | `/api/mn2/p2p/{listings,buy,...}` | Seller escrow + buyer hold; KYC-gated |

---

## 11. Staking automation layer (secret-gated)

For headless / cron / LLM personas acting **on behalf of** users, separate from the parity layer.

- **Auth:** `AGENT_MN2_STAKING_SECRET` (falls back to `AGENT_MN2_SHOP_SECRET`), header `X-Agent-Staking-Key`. Read-only verbs (`status`, `calculator`, `rewards_table`, `monitor`, `onramp_status`, `p2p_listings`, `p2p_status`) work without it.
- **Discover:** `GET /api/agent/staking/capabilities` → machine-readable verb manifest + config.
- **Execute:** `POST /api/agent/staking/execute` → `{ action, user_id, params... }`. Verbs include `accept_terms`, `stake`, `unstake`, `set_auto_compound`, `heartbeat`, `onramp_*`, `p2p_*`.
- **Personas + autonomous loop:** `data/agent_staking_agents.json` binds `agent_id → user_id` + policy (`target_staked`, `max_staked`, `keep_balance_min`, `auto_compound`, `heartbeat`, `rebalance_step_max`, `auto_accept_terms`, `allowed_actions`).
  - `upsert_agent` `{agent_id, user_id, policy}` — create/update a persona.
  - `run_agent` `{agent_id, dry_run?}` — one policy step (consent-gate → heartbeat → align auto-compound → rebalance toward target within caps).
  - `run_all` `{dry_run?}` — step every enabled persona.
- **Cron entry point:** `POST /api/agent/staking/ops/run-all` (ops-token gated via `MN2_OPS_SECRET`) — driven hourly by `cron/mn2_accrue_rewards.sh`.
- **Governance:** consent required before agent `stake`/`onramp_order` (`consent_required`); kill switch `agent.automation_enabled: false` in `mn2_staking_config.json` disables the loop without affecting the user parity layer; every step is audited to `mn2_staking_agent_activity.jsonl` and counted in the monitor (`agent_managed`, `agent_staked_mn2`, `agent_actions_24h`).

---

## Agent parity summary

| Action | Method | Path | Purpose |
|--------|--------|------|--------|
| Get balance | GET | `/api/mn2/balance?user_id=...` | In-app MN2 balance + shop rate |
| Get deposit address | GET | `/api/mn2/deposit-address?user_id=...` | User’s MN2 receive address |
| List transactions | GET | `/api/mn2/transactions?user_id=...` | Ledger history with explorer links |
| Withdraw | POST | `/api/mn2/withdraw` | Send MN2 to an external address |
| Scan deposits | POST | `/api/mn2/scan-deposits` | Ops: run scanner once |
| Ops stats | GET | `/api/mn2/ops/stats` | Ops: last scanner runs + RPC summary (token if MN2_OPS_SECRET set) |
| Create on-chain payment | POST | `/api/mn2/order-payment` | Phase 8: get address + amount for shop item; user sends MN2 on-chain |
| Order payment status | GET | `/api/mn2/order-payment/status?payment_ref=...` | Poll until fulfilled |
| Get price | GET | `/api/mn2/price` | Phase 9: MN2/USD + last_updated (no auth) |
| List verified users | GET | `/api/mn2/ops/verified-users` | Phase 10: ops only (token) |
| Add/remove verified | POST | `/api/mn2/ops/verify-user` | Phase 10: body user_id, action=add\|remove (token) |

Any client that can send HTTP requests (scripts, MCP tools, Cursor agents, etc.) can perform the same MN2 flows as the Shop and Profile UI by calling these endpoints with the appropriate `user_id`.
