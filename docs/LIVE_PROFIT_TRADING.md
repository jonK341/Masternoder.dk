# Live profit trading — operator guide

Real cross-venue arbitrage on **your own treasury** (Binance + NonKYC), stashing USD profit to platform treasury and optional PayPal sweep.

> **Status (2026-07):** Path B funded (~$79 USDC + DOGE on Binance, ~$64 USDT + DOGE on NonKYC). Waiting for **≥18 bps** spread. Local daemon = primary executor; server cron = backup once NonKYC API works from VPS IP.

---

## Quick start

```cmd
scripts\configure_live_profit_max.cmd
scripts\run_all_profit_daemons.cmd
python scripts\profit_status_report.py
python scripts\_check_live_balances_once.py
```

Server deploy:

```cmd
python scripts\push_exchange_live_server.py
python scripts\_run_server_live_check.py
```

---

## Path B — EEA Binance (USDC) + NonKYC (USDT)

| Step | Action |
|------|--------|
| 1 | Buy **USDC** on Binance (MiCA — USDT not offered to EEA retail) |
| 2 | Withdraw **~$95 USDC** (TRC20) to NonKYC → swap to **USDT** there |
| 3 | Keep **~$79 USDC** on Binance |
| 4 | Buy **~$30 DOGE** on **both** venues (sell legs) |
| 5 | Set `BINANCE_QUOTE=USDC` (auto via `configure_live_profit_max`) |
| 6 | Run local profit daemon; wait for spread ≥ **18 bps** |

Bot uses **DOGEUSDC** on Binance and **DOGE_USDT** on NonKYC.

---

## Referral & signup links

Use these when onboarding operators or documenting the stack. Replace `{YOUR_REF}` with your personal codes where applicable.

| Service | Signup / referral | Notes |
|---------|-------------------|--------|
| **Binance (EEA)** | [binance.com/register](https://www.binance.com/en/register) | Fund with **USDC**; enable API (trade only, no withdraw) |
| **NonKYC.io** | [nonkyc.io](https://nonkyc.io) | 2nd live venue; USDT pairs; **IP whitelist required** |
| **XeggeX** | [xeggex.com/signup](https://www.xeggex.com/signup) | Optional 3rd venue — fix API 401 before funding |
| **MasterNoder casino** | `/casino` → Social → invite | Platform referral quests: `/api/casino/social/referral/quests` |
| **MasterNoder MN2** | `/shop` PayPal packs | Referee purchase credits: see `docs/MN2_TODO.md` tier C1 |

Optional env (local `.env`, not committed):

```
# BINANCE_REFERRAL=your_binance_ref_code
# NONKYC_REFERRAL=your_nonkyc_ref_if_available
```

---

## API keys & IP whitelist (NonKYC)

1. NonKYC → **Account → API** → Read + Trading (withdraw only if needed + IP list set).
2. Whitelist **IPv4 only** (Binance and NonKYC reject IPv6 in API settings):
   - **Home IPv4** — local daemon (e.g. `109.58.70.120`)
   - **Server IPv4** — `python scripts\_run_server_live_check.py` → `server_outbound_ipv4=…` (e.g. `140.82.39.124`)
   - On the VPS set **`EXCHANGE_FORCE_IPV4=1`** so API calls use IPv4 (avoids 401 when the host has IPv6).
3. Save with **2FA** → Update.
4. Re-check: `api_ok=True` in server live check.

---

## Trading mechanics (what we use vs skip)

| Mechanic | Used? | Notes |
|----------|-------|--------|
| Spatial arb Binance ↔ NonKYC | **Yes** | Live when spread + inventory OK |
| USDC quote on Binance | **Yes** | EEA/MiCA |
| Pre-funded inventory (no per-trade transfer) | **Yes** | `prefunded_transfer_cost_bps: 6` |
| Inventory-aware symbol scan (DOGE first) | **Yes** | Skips symbols without quote/coin |
| Unhealthy venue drop (401) | **Yes** | XeggeX excluded until API fixed |
| Fresh prices in live mode | **Yes** | No stale cache on live scans |
| Cross-trade / casino / AI bots | Running | **Internal** PnL — not exchange USD |
| XeggeX third venue | **No** | API 401 |
| Real PayPal sweep | **After** first LIVE stashed > $0 | `EXCHANGE_PAYOUT_PAYPAL_LIVE=1` |
| Maker/limit orders | **No** | Market orders only |
| Auto rebalance USDC↔USDT | **Manual** | Path B deposit flow |

---

## PayPal vs compound on exchanges

**Recommended for your setup:** keep profits on **Binance (USDC) + NonKYC (USDT/DOGE)**, not auto-sweep to PayPal.

| Path | What happens |
|------|----------------|
| **Live arb trade** | Profit stays on the venue wallets (more USDC/USDT after the sell leg) — **this is real compounding** |
| **Internal ledger** | Tracks estimated P&L for reports (`LIVE stashed` line) — does not move exchange funds |
| **PayPal auto-sweep** | **OFF** by default (`EXCHANGE_AUTO_PAYPAL_SWEEP=0`, `auto_sweep: false`) |

Why compound on-venue is stronger at ~$200 scale:

- Bigger USDC/USDT balances → larger buy legs without new deposits  
- More DOGE on both sides → more sell-leg capacity  
- PayPal sweep adds friction and removes capital from the arb loop  

Manual PayPal later: set `EXCHANGE_AUTO_PAYPAL_SWEEP=1` only when you want to take profit off-platform.

---

- Retail cross-venue arb is **crowded**; edges are brief and often **<18 bps** on BTC/ETH.
- **DOGE** on Binance ↔ small venues can spike — farm is tuned for DOGE/XRP/LTC first.
- Negative spreads most of the time is **normal** — first live trade needs a volatility blip.
- Do **not** add capital until `LIVE stashed > 0` or you accept longer wait.

---

## TODO / follow-ups

- [x] Confirm NonKYC **server outbound IP** whitelisted + `EXCHANGE_FORCE_IPV4=1`
- [ ] First live arb: `LIVE stashed > 0` in `profit_status_report.py`
- [ ] Enable real PayPal sweep after live stash ≥ $35
- [ ] Fix XeggeX API keys (optional 3rd venue)
- [ ] Push config after changes: `push_exchange_live_server.py`
- [ ] Alert hook when `profitable_count ≥ 1` (Discord/webhook — not wired yet)

See also: [EXCHANGE_CROSS_VENUE_ARBITRAGE.md](EXCHANGE_CROSS_VENUE_ARBITRAGE.md), [DAEMONS_AND_AGENTS.md](DAEMONS_AND_AGENTS.md).
