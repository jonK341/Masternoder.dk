# Cross-Venue Arbitrage — Plan

Connect MasterNoder Exchange to major external venues (Binance, Coinbase, NonKYC.io, …),
scan price differences, and let agents trade the spread into profit, stashing earnings
in per-agent accounts and (optionally) external wallets — with all sensitive credentials
kept in one encrypted vault.

> **Status:** Phase 1 shipped (read-only market data + paper arbitrage agents).
> Live trading and real custody are **disabled by default** and gated behind explicit
> config + secrets. See "Go-live gates" below.

---

## Reality check (read before going live)

These are real constraints, not blockers to the build — but they decide what is legal/profitable:

1. **Regulation (EU/DK).** Operating an exchange + routing customer-implicating funds across
   venues likely needs a **MiCA CASP** authorization. The current product is "custodial
   simulated trading for platform credits." Keep arbitrage **on the platform's own treasury
   funds**, not pooled customer funds, until licensed.
2. **Real arbitrage needs pre-funded capital on each venue.** You cannot "buy on A, sell on B"
   atomically unless you already hold the asset on B and quote on A. Cross-venue transfers are
   slow (minutes) and cost network + withdrawal fees that usually erase retail spreads.
3. **Latency.** A Flask box cannot beat HFT firms on the headline spreads. The realistic edge is
   **slow stat-arb / rebalancing / funding-rate / triangular** on mid-cap pairs, not BTC top-of-book.
4. **Security.** Trade-enabled API keys and wallet seeds are the highest-value secret in the system.
   They must be **encrypted at rest**, **never in `.env` plaintext**, **IP-allowlisted**, and
   **withdrawal scope disabled** on the venue side.

The build below is structured so Phase 1 is **safe and useful immediately** (live market data,
margin scanning, paper P&L), and live trading is a deliberate, auditable switch.

---

## Architecture

```
                ┌─────────────────────────────────────────────┐
                │            MasterNoder Exchange             │
                │  internal order book + custodial wallets    │
                └───────────────┬─────────────────────────────┘
                                │ internal price (USD)
   public REST tickers         ▼
 ┌──────────┐  ┌──────────────────────────────┐   ┌───────────────────────────┐
 │ 10 venue │→ │ external_exchange_connector   │ → │ exchange_arbitrage_service │
 │ adapters │  │  normalize {bid,ask,last}     │   │  margin scan + rank        │
 └──────────┘  └──────────────────────────────┘   │  paper-trade simulation    │
                                                   │  agent profit accounts     │
                                                   └─────────────┬─────────────┘
                                                                 │ audit (hash chain)
   ┌────────────────────────────┐                               ▼
   │ exchange_secrets_vault      │  ← API keys / seeds (Fernet)  audit_log.jsonl
   │ + wallet registry (public)  │  ← deposit addresses
   └────────────────────────────┘
```

### Components (Phase 1 = shipped)

| Component | File | Mode |
| --- | --- | --- |
| Connector config (10 venues) | `data/exchange_connectors_config.json` | read-only |
| Connector service | `backend/services/external_exchange_connector_service.py` | read-only public tickers |
| Margin scanner + paper agents | `backend/services/exchange_arbitrage_service.py` | paper |
| Secrets vault + wallet registry | `backend/services/exchange_secrets_vault_service.py` | encrypted (Fernet) |
| API routes (`/api/exchange/arbitrage/*`) | `backend/routes/crypto_exchange_routes.py` | admin-gated |
| Daemon | `scripts/exchange_arbitrage_daemon.py` | paper loop |
| **AI multi-venue trader** | `backend/services/exchange_ai_trading_service.py` | analyze + paper/live execute |
| **Signed venue API client** | `backend/services/exchange_venue_api_service.py` | Binance/OKX/Bybit/NonKYC/KuCoin live; others paper stub |
| AI + venue config | `data/exchange_ai_trading_config.json`, `data/exchange_venue_api_config.json` | config |
| AI APIs (`/api/exchange/ai-trading/*`) | `backend/routes/crypto_exchange_routes.py` | analyze public; run/probe admin |

---

## The 10 connections

All Phase-1 calls hit **public** market-data endpoints (no keys, no account access):

| # | Venue | Public ticker | Notes |
| - | ----- | ------------- | ----- |
| 1 | Binance | `api.binance.com/api/v3/ticker/bookTicker` | deepest liquidity, USDT pairs |
| 2 | Coinbase | `api.exchange.coinbase.com/products/{p}/ticker` | USD pairs, strong fiat rails |
| 3 | NonKYC.io | `api.nonkyc.io/api/v2/ticker/{pair}` | USDT pairs (`BTC_USDT`); privacy-focused; **recommended 2nd live venue** |
| 4 | KuCoin | `api.kucoin.com/api/v1/market/orderbook/level1` | wide mid-cap listing |
| 5 | OKX | `okx.com/api/v5/market/ticker` | USDT pairs, derivatives too |
| 6 | Bybit | `api.bybit.com/v5/market/tickers` | spot + perp funding edge |
| 7 | Bitfinex | `api-pub.bitfinex.com/v2/ticker/{p}` | USD pairs, lending/funding |
| 8 | Gate.io | `api.gateio.ws/api/v4/spot/tickers` | long-tail listings |
| 9 | Bitstamp | `bitstamp.net/api/v2/ticker/{p}` | EUR/USD, EU-friendly |
| 10 | Crypto.com | `api.crypto.com/v2/public/get-ticker` | retail + card on-ramp |

