# Reusable Migration Strategy for Sites & Features

**Purpose:** Apply the same migration approach used for the Shop Purchase system to other sites or features (e.g. Battle, Trophies, Chat history, Gallery, Points, etc.) so they can move from in-memory/JSON/placeholder logic to database-backed, auditable, and analytics-ready behavior.

---

## 1. Strategy Overview

| Step | What to do | Outcome |
|------|------------|--------|
| **1. Tables** | Define and create DB tables for the feature (catalog, transactions, user state). | Schema exists; app still works without it. |
| **2. Migration script** | Standalone script that creates tables + optional seed; use `--standalone` for direct DB (no Flask). | One command to bring a new env up to date. |
| **3. Service layer** | Feature-specific service that reads/writes DB; every function checks “tables exist?” and returns safe fallback (e.g. `None`, `[]`) when not. | No crashes if migration not run; feature degrades gracefully. |
| **4. Routes** | Routes use service when available; fall back to existing (seed/JSON/mock) logic. | Same URLs; behavior improves after migration. |
| **5. Frontend** | Optional: new sections (history, inventory, stats) that call new endpoints; show “empty” when migration not run. | UX improves after migration; no breakage before. |
| **6. Analytics** | Optional: analytics functions + endpoint (e.g. popular items, revenue, user stats). | Same strategy can add analytics to any feature. |

---

## 2. Step-by-Step Template for a New Feature

### 2.1 Define tables

- **Catalog/definition table** (e.g. `feature_items`, `battle_events_def`) – things that can be “bought” or “triggered”.
- **Transaction/history table** (e.g. `feature_purchases`, `battle_matches`) – who did what, when, and at what “price”.
- **User state table** (e.g. `user_feature_inventory`, `user_battle_stats`) – current state per user.

Use **TEXT** for JSON in SQLite; **INTEGER** for counts/ids; **TIMESTAMP** for created_at. Add indexes on `user_id`, foreign keys (item_id), and `created_at` for analytics.

### 2.2 Migration script pattern

- **Location:** `scripts/<feature>_migration.py` (e.g. `scripts/shop_purchase_migration.py`).
- **Options:**
  - **With Flask:** `create_app()` then use `db.session` (slow if many blueprints).
  - **Standalone:** `create_engine(DATABASE_URL)`, `connection.execute(text(...))`, `connection.commit()` after each DDL; load `.env` for `DATABASE_URL`. No Flask imports.
- **Idempotency:** `IF NOT EXISTS` for tables; skip seed if catalog table already has rows.
- **Seeding:** Prefer importing from the feature’s existing “seed” (e.g. `_seed_shop_items`) so one source of truth; catch import errors and warn “run from project root”.

Example structure:

```python
# scripts/example_feature_migration.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(sys.path[0])
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(sys.path[0], '.env'))
except Exception:
    pass

from sqlalchemy import text, inspect, create_engine

USE_STANDALONE = '--standalone' in sys.argv

class ExampleMigration:
    def __init__(self, standalone=False):
        if standalone:
            url = os.getenv('DATABASE_URL') or 'sqlite:///your.db'
            self.engine = create_engine(url)
            self.conn = self.engine.connect()
            self._execute = lambda s, p=None: self.conn.execute(text(s), p or {})
            self._commit = self.conn.commit
            self._tables = lambda: inspect(self.engine).get_table_names()
        else:
            from src.app import create_app
            from src.db.models import db
            app = create_app()
            app.app_context().push()
            self._db = db
            self._execute = lambda s, p=None: db.session.execute(text(s), p or {})
            self._commit = db.session.commit
            self._tables = lambda: inspect(db.engine).get_table_names()

    def run_migration(self):
        self._create_tables()
        self._create_indexes()
        self._seed_if_needed()

def main():
    m = ExampleMigration(standalone=USE_STANDALONE)
    m.run_migration()
    if USE_STANDALONE and getattr(m, 'conn', None):
        m.conn.close()
```

### 2.3 Service layer pattern

- **Location:** `backend/services/<feature>_db_service.py`.
- **Convention:**
  - `_get_db()` or equivalent to obtain `db` inside Flask app context.
  - `feature_tables_exist()` → bool (e.g. check for one key table).
  - All public functions: if not `feature_tables_exist()`, return `None`, `[]`, or `{}` (no raise).
  - Use raw SQL via `text(...)` and parameter binding; commit after each logical write.

Example:

