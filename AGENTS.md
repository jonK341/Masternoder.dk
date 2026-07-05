# AGENTS.md

## Cursor Cloud specific instructions

MasterNoder.dk is a single Python 3.12 Flask backend (application factory in `src/app/__init__.py`, entry point `run.py`). It serves a large gamified platform (~154 blueprints: users, points/XP, trophies, battles, shop, agents) plus the flagship `/vidgenerator` AI video generator. There is no separate frontend build; HTML/JS is served directly by Flask.

### Environment
- A Python virtualenv lives at `.venv` (gitignored). The update script creates it and installs `requirements.txt`. Always run tools via `.venv/bin/python` / `.venv/bin/pytest`.
- `requirements.txt` = base dev runtime + test/debug tooling. `requirements-optional.txt` is the heavy optional stack (torch, transformers, selenium, moviepy, etc.) — do NOT install it wholesale unless you specifically need those features.
- A local dev `.env` is optional. With no `.env`, the app runs in debug/dev mode and stores data in SQLite at `instance/database.db` (auto-created). `.env.example` defaults to `FLASK_ENV=production`; do not copy it verbatim for local dev.

### Run / lint / test
- Run the dev server: `.venv/bin/python run.py` (listens on `0.0.0.0:5000`; falls back to `5003` if 5000 is busy). Health check: `GET /api/health` → `{"status":"healthy"}`. Main UI: `/vidgenerator/`, `/vidgenerator/gallery`, `/vidgenerator/generator`.
- Lint (matches CI `.github/workflows/python-package-conda.yml`): `.venv/bin/python -m flake8 . --select=E9,F63,F7,F82`. Note: `flake8` is not in requirements (install ad-hoc); `backend/routes/debugger_builder.py` crashes pycodestyle's W605 check, so exclude it: `--exclude=backend/routes/debugger_builder.py`. There are pre-existing F821/E999 findings in `scripts/` and some `backend/` files — they are not caused by env setup.
- Tests: `.venv/bin/python -m pytest tests/unit -q` (~5–6 min, 900+ tests). ~67 tests fail on a clean checkout for pre-existing app reasons (missing in-repo modules, assertion mismatches, features needing API keys) — not dependency problems. `pytest` basetemp is pinned to `.pytest-tmp-local` via `tests/conftest.py`.

### Gotchas
- First request after boot and the first hit to any not-yet-registered endpoint are slow (an auto-fix-404 / "Register Intelligence" middleware lazily creates handlers). Steady-state reads are ~3s.
- The flagship video generation (`POST /api/generator/create` and the AI-clips endpoints) requires at least one LLM provider API key (e.g. `GROQ_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_AI_API_KEY`); without a key the job writes a `*.status.json` sidecar with `"error_message": "No AI provider API keys configured"`. `ffmpeg` is available system-wide, but real encoding also needs the optional `moviepy` + `imageio-ffmpeg` packages.
- `POST /api/user/create` actually creates and persists the user (see `user_accounts` / `user_profiles` tables) but returns `400 {"error":"User already exists"}` even for brand-new IDs — a pre-existing quirk of the onboarding flow, not a failure. Verify via the DB, not the HTTP body.
