# Star Map 25 — Top 10 Ideas Recap

**Purpose:** Recap the core Star Map 25 concept and top 10 design/UX ideas for the 25-point Imperium investigation grid (Warhammer 40,000 themed).

---

## 1. **25 investigation points = one per system**

Each of the 25 points is a star system (host star + planets) with canonical WH40K names. Users “investigate” a point once per account to earn `game_points` and unlock a lore snippet. Clear 1–25 progression.

---

## 2. **Five Segmentae Majoris**

Map is organized by the Imperium’s five segmentums: Solar, Obscurus, Tempestus, Pacificus, Ultima. Each has a Segmentum Fortress (e.g. Mars, Cypra Mundi, Hydraphur, Bakka, Kar Duniash). UI can group points by segmentum and show “Segmentum Clear” trophies.

---

## 3. **One-time reward per point per user**

Each of the 25 points is investigable once per user. Investigating awards a fixed `game_points` value (e.g. 10–15) and unlocks the lore entry. Prevents farming; encourages completion.

---

## 4. **Shop category “starmap25”**

Shop has boosters (e.g. 2× investigation points for 1h/6h/24h), extra game time (e.g. +30m, +1h, +2h for Hunter + Star Map 25), and trophies (Terra, Segmentum Clear, Full Clear, Lore Master). All under category `starmap25`.

---

## 5. **Star Map 25 Monitor page**

Dedicated dashboard at `/vidgenerator/starmap25/`: progress (X/25), total points earned, grid of 25 cards with “Investigate” and lore. Trophies page links to “Star Map 25 Monitor”.

---

## 6. **Hunter game integration**

Hunter game has a “Star Map 25” tab: progress, points earned, specials (View Star Map, Run Verification, Run DNA Test), quick-investigate grid, link to full monitor. Effect clusters include `starmap25_investigate`, `starmap25_view`.

---

## 7. **API surface**

- `GET /api/star-map/25` — full 25-point map (ids, names, segmentum, lore, point_value).
- `GET /api/star-map/25/status?user_id=` — `investigated_ids`, `total_points_earned`.
- `POST /api/star-map/25/investigate` — body `{ "user_id", "point_id" }` — one-time award and record.

---

## 8. **Data: `data/star_map_25.json`**

Single source of truth: array of 25 systems with `id`, `name`, `host_star`, `segmentum`, `planets`, `life_bearing`, `info`, `point_value`, `lore`, `icon`. Investigations stored in `data/star_map_25_investigations.json` (or DB) per user.

---

## 9. **Trophies and achievements**

Trophies: “Terra” (first investigation), “Segmentum Clear” (all 5 fortresses in one segmentum), “Full Clear” (all 25), “Lore Master” (all 25 lore entries). Visible in Trophies page and profile.

---

## 10. **Optional: 3D map and coordinated grid**

Future: Three.js scene with 25 points as spheres in a galactic layout; orbit/rotate. Monitor panel: 25-cell grid (1–25) with investigated (e.g. gold) vs not, for quick status.

---

*See also: STARMAP_25_WARHAMMER40K_RESEARCH.md, HUNTERS_STAR_MAP_IMPLEMENTATION_SUMMARY.md (sect. 10).*
