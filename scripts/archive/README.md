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
