# Platform backlog (MasterNoder.dk)

This list tracks follow-ups after the gallery, shop, starmap25, leaderboard, agents, themes (Metallica / WW1 / WW2), Technologi/metal, and generator–profile points alignment work.

## Done in this round

- **Podcast vertical (web)** — `/podcast` hub with BBCG theme, verified sound (`sound-check`, stream repair, Sound Lab), AI generate/encode, MN2 rewards, episode + news comments, 24-site portal strip, RSS (`/api/podcast/rss.xml`), transcripts, chapters, queue, leaderboard, bubble visualizer. **33 tests** (`test_podcast.py` + `test_podcast_routes.py`). Docs: `docs/PODCAST.md`.
- **Generator UI:** Pre-flight checklist (LLM + Video AI + Agents), AI Power section with "Use all AIs" toggle and provider grid (LLM + video chips), quality options (Bedst/Max for multi-AI), Updates changelog, Agent Support link.
- Leaderboard UI routes: `GET /api/leaderboard/all`, `/api/leaderboard/categories`, `/api/leaderboard/<system>` with `points` + `username` on rows; catch-all registered after static routes so `/top10` and `/player/...` still work.
- Star Map 25: investigation rewards use `STAR_MAP_INVESTIGATION_MULTIPLIER` (1.2); status JSON includes `investigation_reward_multiplier`.
- Themes: Metallica, WW1, WW2 in `themes_list`; unlock levels in `themes_user` (`ww1`/`ww2` at 5, `metallica` at 6).
- Generator awards: `GENERATION_POINTS_PER_VIDEO` / `PER_CLIP` raised (55 / 28) so profile generation_points tracks a slightly higher tier.
- Gallery: API health line in header; shop: catalog status line; metal (Technologi): hub links; agents: fetch retry helper; starmap25: Season 2 banner.
- Script: `scripts/service_check_all_components.py` for HTTP probes (set `PLATFORM_BASE_URL`).

## Short-term

1. **Deploy**: Include updated static pages (`gallery`, `shop`, `starmap25`, `metal`, `agents`, `leaderboards`) and backend routes in your deploy manifest; restart the app workers that serve API + static.
2. **Themes**: Add optional `vidgenerator/static/img/themes/` previews for `metallica`, `ww1`, `ww2`; add CSS under `vidgenerator/static/themes/` if you want distinct looks in the generator UI.
3. **Leaderboard**: Wire timeframe filters if the UI sends `timeframe=` (currently ignored); add tests for `/api/leaderboard/generation` vs unified DB field names.
4. **Star Map 25**: If JSON `point_value` should be the single source of truth without multiplier, set multiplier to `1.0` and bump `data/star_map_25.json` values instead.
5. **Points audit**: Run one full generation job and confirm `GET /api/points/comprehensive` (or profile UI) shows the same delta as `_award_generation_points` for the same job.

## Medium-term

1. **Gallery** (done): Server-side pagination and caching for `/api/gallery/list` — added `_list_videos_cached()` with TTL (GALLERY_CACHE_TTL_SEC); list endpoint uses cache; pagination already supported.
2. **Shop** (done): Feature flag `USE_SHOP_V3` (env); `GET /api/shop/config` returns `use_shop_v3`; shop UI fetches config and uses shop-v3 or game/shop accordingly; fallback on 5xx.
3. **Agents** (done): `user_agent_skills.get_user_skills()` seeds balanced path (content_generator, analytics, learning, **reporter_agent** with `broadcast` + `news_report_ingredients`, 10 skills) when no file exists; **`POST /api/agents/user-skills/maintenance-inactive`** trims stale files (batch 10); **`/api/agents/reporter/knowledge-ingredients`** + `cron/knowledge_sharing_report.sh` for knowledge-sharing report ingredients. See `docs/AGENTS_SKILLS_SYNC.md`.
4. **Star Map 25** (done): `starmap25/index.html` and `game/index.html` expose `investigation_reward_multiplier`; show multiplier stat box, reward formula (base × mult = awarded) on each point card.

## Google Play Store app — **deferred**

Saved for later. Full spec when resumed: **[docs/PODCAST.md](PODCAST.md)** § Google Play Store app. Todo id: `a1b2c3d4-e5f6-7890-abcd-ef1234567890` in `data/todos/todos.json`. Do not start until explicitly scheduled.

## Ops / security

- Rotate any credentials that appear in deployment scripts; prefer env-only secrets.
- Run `python scripts/service_check_all_components.py` after deploy (`PLATFORM_BASE_URL=https://masternoder.dk` or `http://127.0.0.1:5000` on server). MN2-heavy checks: omit `PLATFORM_SKIP_SLOW_CHECKS` for full coverage, or set `PLATFORM_SKIP_SLOW_CHECKS=1` for a faster pass (skips payment-health, integration-health, generation-health).
