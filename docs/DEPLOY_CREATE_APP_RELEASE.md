# Deploy handoff — Create App release (PR 81)

**Status:** Ready for laptop deploy. Cloud agent does not deploy.

**Branch:** `cursor/super-encoder-create-app-2eea`

## Pre-deploy (laptop)

```bash
git checkout cursor/super-encoder-create-app-2eea
git pull origin cursor/super-encoder-create-app-2eea
.venv\Scripts\python.exe -m pytest tests/unit/test_create_app_super_encoder.py tests/unit/test_click_mn2_rewards.py tests/unit/test_frontpage_portal_links.py -q
```

Expected: 17+ passed (Create App suite now includes finish/join/super-encode tests).

Audit deploy file coverage:

```bash
python scripts/audit_deploy_manifest.py create_app_release static_pages --fail-on-missing
```

## Deploy

```bash
python scripts/deploy.py create_app_release static_pages --ask-pass
```

Alternative:

```bash
python scripts/deploy_all_and_restart_uwsgi.py --manifest create_app_release static_pages
```

## Post-deploy

Follow `docs/DEPLOY_PREP.md` for URL timing checks.

Smoke paths: `/`, `/create-app/`, `/api/create-app/encoder-hub`, `/api/game-hub/overview?user_id=default_user`

## Runtime data (not in git)

- `data/click_game/`
- `data/trophy_income/`
- `data/trophy_quests/`
- `data/mn2_ledger.json` ledger mutations from dev tests
