# Shop V9.2 — Monetization Update

Status: **Shipped** · UI version `9.2.0` · Product line: Shop V.9 (Deals & VIP tab)

This update adds new ways to earn revenue from the shop on top of the existing Shop V.9
catalog, coin packs, subscriptions, MN2 wallet, and auction house. It is intentionally
**config-driven** (`data/monetization_config.json` → `shop_monetization`) so prices,
odds, and rewards can be tuned without code changes.

---

## 1. Ideation — 25 ways to make money in the shop

1. **Mystery boxes / loot crates** — weighted randomized rewards, paid per open.
2. **VIP membership pass** — recurring 30-day perks (daily coins, discount, badge).
3. **Spin-the-wheel** — one free daily spin, paid extra spins.
4. **Flash sales** — time-boxed rotating discounts to drive urgency.
5. **Coin gifting** — players send coins to each other (drives social top-ups).
6. **Whale coin packs** — large PayPal packs ($39.99 / $89.99) with bonus coins.
7. **Loyalty / cashback** — earn points per coin spent, redeem for rewards; tiered.
8. **Featured auction listings** — pay coins to promote a listing to the top.
9. **Mega bundles** — one-checkout bundle of coins + boosters + exclusive cosmetic.
10. **Stronger staking boosters** — premium x3 staking surge SKUs.
11. **Season / battle pass** — tiered seasonal reward track (free + premium lanes).
12. **Name / username change token** — paid vanity change.
13. **Limited seasonal/holiday cosmetics** — scarcity-driven cosmetic drops.
14. **Premium "gem" currency** — second hard currency above coins.
15. **Energy / time-skip refills** — pay to skip cooldowns.
16. **Referral spend rewards** — paid invite boosters.
17. **Bulk discount tiers** — buy-more-save-more on consumables.
18. **Ad-free / "remove PTC" pass** — pay to hide promoted placements.
19. **Insurance / shield tokens** — protect staking or battle outcomes.
20. **Token-gated exclusives** — hold MN2 to unlock special SKUs.
21. **Tip jar / creator donations** — voluntary support with cosmetic thank-yous.
22. **Auction listing fee tiers** — higher visibility for higher fees.
23. **Daily login streak shop credits** — retention-driven micro top-ups.
24. **Cosmetic upgrade / fusion** — combine owned cosmetics into rarer ones for coins.
25. **Charity round-up** — round purchases up; optional, brand-positive.

## 2. Reduction — Top 10 (selected for revenue impact + fit with the existing stack)

| # | Feature | Why it made the cut |
|---|---------|---------------------|
| 1 | Whale coin packs | Direct fiat ARPU lift; pure config, zero risk. |
| 2 | VIP Pass (30 days) | Recurring revenue + daily-return hook. |
| 3 | Mystery boxes | High-margin repeat spend with transparent odds. |
| 4 | Spin the wheel | Daily engagement loop; free→paid conversion. |
| 5 | Flash sales | Urgency on existing catalog; no new SKUs needed. |
| 6 | Coin gifting | Social-driven top-ups; expands paying base. |
| 7 | Loyalty / cashback | Retention + reason to consolidate spend here. |
| 8 | Featured auction listings | Monetizes the existing P2P marketplace. |
| 9 | Mega bundle | Raises average order value. |
| 10 | Premium staking boosters | Ties shop spend to the MN2 staking economy. |

Deferred (good, but heavier or riskier): season pass, gem currency, ad-free pass,
cosmetic fusion, token-gating — tracked for a later phase.

## 3. Implementation map

**Config:** `data/monetization_config.json`
- `coin_packs[]` — added `coin-pack-xl`, `coin-pack-xxl` (whale packs).
- `digital_goods[]` — added `vip-pass-monthly` (delivery `vip_pass`).
- `content_bundles[]` — added `bundle-whale-mega`.
- `shop_booster_skus[]` — added `booster-staking-300-12h`.
- `shop_monetization{}` — new block: `vip_pass`, `mystery_boxes`, `spin_wheel`,
  `flash_sales`, `loyalty`, `gifting`, `auction_feature`.

