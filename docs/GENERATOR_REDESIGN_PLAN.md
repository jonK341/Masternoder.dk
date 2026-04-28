# Generator Redesign Plan — Clip with Context, Points, and Better UX

## Goals

1. **Every run produces a clip with context** — Profile, agents, service worker (and optionally unified points) feed into each generation so output is personalized and consistent.
2. **Points flow to profile and unified system** — All generation rewards are stored in the DB and reflected in profile/XP/level.
3. **Generator as the attraction point** — Redesign the site/UX so the generator is the main, smooth entry point.
4. **All points in the database** — Single source of truth: unified points DB + profile, with no “missing” updates in the UI.

---

## 1. Clip-with-Context Every Run

### Current state

- **Documentary create** (`/api/generator/create`) uses a simple prompt/title/description; video is a single clip or basic segments.
- **make_a_vid.py** already gathers full context (profile, agent_connections, agent_groups, service_worker_context) and builds multi-segment videos via `generate_rich_video_sync`.
- Context is **not** wired into the normal create flow used by the browser.

### Target behavior

- **Every** generator run (documentary or “quick clip”) should:
  1. Resolve **user_id** (from request or session).
  2. **Gather context** once per run:
     - Profile (display_name, bio, skill_path, preferences).
     - Agent–generator connections (list from `generator_agent_connections`).
     - Optional: agent groups, service worker role, **current unified points** (for “level” or “streak” in the clip).
  3. Build **segments** from that context (intro, profile, agents, outro) plus any user prompt/title.
  4. Call **one** video pipeline: `generate_rich_video_sync(doc_id, segments, ...)` so every output is a “clip with context”.
- Keep **short mode**: e.g. 3 segments (intro, prompt, outro) for “quick clip” to keep runs fast when needed.

### Implementation outline

- In **video_generator_service** (or a small helper used by the create endpoint):
  - Add `gather_context_for_user(user_id) -> dict` (reuse logic from `make_a_vid.gather_all_context`).
  - Add `context_to_segments(ctx, user_prompt=None, short=False) -> list` (reuse/adapt `make_a_vid.context_to_segments`).
- In the **create** flow (e.g. `missing_endpoints_routes.generator_create` or the background runner it uses):
  - After creating `doc_id` and config, call `gather_context_for_user(user_id)`.
  - Build segments with `context_to_segments(ctx, user_prompt=prompt, short=config.get('short_clip', False)`.
  - Pass segments into the existing rich-video pipeline (or a thin wrapper that still calls `generate_rich_video_sync`).
- **AI-clips** can use the same context for consistency (e.g. same intro/outro, agent list).

Result: every run is a “clip with context” without the user having to run `make_a_vid.py` manually.

---

## 2. Points: Profile + Unified System + Database

### Current state

- **video_generator_service**: On documentary completion it calls `_award_generation_points(user_id, doc_id, points)` which:
  - Calls `unified_points_db.add_points(user_id, 'generation_points', points, ...)`.
  - Updates profile `preferences.last_documentary_id` via `user_onboarding.update_user_profile`.
  - Sets `job['points_earned']` and `job['user_id']` and persists via `job_store_set`.
- **unified_points_database**: Uses a **file fallback** (JSON per user in `logs/unified_points/`) and **best-effort DB** (e.g. `player_levels`, system snapshots). So points are durable in files; DB may or may not be present.

### Target behavior

- **All points from generation** go through one path:
  1. **Unified points DB** (or file store if DB not available): `generation_points` (and optionally small `activity_points` for “did a run”).
  2. **Profile**: Update `last_documentary_id` and optionally a “total_generation_points” or “last_run_at” so the profile reflects latest activity.
  3. **Job record**: Always set `points_earned` and `user_id` on the job so history/stats show correct totals.
- **Single source of truth**: Prefer DB for production; keep file store as fallback so points are never lost. Ensure the **get-all-connected** (or equivalent) API returns `result.all_points` including `generation_points`, `xp_total`, `level` so the UI can show them without stale data.

### Implementation outline

