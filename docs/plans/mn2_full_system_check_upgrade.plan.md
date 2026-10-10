# MN2 Full System Check + Upgrade Plan

**Date:** 2026-09-15  
**Scope:** MasterNoder2 coin across daemon, payments, masternodes, staking, explorer, exchange, and ops  
**Live probe:** SSH + public/local APIs on `masternoder.dk`  
**Related:** [MN2_OPS.md](../MN2_OPS.md) · [MN2_TODO.md](../MN2_TODO.md) · [MN2_DAEMON_MULTI_PING_UPGRADE.md](../MN2_DAEMON_MULTI_PING_UPGRADE.md) · [MN2_ECOSYSTEM_REPORT.md](../MN2_ECOSYSTEM_REPORT.md)

---

## 1. Executive verdict

| Area | Status | Notes |
|------|--------|-------|
| Chain / RPC | **OK (degraded ops model)** | Block **972091**, 4 peers, wallet unlocked, ~3.25M MN2 balance |
| Process stability | **OK ~1d 21h** | Same PID since Sep 13 reindex; **0 SEGV in last 12h+** |
| systemd ownership | **Broken** | Unit `failed`; live process is **nohup `-reindex`** — not restart-safe |
| App health APIs | **Degraded** | `/api/mn2/health` → **503** (`daemon_staking` inactive) |
| Masternode network view | **Critical** | `listmasternodes` **len=0**, `getmasternodecount` all zeros |
| Hosted fleet | **Critical** | Site: **52 hosted**; daemon: **0 ENABLED with activetime** |
| Staking (daemon) | **Down** | `staking status: false`, `mnsync: false` |
| Shop catalog / price | **OK** | MN2 packs + USD price respond |
| Explorer PM2 | **OK** | online (3 lifetime restarts) |
| Host RAM | **Critical** | **1.6 GiB** total, ~**256 MiB** available — root of timeouts/SEGV risk |

**Bottom line (2026-09-16):** Daemon is **systemd-owned** (no `-reindex` in cmdline) and chain is **re-syncing** (~697k → ~972k tip after deploy recovery). **Masternode list still empty** (`mnsync` asset 2). RAM **below DoD** (~276–426 MiB). Do not mark hosting/staking healthy until DoD below is green.

---

## 1b. Immediate next actions (runbook)

| # | Action | Status (2026-09-16) |
|---|--------|---------------------|
| **1** | Leave nohup `-reindex` alone until soft-stop trial | **OK** — no live `-reindex` daemon; `systemctl is-active` = **active**; cmdline = `-datadir=/var/www/html/config` only |
| **2** | Set `ops.multi_ping_enabled` **false** (binary v1.2.3.0 / `1020300`) | **Done** — server + repo `data/mn2_masternode_config.json` |
| **3** | Free RAM / open resize ticket (**≥ 4 GiB**) | **Partial** — explorer paused briefly → **426 MiB** peak; ticket: [RAM_RESIZE_TICKET.md](../ops/RAM_RESIZE_TICKET.md) — **open** |
| **4** | Debug empty `listmasternodes` (mnsync / peers) | **In progress** — 5 peers, 12× onetry rounds; asset **2**, `countMasternodeList=0`; `startmasternode` blocked: *sync in progress* |

**Repeat:** `python scripts/mn2_immediate_actions_remote.py` (full) or `--no-mnsync` (probe only).

#### Execution log (2026-09-16 ~02:49 UTC — continued)

| Probe | Result |
|-------|--------|
| Block height | **~855k** (~**88%** of ~972k tip); climbing steadily |
| Explorer PM2 | **stopped** during catch-up (RAM headroom ~502 MiB with explorer off) |
| Watcher | `scripts/mn2_watch_sync_then_enable_remote.py` running — auto mnsync-finish + fleet at tip |

#### Execution log (2026-09-16 ~02:13 UTC)

