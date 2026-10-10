# Platform backlog (MasterNoder.dk)

This list tracks follow-ups after the gallery, shop, starmap25, leaderboard, agents, themes (Metallica / WW1 / WW2), Technologi/metal, and generator–profile points alignment work.

**Last refreshed:** 2026-09-30 · Living map: [README.md](README.md) · MN2 detail: [MN2_TODO.md](MN2_TODO.md)

## Recent platform notes (repo — verify on deploy)

- **Monetization revenue tracks** — `data/monetization_revenue_tracks.json` (tiers A–E) + streams/recap services. Narrative checklist: [MN2_TODO.md § Monetization machine](MN2_TODO.md#monetization-machine--revenue-tracks).
- **Quests (90 levels)** — `quest_system.py` progression (9×10) + `quest_page` API routes in repo; confirm registration/UI on the branch you ship before treating as live.
- **Shop / auction** — `shop_auction_service` + `/api/shop/auction/*` (fees / listings / buy). Ideas layer: [SHOP_MONETIZATION_V92.md](SHOP_MONETIZATION_V92.md).
- **API / crypto profile** — `generator_api_crypto_service` (profile + daily MN2 caps) with unit tests; generator API tiers via monetization expansion routes.
- **Create App** — deploy handoff: [DEPLOY_CREATE_APP_RELEASE.md](DEPLOY_CREATE_APP_RELEASE.md) (laptop/SSH).
- **Google Play** — casino TWA/Capacitor shell + assetlinks checklist: [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md). Broader podcast/app vision still deferred below — **do not** treat Play Store listing as done.

## Done in this round

- [x] **Podcast vertical (web)** — `/podcast` hub with BBCG theme, verified sound (`sound-check`, stream repair, Sound Lab), AI generate/encode, MN2 rewards, episode + news comments, 24-site portal strip, RSS (`/api/podcast/rss.xml`), transcripts, chapters, queue, leaderboard, bubble visualizer. **33 tests** (`test_podcast.py` + `test_podcast_routes.py`). Docs: `docs/PODCAST.md`.
- [x] **Generator UI:** Pre-flight checklist (LLM + Video AI + Agents), AI Power section with "Use all AIs" toggle and provider grid (LLM + video chips), quality options (Bedst/Max for multi-AI), Updates changelog, Agent Support link.
- [x] **Leaderboard UI routes:** `GET /api/leaderboard/all`, `/api/leaderboard/categories`, `/api/leaderboard/<system>` with `points` + `username` on rows; catch-all registered after static routes so `/top10` and `/player/...` still work.
- [x] **Star Map 25:** investigation rewards use `STAR_MAP_INVESTIGATION_MULTIPLIER` (1.2); status JSON includes `investigation_reward_multiplier`.
- [x] **Themes:** Metallica, WW1, WW2 in `themes_list`; unlock levels in `themes_user` (`ww1`/`ww2` at 5, `metallica` at 6).
- [x] **Generator awards:** `GENERATION_POINTS_PER_VIDEO` / `PER_CLIP` raised (55 / 28) so profile generation_points tracks a slightly higher tier.
- [x] **Gallery:** API health line in header; shop: catalog status line; metal (Technologi): hub links; agents: fetch retry helper; starmap25: Season 2 banner.
- [x] **Script:** `scripts/service_check_all_components.py` for HTTP probes (set `PLATFORM_BASE_URL`).
- [x] **PR stack #21–#27 merged** — MN2 waterfall split on `main` (2026-06-23).
- [x] **Deploy + apply_updates** — PR #29 `--ask-pass` path; `apply_updates.py` verified on prod (2026-06-23).

## Short-term

- [ ] **Deploy**: Include updated static pages (`gallery`, `shop`, `starmap25`, `metal`, `agents`, `leaderboards`) and backend routes in your deploy manifest; restart the app workers that serve API + static.
- [ ] **Themes**: Add optional `vidgenerator/static/img/themes/` previews for `metallica`, `ww1`, `ww2`; add CSS under `vidgenerator/static/themes/` if you want distinct looks in the generator UI.
- [ ] **Leaderboard**: Wire timeframe filters if the UI sends `timeframe=` (currently ignored); add tests for `/api/leaderboard/generation` vs unified DB field names.
- [ ] **Star Map 25**: If JSON `point_value` should be the single source of truth without multiplier, set multiplier to `1.0` and bump `data/star_map_25.json` values instead.
- [ ] **Points audit**: Run one full generation job and confirm `GET /api/points/comprehensive` (or profile UI) shows the same delta as `_award_generation_points` for the same job.
- [ ] **Quests UI**: Confirm `quest_page` blueprint is registered where you expect and that a player-facing progression UI is deployed (90-level service exists in repo).

## Medium-term

- [x] **Gallery** (done): Server-side pagination and caching for `/api/gallery/list` — added `_list_videos_cached()` with TTL (GALLERY_CACHE_TTL_SEC); list endpoint uses cache; pagination already supported.
- [x] **Shop** (done): Feature flag `USE_SHOP_V3` (env); `GET /api/shop/config` returns `use_shop_v3`; shop UI fetches config and uses shop-v3 or game/shop accordingly; fallback on 5xx.
- [x] **Agents** (done): `user_agent_skills.get_user_skills()` seeds balanced path (content_generator, analytics, learning, **reporter_agent** with `broadcast` + `news_report_ingredients`, 10 skills) when no file exists; **`POST /api/agents/user-skills/maintenance-inactive`** trims stale files (batch 10); **`/api/agents/reporter/knowledge-ingredients`** + `cron/knowledge_sharing_report.sh` for knowledge-sharing report ingredients. See `docs/AGENTS_SKILLS_SYNC.md`.
- [x] **Star Map 25** (done): `starmap25/index.html` and `game/index.html` expose `investigation_reward_multiplier`; show multiplier stat box, reward formula (base × mult = awarded) on each point card.

## Google Play Store app — **deferred / gated**

- **Podcast / general app vision:** saved for later. Spec when resumed: **[PODCAST.md](PODCAST.md)** § Google Play Store app. Todo id: `a1b2c3d4-e5f6-7890-abcd-ef1234567890` in `data/todos/todos.json`. Do not start until explicitly scheduled.
- **Casino Android shell:** follow **[CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md)** after Play developer account + App Signing SHA for `assetlinks.json`. Revenue-track JSON may label a Google Play track as inventory “live”; that is **not** the same as store listing approval.

## Ops / security

- [ ] Rotate any credentials that appear in deployment scripts; prefer env-only secrets.
- [ ] Run `python scripts/service_check_all_components.py` after deploy (`PLATFORM_BASE_URL=https://masternoder.dk` or `http://127.0.0.1:5000` on server). MN2-heavy checks: omit `PLATFORM_SKIP_SLOW_CHECKS` for full coverage, or set `PLATFORM_SKIP_SLOW_CHECKS=1` for a faster pass (skips payment-health, integration-health, generation-health).
