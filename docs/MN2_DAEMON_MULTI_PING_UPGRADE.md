# MasterNoder2 daemon — multi-ping upgrade (design note)

**Status:** Planned (not in current v1.2.3.x binary)  
**Repo:** [github.com/jonK341/MasterNoder2](https://github.com/jonK341/MasterNoder2) (C++ fork, not this Flask site)  
**Site repo:** hosting automation only — cannot multi-ping without a new daemon build.

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
