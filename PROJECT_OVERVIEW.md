# MasterNoder.dk — Project Overview <!-- pragma: allowlist secret -->

**Last verified:** 2026-07-06 · **Purpose:** one place to understand what this project is, what state it's actually in, and where everything else lives. If you read nothing else in this repo, read this file and [`docs/ROADMAP_Q3_2026.md`](docs/ROADMAP_Q3_2026.md).

---

## 1. What this is

MasterNoder.dk is a Flask platform that grew from an AI video-generation tool into a broader crypto-gaming-community ecosystem built around **MN2**, a masternode cryptocurrency. In one sentence: **an AI video generator and gamified point/achievement layer, wrapped around an MN2 crypto economy (masternode hosting, staking, a casino, an exchange, and a P2P market) with a large agent/AI automation layer on top.**  <!-- pragma: allowlist secret -->

That breadth is itself an open strategic question — see [`docs/PROJECT_RETHINK.md`](docs/PROJECT_RETHINK.md), which has not yet been resolved: is the core product the generator, the gamified economy, or the agent layer? Whoever picks this up next should treat that as a live decision, not settled history.

## 2. Current state (verified against `git`/`gh`, not just docs)

Documentation in this repo drifts from reality quickly — several files from January 2026 declare the site fully live and launch-ready with 0% errors, while dated ops logs from months later tell a very different story. Treat the table below, cross-checked directly against GitHub, as more reliable than any single status doc.

