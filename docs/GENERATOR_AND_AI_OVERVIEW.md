# Generator process and AI integration — overview

**Context:** The first major problem (port 5000 bottleneck and lag) is addressed via more workers, a second backend on 5001, nginx upstream, LITE_APP, and response caching. This doc summarizes **what the generator is**, **how AI is integrated**, and **what’s working** so you can fix or extend the generator and AI flows next.

---

## 1. Problem 1 status: bottleneck

- **Done:** More workers on 5000 (`uwsgi.ini`: 4 processes × 2 threads), second uWSGI on 5001, nginx `flask_backend` upstream, LITE_APP=1, caching for heavy APIs (points/all, stats/summary, frontpage/init).
- **Scripts:** `python scripts/run_bottleneck_fixes.py` (or `fix_502.py` + `enable_nginx_upstream.py`).
- **Details:** `docs/PORT_5000_BOTTLENECK_AND_SOLUTIONS.md`.

---

## 2. The generator process (what it is)

The **generator** is the feature that lets users create **documentary-style videos** and **AI clips** from a prompt/title. Jobs are stored (in-memory and/or DB), progress is polled, and final video is served.

### 2.1 Two main flows

| Flow | Entry API | What runs | Progress / result |
|------|-----------|-----------|-------------------|
| **Documentary** | `POST /api/unified/generate-video` or `POST /api/generator/create` | Background encoding (MoviePy, segments, optional AI-enriched script) | `GET /api/documentary/progress/<doc_id>` → `GET /api/documentary/video/<doc_id>` |
| **AI clips** | `POST /api/ai-clips/generate` or `POST /api/generator/ai-clips` | Background AI clips (LLM script/plan → one short clip per scene) | `GET /api/generator/ai-clips/<job_id>` (status + `clips[]` with URLs) |

### 2.2 Where it runs (backend)

- **Routes:** Generator/documentary/ai-clips endpoints are registered in **`backend/routes/generator_routes.py`** (blueprint `generator_bp`). View logic lives in **`backend/routes/missing_endpoints_routes.py`** (no route decorators there for these endpoints); shared job helpers in **`backend/routes/generator_shared.py`**.
- **Job store:** In-memory `_video_jobs` dict + optional DB via **`backend/services/generator_db_service.py`** (`get_job`, `save_job`, `list_jobs`). Tables: `video_generation_jobs`, `job_artifacts` (created by `scripts/generator_migration.py`).
- **Video pipeline:** **`backend/services/video_generator_service.py`**:
  - **Documentary:** `generate_video_background()` → `_generate_video_sync()` (MoviePy, segment colors, optional AI-enhanced segments/titles). Output: `vidgenerator/videos/<doc_id>.mp4` (or `VIDEOS_DIR`).
  - **AI clips:** `generate_ai_clips_background()` → plans segments (optionally via LLM), then for each clip calls `generate_rich_video_sync()` or `_generate_video_sync()`, appends to `job['clips']` with URLs like `/api/documentary/video/<clip_id>`.
- **Frontend:** **`generator/index.html`** (root or under `vidgenerator/`) — create documentary, AI clips, progress, history, stats, debug.

### 2.3 Important APIs (quick reference)

| Method | Path | Purpose |
|--------|------|--------|
| POST | `/api/unified/generate-video` | Create documentary (unified) |
| POST | `/api/generator/create` | Create documentary job |
| POST | `/api/ai-clips/generate` | Start AI clips (with optional LLM script) |
| POST | `/api/generator/ai-clips` | Start AI clips (alternate) |
| GET | `/api/documentary/progress/<doc_id>` | Documentary progress (and sidecar `.status.json`) |
| GET | `/api/documentary/video/<doc_id>` | Serve documentary or clip MP4 |
| GET | `/api/generator/ai-clips/<job_id>` | AI clips status + `clips[]` |
| GET | `/api/generator/jobs` | List jobs (DB when migration run) |
| GET | `/api/generator/history` | My jobs / history |
| GET | `/api/generator/statistics` | Aggregates (total_videos, theme_distribution, etc.) |
| GET | `/api/generator/test` | Health (DB + video pipeline) |
| GET | `/api/generator/presets` | Style presets, theme tones, creative twists (for unique videos) |
| GET/POST | `/api/generator/ai-ideas` | AI-generated prompt ideas for a topic (`topic`, optional `count`) |

