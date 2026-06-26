# Casino integrations checklist (non-Discord)

Audit date: **2026-06-26** · Branch: `feat/casino-mega-expansion`

MasterNoder2 Casino is an **entertainment platform**: social lounge, virtual coins, tournaments, and community loops — built for engagement and sustainable monetization (MN2 packs, optional fiat where licensed), not unrealistic gambling claims.

Discord is **done** — this doc covers Facebook/Meta, other social, mobile stores, casino AI agents, deploy gaps, global sync, revenue reports, and production verification.

Related: [CASINO_EXPANSION_REPORT.md](CASINO_EXPANSION_REPORT.md) · [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md) · [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) · [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md) · [CASINO_IDEAS.md](CASINO_IDEAS.md)

---

## Status table

| Integration | Status | Next action | Doc link |
| ----------- | ------ | ----------- | -------- |
| **YouTube (social link)** | **Wired** — `social_links` → `https://youtube.com/@MasterNoder` | Verify channel is live | `data/casino_config.json` |
| **YouTube API / embed** | **Not built** | Optional: live stream embed on Social tab | — |
| **Main site casino** | **Done (prod)** — `GET /casino/` → 200 | Deploy mega-expansion slice | [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) |
| **Global hub sync** | **Code done** — `casino_global_controller`, hub config, UI network tab | Deploy + verify `GET /api/casino/global/leaderboard` | [CASINO_GLOBAL_SYNC.md](CASINO_GLOBAL_SYNC.md) |
| **Revenue daily reports** | **Code done** — `casino_revenue_report`, cron script | Deploy; schedule `cron/casino_daily_revenue_report.sh` | [CASINO_REVENUE_REPORTS.md](CASINO_REVENUE_REPORTS.md) |
| **Slot catalog** | **35 machines** (10 original + 25 themed expansion) | Deploy `data/casino_config.json` + `casino.css` | `GET /api/casino/slots` |
| **Facebook OG tags** | **Done** — `casino/index.html` has `og:*` + Twitter card meta | Generate & deploy `banner-masternoder2-casino.png` | [CASINO_MARKETING.md](CASINO_MARKETING.md) |
| **Meta Pixel (`META_PIXEL_ID`)** | **Wired** — API returns `pixel_id` when env set; `casino.js` loads `fbq` + `PageView` + `CasinoBigWin` events | Set `META_PIXEL_ID` on server `.env` if not already | [CASINO_DEPLOY_OPS.md § C.4](CASINO_DEPLOY_OPS.md) |
| **Share big-win API** | **Done** — `POST /api/casino/share/big-win` | Smoke-test from Social tab after a real win | [CASINO_MARKETING.md](CASINO_MARKETING.md) |
| **Facebook page link** | **Done** — `data/casino_config.json` → `facebook.page_url` | Confirm live page URL | [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) |
| **Facebook casino webhook bot** | **Not built** — MN2_TODO E3 pending | Defer or implement webhook | [MN2_TODO.md](MN2_TODO.md) |
| **Social follow links** | **Wired** — Discord, YouTube, Facebook, X, Instagram, TikTok, Telegram, GitHub, Google Play | Verify each URL is a live account | `data/casino_config.json` |
| **Social tab UI** | **Done** — follow grid, share bar, WhatsApp, X thread, referral, Discord opt-in | Deploy latest `casino.js` | `static/js/casino.js` |
| **Share network grid** | **Done** — from `data/social_networks.json` | Redeploy if networks missing on prod | `data/social_networks.json` |
| **Marketing API** | **Code done; prod missing** — `GET /api/casino/marketing` → 404 on prod | Deploy casino manifest slice | [CASINO_MARKETING.md](CASINO_MARKETING.md) |
| **Google Play registration** | **Tuesday** — $25 fee scheduled; account not yet active | Pay fee → upload AAB → get App Signing SHA | [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md) |
| **Android TWA (Bubblewrap)** | **Code done** — `mobile/casino-twa/` | Build AAB after Play account | [mobile/casino-twa/README.md](../mobile/casino-twa/README.md) |
| **Android/iOS Capacitor** | **Code done** — `mobile/casino-app/` + `ios/` | `npm run assets` → signed AAB / Xcode archive | [mobile/casino-app/README.md](../mobile/casino-app/README.md) |
| **Digital Asset Links** | **Fixed structure** — placeholder `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` (64 hex after Tuesday) | Tuesday: Play Console SHA → deploy `well_known` | [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md) |
| **Play Store listing copy** | **Draft done** | Screenshots + content rating after Play account | [PLAY_STORE_LISTING.md](../mobile/casino-app/PLAY_STORE_LISTING.md) |
| **Apple AASA (Universal Links)** | **PAUSED** — no Apple Developer account; `TEAMID` placeholder on prod | Resume when Apple Developer enrolled | [CASINO_DEPLOY_OPS.md § C.2](CASINO_DEPLOY_OPS.md) |
| **iOS without Apple account** | **Works** — PWA + custom scheme `masternoder://` | No action until Apple account | `mobile/casino-app/README.md` |
| **App Store URL** | **Placeholder** — `id0000000000` | After App Store approval, update `casino_config.json` | [APP_STORE_LISTING.md](../mobile/casino-app/APP_STORE_LISTING.md) |
| **Capacitor iOS project** | **Done** — Associated Domains in entitlements | Set Xcode Team when account exists | [mobile/casino-app/README.md](../mobile/casino-app/README.md) |
| **Casino AI agent docs** | **Done** | — | [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md) |
| **Casino AI agent routes** | **Code done; prod stub** | Deploy casino manifest + restart uWSGI | [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md) |
| **Agent seed data** | **Done** — `data/casino_agents.json`, `data/casino_agent_models.json` (Kelly, Safe Grinder, Meta Oracle) | Deploy with casino manifest | [CASINO_EXPANSION_REPORT.md](CASINO_EXPANSION_REPORT.md) |
| **`AGENT_CASINO_SECRET` + LLM keys** | **Server env** — user uploaded `.env` | Verify dry-run `run-all` after deploy | [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md) |
| **feat/casino-mega-expansion deploy** | **Ready to push** | Commit → push → deploy casino + well_known | [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) |

