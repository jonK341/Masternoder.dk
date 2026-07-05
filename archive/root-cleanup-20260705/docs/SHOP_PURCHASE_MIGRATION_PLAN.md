# Shop Purchase System Migration Plan

**Date:** 2026-02-11  
**Status:** ✅ Implemented – Working solution with fallback

---

## 🎯 Migration Overview

This migration adds proper database support for the shop purchase system, moving from:
- ❌ **Before:** Purchase data only in `point_transactions` metadata
- ✅ **After:** Dedicated tables for purchases, inventory, and shop catalog

**Working solution:** The app works **with or without** running the migration. If tables don't exist, the shop uses seeded items and does not record purchases/inventory. After migration, items come from DB and purchases are recorded.

---

## 📊 New Database Tables

### 1. `shop_items` - Shop Catalog
**Purpose:** Store shop item catalog (replaces seeded code)

**Schema:**
```sql
CREATE TABLE shop_items (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    price_type VARCHAR(20) NOT NULL CHECK(price_type IN ('coins', 'unified_points')),
    price_coins INTEGER DEFAULT 0,
    price_points JSON,
    icon VARCHAR(10) DEFAULT '🛍️',
    rarity VARCHAR(20) DEFAULT 'common' CHECK(rarity IN ('common', 'rare', 'epic', 'legendary')),
    is_active BOOLEAN DEFAULT 1,
    stock_limit INTEGER,
    purchase_limit INTEGER,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Indexes:**
- `idx_shop_items_category` - Filter by category
- `idx_shop_items_active` - Filter active items
- `idx_shop_items_rarity` - Filter by rarity

**Benefits:**
- Items can be updated without code changes
- Admin can manage catalog via API/database
- Stock limits and purchase limits supported
- Historical item data preserved

---

### 2. `shop_purchases` - Purchase History
**Purpose:** Track all shop purchases with full audit trail

**Schema:**
```sql
CREATE TABLE shop_purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    item_id VARCHAR(100) NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    quantity INTEGER DEFAULT 1,
    price_type VARCHAR(20) NOT NULL CHECK(price_type IN ('coins', 'unified_points')),
    price_paid_coins INTEGER DEFAULT 0,
    price_paid_points JSON,
    balance_before JSON,
    balance_after JSON,
    purchase_status VARCHAR(20) DEFAULT 'completed' CHECK(purchase_status IN ('completed', 'refunded', 'cancelled')),
    refunded_at TIMESTAMP,
    refund_reason TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Indexes:**
- `idx_shop_purchases_user_id` - User purchase history
- `idx_shop_purchases_item_id` - Item popularity
- `idx_shop_purchases_created_at` - Time-based queries
- `idx_shop_purchases_user_created` - User history sorted by date

**Benefits:**
- Complete purchase audit trail
- Support for refunds
- Analytics: popular items, revenue, user spending
- Balance tracking (before/after)

---

### 3. `user_inventory` - Owned Items
**Purpose:** Track what items users own

**Schema:**
```sql
CREATE TABLE user_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    item_id VARCHAR(100) NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    quantity INTEGER DEFAULT 1,
    purchase_id INTEGER,
    is_active BOOLEAN DEFAULT 1,
    expires_at TIMESTAMP,
    used_at TIMESTAMP,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, item_id)
)
```

**Indexes:**
- `idx_user_inventory_user_id` - User's inventory
- `idx_user_inventory_item_id` - Item ownership
- `idx_user_inventory_active` - Active items only
- `idx_user_inventory_user_item` - Fast lookup

**Benefits:**
- Prevent duplicate purchases (if item is single-use)
- Track item usage
- Support expiring items (boosts, temporary items)
- Link to purchase history

---

## 🔄 Migration Steps (Implemented)

### Phase 1: Create Tables
1. Run from **project root**: `python scripts/shop_purchase_migration.py`
2. Script creates `shop_items`, `shop_purchases`, `user_inventory` and indexes.
3. If `create_app()` or DB is slow, the script may take 30+ seconds; run in a terminal and wait.

### Phase 2: Seed Data
1. Same script seeds `shop_items` from `backend.routes.shop_routes._seed_shop_items()`.
2. If import fails (e.g. not run from project root), seed is skipped; run again from repo root.

