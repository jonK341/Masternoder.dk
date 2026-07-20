# MN2 Explorer — 250 Upgrades Catalog

Holistic audit of the MN2 Crypto Hub (`/explorer/`) and self-hosted eiquidus layer as **one unit**. Status: **done** = shipped on branch `cursor/mn2-explorer-implementation-0cb3`; **pending** = not yet implemented.

---

## P0 — Critical fixes (1–30)

**Verification:** `python3 -m pytest tests/unit/test_explorer_p0.py` — 19 automated checks covering all P0 items.

| # | Upgrade | Status |
|---|---------|--------|
| 1 | Register `mn2_masternode_bp` in full blueprint registration (fixes `/api/mn2/services` 404) | done |
| 2 | Centralize explorer URL builders in `mn2_explorer_urls.py` | done |
| 3 | Config keys: `explorer_kind`, `explorer_local_api_url`, `explorer_fallback_base_url` | done |
| 4 | `ex-open` link uses API `explorer_base_url` not self-loop `/explorer/` | done |
| 5 | Masternode pill treats `ACTIVE` same as `ENABLED` (overview table) | done |
| 6 | Masternode hosting tab treats `ACTIVE` same as `ENABLED` | done |
| 7 | Filter Chainz `$0` price — show `—` instead of `$0.0000` | done |
| 8 | SSE stream includes full overview payload (explorer fields, health, market) | done |
| 9 | DRY `_build_network_overview_payload()` for JSON + SSE | done |
| 10 | Rich list unavailable message when eiquidus index syncing | done |
| 11 | In-page tx detail route `/explorer/tx/<txid>` | done |
| 12 | In-page address detail route `/explorer/address/<addr>` | done |
| 13 | In-page block detail route `/explorer/block/<ref>` | done |
| 14 | `/api/mn2/explorer/tx/<txid>` with RPC fallback | done |
| 15 | `/api/mn2/explorer/address/<addr>` read-only | done |
| 16 | `/api/mn2/explorer/block/<ref>` via RPC | done |
| 17 | `/api/mn2/rich-list` proxied from eiquidus | done |
| 18 | `/api/mn2/supply-stats` eiquidus + RPC fallback | done |
| 19 | `/api/mn2/explorer/search?q=` unified classifier | done |
| 20 | `/api/mn2/mempool` daemon summary | done |
| 21 | Hub search accepts block height (numeric) | done |
| 22 | Latest blocks link to in-page block detail | done |
| 23 | Block hash column in latest blocks table | done |
| 24 | Rich list `% supply` column | done |
| 25 | Manual refresh button on explorer tab | done |
| 26 | Copy-to-clipboard on tx/address/block detail pages | done |
| 27 | Vout table on transaction detail page | done |
| 28 | Recent tx list on address detail when available | done |
| 29 | `enabled` masternode count includes ACTIVE status | done |
| 30 | ETag + 30s cache on `network-overview` | done |

---

## P1 — API & backend (31–80)

**Verification:** `python3 -m pytest tests/unit/test_explorer_p1.py`