---

## Production curl results (2026-06-26)

| Check | Result |
| ----- | ------ |
| `GET /casino/` | **200** |
| `GET /api/casino/social/links` | **200** — follow links, share networks, `pixel_id` when `META_PIXEL_ID` set |
| `GET /api/casino/mobile/config` | **200** — `app_store_url` placeholder, Play URL set |
| `GET /.well-known/assetlinks.json` | **200** — placeholder until Tuesday Play SHA |
| `GET /.well-known/apple-app-site-association` | **200** — `TEAMID` placeholder (**paused**) |
| `POST /api/casino/share/big-win` | **200** |
| `GET /api/casino/marketing` | **404** — not deployed |
| `GET /api/casino/global/leaderboard` | **Stub** — deploy real route |
| `GET /api/casino/revenue/daily` | **Stub** — deploy real route |
| `GET /api/casino/slots` | **200** |
| `GET /api/agent/casino/models` | **Stub** — deploy agent routes + seed JSON |
| `GET /api/agents/intelligence/llm-status` | **Stub** — same |

---

## Prioritized “do next” (top 5)

1. **Tuesday Play SHA** — $25 fee → AAB upload → paste App Signing SHA → `python scripts/deploy.py well_known --ask-pass`.
2. **Deploy casino slice** — closes prod gaps (marketing, global, revenue, agent routes, Meta Pixel JS, seed agents).
3. **Merge PR #43** — critical infrastructure review (broadcast, fanout, revenue).
4. **Agent dry-run** — after deploy, `POST /api/agent/casino/run-all` with `{"dry_run": true}`.
5. **Social polish** — OG banner PNG, verify profile URLs.

