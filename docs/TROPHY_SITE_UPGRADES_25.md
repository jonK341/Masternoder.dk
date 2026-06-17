# Trophy Site — 25 New Features & Upgrades Plan

Active upgrade plan for the Trophy site (`/trophies`, served from `trophies/index.html`,
mirrored to `vidgenerator/trophies/index.html`, routed by `backend/routes/trophies_routes.py`).

**Status:** Planning
**Owner:** TBD
**Last updated:** 2026-06-04

## Context (current state)

- Page tabs today: **Table**, **Unlocked**, **Locked**, a **category** `<select>`
  (generation, achievements, battle, points, social, content, milestones, special),
  plus **Star Map**, **Comm. Psychology**, **Rulebook**, **Compendium V2.1**,
  **Effect Clusters**, **Stories**.
- Trophies come from a client-side `TROPHY_DEFINITIONS` map (~63 trophies, 7 categories,
  rarities: common / rare / epic / legendary) merged with backend data via
  `GET /api/trophies/list`, `GET /api/game/achievements`, and `GET /api/battle/pvp/trophies`.
- Stats header: Total / Unlocked / Locked / Trophy Points. No progress, no notifications,
  no per-trophy detail, no leaderboard, no sharing.
- The page already loads the shared navigation toolbar, unified point counters, and the
  Intelligence widget.

## Goals

1. Make the trophy site feel alive (progress, notifications, celebration).
2. Make every UI action agent-achievable (parity per `docs/PROJECT_RETHINK.md`).
3. Move trophy definitions to a single backend source of truth so the page, agents, and
   the generator stay in sync.
4. Add social/competitive surface (leaderboards, sharing, comparison).

---

## Phase 1 — Foundation & Quick Wins (Features 1–8) ✅ DONE (2026-06-04)

- [x] **1. Single backend source of truth for trophy definitions.**
  Definitions moved to `data/trophy_definitions.json` (63 trophies) and served from
  `GET /api/trophies/definitions`. `GET /api/trophies/list` now merges JSON (canonical) +
  DB + legacy; client `TROPHY_DEFINITIONS` is offline fallback only.

- [x] **2. Per-trophy progress bars.**
  Added `progress_metric` / `progress_target` to each definition; the page computes current
  values from `GET /api/points/all` and renders a progress bar in the requirement cell of
  locked rows (e.g. "7 / 10"). Honest: only known metrics show a bar.

- [x] **3. Trophy unlock toast notifications.**
  Toast stack with `showTrophyToast()`; legendary/epic reuse `confettiBurst()`. Armed 4s
  after load to avoid spamming already-earned trophies.

- [x] **4. Trophy detail modal.**
  Click a row to open a modal (description, status, category, rarity, reward, requirement,
  progress, unlock date). Deep-linkable via `#trophy=<id>`, closeable via X / overlay / Esc.

- [x] **5. Search box for trophies.**
  Debounced search matching name / description / requirement / category, combinable with
  tabs and the category dropdown.

- [x] **6. Sort controls.**
  Sort by name, category, rarity, reward, status, and "closest to unlock" (progress).

- [x] **7. Rarity summary + completion ring.**
  Header completion ring (% unlocked) + per-rarity pills (unlocked/total for
  common/rare/epic/legendary).

- [x] **8. Persist last filter/tab/search/sort.**
  Active filter, search, and sort persist in `localStorage` (`trophyPagePrefs`) and restore
  on reload.

**Files touched:** `data/trophy_definitions.json` (new), `backend/routes/trophies_routes.py`
(definitions loader + `/api/trophies/definitions` + canonical `list` merge + reward-aware
award + root-path page fix), `trophies/index.html` (UI + JS for features 2–8, cache bump).

## Phase 2 — Engagement & Gameplay (Features 9–16) — 7/8 DONE (2026-06-06)

- [x] **9. Trophy sets / collections.**
  `sets` metadata in `trophy_definitions.json` (5 sets) + `set` membership on trophies.
  Exposed via `/api/trophies/definitions`; new "🎯 Sets" tab shows per-set progress, members,
  and completion bonus.

- [x] **10. Daily / weekly trophy quests.**
  `GET /api/trophies/quests` generates date-seeded daily + weekly objectives (same for all
  users), marks completion against unlocked trophies. New "📋 Quests" tab.

- [x] **11. Seasonal / limited-time trophies.**
  `season` + `available_from`/`available_until` fields (3 seasonal trophies). New "🗓️
  Seasonal" tab with active/upcoming/ended states and countdowns; server enforces the window
  on sync/claim.

- [x] **12. Next-up recommendations.**
  "⏳ Closest to unlocking" widget at the top of the Table tab: top 4 locked trophies by
  progress %, each opens the detail modal.

- [x] **13. Reward claim flow.**
  Idempotent `POST /api/trophies/claim` credits the trophy `reward` to `trophy_points` at
  most once; "Claim reward" button in the detail modal for unlocked trophies.

- [x] **14. Trophy showcase on profile.** (done 2026-06-06)
  `GET/POST /api/trophies/showcase` (file-backed, max 6). Pin/unpin button in the trophy
  modal; `profile/index.html` renders the pinned showcase (deep-links to `#trophy=<id>`).

- [x] **15. Hidden / secret trophies.**
  `hidden: true` (viral_creator, content_moderator) render as "??? (Hidden)" until unlocked,
  in table, modal, next-up, and sets.

