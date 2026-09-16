# PayPal + MN2 Rails — One Pager

Use two explicit payment rails:

- **PayPal -> credits:** fiat checkout, credits granted after capture, COGS measured against jobs.
- **MN2 -> balance:** crypto deposit or shop debit, ledgered separately from fiat revenue.

## Operating Rules

- Do not mix chargeback-prone fiat flows with irreversible crypto settlement in one unclear SKU.
- Keep each catalog item tagged with supported rails: `paypal`, `mn2`, and/or `credits`.
- Track generator-heavy SKUs against metering COGS; track pure digital goods as low-COGS revenue.

## Current Repo Touchpoints

- `data/monetization_config.json`
- `data/mn2_config.json`
- `backend/services/monetization_config_service.py`
- `backend/routes/shop_routes.py`

## Trophy rail (2026-09 plan 001)

| Rail | Trophy checkout | Settlement |
|------|-----------------|------------|
| **PayPal** | Shop/Exchange trophy cards → `create-order` uses server `effective_price_usd` | Edition + `hold_until` + `trophy_edition_proof` ledger |
| **MN2** | Shop MN2 button / block claim | `fulfill_shop_purchase` + edition row in `trophy_editions/{user}.json` |
| **Coins** | Shop coin purchase | Same inventory path; dynamic coin price from pricing engine |

**Not supported:** on-chain MN2 NFT mint per trophy (`on_chain_mint: false` on all trophy SKUs).

**Trading:** Edition-aware auction (`edition_no` required) and peer transfer (`POST /api/shop/trophies/transfer`) — both blocked while PayPal hold is active.
