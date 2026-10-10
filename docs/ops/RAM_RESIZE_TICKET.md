# VPS RAM resize ticket (MN2 ops)

**Opened:** 2026-09-16 UTC  
**Host:** masternoder.dk  
**Current:** 1.6 GiB RAM (~276–426 MiB available under load)  
**Requested:** **≥ 4 GiB** (prefer 8 GiB if explorer + Mongo stay co-located)

## Why

- `masternoder2d` SEGV on cold start / reindex handoff
- SSH banner timeouts under uwsgi ×2 + Mongo + explorer + profit daemons
- Chain re-sync after restart consumes RAM + swap (block height dropped from ~972k → re-syncing)

## Success criteria (DoD item)

- Steady `MemAvailable` **> 500 MiB** for 24h
- No OOM / SEGV during `systemctl start` without `-reindex`

## Owner action

1. Resize VPS in provider panel (avoid reboot during active chain sync if possible).
2. After resize: keep `dbcache=32` at 4 GiB; raise only after 48h stable.
3. Re-run `scripts/mn2_immediate_actions_remote.py` and confirm DoD-5 PASS.

## Status

| Date | MemAvailable | Notes |
|------|----------------|-------|
| 2026-09-16 | ~276–426 MiB | Explorer paused briefly; still below 500 MiB target — **ticket open** |
