# MN2 Laptop Trader

A standalone dashboard + trading loop you run **on your own machine** (whose IP can reach the
exchanges — unlike the geo-blocked cloud sandbox). It pulls cross-trade **signals** from the
site's profit daemon, shows your **balances** (per venue / per pair) and grid **PnL**, and runs
the grid/market-maker bot locally so trades execute from your IP.

## Run

```bash
# from the repo root
pip install -r requirements.txt          # Flask, requests, cryptography already included
export SITE_URL=https://your-site.example    # where signals come from (omit to compute locally)
export SITE_ADMIN_KEY=<your exchange admin key>
# venue API keys (same as the main app):
export BINANCE_API_KEY=...  BINANCE_API_SECRET=...
export EXCHANGE_VAULT_KEY=...              # if NonKYC keys are in the encrypted vault
python trader_app/app.py                   # -> http://127.0.0.1:8800
```

Open http://127.0.0.1:8800 for the dashboard.

## What it shows
- **Total balance** and **realized PnL** headline KPIs, plus open-order count and mode (paper/LIVE).
- **Account balances** per venue and per asset/pair with USD value.
- **Grid positions & PnL**: inventory, avg cost, realized PnL, open orders, and halt state per market.
- **Cross-trade signals** from the site daemon (arbitrage spreads + grid candidates), flagged
  `actionable` when both legs are real venues (internal/simulated legs are info-only).

## Controls
- **Enable / Disable** the grid bot.
- **Run tick** — one grid cycle (paper by default).

## Going live (real money)
Paper by default — nothing trades for real until you set **both**:
```bash
export EXCHANGE_ARBITRAGE_LIVE=1
export EXCHANGE_GRID_LIVE=1
```
and fund the venue spot wallets in the quote assets (USDC on Binance, USDT on NonKYC).
Risk is bounded by the grid config (`data/exchange_grid_bot_config.json`): per-asset
`max_inventory_usd` and a global `hard_loss_cap_usd` that auto-halts and cancels all orders.
Grid/market-making books small wins in ranging markets and **loses in trends** — it is
risk-capped, not guaranteed profit.

## Config file (optional)
Instead of env vars you can create `trader_app/config.json`:
```json
{ "site_url": "https://your-site.example", "admin_key": "..." }
```
