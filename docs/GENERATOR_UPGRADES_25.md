# Generator — 25 Upgrades

**Purpose:** Prioritized upgrade plan for the AI Video Generator (`/generator`, `generator/index.html`, `backend/services/video_generator_service.py`).

**Status:** Phase 1–3 complete (2026-06-17)  
**Last updated:** 2026-06-17  
**Related:** [GENERATOR_AND_AI_OVERVIEW.md](./GENERATOR_AND_AI_OVERVIEW.md) · [GENERATOR_PAGE_AND_POINTS_OVERVIEW.md](./GENERATOR_PAGE_AND_POINTS_OVERVIEW.md) · [plans/generator_page_roadmap.plan.md](./plans/generator_page_roadmap.plan.md) · M8 #59 (Discord Generator Showcase)

---

## Review summary (current state)

| Area | Working today | Gaps |
|------|---------------|------|
| **Create flow** | Documentary + AI clips, subprocess encoding, sidecar progress, disk pre-check, duration cap, entitlement reserve | Queue disabled (`queue_enabled: false`); UI missing several wired APIs |
| **AI pipeline** | Multi-provider LLM bridge, scene plan, segment enrich, animated segments (`_make_animated_segment_clip`), context service + cache | No native AI video in documentary path; template titles still color/animation only |
| **Points / MN2** | 55 pts/video, 28 pts/clip, segment bonus, MN2 pay tiers, finish bonus, refund on failure | Credits 402 not surfaced in UI; settle runs but no “credits used” in finish box |
| **UX** | Magic generate, pre-flight checklist, recent clips, MN2 strip, retry, poll backoff, job ID copy | No stats strip, no AI ideas, presets hardcoded, no queue position, no restart button |
| **Integrations** | AI clips → Discord showcase + platform_news | **Documentary complete does not call `post_generator_showcase`** (clips only) |
| **Ops** | `generator` + `generator_recent` deploy manifests, `/api/generator/test`, COGS metering | DB migration not in default deploy; stale sidecar/MP4 cleanup manual |

**Already shipped (prior “20 improvements”):** VIDEOS_DIR consistency, validation, disk check, job ID in progress, test endpoint disk write, logging, retry UX, poll backoff — see §9 in [GENERATOR_AND_AI_OVERVIEW.md](./GENERATOR_AND_AI_OVERVIEW.md).

---

## The 25 upgrades

