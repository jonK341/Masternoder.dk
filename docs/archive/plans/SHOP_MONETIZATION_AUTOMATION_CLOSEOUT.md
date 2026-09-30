<!-- ARCHIVED SHOP_MONETIZATION_AUTOMATION_CLOSEOUT.md — finished plan removed from active docs. -->

> **Archived:** 2026-06-17. Closeout doc — automation shipped.

# Shop & monetization automation — closeout

**Date:** April 2026  
**Purpose:** Single conclusion for the Shop V.9 (formerly labeled v4) / API line / SCR blend / deploy verification work.

---

## What is done

1. **Shop V.9** — `SHOP_UI_VERSION` = `9.0.0`; catalog, PayPal packs, subscriptions, MN2, inventory, and `ShopV9` shadow (`shop_v9_shadow_*`, migrates `shop_v4_shadow_*`) + profile sync (`ShopV4` remains an alias on the shop page).
2. **API line checks** — Canonical list in `data/shop_v4_api_line_checks.json`, exposed on `GET /api/shop/config` as `api_line_checks`; same list used by `scripts/shop_v4_production_smoke.py --full-line` and the shop page **Run checks** button.
3. **Tests** — `tests/unit/test_shop_api_line_checks.py`, `test_shop_file_inventory.py`, `test_11_shop_routes.py` (config version), slow purchase-flow tests marked `@pytest.mark.slow`.
4. **SCR / phase C sanity** — `backend/services/monetization_scr_blend_service.py` + `scripts/monetization_scr_export.py` (blended ledger vs metering); CSV rollups remain `scripts/scr_usage_export.py`.
5. **Deploy automation** — After a successful `deploy.py` run, set **`DEPLOY_POST_VERIFY=1`** to run **`scripts/post_deploy_verify.py`**, which:
   - runs **`shop_v4_production_smoke.py --full-line`** against **`POST_DEPLOY_BASE_URL`** (default `https://masternoder.dk`);
   - runs **shop unit tests** locally with **`-m "not slow"`** by default (use **`--pytest-include-slow`** for the full purchase-flow tests).

---

## Migration plan status

See **`docs/SHOP_PURCHASE_MIGRATION_PLAN.md`** (conclusion table at bottom). Summary: SQL migration is **optional** for production if **`shop_file_mode`** is acceptable; **`GET /api/shop/payment-health`** includes **`shop_storage`** for visibility.

---

## What you still operate manually

- **PayPal:** live credentials, real billing plan IDs, webhooks (see `docs/MONETIZATION_PAYPAL.md`).
- **Production DB migration:** run `python scripts/shop_purchase_migration.py` on the server when you want durable SQL catalog/inventory instead of file-mode.
- **Optional:** backfill old shop purchases from `point_transactions` into `shop_purchases` (documented in the migration plan; not required for new purchases).

---

## Commands (cheat sheet)

```bash
# After deploy (local machine, network to prod)
set DEPLOY_POST_VERIFY=1
python deploy.py

# Or verify without redeploying
python scripts/post_deploy_verify.py
python scripts/post_deploy_verify.py --base-url https://masternoder.dk
python scripts/post_deploy_verify.py --list

# Margin snapshot (ledger + metering logs on disk)
python scripts/monetization_scr_export.py --since-days 30 --json
```

---

**Disclaimer:** Blended margin and file-mode inventory are operational aids; job-level revenue ↔ COGS attribution remains a future enhancement when you need phase C precision.
