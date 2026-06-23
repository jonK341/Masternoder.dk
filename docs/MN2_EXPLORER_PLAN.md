# MN2 explorer — hybrid plan (self-hosted iquidus + on-site stats tiles)

This plan builds the MN2 explorer as a **hybrid**: run a real **block explorer from source** (iquidus) on the same server as the daemon and Masternoder.dk, and have the Flask site treat **our own explorer as the primary data source** for stats and links, with daemon **RPC** and **Chainz CryptoID** as fallbacks only.

**Decision (locked):** Hybrid, same-server. Rejected alternatives: *online-stats-only* (can't browse blocks/txs/addresses or build a rich list; rate-limited by Chainz at 1 req/10s; third-party dependency) and *RPC-only* (a bare PIVX/Bitcoin-style daemon can't answer per-address history without an index).

**Related docs:** [EXPLORER_REINSTALL_CHECKLIST.md](EXPLORER_REINSTALL_CHECKLIST.md) · [MN2_STAKING_PLAN.md §16](MN2_STAKING_PLAN.md) · [MN2_DAEMON_SETUP.md](MN2_DAEMON_SETUP.md) · [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md)

---

## 0. Core constraints (read first)

- **A real explorer needs a chain index.** Browse-by-block, browse-by-tx, **address history**, and **rich list** cannot be served by Chainz or by bare daemon RPC. iquidus indexes the chain into MongoDB; the daemon must expose `txindex=1` (and `addressindex=1` for address pages / rich list on PIVX-style chains).
- **Explorer is display-only.** Per the integration doc's RPC-vs-explorer rule, crediting/withdrawals never depend on the explorer; it is for human/agent visibility only. Never block a balance operation on explorer availability.
- **Source priority for stats:** **our iquidus (local) → daemon RPC → Chainz (last resort)**. Local-first removes the Chainz rate limit and third-party risk; RPC and Chainz remain resilient fallbacks.

---

## 1. Goals & non-goals

**Goals**
- Stand up a self-hosted **iquidus** block explorer (blocks, txs, addresses, search, rich list, supply) against masternoder2d.
- Make Masternoder.dk render an **explorer overview** (price, height, supply, masternode count, difficulty, staking weight, our pool vs network) sourced **local-first**.
- Switch all on-site explorer **links** (tx/address) to our explorer's URL shape, with Chainz kept as a config-selectable fallback.

**Non-goals (this phase)**
- Replacing the staking/on-ramp/P2P stats already in `/api/mn2/network-overview`.
- A second explorer codebase (`masternoder2d`-based) — keep iquidus; revisit later if needed.
- Multi-server / dedicated explorer host (same-server for now).

---

## 2. Architecture overview

```
masternoder2d (txindex=1, addressindex=1, server=1, rpcbind=127.0.0.1:9332)
   │  JSON-RPC
   ├── iquidus explorer (Node + MongoDB)  ──>  https://camgirls.masternoder.dk/
   │        exposes /ext/* + /api/* + HTML block/tx/address/richlist pages
   │
   └── Flask (Masternoder.dk)
          ├── mn2_chainz.network_overview()   (extended: iquidus-first → RPC → Chainz)
          ├── mn2_routes._explorer_*           (URL builders: iquidus shape vs chainz .dws)
          └── /explorer overview page          (tiles consuming /api/mn2/network-overview)
```

---

## 3. Server work (from source) — extends EXPLORER_REINSTALL_CHECKLIST.md

The checklist already covers Mongo, iquidus install, `settings.json`, PM2, nginx, TLS. This plan adds the **daemon index requirements** that make address/tx/richlist pages actually populate:

