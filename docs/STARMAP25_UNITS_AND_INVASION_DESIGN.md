# Star Map 25 — Units, Special Units & Invasion (design synthesis)

**Purpose:** One coherent design for adding **units** and **special units** that **invade** the star systems we map, with **AI and agents** for content, balance, and map creation. Fits the existing Star Map 25 (investigate → game_points, segmentums, WH40K theme).

---

## 1. Core idea in one sentence

Users **deploy units** (and optional **special units**) to **invade** star systems on the map; invasion runs **after or alongside** investigation, grants bonus rewards and “secured” state, and **AI/agents** drive unit lore, invasion narratives, and optional procedural map events.

---

## 2. Two-layer model (investigate → invade)

Keep current **investigate** as the first step; add **invasion** as a second, optional layer on the same 25 systems.

| Layer | Action | Reward | Who can do it |
|-------|--------|--------|----------------|
| **1. Investigate** | Scout the system (existing) | game_points once, unlock lore | Any user, once per point |
| **2. Invade** | Deploy units to secure/pacify | Bonus game_points, “secured” badge, optional extra lore | User who has investigated that point and has units |

**Why two layers:** No change to existing progress; invasion is an **extra** loop that uses the same map and fits “we are mapping the systems” → “we are invading them.”

---

## 3. Units and special units

### 3.1 Units (standard)

- **Definition:** Reusable “troop type” the user can assign to a star system. Not consumed one-shot; either **deployed** (one deployment per system) or **pool** (spend from pool per invasion).
- **Suggested types (WH40K-flavoured):**
  - **Guard** — baseline; good for any system.
  - **Fleet** — bonus on naval/fortress worlds (e.g. Hydraphur, Bakka).
  - **Scout** — bonus on first investigation or uncharted; faster “intel.”
  - **Garrison** — hold a system; reduces “rebellion” or unlocks repeat bonus (if you add that later).

**Data:** One source of truth, e.g. `data/starmap25_units.json` (or a `units` block in `star_map_25.json`): `id`, `name`, `description`, `icon`, `tags` (e.g. `["ground","fortress"]`), optional `strength` / `bonus_segmentum` for modifiers.

### 3.2 Special units

- **Definition:** Rare or elite types with **stronger effects** or **special rules** (e.g. double bonus on fortress, unlock hidden lore, or one-time “conquer” effect).
- **Suggested types:**
  - **Space Marines** — bonus on legion homeworlds (Fenris, Baal, Macragge, etc.).
  - **Mechanicus** — bonus on Forge Worlds (Mars, Ryza).
  - **Inquisition** — bonus on Terra / Cypra Mundi; unlock “classified” lore snippet.
  - **Assassin** — one-time “decapitation” on one system: huge bonus, then unit exhausted for that system.

**Data:** Same file or `data/starmap25_special_units.json`: `id`, `name`, `description`, `icon`, `special_rule` (e.g. `bonus_fortress`, `unlock_lore`, `one_time`), `required_investigate: true`.

**Acquisition:** Special units can be earned (e.g. “Complete Segmentum Solar” → unlock Mechanicus) or from Shop (starmap25 category), so Shop and progression stay linked.

---

## 4. Invasion mechanic (synthesis)

- **Trigger:** User has **investigated** a point and has at least one **unit** (and optionally one **special unit**) to deploy.
- **Action:** User selects a system (from monitor or game tab) and chooses “Invade” with chosen unit + optional special unit.
- **Result:**
  - System gets **invaded** once per user (like investigate: one-time per user per point).
  - **Bonus game_points** (e.g. +5 or +10) depending on unit/special and system tags (e.g. Fleet + Hydraphur = extra).
  - System marked **secured** in UI (badge / different color).
  - Optional: **AI-generated invasion blurb** (one short sentence) stored per user per point for “Your invasions” view.
- **Failure / risk (optional):** You can add “invasion can fail” with a simple roll (e.g. 80% success) so special units or items improve chance; analytics_agent can then tune rates.

---

## 5. Where AI and agents fit