Each venue entry carries: enabled flag, mode, taker fee (bps), withdrawal fee notes, and the
internal→venue symbol mapping.

---

## Profit strategies (cross-trading ideas)

1. **Spatial arbitrage** — buy lowest-ask venue, sell highest-bid venue (needs pre-funding both sides).
2. **Internal vs external** — when the MasterNoder internal price drifts from the global mid,
   agents rebalance toward the external mid (keeps internal prices honest + captures spread).
3. **Triangular** — within one venue, A→B→C→A loops when cross rates misalign.
4. **Funding-rate carry** — long spot / short perp (or vice-versa) to collect funding (Bybit/OKX).
5. **Stablecoin peg** — USDT/USDC/DAI deviations from $1.
6. **Maker rebate harvesting** — post-only liquidity on rebate venues.
7. **Latency-tiered TWAP** — split large internal fills across venues to reduce slippage.
8. **Withdrawal-aware routing** — only act when spread > taker fees + transfer + network cost.
9. **Inventory bands** — keep target inventory per asset per venue; trade back to band.
10. **Volatility breakout** — widen quotes / pause agents when spread volatility spikes (risk off).

The scanner currently implements #1 and #2 in paper mode; others are config hooks for later phases.

---

## Profit custody (agent accounts + external wallets)

- Each agent has a **profit account**: `data/crypto_exchange/agent_accounts/<agent>.json`
  tracking realized paper P&L, per-venue notional, trade count, and last action.
- **Wallet registry** (public deposit addresses, labels, venue) lives in the vault module's
  plaintext registry — addresses are not secret.
- **Secrets** (API key/secret, withdrawal whitelist, seeds) live **only** in the encrypted
  vault (`secrets_vault.enc`, Fernet). One file, one place, encrypted at rest.
- Sweep policy (future): when an agent's realized profit crosses a threshold, sweep to the
  configured external wallet for that agent (manual approval first).

---

## Security model

- Vault key from `EXCHANGE_VAULT_KEY` (Fernet key) — never committed, server-only.
- API keys stored **trade-only, no-withdrawal**, IP-allowlisted on the venue.
- All agent actions, scans, and credential reads write to the **hash-chained audit log**.
- Admin endpoints require `EXCHANGE_ADMIN_KEY` (or `COGS_ADMIN_REPORT_KEY`).
- Live trading requires BOTH `EXCHANGE_ARBITRAGE_LIVE=1` AND a per-venue live key present in the vault.

## Go-live gates (must all be true to trade real funds)

1. `EXCHANGE_ARBITRAGE_LIVE=1` set on the server.
2. Per-venue API key + secret present in the encrypted vault.
3. Venue key scoped trade-only, withdrawals disabled, IP allowlisted.
4. Treasury-funded balances on each venue (no pooled customer funds).
5. Legal sign-off on MiCA posture for the activity.

Until then everything runs in **paper** mode: real prices in, simulated fills, tracked P&L.

---

## NonKYC.io API keys (recommended 2nd live venue)

Use NonKYC.io together with Binance for cross-venue arbitrage (Binance alone is not enough for external-only arb).

### 1. Create API keys on NonKYC.io

1. Log in at [https://nonkyc.io](https://nonkyc.io)
2. Open **Account → API** (or **Settings → API keys**)
3. Create a new key pair — save the **Access Key** and **Secret Key**
4. Restrict the key to **trade only** (no withdrawals) if the UI offers scopes
5. Optionally IP-allowlist your server IP

### 2. Add keys to local `.env`

Place these near your other exchange keys (uncommented, no quotes):

```
NONKYC_API_KEY=your_access_key_here
NONKYC_API_SECRET=your_secret_key_here
```

### 3. Push to server and import vault

```cmd
scripts\push_exchange_live_server.cmd
```

Or locally:

```cmd
python scripts\enable_live_daemons.py
python scripts\configure_live_trading.py --import-keys
```

### 4. Verify readiness

```cmd
python scripts\configure_live_trading.py
```

Expect `Live-ready venues: 2` with both `binance` and `nonkyc` showing `live_ready=True`.

API docs: [https://nonkyc.io](https://nonkyc.io) → API section · base URL `https://api.nonkyc.io/api/v2`

---

## Phased rollout

- **Phase 1 (done):** 10 read-only connectors, margin scanner, paper agents, profit accounts, vault, audit, admin APIs, daemon.
- **Phase 1b (done):** AI multi-venue trader — scans all 10 venues, scores with super-skills (sentiment alpha, ML forecast, Kelly sizing, latency momentum), executes signed API calls on Binance/OKX/Bybit/NonKYC/KuCoin (paper by default; live when gated).
- **Phase 2:** live balances read (signed account endpoints), withdrawal-aware cost model, alerting.
- **Phase 3:** gated live execution on 1–2 venues, treasury-funded, tiny notionals, kill-switch.
- **Phase 4:** funding-rate + triangular strategies, auto-sweep to external wallets with approval.