**Service:** `backend/services/shop_monetization_service.py`
- State persists at `logs/shop_monetization/state.json` (file-mode, same pattern as
  `shop_db_service` / `shop_auction_service`). All balance changes go through
  `unified_points_db` so coins/MN2 stay consistent.
- Public functions: `get_vip_status`, `activate_vip`, `claim_vip_daily`,
  `list_mystery_boxes`, `open_mystery_box`, `get_spin_status`, `spin_wheel`,
  `get_flash_sales`, `gift_coins`, `list_gifts`, `get_loyalty`, `redeem_loyalty`,
  `feature_listing`, `get_featured_listing_ids`, `get_overview`.

**Routes:** `backend/routes/shop_monetization_routes.py` (blueprint `shop_monetization_bp`,
registered in `backend/register_blueprints.py` right after the shop blueprint):

| Method | Endpoint |
|--------|----------|
| GET  | `/api/shop/monetization/overview` |
| GET  | `/api/shop/vip/status` |
| POST | `/api/shop/vip/claim-daily` |
| GET  | `/api/shop/mystery-boxes` |
| POST | `/api/shop/mystery-box/open` |
| GET  | `/api/shop/spin-wheel` |
| POST | `/api/shop/spin-wheel/spin` |
| GET  | `/api/shop/flash-sales` |
| POST | `/api/shop/gift` |
| GET  | `/api/shop/gifts` |
| GET  | `/api/shop/loyalty` |
| POST | `/api/shop/loyalty/redeem` |
| POST | `/api/shop/auction/feature` |
| GET  | `/api/shop/auction/featured` |

**Catalog integration** (`backend/routes/shop_routes.py`):
- `SHOP_UI_VERSION` bumped to `9.2.0`.
- `_apply_shop_item_effects` activates VIP when a `delivery: vip_pass` SKU is purchased,
  so the VIP Pass can be bought with coins / unified points / PayPal / MN2 via the normal
  purchase flow.
- `/api/shop/auction/listings` marks and floats `featured` listings to the top.
- `/api/shop/config` exposes a `monetization_shop.v92` capability summary.

**Frontend** (`shop/index.html`):
- New **⭐ Deals & VIP** tab and panel: VIP card, loyalty card, spin wheel, mystery
  boxes (with published odds), flash sales, and coin gifting.
- Version badges and update banner refreshed to v9.2.0.

## 4. Pricing & odds (defaults — tune in config)

- VIP Pass: 1500 coins / $9.99, 30 days, +100 daily coins, 10% box/spin discount,
  2 free daily spins, +5% loyalty cashback.
- Mystery boxes: Bronze 150 / Silver 400 / Gold 1000 coins, each with weighted loot
  and a published break-even tier (odds returned to the client).
- Spin: 1 free/day (VIP +2), 50 coins per paid spin.
- Flash sales: 3 SKUs, 20–50% off, rotate every 6h (deterministic per window).
- Loyalty: 5 pts per 100 coins spent. Earned across the **whole catalog** — coin and
  in-wallet MN2 purchases call `accrue_purchase_loyalty` from the main purchase flow
  (`shop_routes.shop_purchase` and `shop_mn2_purchase_core`), in addition to the V9.2
  mechanics. Tiers Bronze→Platinum add 3–12% cashback; VIP adds +5%. Redeem for coins
  or boosters. Purchase responses now include `loyalty_earned`.
- Gifting: min 10 coins, 0% fee (configurable).
- Featured auction: 200 coins for 48h.

## 5. Safety notes

- All paid actions debit **before** granting and validate balances first; gifting
  refunds the sender if delivery fails.
- Odds for mystery boxes are returned to the client for transparency.
- Guest (`default_user`) is blocked from spend/gift/feature actions.
- Everything degrades gracefully: if the `shop_monetization` config block is missing,
  endpoints return empty/inactive states instead of erroring.

## 6. Tests

`tests/unit/test_shop_monetization.py` — covers VIP activation/claim,
VIP discount, mystery box charge/reward + insufficient funds, spin (free→paid),
gifting transfer + validation, loyalty accrual/redeem, featured-listing ownership,
flash-sale shape/stability, and the Top 25 collection (status, claim gating, one-time
reward, guest block). Balance ops use an in-memory fake points DB; state is isolated
via a temp `MASTERNODER_LOG_DIR`.