| Role | Content / system | Who |
|------|------------------|-----|
| **Unit and special-unit copy** | Names, short descriptions, “special_rule” flavor text. | **content_generator_agent** |
| **Invasion narrative** | Per invasion: one-line “After a brutal void battle, the 3rd Fleet secured Hydraphur.” | **content_generator_agent** (or LLM on demand when user invades) |
| **Map creation / events** | New **systems** (e.g. 5 more “expedition” systems), or **events** (“Ork incursion at X — deploy Guard for bonus”). | **content_generator_agent** + data pipeline; learning_agent can suggest which events to add from engagement. |
| **Strategy and balance** | “Best unit for fortress worlds,” “Recommended order: Terra → Mars → …” | **learning_agent** (from outcomes / win rates if you add failure). |
| **Analytics and tuning** | Invasion success rate, most-used units, which systems are invaded least. | **analytics_agent**; feed into balance and map-creation tasks. |

**Map creation with AI:**  
- **Option A (static):** AI generates a **one-off batch** of new systems (names, segmentum, lore, point_value) → you review and add to `star_map_25.json` or a second map “Star Map 30” (25 + 5).  
- **Option B (events):** Same 25 systems; AI generates **temporary events** (e.g. “Revolt on Ryza — deploy Mechanicus for 2× bonus this week”) stored in `data/starmap25_events.json`; agents propose and you approve.  
- **Option C (procedural):** User clicks “Generate new system”; LLM returns name + lore + segmentum; user can “add to my map” (personal or global after moderation).  

Start with **Option B** for minimal schema change; add A or C later.

---

## 6. Best solution summary (recommended path)

1. **Keep** investigate exactly as is (one-time game_points + lore per system per user).
2. **Add** `data/starmap25_units.json` and `data/starmap25_special_units.json` (or one file with `units` + `special_units`).
3. **Add** invasion state per user per point (e.g. in `star_map_25_investigations.json` as `invaded_ids` and optional `invasion_blurb` per point).
4. **New API:**  
   - `GET /api/star-map/25/units` — list units and special units.  
   - `POST /api/star-map/25/invade` — body `{ "user_id", "point_id", "unit_id", "special_unit_id" (optional) }` → validate (investigated, has unit), apply bonus game_points, mark secured, store blurb (e.g. from LLM).
5. **User roster:** Either **fixed roster** (everyone has Guard, Fleet, Scout; specials from Shop/quests) or **pool** (earn units via game_points / Shop); start with fixed roster for simplicity.
6. **AI:**  
   - **content_generator_agent:** Unit/special-unit descriptions; optional invasion blurbs (batch or on-invade).  
   - **learning_agent:** Strategy hints, “best unit for this system.”  
   - **analytics_agent:** Invasion stats, suggest balance and events.  
7. **Map creation:** Start with **events** (Option B) on the same 25 systems; later add AI-proposed new systems (Option A/C) if you want more map content.

---

## 7. Data shape (minimal)

**Units (example):**
```json
{
  "units": [
    { "id": "guard", "name": "Imperial Guard", "description": "Baseline deployment.", "icon": "🪖", "tags": ["ground"] },
    { "id": "fleet", "name": "Segmentum Fleet", "description": "Naval superiority.", "icon": "🚀", "tags": ["naval"], "bonus_tags": ["fortress"] }
  ],
  "special_units": [
    { "id": "marines", "name": "Space Marines", "description": "Elite; bonus on Legion worlds.", "icon": "🦅", "special_rule": "bonus_legion_homeworld" }
  ]
}
```

**Invasion state (per user):**  
In `star_map_25_investigations.json` or new `star_map_25_invasions.json`:  
`{ "user_id": { "invaded_ids": ["terra_sol", "hydraphur"], "blurbs": { "terra_sol": "The 3rd Fleet secured Terra approach." } } }`

---

## 8. Buildup mechanism (units + buildings → generate points)

Users **build buildings** and **deploy units** on **planets** in systems they have already **investigated**. Each building and each deployed unit **generates game_points per day**. Users **collect** to add those points to their balance.

### 8.1 Data

