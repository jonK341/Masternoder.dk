# Exchange ↔ Casino bridge

How the trading agents stack connects to the casino — and what to think about next.

## Shared today

| Link | Detail |
|------|--------|
| **MN2 wallet** | Exchange rentals/shop and casino MN2 bets use the same `mn2_balance` |
| **Agent control center** | `/exchange#cex-control-center` — rent, skills, PayPal/coins/MN2 pay, profit cash-out |
| **Cash-out → casino** | Paper profit can convert to **casino play coins** (100 coins / USD) |
| **Skills overlap** | Casino agent models use `kelly_sizing`; exchange rentals can attach the same skill |
| **XP / progression** | Exchange leveling + casino progression both reward activity (separate tracks today) |

Config: `data/exchange_controller_config.json` · `data/casino_config.json` → `real_money.exchange_bridge`

## API (controller)

| Method | Path |
|--------|------|
| GET | `/api/exchange/controller/hub` |
| GET | `/api/exchange/controller/catalog` |
| POST | `/api/exchange/controller/quote` |
| POST | `/api/exchange/controller/checkout` `{ action, target_id, payment_method, agent_id?, auto_renew? }` |
| POST | `/api/exchange/controller/cash-out` `{ amount_usd?, destination: mn2\|coins\|casino_coins }` |
| POST | `/api/exchange/controller/paypal/create` |
| POST | `/api/exchange/controller/paypal/capture` |

`action`: `rent` · `addon` · `shop`  
`payment_method`: `mn2` · `coins` · `paypal`

## Casino — what else to think about

### High value (product)

1. **Unified wallet UI** — ✓ casino `#casino-exchange-bridge` strip + `/api/casino/exchange-bridge`  
2. **Cross-quests** — ✓ weekly bridge quests (`/api/exchange/casino-bridge/quests`) + battle pass actions `exchange_rent`, `casino_mn2_win`  
3. **Skill marketplace** — ✓ same controller checkout from exchange + casino link (skill packs need agent in control center)  
4. **Leaderboard fusion** — ✓ weekly Trader + High roller board (`/api/exchange/casino-bridge/leaderboard`)  
5. **Discord fan-out** — ✓ `#market` embeds for elite rentals + MN2 wins; combined pulse when both in same batch  

### Compliance & risk

6. **Separate disclaimers** — paper exchange profit vs real MN2 casino stakes (already split in config)  
7. **PayPal rails** — exchange controller PayPal ≠ casino USD balance; don’t mix capture handlers  
8. **Trust gates** — exchange trust tier before enabling MN2 casino high-roller tables  
9. **Loss limits** — casino `max_loss_mn2` tiers should consider shared MN2 balance  

### Technical next steps

10. **Casino agent → exchange skill import** — let `casino_meta_oracle` rent `sentiment_alpha` for 7 days  
11. **Rental completion → casino bonus** — ✓ auto-grant 50 play coins on claim (`grant_casino_bridge_bonus`)  
12. **Facebook / E3 webhook** — casino stream bot mentions exchange rentals (see `MN2_TODO` E3)  
13. **LiveKit / social** — camgirls tip → exchange MN2 pack coupon  

### Tests

```bash
python -m pytest tests/unit/test_exchange_casino_bridge_product.py tests/unit/test_exchange_user_controller.py tests/unit/test_market_discord_fanout.py -q
```