```python
# backend/services/example_db_service.py
from sqlalchemy import text, inspect
from typing import List, Dict, Any, Optional

def _get_db():
    from src.db.models import db
    return db

def feature_tables_exist() -> bool:
    try:
        return 'example_main_table' in inspect(_get_db().engine).get_table_names()
    except Exception:
        return False

def get_items_from_db() -> Optional[List[Dict[str, Any]]]:
    if not feature_tables_exist():
        return None
    try:
        db = _get_db()
        rows = db.session.execute(text("SELECT id, name FROM example_items")).fetchall()
        return [{'id': r.id, 'name': r.name} for r in rows]
    except Exception:
        return None

def record_action(user_id: str, item_id: str, ...) -> Optional[int]:
    if not feature_tables_exist():
        return None
    try:
        db = _get_db()
        db.session.execute(text("INSERT INTO example_history (...) VALUES (...)"), {...})
        r = db.session.execute(text("SELECT last_insert_rowid()")).scalar()
        db.session.commit()
        return r
    except Exception:
        db.session.rollback()
        return None
```

### 2.4 Route integration pattern

- **Items/list:** `items = get_items_from_db() if get_items_from_db() else _seed_items()`.
- **Action (e.g. purchase):** After validating and performing the action (e.g. deduct currency), call `record_action(...)` and, if needed, `add_to_user_state(...)`; ignore return if `None`.
- **New endpoints:** e.g. `GET /api/example/history`, `GET /api/example/analytics`; call service; return empty list / default stats when tables missing.

### 2.5 Frontend pattern

- **New sections:** e.g. “My history”, “My inventory”; call new APIs; show “No data” or “Could not load” when empty or error.
- **Badges/state:** When rendering list items, if user state is available (e.g. inventory), show “Owned” or similar from that data.
- **Load order:** Fetch user-specific data (inventory, history) before rendering the main list so badges/state are correct on first paint.

### 2.6 Analytics pattern (Phase 5 style)

- In the feature’s `_db_service`: add functions like `get_analytics_popular()`, `get_analytics_revenue_by_X()`, `get_analytics_user_activity(user_id)`, `get_analytics_refund_stats()`.
- Single endpoint e.g. `GET /api/example/analytics?user_id=...&days=30` that returns a JSON object of all aggregates; when tables missing, return empty/default numbers.

---

## 3. Where to Apply This Strategy

| Site / feature | Suggested tables | Migration script | Service | Notes |
|----------------|------------------|------------------|---------|--------|
| **Shop** | shop_items, shop_purchases, user_inventory | `shop_purchase_migration.py` | shop_db_service | ✅ Done (reference) |
| **Battle** | battle_matches | `battle_migration.py` | battle_db_service | ✅ Done – history, quick (record), leaderboard |
| **Trophies** | trophy_definitions, user_trophy_unlocks | `trophies_migration.py` | trophies_db_service | ✅ Done – list, award; seed definitions |
| **Chat** | chat_sessions, chat_messages | chat_migration.py | chat_db_service | ✅ Done – history, send, messages, clear |
| **Gallery** | gallery_items, user_gallery_state, gallery_downloads | gallery_migration.py | gallery_db_service | ✅ Done – record view/download, GET /downloads |
| **Points** | point_aggregates_daily | points_migration.py | points_db_service | ✅ Done – analytics daily/summary, GET /api/points/analytics |
| **Generator / Jobs** | video_generation_jobs, job_artifacts | generator_migration.py | generator_db_service | ✅ Done – get/set job, list_jobs; missing_endpoints uses DB when tables exist |

---

## 4. Checklist for Each New Feature

- [ ] Tables designed (catalog, transactions, user state).
- [ ] Migration script added; supports `--standalone` and idempotent run.
- [ ] Service module added; every function checks tables and returns safe fallback.
- [ ] Routes updated to use service when available and keep existing fallback.
- [ ] New endpoints for history/inventory/analytics; return empty when no tables.
- [ ] Frontend: optional sections + “owned”/state badges; load order correct.
- [ ] Analytics (optional): analytics functions + single analytics endpoint.
- [ ] Docs: add the feature to “Where to Apply” and note any deviations.

---

## 5. Integration with Existing Codebases

- **Existing seed/mock data:** Keep it; use as fallback when `get_X_from_db()` returns `None` or `[]`.
- **Existing endpoints:** Don’t change URLs; change implementation to “try DB then fallback”.
- **Multiple apps/sites:** Same pattern: each site has its own migration script and service; shared DB or separate DB per site is a config choice (e.g. `DATABASE_URL` per app).
- **Other stacks (non-Flask):** Use the same table design and “standalone” migration script; in the app, replace `_get_db()` with that stack’s DB access and keep the “tables exist?” and fallback semantics.

