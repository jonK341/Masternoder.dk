# MN2 TODO

Last updated: **2026-06-17** (Tier A monetization shipped in repo · `mn2_next_ops_remote.py` for server crons)

See [MN2_RELEASE_BUILD.md](MN2_RELEASE_BUILD.md) · [MN2_TRADER_MARKET.md](MN2_TRADER_MARKET.md) · [MONETIZATION_PAYPAL.md](MONETIZATION_PAYPAL.md) · [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md) · [CAMGIRLS_PHASE1C.md](CAMGIRLS_PHASE1C.md)

---

## Done ✓

- Explorer · staking · trader pool/market · Game Hub · compendium calm reader (V1–V16)
- Camgirls Phase 1c + daemon payouts — **5 live AI models** (Nova, Luna, Sage, Ember, Iris)
- **Discord cross-roads (code)** — market fan-out, alert funnel types, affiliate rotator, FAQ, trader tick emit
- **Shop V.9 MN2 services** — masternode hosting catalog, live slot meter, Proof of Reserves SKU, digital downloads, unified purchase history
- **Masternode hosting checkout (multi-rail)** — PayPal **$4.99/slot**, coins, in-wallet MN2, on-chain MN2; shop + Explorer
- **`mn2_staking` deploy + trader market verify** — 2026-06-17
- **Tier A monetization (repo)** — shop revenue strip, featured coin pack, Discord promo codes (`DISCORD-STARTER`, `MARKET-BONUS`), checkout promos (`GENERATE10`, `HOSTMN5`), Explorer staking CTAs; cron files for market fan-out + monetization emails

---

## Next — run in order

### 1. One-shot server ops (requires `--ask-pass` — `.env` `DEPLOY_PASS` is stale)

```powershell
python scripts/mn2_next_ops_remote.py --ask-pass
python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking
python scripts/mn2_next_ops_remote.py --ask-pass --camgirls
```

Installs: masternode provision cron, **Discord market fan-out**, **monetization retention cron**, API verify, optional wallet unlock + trader ticks, optional camgirls provision.

Then deploy monetization UI + config:

```powershell
python scripts/deploy.py mn2_staking --ask-pass
```

### 2. Post-deploy smoke (hosting + shop)

| Check | Where | Pass criteria |
|-------|--------|----------------|
| Slot meter | `/shop?tab=mn2` | “Hosting slots: N available … $4.99/slot” |
| Revenue strip | `/shop` catalog tab | Host / coins / boosters / camgirls links visible |
| Featured pack | `/shop` → PayPal & coins | **500 Coins** has “BEST VALUE” badge |
| Promo redeem | Shop promo box | `DISCORD-STARTER` → +100 coins |
| Quote API | `POST /api/mn2/masternode/checkout/quote` | `coins_total`, `mn2_total`, `payment_rails` |
| Multi-rail hosting | Shop MN2 tab | PayPal / coins / MN2 / on-chain each provision |

### 3. v1.2.3.0 release binary (tag exists; GitHub release asset missing)

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
- [ ] **Run `mn2_next_ops_remote.py --ask-pass`** — market + monetization crons + verify (not run yet — SSH auth failed with stale `.env`)
- [ ] **Restore staking + market** — `--restore-staking` flag on same script
- [ ] Rotate `DEPLOY_PASS` in `.env` (fixes non-interactive deploy)
- [ ] **Live Pro subscription** — replace `P-PLACEHOLDER-PRO` in `monetization_config.json` + `PAYPAL_WEBHOOK_ID`
- [ ] Set `NOTIFY_SMTP_*` + `AGENT_CRON_SECRET` on server for monetization emails

---

## Camgirls