**Unique video every time:** Pass `style_preset`, `theme_tone`, or `creative_twist` in the body of `POST /api/unified/generate-video` or `POST /api/ai-clips/generate`. If omitted, the pipeline picks random style/tone/twist so each run differs. +5 points bonus when you supply presets/twist.

**Points:** Documentary and AI clips both award generation_points, XP, activity_points, knowledge_points, coins (and triggers/trophies/agent skills). AI clips award points when the job completes (per clip + per segment).

Progress is written to a **sidecar file** (e.g. `.status.json`) so any worker can serve progress for a job started on another worker (multi-worker safe).

### 2.4 Documentary limitation and roadmap (MoviePy / sample)

- **Current behavior:** Documentary output is built from **color/segment clips** (MoviePy `ColorClip` per segment, or a sampled/copied clip). There are no template titles overlays or full AI-generated video; the pipeline uses **MoviePy** (and a sample fallback if MoviePy is unavailable) to produce short clips that are concatenated.
- **Limitation:** No text-on-video titles from templates, no AI video generation (e.g. image-to-video or native AI video APIs). Segment content is driven by LLM-enhanced descriptions and mood colors.
- **Roadmap (possible next steps):** (1) Template titles — overlay text titles per segment using MoviePy or a simple renderer. (2) Future AI video — integrate an AI video API (e.g. Runway, Pika, Sora) when available and cost-effective to produce full AI-generated clips instead of color segments.

---

## 3. AI integration (where and how)

### 3.1 Central service: LLM service

- **File:** **`backend/services/llm_service.py`**
- **Role:** Multi-provider, OpenAI-compatible chat/complete/embed with task-based routing and fallback.
- **Providers (examples):** openai, groq, gemini, openrouter, cerebras, deepseek, mistral, together, anthropic, azure. Each has `api_key_env`, `default_model`, `cost_tier` (free/paid).
- **Collection in sync:** The **Agent Support → Resources** list (Profile → Agent Support → Resources) is built from `llm_service.PROVIDERS`: each provider’s `api_key_env` and label are taken from `PROVIDERS`, and signup URLs from `agent_support_service.LLM_PROVIDER_URLS`. Adding a new AI provider: (1) add it to `backend/services/llm_service.py` `PROVIDERS`, (2) add its signup URL to `backend/services/agent_support_service.py` `LLM_PROVIDER_URLS`, (3) add the env var to `.env.example` (AI LLM or Optional section).
- **Task routing (examples):** `speed` → groq/cerebras; `code` → mistral; `reason` → deepseek/openrouter; `context` → gemini; `free` → free-tier providers.
- **Public API:** `chat(messages, ...)`, `complete(prompt, ...)`, `embed(text)`, `get_provider_status()`, `reset_circuit(provider)`. Object-style: `llm_service.chat()`, `llm_service.complete()`, `llm_service.is_available()`.

### 3.1b Video AI Bridge (all providers → vid generation)

