# MN2 TODO

Last updated: **2026-06-20** (mn2_next_ops + optionals crons · 5-node masternode fleet · Discord `#market` webhook fixed · catalog perf fix pending deploy · v1.2.3.0 build stalled)

See [MN2_RELEASE_BUILD.md](MN2_RELEASE_BUILD.md) · [MN2_TRADER_MARKET.md](MN2_TRADER_MARKET.md) · [MONETIZATION_PAYPAL.md](MONETIZATION_PAYPAL.md) · [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md) · [CAMGIRLS_PHASE1C.md](CAMGIRLS_PHASE1C.md)

---

## Done ✓

- Explorer · staking · trader pool/market · Game Hub · compendium calm reader (V1–V16)
- Camgirls Phase 1c + daemon payouts — **5 live AI models** (Nova, Luna, Sage, Ember, Iris)
- **Discord cross-roads (code)** — market fan-out, alert funnel types, affiliate rotator, FAQ, trader tick emit
- **Shop V.9 MN2 services** — masternode hosting catalog, live slot meter, Proof of Reserves SKU, digital downloads, unified purchase history
- **Masternode hosting checkout (multi-rail)** — PayPal **$4.99/slot**, coins, in-wallet MN2, on-chain MN2; shop + Explorer
- `**mn2_staking` deploy + trader market verify** — 2026-06-17
- **Tier A monetization (repo)** — shop revenue strip, featured coin pack, Discord promo codes (`DISCORD-STARTER`, `MARKET-BONUS`), checkout promos (`GENERATE10`, `HOSTMN5`), Explorer staking CTAs; cron files for market fan-out + monetization emails
- **M8 promo rotator (#52)** — `promo_rotator_payload()` + `/api/discord/m8/promo-rotator` + `cron/discord_promo_rotator.sh` (Mon/Wed/Fri); affiliate rotator embeds shop promo hints
- **Compendium 25/25 milestone** — `compendium_milestone_service` → `platform_news` + Discord + 0.01 MN2 + `#game` fanout
- **Tier B1 MN2 starter bundle** — `bundle-mn2-starter` (500 coins + 7-day staking booster + badge) in `monetization_config.json`
- **Game tabulator v2 + level MN2 rewards** — grouped hub nav on `/game/`; `GET/POST /api/game/crypto/level-rewards`
- **Tier C1/C2** — referral purchase credits + post-purchase upsell modal
- **Tier C3 weekly revenue pulse** — admin email from ledger + hosting + camgirls tips (Mon cron)
- **Tier C4 SEO** — `/hosting/` landing, generator/camgirls meta, sitemap + robots
- **Tier C5 compendium paid chapters** — free pages 1–3, premium SKUs, milestone webhooks at 3/10/25
- **Tier C6 hosting Discord VIP** — auto-role on paid hosting when Discord linked (M8 #51)
- **Tier B2 on-ramp + hosting** — sequenced bundle with auto HOSTMN5 on PayPal hosting checkout
- **Camgirls deploy + verify (2026-06-18)** — `mn2_env` + `camgirls` manifests via `--ask-pass`; 5/5 payout addresses (Nova–Iris); public verify **4/4** (60s timeout in `camgirls_post_deploy_verify.py`); agents burst **6/6** stable after `deploy.py` dual uwsgi restart (`:5000` + `:5001`)

- **Tier D1–D3** — marketplace bid escrow, LiveKit voice spike, mobile IAP stub
- **Deploy 2026-06-20** — `deploy.py mn2_staking --upload-only` + `apply_updates.py` (98 files); python-proxy + uwsgi-vidgenerator restarted
- **`mn2_next_ops_remote.py --ask-pass --optionals`** — 2026-06-20: masternode provision cron, Discord market + promo + monetization + revenue-pulse + margin-report crons; fleet verify **5/5 active** (`platform-mn-1`…`5`, 95 slots free)
- **`mn2_ops_optionals_remote.py --ask-pass --all`** — 2026-06-20: `AGENT_CRON_SECRET` + `COGS_ADMIN_REPORT_KEY` bootstrapped; crons reinstalled; smoke **3/3** (livekit stub, report 200, revenue pulse 200 `email_sent=false`)
- **Discord `#market` webhook** — `DISCORD_CHANNEL_ID_MARKET` set to full webhook URL on server (2026-06-20 audit); fixes prior **403** on spotlight fan-out

---

## Next sprint (Phase next) — prioritized

Run top-down. **Owner:** `SSH` = server via `--ask-pass` · `Win` = Windows deploy scripts · `Code` = repo change + deploy.

| Pri | Task | Owner | Depends on | Command / note |
| --- | ---- | ----- | ---------- | -------------- |
| **P0** | **Camgirls catalog perf** — public `/api/camgirls/performers` was ~19–25s (tip index N× reads); fix in repo (`_tip_index` cache, `lite=1`, batched enrich) | Win → SSH | uncommitted code | `python scripts/deploy.py camgirls --ask-pass` then `python scripts/camgirls_post_deploy_verify.py --base-url https://masternoder.dk` → **4/4** |
| **P0** | **v1.2.3.0 release tarball** — tag exists; GitHub draft asset still missing; blocks daemon upgrade | Win | interactive SSH; `libgmp-dev` on server if linker fails | See [§ Release v1.2.3.0](#3-v1230-release-binary-tag-exists-github-release-asset-missing) — **2026-06-18 build session had no captured output**; confirm `/tmp/mn2-build.log` on server or re-run |
| **P0** | **Discord spotlight fan-out** — platform news OK; re-post to `#market` now webhook URL is fixed | SSH | webhook env (done) | `python scripts/camgirls_discord_spotlight.py --remote-only --ask-pass` |
| **P1** | **Restore staking + trader market** — wallet unlock + market ticks (not run yet) | Win | base crons (done) | `python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking` |
| **P1** | **Post-deploy smoke** — shop/hosting/monetization UI + Tier D APIs | Win / manual | Tier D deploy (done) | Table in [§2 Post-deploy smoke](#2-post-deploy-smoke-hosting--shop) |
| **P1** | **Live Pro subscription** — replace `P-PLACEHOLDER-PRO` + `PAYPAL_WEBHOOK_ID` | SSH + Code | PayPal dashboard | Edit server `.env` + `data/monetization_config.json`; redeploy `mn2_staking` |
| **P1** | **Tier enforcement on server** — premium generator caps | SSH | monetization config live | Set `MONETIZATION_TIER_ENFORCEMENT=1` in server `.env`; reload uwsgi |
| **P1** | **SMTP + admin email** — weekly revenue pulse + margin report emails | SSH | none | `NOTIFY_ADMIN_EMAIL` + `NOTIFY_SMTP_*` via optionals flags or edit server `.env` |
| **P2** | **Daemon upgrade v1.2.3.0** | Win | **P0 release asset published** | `mn2_daemon_upgrade_remote.py --ask-pass --apply` + `--verify-post` |
| **P2** | **LiveKit voice (Camgirls Phase 3)** — currently `mode=stub` | SSH | LiveKit cloud creds | `mn2_ops_optionals_remote.py --ask-pass --livekit-url … --reload --verify` |
| **P2** | **Sync local `DEPLOY_PASS`** — non-interactive SSH still fails without matching password | Win | none | Update local `.env` to match server |
| **P2** | **Camgirls Phase 4 nginx** — only if moving UI to `camgirls.masternoder.dk/app/` | SSH | product decision | [CAMGIRLS_PHASE4_NGINX.md](CAMGIRLS_PHASE4_NGINX.md) |

### `mn2_next_ops_remote.py` scope

One SSH session: install **masternode provision**, **Discord market fan-out**, **monetization retention**, **revenue pulse**, **margin report**, **promo rotator** crons; fix `masternode.conf` perms; verify `GET /api/mn2/masternode/service`; retry `provision-pending`. Flags: `--restore-staking` (wallet unlock + trader ticks), `--camgirls` (payouts + verify + spotlight API), `--optionals` (chain `mn2_ops_optionals_remote.py --all`), `--purge-stale-hosts`.

**2026-06-20:** base + `--optionals` completed. Still open: `--restore-staking`, `--camgirls` spotlight re-run.

---

## Next — run in order

### 1. One-shot server ops (requires `--ask-pass` — `.env` `DEPLOY_PASS` still stale for non-interactive SSH)

**Done 2026-06-18:** `deploy.py mn2_env --ask-pass` + `deploy.py camgirls --ask-pass` (onboard + payouts + social layer live).

**Done 2026-06-20:** `mn2_next_ops_remote.py --ask-pass --optionals` (all crons + fleet verify) · `mn2_ops_optionals_remote.py --ask-pass --all` (secrets + smoke 3/3).

**Still pending:**

```powershell
python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking
python scripts/camgirls_discord_spotlight.py --remote-only --ask-pass
python scripts/deploy.py camgirls --ask-pass
```

**Optionals (done 2026-06-20 — re-run only after env changes):**

```powershell
python scripts/mn2_ops_optionals_remote.py --ask-pass --audit
python scripts/mn2_ops_optionals_remote.py --ask-pass --all
# LiveKit when you have cloud.livekit.io credentials:
python scripts/mn2_ops_optionals_remote.py --ask-pass --livekit-url wss://....livekit.cloud --livekit-api-key APIxxx --livekit-api-secret SECxxx --reload --verify
```

Installs: masternode provision cron, **Discord market fan-out**, **monetization retention cron**, API verify, optional wallet unlock + trader ticks.

Then deploy monetization UI + config (if not already current on server):

```powershell
python scripts/deploy.py mn2_staking --ask-pass
```

**2026-06-20 deploy:** routes + Tier D live. ~~Pending one file: `monetization_config_service.py`~~ **verified** — `/api/generator/api/tiers` returns 3 tiers.

```powershell
# Hotfix only if monetization_config_service.py changes again:
python scripts/deploy.py --files backend/services/monetization_config_service.py --ask-pass
python scripts/apply_updates.py --ask-pass
```

### 2. Post-deploy smoke (hosting + shop)


| Check              | Where                                     | Pass criteria                                    |
| ------------------ | ----------------------------------------- | ------------------------------------------------ |
| Slot meter         | `/shop?tab=mn2`                           | “Hosting slots: N available … $4.99/slot”        |
| Revenue strip      | `/shop` catalog tab                       | Host / coins / boosters / camgirls links visible |
| Featured pack      | `/shop` → PayPal & coins                  | **500 Coins** has “BEST VALUE” badge             |
| Promo redeem       | Shop promo box                            | `DISCORD-STARTER` → +100 coins                   |
| Quote API          | `POST /api/mn2/masternode/checkout/quote` | `coins_total`, `mn2_total`, `payment_rails`      |
| Multi-rail hosting | Shop MN2 tab                              | PayPal / coins / MN2 / on-chain each provision   |
| Generator API tiers | `GET /api/generator/api/tiers`           | `tiers` length **3** (needs `monetization_config_service.py` on server) |
| Mobile IAP catalog | `GET /api/mobile/iap/catalog`             | `products` length **3**                          |
| Marketplace escrow | `GET /api/shop/marketplace/escrow?user_id=x` | `success: true` (may be slow ~20s first hit)  |


### 3. v1.2.3.0 release binary (tag exists; GitHub release asset missing)

**2026-06-18:** First remote build failed (`__gmpz_*` linker — ensure `libgmp-dev` on server). Retry started via `mn2_build_release_remote.py --ask-pass --publish --draft` — **no captured stdout** in local terminal (check server `/tmp/mn2-build.log` or re-run).

**Option A — build on server:**

```powershell
python scripts/mn2_build_release_remote.py --ask-pass --publish --draft
```

**Option B — Linux/WSL:**

```bash
bash scripts/mn2_build_release.sh
python scripts/mn2_publish_release.py --tarball /tmp/mn2-build/dist/masternoder2d.tar.gz \
  --manifest /tmp/mn2-build/dist/RELEASE_MANIFEST.json --skip-tag --draft
```

### 4. Daemon upgrade (after release asset is live)

```powershell
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --apply
python scripts/mn2_daemon_upgrade_remote.py --ask-pass --verify-post
```

### 5. Manual ops checklist

- [x] **Revive / register 1 masternode** — `platform-mn-1` ENABLED 2026-06-17
- [x] **Deploy masternode hosting (multi-rail + shop/explorer UI)** — 2026-06-17
- [x] **Masternode post-deploy on deploy** — `deploy.py mn2_staking` runs provision cron + fleet seed + game cron
- [x] **Deploy `mn2_env` + `camgirls`** — `--ask-pass` 2026-06-18 (5/5 performers, verify 4/4 public, agents 6/6)
- [x] **Run `mn2_next_ops_remote.py --ask-pass`** — 2026-06-20 with `--optionals` (crons + fleet 5/5)
- [x] **Run `mn2_ops_optionals_remote.py --ask-pass --all`** — 2026-06-20: secrets OK, crons OK, smoke 3/3 (livekit stub, report 200, cron 200 `email_sent=false`)
- [ ] **Restore staking + market** — `--restore-staking` on `mn2_next_ops_remote.py`
- [ ] **Deploy camgirls catalog perf fix** — `_tip_index` cache + verify 60s timeout (uncommitted)
- [ ] **Re-run Discord spotlight fan-out** — webhook URL fixed 2026-06-20; platform news already published
- [ ] **Sync `DEPLOY_PASS` in local `.env`** — `--ask-pass` works; non-interactive SSH still needs matching password
- [ ] **Live Pro subscription** — replace `P-PLACEHOLDER-PRO` in `monetization_config.json` + `PAYPAL_WEBHOOK_ID`
- [ ] **SMTP + admin email** — `NOTIFY_ADMIN_EMAIL` + `NOTIFY_SMTP_*` (blocks weekly pulse/margin emails)
- [ ] **LiveKit** — `LIVEKIT_*` on server (camgirls voice currently `mode=stub`)
- [x] **Discord #market** — webhook URL set; fan-out cron installed

---

## Camgirls

- [x] Phase 1c + daemon payouts — 5 performers
- [x] **Studio stack** — voice, music, dances, gifts, goals, wheel/dice, emoji, buzz bar
- [x] **Social layer** — favorites, fan club, offline inbox, private show, moods/scenes, leaderboard, chat history
- [x] **Deploy** `camgirls` manifest — social layer live 2026-06-18 (`deploy.py camgirls --ask-pass`)
- [x] **Server onboard + payouts** — 5/5 performers (Nova, Luna, Sage, Ember, Iris), daemon payout addresses on server
- [x] **Post-deploy verify** — public **4/4** + remote checks pass; agents burst **6/6** stable (2026-06-18). Public timeout **60s** in `camgirls_post_deploy_verify.py` (uncommitted repo fix).
- [x] **Discord spotlight — platform news** — partner-spotlight API published news item 2026-06-18
- [ ] **Discord spotlight — webhook fan-out** — was HTTP **403** (fixed: `DISCORD_CHANNEL_ID_MARKET` = full webhook URL on server 2026-06-20); **re-run spotlight:**
  ```powershell
  python scripts/camgirls_discord_spotlight.py --remote-only --ask-pass
  ```
- [ ] **Catalog perf deploy** — repo fix for ~19–25s public `/api/camgirls/performers`; deploy `camgirls` manifest + verify **4/4**
- [ ] **Phase 3 — LiveKit voice** — optional; set `LIVEKIT_*` via `mn2_ops_optionals_remote.py` (currently `mode=stub`)

---

## Monetization machine — revenue tracks

North star: [MONETIZATION_PAYPAL.md §0](MONETIZATION_PAYPAL.md#0-single-metric-north-star).

### Tier A — shipped in repo (deploy to activate)


| #   | Track                      | Status                                                                                  |
| --- | -------------------------- | --------------------------------------------------------------------------------------- |
| A1  | Pro subscription           | **Ops** — replace PayPal plan id                                                        |
| A2  | Coin pack hero             | ✓ `featured` on 500-coin pack + BEST VALUE badge                                        |
| A3  | Hosting funnel             | ✓ Shop revenue strip + Explorer staking CTAs                                            |
| A4  | Staking boosters           | ✓ Linked from shop strip; promote on monitor (copy done)                                |
| A5  | Camgirls monetization      | ✓ Deployed 2026-06-18 — tips/payouts live; catalog perf fix + spotlight fan-out re-run pending |
| A6  | Discord promo codes        | ✓ `DISCORD-STARTER`, `MARKET-BONUS` + `GENERATE10` / `HOSTMN5` + **promo rotator cron** (installed 2026-06-20) |
| A7  | Premium generator tiers    | **Ops** — `MONETIZATION_TIER_ENFORCEMENT=1` on server                                   |
| A8  | Allowance + renewal emails | ✓ Cron installed 2026-06-20 — **Ops** — SMTP (`AGENT_CRON_SECRET` set) |


### Tier B — product bundles (2–5 days each)


| #   | Track                   | Idea                                                         |
| --- | ----------------------- | ------------------------------------------------------------ |
| B1  | MN2 starter bundle      | ✓ `bundle-mn2-starter` in monetization_config                |
| B2  | On-ramp + hosting       | ✓ Auto `HOSTMN5` on hosting PayPal checkout + shop wizard + on-ramp → shop deep link |
| B3  | Battle pass season      | ✓ Quests + XP hooks (shop, generator, hosting, casino bets) |
| B4  | Digital goods expansion | ✓ Compendium ch. IV, cinematic sound pack, creator avatar frame in catalog |
| B5  | Auction house fee       | ✓ 5% enforced (`shop_auction_service`) + `GET /api/shop/tier-b/auction-fee` |
| B6  | Casino MN2 buy-in packs | ✓ `casino_mn2_*` packs + casino UI + purchase API           |
| B7  | Copy-trading premium    | ✓ Monthly SKU — coins/PayPal + shop Deals card              |
| B8  | B2B studio SCR          | ✓ Agency outreach + self-serve deposit (`scr_checkout_service`) |


### Tier C — growth & retention


| #   | Track                             | Idea                                                                                       |
| --- | --------------------------------- | ------------------------------------------------------------------------------------------ |
| C1  | Referral credits                  | ✓ Coins when referee buys first pack or hosting slot (`referral_purchase_rewards_service`) |
| C2  | Post-purchase upsell modal        | ✓ After PayPal capture + hosting capture (`shop_upsell_service`, shop modal)               |
| C3  | Weekly revenue pulse              | ✓ Cron Mon 10:00 UTC — `monetization_revenue_pulse_service` + `revenue_pulse_cron.sh`      |
| C4  | SEO landing pages                 | ✓ `/hosting/` landing + meta on generator/camgirls + `sitemap.xml` / `robots.txt`          |
| C5  | Compendium paid chapters          | ✓ Free 1–3 · SKUs `compendium-chapters-4-12` / `compendium-premium-full` · Discord 3/10/25 |
| C6  | VIP Discord for hosting customers | ✓ M8 #51 auto-role on paid hosting + link sync (`discord_hosting_vip_service`) |
| C7  | Metered generator API             | ✓ Starter/Pro/Enterprise SKUs · quota on `/api/generator/create` · `GET /api/generator/api/*` |
| C8  | Phase C margin report             | ✓ Tue 10:00 UTC — `monetization_margin_report_service` + scr_blend email |


### Tier D — platform extensions (repo)


| #   | Track                     | Status |
| --- | ------------------------- | ------ |
| D1  | Player marketplace escrow | ✓ Bid coin escrow + release on outbid/cancel · `GET /api/shop/marketplace/escrow` |
| D2  | LiveKit camgirls voice    | ✓ `camgirls_livekit_service` · stub/live token · `POST /api/camgirls/livekit/token` |
| D3  | Mobile IAP                | ✓ Stub receipt fulfill · `GET /api/mobile/iap/catalog` · `POST /api/mobile/iap/fulfill` |


---

## M8 Discord — status


| Stream                  | Status                                                                           |
| ----------------------- | -------------------------------------------------------------------------------- |
| 51–60 core streams      | Live                                                                             |
| **Market fan-out**      | ✓ Cron installed 2026-06-20 (`mn2_next_ops`) |
| **Game fan-out**        | Installed on `mn2_staking` deploy                                                |
| **Promo rotator**       | ✓ `DISCORD-STARTER` / `HOSTMN5` / `MARKET-BONUS` / `GENERATE10` in daily rotator |
| **Partner spotlight**   | ✓ Platform news 2026-06-18 · **Ops:** re-run fan-out to `#market` (webhook URL fixed 2026-06-20) |


**Next:** compendium milestone webhooks — ✓ shipped; progress reader emits on 25/25.