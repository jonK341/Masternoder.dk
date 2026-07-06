# Archived scripts

These were moved here during consolidation to reduce script count. Use the canonical scripts instead:

- **Deploy:** `python scripts/deploy.py profile|sync|loading` or `python scripts/deploy.py --files path1 path2 ...`
- **Check server:** `python scripts/check.py server|routes|uwsgi|disk`
- **Cleanup / disk:** `python scripts/server_cleanup_scan.py` (optionally `--clean`)
- **Clear pycache + restart:** `python scripts/clear_pyc_restart.py`
- **Uwsgi reload:** `python scripts/force_uwsgi_reload.py` (if still present) or restart via deploy

Archived items:
- Versioned duplicates (check_server2–4, check_routes2–3, diagnose_404_v2–v4, read_pipeline2–3, deploy_finish_v2–v3, etc.)
- Duplicate restart/clear scripts (force_restart_uwsgi, clear_pycache_restart, etc.)
- Redundant safe-cleanup/delete scripts (replaced by server_cleanup_scan.py)

## 2026-07-06: repo-root script sprawl (124 files)

The repo root had accumulated 133 one-off Python scripts (add_/debug_/fix_/get_*_error/investigate_/read_and_fix_/restart_*/setup_/simple_*/update_* etc.) from iterative debugging sessions — the exact pattern already documented in [`docs/REFLECTION_PY_AND_FILES.md`](../../docs/REFLECTION_PY_AND_FILES.md), just at the repo root instead of `scripts/`.

Moved 124 of them here after verifying each had **zero** references from systemd units, CI workflows, cron jobs, deploy manifests, or `import` statements elsewhere (only stale mentions in an already-superseded `scripts_analysis_report.txt` audit dump and two docs describing historical context, neither of which is a functional dependency).

**Kept at repo root** (still live/referenced): `run.py`, `wsgi.py` (Flask entry points); `deploy.py` (current manifest-based deploy tool); `deploy_ssh_env.py` (shared SSH helper — `import`ed by dozens of live `scripts/*.py`); `fix_502.py`, `restart_uwsgi.py`, `restart_flask_app.py`, `restart_ncixg.py` (actively referenced by current ops docs and other live scripts); `performance_monitor.py` (referenced as a building block in the active `docs/plans/masternoder_mn2_ecosystem.plan.md`).