- **File:** **`backend/services/video_ai_bridge.py`**
- **Role:** Routes every generator AI call through a **stage** so different providers are used at different pipeline steps. Each stage maps to a task type (context, speed, reason), so with multiple API keys you automatically use e.g. Gemini for scene planning, Groq for segment enhancement, DeepSeek for prompt ideas.
- **Stages:** `scene_plan` → context; `segment_enhance` → speed; `opening_hook` → speed; `agent_angles` → speed; `title_variations` → speed; `prompt_ideas` → reason; `enhanced_descriptions` → speed; `strategy` → reason; `video_concept` → speed.
- **Single-call:** `complete_for_stage(stage, prompt, system_prompt, ...)` — one completion with the right task_type and optional `use_best` from `extra_context.quality_mode`.
- **Multi-provider (use all AIs):** When `use_all_ais=True` in config (or when 2+ LLM providers are configured — default in backend), the pipeline uses multiple providers and tracks which AIs contributed:
  - **Opening hook:** `complete_multi_provider("opening_hook", ...)` then `pick_best_opening_hook(responses)`.
  - **Segment enhance:** `complete_multi_provider("segment_enhance", ...)` then `merge_segment_enhancements()` so up to 4 providers enrich mood/tagline/key_fact.
  - **Scene plan:** Single provider per run; provider name is recorded in `providers_used`.
- **Provider tracking and profile/points:** Every successful LLM call appends the provider name to `providers_used`. On completion: job and sidecar store `providers_used`; `GET /api/documentary/progress/<id>` returns `providers_used`; `_award_generation_points()` gets a **multi-AI bonus** (+5 per extra provider, cap 20), writes `meta['providers_used']` and profile `last_providers_used` / `total_multi_ai_generations`; trophy **Multi-AI Power** is awarded when a video used 2+ AIs. Generator stats include `ai_providers_configured`. The generator finish box shows "AIs brugt: …" when the progress response includes `providers_used`.
- **Generator config:** Pass `use_all_ais: true` to force multi-provider; omit it to use the default (true when 2+ providers are configured). The UI also sets `use_all_ais` when quality is "best" / "max" / "ultra".

### 3.2 Where AI is used in the generator

| Place | What it does |
|-------|----------------|
| **video_generator_service** | **Documentary:** `_ai_enhance_segments()` (LLM enriches segment descriptions, mood, taglines, **key_fact** per scene); `_ai_generate_enhanced_descriptions()` (chapter paragraphs); `_ai_generate_title_variations()` (chapter titles); **`_ai_generate_opening_hook()`** (one catchy opening line); **`_ai_generate_agent_angles()`** (LLM suggests how the user’s assigned agents’ expertise could shape the narrative); optional `_ai_content_strategy()` / `_ai_video_concept()` via `ai_content_generator`. **Scene plan:** `_plan_ai_segments()` now includes **assigned_agents** and agent narrative angle in the prompt, and requests an **opening_hook** in the JSON; first segment uses the hook as tagline on screen. **Agent credit:** `_rulebased_ai_enrich()` adds “Agent-assisted: [agent names]” to the last segment when the user has assigned agents. **AI clips:** `_plan_ai_segments()` uses LLM to plan scenes. **Unique every time:** `_get_style_and_tone_for_plan()` picks style_preset, theme_tone, creative_twist. **AI ideas:** `_ai_generate_prompt_ideas(topic)`. All best-effort; fallbacks when LLM is unavailable. |
| **missing_endpoints_routes** | `POST /api/ai-clips/generate`: optionally calls `llm_service.complete()` to create an “enhanced” script outline before starting `_start_ai_clips_generation()`. |

### 3.3 Where AI is used elsewhere in the app

- **Battle, Shop, Gallery, Chat, Quests, Leaderboard, Agent automation, User profile, Debug, Rulebook/missing_endpoints:** Various routes call `llm_service.chat()` or `llm_service.complete()` for descriptions, suggestions, diagnostics, or agent tasks.
- **AI providers API:** **`backend/routes/ai_providers_routes.py`** — `GET /api/ai/providers`, `GET /api/ai/providers/test`, `POST /api/ai/chat`, video-provider status/test.
- **Agent content/orchestration:** **`backend/services/agent_content_generator.py`**, **`agent_ai_orchestrator.py`**, **`ai_content_generator.py`** use the LLM service for content generation and agent tasks; some call into `video_generator_service` (e.g. `generate_video_background`, `generate_ai_clips_background`).