---

## Copy-paste commands

### 1. Deploy casino + well-known

```powershell
cd C:\Users\jonkh\UsecaseSampler\Masternoder.dk
python -m pytest tests/unit/test_casino_routes.py tests/unit/test_casino_social_integration.py tests/unit/test_casino_agents.py -q
python scripts/deploy.py casino --ask-pass
python scripts/deploy.py well_known --ask-pass
```

### 2. Google Play — Tuesday SHA (see full guide)

[CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md)

```powershell
$sha = "AA:BB:CC:DD:..."
(Get-Content static\.well-known\assetlinks.json -Raw) `
  -replace 'REPLACE_WITH_PLAY_APP_SIGNING_SHA256', $sha |
  Set-Content static\.well-known\assetlinks.json -NoNewline
python scripts/deploy.py well_known --upload-only --ask-pass
```

**Local TWA only (pre-Play):** debug keystore SHA via `keytool -list -v -keystore %USERPROFILE%\.android\debug.keystore -alias androiddebugkey -storepass android`

### 3. Apple — PAUSED

Universal Links / AASA updates are **paused** until an Apple Developer account exists. PWA install and `masternoder://` deep links work without Apple enrollment. When ready:

```powershell
$team = "ABCDE12345"
(Get-Content static\.well-known\apple-app-site-association -Raw) -replace 'TEAMID', $team |
  Set-Content static\.well-known\apple-app-site-association -NoNewline
python scripts/deploy.py well_known --upload-only --ask-pass
```

### 4. Meta Pixel

Server `.env`:

```bash
grep -q '^META_PIXEL_ID=' /var/www/html/.env || echo 'META_PIXEL_ID=YOUR_PIXEL_ID' >> /var/www/html/.env
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
```

Client: `casino.js` reads `facebook.pixel_id` from `GET /api/casino/social/links` and initializes `fbq` automatically. No pixel ID is stored in the repo.

### 5. Casino AI agents — server env + dry-run

```bash
AGENT_CASINO_SECRET=<paste-secret>
CASINO_AGENT_LLM=1
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
LLM_TIMEOUT_SECONDS=12
```

```bash
curl -sS https://masternoder.dk/api/agent/casino/models | jq .
curl -sS -X POST https://masternoder.dk/api/agent/casino/run-all \
  -H "Content-Type: application/json" \
  -H "X-Agent-Casino-Key: YOUR_AGENT_CASINO_SECRET" \
  -d '{"dry_run": true}' | jq .
```

### 6. Production verification bundle

```bash
BASE=https://masternoder.dk
curl -sS -o /dev/null -w "casino %{http_code}\n" "$BASE/casino/"
curl -sS "$BASE/api/casino/social/links" | jq '.facebook.pixel_id, (.follow_links | length)'
curl -sS "$BASE/.well-known/assetlinks.json" | jq .
curl -sS "$BASE/api/casino/marketing" | jq .
curl -sS "$BASE/api/agent/casino/models" | jq .
```

### 7. PR #43

```powershell
gh pr view 43
gh pr checks 43
gh pr merge 43 --squash   # after review
```

---

## Quick reference

| Item | Value / location |
| ---- | ---------------- |
| Android package | `dk.masternoder.casino` |
| assetlinks placeholder | `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` (64 hex after Tuesday) |
| AASA | **PAUSED** — `TEAMID` placeholder |
| App Store placeholder | `https://apps.apple.com/app/id0000000000` |
| Meta pixel | `META_PIXEL_ID` in server `.env` → `fbq` in `casino.js` |
| Agent auth | `AGENT_CASINO_SECRET` + header `X-Agent-Casino-Key` |
| Agent seed bots | Kelly Optimizer, Safe Grinder, Meta Oracle |
| Ops shell checklist | `bash scripts/casino_ops_setup.sh` |
