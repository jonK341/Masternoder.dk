# Ubuntu Web Server Cleanup (masternoder.dk)

When the server disk is full or you want to free space, use the scan script from your local machine (it SSHs to the server).

## Scan only (report)

```bash
python scripts/server_cleanup_scan.py
```

This prints a report of disk usage and **safe-to-delete** candidates:

| Category | Location | Action with `--clean` |
|----------|----------|------------------------|
| Nginx cache | `/var/cache/nginx` | Cleared |
| APT cache | `/var/cache/apt/archives` | `apt-get clean` |
| Python cache | `__pycache__`, `*.pyc` under `/var/www/html` | Deleted |
| Video retention | `vidgenerator/videos` | Keep top 10 by size, delete rest |
| Orphan metadata/temp | `*.job.json`, `*.pipeline.json`, `*_temp_audio.mp4` without `.mp4` | Deleted |
| System journal | `journalctl` | Vacuum to keep 3 days |

After cleanup, the script reports **Space freed** (difference in available disk space before vs after).

The report also shows: overall `df -h`, `/var` usage, app/nginx log sizes, large files >5MB under `/var/www`, and `/tmp`/`/var/tmp`.

## Run cleanup

```bash
python scripts/server_cleanup_scan.py --clean
```

You will be prompted to confirm. To skip the prompt (e.g. in automation):

```bash
python scripts/server_cleanup_scan.py --clean --yes
```

## Whole-drive cleanup (aggressive)

To free as much space as possible on the server:

```bash
python scripts/server_cleanup_scan.py --full --yes
```

This runs everything in `--clean` plus:

- Journal vacuum to 50M (instead of 3 days)
- Truncate app logs (uwsgi.log, flask_app.log) and nginx access/error logs
- `apt-get autoremove`
- Remove files in `/tmp` and `/var/tmp` older than 7 days

To also **remove all videos** (not just keep top 10) for maximum space:

```bash
python scripts/server_cleanup_scan.py --full --yes --clear-all-videos
```

## Requirements

- **Local:** `paramiko`, and `DEPLOY_PASS` in the environment for SSH to `root@masternoder.dk` (no password is embedded in scripts).
- **Server:** Repo at `/var/www/html`; for video cleanup, `scripts/cleanup_videos_keep_top10.py` must be present (e.g. under `/var/www/html` or `/var/www/html/vidgenerator`).

## Optional: manual cleanup on server

If you SSH in yourself:

- **Videos (keep top 10):**  
  `cd /var/www/html && VIDEOS_DIR=/var/www/html/vidgenerator/videos python3 scripts/cleanup_videos_keep_top10.py`
- **Clear all video storage:**  
  Use the app’s `clear_all_video_storage()` (e.g. via API or shell) if implemented.
- **Journal:**  
  `journalctl --vacuum-time=3d` or `journalctl --vacuum-size=100M`
- **Logs:**  
  Truncate or rotate large `uwsgi.log` / `flask_app.log` / nginx logs if needed (see report).

See also [VIDEO_STORAGE_STRATEGY.md](VIDEO_STORAGE_STRATEGY.md) for the 25GB disk strategy and retention policy.