### Phase 3: Backend (Done)
1. **`backend/services/shop_db_service.py`** – New service:
   - `shop_tables_exist()`, `get_shop_items_from_db()`, `record_purchase()`, `add_to_inventory()`, `get_purchases()`, `get_inventory()`
   - All functions safe when tables are missing (return None / []).
2. **`backend/routes/shop_routes.py`**:
   - `_get_shop_items()` uses DB when tables exist, else `_seed_shop_items()`.
   - After successful purchase (coins or points), calls `record_purchase()` and `add_to_inventory()` when DB is available.
   - New endpoints: `GET /api/shop/purchases?user_id=`, `GET /api/shop/inventory?user_id=`

### Phase 4: Frontend Updates ✅
1. ✅ **Purchase history** – Collapsible "Purchase History" section on shop page; loads `GET /api/shop/purchases`, shows last 20 purchases with item name, quantity, price, date.
2. ✅ **Inventory display** – Collapsible "My Inventory" section; loads `GET /api/shop/inventory`, shows owned items and quantities.
3. ✅ **Owned badge** – Shop item cards show an "OWNED" (or "OWNED ×N") badge when the user has the item in inventory; inventory/purchases loaded before shop grid so badges appear on first paint.

### Phase 5: Analytics ✅
1. ✅ **Popular items** – `get_analytics_popular_items(limit)` in `shop_db_service.py`; most purchased by quantity.
2. ✅ **Revenue by item** – `get_analytics_revenue_by_item()` (coins per item).
3. ✅ **Revenue by category** – `get_analytics_revenue_by_category(days)` (optional `days` filter).
4. ✅ **User spending** – `get_analytics_user_spending(user_id)` (total coins, purchase count, quantity).
5. ✅ **Refund stats** – `get_analytics_refund_stats()` (total, completed, refunded, refund_rate).
6. ✅ **Single endpoint** – `GET /vidgenerator/api/shop/analytics?user_id=...&limit=10&days=30` returns all of the above; `user_spending` included when `user_id` is present.

---

## 📝 Code Changes Required

### Backend Changes

#### `backend/routes/shop_routes.py`

**Current:**
```python
def shop_v3_items():
    items = _seed_shop_items()  # From code
    return jsonify({'success': True, 'items': items})
```

**After Migration:**
```python
def shop_v3_items():
    items = get_shop_items_from_db()  # From database
    return jsonify({'success': True, 'items': items})
```

**Purchase Handler:**
```python
def shop_purchase():
    # ... existing validation ...
    
    # Record purchase
    purchase_id = record_purchase(user_id, item, quantity, price_paid, balance_before, balance_after)
    
    # Add to inventory
    add_to_inventory(user_id, item_id, quantity, purchase_id)
    
    return jsonify({'success': True, 'purchase_id': purchase_id, ...})
```

---

## 🔍 Data Migration

### Existing Purchase Data
Currently, purchases are logged in `point_transactions` with metadata:
```json
{
  "source": "shop_purchase",
  "metadata": {
    "item_id": "shop-1",
    "item_name": "Item Name",
    "quantity": 1
  }
}
```

**Migration Script Needed:**
- Extract purchase data from `point_transactions` where `source = 'shop_purchase'`
- Create `shop_purchases` records
- Create `user_inventory` records (if applicable)
- Link via `reference_id` or `metadata`

---

## ✅ Benefits

1. **Purchase History**
   - Users can see their purchase history
   - Support for refunds
   - Analytics and reporting

2. **Inventory Management**
   - Track owned items
   - Prevent duplicate purchases
   - Support expiring items

3. **Shop Catalog Management**
   - Update items without code changes
   - Stock management
   - Purchase limits
   - Admin interface possible

4. **Analytics**
   - Popular items
   - Revenue tracking
   - User behavior analysis

---

## 🚀 How to Run the Migration

From the **project root** (where `src/` and `backend/` live):

```bash
# Windows PowerShell
cd c:\Users\jonkh\UsecaseSampler\Masternoder.dk
python scripts/shop_purchase_migration.py
```

