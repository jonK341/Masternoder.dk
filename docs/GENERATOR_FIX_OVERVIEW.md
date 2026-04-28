# Generator Fix – Overview

**Purpose:** Single overview of the video/documentary generator feature and a structured plan to fix it.

**Status:**  
- **Phase 1 done:** Missing endpoints implemented; response shapes match `vidgenerator/generator/index.html`. Service: `get_job_statistics`, `get_job_performance`, `get_job_count`, `get_theme_distribution`.  
- **Phase 2 done:** Video pipeline hardened: failures set job to `failed` with `error_message` persisted; `run()` wrapped in try/except; `_generate_video_sync` returns `(path, error_message)`. Migration run (tables created when needed).

---

## 1. What the generator is

The **generator** is the feature that:

- Lets users create **documentary-style videos** from a prompt/title.
- Supports **AI clips** generation (script + clip workflow).
- Stores **jobs** (pending / processing / completed / failed) and serves progress + final video.

**User entry points:**

- **Frontend:** `vidgenerator/generator/index.html` (main Generator UI).
- **Nav:** Links from Gallery, Stats, Lab, etc. to “Generator”.

**Main flows:**

1. **Documentary:** User submits prompt → `POST /api/unified/generate-video` or `POST /api/generator/create` → background job → poll `GET /api/documentary/progress/<doc_id>` → play `GET /api/documentary/video/<doc_id>`.
2. **AI clips:** User submits prompt → `POST /api/ai-clips/generate` (or fallback `POST /api/generator/ai-clips`) → poll `GET /api/generator/ai-clips/<job_id>` for status/clips.

---

## 2. Components (where things live)

| Layer | Location | Role |
|-------|----------|------|
| **DB tables** | Migration: `video_generation_jobs`, `job_artifacts` | Persist jobs; created by `scripts/generator_migration.py` (e.g. `--standalone`). |
| **Migration** | `scripts/generator_migration.py` | Creates tables + indexes; idempotent. |
| **DB service** | `backend/services/generator_db_service.py` | `get_job`, `save_job`, `list_jobs`, `generator_tables_exist()`. Safe when migration not run. |
| **Video pipeline** | `backend/services/video_generator_service.py` | `generate_video_background()`; uses MoviePy or sample-file fallback; updates job via `job_store_get` / `job_store_set`. |
| **Routes** | `backend/routes/missing_endpoints_routes.py` | All generator/documentary/ai-clips and unified generate endpoints live here (no dedicated `generator_routes.py` yet). |
| **Frontend** | `vidgenerator/generator/index.html` | Single-page UI: create documentary, AI clips, progress, history, stats, debug. |

Other features (Battle, Trophies, Chat, Shop, etc.) use dedicated route modules (e.g. `battle_routes.py`, `trophies_routes.py`); the generator does not.

---

## 3. Current API surface

**Implemented in backend:**

- `GET /api/generator/jobs?user_id=...&limit=50` – list jobs (DB when migration run).
- `POST /api/generator/create` – create documentary job, start background generation.
- `POST /api/generator/ai-clips` – create AI-clips job (stub).
- `GET /api/generator/ai-clips/<job_id>` – AI-clips status.
- `POST /api/ai-clips/generate` – AI clips with optional LLM enhancement.
- `GET /api/documentary/progress/<doc_id>` – progress for documentary.
- `POST /api/documentary/restart/<doc_id>` – restart documentary.
- `GET /api/documentary/video/<doc_id>` – serve video or JSON status.
- `POST /api/unified/generate-video` – unified documentary creation (same pipeline as create).

**Also implemented (Phase 1):**

- `GET /api/generator/history?user_id=...&limit=10` – “my jobs” with shape `history: { total, successful, avg_time, today, recent[] }`.
- `GET /api/generator/statistics?user_id=...&days=7` – `statistics: { total_videos, themes_count, theme_distribution, ... }`.
- `GET /api/generator/performance?user_id=...` – `performance: { success_rate, avg_speed, best_provider, trend }`.
- `GET /api/generator/quick-actions?user_id=...` – `actions: { recent_videos[] }` plus `quick_actions[]`.
- `GET /api/generator/debug-routes` – list of generator routes for debug UI.
- `GET /api/generator/test` – health check (DB + video pipeline availability).
- `GET /api/generator/agent-connections` – 20 agent–generator integration points (for UI).
- `POST /api/generator/magic-generate` – Magic Technology: one-click documentary.