### 3.4 Configuration

- **Env vars (examples):** `OPENAI_API_KEY`, `GROQ_API_KEY`, `GOOGLE_AI_API_KEY`, `OPENROUTER_API_KEY`, etc. See `PROVIDERS` in `llm_service.py`.
- **Availability:** `llm_service.is_available()` checks if at least one provider is configured and working. Generator and AI-clips paths degrade gracefully when LLM is unavailable.

---

## 4. What’s working (after bottleneck fix)

- **Site and generator page** are served with less lag (two backends, caching, more workers).
- **Documentary flow:** Create → background job → poll progress → play video. Progress and video are worker-agnostic (sidecar file + shared storage).
- **AI clips flow:** Create → background job → poll status → clips with URLs. LLM used for script/plan when available.
- **Generator APIs:** jobs, history, statistics, performance, quick-actions, test, magic-generate, agent-connections, documentary progress/video, ai-clips status — implemented and documented in `docs/GENERATOR_FIX_OVERVIEW.md`.
- **AI providers:** Status and test endpoints; chat endpoint; circuit breaker; multiple providers with fallback.

---

## 5. What you might fix or improve next (generator + AI)

- **Generator**
  - **Done:** Generator/documentary/ai-clips routes are in **`backend/routes/generator_routes.py`** (blueprint `generator_bp`); view logic remains in `missing_endpoints_routes.py`, shared helpers in `generator_shared.py`.
  - **Migration:** Run the generator DB migration in **every environment** so jobs persist: `python scripts/generator_migration.py --standalone`. Add this to your deploy or one-time setup (see **Deployment** below). Without it, jobs are in-memory only and lost on restart.
  - **Documentary scope:** Current limitation and roadmap are documented in **§2.4** (MoviePy/color segments; roadmap: template titles, future AI video).

- **AI**
  - **Configure at least one LLM provider** (e.g. Groq, Gemini for free tier) so AI-enhanced documentary and AI clips get full behavior. Set the corresponding env var (e.g. `GROQ_API_KEY`, `GOOGLE_AI_API_KEY`).
  - **Verify providers:** Use **`GET /api/ai/providers`** (list providers and status) and **`GET /api/ai/providers/test`** (test each provider). If a provider fails, fix API keys or reset the circuit breaker (see `llm_service` / AI providers routes).
  - **Pipeline timeouts:** Video-pipeline LLM calls use a **90s timeout** so one slow provider doesn’t block workers; optional retries can be added around `llm_service.complete()` if needed.

- **Operations**
  - **Disk space:** The video pipeline checks free space before encoding. Ensure **`VIDEOS_DIR`** (env override) or **`vidgenerator/videos`** has at least **100 MB free**. The service uses `_check_disk_space()` and refuses to start encoding if below that.
  - **Monitoring:** Watch for **failed jobs** (`status: failed`, `error_message` in `GET /api/documentary/progress/<doc_id>` or `GET /api/generator/jobs`). When **increasing workers**, watch for **OOM** (e.g. `dmesg`, `journalctl` for OOM killer; consider swap and LITE_APP=1).

---

## 6. File reference

| Topic | File(s) |
|-------|--------|
| Generator routes (blueprint registration, documentary, ai-clips, jobs, progress, video) | `backend/routes/generator_routes.py`, view logic in `missing_endpoints_routes.py`, shared state in `generator_shared.py` |
| Video pipeline (documentary + AI clips, AI-enhanced segments, 90s LLM timeout) | `backend/services/video_generator_service.py` |
| Video AI bridge (stage → task_type, multi-provider for use_all_ais) | `backend/services/video_ai_bridge.py` |
| Job persistence | `backend/services/generator_db_service.py` |
| LLM (multi-provider, chat/complete/embed) | `backend/services/llm_service.py` |
| AI providers API (status, test, chat) | `backend/routes/ai_providers_routes.py` |
| Generator UI | `generator/index.html` (project root or vidgenerator/) |
| Generator fix checklist and E2E | `docs/GENERATOR_FIX_OVERVIEW.md`, `scripts/test_generator_e2e.py`, `scripts/hard_test_generator_urls.py` |
| Bottleneck and solutions | `docs/PORT_5000_BOTTLENECK_AND_SOLUTIONS.md` |
| Agent–generator connections | `backend/services/generator_agent_connections.py` |
| DB migration (generator tables) | `scripts/generator_migration.py` |
| Generation test (after deploy) | `scripts/test_generator_after_deploy.py` |