- [x] **16. Streak & milestone trophies wired to real events.**
  `POST /api/trophies/sync` computes real progress metrics server-side from the unified
  points DB and awards every eligible (and available) trophy; the page calls it on load and
  toasts genuine new unlocks instead of guessing client-side.

**Files touched:** `data/trophy_definitions.json` (sets/seasonal/hidden, v1.1.0),
`backend/routes/trophies_routes.py` (`compute_user_metrics`, `eligible_trophy_ids`,
`_seasonal_available`, `/sync`, `/claim`, `/quests`, sets in `/definitions`),
`trophies/index.html` (Sets/Quests/Seasonal tabs, next-up, hidden display, claim button,
sync on load, cache bump).

## Phase 3 — Social & Competitive (Features 17–21) ✅ DONE (2026-06-06)

- [x] **17. Trophy leaderboard.**
  `GET /api/trophies/leaderboard` ranks top collectors by trophy points (scanned from
  `data/user_points/*.json`, 60s cache), shows the current user's rank. New "🏅 Leaderboard"
  tab with medals + "you" highlight.

- [x] **18. Compare with a friend.**
  `GET /api/trophies/compare?with=<user_id>` returns each user's unlocked set + a_only /
  b_only / shared. New "🆚 Compare" tab with side-by-side columns.

- [x] **19. Shareable trophy card image.**
  Client-side canvas renders a 1200×630 card (unlocked/total, Trophy Score, points) and
  downloads it as PNG. "📸 Share my trophy card" button in the header.

- [x] **20. Activity feed.**
  `GET /api/trophies/activity` returns recent unlocks (from the trophy DB). New "📰 Activity"
  tab.

- [x] **21. Rarity-weighted "Trophy Score".**
  common=1, rare=3, epic=8, legendary=20. Shown as a header stat card and used in the share
  card.

**Files touched:** `backend/services/trophy_social_service.py` (new — leaderboard, activity,
showcase, compare, score), `backend/routes/trophies_routes.py` (`/leaderboard`, `/activity`,
`/compare`, `GET`+`POST /showcase`), `trophies/index.html` (Leaderboard/Compare/Activity
tabs, Trophy Score stat, share button, showcase pin in modal), `profile/index.html`
(showcase render).

## Phase 4 — Polish, Agent Parity & Ops (Features 22–25) ✅ DONE (2026-06-06)

- [x] **22. Agent-native trophy tools.** ✅
  `GET /api/trophies/agent-tools` returns a capability map of all 11 trophy actions, and
  `POST /api/trophies/agent-action` dispatches them — read actions run directly, mutating
  actions (sync/claim/showcase_set) require explicit `approved: true`. Full parity with the
  UI per `docs/PROJECT_RETHINK.md`.

- [x] **23. Accessibility & keyboard navigation.** ✅
  Tabs now form an ARIA `tablist` with `role="tab"`/`aria-selected` and arrow/Home/End
  key navigation. Table rows are focusable (`tabindex`, `role="button"`, `aria-label`) and
  activate the modal on Enter/Space. The detail modal traps Tab focus, focuses the close
  button on open, restores focus on close, and closes on Escape. `prefers-reduced-motion`
  disables the rotating glow, icon bounce, and confetti-style animations. Visible
  `:focus-visible` outlines added throughout.

- [x] **24. Performance & caching cleanup.** ✅
  Removed the always-on body `MutationObserver` and duplicate fill timers. The table now
  uses a single clean render path: immediate `fillTableSync()` plus one idempotent safety
  check on `load`. Definitions are already cached server-side (mtime-based) and the page
  carries the `cache-version` meta (`20260606c`).

- [x] **25. Admin authoring + health check.** ✅
  `GET /api/trophies/health` validates definitions (duplicate ids, missing reward/rarity,
  metric/target mismatch, bad seasonal dates, dangling set members), confirms the showcase
  dir is writable, and reports DB table state. `POST /api/trophies/admin/upsert` adds/edits
  a trophy in the JSON source with no redeploy — disabled by default and gated behind the
  `TROPHY_ADMIN_SECRET` env var + `X-Trophy-Admin-Token` header. Full surface documented in
  `docs/TROPHIES_API_OPENAPI.md`.

---

## Suggested order

1. **Phase 1** (1–8): low-risk, high-visibility, unblocks everything else once #1 lands.
2. **Phase 2** (9–16): the engagement loop; #16 makes unlocks trustworthy.
3. **Phase 3** (17–21): social surface once data is solid.
4. **Phase 4** (22–25): parity, a11y, perf, and ops hardening.

## Acceptance / done criteria

- Trophy definitions load from one backend source; client map is fallback only.
- Locked trophies show real progress; unlocks trigger a toast + reward claim.
- New tabs (Sets, Quests, Seasonal, Leaderboard) render from real endpoints.
- Every UI action has an agent-callable equivalent.
- Page passes a keyboard-only pass and respects reduced motion.
- `GET /api/trophies/health` returns green; endpoints documented in OpenAPI.

## Touch points

- Frontend: `trophies/index.html`, `vidgenerator/trophies/index.html`, `profile/index.html`.
- Backend: `backend/routes/trophies_routes.py`, `backend/services/trophies_db_service.py`,
  `backend/services/video_generator_service.py` (`_check_and_award_trophies`).
- Data: `data/trophy_definitions.json` (new), `data/achievements.json`.
- Docs: `docs/TROPHIES_API_OPENAPI.md` (update once shipped).