`tests/unit/test_mn2_order_payment.py` — covers the MN2 on-chain order-payment
upgrades: progress fields, grace-window matching, `confirming` state, underpaid
marking, and amount-received recording on fulfilment.

## 7. Top 25 Legends — series, bundles & completion trophy

The flagship **Top 25 Legends** collectible series (`top25-01`…`top25-25`, category
`top25`) is sold individually and via three upsell bundles (config:
`content_bundles`), all coin-priced so they work with coins / in-wallet MN2 /
on-chain MN2 / PayPal and earn loyalty:

| Bundle | Includes | Coins | Save |
| --- | --- | --- | --- |
| `bundle-top25-starter` | ranks #01–#05 | 1,299 | ~21% |
| `bundle-top25-elite` | ranks #21–#25 | 16,999 | ~21% |
| `bundle-top25-complete` | all 25 + 2,500 bonus coins | 29,999 | ~30% |

**Completion trophy.** `shop_monetization.top25_collection` configures the goal
(total 25, reward = 5,000 coins + 1,000 loyalty + `top25-collector-trophy` + a
`top25-collector` badge). Logic in `shop_monetization_service` (`get_top25_status`,
`claim_top25_completion`); endpoints `GET /api/shop/top25/status` and
`POST /api/shop/top25/claim`. Ownership is read from the user's inventory, so the
trophy unlocks whether the set was bought item-by-item or via the Complete bundle.
Claim is one-time and guests are blocked. Surfaced as a progress card on the
**Deals & VIP** tab.

## 8. MN2 on-chain payment upgrades (V9.2)

The on-chain checkout (`/api/mn2/order-payment`) was hardened against fund loss and
given live progress (config in `data/mn2_config.json`):

- **Tolerant matching.** The scanner no longer requires an *exact* amount.
  `order_payment_overpay_credit` fulfils on overpay and refunds the excess to the
  buyer's `mn2_balance` (ledger `order_overpay_change`). `order_payment_underpay_credit`
  credits a short payment to balance (ledger `order_underpaid_credit`) instead of
  stranding it.
- **Daemon completes the transaction (`order_payment_combined_fulfill`, default on).**
  On underpay, after crediting what arrived, the scanner auto-completes the order from
  the buyer's *combined* `mn2_balance` (debits the full `amount_mn2`, ledger
  `mn2_order_combined_fulfill`) so the on-chain payment finishes end-to-end without the
  user returning to the interface. If the balance still can't cover it, the order stays
  `underpaid` with the credit intact; if fulfilment fails after debiting, the debit is
  refunded so funds are never lost. Logic lives in the testable
  `mn2_deposit_scanner.apply_order_payment(...)` helper.
- **Grace window.** `order_payment_grace_hours` (default 24h) keeps an order matchable
  after its 1h checkout timer, so a late payment still fulfils rather than being lost.
- **Confirmation progress.** Orders gain a `confirming` status with
  `confirmations` / `confirmations_required` surfaced via
  `/api/mn2/order-payment/status`, so the checkout modal can show "x/N confirmations".

All credits remain idempotent via the ledger's `is_txid_processed` guard.

## 9. Explorer: more daemon stats + 5-day Network Monitor

`/explorer` now surfaces live daemon RPC stats and a 5-day monitor (under the
**Network** section):

- **Daemon tiles.** `mn2_chainz.daemon_extras()` (RPC-only, cached ~30s) adds peers
  (`getconnectioncount`), mempool size/bytes (`getmempoolinfo`), version/subversion
  (`getnetworkinfo`), sync progress + chain + on-disk size (`getblockchaininfo`), and
  money supply (`getblockchaininfo`/`getinfo`). Exposed on `/api/mn2/network-overview`
  under a `daemon` block (plus top-level `connections`/`mempool_tx`).
- **5-day Network Monitor.** New area-chart grid driven by
  `/api/mn2/network-history?hours=120` covering block height, price, difficulty,
  network weight, masternodes, peers, mempool, and pool staked — each with a
  last value, min…max range, and % delta badge. Recent `/api/mn2/network-alerts`
  (staking-stopped / height-stall) render below it. `connections` and `mempool_tx`
  were added to the snapshot keys so they chart over time going forward.
