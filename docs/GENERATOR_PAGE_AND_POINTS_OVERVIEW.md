# Generator Page, Clips/Videos & Unified Point System — Overview

**Purpose:** Single overview of the generator page, the clips/videos it creates, components in use, improvement options, point scale, and the unified point system to include.

---

## 1. Generator Page & What It Creates

### Entry point
- **Frontend:** `vidgenerator/generator/index.html` — main Generator UI (single large page with embedded CSS/JS).
- **Flows:**
  1. **Documentary / clip:** User enters title + description → **Create** → backend starts a job → page polls progress → on completion: video player + “You earned X points”.
  2. **Unified create:** Page tries `POST /api/unified/generate-video` first; on failure falls back to `POST /api/generator/create`.
  3. **AI clips:** Optional “agent opinion” after create; separate AI-clips flow exists (`POST /api/ai-clips/generate`, `GET /api/generator/ai-clips/<job_id>`).

### What gets generated (clips/videos)

| Type | How it’s built | Output |
|------|----------------|--------|
| **Clip with context (default)** | `use_context: true` in config → `generator_context_service.gather_context_for_user()` + `context_to_segments()` → `generate_rich_video_sync(doc_id, segments)` | Multi-segment MP4: intro, user prompt/title, profile, agents, optional “level/gen points” segment, outro. Segments are ColorClips (or ImageClips if image_path) with optional text; concatenated. |
| **Short clip** | `short_clip: true` or duration &lt; 120s → 3 segments: intro, “Your clip”, end. | Shorter MP4, same pipeline. |
| **Fallback (no context)** | If context/segments fail → `_generate_video_sync(doc_id, prompt, title, duration)` | Single MoviePy ColorClip or copy of sample video. |

- **Output path:** `vidgenerator/videos/<doc_id>.mp4`.
- **Served at:** `GET /vidgenerator/api/documentary/video/<doc_id>` (or equivalent documentary video route).

So the generator page effectively creates **one video per run**: either a **context-rich multi-segment clip** (profile, agents, prompt, points) or a **simple single-clip** fallback.

---

## 2. Components in Use vs Needed

### Backend (in use and needed)

| Component | Role | Needed? |
|-----------|------|--------|
| `backend/services/video_generator_service.py` | `generate_video_background`, `generate_rich_video_sync`, `_generate_video_sync`, `_award_generation_points`, `_set_job_failed` | ✅ Yes — core pipeline. |
| `backend/services/generator_context_service.py` | `gather_context_for_user`, `context_to_segments` — profile, agents, unified points → segments | ✅ Yes — for “clip with context” every run. |
| `backend/services/generator_db_service.py` | `get_job`, `save_job`, `list_jobs`, DB when migration run | ✅ Yes — job persistence. |
| `backend/services/unified_points_database` | `add_points`, `get_all_points` — generation_points, file + DB | ✅ Yes — points storage. |
| `backend/routes/missing_endpoints_routes.py` | Generator/create, documentary, unified generate-video, progress, video, history, stats, etc. | ✅ Yes — API surface. |

### Frontend — generator page scripts (in use)

| Script | Role |
|--------|------|
| `error-manager.js` | Centralized error logging. |
| `unified-generator-battle.js` | Battle integration (optional load). |
| `service-worker-gatherer.js` | SW registration; progress messages. |
| `media-gatherer.js` | Media/context gathering. |
| `toast-notifications.js` | Toasts. |
| `progression-display.js` | Progress UI. |
| `navigation-toolbar.js` | Nav. |
| `theme-timeline.js` | Theme/timeline UI. |
| `hypnotic-point-counters.js` | Point display (optional). |
| `trigger-based-actions.js` | Triggers (optional). |
| `comprehensive-loading-fix.js` | Loading state. |
| `universal-auto-save-status.js` | Auto-save status. |
| `top50-monetization-frame.js` | Top 50 / monetization. |
| `energy-regeneration-timers.js` | Energy timers. |
| `stats-achievements-tracker.js` | Fetches stats + points, checks achievements, awards one-time rewards. |
| `image-support.js`, `template-effects.js`, `template-services.js`, `agent-skill-sets.js`, `template-engine-core.js` | Templates, agents, images. |
| `unified-point-counters.js` | Loads `/vidgenerator/api/points/all`, updates many DOM elements (XP, level, stats points, achievements, trophies, coins, battle, etc.). |
| `comprehensive-api-integration.js` | Broader API integration. |

### Frontend — generator page inline logic

- **Create request:** Builds `requestBody` (title, description, user_id, etc.), calls unified then generator create, then `pollVideoProgress(docId)`.
- **Points:** `updatePointsDisplay()` calls `GET /api/points/get-all-connected?user_id=...`, then `processPointsData()` → `updatePointElement()` for `points-xp`, `points-level`, `points-generation`, `points-activity`, `points-battle`, `points-quest`, `points-total`.
- **Hooks:** On “video generated” (custom event) and after create: `setTimeout(updatePointsDisplay, 3000)`; also `setInterval(updatePointsDisplay, 5000)`.

