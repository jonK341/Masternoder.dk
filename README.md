# MasterNoder.dk  <!-- pragma: allowlist secret -->

AI video generator + gamified point/achievement layer, built around an MN2 masternode crypto economy (hosting, staking, a casino, an exchange, and a P2P market) with an agent/AI automation layer on top.

**For the full picture — current state, architecture, and where everything lives — see [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md).**
**For active priorities, see [`docs/ROADMAP_Q3_2026.md`](docs/ROADMAP_Q3_2026.md).**

## Quick start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt          # base + test/debug tooling
.venv/bin/python -m pip install -r requirements-optional.txt # only if working on AI/LLM provider features
python run.py
```

Serves on `http://localhost:5000`.

## Repo layout

```
backend/      # Flask routes (backend/routes/) and business logic (backend/services/)
src/          # Flask app core / factory
scripts/      # Ops, deploy, and one-off automation scripts (large — see docs/ROADMAP_Q3_2026.md Month 2)
docs/         # All documentation — see docs/README.md for the index, docs/archive/ for superseded history
tests/        # pytest suite (unit/integration/performance/slow markers in pytest.ini)
systemd/      # uwsgi + profit-daemon systemd unit files
data/, migrations/, cron/   # config data, DB migrations, cron job definitions
```

## Tests

```bash
pytest tests/unit
```

## Documentation

Start with [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md), then [`docs/README.md`](docs/README.md) for the full topic index. Live, frequently-updated backlogs: [`docs/MN2_TODO.md`](docs/MN2_TODO.md), [`docs/CASINO_TODO.md`](docs/CASINO_TODO.md), [`docs/PLATFORM_TODO.md`](docs/PLATFORM_TODO.md).
