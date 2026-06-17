# MN2 Trader Market

**Last updated:** 2026-06-17

Internal **MN2 ↔ coins** order book with six trader agents providing liquidity. Separate from PayPal Model B (`/api/mn2/p2p/*`).

---

## Architecture

| Layer | Component |
|-------|-----------|
| **Order book** | `backend/services/p2p_market_service.py` → `data/p2p_market_orders.json`, `p2p_market_trades.jsonl` |
| **Trader fleet** | `backend/services/agent_trader_service.py` — 6 strategies, sell + cross-buy each tick |
| **Staking pool** | `backend/services/agent_trader_staking_service.py` — ~25k±10k MN2 staked per agent |
| **API** | `backend/routes/p2p_market_routes.py`, `agent_trader_staking_routes.py` |
| **UI** | Explorer → **Market** tab (`/explorer?tab=market`) — `static/js/mn2-internal-market.js` |
| **Cron** | `cron/agents_trader.sh` every 15 min → `agent_trader` job |

---

## API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/market/config` | GET | Public config (enabled, trader count, reference price) |
| `/api/market/ticker` | GET | Best bid/ask, depth, last trade price |
| `/api/market/orders` | GET | Open orders (`?side=sell`) |
| `/api/market/trades` | GET | Recent fills |
| `/api/market/orders` | POST | Create buy/sell (`user_id`, `side`, `mn2_amount`, `price_coins_per_mn2`) |
| `/api/market/fill` | POST | Buy from a sell order |
| `/api/market/cancel` | POST | Cancel own open order |
| `/api/agents/trader-staking/status` | GET | Trader pool + follower copy-trade state |
| `/api/agents/trader-staking/run-market` | POST | Ops: one fleet tick (wallet sync + sell + buy) |

---

## Ops — manual tick

```bash
SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' /var/www/html/.env | head -1 | cut -d= -f2- | tr -d '\r"')
curl -s -X POST -H "X-Ops-Secret: $SECRET" http://127.0.0.1:5000/api/agents/trader-staking/run-market | jq '.trades,.wallet_sync'
curl -s http://127.0.0.1:5000/api/market/ticker | jq
curl -s 'http://127.0.0.1:5000/api/market/orders?side=sell&limit=5' | jq
curl -s 'http://127.0.0.1:5000/api/market/trades?limit=5' | jq
```

From Windows:

```powershell
python scripts/_verify_trader_market_remote.py --ask-pass
```

---

## Deploy

```powershell
python scripts/deploy.py mn2_staking --ask-pass
```

Uploads routes, trader services, explorer market UI, and cron scripts.

---

## Config

`data/mn2_staking_config.json` → `trader_agents.market`:

- `sell_mn2_per_order`: 50
- `fill_mn2_per_trade`: 25
- `reference_price_coins_per_mn2`: 100
- `keep_balance_min_mn2`: 5000 (free MN2 for market vs staked)

---

## User flow

1. Open [Explorer → Market](https://masternoder.dk/explorer?tab=market)
2. See ticker + trader agent strip + open sells
3. **Buy** — click Buy on any sell row (costs coins, credits MN2)
4. **Sell** — list MN2 at a coins/MN2 price (locks MN2 until fill or cancel)

Requires a real `game_user_id` (not `default_user`) for mutating actions.

---

## Two markets on one tab

| Market | API | Settlement |
|--------|-----|------------|
| **Internal order book** | `/api/market/*` | Unified coins |
| **PayPal P2P (Model B)** | `/api/mn2/p2p/*` | PayPal USD — shown only when enabled in config |

---

## Activity events & Discord

Market actions emit to `logs/activity_events.jsonl` with `channel=market`:

| Event | When |
|-------|------|
| `p2p_market_order` | User or agent lists a sell |
| `p2p_market_fill` | Buy matches a sell |
| `p2p_market_cancel` | Order cancelled |
| `trader_market_tick` | Fleet cron completes with ≥1 cross-trade |

**Discord fan-out:** `market_discord_fanout.py` posts fills ≥ `MARKET_DISCORD_MIN_MN2` (default 5) and trader tick summaries to `#market`. Cron: `cron/discord_market_fanout.sh`.

Full integration map: [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md) · Ops: [MN2_OPS.md](MN2_OPS.md) §10.
