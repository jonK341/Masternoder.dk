# AGENTS.md

## Cursor Cloud specific instructions

MasterNoder.dk is a single Python 3.12 Flask backend (application factory in `src/app/__init__.py`, entry point `run.py`). It serves a large gamified platform (~154 blueprints: users, points/XP, trophies, battles, shop, agents) plus the flagship `/vidgenerator` AI video generator. There is no separate frontend build; HTML/JS is served directly by Flask. <!-- pragma: allowlist secret -->

### Environment
- A Python virtualenv lives at `.venv` (gitignored). The update script creates it and installs deps. Always run tools via `.venv/bin/python` / `.venv/bin/pytest`.
- pip must be run from the repo root. The dev requirements file uses a relative `-r` include of the slim runtime file, so `pip install -r requirements.txt` fails with "Could not open requirements file" when the cwd is not the repo root. The update script `cd`s into the repo root first and installs both files. <!-- pragma: allowlist secret -->
- The slim runtime file (`requirements-*.txt`) holds the core deps; `requirements.txt` adds test/debug tooling. `requirements-optional.txt` is the heavy optional stack (torch, transformers, selenium, …) — do NOT install it wholesale.
- The flagship video generator needs a small subset of the optional stack: `openai` (the OpenAI-compatible client used for ALL LLM providers, incl. Groq/Gemini) plus `moviepy` + `imageio-ffmpeg` for encoding. The update script installs these three; `ffmpeg` itself is already on the system.
- A local dev `.env` is optional. With no `.env`, the app defaults to a local SQLite DB under `instance/` (auto-created). `.env.example` ships deploy-oriented defaults; do not copy it verbatim for local dev.

### Run / lint / test
- Run the dev server: `.venv/bin/python run.py` (listens on `0.0.0.0:5000`; falls back to `5003` if 5000 is busy). Health check: `GET /api/health` → `{"status":"healthy"}`. Main UI: `/vidgenerator/`, `/vidgenerator/gallery`, `/vidgenerator/generator`.
- IMPORTANT when the deploy secret set is injected as env vars: `OUTPUT_DIR`/`UPLOAD_DIR` may point at `/var/www/...` and the deploy-mode flags may be on, which makes `run.py` fail with `Permission denied: '/var/www'` and disables debug. Injected env vars override `.env` (dotenv does not override existing vars). Start with local overrides for the output/upload dirs and dev-mode flags, e.g.: `env OUTPUT_DIR="$PWD/output" UPLOAD_DIR="$PWD/uploads" PRODUCTION=false FLASK_ENV=development FLASK_DEBUG=True .venv/bin/python run.py`. <!-- pragma: allowlist secret -->
- Lint (matches CI `.github/workflows/python-package-conda.yml`): `.venv/bin/python -m flake8 . --select=E9,F63,F7,F82`. Note: `flake8` is not in requirements (install ad-hoc); `backend/routes/debugger_builder.py` crashes pycodestyle's W605 check, so exclude it: `--exclude=backend/routes/debugger_builder.py`. There are pre-existing F821/E999 findings in `scripts/` and some `backend/` files — they are not caused by env setup.
- Tests: `.venv/bin/python -m pytest tests/unit -q` (~5–6 min, 900+ tests). ~67 tests fail on a clean checkout for pre-existing app reasons (missing in-repo modules, assertion mismatches, features needing API keys) — not dependency problems. `pytest` basetemp is pinned to `.pytest-tmp-local` via `tests/conftest.py`.

### Gotchas
- First request after boot and the first hit to any not-yet-registered endpoint are slow (an auto-fix-404 / "Register Intelligence" middleware lazily creates handlers). Steady-state reads are ~3s.
- Flagship video generation (`POST /api/generator/create` and the AI-clips endpoints) requires at least one LLM provider API key (e.g. `GROQ_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_AI_API_KEY`) AND the `openai` package; without a key the job writes a status sidecar (`vidgenerator/videos/<doc_id>.status.json`) whose `error_message` says no AI provider is configured.
- The `POST /api/generator/create` HTTP handler runs monetization/entitlement/MN2-RPC steps before generation; when the deploy secrets carry LIVE flags + a real `MN2_RPC_URL`, that request can hang on unreachable external services. To validate generation itself, call the service layer directly (`backend.services.video_generator_service`) instead of the HTTP endpoint.
- `POST /api/user/create` actually creates and persists the user (see `user_accounts` / `user_profiles` tables) but returns `400 {"error":"User already exists"}` even for brand-new IDs — a pre-existing quirk of the onboarding flow, not a failure. Verify via the DB, not the HTTP body.
