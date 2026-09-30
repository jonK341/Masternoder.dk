# MN2 v1.3.1.0 build checkpoint (paused)

**Saved:** 2026-07-01  
**Goal:** Option A — fast build (`--without-miniupnpc`) → draft publish → daemon upgrade → activate `SPORK_112_EXCHANGE_LIVE_TRADING`.

## Post-/tmp cleanup (verified OK)

Nothing production missing. Daemon, wallet, `.env`, uwsgi all healthy. Only `/tmp` build debris was removed.

## Code changes already in repo (local, not committed)

| File | Change |
|------|--------|
| `scripts/mn2_build_release.sh` | Fast configure adds `--without-miniupnpc` |
| `docs/patches/mn2-gcc15-boost-placeholders.patch` | Fixes GCC 15 `_1`/`_2` in `validationinterface.cpp` |
| `scripts/mn2_build_release_remote.py` | Uploads `mn2-gcc15-*.patch`; kills stale builds; detached `nohup` build + poll |
| `scripts/mn2_server_health_check.py` | Quick post-cleanup / health script |

Build root on server: `/var/mn2-build` (not `/tmp`).

## Build attempts so far

1. **First fast build** — failed: miniupnpc/GCC 15 (`UPNP_GetValidIGD` arity). Fixed with `--without-miniupnpc`.
2. **Second fast build** — failed: Boost placeholders in `validationinterface.cpp`. Fixed with gcc15 compat patch.
3. **Third attempt** — SSH overloaded (dual builds); client disconnected ~37 min in. No v1.3.1 tarball produced.
4. **Server recovered** — health check OK (daemon block ~934693). Stale `bash /tmp/mn2_build_release.sh` may still exist; new script kills it before starting.

Local `dist/masternoder2d.tar.gz` is still **v1.3.0.0** (no exchange sporks) — do not use for upgrade.

## Resume commands (when ready)

```powershell
cd C:\Users\jonkh\UsecaseSampler\Masternoder.dk

# 1) Build v1.3.1.0 on server (detached, ~30–90 min)
python scripts/mn2_build_release_remote.py --fast --publish --draft

# 2) Upgrade production daemon
python scripts/mn2_daemon_upgrade_remote.py --apply --verify-post

# 3) Activate live trading spork on-chain
python scripts/mn2_activate_spork_remote.py SPORK_112_EXCHANGE_LIVE_TRADING 1703122560

# 4) Verify
python scripts/mn2_check_spork_server.py
```

Health check anytime:

```powershell
python scripts/mn2_server_health_check.py
```

## Live trading gate (workaround until v1.3.1 upgrade)

Server `.env` should have:

- `EXCHANGE_ARBITRAGE_LIVE=1`
- `MN2_SPORK_OVERRIDE_JSON={"SPORK_112_EXCHANGE_LIVE_TRADING":1703122560}`

Daemon `masternoder2.conf` needs `sporkkey` (already set on server).

## If SSH hangs again

Reboot VPS from host panel, or SSH in and:

```bash
pkill -f mn2_build_release.sh
pkill -9 -f 'make.*masternoder2d'
```

Then re-run step 1 from Windows.
