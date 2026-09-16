# Exchange rental & shop

Easy try-before-buy rentals, skill add-ons for agent-tools, and an MN2 shop with rewards and boosts.

## Rental hub

Rent a bot for **3–7 days** (cheaper than buying). Profit accrues to your account. When the term ends, claim a **completion reward** (MN2 + XP).

| Rental ID | Days | MN2 | Skills |
|-----------|------|-----|--------|
| `rent_starter_7d` | 7 | 45 | spatial_arbitrage, withdrawal_aware_routing |
| `rent_pro_7d` | 7 | 120 | triangular, stablecoin peg, TWAP |
| `rent_elite_3d` | 3 | 95 | volatility breakout, cross-pair momentum |

Config: `data/exchange_rental_config.json`

### Skill add-ons

Attach extra skills to any **active rental or owned bot**:

- Z-Score Stat Arb, Avellaneda-Stoikov MM, AI Sentiment, Kelly Sizing, Latency Momentum  
- Priced per addon in MN2 for N days  

## Exchange shop

Config: `data/exchange_shop_catalog.json`

| Item | Category | Effect |
|------|----------|--------|
| Trader Starter Chest | reward | MN2 + XP |
| Arbitrage Skill Pack | skill | +2 skills for 14 days on a bot |
| Rental +3 Days | rental | Extend active rental |
| Silver Trust Badge | trust | +8 trust for 30 days |
| Profit Boost 24h | boost | 1.25× paper profit |
| Fee Discount Card | fee | −15 bps fees for 14 days |
| Premium Scan Token | tool | 10 priority radar scans |
| Sentient Trial Voucher | rental_voucher | Prepaid elite rental |

## API

| Method | Path |
|--------|------|
| GET | `/api/exchange/rental/catalog` |
| GET | `/api/exchange/rental/mine` |
| POST | `/api/exchange/rental/rent` `{ rental_id }` |
| POST | `/api/exchange/rental/add-skill` `{ agent_id, addon_id }` |
| POST | `/api/exchange/rental/claim-reward` `{ agent_id }` |
| GET | `/api/exchange/shop/catalog` |
| GET | `/api/exchange/shop/state` |
| POST | `/api/exchange/shop/purchase` `{ item_id, agent_id? }` |

## UI

Exchange page → **Easy rental** + **Exchange shop** sections (below marketplace).  
Hero banner + 3 visual cards in header (`static/img/exchange/`).

## Auto-renew

Enable per rental (checkbox on **My rentals**) or when renting (`auto_renew: true`).

- Renews within **24h** of expiry (or **6h grace** after) at **−10% MN2**
- Master daemon runs `process_auto_renewals()` each tick
- API: `POST /api/exchange/rental/auto-renew` `{ agent_id, enabled }`

## Main shop link

Five consumables appear in **`/shop?category=exchange`**: chest, trust badge, profit boost, fee card, scan tokens.  
Skill packs / rental extensions stay on the exchange page (need agent ID).

Config flag per item: `"shop_linked": true|false` in `exchange_shop_catalog.json`.