- **`data/starmap25_buildings.json`** — Building types: `id`, `name`, `description`, `icon`, `points_per_day`, `build_cost` (game_points), `tags`, optional `bonus_on_tags` (e.g. forge → extra on Forge Worlds).
- **`data/starmap25_units.json`** — Units and special_units: `id`, `name`, `icon`, `points_per_day`, `deploy_cost`, optional `bonus_tags` + `bonus_points_per_day` when deployed on matching systems.
- **`data/starmap25_buildup.json`** — Per-user state: `users[user_id].placements[]` (each: `point_id`, `planet`, `type` "building"|"unit", `id`, `at` ISO timestamp), `users[user_id].last_collect_ts`.

### 8.2 Rules

- **Build:** User must have **investigated** the system; **planet** must be in that system’s `planets` list. Pay **build_cost** (game_points); one building per building type per planet (per `max_per_planet` in data).
- **Deploy:** Same: investigated system, valid planet. Pay **deploy_cost** if any. Multiple units can be deployed (e.g. one unit per planet).
- **Point generation:** For each placement, `points_per_day` (and bonus if point’s tags match `bonus_on_tags` / `bonus_tags`) × days since **last_collect_ts** (or since `at` if never collected). Sum = **pending_points**.
- **Collect:** POST collect → add **pending_points** to user’s **game_points**, set **last_collect_ts** = now.

### 8.3 API

| Method | Path | Purpose |
|--------|------|--------|
| GET | `/api/star-map/25/buildings` | List building types (points_per_day, build_cost). |
| GET | `/api/star-map/25/units` | List units and special_units (points_per_day, deploy_cost). |
| GET | `/api/star-map/25/buildup?user_id=` | User’s placements, last_collect_ts, **pending_points**. |
| POST | `/api/star-map/25/build` | Body: `user_id`, `point_id`, `planet`, `building_id`. Build on planet (deduct build_cost). |
| POST | `/api/star-map/25/deploy` | Body: `user_id`, `point_id`, `planet`, `unit_id`. Deploy unit (deduct deploy_cost). |
| POST | `/api/star-map/25/collect` | Body: `user_id`. Award pending_points to game_points, update last_collect_ts. |

### 8.4 System levels and daily reset

- **Levels:** Each of the 25 systems has a **level 1–5** (Scouted → Established → Fortified → Bastion → Dominion). Level is computed from placements in that system: 1 = investigated; 2 = 1+ building; 3 = 3+ buildings or 2+ units; 4 = 5+ placements; 5 = 8+ placements.
- **Structures by level:** Buildings have **min_level** (1–5). Higher-level structures (Orbital Fortress, Cathedral, Primarch's Gate) are harder to obtain and have **daily_reset_bonus**: 2× points for 12h after **daily reset** (midnight UTC). Daily reset makes them a must-have for maximum yield.
- **API:** `GET /api/star-map/25/levels?user_id=` returns **system_levels**, **level_rules**, **next_daily_reset_utc**, **in_daily_reset_bonus_window**.

### 8.5 Buildings (examples in data)

Outpost, Listening Post (level 1), Barracks (2), Forge Shrine, Naval Dock (3), Sanctum (4), Orbital Fortress (4, daily_reset_bonus), Cathedral, Primarch's Gate (5, daily_reset_bonus).

### 8.6 Units (examples in data)

Guard (1/day, free), Fleet (2/day + 1 on fortress, 5), Scout (1/day, 3), Garrison (2/day, 8). Special: Space Marines (3+2 on legion, 15), Mechanicus (3+2 on forge, 18), Inquisition (4+1 on throne/fortress, 20).

---

## 9. References

- Existing: `data/star_map_25.json`, `backend/routes/star_map_routes.py`, `docs/STARMAP_25_TOP10_IDEAS.md`, `docs/STARMAP_25_50_PROJECTS.md`.
- Buildup data: `data/starmap25_buildings.json`, `data/starmap25_units.json`, `data/starmap25_buildup.json`, `data/starmap25_system_levels.json`, `data/agent_calendar.json`.
- Agents: `content_generator_agent`, `learning_agent`, `analytics_agent` (Generator “Assign 50 Star Map projects”).

This doc is the **synthesis** for units, special units, invasion, and **buildup** (buildings + units on planets that generate game_points over time; collect to add to balance).
