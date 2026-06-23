# MasterNoder2 daemon — multi-ping upgrade (design note)

**Status:** **In progress** — C++ spike implemented in local `external/MasterNoder2` (v1.3.0.0); production still on **v1.2.3.x** until build + deploy  
**Daemon repo:** [github.com/jonK341/MasterNoder2](https://github.com/jonK341/MasterNoder2) (C++ fork)  
**Site repo:** hosting automation, probes, and `ops.multi_ping_enabled` gate (this PR)

---

## Progress checklist (2026-06-23)

| Step | Status | Notes |
| ---- | ------ | ----- |
| Read `ManageStatus` / `SendMasternodePing` call graph | **Done** | `obfuscation.cpp` ~690s, `masternode-sync.cpp` |
| `CMasternodePingTarget` + `mapExtraPingTargets` | **Done** | `external/MasterNoder2/src/activemasternode.{h,cpp}` |
| `RegisterPingTarget` / `RegisterAllPingTargets` | **Done** | Skips vin already owned by primary |
| `ManageExtraPingTargets` in ping cycle | **Done** | Called at end of `ManageStatus()` |
| RPC `alias` / `all` → `pingRegister` in JSON | **Done** | `src/rpc/masternode.cpp` |
| Startup `-mnmultiping=1` (default on) | **Done** | `src/init.cpp` |
| Version bump **1.3.0.0** | **Done** | `configure.ac`, `release-notes-1.3.0.0.md` |
| Site `multi_ping_enabled` + service helpers | **Done** | `mn2_masternode_service.py`, config JSON |
| Probe scripts | **Done** | `mn2_probe_multi_ping.py`, `mn2_check_activetime_public.py` |
| Unit tests (site) | **Done** | `tests/unit/test_mn2_multi_ping.py` |
| Build + regtest on Linux | **Pending** | Windows workspace — build on fleet server |
| GitHub release v1.3.0.0 assets | **Pending** | `mn2_build_release_remote.py --publish` |
| Prod deploy | **Pending** | `mn2_daemon_upgrade_remote.py --apply` |
| Enable `ops.multi_ping_enabled: true` | **Pending** | After QA: 4+ ENABLED with rising activetime |
| Retire `primary_ping_alias` privkey hack | **Pending** | Optional once multi-ping stable |

---

## C++ implementation (v1.3.0.0)

Local reference tree: `external/MasterNoder2/` (nested clone; push branch to MasterNoder2 repo).

| File | Change |
| ---- | ------ |
| `src/activemasternode.h` | `CMasternodePingTarget`, `mapExtraPingTargets`, register/ping APIs |
| `src/activemasternode.cpp` | `SendMasternodePingForTarget`, `ManageExtraPingTargets`, `RegisterPingTarget` |
| `src/rpc/masternode.cpp` | `startmasternode alias\|all\|local` registers ping targets when `-mnmultiping=1` |
| `src/init.cpp` | `RegisterAllPingTargets()` at startup when `fMasterNode` |
| `configure.ac` | `1.3.0.0` |

**Call graph (unchanged entry, new tail):**

```
obfuscation thread (every MASTERNODE_PING_SECONDS)
  → CActiveMasternode::ManageStatus()     # primary (masternoder2.conf privkey)
  → CActiveMasternode::ManageExtraPingTargets()  # each registered alias
       → SendMasternodePingForTarget()
```

**RPC behaviour (v1.3+):**

```bash
masternoder2-cli startmasternode alias false customer-mn-42
# detail[].pingRegister == "registered"

masternoder2-cli startmasternode all false
# each success → pingRegister; broadcasts missing + registers ping set

masternoder2-cli startmasternode local false
# starts primary + RegisterAllPingTargets()
```

**Disable multi-ping (rollback to v1.2 behaviour):** `mnmultiping=0` in `masternoder2.conf`.

---

## Site repo integration

| Item | Location |
| ---- | -------- |
| Feature flag | `data/mn2_masternode_config.json` → `ops.multi_ping_enabled` (default `false`) |
| Version detect | `daemon_supports_multi_ping()` — `getinfo.version >= 1.3.0` |
| Provision path | `_start_masternode`: `alias` then `local` when multi-ping on |
| Watchdog | `maintain_ping_loop()` → `_register_fleet_ping_targets()` (`startmasternode all`) |
| Service API | `GET /api/mn2/masternode/service` → `daemon.multi_ping_*`, `enabled_with_activetime` |
| Probes | `python scripts/mn2_probe_multi_ping.py` · `python scripts/mn2_check_activetime_public.py` |

**After prod deploy:**

```powershell
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply --verify-post
# QA:
python scripts/mn2_probe_multi_ping.py --public
python scripts/mn2_probe_multi_ping.py --register   # on server / with RPC .env
# Then set multi_ping_enabled: true and redeploy mn2_staking
```

---

## Problem

One `masternoder2d` process today runs **one** `CMasternode` ping loop tied to:

- `masternode=1` + `masternodeprivkey=` in **masternoder2.conf**
- Optional `masternodeaddr=` (hairpin: `127.0.0.1:17646`)

All other lines in **masternode.conf** can be **broadcast** (`ACTIVE`, `activetime=0`) but do not get their own ping / activetime counter unless you switch privkey and restart — or run **separate daemons**.

---

## What users often expect (wrong syntax)

| Command | Valid? | Effect |
| ------- | ------ | ------ |
| `startmasternode local false` | Yes | Ping the privkey in **masternoder2.conf** (not a name) |
| `startmasternode alias false platformmn2` | Yes | Start/broadcast **that alias** from masternode.conf |
| `startmasternode local false platformmn2` | **No** | `local` does not take an alias; third arg is only for `alias` / `many` modes |

**Activetime** is not “switched on” by naming the MN in the RPC call. The daemon increments it when its **internal** `ManageStatus` / `SendMasternodePing` loop runs successfully for the active privkey.

---

## Not a firewall “multi-connection block” on 17646

Typical failure on a VPS hosting many MNs on one IP:

1. **Hairpin NAT** — daemon tries `Connect(PUBLIC_IP:17646)` to ping itself → fails. Fix: `masternodeaddr=127.0.0.1:17646` in masternoder2.conf (broadcast IP stays public in masternode.conf).
2. **Ping loop stopped** — after `systemctl restart masternoder2d`, internal thread does not run until `startmasternode local false` again.
3. **Wrong privkey** — `masternodeprivkey` does not match the masternode.conf line you care about.
4. **Locked collateral** — `lockunspent` hides UTXOs from `startmasternode`.
5. **Frozen activetime** — list still shows old `activetime` (e.g. 156002) while ping is dead; value stops increasing.

Inbound rules on 17646 rarely block **outbound** self-ping; check `debug.log` for `Could not connect to …:17646` vs `SendMasternodePing`.

---

## Upgrade option A — multi-ping in one daemon (best for hosting)

**Goal:** One process pings **every** valid line in `masternode.conf` (or a configured subset).

**Rough C++ work (PIVX/DASH-style fork):**

1. Refactor `activeMasternode` singleton → map `alias → CMasternode` or iterate `masternode.conf` entries in `ManageStatus()`.
2. Each entry: own privkey, ping via shared `masternodeaddr` / port.
3. RPC `startmasternode alias false <name>` registers that alias in the ping set without restart.
4. Optional RPC `startmasternode all false` ping all configured aliases.
5. Tests + release **v1.3.0.0** (or v1.2.4.0).

**Effort (estimate):**

| Phase | Time | Deliverable |
| ----- | ---- | ----------- |
| Spike + read upstream ManageStatus | 2–4 days | Confirm call graph in MasterNoder2 |
| Implement multi-ping loop | 5–10 days | Branch + unit/regtest |
| QA on fleet server | 2–3 days | 4× ACTIVE → 4× activetime rising |
| Release + deploy | 1 day | `mn2_daemon_upgrade_remote.py` |

**Total:** ~2–3 weeks calendar (one experienced fork maintainer), not counting review.

**This site repo after release:** drop `primary_ping_alias` single-MN hack; shop calls `startmasternode alias false <alias>` per purchase; optional `maintain_ping_loop` only as watchdog if ping stalls.

---

## Upgrade option B — multi-daemon (no C++ change)

Run **N** systemd units:

- `masternoder2d-fleet@platformmn2.service` … different `-datadir=` or subdirs
- Each datadir: own `masternodeprivkey`, one line in `masternode.conf`, unique P2P port if required

**Pros:** Works on today’s binary.  
**Cons:** N× disk/RAM/sync; ops heavy for 100 hosted slots.

---

## Upgrade option C — watchdog only (current site, interim)

- `maintain_ping_loop()` in cron: if ENABLED `activetime` **stops increasing**, re-issue `startmasternode local false` (no restart unless conf changed).
- Does **not** ping all fleet MNs; keeps **one** timer alive.

---

## Recommended roadmap

1. **Now (site):** deploy frozen-activetime watchdog + correct RPC order (`alias false <name>` then `local false` after privkey sync).
2. **Next (daemon v1.3):** Option A — multi-ping in MasterNoder2 repo.
3. **Parallel:** Document Option B for urgent fleet if C++ slips.

Track in [MN2_TODO.md](MN2_TODO.md) § Daemon multi-ping.
