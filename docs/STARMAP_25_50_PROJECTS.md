# Star Map 25 — 50 Implementation Projects

**Purpose:** Fifty concrete projects for agents and developers to implement on the Star Map 25 (Imperium Investigation Grid). Use as a backlog: assign to `content_generator_agent`, `learning_agent`, `analytics_agent`, or manual dev.

**Assignment (AIs + agents):** Each project has a `suggested_agent` in `data/starmap25_agent_projects.json`. To assign all 50 to the three agents at once: **Generator → "Assign 50 Star Map projects to agents"** (calls `POST /api/debugger/tasks/assign-starmap50`). Alternatively call `POST /api/debugger/tasks/assign-rulebook-todo` with `{ "only_starmap25": true, "use_starmap50": true }` or `{ "only_starmap25": true, "max_tasks": 50 }`.

**References:** `data/star_map_25.json`, `data/starmap25_agent_projects.json`, `backend/routes/star_map_routes.py`, `backend/routes/debugger_agent_tasks_routes.py`, `starmap25/index.html`, `STARMAP25_TODO_25.md`, `STARMAP_25_TOP10_IDEAS.md`.

---

## Data & content (1–10)

| # | Project | Scope | Notes |
|---|---------|--------|--------|
| **1** | Validate `star_map_25.json` schema | Ensure every point has `id`, `name`, `host_star`, `segmentum`, `planets`, `life_bearing`, `life_label`, `info`, `point_value`, `icon`, `lore`, `index`. Add missing fields or defaults. | `data/star_map_25.json` |
| **2** | Add `coordinates` to each point | Add optional `x`, `y`, `z` (or `ra`, `dec`, `dist`) for 3D map placement; derive from segmentum if needed. | `data/star_map_25.json` |
| **3** | Add `tags` per point | e.g. `["fortress", "legion_homeworld", "traitor"]` for filtering and badges on UI. | `data/star_map_25.json` |
| **4** | Add `unlock_requirement` (optional) | Some points gated by "investigate Terra first" or segmentum order; document in data, implement in API later. | `data/star_map_25.json` |
| **5** | Extended lore paragraphs | For each of 25 points, add a second field `lore_long` (2–4 sentences) for "Read more" on monitor. | `data/star_map_25.json` |
| **6** | Canon links | Add `lexicanum_url` or `wh40k_wiki` per point for "Learn more" link. | `data/star_map_25.json` |
| **7** | Segmentum metadata | Add `data/segmentums.json` or a `segmentums` block in `star_map_25.json`: name, color, description, fortress_point_id. | New file or extend `star_map_25.json` |
| **8** | Point icons as assets | Ensure each `icon` has a corresponding emoji or sprite; add fallback icon list. | `starmap25/`, `static/img/` |
| **9** | Localization keys | Add `name_key`, `info_key`, `lore_key` for i18n; keep current en as default. | `data/star_map_25.json` |
| **10** | Version and changelog | Add `version`, `changelog` to `star_map_25.json` and expose via API for "What's new" on monitor. | `data/star_map_25.json`, `star_map_routes.py` |

---

## API (11–20)

| # | Project | Scope | Notes |
|---|---------|--------|--------|
| **11** | GET `/api/star-map/25/point/<id>` | Single-point detail by id; 404 if not found. | `star_map_routes.py` |
| **12** | GET `/api/star-map/25?segmentum=Ultima` | Filter 25-point list by segmentum query param. | `star_map_routes.py` |
| **13** | GET `/api/star-map/25/segmentums` | Return list of segmentums with point count and fortress id. | `star_map_routes.py` |
| **14** | POST investigate idempotency | Return same `points_earned` and success if user already investigated; no double award. | `star_map_routes.py` (verify current behavior) |
| **15** | Rate limit investigate | Max N investigations per user per hour (e.g. 10) to avoid abuse; return 429 with Retry-After. | `star_map_routes.py` |
| **16** | GET `/api/star-map/25/leaderboard` | Top users by `total_points_earned` or investigations count (optional, anonymized). | `star_map_routes.py`, investigations data |
| **17** | ETag / If-None-Match for map | Return 304 when map JSON unchanged; reduce payload. | `star_map_routes.py` |
| **18** | Bulk status: POST body `user_ids[]` | Return status for multiple users in one call for admin/analytics. | `star_map_routes.py` |
| **19** | OpenAPI spec for Star Map 25 | Document all Star Map 25 endpoints in `docs/api/star-map-25.yaml` or existing OpenAPI. | `docs/` |
| **20** | Health check for investigations file | GET `/api/star-map/25/health`: writable, readable, last_modified. | `star_map_routes.py` |

---

## Monitor page UI (21–30)

