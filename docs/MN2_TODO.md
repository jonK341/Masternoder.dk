# MN2 TODO

Last updated: **2026-06-23** (PR **#30** multi-ping site integration merged — ops.multi_ping_enabled **false** until v1.3 daemon deploy — PR **#29** --ask-pass on prod — fleet **~30** hosted — explorer **masternodes tab** live)

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
- **`mn2_next_ops_remote.py --ask-pass --optionals`** — 2026-06-20: masternode provision cron, Discord market + promo + monetization + revenue-pulse + margin-report crons; fleet verify **5/5 active** (`platform-mn-1`…`5`) — superseded 2026-06-22: **19+** on chain, cap **250**; backlog **cleared 2026-06-23** (**30** hosted)
- **`mn2_ops_optionals_remote.py --ask-pass --all`** — 2026-06-20: `AGENT_CRON_SECRET` + `COGS_ADMIN_REPORT_KEY` bootstrapped; crons reinstalled; smoke **3/3** (livekit stub, report 200, revenue pulse 200 `email_sent=false`)
- **Discord `#market` webhook** — `DISCORD_CHANNEL_ID_MARKET` set to full webhook URL on server (2026-06-20 audit); fixes prior **403** on spotlight fan-out
- **Camgirls catalog perf deploy** — `_tip_index` cache + `lite=1`; public `/api/camgirls/performers` ~**3.6s** live (2026-06-20)
- **v1.2.3.0 release binary** — server build OK; 3 assets on GitHub ([release tag](https://github.com/jonK341/MasterNoder2/releases/tag/v1.2.3.0)); tarball 5,665,662 bytes, sha256 `0fa3c4fa…`
- **Discord spotlight fan-out** — `camgirls_discord_spotlight.py --remote-only --ask-pass` re-posted to `#market` (2026-06-20)
- **Restore staking + trader market** — `mn2_next_ops_remote.py --ask-pass --restore-staking` (2026-06-20): wallet unlocked, staking=true, 2× market ticks, recent trades OK
- **Daemon upgrade v1.2.3.0** — `mn2_daemon_upgrade_remote.py --ask-pass --apply` + `--verify-post` (2026-06-20): systemd active, daemon v1.2.3.0-61caddb, mnsync synced, getnewaddress OK; post-verify **PASS**. Wallet locks on restart → background `--restore-staking` when convenient.
- **Masternode start: local-first (2026-06-14)** — purchases + cron + ops scripts use `startmasternode local false` before `alias` fallback; syncs `masternodeprivkey` + hairpin `masternodeaddr=127.0.0.1:17646` in `masternoder2.conf` on provision.
- **Fleet ops (2026-06-21/22)** — RPC on **9332** (`mn2_ensure_rpc_conf.sh`); `config/` **root:www-data 775** (`mn2_fix_config_permissions.sh`, `deploy.py` post-deploy chmod); alias provision hotfix; **19+ masternodes on chain**; `provision-pending` pipeline working.
- **Hosting capacity** — `max_hosted_nodes=250` in `data/mn2_masternode_config.json` (was 100 in UI defaults; conservative cap until daemon multi-ping).
- **Shop smoke (2026-06-22)** — `shop_v4_production_smoke.py --full-line` **10/10**; coins hosting purchase **PASS** for `shop_mn_purchase_test` (`mn_hosting_coins_purchase_test_live.py`).
- **Deploy 2026-06-22** — `deploy.py mn2_staking` + `static_pages` + `mn2_env` + `apply_updates.py --ask-pass`; fleet ops scripts live (RPC **9332**, config **775**, alias fix); `max_hosted_nodes=250`; `deploy.py` multi-manifest fix shipped.
- **Provisioning backlog cleared (2026-06-23)** — `GET /api/mn2/masternode/service`: **30** hosted · **28** active · **2** in-flight provisioning (with collateral) · **0** stale provisioning · **220** slots free; on-chain **6** / **5** ENABLED (`mn2_check_activetime_public.py`).
- **PR stack #21–#27 merged (2026-06-23)** — deploy tooling, fleet ops, explorer hub, hosting shop, docs, page-shell, podcast, monetization core, split leftovers (see [MN2_OPS.md § Waterfall](MN2_OPS.md#waterfall-merge-order-split-prs-1927)).
- **PR #29 deploy fixes (2026-06-23)** — `deploy.py` / `apply_updates.py` `--ask-pass` (stale `DEPLOY_PASS` retry), unified SSH, selective `static_pages` upload, `apply_updates` backend quick-check timeout tolerance.
- **`apply_updates.py --ask-pass` on prod (2026-06-23)** — user-confirmed; uwsgi + nginx reload without reboot.
- **PR #30 multi-ping site integration (2026-06-23)** — fleet helpers + probes + docs/patches/mn2-daemon-v1.3.0-multi-ping.patch; **ops.multi_ping_enabled: false** until v1.3 binary built/deployed ([MN2_DAEMON_MULTI_PING_UPGRADE.md](MN2_DAEMON_MULTI_PING_UPGRADE.md)).
- **Explorer masternodes tab deployed** — `mn2-crypto-hub.js` + `GET /api/mn2/masternodes?fresh=1`; `/explorer?tab=masternodes` slot meter, fleet grid, PayPal checkout.
- **Explorer static fixes deployed** — `static_pages` manifest (`mn2_explorer_data.py`, hub JS). Explorer VPS nginx (`fix_explorer_subdomains_remote.py` — eiquidus `getlasttxsajax` + `cam.masternoder.dk` redirect) — **DONE 2026-06-23** (`--ask-pass`; nginx reload + pm2 explorer restart OK).

---

## uWSGI — which unit to use (not `uwsgi.service`)

**Observed:** `systemctl stop` / `systemctl start` on legacy **`uwsgi.service`** may fail or appear to do nothing — **site stays up**. That is expected.

| Unit | Port | Role |
| ---- | ---- | ---- |
| **`uwsgi-vidgenerator.service`** | **5000** | Primary Flask app (nginx upstream) |
| **`uwsgi-vidgenerator-5001.service`** | **5001** | Second backend (load spread) |
| `uwsgi.service` | — | **Legacy Debian emperor / LSB — do not use** for this site |

**Restart app after code/env deploy:**

```bash
sudo systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
# or from PC: python scripts/deploy.py mn2_staking --ask-pass  (restarts both)
```

**Diagnose:** `cd /var/www/html && sudo bash scripts/uwsgi_diagnose_server.sh` · [UWSGI_EXIT1_TROUBLESHOOTING.md](UWSGI_EXIT1_TROUBLESHOOTING.md)

---

## Masternode — `startmasternode local` (ping / activetime)

**Why:** `startmasternode alias` only **broadcasts** to the network. **`activetime`** and **ENABLED** need the daemon **ping loop** → `startmasternode local false` with `masternode=1` + matching `masternodeprivkey` in `masternoder2.conf`. On this host, **hairpin NAT** requires `masternodeaddr=127.0.0.1:17646` (public IP stays in `masternode.conf`).

**Order on every start:** `local false` → `alias false <alias>` (fallback) → `missing false` (last resort).

### Where it is used (repo)

| Path | When |
| ---- | ---- |
| `backend/services/mn2_masternode_service.py` → `_start_masternode()` | **PayPal / shop purchase**, cron `provision-pending`, any `provision_host()` |
| `scripts/mn2_start_masternode.py` | **Manual / SSH ops** (wraps same logic) |
| `scripts/mn2_fleet_autostart.sh` | **Boot** after `masternoder2d` (local, then alias per alias) |
| `scripts/mn2_masternode_start_fleet_remote.py` | Remote fleet fix — calls `mn2_start_masternode.py --all-from-conf` |
| `scripts/mn2_masternode_reinstall_remote.py` | Reinstall platform slots — `_start_masternode()` per alias |

### How to use (server)

```bash
CLI="/opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config"
cd /var/www/html

# One alias (after purchase or conf edit):
python3 scripts/mn2_start_masternode.py --alias platformmn2

# All lines in masternode.conf:
python3 scripts/mn2_start_masternode.py --all-from-conf

# Low-level (same as script step 1):
$CLI startmasternode local false
$CLI startmasternode alias false platformmn2   # broadcast fallback only

# Verify:
$CLI listmasternodes | head -c 4000
$CLI getmasternodecount
```

**Config:** `data/mn2_masternode_config.json` → `ops.restart_daemon_on_provision: true`, `ops.masternode_ping_addr: "127.0.0.1:17646"`. Example daemon block: `config/masternoder2.conf.example`.

**Limit:** One daemon process pings **one** privkey (`masternodeprivkey=`). Fleet aliases 2–5 may stay **ACTIVE** (broadcast) while only the synced privkey goes **ENABLED** with `activetime > 0`.

---

## Next sprint (Phase next) — prioritized

Run top-down. **Owner:** `SSH` = server via `--ask-pass` · `Win` = Windows deploy scripts · `Code` = repo change + deploy.

| Pri | Task | Owner | Depends on | Command / note |
| --- | ---- | ----- | ---------- | -------------- |
| **P1** | **Daemon v1.3 build/deploy + enable multi-ping** — customer ENABLED + rising ctivetime | **MasterNoder2 C++** + SSH | **Site PR #30 merged** | Build v1.3.0.0 → mn2_daemon_upgrade_remote.py --ask-pass --apply → QA probes → set multi_ping_enabled: true + deploy.py mn2_staking --ask-pass|
| **P1** | ~~**Explorer VPS nginx verify**~~ | — | **DONE 2026-06-23** | `fix_explorer_subdomains_remote.py --ask-pass` — snippet + cam redirect + pm2 explorer restart |
| **P2** | **Live Pro subscription** — `PAYPAL_SUBSCRIPTION_PLAN_PRO` + `PAYPAL_WEBHOOK_ID` on server | **PayPal dashboard** + **Server `.env`** | PayPal live plan created | **Code shipped** — env maps `P-PLACEHOLDER-PRO` template; no JSON rename. `python scripts/mn2_p1_monetization_remote.py --ask-pass --paypal-plan-pro P-… --paypal-webhook-id WH-… --reload --verify` |
| **P2** | **Tier enforcement on server** — premium generator caps | **Server `.env`** | Pro plan live (recommended) | `python scripts/mn2_p1_monetization_remote.py --ask-pass --enable-tier-enforcement --reload --verify` |
| **P2** | **Fleet boot autostart** — `mn2-fleet-autostart.service` on reboot | SSH | local-first deployed | § **0. Masternode fleet** M5 — `cp scripts/mn2_fleet_autostart.sh …` · enable systemd unit |
| **P2** | **SMTP + admin email** — weekly revenue pulse + margin report emails | **Server `.env`** | none | `NOTIFY_ADMIN_EMAIL` + `NOTIFY_SMTP_*` via optionals flags or edit server `.env` |
| **P2** | **LiveKit voice (Camgirls Phase 3)** — server reports `mode=live` (optionals 2026-06-20); confirm camgirls token flow | SSH | LiveKit cloud creds | `mn2_ops_optionals_remote.py --ask-pass --livekit-url … --reload --verify` |
| **P2** | **Sync local `DEPLOY_PASS`** — non-interactive SSH still fails without matching password | Win | none | Update local `.env` to match server; test `python scripts/deploy_test_ssh.py` (`--ask-pass` works interactively) |
| **P2** | **Shop UI browser spot-check** (optional) — render + PayPal checkout in browser | **Browser** | deploy done | API **10/10** + coins purchase **PASS** — manual confirm slot meter / revenue strip / BEST VALUE badge if desired |
| **P2** | **Camgirls Phase 4 nginx** — only if moving UI to `camgirls.masternoder.dk/app/` | SSH | product decision | [CAMGIRLS_PHASE4_NGINX.md](CAMGIRLS_PHASE4_NGINX.md) |

**Completed this sprint (2026-06-21/23):** fleet RPC **9332** + config **775** perms + alias fix · **~30** hosted · shop **10/10** + coins purchase PASS · `max_hosted_nodes=250` · **deploy DONE** (PR **#29** `--ask-pass` + `apply_updates` on prod) · **provisioning backlog cleared** · **PR #30** site multi-ping merged — **PR stack #21–#27 merged** · **explorer masternodes tab live**.

**Watch (background — not blocking queue):** `/api/mn2/health` may still show **degraded** (`daemon_staking` inactive) after daemon restarts — re-run when convenient: `python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking`. Only **`platformmn2`** gets ENABLED `activetime` until multi-ping ships (see P1). **2** hosts may still show **provisioning** while collateral/start completes — not stale (`stale_provisioning_count=0`).

### `mn2_next_ops_remote.py` scope

One SSH session: install **masternode provision**, **Discord market fan-out**, **monetization retention**, **revenue pulse**, **margin report**, **promo rotator** crons; fix `masternode.conf` perms; verify `GET /api/mn2/masternode/service`; retry `provision-pending`. Flags: `--restore-staking` (wallet unlock + trader ticks), `--camgirls` (payouts + verify + spotlight API), `--optionals` (chain `mn2_ops_optionals_remote.py --all`), `--purge-stale-hosts`.

**2026-06-20:** base + `--optionals` + `--restore-staking` (earlier session) completed. **2026-06-22:** fleet **19+** on chain; **deploy DONE** (mn2_staking + static_pages + mn2_env). **2026-06-23:** provisioning backlog **cleared** — next: **multi-ping (P1)** · optional explorer nginx verify · PayPal Pro live plan · DEPLOY_PASS sync.

---

## Next — run in order

### 0. Masternode fleet (ops — backlog + boot autostart)

| # | Task | Owner | Status / action |
| - | ---- | ----- | --------------- |
| **M1** | **Deploy local-first + ops scripts** | Win | **Done (2026-06-22)** — `deploy.py mn2_staking` + `static_pages` + `mn2_env` + `apply_updates.py --ask-pass` |
| **M2** | **Confirm hairpin in `masternoder2.conf`** | SSH | **Done** — `masternode=1`, `masternodeprivkey=<platformmn2 key>`, `masternodeaddr=127.0.0.1:17646` · RPC **9332** · `config/` **775** |
| **M3** | **Start fleet (local first)** | SSH | **Done** — **19+** on chain; `mn2_start_masternode.py --all-from-conf` / fleet ops remote |
| **M4** | **Verify activetime** | SSH | **Partial** — `platformmn2` ENABLED + `activetime > 0`; customer aliases **ACTIVE** only until **multi-ping** (P1) |
| **M5** | **Boot autostart** | SSH | **Pending (P2)** — `cp scripts/mn2_fleet_autostart.sh /usr/local/bin/mn2-fleet-autostart && chmod +x …` · install `systemd/mn2-fleet-autostart.service.example` · `systemctl enable --now mn2-fleet-autostart` |
| **M6** | **Clear ~15 provisioning hosts** | SSH + cron | **Done (2026-06-23)** — **30** hosted · **28** active · **0** stale provisioning; **2** in-flight with collateral |
| **M7** | **Remote one-shot (optional)** | Win | `python scripts/mn2_masternode_fleet_ops_remote.py --ask-pass --watch` (install autostart + local start + poll ENABLED) |

**Do not use** legacy `uwsgi.service` for app reload — restart **`uwsgi-vidgenerator`** + **`uwsgi-vidgenerator-5001`** only (§ uWSGI above).

### 1. Active queue (top-down)

| # | Task | Owner | Action |
| - | ---- | ----- | ------ |
| 1 | **Fleet boot autostart (M5)** | **SSH** | Install `systemd/mn2-fleet-autostart.service` · `scripts/mn2_fleet_autostart.sh` · verify after reboot |
| 2 | **PayPal Pro live plan + webhook** | **PayPal dashboard** | § [**PayPal Pro setup (queue #2)**](#paypal-pro-setup-queue-2) below |
| 3 | **Deploy live Pro ids** | **Server `.env`** + repo | § [**After PayPal dashboard (queue #3)**](#after-paypal-dashboard-queue-3) |
| 4 | **Tier enforcement** | **Server `.env`** | `MONETIZATION_TIER_ENFORCEMENT=1` via `deploy.py mn2_env --ask-pass` |
| 5 | **Restore staking** *(parallel / background)* | SSH | `python scripts/mn2_next_ops_remote.py --ask-pass --restore-staking` — not blocking items 1–4 |

#### PayPal Pro setup (queue #2)

**Owner:** PayPal dashboard (Live). **Code is shipped** — webhook route, subscription create/bind, shop Pro block. Repo still has placeholder plan id `P-PLACEHOLDER-PRO` in `data/monetization_config.json`.

**Prerequisites:** Live REST app credentials already on server (`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE=live`). Use the **same app** for plan + webhook.

**Exact webhook URL (configure in PayPal dashboard):**

```text
https://masternoder.dk/api/monetization/webhooks/paypal-subscription
```

Route: `POST` only · `backend/routes/cogs_routes.py` → `monetization_paypal_subscription_webhook()`. Verification uses `PAYPAL_WEBHOOK_ID` (+ client id/secret). **Never** set `PAYPAL_WEBHOOK_BYPASS=1` in production.

**PayPal Developer Dashboard — step-by-step (Live):**

1. Open [developer.paypal.com](https://developer.paypal.com) → **Live** (not Sandbox) → **Apps & Credentials** → select the **masternoder** REST app (same as server `PAYPAL_CLIENT_ID`).
2. **Catalog → Products → Create product**
   - Type: **Service** or **Digital goods**
   - Name: e.g. `MasterNoder Pro`
   - Category: Software / Digital goods (any valid category)
3. **Subscriptions → Create plan** (attach to product above)
   - Plan name: `Pro monthly` (must match shop label intent)
   - Billing cycle: **Monthly**, **1** cycle, **infinite** renewals
   - Price: **USD 19.99** (must match `price_usd_monthly` in config)
   - Status: **Active**
   - **Copy Plan ID** → starts with `P-` (e.g. `P-5AB12345XY6789012MNOPQRSTU`)
4. **Webhooks → Add webhook** (same Live app)
   - URL: `https://masternoder.dk/api/monetization/webhooks/paypal-subscription`
   - Event types (minimum — code handles these in `monetization_subscription_service.py`):
     - `BILLING.SUBSCRIPTION.ACTIVATED`
     - `BILLING.SUBSCRIPTION.CANCELLED`
     - `PAYMENT.SALE.COMPLETED`
   - Save → **Copy Webhook ID** (not the URL; id looks like `WH-…` or alphanumeric per PayPal UI)
5. **Webhook test:** PayPal may send a verification ping on save; endpoint must return **200** (requires `PAYPAL_WEBHOOK_ID` already on server — if first-time setup, set webhook id on server first via queue #3 step 2, reload uwsgi, then re-save webhook in dashboard).

**What you paste from PayPal (keep private — do not commit):**

| From PayPal | Paste into |
| ----------- | ---------- |
| Plan ID `P-…` | Repo `data/monetization_config.json` — **rename JSON key** `P-PLACEHOLDER-PRO` → your `P-…` (see queue #3) |
| Webhook ID | Server `.env` → `PAYPAL_WEBHOOK_ID=` |

**Pro plan entitlements (already in repo — do not change unless product decision):**

| Field | Value |
| ----- | ----- |
| `label` | Pro monthly |
| `price_usd_monthly` | 19.99 |
| `monthly_generation_credits` | 8.0 |
| `tier` | pro |

**Optional (not blocking Pro):** second placeholder `P-PLACEHOLDER-MN-HOST` ($4.99/mo masternode hosting sub) — create a separate PayPal plan only if you want recurring hosting billing; shop hosting today uses one-time $4.99 checkout.

**Repo validation (no dedicated script):** `python -m pytest tests/unit/test_monetization_commits.py tests/unit/test_monetization_allowance.py tests/unit/test_paypal_subscription_webhook.py -q` — config loads; allowance tests assert `P-PLACEHOLDER-PRO` shape. After replacing plan id, update test fixtures if you rename the placeholder key.

**Verify after deploy (queue #3):** `GET https://masternoder.dk/api/monetization/config` → `subscriptions.plans` shows your `P-…` id · shop **PayPal & coins** tab → Pro subscribe button · test subscribe in Live (small real charge) → return URL `/shop?paypal_subscription=success&…` → bind → check `logs/monetization/subscription_bindings.json` on server.

---

#### After PayPal dashboard (queue #3)

1. **`data/monetization_config.json`** — under `subscriptions.plans`, **rename the key** (PayPal plan id is the JSON key):

   ```json
   "P-YOUR-LIVE-PLAN-ID": {
     "label": "Pro monthly",
     "price_usd_monthly": 19.99,
     "monthly_generation_credits": 8.0,
     "tier": "pro"
   }
   ```

   Delete or leave `P-PLACEHOLDER-PRO` only if unused; shop lists all keys under `subscriptions.plans`.

2. **Server `.env`** (via SSH or `python scripts/deploy.py mn2_env --ask-pass`):

   ```bash
   PAYPAL_WEBHOOK_ID=<webhook id from dashboard>
   PAYPAL_MODE=live
   # PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET already set
   ```

3. **Deploy config + restart app:**

   ```powershell
   python scripts/deploy.py mn2_staking --ask-pass
   ```

   Restarts `uwsgi-vidgenerator` + `uwsgi-vidgenerator-5001`. Hotfix JSON only: same command (includes `data/monetization_config.json` in manifest).

4. **Queue #4 (recommended after Pro live):** `MONETIZATION_TIER_ENFORCEMENT=1` via `deploy.py mn2_env --ask-pass` → reload → spot-check 402/403 over cap.

**Done 2026-06-18:** `deploy.py mn2_env --ask-pass` + `deploy.py camgirls --ask-pass` (onboard + payouts + social layer live).

**2026-06-20:** `mn2_next_ops_remote.py --ask-pass --optionals` (all crons + fleet verify) · `mn2_ops_optionals_remote.py --ask-pass --all` (secrets + smoke 3/3) · `--restore-staking` (wallet + market ticks) · camgirls perf deploy · Discord spotlight fan-out · v1.2.3.0 release build + GitHub assets · **daemon upgrade v1.2.3.0** (`--apply` + `--verify-post` PASS) · post-deploy **API** smoke PASS.

**2026-06-21/22:** fleet RPC **9332** + config **775** + alias provision fix · **19+** masternodes on chain · shop **10/10** + coins purchase PASS · `max_hosted_nodes=250`.

**2026-06-23:** provisioning backlog **cleared** — **30** hosted · **28** active · **0** stale provisioning.

**2026-06-22 deploy:** `mn2_staking` + `static_pages` + `mn2_env` + `apply_updates.py --ask-pass` — fleet ops + shop + explorer static live; explorer VPS nginx script optional verify.

**Optional — sync DEPLOY_PASS for non-interactive deploys:**

```powershell
# After updating .env with current root password:
python scripts/deploy_test_ssh.py
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

**Automated run 2026-06-22** (`shop_v4_production_smoke.py --full-line` + `mn_hosting_coins_purchase_test_live.py` + public API):

| Check | Result | Notes |
| ----- | ------ | ----- |
| Shop API line (`--full-line`) | **10/10** | All endpoints OK |
| Coins hosting purchase | **PASS** | User `shop_mn_purchase_test` — pay-coins checkout + provision path |
| Generator tiers | **PASS** | `GET /api/generator/api/tiers` → **3** tiers |
| Mobile IAP | **PASS** | `GET /api/mobile/iap/catalog` → **3** products |
| Marketplace escrow | **PASS** | `GET /api/shop/marketplace/escrow` → `success: true` |
| MN2 health | **WARN** | May show **degraded** (`daemon_staking` inactive) — background `--restore-staking` |
| Masternode service | **OK** | **30** hosted · **28** active · **0** stale provisioning (2026-06-23); on-chain **6** / **5** ENABLED; cap **250** slots |
| Camgirls verify | **4/4** | page + performers + agents + agent-tools OK (prior run) |

**Shop smoke — 2026-06-22** (API/automated **done** · optional browser spot-check P2):

| Check | URL | API / automated | Browser | Notes |
| ----- | --- | --------------- | ------- | ----- |
| Slot meter | [shop?tab=mn2](https://masternoder.dk/shop?tab=mn2) | **PASS** | optional | `GET /api/mn2/masternode/service` · cap **250** · `$4.99/slot` |
| Revenue strip | [shop](https://masternoder.dk/shop) | **PASS** | optional | `.shop-revenue-strip` in deployed HTML |
| Featured pack | [shop?tab=coins](https://masternoder.dk/shop?tab=coins) | **PASS** | optional | `coin-pack-m` **500 Coins** `featured: true` |
| Promo redeem | Shop promo box | **PASS** | optional | `POST /api/shop/promo/apply` — `--promo-check` in smoke |
| Multi-rail hosting | [shop?tab=mn2](https://masternoder.dk/shop?tab=mn2) | **PASS** | optional | Coins purchase **PASS** (`shop_mn_purchase_test`); PayPal/on-chain not re-run this pass |


### 3. v1.2.3.0 release binary — **published 2026-06-20**

**Build:** `mn2_build_release_remote.py --ask-pass --publish --draft` — smoke OK (daemon/cli v1.2.3.0-61caddb), tarball 5,665,662 bytes.

**GitHub:** [v1.2.3.0 release](https://github.com/jonK341/MasterNoder2/releases/tag/v1.2.3.0) — assets: `masternoder2d.tar.gz`, `.sha256`, `RELEASE_MANIFEST.json`. Tarball URL reachable.

**Verify locally:** `python scripts/mn2_release_status.py`

### 4. Daemon upgrade v1.2.3.0 — **done 2026-06-20**

Applied + post-verify PASS (systemd active, v1.2.3.0-61caddb, mnsync synced, getnewaddress OK). Wallet may lock on restart → background `--restore-staking` (not blocking active queue).

### 5. Manual ops checklist

- [x] **Revive / register 1 masternode** — `platform-mn-1` ENABLED 2026-06-17
- [x] **Deploy masternode hosting (multi-rail + shop/explorer UI)** — 2026-06-17
- [x] **Masternode post-deploy on deploy** — `deploy.py mn2_staking` runs provision cron + fleet seed + game cron
- [x] **Deploy `mn2_env` + `camgirls`** — `--ask-pass` 2026-06-18 (5/5 performers, verify 4/4 public, agents 6/6)
- [x] **Run `mn2_next_ops_remote.py --ask-pass`** — 2026-06-20 with `--optionals` (crons + fleet 5/5)
- [x] **Run `mn2_ops_optionals_remote.py --ask-pass --all`** — 2026-06-20: secrets OK, crons OK, smoke 3/3 (livekit stub, report 200, cron 200 `email_sent=false`)
- [x] **Restore staking + market** — `--restore-staking` 2026-06-20 earlier session (wallet unlocked, 2× ticks, trades OK)
- [x] **Masternode local-first + fleet ops** — RPC **9332**, config **775**, alias fix, **19+** on chain, provision working (2026-06-22)
- [x] **Hosting capacity 250** — `max_hosted_nodes=250` deployed (2026-06-22)
- [x] **Shop API smoke** — **10/10** + coins purchase **PASS** (`shop_mn_purchase_test`) (2026-06-22)
- [x] **Post-deploy API smoke** — shop 10/10 + camgirls 4/4 + Tier D APIs (§2)
- [x] **Deploy fleet + shop + explorer static** — `mn2_staking` + `static_pages` + `mn2_env` + `apply_updates.py --ask-pass` (2026-06-22/23)
- [x] **PR stack #21–#27 merged** — waterfall split landed on `main` (2026-06-23)
- [x] **PR #29 deploy fixes** — `--ask-pass`, selective `static_pages`, `apply_updates` SSH + timeout tolerance (2026-06-23)
- [x] **`apply_updates.py` on prod** — user-confirmed success (2026-06-23)
- [x] **Explorer masternodes tab** — `/explorer?tab=masternodes` hub JS + API live (2026-06-23)
- [x] **Clear ~15 provisioning hosts** — **cleared 2026-06-23** (**30** hosted · **0** stale provisioning)
- [x] **Explorer VPS nginx verify** — `fix_explorer_subdomains_remote.py --ask-pass` (2026-06-23; nginx test OK, pm2 explorer restarted)
- [x] **Profile hub (PR #31)** — tab bar, wallet fix, security layers, avatar · `static_pages` deploy (2026-06-23)
- [ ] **Fleet boot autostart (M5)** — systemd `mn2-fleet-autostart` not yet enabled
- [x] **Multi-ping site integration (PR #30)** — helpers + probes + C++ patch doc; flag **multi_ping_enabled: false** until v1.3 on prod
- [ ] **Daemon v1.3 deploy + enable multi-ping (customer ENABLED)** — P1 · [MN2_DAEMON_MULTI_PING_UPGRADE.md](MN2_DAEMON_MULTI_PING_UPGRADE.md)
- [ ] **Shop UI browser spot-check** — optional P2 (API/automated done)
- [x] **Deploy camgirls catalog perf fix** — live ~3.6s on `/api/camgirls/performers?lite=1` (2026-06-20)
- [x] **Re-run Discord spotlight fan-out** — `#market` webhook fixed; spotlight re-posted 2026-06-20
- [x] **v1.2.3.0 release assets** — GitHub tarball + manifest published 2026-06-20
- [x] **Daemon upgrade v1.2.3.0** — applied + `--verify-post` PASS 2026-06-20
- [ ] **Restore staking (background)** — health **degraded** 2026-06-20; `--ask-pass --restore-staking` when convenient (not blocking queue)
- [ ] **Sync `DEPLOY_PASS` in local `.env`** — `--ask-pass` works; non-interactive SSH still needs matching password
- [ ] **Live Pro subscription (P2)** — repo still has `P-PLACEHOLDER-PRO` / `P-PLACEHOLDER-MN-HOST`; PayPal dashboard plan + webhook per [MONETIZATION_PAYPAL.md §3](MONETIZATION_PAYPAL.md#3-subscriptions-recurring); then `PAYPAL_WEBHOOK_ID` on server `.env` + redeploy
- [ ] **Tier enforcement (P2)** — `MONETIZATION_TIER_ENFORCEMENT=1` on server ([MONETIZATION_PAYPAL.md §2](MONETIZATION_PAYPAL.md#2-premium-generation-tiers))
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
- [x] **Discord spotlight — webhook fan-out** — re-posted to `#market` 2026-06-20 (webhook URL fixed)
- [x] **Catalog perf deploy** — public `/api/camgirls/performers` ~3.6s with `lite=1` (2026-06-20)
- [ ] **Phase 3 — LiveKit voice** — optionals smoke shows `mode=live`; confirm camgirls token flow end-to-end (not P0 — no duplicate deploy/verify items)

---

## Monetization machine — revenue tracks

North star: [MONETIZATION_PAYPAL.md §0](MONETIZATION_PAYPAL.md#0-single-metric-north-star).

### Tier A — shipped in repo (deploy to activate)


| #   | Track                      | Status                                                                                  |
| --- | -------------------------- | --------------------------------------------------------------------------------------- |
| A1  | Pro subscription           | **Ops** — repo + server still use `P-PLACEHOLDER-PRO`; [MONETIZATION_PAYPAL.md §3](MONETIZATION_PAYPAL.md#3-subscriptions-recurring) (plan + webhook) + `PAYPAL_WEBHOOK_ID` on server |
| A2  | Coin pack hero             | ✓ `featured` on 500-coin pack + BEST VALUE badge                                        |
| A3  | Hosting funnel             | ✓ Shop revenue strip + Explorer staking CTAs                                            |
| A4  | Staking boosters           | ✓ Linked from shop strip; promote on monitor (copy done)                                |
| A5  | Camgirls monetization      | ✓ Deployed + catalog perf ~3.6s; spotlight fan-out 2026-06-20 |
| A6  | Discord promo codes        | ✓ `DISCORD-STARTER`, `MARKET-BONUS` + `GENERATE10` / `HOSTMN5` + **promo rotator cron** (installed 2026-06-20) |
| A7  | Premium generator tiers    | **Ops** — `MONETIZATION_TIER_ENFORCEMENT=1` on server ([MONETIZATION_PAYPAL.md §2](MONETIZATION_PAYPAL.md#2-premium-generation-tiers)) |
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
| **Partner spotlight**   | ✓ Platform news 2026-06-18 · ✓ `#market` fan-out re-posted 2026-06-20 |


**Next:** compendium milestone webhooks — ✓ shipped; progress reader emits on 25/25.