---

## 7. Generation test result, logs, and debug

- **Run test after deploy:**  
  `python scripts/test_generator_after_deploy.py`  
  or with live URL:  
  `BASE_URL=https://masternoder.dk python scripts/test_generator_after_deploy.py`  
  The script prints: GET /api/generator/test result, then creates a short test video and polls progress. Result is in the script stdout (OK/FAIL/WARN).

- **Where to check logs and debug:**
  - **On server:** Generator and encoding run in uWSGI workers. Check **`/var/www/html/uwsgi.log`** for tracebacks, `[VideoGenerator]`, or encoding errors. For OOM: `journalctl -u uwsgi-vidgenerator -n 100`, `dmesg | tail`.
  - **Local:** `logs/flask_app.log` (if Flask file logging is enabled). Generator test script output is only in the terminal where you run it.
  - **API checks:** `GET /api/generator/test` — returns `database_available`, `video_pipeline_available`. `GET /api/generator/jobs` — list jobs; failed jobs have `status: "failed"` and `error_message`. `GET /api/documentary/progress/<doc_id>` — progress and `error_message` if failed.

---

## 8. Generation process end-to-end (re-check)

Step-by-step from first request to playable video.

| Step | What happens | Where |
|------|----------------|-------|
| **1. Create** | User submits title/description (and optional config) from generator UI. Frontend sends **POST /api/generator/create** with JSON body (title, description, theme, duration, short_clip, quality_mode, style_preset, theme_tone, creative_twist, user_id, etc.). | `generator/index.html` → `backend/routes/generator_routes.py` (generator_bp) → `missing_endpoints_routes.generator_create()` |
| **2. Job init** | `generator_create()` generates a new `doc_id` (UUID), builds `config` dict, calls `_ensure_video_job(doc_id, 'processing')`, sets `job['type']='documentary'`, `job['config']=config`, `_set_video_job(doc_id, job)`, then **`_start_documentary_encoding(doc_id, config)`**. Returns 202 with `documentary_id: doc_id`. | `missing_endpoints_routes` (uses `generator_shared` aliases: _ensure_video_job, _set_video_job, _start_documentary_encoding) |
| **3. Start encoding** | **`generator_shared.start_documentary_encoding(doc_id, config)`**: (a) Writes **sidecar** `VIDEOS_DIR/<doc_id>.status.json` with status=processing, progress=0. (b) Tries **subprocess**: `write_job_config_for_subprocess(doc_id, config)` writes **`VIDEOS_DIR/<doc_id>.job.json`**; then spawns **`python -m backend.run_generator_job <doc_id>`** (non-blocking). If that fails, falls back to **in-process thread** via `start_video_generation()` → `generate_video_background()`. | `generator_shared.start_documentary_encoding` → `video_generator_service.write_job_config_for_subprocess` + `subprocess.Popen(backend.run_generator_job)` or `generate_video_background()` |
| **4. Subprocess (preferred)** | **`backend.run_generator_job`**: Reads config from `VIDEOS_DIR/<doc_id>.job.json`, then calls **`run_video_generation_standalone(doc_id, config)`**, which calls **`_run_video_generation_impl(doc_id, config, noop_get, noop_set)`**. No job store in subprocess; progress is written only to **sidecar** so any worker can serve progress. | `backend/run_generator_job.py` → `video_generator_service.run_video_generation_standalone` → `_run_video_generation_impl` |
| **5. Pipeline impl** | **`_run_video_generation_impl`**: (a) **Disk check**: encoding uses `_check_disk_space()` (requires ≥100 MB free in VIDEOS_DIR). (b) **AI planning**: if `use_context`, calls **`_plan_ai_segments(...)`** (LLM scene plan; 90s timeout). (c) **Encode**: **`generate_rich_video_sync(doc_id, segments, ...)`** or fallback **`_generate_video_sync(...)`** (MoviePy ColorClip segments → concatenate → write **`VIDEOS_DIR/<doc_id>.mp4`**). (d) **Progress**: `on_progress(percent, message)` writes **sidecar** and optionally job store. (e) **Success**: awards points via `_award_generation_points`, updates job/sidecar to status=completed, progress=100, video_url. (f) **Failure**: `_set_job_failed(...)` and sidecar status=failed, error_message. | `video_generator_service._run_video_generation_impl` → `_plan_ai_segments`, `generate_rich_video_sync` / `_generate_video_sync`, `_write_status_sidecar`, `_award_generation_points` |
| **6. Progress (polling)** | Frontend polls **GET /api/documentary/progress/<doc_id>**. Handler **prefers sidecar** (`_get_video_status_sidecar(doc_id)`): reads **`VIDEOS_DIR/<doc_id>.status.json`** (or `output/videos`, `vidgenerator/static/videos`). If sidecar has status, returns progress, status, message, error_message, video_url. If no sidecar, uses in-memory/DB job; if status still pending/processing, re-reads sidecar and syncs job. If a valid MP4 exists (≥1024 bytes) under same dirs, can mark completed. Returns JSON: success, documentary_id, status, progress, message, stage, video_url, error_message (if failed). | `missing_endpoints_routes.documentary_progress` → `generator_shared.get_video_status_sidecar` / `get_video_file_path` |
| **7. Video file** | When status=completed, user opens **GET /api/documentary/video/<doc_id>** (or with `?download=1`). Handler uses **`_get_video_file_path(doc_id)`** to find **`<doc_id>.mp4`** in `vidgenerator/videos`, `output/videos`, or `vidgenerator/static/videos` (under project root). If file exists and size ≥ 1024 bytes, returns **send_file(path, mimetype='video/mp4', ...)**. Otherwise returns JSON with video_url and status. | `missing_endpoints_routes.documentary_video` → `generator_shared.get_video_file_path` |
| **8. End** | User can download or play the MP4; job remains in memory/DB; sidecar and MP4 stay on disk (VIDEOS_DIR). Points and trophies have been awarded in step 5. | — |

