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