| # | Upgrade | Phase | Status |
|---|---------|-------|--------|
| 1 | **Documentary Discord showcase** — call `post_generator_showcase()` on documentary completion (parity with AI clips; M8 #59) | P1 | ✅ Done |
| 2 | **402 credits UX** — on `insufficient_generation_credits`, show required vs available + link to Shop / MN2 strip | P1 | ✅ Done |
| 3 | **AI prompt ideas** — “Suggest prompts” button → `GET/POST /api/generator/ai-ideas?topic=` fills title/description | P1 | ✅ Done |
| 4 | **Dynamic presets** — load style/tone/twist options from `GET /api/generator/presets` instead of hardcoded `<select>` | P1 | ✅ Done |
| 5 | **Stats strip** — header row: total videos, success rate, themes used (`/api/generator/statistics` + `/performance`) | P1 | ✅ Done |
| 6 | **Per-segment progress** — show `stage` / “Segment 2/5” from progress poll in `#progressStage` | P1 | ✅ Done |
| 7 | **Profile context toggle** — checkbox “Include my profile & agents” → `use_context` / `include_points_in_clip` | P1 | ✅ Done |
| 8 | **Restart failed job** — “Prøv igen med samme config” → `POST /api/documentary/restart/<doc_id>` | P1 | ✅ Done |
| 9 | **Finish box: credits + points** — show `points_earned`, providers used, credits debited, MN2 earn note | P1 | ✅ Done |
| 10 | **Content categories** — optional category picker from `GET /api/content-categories/list` (Rulebook V12) | P1 | ✅ Done |
| 11 | **Enable job queue (prod)** — set `data/generator_config.json` `queue_enabled: true`; show position via `/api/generator/queue-status` | P2 | ✅ Done |
| 12 | **Queue UI** — “I kø: #3” while processing; MN2/express jobs show priority boost | P2 | ✅ Done |
| 13 | **Generation health widget** — compact status from `/api/generator/generation-health` (LLM + pipeline ready) | P2 | ✅ Done |
| 14 | **Auto gallery index** — on complete, append job to gallery list JSON so new videos appear without manual clean | P2 | ✅ Done |
| 15 | **Stale artifact cleanup** — cron/script: delete failed `.status.json` / orphan `.job.json` older than 7 days; keep completed MP4s | P2 | ✅ Done |
| 16 | **Deploy: run migration** — add `python scripts/generator_migration.py --standalone` to deploy checklist / post-deploy hook | P2 | ✅ Done |
| 17 | **Unified points refresh** — load `unified-point-counters.js`; refresh on finish via canonical `/api/points/all` | P2 | ✅ Done |
| 18 | **Achievement toast on finish** — fire `videoGenerated` event + optional trophy toast when stats tracker detects new unlock | P2 | ✅ Done |
| 19 | **Share actions** — finish links: Copy URL, Open Gallery, Post to Discord (if user linked), Download | P2 | ✅ Done |
| **C0** | **Crypto rewards (MN2)** — base + multi-AI + daily-first + staking bonus on every completion | P2 | ✅ Done |
| 20 | **COGS-aware pricing hint** — surface `GET /api/generator/pricing` advisory in MN2 strip (“ref job ≈ X MN2”) | P3 | ✅ Done |
| 21 | **Agent-native tools** — capability map: `generator_create`, `generator_progress`, `generator_history`, `generator_ai_ideas` | P3 | ✅ Done |
| 22 | **Game Hub quest** — weekly “Generate 1 video” quest progress from generator completion events | P3 | ✅ Done |
| 23 | **Video AI in clips tab** — when HeyGen/Runway/Replicate configured, offer “avatar clip” sub-mode on Clip tab | P3 | ✅ Done |
| 24 | **Theme unlocks by shop** — extend `themes_user` with purchased theme IDs from shop inventory, not level-only | P3 | ✅ Done |
| 25 | **Ops dashboard row** — add generator queue depth + last-24h success rate to unified dashboard / ops stream | P3 | ✅ Done |

---

## Phase guide

### Phase 1 — UI parity (1–10)

Wire APIs that already exist but the page does not use. Low risk, high visibility. Single deploy: `python scripts/deploy.py generator --ask-pass`.

**Acceptance:** Create → progress shows segment stage → finish box shows points + providers → failed job can restart → 402 shows shop link.

### Phase 2 — Reliability & discoverability (11–19)

Turn on queue in production, persist jobs to DB, keep gallery and points in sync, reduce disk clutter.

**Acceptance:** Two concurrent creates queue instead of saturating uWSGI; completed videos appear in gallery within one refresh; old failed sidecars pruned weekly.

### Phase 3 — Ecosystem (20–25)

MN2/COGS alignment, agent parity, Game Hub quests, premium video-AI path, ops visibility.

**Acceptance:** Agent can create and poll a video via documented tools; Game Hub quest increments on completion; ops stream shows queue depth.

---

## Implementation notes (by item)

### 1 — Documentary Discord showcase

In `video_generator_service._run_video_generation_impl`, after `_write_status_sidecar(..., status="completed")`, mirror the AI-clips block:

```python
from backend.services.discord_m8_streams import post_generator_showcase
post_generator_showcase(job_id=doc_id, title=str(title)[:120], user_id=user_id)
```

Non-blocking; already rate-limited in `discord_m8_streams`.

### 3 — AI prompt ideas

UI: button beside title field → `POST /api/generator/ai-ideas` with `{ topic, count: 5 }` → populate title/description from first idea.

### 11 — Enable queue

```json
// data/generator_config.json
{ "queue": { "queue_enabled": true, "max_concurrent": 1, "mn2_paid_bonus": 30 } }
```

Or `VIDEO_JOB_QUEUE=1` on server. Verify with `GET /api/generator/queue-status`.

### 16 — Migration in deploy

Add to [DEPLOYMENT.md](./DEPLOYMENT.md) generator section:

```bash
python scripts/generator_migration.py --standalone
```

Without this, jobs are in-memory only and lost on uWSGI restart.

---

## Deploy

```powershell
# UI + static
python scripts/deploy.py generator --ask-pass

# Backend pipeline + routes (includes video_generator_service)
python scripts/deploy.py generator_recent --ask-pass
```

**Smoke test:**

```powershell
python scripts/test_generator_after_deploy.py
# or
python scripts/hard_test_generator_urls.py --quick
```

---

## Test plan (all 25)

- [ ] Documentary complete posts to `#generator` / platform_news channel
- [ ] Guest + logged-in user: create, poll, play, download
- [ ] Insufficient credits returns 402 with readable UI message
- [ ] AI ideas, presets, content categories load without 404
- [ ] Progress shows segment index when pipeline reports `stage`
- [ ] Restart recovers a failed job with same config
- [ ] Queue enabled: second job waits; MN2 job jumps priority
- [ ] Gallery lists new video after completion
- [ ] Points counters refresh after finish
- [ ] Agent tool can create + poll (parity check)
- [ ] `hard_test_generator_urls.py` full run passes on production

---

## File map

| Concern | Primary files |
|---------|----------------|
| UI | `generator/index.html` |
| Routes | `backend/routes/generator_routes.py`, `missing_endpoints_routes.py` |
| Pipeline | `backend/services/video_generator_service.py`, `backend/run_generator_job.py` |
| Context | `backend/services/generator_context_service.py`, `generator_context_cache.py` |
| MN2 / credits | `generator_mn2_service.py`, `generator_entitlement_service.py` |
| Queue | `backend/services/video_job_queue.py`, `data/generator_config.json` |
| Discord | `backend/services/discord_m8_streams.py` |
| Deploy | `scripts/deploy.py` (`generator`, `generator_recent`) |
| Tests | `scripts/hard_test_generator_urls.py`, `scripts/test_generator_e2e.py` |
