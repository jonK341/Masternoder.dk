# Rulebook readers & compendium progress

**Last updated:** 2026-06-17

This document describes every **reader surface** in the platform: where rulebooks and compendium content are shown, how reading progress is recorded, and which APIs agents should use.

**Related:** [COMPENDIUM_RULEBOOK_V1_V15.md](./COMPENDIUM_RULEBOOK_V1_V15.md) · [RULEBOOK_CANON.md](./RULEBOOK_CANON.md) · [RULEBOOK_AGENT_CONTEXT.md](./RULEBOOK_AGENT_CONTEXT.md) · [RULEBOOK_TODO_25.md](./RULEBOOK_TODO_25.md)

---

## Catalog overview (V1–V16)

| Version | Reader URL | Data file | Points page # |
|---------|------------|-----------|---------------|
| V3 Comm. Psych | `/compendium/page-1` … `page-10` | `communication_psychology_theories.json` | 1–10 |
| V2 Hunters | `/compendium/hunters-rulebook` | `hunters_rulebook_v2.json` | 11 |
| V1 Core | `/compendium/rulebook-v1` | `rulebook_v1_core.json` | 12 |
| V3.2 Protocols | `/compendium/rulebook-v3-2` | `rulebook_v3_2_systemic_protocols.json` | — (browse only) |
| V4–V14 | `/compendium/rulebook-v4` … `v14` | `rulebook_v4_*.json` … `v14_*.json` | 13–23 |
| V15 Index | `/compendium/` | `rulebook_index_v15.json` | 24 |
| V16 Sync | `/compendium/rulebook-v16` | `rulebook_v16_sync.json` | 25 |

**Master index API:** `GET /api/rulebooks/index` (includes V16 entry).

---

## Calm reading system (2026-06-17)

Steady, accessible reading across the site:

| Entry | Where |
|-------|--------|
| **Nav → Library** | All pages with toolbar → `/compendium/?calm=1` |
| **Floating launcher** | Bottom-right on non-compendium pages (`reader-launcher.js`) |
| **Continue card** | `/compendium/` index — resume last page or next unread |
| **Reading chrome** | Sticky progress bar + prev/next footer on every compendium page |
| **Calm mode** | Serif typography, soft palette, optional Focus (hides chrome) |
| **Keyboard** | ← → prev/next · Esc exit focus |

Assets: `static/css/calm-reader.css` · `static/js/calm-reader.js` · `static/js/reader-launcher.js`

---

## Reader surfaces

### 1. Compendium hub (`/compendium/`)

- **File:** `compendium/index.html`
- **Purpose:** Grid of all volumes; inline hash preview (`#rulebook-v9`).
- **Progress:** Index itself is page **24** (V15 master index) when opened directly; hash previews do not auto-award.
- **Tracker:** `static/js/compendium-view-tracker.js` on child pages only.

### 2. Shared rulebook viewer (`/compendium/rulebook-v*`, `rulebook-v3-2`)

- **File:** `compendium/rulebook-viewer.html`
- **API:** `GET /api/rulebooks/<version>` (`v1`, `v3.2`, `v16`, …)
- **Renders:** rules, clusters, spells, agent_prompt, tech_spec, user_guide, manual, sync_domains (V16).
- **Tracker:** awards compendium points on load via `compendium-view-tracker.js`.

### 3. Communication Psychology pages (`/compendium/page-N`)

- **Files:** `compendium/page-1.html` … `page-10.html`
- **Tracker:** page number = URL segment (1–10).

### 4. Hunters rulebook page (`/compendium/hunters-rulebook`)

- **File:** `compendium/hunters-rulebook.html`
- **Also available via API:** `GET /api/game/hunters/rulebook`
- **Tracker:** page **11**.

### 5. Trophies tabs (`/trophies`)

| Tab | Loader | Source |
|-----|--------|--------|
| **Rulebook** | `loadRulebook()` | `GET /api/game/hunters/rulebook` (V2 spells) |
| **Compendium V2.1** | `loadCompendium()` | `GET /api/compendium/pages` → links to full readers |

### 6. Aggregator progress reader (`/aggregator`)

- **UI:** `#agg-progress-reader` in `aggregator/index.html`
- **Script:** `static/js/aggregator-monitor-game.js` → `refreshProgressReader()`
- **Shows:** battle stats, hunter level/XP, monitor moves, **compendium pages read**, **story read %**.

### 7. Game Hub story reader (`/trophies/#stories`, frontpage Story tab)

- **Mark read:** `POST /api/game-hub/stories/read` `{ "story_id": "…" }`
- **Progress:** `GET /api/game-hub/stories/progress`
- **Overview:** `GET /api/game-hub/overview` → `tabs.story`

---

## Progress & points APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/compendium/view` | POST | Award **15 compendium_points** per page (1–25) |
| `/api/compendium/pages` | GET | Unified page list for Trophies + agents |
| `/api/user/compendium/progress` | GET | `pages_read`, `total_read`, `completion_pct` |
| `/api/rulebooks/index` | GET | V1–V16 catalog with `url_path` |
| `/api/rulebooks/<version>` | GET | Full rulebook JSON |
| `/api/rulebooks/agent-context` | GET | Aggregated agent_prompt / tech_spec / manual |
| `/api/game-hub/stories/progress` | GET | Hunter story read count & continue CTA |

**Identity:** All readers use `game_user_id` from session, body/query, or `localStorage`.

**Sync:** Successful compendium views call `record_domain_sync('compendium')` (see V16 rulebook).

---

## Agent usage

1. **Help users find rules:** cite `user_guide` from `GET /api/rulebooks/agent-context?format=prompt`.
2. **Tool routing:** use `tech_spec` fields; shop questions → V9; sync questions → V16.
3. **Nudge unread content:** `GET /api/user/compendium/progress` → suggest next page from `/api/compendium/pages`.
4. **Story continuity:** `GET /api/game-hub/stories/progress` → `continue_story` + link `/trophies/#stories`.

---

## Deploy

```powershell
python scripts/deploy.py compendium --ask-pass
```

Manifest **`compendium`** uploads: compendium HTML, rulebook data JSON, `rulebook_routes.py`, `compendium_routes.py`, `compendium-view-tracker.js`, and related static assets.

Also included in **`trophies`** / **`game_hub`** when those UIs change.

---

## Discord cross-road (M8)

Compendium is in the daily affiliate rotator (#57) at `/compendium/?calm=1`. Reading progress does not yet emit Discord events — planned: 25/25 pages milestone → `platform_news` + optional Discord post. See [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md).

---

## Maintenance checklist

- [ ] `data/rulebook_index_v15.json` lists every volume including V16
- [ ] `GET /api/compendium/pages` matches compendium index grid
- [ ] `compendium-view-tracker.js` page map matches pages API (1–25)
- [ ] `COMPENDIUM_RULEBOOK_V1_V15.md` documents V16 sync section
- [ ] Trophies Compendium tab text says V1–V16

See [RULEBOOK_TODO_25.md](./RULEBOOK_TODO_25.md) for the full 25-task assignment table.