If the script hangs (e.g. on `create_app()` or DB connect), wait up to 60s or run with the same Python/env as the Flask app. No tables = shop still works with seeded items and no purchase history.

---

## ⚠️ Migration Issues & Fixes

| Issue | Cause | Fix |
|-------|--------|-----|
| Script hangs | `create_app()` or DB slow/locked | Wait 60s; run when no other process uses the DB; or run migration from same env as the app. |
| "Could not import _seed_shop_items" | Not run from project root | `cd` to repo root so `backend.routes.shop_routes` is importable. |
| Shop still shows items but no history | Migration not run | Run `scripts/shop_purchase_migration.py` once from project root. |
| SQLite "table already exists" | Re-run migration | Safe; script skips existing tables and skips seed if `shop_items` has rows. |

---

## 📋 Migration Checklist

- [x] Create migration script
- [x] Run migration on development (`python scripts/shop_purchase_migration.py --standalone`)
- [x] Verify tables created (`shop_items`, `shop_purchases`, `user_inventory`)
- [x] Backend uses DB when available and records purchases
- [x] **File-mode fallback** — when `shop_items` table is missing, purchases/inventory persist under `logs/shop_file_mode/` (`shop_db_service`); no silent loss of UX.
- [x] GET /api/shop/purchases and GET /api/shop/inventory added
- [x] Test purchase flow (unit + API line checks; production migration is ops-owned)
- [x] Update frontend (`shop/index.html` v4 — inventory + purchase history, Owned badges, product line + API checks)
- [ ] Run SQL migration on production (optional if file-mode is acceptable; use `GET /api/shop/payment-health` → `shop_storage` for mode)

---

## 📁 Files Touched

| File | Role |
|------|------|
| `scripts/shop_purchase_migration.py` | Creates tables, indexes, seeds `shop_items`; `--standalone` for direct DB |
| `backend/services/shop_db_service.py` | DB reads/writes + Phase 5 analytics; no-op when tables missing |
| `backend/routes/shop_routes.py` | `_get_shop_items()`, record purchase/inventory, GET purchases, inventory, analytics |
| `shop/index.html` | Shop v4 — inventory, purchase history, Owned badges, API line tests |
| `docs/MIGRATION_STRATEGY_REUSABLE.md` | Reusable strategy to apply same pattern to other sites/features |

---

## 🔁 Applying This Strategy to Other Sites

Use the **same pattern** for Battle, Trophies, Chat, Gallery, Points, Generator, etc.:

1. **Tables** – Catalog + transaction/history + user state tables.
2. **Migration script** – Standalone-capable, idempotent, optional seed.
3. **Service layer** – Feature `_db_service` with “tables exist?” checks and safe fallbacks.
4. **Routes** – Use DB when available, keep existing fallback; add history/analytics endpoints.
5. **Frontend** – Optional sections and “owned”/state badges; load order for first-paint correctness.
6. **Analytics** – Optional analytics functions + single analytics endpoint.

Full template, checklist, and “where to apply” list: **`docs/MIGRATION_STRATEGY_REUSABLE.md`**.

---

**Migration Status:** ✅ Implemented (Phases 1–5). Run `scripts/shop_purchase_migration.py` from project root when you want SQL-backed catalog/inventory; until then file-mode + seeded catalog keeps the shop working.

---

## Conclusion (April 2026)

| Track | State |
|--------|--------|
| **Schema + script** | Delivered; idempotent migration and seed. |
| **Runtime without migration** | Delivered — `shop_db_service` uses DB when `shop_items` exists, else JSON files under `logs/shop_file_mode/`. |
| **UX** | Shop v4 + Profile inventory use the same APIs; shadow backup in browser optional. |
| **Ops** | Production may stay on file-mode or migrate once; check `shop_storage` in payment-health. |
| **Legacy data** | Backfill from `point_transactions` (see “Data Migration” above) remains **optional** if you need historical rows in `shop_purchases`. |
| **Automation** | Post-deploy: `python scripts/post_deploy_verify.py` or `DEPLOY_POST_VERIFY=1` with `deploy.py`. See `docs/SHOP_MONETIZATION_AUTOMATION_CLOSEOUT.md`. |