| Probe | Result |
|-------|--------|
| Block height | **696799** (climbing; was ~972k pre-restart) |
| `mnsync` | asset **2**, `countMasternodeList=0`, `IsBlockchainSynced=false` |
| `listmasternodes` | **[]** |
| `/api/mn2/health` | **503** (`degraded` — `daemon_staking` inactive; in-app `staking` config healthy) |
| `/api/shop/payment-health` | RPC block **730373** (daemon catching up) |
| RAM | **276–426 MiB** available (DoD needs **> 500 MiB** for 24h) |

---

## 2. Live scorecard (2026-09-15 baseline · see §1b for current)

### 2.1 Daemon / RPC

| Check | Result |
|-------|--------|
| Process | `pid 4163219` · `… -reindex -printtoconsole` · etime **1-21:01** · RSS ~120 MB |
| Port | `127.0.0.1:9332` listening |
| `getblockcount` | **972091** |
| `getconnectioncount` | **4** |
| `getwalletinfo` | balance ≈ **3,247,749** MN2 · immature ≈ 29k · unlocked |
| `getstakinginfo` | walletunlocked/mintable **true** · **staking false** · **mnsync false** |
| `mnsync status` | `IsBlockchainSynced: true` · **countMasternodeList: 0** · assets requested |
| `listmasternodes` | **[]** (empty) |
| `getmasternodestatus` | Started locally but **not in MN list** |
| `masternode.conf` | **39** aliases (platformmn2…) |
| systemd | `ActiveState=failed` · `Restart=no` override from recovery |

### 2.2 Application surfaces

| Surface | Probe | Result |
|---------|-------|--------|
| `GET /api/mn2/health` | local :5000 | **503** — staking inactive; other components mixed |
| `GET /api/mn2/price` | public | **200** · ~$6.29 |
| `GET /api/shop/mn2-packs` | public | **200** |
| `GET /api/mn2/staking/config` | public | **200** · APR config OK |
| `GET /api/mn2/masternode/service` | public | **200** · hosted **52** · `enabled_with_activetime: 0` · version **1020300** (v1.2.3) |
| `GET /api/mn2/network-overview` | public | **timeout** (load) |
| `GET /api/mn2/explorer/status` | public/local | flaky / partial nulls |
| `GET /api/mn2/staking/proof-of-reserves` | public | **timeout** |
| Deposit scan crons | `/etc/cron.d/masternoder-mn2-*` | Present: scan, accrue, provision, micro-tx, watchdogs, explorer-probe, network-snapshot |
| Explorer PM2 | `explorer` | **online** |
| Disk | `/` | **73%** used (15G free) |
| Config `ops.multi_ping_enabled` | JSON | **true** while binary is still **v1.2.3.0** — flag ahead of binary |

### 2.3 Function map vs production readiness

| Function | Code ready | Prod ready | Blocker |
|----------|------------|------------|---------|
| RPC / getinfo / blocks | Yes | **Yes** | — |
| Deposit addresses + scanner cron | Yes | **Likely** (verify last scan run) | Health 503 noise |
| In-wallet shop MN2 spend | Yes | **Likely** | App timeouts under load |
| On-chain order-payment | Yes | **At risk** | Load + MN/staking side effects |
| Withdraw + float gates | Yes | **At risk** | Need reconcile after long reindex |
| Masternode hosting checkout | Yes | **No** | Empty MN list / 0 ENABLED |
| Fleet ping / provision | Yes | **No** | mnsync list empty; multi-ping flag/binary mismatch |
| Daemon staking yield | Yes | **No** | staking + mnsync false |
| In-app staking pool UI | Yes | **Partial** | Config OK; yield depends on daemon |
| Explorer display | Yes | **Partial** | Timeouts; richlist depends on eiquidus |
| Proof of reserves | Yes | **Degraded** | API timeouts |
| Exchange / internal AMM | Yes | **Unknown** | Not smoke-tested this pass — schedule |
| Creator rating MN2 | Yes | **Unknown** | Depends on balance + health |
| Multi-ping (v1.3) | Patch + site gate | **No** | Binary still 1.2.3; flag already true |