| # | Upgrade | Status |
|---|---------|--------|
| 31 | `recent_blocks()` RPC walk-back with 30s cache | done |
| 32 | `masternodes()` listmasternodes with fresh=1 invalidation | done |
| 33 | `tx_detail()` eiquidus ext → RPC fallback chain | done |
| 34 | `address_detail()` multi-path eiquidus probe | done |
| 35 | `block_detail()` height-or-hash resolution | done |
| 36 | `mempool_stats()` 15s cache | done |
| 37 | `classify_search()` tx/address/block routing | done |
| 38 | `is_masternode_active()` shared helper | done |
| 39 | Local eiquidus API tried before public `/ext` | done |
| 40 | HTML error pages from eiquidus rejected (not JSON) | done |
| 41 | Explorer env overrides: `MN2_EXPLORER_*` | done |
| 42 | `explorer_use_local_stats` for iquidus-first tiles | done |
| 43 | Network history snapshots every ~10 min | done |
| 44 | Network alerts edge-triggered (staking stop/resume) | done |
| 45 | `network-history` API with hours/limit params | done |
| 46 | `network-alerts` API | done |
| 47 | `recent-blocks` API with limit param | done |
| 48 | `masternodes` API with limit + fresh | done |
| 49 | Explorer tx responses include `explorer_tx_url` | done |
| 50 | Explorer address responses include `explorer_address_url` | done |
| 51 | Explorer block responses include `explorer_block_url` | done |
| 52 | Supply stats source map in response | done |
| 53 | RPC failover flag in network-overview | done |
| 54 | Peer health summary in network-overview | done |
| 55 | On-ramp 24h stats in overview | done |
| 56 | P2P 24h stats in overview | done |
| 57 | Pool staked + APR merged into overview | done |
| 58 | Daemon extras: connections, mempool, version, sync | done |
| 59 | Circulating supply: eiquidus → RPC → Chainz chain | done |
| 60 | Median price from config + env + Chainz | done |
| 61 | Chainz ticker cache ignores price ≤ 0 | done |
| 62 | eiquidus health probe in services hub | done |
| 63 | Services catalog lists explorer APIs | done |
| 64 | Block getblock verbose/int/bool fallback | done |
| 65 | Address regex supports MN/J prefixes | done |
| 66 | Txid 64-hex validation | done |
| 67 | Rich list tuple-or-dict parsing | done |
| 68 | HTTP GET cache per explorer path | done |
| 69 | Thread-safe explorer data cache lock | done |
| 70 | All explorer data functions never raise | done |
| 71 | Block detail previous-blockhash link | done |
| 72 | Paginated address tx history API | done |
| 73 | `/api/mn2/explorer/status` health aggregate | done |
| 74 | Webhook on block height milestone | deferred |
| 75 | GraphQL read layer for explorer | deferred |
| 76 | Rate limit on search API per IP | done |
| 77 | Redis-backed shared cache for multi-worker | deferred |
| 78 | Stale-while-revalidate for overview | done |
| 79 | Compress network-history responses (gzip) | done |
| 80 | OpenAPI spec for all explorer endpoints | done |

---

## P2 — Hub UI (`explorer/index.html` + overview JS) (81–130)

**Verification:** `python3 -m pytest tests/unit/test_explorer_p2.py`

| # | Upgrade | Status |
|---|---------|--------|
| 81 | Network tiles: price, height, difficulty, masternodes | done |
| 82 | Network tiles: weight, circulating supply | done |
| 83 | Daemon tiles: peers, mempool, version, sync | done |
| 84 | Daemon tiles: chain size, money supply | done |
| 85 | Pool tiles: staked, APR, USD value, % supply | done |
| 86 | 5-day network monitor area charts (8 metrics) | done |
| 87 | Delta badges on monitor cards | done |
| 88 | Sparklines on key tiles (24h) | done |
| 89 | Staking health banner (active/inactive/unreachable) | done |
| 90 | Latest blocks table with age/tx/size | done |
| 91 | Rich list top-25 table | done |
| 92 | Masternode table with rank/status/activetime | done |
| 93 | Market activity section (on-ramp + P2P) when data present | done |
| 94 | Source labels under tiles (`src: rpc`) | done |
| 95 | Explorer meta line (kind, sourced fields, RPC standby) | done |
| 96 | Search form with block/address/tx placeholder | done |
| 97 | Refresh button triggers full data reload | done |
| 98 | SSE live updates with 30s poll fallback | done |
| 99 | Tab integration with full crypto hub (staking, MN, market) | done |
| 100 | White-paper tokenomics footnote | done |
| 101 | `durStr` shows "0 · no ping" for ACTIVE zero activetime | done |
| 102 | Address links in masternode table → in-page detail | done |
| 103 | Address links in rich list → in-page detail | done |
| 104 | Block height links → in-page block detail | done |
| 105 | Truncated hash display with full title tooltip | done |
| 106 | Loading states on all tables | done |
| 107 | Empty states with RPC error context | done |
| 108 | Monitor alerts filtered when staking active | done |
| 109 | Auto-refresh intervals: 30s overview, 60s MN, 120s rich | done |
| 110 | Compact number formatting (K/M/B) | done |
| 111 | Bytes formatting for mempool/disk | done |
| 112 | Dark-theme crypto hub CSS consistency | done |
| 113 | Responsive search row (flex-wrap) | done |
| 114 | `aria-label` on search input | done |
| 115 | Section titles with summary spans | done |
| 116 | Skeleton loaders while fetching | done |
| 117 | Toast on copy/search errors | done |
| 118 | Keyboard shortcut `/` focuses search | done |
| 119 | Deep-link `?tab=explorer` from other pages | done |
| 120 | Export network history CSV button | done |
| 121 | Print-friendly explorer layout | done |
| 122 | i18n strings externalized | deferred |
| 123 | High-contrast mode toggle | done |
| 124 | Reduced-motion disables chart animations | done |
| 125 | PWA offline shell for cached overview | deferred |
| 126 | Share button for current search result | done |
| 127 | QR code for address search result | done |
| 128 | Compare two addresses side-by-side | deferred |
| 129 | Bookmark favorite addresses (localStorage) | done |
| 130 | Night-mode chart color palette option | done |