- Keep **GENERATION_POINTS_PER_VIDEO** (e.g. 25) and **GENERATION_POINTS_PER_CLIP** (e.g. 10) for short runs if you add a “quick clip” mode.
- In **unified_points_database.add_points**:
  - Ensure file store is always written first (already done).
  - In DB path: ensure `player_levels` and any `system_point_snapshots` / usage tables are updated so that `get_all_points()` and profile APIs read from the same place when possible.
- In **video_generator_service** (and any future “clip completed” path):
  - Always call `_award_generation_points(user_id, doc_id, points)` on success.
  - Always set `job['points_earned']` and `job['user_id']` and persist the job (DB if migration run, else in-memory).
- **Profile**: Keep updating `preferences.last_documentary_id`; optionally add `last_generation_at` or aggregate in profile for display.
- **Frontend**: Ensure generator page calls the points API after “video completed” and refreshes the points widget (already partially there with `updatePointsDisplay` / `videoGenerated`).

Result: every run that completes adds points to the unified system and profile, and all points are persisted (DB or file) and visible in the UI.

---

## 3. Site Redesign — Generator as Attraction Point

### Ideas for better UX

- **Landing / home**: Make the generator the hero: one clear “Create a clip” or “Start documentary” CTA, short explanation (“Personalized clip from your profile and agents”), and maybe a preview or latest clip.
- **Single flow**: One primary path: “Create clip” → optional prompt → progress (with context summary: “Using your profile and 20 agents”) → result (video + points earned). Avoid scattering creation across multiple disconnected pages.
- **Points visible up front**: Show XP, level, and generation points near the main CTA so users see progress and reward immediately.
- **History and stats**: One place for “My clips” (jobs list) and “My stats” (total videos, points earned, success rate) so the generator feels like a coherent feature, not a form.
- **Lab / advanced**: Keep “Lab” or “Advanced” for power users (e.g. full context editor, long documentary) without cluttering the main flow.
- **Performance**: Prefer “clip with context” (short mode) as default so most runs finish in under a minute; offer “Full documentary” as an option.

### Implementation outline (high level)

- **Navigation**: Generator is the first or second item; “Gallery” and “Profile” (with points) are one click away.
- **Generator page**:
  - Top: Points widget + “Create a clip” (primary) and “Full documentary” (secondary).
  - Center: Progress area (and when done: video player + “You earned X points”).
  - Bottom/side: “My recent clips” (from jobs/history API) and link to full history.
- **Unified points API**: Ensure one endpoint (e.g. get-all-connected or profile/points) returns everything the generator UI needs so the page doesn’t depend on multiple failing endpoints.

Result: the site feels centered on the generator, with a smooth path from “one click” to “clip with context” and visible points.

---

## 4. How to Implement (Phased)

### Phase 1 — Context every run + points guaranteed

1. Add **context gathering and segment building** to the create flow (reuse `make_a_vid` logic inside backend).
2. Ensure **every completed run** calls `_award_generation_points` and updates job `points_earned` and `user_id`; ensure unified DB (and file fallback) is the single place points are written.
3. Verify **get-all-connected** (or equivalent) returns `result.all_points` so the generator UI can show points after each run.

### Phase 2 — UX revamp

1. Simplify generator **index.html**: one primary CTA, progress, then result + points.
2. Add “My recent clips” from jobs/history API (when those endpoints are available on the server).
3. Adjust **navigation** so Generator is the attraction point (order and labels).

### Phase 3 — Database and profile

1. Ensure **unified_points_database** writes to DB when possible (player_levels, system_point_snapshots) and that profile APIs read from the same store.
2. Optionally add **migration or script** to backfill or verify that all generation points are reflected in the DB and profile.

---

## 5. Summary

| Area | Current | Target |
|------|---------|--------|
| **Clip content** | Simple prompt/title; no profile/agents | Every run = clip with context (profile, agents, optional points) |
| **Points** | Awarded on completion; file + best-effort DB | All points in DB (or file fallback); profile + job updated |
| **UX** | Multiple entry points; points sometimes missing in UI | Generator = attraction; one main flow; points visible |
| **Persistence** | File store + optional DB | Single source of truth; UI reads from same place |

Implementing **Phase 1** (context every run + points guaranteed + API shape for UI) gives the biggest benefit; then Phase 2 (UX) and Phase 3 (DB/profile) complete the redesign.