---

## 4. Suggested fix plan (prioritized)

### Phase 1 – Endpoints and wiring (quick wins)

1. **Alias or implement missing generator endpoints**
   - `GET /api/generator/history` → same as `GET /api/generator/jobs` (e.g. `user_id`, `limit=10`) so “My jobs” works.
   - `GET /api/generator/statistics` → return aggregates from `video_generation_jobs` when DB exists (e.g. counts by status, last 7 days).
   - `GET /api/generator/performance` → optional: simple performance stats (e.g. avg duration, success rate) from DB or stub.
   - `GET /api/generator/quick-actions` → stub or small list of suggested actions for the UI.
   - `GET /api/generator/debug-routes` → list of generator-related routes (for debug UI).
   - `GET /api/generator/test` → health check for generator (e.g. DB + pipeline availability).

2. **Optional:** Move generator/documentary/ai-clips routes from `missing_endpoints_routes.py` into a dedicated `backend/routes/generator_routes.py` and register the blueprint (same URLs). Keeps migration strategy doc and future changes clearer.

### Phase 2 – Pipeline and jobs

3. **Video pipeline**
   - Ensure `video_generator_service` is robust: errors set job to `failed`, message stored, no silent swallows.
   - Confirm output directory (`vidgenerator/videos` or configured path) is writable and used consistently for documentary and for `/api/documentary/video/<doc_id>`.
   - If “documentary” should be more than a color clip: document current limitation (MoviePy/sample) and optionally add a small roadmap (e.g. template-based titles, placeholder for future AI video).

4. **Job payload consistency**
   - `generator_db_service` and routes already support both `id` and `job_id`. Ensure any new code uses the same convention so DB ↔ in-memory fallback stay in sync.

### Phase 3 – Frontend and UX

5. **Generator page**
   - Point “history” (or “My jobs”) to `GET /api/generator/jobs` (or the new `history` alias) and display list (status, created_at, link to progress/video).
   - If endpoints remain stubbed (statistics/performance/quick-actions), show “Coming soon” or hide sections so no 404s.
   - Ensure documentary flow uses one of the working endpoints (`/api/unified/generate-video` or `/api/generator/create`) and that progress and video URL match what the backend returns.

6. **Optional**
   - Add “My jobs” to Stats/Lab as in migration doc, using `GET /api/generator/jobs?user_id=...`.

### Phase 4 – Operations and docs

7. **Migrations**
   - Ensure `python scripts/generator_migration.py --standalone` (or `run_all_migrations.py`) is run in every environment so generator tables exist and jobs persist.

8. **Docs**
   - Keep `docs/MIGRATION_STRATEGY_REUSABLE.md` “Generator / Jobs” row and “Frontend (next steps)” in sync with any new routes or renames.
   - Optionally add a short “Generator” section that points to this overview and to the main endpoints.

---

## 5. Checklist (copy-paste)

- [x] Add or alias: `history`, `statistics`, `performance`, `quick-actions`, `debug-routes`, `test`.
- [x] Wire generator page “My jobs” to jobs (or history) API; response shapes match frontend (history.total/recent, statistics.total_videos/theme_distribution, performance.success_rate/avg_speed, actions.recent_videos).
- [x] Confirm documentary create → progress → video (E2E test: `python scripts/test_generator_e2e.py`; use `--quick` to skip long poll).
- [x] Confirm AI-clips create → status polling (covered in same E2E script).
- [ ] (Optional) Move generator routes to `generator_routes.py` (left in `missing_endpoints_routes.py` for now).
- [x] Harden video pipeline: errors set job `failed` + `error_message`; run() try/except.
- [x] Run generator migration (e.g. `python scripts/generator_migration.py --standalone`); run in all envs as needed.

---

## 6. Testing the generation process