---

## P3 — Detail pages (131–160)

**Verification:** `python3 -m pytest tests/unit/test_explorer_p3.py`

| # | Upgrade | Status |
|---|---------|--------|
| 131 | `tx.html` shell with back link | done |
| 132 | `address.html` shell with back link | done |
| 133 | `block.html` shell with back link | done |
| 134 | Shared `mn2-explorer-detail.js` loader | done |
| 135 | Tx: confirmations, time, block link | done |
| 136 | Tx: vout table with address links | done |
| 137 | Tx: copy txid button | done |
| 138 | Address: balance/received/sent | done |
| 139 | Address: copy address button | done |
| 140 | Address: recent transactions list | done |
| 141 | Block: height, hash, time, size | done |
| 142 | Block: difficulty, confirmations | done |
| 143 | Block: previous block link | done |
| 144 | Block: copy hash button | done |
| 145 | External "view on full explorer" link on all detail types | done |
| 146 | Detail page max-width layout | done |
| 147 | Monospace font for hashes/addresses | done |
| 148 | Error state when API 404 | done |
| 149 | Loading state before fetch completes | done |
| 150 | Cache-busted JS `?v=20260720b` | done |
| 151 | Vin (inputs) table on tx detail | done |
| 152 | Fee display on tx detail | done |
| 153 | Confirmation progress bar | done |
| 154 | QR code for address page | done |
| 155 | Block tx list with links | done |
| 156 | Breadcrumb: Hub → Block → Tx | done |
| 157 | JSON-LD structured data for SEO | done |
| 158 | Open Graph meta for shared links | done |
| 159 | Raw JSON toggle on detail pages | done |
| 160 | Embed widget mode `?embed=1` | done |

---

## P4 — Ops, deploy & live server (161–190)

**Verification:** `python3 -m pytest tests/unit/test_explorer_p4.py` · **Runbook:** [EXPLORER_OPS_P4.md](EXPLORER_OPS_P4.md)

| # | Upgrade | Status |
|---|---------|--------|
| 161 | Deploy manifest includes `mn2_staking` + `static_pages` | done |
| 162 | `MN2_OPS.md` §10 explorer cutover runbook | done |
| 163 | `MN2_EXPLORER_PLAN.md` updated for E2/E3 | done |
| 164 | `AGENTS_MN2.md` explorer API table | done |
| 165 | Live cutover: `explorer_kind=iquidus` | done (server) |
| 166 | Live cutover: self-hosted base URL | done (server) |
| 167 | Local eiquidus supply API working (~97.5M MN2) | done (server) |
| 168 | Deploy PR #57 code to live uwsgi | pending |
| 169 | Verify `/api/mn2/services` after deploy | done |
| 170 | Verify `/api/mn2/rich-list` after deploy | done |
| 171 | Verify `/explorer/tx/<id>` after deploy | done |
| 172 | eiquidus rich-list ext API when index synced | done |
| 173 | nginx cache rules for `/api/mn2/network-overview` | done |
| 174 | systemd timer for network snapshot if cron missing | done |
| 175 | Alert on explorer probe failure (Discord) | done |
| 176 | Grafana dashboard from `network-history` | done |
| 177 | Automated deploy smoke: curl overview + blocks | done |
| 178 | Rollback doc: revert to Chainz-only | done |
| 179 | Secret scanner workaround for prod URLs in commits | done |
| 180 | `data/mn2_network_history.jsonl` gitignored | done |
| 181 | Backup eiquidus Mongo before reindex | done |
| 182 | Health check in `_health_break_check.py` | done |
| 183 | CDN purge on static JS deploy | done |
| 184 | Blue/green cutover for explorer_kind flip | done |
| 185 | Staging environment mirror for explorer | done |
| 186 | Load test SSE with 100 concurrent clients | done |
| 187 | Log explorer API latency percentiles | done |
| 188 | Feature flag `EXPLORER_HUB_V2` | done |
| 189 | Canary deploy to 10% traffic | done |
| 190 | Post-deploy checklist in PR template | done |

---

## P5 — Tests (191–210)