### Components that should be used (recommended)

| Component | Status | Recommendation |
|-----------|--------|----------------|
| `point-system-save-manager.js` | Used on other pages (e.g. debugger, main index backup); **not** loaded on generator | **Include on generator** if you want: DOM + unified counter → DB + local JSON, repair, progression trigger, and consistent persistence with the rest of the app. |
| **Unified points API** | Generator uses `get-all-connected`; other scripts use `vidgenerator/api/points/all` | Standardize generator to use the same “get all points” contract (e.g. one canonical endpoint) so one source of truth. |
| **Stats / achievements** | `stats-achievements-tracker.js` already loads; it uses `points/all` and awards rewards | Ensure generator completion is reflected in stats (e.g. videos created) so achievements (e.g. “First Video”, “10 videos”) unlock correctly. |

---

## 3. What Can Be Added to the Process of Generating Videos

- **Before generation**
  - **Quick clip vs full documentary toggle** in UI (short mode = fewer segments, faster).
  - **Theme/template selector** (if you add theme-aware segments later).
  - **Optional “include my level/points in clip”** (already in context; could be a checkbox).
- **During generation**
  - **Per-segment progress** in the progress bar (e.g. “Building segment 2/5” from `generate_rich_video_sync` `on_progress`).
  - **Service worker** already forwards progress; ensure progress text reflects segment index.
- **After generation**
  - **Guaranteed points refresh:** Already calling `updatePointsDisplay` after completion; ensure backend has written `generation_points` before the next poll (e.g. order: write points → then set job completed).
  - **“My recent clips”** from `GET /api/generator/jobs` or `history` on the same page (list with link to video + points earned).
  - **Achievement popup** when a stat achievement is unlocked (e.g. “First Video” +100 points) — stats-achievements-tracker already awards; optional: show a toast on generator page when `videoGenerated` and new achievement.
- **Backend**
  - **Different point amounts:** e.g. `GENERATION_POINTS_PER_VIDEO = 25` for full documentary, `GENERATION_POINTS_PER_CLIP = 10` for short clip (constant exists in plan; add in code if not already).
  - **Quality/duration bonuses:** optional extra points for longer or “high quality” runs (when you have a quality metric).

---

## 4. Point Scale Rewarded — Overview

### Generation (video/clip completion)

| Source | Amount | When |
|--------|--------|------|
| **video_generator_service** | **50** base (`GENERATION_POINTS_PER_VIDEO`) for full documentary | Every completed full video (one-time per job). |
| **Short clip** | Same 25 in current code; redesign plan suggests **10** for “quick clip” — not yet split in code. | Would apply if you add a “quick clip” mode and set `points = GENERATION_POINTS_PER_CLIP`. |

Total per job = base + (number of segments × 10) + duration bonus. Points flow to all pages via unified points API.

Backend: `_award_generation_points(user_id, doc_id, points)` → `unified_points_db.add_points(user_id, 'generation_points', points, ...)` and profile `last_documentary_id`; job gets `points_earned` and `user_id`. Production demo: run `python scripts/seed_production_video.py` to create `vidgenerator/videos/production-demo.mp4`; generator history includes it when the file exists.

### Stats achievements (one-time rewards)

Awarded by **stats-achievements-tracker.js** (via `POST /vidgenerator/api/rewards/create`) when a stat threshold is first reached. Examples:

| Category | Achievement | Condition | Points |
|----------|-------------|-----------|--------|
| Videos | First Video | total ≥ 1 | 100 |
| Videos | Video Creator | total ≥ 10 | 500 |
| Videos | Video Master | total ≥ 50 | 2,000 |
| Videos | Video Legend | total ≥ 100 | 5,000 |
| Videos | First Completion | completed ≥ 1 | 150 |
| Achievements | First Achievement | earned ≥ 1 | 50 |
| Achievements | Achievement Collector | earned ≥ 10 | 500 |
| Achievements | Achievement Master | earned ≥ 25 | 1,500 |
| Battles | First Battle / First Victory / 10 wins / 50 wins / 80% win rate | various | 50–2,000 |
| Points | Point Collector / Master / Legend | total 1k / 10k / 100k | 100 / 500 / 2,000 |
| XP | Level 5 / 10 / 25, XP 10k | level or total XP | 100–1,000 |
| Trophies | First / 5 / 10 | count | 100–1,000 |
| Milestones | First / 5 | reached | 100 / 500 |

So the **scale** is: **25 per generation** plus **50–5,000** per one-time stat achievement depending on category and tier.

---

