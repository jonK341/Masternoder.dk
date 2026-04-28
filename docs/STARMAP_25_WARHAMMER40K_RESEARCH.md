# Star Map 25 — Warhammer 40,000 Research & Brainstorm

**Purpose:** Define the "First Starmap 25" as 25 investigation points across the Imperium. Each point is a star system (host star + planets) with canonical WH40K names. Users investigate points to earn game_points and unlock lore.

---

## 1. Warhammer 40K Galaxy Overview (Summary)

- The **Imperium of Man** divides the Milky Way into **five Segmentae Majoris**. Each has a Segmentum Fortress and Master of the Segmentum.
- **Segmentum Solar** (centre) — Fortress: **Mars**. Heart of the Imperium; contains Terra (Earth).
- **Segmentum Obscurus** (north) — Fortress: **Cypra Mundi**. Contains the Eye of Terror, Cadia (pre–M42).
- **Segmentum Tempestus** (south) — Fortress: **Bakka**.
- **Segmentum Pacificus** (west) — Fortress: **Hydraphur**.
- **Segmentum Ultima** (east) — Fortress: **Kar Duniash**. Largest; Ultramar, Macragge, many xenos borders.

Sectors contain sub-sectors (typically 2–8 systems within ~10 ly). Unclaimed space is wilderness/forbidden zones.

**First Founding:** The Emperor created 20 Space Marine Legions (Legiones Astartes), each tied to a Primarch and often to a homeworld. After the Horus Heresy, loyalist Legions were broken into Chapters; traitor Legions fled to the Eye of Terror.

---

## 2. The 25 Points — Host Star and Planets (Canonical Names)

Each of the 25 points is one **system**. Naming follows: **Host star/system name → primary world(s)**. Many WH40K sources name the planet rather than the star; we use the **system name** as the “host” and list **planets** as in lore.

| # | Point ID | Host Star / System | Segmentum | Planets (examples) | Life-bearing / Notable | Lore (short) |
|---|----------|--------------------|-----------|--------------------|------------------------|--------------|
| 1 | terra_sol | Sol | Solar | Mercury, Venus, Terra (Earth), Mars, Jupiter, Saturn, Uranus, Neptune | Terra, Mars | Holy Terra; Throneworld. Mars: Adeptus Mechanicus. |
| 2 | mars_sol | Sol (Mars) | Solar | (Mars as focus) | Mars | Forge World; Segmentum Solar fortress. |
| 3 | cypra_mundi | Cypra Mundi System | Obscurus | Cypra Mundi (capital) | Cypra Mundi | Segmentum Obscurus fortress. |
| 4 | hydraphur | Hydraphur System | Pacificus | Hydraphur (capital) | Hydraphur | Segmentum Pacificus fortress. |
| 5 | bakka | Bakka System | Tempestus | Bakka (capital) | Bakka | Segmentum Tempestus fortress. |
| 6 | kar_duniash | Kar Duniash System | Ultima | Kar Duniash (capital) | Kar Duniash | Segmentum Ultima fortress. |
| 7 | macragge | Macragge System | Ultima | Macragge, Calth, others (Ultramar) | Macragge | Ultramarines homeworld; capital of Ultramar. |
| 8 | fenris | Fenris System | Obscurus | Fenris | Fenris | Space Wolves homeworld; death world. |
| 9 | cadia | Cadian System | Obscurus | Cadia (destroyed M41) | Cadia | Cadian Gate; fell 999.M41. |
| 10 | baal | Baal System | Ultima | Baal Prime, Baal Secundus, Baal (main) | Baal | Blood Angels homeworld. |
| 11 | nocturne | Nocturne System | Ultima | Nocturne, its moons | Nocturne | Salamanders homeworld; volcanic. |
| 12 | medusa | Medusa System | Obscurus | Medusa | Medusa | Iron Hands homeworld; high gravity. |
| 13 | olympia | Olympia System | Obscurus | Olympia (destroyed) | Olympia | Iron Warriors (traitor) homeworld. |
| 14 | caliban | Caliban System | Obscurus | Caliban (destroyed) | Caliban | Dark Angels homeworld; lost. |
| 15 | chogoris | Chogoris System | Ultima | Chogoris (Mundus Planus) | Chogoris | White Scars homeworld. |
| 16 | barbarus | Barbarus System | Obscurus | Barbarus | Barbarus | Death Guard (traitor) homeworld; toxic. |
| 17 | chemos | Chemos System | Ultima | Chemos | Chemos | Emperor's Children (traitor) homeworld. |
| 18 | colchis | Colchis System | Obscurus | Colchis (destroyed) | Colchis | Word Bearers (traitor) homeworld. |
| 19 | nostramo | Nostramo System | Obscurus | Nostramo (destroyed) | Nostramo | Night Lords (traitor) homeworld. |
| 20 | prospero | Prospero System | Obscurus | Prospero (destroyed) | Prospero | Thousand Sons (traitor) homeworld. |
| 21 | cthonia | Cthonia System | Solar | Cthonia (destroyed) | Cthonia | Luna Wolves / Sons of Horus; near Terra. |
| 22 | deliverance | Lycaeus System | Ultima | Deliverance (moon), Lycaeus (primary) | Deliverance | Raven Guard; Deliverance is the moon. |
| 23 | nuceria | Nuceria System | Ultima | Nuceria | Nuceria | World Eaters (Angron); gladiator world. |
| 24 | inwit | Inwit System | Solar | Inwit (ice world) | Inwit | Imperial Fists (Dorn) upbringing. |
| 25 | ryza | Ryza System | Ultima | Ryza (Forge World) | Ryza | Major Forge World; plasma tech. |