---

## 3. Root causes (ordered)

1. **Host undersized (1.6 GiB RAM)** — daemon + uwsgi×2 + Mongo + explorer + profit daemons → SSH banner failures, API timeouts, historical SEGV on cold start.
2. **Lifecycle debt** — production RPC is a **manual `-reindex` process**, not systemd. Any reboot or accidental `systemctl start` risks SEGV crash-loop again.
3. **Masternode list never populated** after reindex — blockchain tip OK but **MN inventory = 0**, so hosting/ping/ENABLED metrics are worthless.
4. **Premature `multi_ping_enabled: true`** on **v1.2.3.0** — site believes multi-ping is on; daemon cannot do fleet-wide ENABLED activetime.
5. **Cold-start SEGV** (Sep 13) — normal start without `-reindex` dies in `Loading block index`; needs soft-stop proof before trusting systemd again.

---

## 4. Upgrade plan

### Phase 0 — Stabilize ops model (P0, 1–2 days)

**Goal:** Keep payments alive; make daemon restart-safe; stop lying health.

| Step | Action | Success criteria |
|------|--------|------------------|
| 0.1 | **Do not** `systemctl restart masternoder2d` until 0.4 passes | Process PID stays healthy |
| 0.2 | Pause non-essential RAM hogs during peak (exchange `--once` storms, heavy profit profile) | Available RAM **> 500 MiB** steady |
| 0.3 | Soft-stop only: `masternoder2-cli stop` → wait until exit → start **without** `-reindex` via systemd | No SEGV for **2h**; RPC block height continuous |
| 0.4 | If 0.3 fails: leave nohup running; schedule **RAM upgrade** before retry | Document result in ops log |
| 0.5 | Set systemd `Restart=on-failure` only after 0.3 OK; remove recovery `Restart=no` | `systemctl is-active masternoder2d` = active |
| 0.6 | Align health: restore staking unlock after restart (`mn2_next_ops_remote.py --restore-staking`) | `/api/mn2/health` not 503 for staking alone |

**Files / scripts:** `systemd/masternoder2d.service.example`, `scripts/mn2_next_ops_remote.py`, `scripts/_prod_mn2_recovery.py`, `/etc/systemd/system/masternoder2d.service.d/override.conf`

#### Phase 0 execution log (2026-09-15)

| Result | Detail |
|--------|--------|
| **Soft-stop** | `masternoder2-cli stop` exited cleanly (~10s); no SIGKILL |
| **First systemd start** | Failed: `Unable to start HTTP server` (port race right after stop) |
| **Fallback proof** | nohup **without** `-reindex` came up at block **972416** — cold start OK after clean stop |
| **Retry systemd** | Waited for `:9332` free → `systemctl start` → **active**; RPC stable 5 consecutive polls |
| **Lifecycle** | Process `masternoder2d -datadir=…` (no `-reindex`); `Restart=on-failure` enabled |
| **payment-health** | **healthy** @ 972416 |
| **mn2_rpc** | **healthy** |
| **daemon_staking** | Still **inactive** (`mnsync: false`, `haveconnections: false`) — deferred to Phase 1 |
| **Passphrase** | `MN2_WALLET_PASSPHRASE` not in server `.env`; wallet already `walletunlocked: true` |
| **Residual watch** | Confirm no SEGV for **2h** after handoff; then mark Phase 0 fully closed |

#### Immediate next actions log (2026-09-15 ~21:21 UTC)

| Action | Result |
|--------|--------|
| systemd daemon (no `-reindex`) | **active** · block **972421** · payment-health **healthy** |
| `ops.multi_ping_enabled` → **false** | Set on server + in repo `data/mn2_masternode_config.json` |
| Free RAM | Paused explorer/profit briefly → **~530 MiB** available |
| addnode peers + mnsync reset/next | **5** connections; mnsync stuck at asset **2**, `countMasternodeList=0` |
| `startmasternode local` | Reports started but **not in MN list** (expected until mnsync completes) |
| **Still blocked** | Need longer `mnsync-finish` watch or daemon bounce after addnode; then Phase 1.3 activetime |