- [x] Phase 1c + daemon payouts — 5 performers
- [x] **Studio stack** — voice, music, dances, gifts, goals, wheel/dice, emoji, buzz bar
- [x] **Deploy** `camgirls` manifest — 2026-06-17
- [ ] **Server ops** — provision Sage/Ember/Iris payouts (needs `.env` RPC creds):
  ```bash
  cd /var/www/html
  bash scripts/camgirls_py.sh scripts/camgirls_provision_payout_addresses.py --check-rpc
  bash scripts/camgirls_py.sh scripts/camgirls_provision_payout_addresses.py
  ```
  Nova/Luna succeed from **cache**; new performers need `getnewaddress` + `MN2_RPC_USER`/`MN2_RPC_PASSWORD` in `.env`.
- [ ] Phase 3 — LiveKit voice spike (optional)

---

## Monetization machine — revenue tracks

North star: [MONETIZATION_PAYPAL.md §0](MONETIZATION_PAYPAL.md#0-single-metric-north-star).

### Tier A — shipped in repo (deploy to activate)

| # | Track | Status |
|---|--------|--------|
| A1 | Pro subscription | **Ops** — replace PayPal plan id |
| A2 | Coin pack hero | ✓ `featured` on 500-coin pack + BEST VALUE badge |
| A3 | Hosting funnel | ✓ Shop revenue strip + Explorer staking CTAs |
| A4 | Staking boosters | ✓ Linked from shop strip; promote on monitor (copy done) |
| A5 | Camgirls monetization | **Ops** — `--camgirls` server run |
| A6 | Discord promo codes | ✓ `DISCORD-STARTER`, `MARKET-BONUS` + `GENERATE10` / `HOSTMN5` |
| A7 | Premium generator tiers | **Ops** — `MONETIZATION_TIER_ENFORCEMENT=1` |
| A8 | Allowance + renewal emails | ✓ Cron file shipped — **Ops** — SMTP + `AGENT_CRON_SECRET` |

### Tier B — product bundles (2–5 days each)

| # | Track | Idea |
|---|--------|------|
| B1 | MN2 starter bundle | Coin pack + 7-day staking booster + badge |
| B2 | On-ramp + hosting | Sequenced checkout: buy MN2 → reserve slot |
| B3 | Battle pass season | Limited pass tied to generator + shop quests |
| B4 | Digital goods expansion | Compendium PDFs, sound packs, avatar frames |
| B5 | Auction house fee | 5–10% platform fee (copy mentions 5% — wire if not enforced) |
| B6 | Casino MN2 buy-in packs | Labeled packs for casino bankroll |
| B7 | Copy-trading premium | Monthly follow-top-trader SKU |
| B8 | B2B studio SCR | Agency outreach + self-serve deposit |

### Tier C — growth & retention

| # | Track | Idea |
|---|--------|------|
| C1 | Referral credits | Coins when referee buys first pack or hosting slot |
| C2 | Post-purchase upsell modal | After capture: booster / camgirl tip / hosting |
| C3 | Weekly revenue pulse | Cron email: `payment_ledger` + hosting + tips |
| C4 | SEO landing pages | `/hosting`, meta for generator + camgirls |
| C5 | Compendium paid chapters | Free 1–3; premium SKUs; Discord milestone webhooks |
| C6 | VIP Discord for hosting customers | M8 #51 auto-role |
| C7 | Metered generator API | Sell API key tiers |
| C8 | Phase C margin report | `monetization_scr_blend_service` weekly |

### Tier D — deferred

| # | Track |
|---|--------|
| D1 | Player marketplace escrow |
| D2 | LiveKit camgirls voice |
| D3 | Mobile IAP |

---

## M8 Discord — status

| Stream | Status |
|--------|--------|
| 51–60 core streams | Live |
| **Market fan-out** | Cron file shipped — run `mn2_next_ops_remote.py --ask-pass` |
| **Game fan-out** | Installed on `mn2_staking` deploy |
| **Promo rotator** | Add `DISCORD-STARTER` / `HOSTMN5` to Discord copy |

**Next:** compendium milestone → news · progress reader webhooks.