---

## 6. Reference Implementations

### Shop (full reference)
- **Tables:** `shop_items`, `shop_purchases`, `user_inventory`.
- **Script:** `scripts/shop_purchase_migration.py` (`--standalone`).
- **Service:** `backend/services/shop_db_service.py`.
- **Routes:** `backend/routes/shop_routes.py` (items, purchase, purchases, inventory, analytics).
- **Frontend:** `vidgenerator/shop/index.html` (Inventory, Purchase History, Owned badges).

### Battle (implemented)
- **Tables:** `battle_matches` (user_id, battle_id, opponent_type, difficulty, result, points_delta, created_at).
- **Script:** `scripts/battle_migration.py` (`--standalone`).
- **Service:** `backend/services/battle_db_service.py` (record_battle, get_battle_history, get_battle_leaderboard).
- **Routes:** `backend/routes/battle_routes.py` – history and leaderboard read from DB; quick battle records a match (stub result) when DB exists.

### Trophies (implemented)
- **Tables:** `trophy_definitions`, `user_trophy_unlocks`.
- **Script:** `scripts/trophies_migration.py` (`--standalone`), seeds 3 default trophies.
- **Service:** `backend/services/trophies_db_service.py` (get_trophy_definitions, get_user_trophies, award_trophy).
- **Routes:** `backend/routes/trophies_routes.py` – list uses DB then falls back to trophy_system; award writes to DB when available.

### Chat (implemented)
- **Tables:** `chat_sessions` (id, user_id, created_at), `chat_messages` (session_id, user_id, username, message, is_ai, created_at).
- **Script:** `scripts/chat_migration.py` (`--standalone`).
- **Service:** `backend/services/chat_db_service.py` (save_message, load_chat_history, get_messages_since, clear_history). Uses room_id `'global'` for main chat.
- **Routes:** `backend/routes/chat_routes.py` – history, send, messages, clear use DB when tables exist; fallback to file.

### Gallery (implemented)
- **Tables:** `gallery_items`, `user_gallery_state` (user_id, item_id, last_viewed_at), `gallery_downloads`.
- **Script:** `scripts/gallery_migration.py` (`--standalone`).
- **Service:** `backend/services/gallery_db_service.py` (record_view, record_download, get_user_downloads, upsert_gallery_item).
- **Routes:** `backend/routes/gallery_routes.py` – video detail and download record view/download when `user_id` query param present; `GET /api/gallery/downloads?user_id=...`.

### Points (implemented)
- **Tables:** `point_aggregates_daily` (user_id, aggregate_date, system_name, total_credits, total_debits, net_change, transaction_count).
- **Script:** `scripts/points_migration.py` (`--standalone`). Requires `point_transactions` for analytics (from unified_points_database_migration or existing).
- **Service:** `backend/services/points_db_service.py` (get_analytics_daily, get_analytics_summary, refresh_daily_aggregates).
- **Routes:** `backend/routes/points_routes.py` – `GET /api/points/analytics?user_id=...&days=30`.

### Generator / Jobs (implemented)
- **Tables:** `video_generation_jobs` (job_id, user_id, job_type, status, progress, config, clips, video_url, etc.), `job_artifacts`.
- **Script:** `scripts/generator_migration.py` (`--standalone`).
- **Service:** `backend/services/generator_db_service.py` (get_job, save_job, list_jobs).
- **Routes:** `backend/routes/missing_endpoints_routes.py` – _get_video_job / _set_video_job use DB when tables exist, then in-memory fallback.

**Run migrations:** From project root either individually or all at once:
- `python scripts/run_all_migrations.py` — runs all 7 migrations with `--standalone`
- Or individually: `python scripts/battle_migration.py --standalone`, `scripts/trophies_migration.py`, `scripts/shop_purchase_migration.py`, `scripts/chat_migration.py`, `scripts/gallery_migration.py`, `scripts/points_migration.py`, `scripts/generator_migration.py`

**Frontend (next steps completed):**
- **Generator:** `GET /api/generator/jobs?user_id=...&limit=50` — list video jobs (Stats/Lab can add "My jobs" UI).
- **Points:** Stats page has a "Points Analytics" section (transactions, credits, debits, net over 30d) when `point_transactions` / analytics exist.
- **Gallery:** Gallery page has a collapsible "My downloads" section that calls `GET /api/gallery/downloads?user_id=...`.