| Area | State |
|---|---|
| **Open PRs** | 18 open as of this writing, oldest from 2026-06-20; 3 already show merge conflicts. This is the single biggest near-term risk — see Month 1 of the roadmap. |
| **Live CPU incident** | Root-caused and fixed in an **unmerged** PR (#46): infinite recursion in path-correction middleware + an incompatible points-DB schema were pegging CPU near 100%. Fix verified (~0.1% idle) but not yet deployed. |
| **Casino** | 25 planned feature "waves" are code-complete and merged (PR #43, 2026-07-04). Remaining work is ops: deploy the slice, Play Store listing, live Discord fan-out. |
| **MN2 masternodes** | ~30 hosted/active on the live server. Daemon multi-ping (v1.3) is built but not deployed — this caps how many masternodes in a fleet can go fully `ENABLED`. |
| **Tests** | `pytest tests/unit` — 913 passed / 67 failed / 2 skipped (2026-07-05), a healthier baseline than older docs suggest. |
| **Money-path safety** | **Not yet hardened.** Balance writes in `backend/services/unified_points_database.py` are not atomic/locked, despite real PayPal and MN2 money flowing through shop, hosting, and casino today. This is the top structural risk for the platform, independent of any single bug. |
| **Documentation** | Was ~310 markdown files across the repo root and `docs/`, most written as one-off "task complete" logs at the moment something shipped. Cleaned up 2026-07-06 (this file is part of that cleanup) — see §5. |

Full detail, sequencing, and a 3-month plan to address all of the above: **[`docs/ROADMAP_Q3_2026.md`](docs/ROADMAP_Q3_2026.md)**.

## 3. Architecture map

```
                         nginx  ──┬──►  uwsgi-vidgenerator.service      (:5000, primary)
                                  └──►  uwsgi-vidgenerator-5001.service (:5001, load-spread)
                                          │
                                          ▼
                              Flask app (src/, backend/, wsgi.py)
                                          │
        ┌───────────────┬────────────────┼─────────────────┬──────────────────┐
        ▼               ▼                ▼                 ▼                  ▼
   Generator/       Unified points    MN2 wallet /     Casino engines    Agents / AI
   video pipeline   economy layer     masternode svc   (slots, crash,    (skills, daemons,
   (backend/         (unified_points  (mn2_wallet_      plinko, etc.)     control board)
   services/          _database.py —   service, mn2_
   video_generator    money source     rpc_client,
   _service.py)        of truth)       mn2_ledger)
        │                  │                │                  │                  │
        └──────────────────┴────────────────┴──────────────────┴──────────────────┘
                                          │
                          Exchange / P2P market / profit daemons
                            (backend/services/exchange_*, scripts/all_profit_daemons.py)
                                          │
                          Social / Discord fan-out / camgirls / podcast
```

**Where things actually live:**

| Concern | Path |
|---|---|
| Flask app entry | `run.py`, `wsgi.py` |
| Routes | `backend/routes/` (160+ files — one of the biggest sprawl risks in the codebase) |
| Business logic | `backend/services/` |
| Money source of truth | `backend/services/unified_points_database.py` (`mn2_balance`, `coins`, `*_points`) |
| MN2 crypto | `backend/services/mn2_wallet_service.py`, `mn2_rpc_client.py`, `mn2_ledger.py`, `data/mn2_config.json` |
| Deploy tooling | `scripts/deploy.py` (manifest-based, current), `scripts/apply_updates.py` |
| Ops/automation scripts | `scripts/` (huge — hundreds of one-off and recurring scripts; see §5) |
| Tests | `tests/` (~166 files, `pytest.ini` configured with unit/integration/performance/slow markers) |
| Systemd units | `systemd/*.service` (uwsgi ×2, MN2 profit daemon) |
| Frontend pages | top-level feature directories (`casino/`, `battle/`, `shop/`, `starmap25/`, `explorer/`, `generator/` etc.) — each usually pairs with a `backend/routes/*_routes.py` |

**Live sequencing plan:** [`docs/plans/master_build_orchestrator.plan.md`](docs/plans/master_build_orchestrator.plan.md) ties together the 4 active build plans in `docs/plans/` behind readiness gates (A → B → S → C → D). Gate S — hardening the money path before any more money-touching features ship — is the most important unmet gate right now.

## 4. Major feature areas

| Area | Status doc |
|---|---|
| MN2 / masternode hosting, staking, explorer | [`docs/MN2_TODO.md`](docs/MN2_TODO.md) (most current, updated ~weekly) |
| Casino | [`docs/CASINO_TODO.md`](docs/CASINO_TODO.md) |
| Generator / video / points / shop / leaderboard | [`docs/PLATFORM_TODO.md`](docs/PLATFORM_TODO.md) |
| Exchange / P2P trading | `docs/EXCHANGE_*.md`, part of the MN2 ecosystem plan |
| Game / battle / Star Map / compendium | [`docs/plans/game_and_battle_review.plan.md`](docs/plans/game_and_battle_review.plan.md), `docs/STARMAP25_*.md` |
| Social / Discord / camgirls / podcast | `docs/DISCORD_*.md`, `docs/PODCAST.md` |
| Agents / AI automation layer | `docs/AGENTS_*.md`, part of the open product-direction question in `PROJECT_RETHINK.md` |

## 5. Documentation & repo hygiene (this cleanup)

As of 2026-07-06:
- **~180 stale, point-in-time markdown files** (one-off "X is now complete" logs, dated status snapshots, superseded plans) were moved from the repo root and `docs/` into [`docs/archive/`](docs/archive/README.md). Nothing was deleted — see that folder's README for the full rationale and an index of what's there.
- **~70 one-off JSON/txt test-result dumps and 8 stale deployment tarballs** at the repo root (dead build artifacts and audit-script output with zero ongoing reference value, verified to have no live code dependencies) were removed outright.
- The remaining **132 files in `docs/`** are indexed by topic in [`docs/README.md`](docs/README.md).
- **Root-level Python script sprawl was not touched in this pass** — there are still hundreds of one-off `deploy_*.py`/`fix_*.py`/`restart_*.py` scripts at the repo root (many already superseded by `scripts/deploy.py`). This is tracked as Month 2 work in the roadmap, not resolved here.

If you're a human or an agent picking up work here: **check `docs/MN2_TODO.md`, `docs/CASINO_TODO.md`, and `docs/PLATFORM_TODO.md` for the live backlog**, and `docs/ROADMAP_Q3_2026.md` for how that backlog fits into a larger sequence — don't trust a status claim just because it's in a file named `*_COMPLETE.md` or `*_FINAL.md` without checking its date against these three.

## 6. Running it locally

A full `AGENTS.md` dev-environment guide (venv layout, lint/test commands, known gotchas) is pending merge in PR #45. Until then, the quick version:

```bash
cd /path/to/repo   # requirements.txt uses a relative include; must run pip from repo root
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt          # base + test/debug tooling
.venv/bin/python -m pip install -r requirements-optional.txt # only if working on AI/LLM provider features
python run.py       # serves on :5000
```

## 7. Where to go next

- **Planning / priorities:** [`docs/ROADMAP_Q3_2026.md`](docs/ROADMAP_Q3_2026.md)
- **Live backlogs:** [`docs/MN2_TODO.md`](docs/MN2_TODO.md), [`docs/CASINO_TODO.md`](docs/CASINO_TODO.md), [`docs/PLATFORM_TODO.md`](docs/PLATFORM_TODO.md)
- **All other current docs:** [`docs/README.md`](docs/README.md)
- **Historical record:** [`docs/archive/`](docs/archive/README.md)