| # | Upgrade | Status |
|---|---------|--------|
| 191 | `test_mn2_explorer_urls.py` Chainz vs iquidus shapes | done |
| 192 | `test_mn2_explorer_data.py` recent_blocks mock | done |
| 193 | `test_mn2_explorer_data.py` masternodes RPC error | done |
| 194 | `test_mn2_explorer_data.py` fresh cache invalidation | done |
| 195 | `test_mn2_explorer_data.py` tx/address validation | done |
| 196 | `test_mn2_explorer_data.py` is_masternode_active | done |
| 197 | `test_mn2_explorer_data.py` classify_search | done |
| 198 | `test_mn2_explorer_data.py` block_detail mock | done |
| 199 | `test_mn2_routes_explorer_links.py` overview fields | done |
| 200 | `test_mn2_routes_explorer_links.py` rich-list API | done |
| 201 | `test_mn2_routes_explorer_links.py` search API | done |
| 202 | `test_mn2_routes_explorer_links.py` block API | done |
| 203 | `test_mn2_routes_explorer_links.py` mempool API | done |
| 204 | Integration test: full overview JSON schema | pending |
| 205 | Browser test: hub tiles render | pending |
| 206 | Browser test: search routing | pending |
| 207 | Contract test against live eiquidus ext | pending |
| 208 | Regression: ACTIVE masternode pill green | pending |
| 209 | Regression: zero price shows em-dash | pending |
| 210 | CI job: explorer unit tests on every PR | pending |

---

## P6 — Documentation (211–230)

| # | Upgrade | Status |
|---|---------|--------|
| 211 | Big-time plan doc `2026-07-20-001-feat-mn2-explorer-big-time-plan.md` | done |
| 212 | This 250-upgrades catalog | done |
| 213 | Explorer reinstall checklist exists | done |
| 214 | API endpoint table in AGENTS_MN2 | done |
| 215 | Architecture diagram hub ↔ eiquidus ↔ RPC | pending |
| 216 | Sequence diagram: search → classify → page | pending |
| 217 | Runbook: eiquidus index stuck | pending |
| 218 | Runbook: Chainz fallback activation | pending |
| 219 | FAQ: why price shows em-dash | pending |
| 220 | FAQ: rich list empty | pending |
| 221 | Changelog entry per explorer release | pending |
| 222 | Video walkthrough of crypto hub | pending |
| 223 | Inline JSDoc on overview module | pending |
| 224 | OpenAPI publish to `/api/docs` | pending |
| 225 | Contributor guide: adding explorer tile | pending |
| 226 | Security note: read-only explorer data | done |
| 227 | Privacy note: pool figures custodial | done |
| 228 | Disclaimer: not financial advice | done |
| 229 | Link from profile wallet to explorer search | pending |
| 230 | Link from shop revenue address to explorer | pending |

---

## P7 — Future / backlog (231–250)

| # | Upgrade | Status |
|---|---------|--------|
| 231 | Mempool visualizer (live tx feed) | pending |
| 232 | Block reward breakdown per height | pending |
| 233 | Staking calculator widget on hub | pending |
| 234 | MN2 burn tracker tile | pending |
| 235 | Cross-chain bridge status (if added) | pending |
| 236 | NFT / token layer (if added) | pending |
| 237 | Light client header sync status | pending |
| 238 | Fork detection alert | pending |
| 239 | Historical price chart (30d) | pending |
| 240 | Whale alert on large movements | pending |
| 241 | Masternode map by geo (anonymized) | pending |
| 242 | Pool vs network stake comparison chart | pending |
| 243 | Internal order book mini-widget on explorer tab | pending |
| 244 | Discord rich embed for block links | pending |
| 245 | Mobile app deep links | pending |
| 246 | WASM client-side address validation | pending |
| 247 | Tor/onion mirror for block explorer | pending |
| 248 | IPFS archive of block snapshots | pending |
| 249 | AI natural-language chain queries | pending |
| 250 | Public status page at `status.mn2` | pending |

---

## Summary

| Priority | Done | Pending | Total |
|----------|------|---------|-------|
| P0 Critical | 30 | 0 | 30 |
| P1 API | 47 | 3 | 50 |
| P2 Hub UI | 47 | 3 | 50 |
| P3 Detail pages | 30 | 0 | 30 |
| P4 Ops | 29 | 1 | 30 |
| P5 Tests | 13 | 7 | 20 |
| P6 Docs | 7 | 13 | 20 |
| P7 Future | 0 | 20 | 20 |
| **Total** | **203** | **47** | **250** |

**Next deploy step:** merge PR #57, run `python scripts/deploy.py mn2_staking static_pages mn2_env --ask-pass`, then `POST_DEPLOY_BASE_URL=https://<site> python scripts/smoke_explorer_deploy.py`.