---

## 3. Brainstorm — Design Choices

- **Host star naming:** WH40K often uses the main planet name for the “system” (e.g. “Macragge System”). We keep that: host = system name, planets = listed bodies. For Sol we explicitly use Sol as host and Terra/Mars as key planets.
- **Life-bearing:** The “life-bearing” or notable world is the main planet (or moon, e.g. Deliverance) we list.
- **Destroyed worlds:** Cadia, Caliban, Olympia, Colchis, Nostramo, Prospero, Cthonia are destroyed or lost in lore; they remain as **investigation points** for history/lore.
- **Segmentum balance:** Solar 3, Obscurus 8, Tempestus 1, Pacificus 1, Ultima 12 — reflects Ultima’s size and Obscurus’ importance (Eye of Terror, many Legion homeworlds).
- **Points to investigate:** Each of the 25 points can be “investigated” once per user; investigating awards **game_points** (e.g. 10–15 per point) and unlocks the lore snippet.
- **Integration:** Same specials as existing star map (run_verification, run_dna_test, view_star_map); 25-map is an extended layer with investigation and monitoring screens.

---

## 4. 25 Investigation Points — Checklist (for UI/API)

1. Terra (Sol)  
2. Mars (Sol)  
3. Cypra Mundi  
4. Hydraphur  
5. Bakka  
6. Kar Duniash  
7. Macragge  
8. Fenris  
9. Cadia  
10. Baal  
11. Nocturne  
12. Medusa  
13. Olympia  
14. Caliban  
15. Chogoris  
16. Barbarus  
17. Chemos  
18. Colchis  
19. Nostramo  
20. Prospero  
21. Cthonia  
22. Deliverance (Lycaeus)  
23. Nuceria  
24. Inwit  
25. Ryza  

---

## 5. Tech Spec (Implementation)

- **Data:** `data/star_map_25.json` — array of 25 systems with `id`, `name`, `segmentum`, `planets`, `life_bearing`, `info`, `point_value`, `specials`.
- **API:**  
  - `GET /api/star-map/25` — full 25-point map.  
  - `POST /api/star-map/25/investigate` — body `{ "user_id", "point_id" }` — award game_points, record investigation.  
  - `GET /api/star-map/25/status?user_id=` — which of the 25 the user has investigated.
- **Screens:**  
  - **Star Map 25 Monitor** — dashboard listing all 25 points, status (investigated / not), total points earned, link to main star map and Trophies.  
  - Trophies Star Map tab links to Star Map 25 Monitor. Hunter game has Star Map 25 tab. Shop has starmap25 category (boosters, gametime, trophies). Effect clusters: starmap25_investigate, starmap25_view. Optional: Trophies Star Map tab can link to “25 Starmap” and show progress (e.g. 12/25 investigated).

---

## 6. Sources (WH40K)

- Segmentum: *Battlefleet Gothic Rulebook*, *Dark Heresy Core Rulebook*, Warhammer 40k Wiki (Fandom), Lexicanum.  
- Homeworlds: Lexicanum/Fandom articles per Primarch and Legion; First Founding and traitor Legion lore.  
- Fortress worlds: Cypra Mundi, Hydraphur, Bakka, Kar Duniash, Mars — standard Segmentum fortress list.

*Document version: 2026-03-04. For Masternoder.dk 25-point starmap feature.*