- **Fast unit tests (no Flask app):**  
  `python tests/test_generator_services.py`  
  Covers: `_generate_video_sync` return shape, `generator_db_service` exports, `_set_job_failed`.

- **E2E (Flask test client):**  
  `python scripts/test_generator_e2e.py`  
  Optional: `--quick` skips the documentary create→progress→video poll (faster).  
  `--poll SEC` sets max wait for documentary completion (default 60).  
  Tests: generator health, jobs, history, statistics, performance, unified generate-video, AI-clips create+status, and full documentary flow.

- **Hard-test (live HTTP):**  
  `python scripts/hard_test_generator_urls.py` (requires server running).  
  `--base URL` (default `http://127.0.0.1:5000`), `--quick` (GET only), `--poll SEC`.  
  Same checks over real HTTP; use to verify full stack and service-worker caching.

- **Service worker:**  
  `vidgenerator/service-worker.js` caches GETs for `/vidgenerator/api/generator/` and `/vidgenerator/api/documentary/` (network-first); POST create is network-only. Progress responses trigger `generation_progress` messages to the generator page. Generator and gatherer scripts are precached.

- **Debug API:**  
  `GET /api/debug/hard-test-generator?run=1&quick=1` runs the same hard-test server-side (Flask test client). Generator UI → “URL Test” tab runs quick or full test and shows results.

- **Documentary progress:** When status is `failed` or `error`, the API now returns `error_message` (and `message`) so the frontend can show the reason.

- **Generator unit tests:** `pytest tests/unit/test_01_generator.py -v` (13 tests). Covers: tables_exist, get_job, save_job, list_jobs, statistics, performance, count, theme_distribution; video _generate_video_sync tuple, _set_job_failed; save_job rejects missing job_id; generate_video_background starts; _row_to_job handles None/invalid JSON. Debugger → Unit tests tab runs all unit tests including generator.

---

## 7. Verification (how to confirm flows)

- **Documentary:** From Generator page, submit a prompt → expect 202 with `documentary_id` → poll `GET /vidgenerator/api/documentary/progress/<doc_id>` until `status` is `completed` or `failed` → if completed, open or request `GET /vidgenerator/api/documentary/video/<doc_id>` (file or JSON). Output directory: `vidgenerator/videos/<doc_id>.mp4` (same as `_get_video_file_path` in routes).
- **AI clips:** Submit to `POST /vidgenerator/api/ai-clips/generate` → poll `GET /vidgenerator/api/generator/ai-clips/<job_id>` for `status` and `clips`. Backend may be stub (no real clip generation yet).
- **Health:** `GET /vidgenerator/api/generator/test` returns `database_available` and `video_pipeline_available` (MoviePy import).

---

## 8. File reference

| Goal | File(s) |
|------|--------|
| Add generator endpoints | `backend/routes/missing_endpoints_routes.py` or new `backend/routes/generator_routes.py` |
| Job persistence | `backend/services/generator_db_service.py` |
| Video creation | `backend/services/video_generator_service.py` |
| Create tables | `scripts/generator_migration.py` |
| Generator UI | `vidgenerator/generator/index.html` |
| Strategy / list of features | `docs/MIGRATION_STRATEGY_REUSABLE.md` |
| Generator E2E tests | `scripts/test_generator_e2e.py` (use `--quick` for fast run) |
| Generator hard-test (live HTTP) | `scripts/hard_test_generator_urls.py` (server must be running) |
| Service worker (generator + agent) | `vidgenerator/service-worker.js` |
| Generator unit tests | `tests/unit/test_01_generator.py`, `tests/test_generator_services.py` |
| Agent-generator connections (20) | `backend/services/generator_agent_connections.py` |
| Upload and deployment | `scripts/deploy_vidgenerator_solution.py`, `docs/DEPLOYMENT.md` |

**Agent-generator connections:** 20 integration points via `GET /api/generator/agent-connections`; **Magic:** one-click video via `POST /api/generator/magic-generate` and "Magic" tab.

This overview is the single place to see what the generator is, what’s implemented, what’s missing, and how to fix it step by step.