### Phase 1 — Masternode sync + fleet (P0, 2–4 days)

**Goal:** Non-empty `listmasternodes`; hosted nodes show ENABLED + rising activetime.

| Step | Action | Success criteria |
|------|--------|------------------|
| 1.1 | Diagnose empty MN list (peers, `mnsync reset`, addnode, network time) | `countMasternodeList > 0` |
| 1.2 | `startmasternode local false` then fleet maintain-ping | `getmasternodestatus` finds node in list |
| 1.3 | Run `mn2_check_activetime_public.py` + `maintain-ping` ops | `enabled_with_activetime ≥ 1` (then scale) |
| 1.4 | **Temporarily set `ops.multi_ping_enabled: false`** until v1.3 binary | Service API matches reality |
| 1.5 | Reconcile hosted_count (52) vs conf aliases (39) vs on-chain | Ops dashboard consistent |

**Files:** `data/mn2_masternode_config.json`, `backend/services/mn2_masternode_service.py`, `scripts/mn2_probe_multi_ping.py`, `scripts/mn2_check_activetime_public.py`, `cron/mn2_masternode_provision.sh`

### Phase 2 — Host capacity (P0/P1, parallel)

**Goal:** Eliminate SEGV/timeout class failures.

| Step | Action | Success criteria |
|------|--------|------------------|
| 2.1 | Resize VPS to **≥ 4 GiB RAM** (prefer 8 GiB if fleet + explorer stay co-located) | Steady available RAM; no SSH banner storms |
| 2.2 | Keep `dbcache=32`, `maxconnections=8` until ≥4 GiB; then raise carefully | No OOM kills |
| 2.3 | Optional: move Mongo/eiquidus or profit daemons off primary | API p95 timeouts drop |

### Phase 3 — Daemon binary upgrade (P1, 1 week)

**Goal:** Ship **v1.3.x multi-ping** (+ optional 1.3.1 sporks) so 250 hosted slots can stay ENABLED.

| Step | Action | Success criteria |
|------|--------|------------------|
| 3.1 | Finish Linux build of multi-ping patch (`docs/patches/mn2-daemon-v1.3.0-multi-ping.patch`) | Regtest / smoke OK |
| 3.2 | Publish GitHub release assets | Tarball + manifest |
| 3.3 | Maintenance window: `mn2_daemon_upgrade_remote.py --apply --verify-post` | `getinfo.version ≥ 1030000` |
| 3.4 | Enable `ops.multi_ping_enabled: true` after probe | ≥4 aliases ENABLED with rising activetime |
| 3.5 | Retire primary-only privkey ping hack | Docs + config cleanup |

**Refs:** [MN2_DAEMON_MULTI_PING_UPGRADE.md](../MN2_DAEMON_MULTI_PING_UPGRADE.md), [MN2_RELEASE_BUILD.md](../MN2_RELEASE_BUILD.md)

### Phase 4 — Payments & conservation hardening (P1, 3–5 days)

**Goal:** Prove money paths after reindex/fleet fix.

| Step | Action | Success criteria |
|------|--------|------------------|
| 4.1 | `scripts/mn2_reconcile.py` + float/conservation ops | No material drift |
| 4.2 | Deposit scanner: last success timestamp + forced dry scan | Credits match on-chain |
| 4.3 | Withdraw dry-run path + one small live withdraw | Completes with ledger meta |
| 4.4 | Shop: `payment_method=mn2` + pack purchase smoke | 200 + balance delta |
| 4.5 | Hosting pay-mn2 / pay-onchain one test order | Provisions without stuck state |
| 4.6 | `/api/mn2/health` and `/api/shop/payment-health` both green | Public smoke green |

### Phase 5 — Staking / POR / explorer (P2, 1 week)

