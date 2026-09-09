# Deploy handoff — Create App + frontpage (PR #81)

**Status:** Deploy-ready. Do **not** deploy from cloud agent — run from laptop when ready.

**Branch:** `cursor/super-encoder-create-app-2eea`  
**PR:** number 81

## What ships

| Area | Paths |
|------|--------|
| Create App hub | `create-app/`, `backend/routes/create_app_routes.py`, `backend/services/create_app_*.py`, `backend/services/super_encoder_service.py` |
| Instant MN2 click rewards | `backend/routes/click_game_routes.py`, `backend/services/click_mn2_rewards_service.py`, `static/js/click-through-game.js`, `game/index.html` |
| Frontpage layout | `index.html`, `static/css/frontpage-home.css`, `static/js/frontpage-home.js`, `static/js/game-hub-panel.js` |
| Nav + lab/podcast entry | `static/js/navigation-toolbar.js`, `lab/index.html`, `podcast/index.html` |
| Data seeds | `data/mn2_config.json`, `data/create_apps.json`, `data/lab_projects_seed.json`, `data/podcast_episodes.json`, `data/agent_leaderboard_rewards.json` |
| Podcast TWA scaffold | `mobile/podcast-twa/*` |

## Pre-deploy checks (laptop)

```bash
git checkout cursor/super-encoder-create-app-2eea
git pull origin cursor/super-encoder-create-app-2eea

.venv\Scripts\python.exe -m pytest tests/unit/test_create_app_super_encoder.py tests/unit/test_click_mn2_rewards.py tests/unit/test_frontpage_portal_links.py -q
```

Expected: **17 passed**.

## Deploy command (recommended)

From repo root on laptop (with `DEPLOY_PASS` or `--ask-pass`):

```bash
python scripts/deploy.py create_app_release static_pages --ask-pass
```

- `create_app_release` — backend routes, services, data seeds, key HTML/JS/CSS
- `static_pages` — all root `*/index.html` + `static/js|css` (nginx cache clear + reload)

### Alternative (full restart wrapper)

```bash
python scripts/deploy_all_and_restart_uwsgi.py --manifest create_app_release static_pages
```

## Post-deploy smoke test

```bash
# Set BASE_URL to production host (see .env or docs/DEPLOY_PREP.md)
python scripts/test_url_timing.py
```

Manual URLs:

| URL | Expect |
|-----|--------|
| `/` | Compact frontpage, hero without headline/graphic overlap |
| `/create-app/` | Super Encoder nr. 1 hub |
| `/api/create-app/encoder-hub` | JSON `success: true` |
| `/api/game/click-game/instant-reward` | POST returns MN2 instant reward |
| `/api/game-hub/overview?user_id=default_user` | JSON overview |

## Runtime data (do not deploy from dev)

These are created on server at runtime — **not** in git:

- `data/click_game/*.json`
- `data/trophy_income/*.json`
- `data/trophy_quests/*.json`
- `data/mn2_ledger.json` (ledger mutations)

## Merge order

1. Review + merge PR #81 to `main`
2. Pull `main` on laptop
3. Run deploy command above
4. Run post-deploy smoke test
