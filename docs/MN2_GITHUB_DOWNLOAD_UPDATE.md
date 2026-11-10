# GitHub download page update — compile & announce

When MasterNoder2 **source** changes, refresh the public download set and tell Discord.

## Required download files

Published under `https://github.com/jonK341/MasterNoder2/releases/tag/<TARGET_VERSION>`
(`TARGET_VERSION` from `scripts/mn2_release_config.py`, currently **v1.3.1.0**):

| File | Builder |
| --- | --- |
| `masternoder2d.tar.gz` | `scripts/mn2_build_release.sh` / `mn2_build_release_remote.py` |
| `RELEASE_MANIFEST.json` | same (sha256 + binary sizes) |
| `MasterNoder2-qt-linux.tar.gz` | `scripts/mn2_build_qt_release.sh` |
| `MasterNoder2-qt-win.zip` | same |
| `QT_RELEASE_MANIFEST.json` | same |

Site `/wallets` and `GET /api/mn2/releases` read these via `RELEASE_BASE` + fixed filenames.

## Compile sequence (build host)

The C++ tree is under `external/MasterNoder2` (gitignored). On a host that has it:

```bash
# 1) Daemon + CLI
bash scripts/mn2_build_release.sh

# 2) Qt desktop wallets (Linux + Windows)
bash scripts/mn2_build_qt_release.sh

# 3) Publish / update GitHub release assets
python scripts/mn2_publish_release.py \
  --tarball dist/masternoder2d.tar.gz \
  --manifest dist/RELEASE_MANIFEST.json \
  --qt-assets

# 4) Verify + write Discord draft (posts only with --post when ready)
python scripts/mn2_prepare_github_download_announce.py
python scripts/mn2_prepare_github_download_announce.py --post
```

Or use the umbrella pipeline: `python scripts/mn2_release_pipeline.py`.

## Site portal copy

`/wallets` shows version, sha256 (when manifests resolve), and links. After publish, hard-refresh `/wallets` — release JSON is cached ~60s server-side.

## Discord

Draft lands in `docs/announcements/mn2-<version>-discord.md`.  
`--post` uses `backend.services.discord_service.post_message` on channel `platform_news` (override with `MN2_RELEASE_DISCORD_CHANNEL`). Requires a configured Discord webhook env for that channel.