| Step | Action | Success criteria |
|------|--------|------------------|
| 5.1 | After mnsync healthy: enable staking, verify rewards path | `staking status: true` |
| 5.2 | Accrue cron + in-app stake/unstake smoke | Leaderboard updates |
| 5.3 | POR endpoint under load budget | `< 3s` local |
| 5.4 | eiquidus index sync / richlist | Explorer status checks green |

### Phase 6 — Product / ecosystem polish (P2/P3)

| Step | Action |
|------|--------|
| 6.1 | Exchange suite pytest drift (`test_exchange_*`) |
| 6.2 | Agent crypto rewards service gaps ([MN2_TODO.md](../MN2_TODO.md)) |
| 6.3 | Treasury distribute / Gate D prod verify leftovers |
| 6.4 | Casino Meta webhook (paused) when tokens ready |
| 6.5 | Document “golden path” runbook: boot → unlock → mnsync → fleet → health |

---

## 5. Suggested execution order (calendar)

```text
Week 0 (now):  Phase 0 soft-stop trial OR RAM ticket; disable premature multi_ping flag
Week 1:        Phase 1 MN list + fleet ENABLED; Phase 4 payment smokes
Week 2:        Phase 2 RAM resize if soft-stop still fails; Phase 3 build v1.3
Week 3:        Phase 3 deploy multi-ping; Phase 5 staking/POR/explorer
Ongoing:       Phase 6 polish + pytest debt
```

---

## 6. Risks & rollback

| Risk | Mitigation |
|------|------------|
| Soft-stop → SEGV loop | Keep nohup recipe; do not enable systemd Restart until proven |
| Hard kill during wallet flush | Prefer `masternoder2-cli stop`; never SIGKILL unless hung >10m |
| Enabling multi-ping on 1.2.3 | Keep flag **false** until version ≥ 1.3.0 |
| Reindex again | Only if OpenBlockFile/SEGV returns; schedule off-peak; pause explorer/profit |
| API timeouts during upgrades | Drain profit/exchange jobs; raise uwsgi timeouts temporarily |

---

## 7. Definition of done

| Criterion | Target | Status (2026-09-16) |
|-----------|--------|---------------------|
| **Lifecycle** | `systemctl is-active masternoder2d` = **active**, no `-reindex` in cmdline | **PASS** |
| **Health** | `GET /api/mn2/health` **not 503** for staking (`daemon_staking` not inactive) | **FAIL** — HTTP **503**, `daemon_staking` inactive (`mnsync: false`) |
| **Masternode fleet** | `listmasternodes` **> 0** · **ENABLED** with `activetime ≥ 5` | **FAIL** — len **0**, ENABLED **0** |
| **Payments** | Deposit + withdraw + shop MN2 smoke **green** | **Not run** — blocked until chain at tip + health green |
| **RAM** | Headroom **> 500 MiB** for **24h** | **FAIL** — spot **276–426 MiB**; resize ticket open |

### Checklist (close when all green)

- [x] `systemctl is-active masternoder2d` = **active** (no nohup `-reindex`)
- [ ] `GET /api/mn2/health` **not 503** for staking (`daemon_staking` active)
- [ ] `listmasternodes` length **> 0**
- [ ] **ENABLED** count with `activetime ≥ 5`
- [ ] Deposit scan + one withdraw + one shop MN2 purchase smoke **green**
- [ ] Available RAM **> 500 MiB** for 24h
- [x] `ops.multi_ping_enabled: false` while binary **< 1.3.0**
- [ ] If multi-ping enabled later: daemon **≥ 1.3.0** and probe scripts pass

---

## 8. Out of scope (this plan)

- Greenfield chain features unrelated to ops recovery  
- Full exchange redesign  
- Moving custody off-server (hardware wallet / multi-sig) — future track  

---

## Confidence

**High** on live findings (probed today).  
**Medium** on Phase 0 soft-stop success (depends on whether SEGV was corruption vs RAM).  
**Medium** on Phase 1 empty MN list root cause (peers vs mnsync vs protocol) — needs hands-on debug in Phase 1.1.