## 5. Unified Point System — Outline to Include

### Goals (from existing design)

- **Single source of truth:** All points (generation, activity, battle, quest, XP, etc.) in one place: DB preferred, file fallback so nothing is lost.
- **One read path for UI:** One “get all points” API used by generator, dashboard, profile, and point counters.
- **Every generation awards points:** Stored under `generation_points`; job record has `points_earned` and `user_id`; profile has `last_documentary_id` (and optionally `last_generation_at`).

### Systems to unify (already referenced in code)

- **XP & level** — `xp_total`, `level` (and level progress).
- **Stats points** — `stats_points_total`, `stats_points_available`; per-stat: creativity, efficiency, quality, social, knowledge, dna_manipulation, dna_cloning.
- **Generation** — `generation_points` (from video/clip completion).
- **Activity** — `activity_points` (optional “did a run”).
- **Achievements / milestones** — `achievements_earned`, `achievements_total`; `milestones_reached`, `milestones_total`.
- **Trophies** — `trophy_points`, `trophy_level`, `trophies_collected`.
- **Economy** — `coins`, `credits`.
- **Battle** — `battle_points`, `battle_wins`, `battle_losses`, `battle_streak`.
- **Metal / theme** — `territory_points`, `sex_metal_points`, `porno_rights_points`, `mtg_points`, `trophy_hunt_points` (+ levels).
- **Content categories** — `conspiracy_points`, `religious_conspiracy_points`, `alternative_theory_points` (bonus from content_category on create; see `docs/CONSPIRACY_AND_CONTENT_CATEGORIES_POINTS.md`).
- **Social** — `friends_count`, `followers_count`, `social_interactions`.
- **Quest** — `quest_points`, `quest_xp`, `active_quests`, `completed_quests`.
- **Engagement** — `videos_created`, `videos_watched`, `generations_total`, `high_quality_generations`, `average_quality_score`, `time_played`, `login_streak`, `daily_logins`, `prestige_count`.

### Implementation outline (to include)

1. **Backend**
   - **Single write path:** All generation rewards go through `unified_points_db.add_points(...)` (already for generation_points).
   - **Single read path:** One endpoint (e.g. `GET /api/points/get-all-connected` or `GET /vidgenerator/api/points/all`) returns a single JSON with all systems above; used by generator, unified-point-counters, and point-system-save-manager.
   - **Persistence:** DB (e.g. `player_levels`, system snapshots) when available; always write to file store so points are never lost.
   - **Profile:** Update `last_documentary_id` and optionally `last_generation_at` / aggregates so profile and “get all points” stay in sync.

2. **Frontend**
   - **Generator:** Use the same “get all points” endpoint and `processPointsData` (or shared helper) so `points-generation`, `points-xp`, `points-level`, and `points-total` match the rest of the app.
   - **Unified counters:** Keep `unified-point-counters.js` updating all DOM elements from that single API so every page shows the same numbers.
   - **Save manager:** Load `point-system-save-manager.js` on the generator page so points (and any local edits) are saved/repaired and progression is triggered; listen for `pointsUpdated` and refresh from unified counter.

3. **Scale**
   - **Per action:** e.g. 25 per video, 10 per short clip (when implemented).
   - **Achievements:** Keep existing one-time rewards (50–5,000) and have them written through the same unified system so totals and level/XP stay consistent.

4. **Visibility**
   - **Generator:** Points widget shows XP, level, generation, activity, battle, quest, total; update after each completed video and on interval.
   - **Single contract:** `result.all_points` (or equivalent) with the keys listed above so all UIs can stay in sync without duplicate logic.

This outline is the **unified point system to include**: one write path, one read API, one contract for the frontend, with generator and stats achievements both feeding and reading from it.

---

## 6. Summary Table

| Topic | Summary |
|-------|---------|
| **Generator page** | `vidgenerator/generator/index.html`; creates one video per run (context-rich multi-segment or simple fallback). |
| **Clips/videos** | Multi-segment MP4 from profile + agents + prompt + optional points; or single ColorClip/sample. |
| **Components in use** | video_generator_service, generator_context_service, generator_db_service, unified_points_database, missing_endpoints_routes; many JS (unified-point-counters, stats-achievements-tracker, SW, etc.). |
| **Components to add** | point-system-save-manager on generator; align on one “get all points” API. |
| **Add to process** | Short-clip toggle, segment progress text, “My recent clips”, optional achievement toast, per-clip vs per-video point constants. |
| **Point scale** | 25 per video; one-time achievements 50–5,000. |
| **Unified system** | One write (unified_points_db), one read API, one contract; generator and all counters use it; include save-manager and profile updates. |

---

*Document generated from codebase review. Align with GENERATOR_REDESIGN_PLAN.md and GENERATOR_FIX_OVERVIEW.md for implementation details.*