1. **`masternoder2.conf` (daemon):** ensure `server=1`, `rpcuser`/`rpcpassword`, `rpcport=9332`, `rpcbind=127.0.0.1`, **`txindex=1`**, and (for address pages / rich list on PIVX-style chains) **`addressindex=1`**, `spentindex=1`, `timestampindex=1` if supported by MasterNoder2. Confirm exact keys in the [MasterNoder2 repo](https://github.com/jonK341/MasterNoder2).
2. **One-time `-reindex`** after enabling those flags so the daemon builds the indexes over existing history (heavy: do it in a quiet window; expect extra disk + CPU).
3. **iquidus `settings.json`:** coin name/symbol, **txid regex**, **address prefix** must match MasterNoder2 chainparams (reuse the prior working backup). Wallet block points at `127.0.0.1:9332` with the same RPC creds.
4. **Sync + cron:** initial full index sync, then iquidus' `sync.js` cron (index update / market / peers) per its docs.

Add these as a short "Daemon index prerequisites" section in the checklist (done in this change set).

---

## 4. Flask work (on-site) — code changes

### 4.1 Config (`data/mn2_config.json`)
Add explorer-shape selector + keep base url:
```json
{
  "explorer_base_url": "https://camgirls.masternoder.dk/",
  "explorer_kind": "iquidus",
  "explorer_local_api_url": "http://127.0.0.1:3000",
  "explorer_fallback_base_url": "https://chainz.cryptoid.info/mn2/"
}
```
> Flip `explorer_base_url`/`explorer_kind` only **after** iquidus is live and synced, so existing Chainz links keep working until cutover.

### 4.2 URL builders (`backend/routes/mn2_routes.py`)
`_explorer_tx_url` / address URL builders currently hardcode Chainz `.dws` shape. Branch on `explorer_kind`:

| kind | tx URL | address URL |
|---|---|---|
| `chainz` (current) | `/tx.dws?txid=<txid>` | `/address.dws?addr=<addr>` |
| `iquidus` (new) | `/tx/<txid>` | `/address/<addr>` |

Centralize into one helper so all call sites (lines ~30, ~63, ~139, ~164, ~237, ~277, ~577) get the right shape automatically.

### 4.3 Local-first stats (`backend/services/mn2_chainz.py`)
Add an **iquidus tier** at the top of `network_overview()`:
- Query the local explorer (`explorer_local_api_url`) for what it serves cheaply: `/api/getblockcount`, `/ext/getmoneysupply` (circulating supply), rich list / distribution, and market/price if configured. Local = no rate limit, low latency.
- Keep existing **RPC** tier for staking weight / masternode count / difficulty (or read from iquidus if it surfaces them), then **Chainz** as final fallback.
- Tag each field's `source` as `iquidus` | `rpc` | `chainz` (the function already tracks `source`). Cache local calls briefly (e.g. 30–60s) to avoid hammering Node.

`/api/mn2/network-overview` (in `mn2_staking_routes.py`) needs **no change** — it already wraps `network_overview()` and adds pool/onramp/p2p stats.

### 4.4 Overview page (frontend)
- `explorer/index.html` + a small `static/js/mn2-explorer-overview.js` that polls `/api/mn2/network-overview` and renders tiles: price (+ change), block height/sync, money supply, masternode count, difficulty, net stake weight, **our pool vs network share** (`pool_total_staked / staking_weight`), and on-ramp/P2P 24h stats.
- Each tile/address/tx links out to the self-hosted explorer via the §4.2 helper. Reuse existing dashboard/table styling.
- Add a "full explorer" link to `camgirls.masternoder.dk`.

---

## 5. Same-server resourcing

One host now runs **masternoder2d + MongoDB + Node/iquidus + Flask**. Watch:
- **Initial index/`-reindex` + iquidus first sync** are CPU/RAM/disk heavy — schedule off-peak.
- `addressindex` materially increases daemon disk usage.
- iquidus via PM2 `bin/cluster` with `--stack-size` (per checklist); give Mongo and the daemon headroom.
- Health: add iquidus reachability to ops stats; if the local explorer is down, `network_overview()` must silently fall back to RPC/Chainz (no user-facing failure).

---

## 6. Phased delivery

**Phase E1 — Server explorer (from source)** — **built 2026-06-04** (see §E1 below)
- [x] Daemon: `txindex=1` + one-time `-reindex` (daemon only supports `-txindex`; **no** `addressindex`/`spentindex` — not needed, eiquidus self-indexes addresses into Mongo).
- [x] Explorer install + `settings.json` + Mongo + PM2 + nginx/TLS. Initial full sync running.
- [ ] Verify `/address/<addr>`, `/tx/<txid>`, rich list once the initial index finishes (`/ext/getmoneysupply` already live).

**Phase E2 — Flask cutover (links)**
- [ ] Add `explorer_kind` / local/fallback URLs to `mn2_config.json`.
- [ ] Branch URL builders in `mn2_routes.py`; centralize into one helper. Tests for both shapes.
- [ ] Flip `explorer_base_url` → self-hosted; Chainz becomes fallback.

**Phase E3 — Local-first stats + overview page**
- [ ] iquidus tier in `network_overview()` (cached, `source`-tagged, RPC/Chainz fallback). *(added once iquidus is live; RPC→Chainz tiers exist today)*
- [x] `explorer/index.html` + `mn2-explorer-overview.js` tiles consuming `/api/mn2/network-overview` — **built & live** (routed via `PAGES` in `all_page_routes.py`; `/api/mn2/network-overview` also returns `explorer_base_url` for the "Open full explorer" link, and is linked in the nav toolbar). Live tiles: price (Chainz); height/difficulty/masternodes/**network weight** (RPC); pool staked/APR/USD value; on-ramp & P2P 24h.
- [x] Parity note in `AGENTS_MN2.md` §12 (public read endpoint, full response shape documented).

> **Verified (2026-06-03):** Chainz public API serves `getblockcount`, `ticker.usd`, `getdifficulty`; **`mncount` is "Unsupported query"**. MasterNoder2 daemon **does not implement `getstakinginfo`** (`-32601`); net stake weight is taken from **`getmininginfo.networkhashps`** (shown as "Network Weight"), masternode count from `getmasternodecount`, all `source: rpc`. On-site links still point at Chainz (`.dws`) until the E2 iquidus cutover.

---

## 7. Decisions (locked)

| # | Decision |
|---|---|
| 1 | Explorer is **self-hosted iquidus from source**, not online-stats-only or RPC-only. |
| 2 | Stats source priority: **iquidus (local) → RPC → Chainz fallback**. |
| 3 | **Same server** as daemon + Masternoder.dk for now. |
| 4 | Explorer is **display-only**; crediting/withdrawals never depend on it. |
| 5 | Cut over on-site links to iquidus **only after** it is live and synced; keep Chainz as config-selectable fallback. |

---

## 8. Top 10 explorer advancements — improve / impair analysis

Candidate advancements beyond the current overview page, rated for what each **improves** and what it **impairs** (cost/risk/downside). **Verdict:** ✅ Adopt · 🟡 Adopt guarded · ⛔ Defer. Ordered by value-to-effort.

| # | Advancement | Improves | Impairs (risk/cost) | Verdict |
|---|-------------|----------|----------------------|---------|
| 1 | **Network stats time-series** — cron snapshots `network-overview` to `data/mn2_network_history.jsonl`; render sparklines (price, height, difficulty, network weight, pool staked) on `/explorer` | Trends instead of point-in-time; "is staking growing?" at a glance | Small storage + a snapshot cron; chart code | ✅ Adopt (cheap, high signal) |
| 2 | **Daemon staking-health banner** — surface `rpc_client.staking_health()` (`staking_active`, `mnsync`, mature/immature) as a status strip | Catches the exact "not minting / mnsync=false" issue we hit; operator + user trust | Exposes some ops state publicly (show booleans, hide balances) | ✅ Adopt (gate detail to ops) |
| 3 | **Stop-staking / sync-stall alert** — if `staking_active` flips false or height stops advancing, alert via existing notification system | Reliability; realized yield can't silently go to 0 | Alert tuning to avoid noise | ✅ Adopt (reuse alert infra) |
| 4 | **Cache headers + ETag on `/api/mn2/network-overview`** + documented JSON schema | Cheap third-party/agent reuse; less load; CDN-friendly | Minimal | ✅ Adopt |
| 5 | **Address/tx/height search box** on `/explorer` that deep-links via the `explorer_kind` URL helper | Core explorer UX without hosting iquidus yet | Depends on target explorer's URL shape (already handled in E2) | ✅ Adopt |
| 6 | **Multi-source price (median)** — Chainz + one more feed, take median; show staleness | Price resilience if Chainz drops/rate-limits | Extra dependency + rate limits; reconciliation of differing prices | 🟡 Guarded (clearly "estimated") |
| 7 | **Latest PoS blocks + reward feed** on `/explorer` (from iquidus once live) | Liveness, engagement, shows minting in real time | Needs iquidus (E1); polling cost | 🟡 Guarded (after E1) |
| 8 | **True pool-vs-network share** — once iquidus rich list exposes the staking address balance in **coins**, compute real share (current "Network Weight" is hashps, not coins) | Meaningful footprint metric | Needs iquidus rich list; address attribution | 🟡 Guarded (after E1) |
| 9 | **SSE/live updates** for `/explorer` + monitor (replace 30s poll) | Real-time feel; fewer requests | Server load, reconnection edge cases (mirror staking-plan §14 #3) | 🟡 Guarded (SSE first, keep poll fallback) |
| 10 | **Masternode list + ROI / emission schedule** page (count, collateral, block reward split, halving/emission) | Investor-facing context; complements staking | Needs reliable MN data (RPC `getmasternodecount` works; per-MN list may not); upkeep | 🟡 Guarded (start with aggregates we already have) |

**Net:** Adopt 1–5 now (no iquidus dependency, high value); 6 & 9 guarded; 7, 8, 10 unlock after **E1 (iquidus from source)**. Items 2 & 3 directly harden the realized-yield path that was just fixed (de-dup §S of the staking plan) by making "is the daemon actually minting?" continuously visible.

### 8.1 Suggested phase placement
- **Phase E4 — Explorer hardening (no iquidus needed):** #1 time-series, #2 health banner, #3 alert, #4 cache/ETag, #5 search box.
- **Phase E5 — Post-iquidus (after E1):** #7 block feed, #8 true pool share, #10 masternode page; #6 multi-source price and #9 SSE slot into either as capacity allows.

### 8.2 Phase E4 — built (2026-06-03)
- [x] **#1 Time-series:** `backend/services/mn2_network_stats.py` (throttled ~10-min snapshots to `data/mn2_network_history.jsonl`, capped) + `GET /api/mn2/network-history`; sparklines for price/difficulty/network-weight/pool on `/explorer`.
- [x] **#2 Health banner:** `network-overview` now includes `staking_health` (`getstakingstatus`-based on MN2); `/explorer` shows a green/amber/red daemon-minting banner.
- [x] **#3 Stop-staking / stall alert:** edge-triggered `staking_stopped` (active→inactive) and `height_stall` (no height progress ≥30 min) → `logs/mn2_network_alerts.jsonl`, optional admin notify via `MN2_ALERT_USER_ID`, exposed at `GET /api/mn2/network-alerts`.
- [x] **#4 Cache/ETag:** `network-overview` returns `Cache-Control: public, max-age=30` + weak `ETag` with `304` revalidation.
- [x] **#5 Search box:** `/explorer` address/txid search deep-links via the `explorer_kind`-aware builder (Chainz `.dws` now, iquidus paths after cutover).

### 8.3 Phase E5 — built via RPC (2026-06-03, no iquidus needed)
Probe confirmed MN2 supports `getbestblockhash`/`getblockhash`/`getblock`, `gettxoutsetinfo`, and `listmasternodes` (but not `getmoneysupply`/`getmasternodelist`). So E5's data items were built directly off RPC instead of waiting for iquidus:
- [x] **#7 Latest blocks:** `backend/services/mn2_explorer_data.recent_blocks()` (RPC tip-walk, cached ~30s) + `GET /api/mn2/recent-blocks`; "Latest blocks" table on `/explorer` (height/age/txs/size, height links to explorer).
- [x] **#8 Pool share (coins-denominated):** `circulating_supply` from `gettxoutsetinfo.total_amount` (cached ~10 min) in `network-overview`; `/explorer` shows **Circulating Supply** + **Pool % of Supply** tiles (honest supply-based share; true stake-weight share still needs iquidus rich list).
- [x] **#10 Masternodes:** `mn2_explorer_data.masternodes()` (`listmasternodes`, cached ~60s) + `GET /api/mn2/masternodes`; Masternodes section on `/explorer` (enabled/total summary + rank/address/status/active table) and a tokenomics note (50/50 MN/staking).
- **Deferred:** #6 multi-source price (no second MN2 USD feed exists — Chainz only); #9 SSE (optional polish, poll works fine at current scale).

---

## E1. Self-hosted explorer — built (2026-06-04)

Stood up a real block explorer from source at **https://camgirls.masternoder.dk/**. Key reality vs. the original plan:

- **Explorer engine: eiquidus** (`team-exor/eiquidus`, the maintained iquidus successor), **not** classic `iquidus/explorer`. Classic iquidus is archived and won't build on Ubuntu 24.04 + Node 20. eiquidus uses the **same `/block/`, `/tx/`, `/address/` URL shape**, so the `explorer_kind: iquidus` link helper (E2) is unaffected.
- **Server stack (all installed this phase):** Node 20.20.2 (NodeSource) + build-essential; MongoDB **8.0** (official repo; host has AVX2 so 8.0 runs); PM2 (single worker via `bin/cluster 1` to fit RAM); nginx vhost → `127.0.0.1:3000` + Let's Encrypt TLS (`certbot --nginx`, auto-renew). DNS for `camgirls` already pointed at the host.
- **Daemon indexing:** active datadir is **`/var/www/html/config`** (systemd unit `masternoder2d.service`). Daemon binary only supports **`-txindex`** (no `addressindex`/`spentindex`/`timestampindex`). Set `txindex=1` + one-time reindex (~900k blocks / 1.2 GB; reindex paused staking ~1 h and tripped the E4 stop-staking/stall alerts as expected). eiquidus builds its **own** address index in Mongo by walking blocks, so daemon `addressindex` is unnecessary — `txindex` (for `getrawtransaction`) is the only requirement. `getrawtransaction` on historical txs confirmed working post-reindex.
- **`settings.json` (key values):** `coin.name=MasterNoder2`, `symbol=MN2`; `wallet` → `localhost:9332` with the daemon's `rpcuser`/`rpcpassword` from `/var/www/html/config/masternoder2.conf`; `dbsettings` → `iquidus@explorerdb` (Mongo pw generated, stored root-only in `/root/explorer_secrets.env`, auth enabled); `webserver.port=3000`; `sync.supply="GETINFO"` (daemon `getinfo.moneysupply` works); `genesis_block=00000742f6…e1e9993`, `genesis_tx=662873dc…aa8080`; `api_cmds.getmasternodelist="listmasternodes"` (eiquidus default already matches MN2); `markets_page` disabled (price comes from Chainz on the Flask side). Parsed/patched via the bundled `jsonminify` so comment/URL handling is safe.
- **Sync:** initial `node scripts/sync.js index update` runs in the background (nohup, resumable). Cron `/etc/cron.d/eiquidus` drives ongoing `index update` (1 min, lock-guarded), `peers` (5 min), `masternodes` (10 min). Full historical index completes over a few hours; `/ext/getmoneysupply` + homepage already serve.
- **Resourcing:** host is 1.9 GB RAM; added a 2 GB swapfile (`/swapfile2`, total ~4.3 GB) before installing the DB stack. Single PM2 worker + `block_parallel_tasks` defaults keep memory in check alongside `masternoder2d` + Mongo + Flask/uwsgi.

**Next: Phase E2** — flip the on-site tx/address links from Chainz `.dws` to the self-hosted `/tx/…`,`/address/…` shape via `explorer_kind`, and optionally add an iquidus stats tier in `network_overview()`. Hold the final `explorer_base_url` flip until the initial index has fully populated address pages.