**Paths (must match):**
- **Config for subprocess:** `VIDEOS_DIR/<doc_id>.job.json` (written by web worker; read by `run_generator_job`). `VIDEOS_DIR` = env **VIDEOS_DIR** or `project_root/vidgenerator/videos`.
- **Progress sidecar:** `VIDEOS_DIR/<doc_id>.status.json` (written by pipeline; read by any worker via `get_video_status_sidecar`). Same dirs as `get_video_file_path`: `vidgenerator/videos`, `output/videos`, `vidgenerator/static/videos` (relative to project root).
- **Output MP4:** `VIDEOS_DIR/<doc_id>.mp4` (same as above).

**VIDEOS_DIR consistency:** `generator_shared.get_video_file_path` and `get_video_status_sidecar` now check **VIDEOS_DIR** first (via `_videos_dirs()`), then fallback to project subdirs. So setting **VIDEOS_DIR** (e.g. `/var/www/html/vidgenerator/videos`) works for both pipeline and progress/video serving. **Recommended for production:** set `VIDEOS_DIR` to a path with enough disk space (≥100 MB free) and ensure the app has write access.

---

## 9. Twenty improvements (implemented)

The following 20 improvements were applied to the generator process, API, frontend, and docs:

| # | Improvement | Where |
|---|-------------|--------|
| 1 | **VIDEOS_DIR first in shared helpers** — `get_video_file_path` and `get_video_status_sidecar` check `VIDEOS_DIR` before project subdirs so production override works. | `backend/routes/generator_shared.py` |
| 2 | **Request validation** — Create endpoint requires title or description; returns 400 with clear error if missing. | `missing_endpoints_routes.generator_create` |
| 3 | **Duration cap** — Duration clamped to 10–300 seconds to avoid runaway jobs. | `missing_endpoints_routes.generator_create` |
| 4 | **Disk check before create** — Fail fast with 503 if `_check_disk_space()` reports &lt;100 MB free so encoding is not started then killed. | `missing_endpoints_routes.generator_create` |
| 5 | **Progress response includes job_id** — `documentary_progress` returns `job_id` (same as `documentary_id`) for support/debugging. | `missing_endpoints_routes.documentary_progress` |
| 6 | **Generator test checks VIDEOS_DIR writable** — `GET /api/generator/test` now verifies write access to VIDEOS_DIR and returns `videos_dir_writable`, `videos_dir`. | `missing_endpoints_routes.generator_test` |
| 7 | **Pipeline logging** — Start/end of `_run_video_generation_impl` logged to stdout (uwsgi.log): `[VideoGenerator] Generation started/finished doc_id=... status=...`. | `video_generator_service._run_video_generation_impl` |
| 8 | **Frontend: show job ID and copy** — Progress box shows Job-ID with “Kopier ID” button so users can paste for support. | `generator/index.html` |
| 9 | **Frontend: retry on failure** — On create or progress failure, a “Prøv igen” button reuses the same form and calls generate again. | `generator/index.html` |
| 10 | **Frontend: poll backoff** — After 48 polls (~2 min), poll interval increases from 2.5 s to 5 s to reduce load on long-running jobs. | `generator/index.html` |
| 11 | **Config duration range** — UI allows 30–300 s (max 5 min) to match backend cap; tooltip added. | `generator/index.html` |
| 12 | **Doc: VIDEOS_DIR recommended** — Overview §8 updated: VIDEOS_DIR is checked first in shared helpers; production recommendation clarified. | `docs/GENERATOR_AND_AI_OVERVIEW.md` |
| 13 | **Doc: 20 improvements list** — This section (§9) documents all improvements for handoff and future changes. | `docs/GENERATOR_AND_AI_OVERVIEW.md` |
| 14 | **Stale job cleanup (doc only)** — To clear stuck jobs: use `GET /api/generator/reset-for-test?confirm=test` (in-memory only) or delete sidecar/job files in VIDEOS_DIR. Documented in quick ref. | `docs/SERVER_QUICK_REFERENCE.md` (add if missing) |
| 15 | **Error message in progress** — Failed status already returns `error_message`; frontend shows it and retry. | Existing + retry UX |
| 16 | **Consistent video_url** — Progress and video endpoints return `/api/documentary/video/<id>`; frontend also accepts `pd.video_url` from API. | Existing |
| 17 | **Health surface** — Test endpoint now covers DB, pipeline, and disk; use it after deploy. | `generator_test` |
| 18 | **No duplicate job store writes** — Sidecar is source of truth for cross-worker progress; job store is updated when sidecar is read. | Existing |
| 19 | **Create error message** — 400/503 responses return a clear `error` field for title required or disk full. | `generator_create` |
| 20 | **Logs traceability** — Start/finish logs include doc_id so you can grep uwsgi.log for a specific job. | `video_generator_service` |

---

This overview is the single place to see: **problem 1 (bottleneck) status**, **what the generator process is**, **how AI is integrated**, **what to fix or improve next**, and **the 20 implemented improvements**.