| # | Project | Scope | Notes |
|---|---------|--------|--------|
| **21** | Group cards by Segmentum | On monitor grid, group 25 cards under headers Solar, Obscurus, Pacificus, Tempestus, Ultima. | `starmap25/index.html` |
| **22** | Responsive grid | 25 columns → 5 cols on tablet, 2–3 on mobile; keep cards readable. | `starmap25/index.html` CSS |
| **23** | "Read full lore" expand | Click to expand `lore_long` in a modal or inline expand. | `starmap25/index.html` |
| **24** | Filter by segmentum/tags | Dropdown or chips: "Show only Ultima", "Fortress worlds only". | `starmap25/index.html` |
| **25** | Sort options | Sort by name, point_value, segmentum, investigated first/last. | `starmap25/index.html` |
| **26** | Keyboard navigation | Arrow keys and Enter to focus and activate Investigate on cards. | `starmap25/index.html` |
| **27** | Share progress | "Share my progress" copies link or image (e.g. "12/25 investigated"). | `starmap25/index.html` |
| **28** | Print-friendly view | CSS print styles: hide nav, show grid and progress. | `starmap25/index.html` |
| **29** | Dark/light theme toggle | Use CSS variables; persist preference in localStorage. | `starmap25/index.html`, `static/css/` |
| **30** | Loading skeletons | Replace "Loading…" with 25 card-shaped skeletons. | `starmap25/index.html` |

---

## 3D map (31–35)

| # | Project | Scope | Notes |
|---|---------|--------|--------|
| **31** | Three.js scene with 25 spheres | One sphere per point; position by segmentum or coordinates. | `starmap25/index.html` or separate JS |
| **32** | Orbit controls and zoom | Camera orbit, zoom to point on click. | Three.js |
| **33** | Labels on hover/click | Show point name and "Investigate" on hover. | Three.js / CSS2DRenderer or sprite |
| **34** | Segmentum colors | Color spheres or connectors by segmentum. | Three.js materials |
| **35** | "Focus on point" button | From grid card, scroll/zoom 3D view to that point. | `starmap25/index.html` |

---

## Shop & economy (36–40)

| # | Project | Scope | Notes |
|---|---------|--------|--------|
| **36** | Starmap25 shop category | Ensure `starmap25` category exists with boosters (2× points 1h/6h/24h), +30m/+2h gametime. | `shop/`, shop API |
| **37** | Starmap25 trophies in shop | Terra, Segmentum Clear, Full Clear, Lore Master purchasable or unlock-only; wire to trophy system. | Shop + trophies |
| **38** | Apply booster to investigate | When 2× booster active, award double `point_value` for that investigation. | `star_map_routes.py`, profile/effects |
| **39** | Shop deep link | From monitor, "Get boosters" links to `/shop?category=starmap25`. | `starmap25/index.html` |
| **40** | Game points display on monitor | Show current user `game_points` total next to "Total points earned" (from profile API). | `starmap25/index.html` |

---

## Trophies & quests (41–45)

| # | Project | Scope | Notes |
|---|---------|--------|--------|
| **41** | Trophy: Terra (first investigation) | Award when first investigation is `terra_sol`; show on Trophies page. | Backend trophies, `star_map_routes.py` or quests |
| **42** | Trophy: Segmentum Clear | Award when all points in one segmentum investigated; one trophy per segmentum. | Backend |
| **43** | Trophy: Full Clear (25/25) | Award when `investigated_count === 25`. | Backend |
| **44** | Trophy: Lore Master | Award when all 25 lore entries unlocked (same as Full Clear or separate "read all" logic). | Backend |
| **45** | Daily/weekly quests | "Star Map Scout" (1/day), "Segmentum Explorer" (5/week); complete on investigate; reward game_points or badge. | `user_engagement.py`, quests API |

---

## Analytics & agent (46–50)

| # | Project | Scope | Notes |
|---|---------|--------|--------|
| **46** | Log investigate events | Log each investigate to `logs/starmap25_investigations.jsonl` (user_id, point_id, ts) for analytics. | `star_map_routes.py` |
| **47** | Agent tool: get_star_map_25_status | MCP or agent API: input user_id, return investigated_ids and total_points_earned. | Agent routes / MCP |
| **48** | Agent tool: investigate_point | Agent can call investigate on behalf of user (with auth); idempotent. | Agent routes |
| **49** | Generator "Assign 25" includes starmap | When "Assign 25 tasks to agents" runs, include up to N starmap tasks (e.g. "expand lore for point X"). | `generator/index.html`, agent assignment |
| **50** | Dashboard widget | On main dashboard, small widget: "Star Map 25: X/25 investigated, Y points earned" with link to monitor. | Dashboard page |

---

## Quick reference

- **Data:** `data/star_map_25.json`, `data/star_map_25_investigations.json`
- **API:** `backend/routes/star_map_routes.py` — GET/POST under `/api/star-map/25*`
- **UI:** `starmap25/index.html` (Monitor), Game tab "Star Map 25", Trophies Star Map tab, Shop category `starmap25`
- **Docs:** `STARMAP25_TODO_25.md`, `STARMAP_25_TOP10_IDEAS.md`, `STARMAP_25_WARHAMMER40K_RESEARCH.md`

*Document version: 2026-03-18. Star Map 25 — 50 projects for agent and dev implementation.*
