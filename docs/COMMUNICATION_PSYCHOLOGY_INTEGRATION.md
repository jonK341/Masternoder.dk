# Communication Psychology Integration

The **25 communication psychology theories** are integrated across the vidgenerator framework, unified points, starmap, DNA theory, profile, trophies, and shop.

## Database

- **Tables** (create with `python scripts/communication_psychology_migration.py`):
  - **comm_psych_theory_unlocks** — `user_id`, `theory_id`, `unlocked_at`, `metadata` (persists each study).
  - **comm_psych_activity_log** — `user_id`, `activity_type` (study | award), `theory_id`, `amount`, `source`, `metadata`, `created_at`.
- Progress is read from DB first, then merged with file store (`logs/communication_psychology/{user_id}.json`). Unlocks and activity are written to both DB and file.

## Data & API

- **Theories data:** `data/communication_psychology_theories.json` — 25 theories in 6 categories (power_dynamics, social_influence, rhetoric, psychological_warfare, digital_power, monetization).
- **User progress:** `logs/communication_psychology/{user_id}.json` — unlocked theory IDs and studied_at timestamps.
- **Points:** `communication_psychology_points` in the unified point system (file store + optional DB snapshots).

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/communication-psychology/theories` | List all 25 theories and categories (also under `/vidgenerator/api/...`) |
| GET | `/api/communication-psychology/progress?user_id=` | User's unlocked theories and comm-psych points (for profile) |
| POST | `/api/communication-psychology/study` | Body: `{ "user_id", "theory_id" }` — unlock theory, award points, check trophies |
| POST | `/api/communication-psychology/award` | Body: `{ "user_id", "amount", "source", "metadata" }` — award points from external activity |
| GET | `/api/communication-psychology/activity?user_id=&limit=` | Recent activity from DB (study, award) for frontend |

## Integration Points

1. **Unified point system** — `communication_psychology_points` is a normal point type; awarded on study and from generator/shop. Shown in profile and any UI that uses `get_all_points()`.
2. **Trigger integration** — `unified_points_trigger_integration` maps `communication_psychology_points` → `communication_psychology` trigger.
3. **Starmap** — `data/star_map.json` has a flyer `comm_psych` linking to the theories API (title: "Communication Psychology").
4. **Profile** — `user_profile.get_profile_display()` returns `communication_psychology`: `unlocked_count`, `total_theories`, `communication_psychology_points`, `unlocked_theories`, `categories`.
5. **DNA / generator** — Video generation with `content_category` in `conspiracy`, `alternative_theories`, `religious_conspiracy`, or `theory` awards extra `communication_psychology_points` via `award_points_for_activity()` and triggers trophy checks.
6. **Trophies** — Seven walkthrough trophies: `comm_psych_first`, `comm_psych_five`, `comm_psych_ten`, `comm_psych_master_25`, `comm_psych_points_500`, `comm_psych_points_1k`, `comm_psych_points_5k`. Seed with:
   ```bash
   python scripts/seed_communication_psychology_trophies.py
   ```
7. **Shop** — Extra items in `_seed_shop_items()`: "Communication Psychology — 25 Theories", "Comm-Psych Theory Unlock Pack", "Framing & Influence Bundle", "Digital Power Pack", "Monetization & Control Pack" (category inventory).

## Trophies (walkthrough)

- **First Theory** — Unlock 1 theory  
- **Five Theories** — Unlock 5  
- **Ten Theories** — Unlock 10  
- **Master of 25** — Unlock all 25  
- **Comm-Psych 500 / 1K / 5K** — Earn 500 / 1000 / 5000 communication_psychology_points  

## Compendium (Rulebook V2.1)

- **10 wiki pages:** `compendium/page-1.html` … `page-10.html` (served at `/compendium/page-1.html` … `/compendium/page-10.html`) — 25 theories distributed across 10 pages. Access via **Trophies → Compendium V2.1** tab or directly `/compendium/`.
- **Unified points:** Viewing a compendium page (via `compendium-view-tracker.js`) POSTs to `/api/compendium/view` and awards **compendium_points** (15 per page). Point type is in unified system and trigger `compendium_view`.
- **APIs:** `GET /api/compendium/pages` — list of 10 pages; `POST /api/compendium/view` — body `{ "user_id", "page_number" }` awards points.

## User index and ID (account control)

- **GET /api/user/index** or **GET /api/users/me** — query `?user_id=` returns `user_id` and **user_index** (stable numeric index derived from user_id). Use for generation context and account control.
- **GET /api/user/account-control** — returns user_id, user_index, and profile summary for generator or account UI.

## Frontend usage

- **Profile:** Use `GET /api/user/profile/<user_id>/display`; response includes `communication_psychology` with unlocked theories and points. Render a "Communication Psychology" block with progress (e.g. 12/25) and list of unlocked theories.
- **Trophies page:** After seeding, `GET /api/trophies/definitions` (or equivalent) returns the new trophies; filter or label by category `communication_psychology`.
- **Starmap:** Flyer "Communication Psychology" can open the theories list (e.g. fetch `/vidgenerator/api/communication-psychology/theories`) or a dedicated page that lists theories and allows "Study" (POST study).
- **Shop:** Filter by category or search for "Communication Psychology" / "Comm-Psych" to show the new items; on purchase you can call `/api/communication-psychology/award` with amount/source if you want to grant comm-psych points for buying those items.
