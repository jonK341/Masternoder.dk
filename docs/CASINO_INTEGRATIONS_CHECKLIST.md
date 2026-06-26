# Casino integrations checklist (non-Discord)

Audit date: **2026-06-26** · Branch: `feat/casino-mega-expansion` · PR: [#43](https://github.com/jonK341/Masternoder.dk/pull/43)

Discord is **done** — this doc covers Facebook/Meta, other social, mobile stores, casino AI agents, deploy gaps, and production verification.

Related ops runbooks: [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) · [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md) · [CASINO_MARKETING.md](CASINO_MARKETING.md)

---

## Status table

| Integration | Status | Next action | Doc link |
|-------------|--------|-------------|----------|
| **Facebook OG tags** | **Done** — `casino/index.html` has `og:*` + Twitter card meta | Generate & deploy `banner-masternoder2-casino.png` (OG image 404 on prod; only SVG exists) | [CASINO_MARKETING.md](CASINO_MARKETING.md) |
| **Meta Pixel (`META_PIXEL_ID`)** | **Partial** — config exposes `pixel_id_env` via API; **no `fbq` script in UI** | Create pixel in Meta Events Manager → add to server `.env` → (optional) wire pixel snippet in `casino/index.html` | [CASINO_DEPLOY_OPS.md § C.4](CASINO_DEPLOY_OPS.md) |
| **Share big-win API** | **Done** — `POST /api/casino/share/big-win` returns Facebook/X/WhatsApp/Telegram URLs | Smoke-test from Social tab after a real win | [CASINO_MARKETING.md](CASINO_MARKETING.md) |
| **Facebook page link (Social tab)** | **Done** — `data/casino_config.json` → `facebook.page_url` + follow card | Confirm `https://facebook.com/MasterNoder` is the real page URL | [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) |
| **Facebook casino webhook bot** | **Not built** — no `facebook_*` routes; MN2_TODO E3 pending | Defer or implement webhook + `FACEBOOK_PAGE_ACCESS_TOKEN` | [MN2_TODO.md](MN2_TODO.md) |
| **Social follow links** | **Wired** — Discord, YouTube, Facebook, X, Instagram, TikTok, Telegram, GitHub, Google Play | **Verify each URL** is a live account (currently brand placeholders) | `data/casino_config.json` |
| **Social tab UI** | **Done** — follow grid, share bar, WhatsApp, X thread, referral, Discord opt-in | Deploy latest `casino.js` if UI lags API | `static/js/casino.js` |
| **Share network grid** | **Done** — from `data/social_networks.json` via `GET /api/casino/social/links` | Redeploy `data/social_networks.json` if WhatsApp/X-thread missing on prod | `data/social_networks.json` |
| **Marketing API** | **Code done; prod missing** — `GET /api/casino/marketing` → 404 on prod | Deploy casino manifest slice (includes route + `data/casino_marketing.json`) | [CASINO_MARKETING.md](CASINO_MARKETING.md) |
| **Google Play registration** | **Ops TODO** — one-time **$25** developer account | [Create Play Console account](https://play.google.com/console/signup) | [mobile/casino-app/PLAY_STORE_LISTING.md](../mobile/casino-app/PLAY_STORE_LISTING.md) |
| **Android TWA (Bubblewrap)** | **Code done** — `mobile/casino-twa/` | Build AAB, internal testing track | [mobile/casino-twa/README.md](../mobile/casino-twa/README.md) |
| **Android/iOS Capacitor** | **Code done** — `mobile/casino-app/` + `ios/` project | `npm run assets` → signed AAB / Xcode archive | [mobile/casino-app/README.md](../mobile/casino-app/README.md) |
| **Digital Asset Links** | **Placeholder on prod** — `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` | Copy Play App Signing SHA-256 → `static/.well-known/assetlinks.json` → `deploy.py well_known` | [CASINO_DEPLOY_OPS.md § C.1](CASINO_DEPLOY_OPS.md) |
| **Play Store listing copy** | **Draft done** — all graphics/checklist items unchecked | Screenshots + feature graphic + content rating questionnaire | [PLAY_STORE_LISTING.md](../mobile/casino-app/PLAY_STORE_LISTING.md) |
| **Apple AASA (Universal Links)** | **Placeholder on prod** — `TEAMID.dk.masternoder.casino` | Replace `TEAMID` with Apple Developer Team ID → deploy well-known | [CASINO_DEPLOY_OPS.md § C.2](CASINO_DEPLOY_OPS.md) |
| **App Store URL** | **Placeholder** — API returns `id0000000000` | After App Store approval, set `mobile.app_store_url` in `casino_config.json` | [APP_STORE_LISTING.md](../mobile/casino-app/APP_STORE_LISTING.md) |
| **Capacitor iOS project** | **Done** — Associated Domains `applinks:masternoder.dk` in entitlements | Set Xcode Team, archive, upload to App Store Connect | [mobile/casino-app/README.md](../mobile/casino-app/README.md) |
| **Casino AI agent docs** | **Done** | — | [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md) |
| **Casino AI agent routes** | **Code done; prod stub** — `GET /api/agent/casino/models` returns Register Intelligence auto-created placeholder | Deploy `agent_casino_routes` + seed JSON files | [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md) |
| **Agent seed data** | **Missing** — no `data/casino_agents.json` or `data/casino_agent_models.json` in repo | Add seed files + add to `deploy.py` casino manifest | [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md) |
| **`AGENT_CASINO_SECRET` + LLM keys** | **Server env TODO** | Generate secret, add `GROQ_API_KEY` / `DEEPSEEK_API_KEY` (min), `CASINO_AGENT_LLM=1` | [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md) |
| **PR #43 merge** | **OPEN, MERGEABLE** (2026-06-26) | Review → merge → deploy casino manifest to prod | [PR #43](https://github.com/jonK341/Masternoder.dk/pull/43) |

---

## Production curl results (2026-06-26)

| Check | Result |
|-------|--------|
| `GET /casino/` | **200** |
| `GET /api/casino/social/links` | **200** — follow links, share networks, `pixel_id_env: META_PIXEL_ID` |
| `GET /api/casino/mobile/config` | **200** — `app_store_url` = `id0000000000`, Play URL set |
| `GET /.well-known/assetlinks.json` | **200** — SHA placeholder `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` |
| `GET /.well-known/apple-app-site-association` | **200** — `TEAMID` placeholder |
| `POST /api/casino/share/big-win` | **200** — share URLs for Facebook, X, WhatsApp, Telegram |
| `GET /api/casino/marketing` | **404** — not deployed |
| `GET /static/img/casino/banner-masternoder2-casino.png` | **404** — OG meta points here; use SVG or generate PNG |
| `GET /api/agent/casino/models` | **Stub** — Register Intelligence auto-created (real route not on prod) |
| `GET /api/agents/intelligence/llm-status` | **Stub** — same |

---

## Prioritized “do next” (top 5)

1. **Merge PR #43 and deploy the full casino slice** — closes prod gaps (`/api/casino/marketing`, agent routes, latest social JS).  
2. **Google Play path** — $25 dev account → build AAB (Capacitor or TWA) → paste **real** App Signing SHA-256 into `assetlinks.json` → deploy `well_known` → internal testing.  
3. **Apple path** — Apple Developer account → replace `TEAMID` in AASA → deploy → Xcode archive with bundle `dk.masternoder.casino`.  
4. **Casino AI agents** — add `data/casino_agents.json` + `data/casino_agent_models.json`, set `AGENT_CASINO_SECRET` + at least one LLM key, `CASINO_AGENT_LLM=1`, dry-run `run-all`.  
5. **Social polish** — generate OG banner PNG, verify/update real social profile URLs, optionally set `META_PIXEL_ID` on server.

---

## Copy-paste commands

### 1. Deploy casino + well-known (after merge or from branch)

```powershell
cd C:\Users\jonkh\UsecaseSampler\Masternoder.dk
python -m pytest tests/unit/test_casino_routes.py tests/unit/test_casino_social_integration.py tests/unit/test_casino_agents.py -q
python scripts/deploy.py casino --ask-pass
python scripts/deploy.py well_known --ask-pass
```

### 2. Google Play — fix Digital Asset Links

```powershell
# After Play Console → App signing → copy SHA-256 (AA:BB:CC:... format)
$sha = "AA:BB:CC:DD:..."
(Get-Content static\.well-known\assetlinks.json -Raw) `
  -replace 'REPLACE_WITH_PLAY_APP_SIGNING_SHA256', $sha |
  Set-Content static\.well-known\assetlinks.json -NoNewline
python scripts/deploy.py well_known --upload-only --ask-pass
```

Verify: [Digital Asset Links tester](https://developers.google.com/digital-asset-links/tools/generator) for `dk.masternoder.casino` + `masternoder.dk`.

### 3. Apple — fix AASA Team ID

```powershell
$team = "ABCDE12345"   # Apple Developer → Membership → Team ID
(Get-Content static\.well-known\apple-app-site-association -Raw) `
  -replace 'TEAMID', $team |
  Set-Content static\.well-known\apple-app-site-association -NoNewline
python scripts/deploy.py well_known --upload-only --ask-pass
```

```bash
curl -sSI https://masternoder.dk/.well-known/apple-app-site-association | head -5
```

### 4. Meta Pixel (optional)

```bash
# On server SSH
grep -q '^META_PIXEL_ID=' /var/www/html/.env || \
  echo 'META_PIXEL_ID=YOUR_PIXEL_ID' >> /var/www/html/.env
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
```

Note: pixel ID is **not injected** in `casino/index.html` today — add Meta base snippet if you want client-side events.

### 5. Casino AI agents — server env + dry-run

```bash
# Generate secret locally
python -c "import secrets; print(secrets.token_urlsafe(32))"

# On server /var/www/html/.env
AGENT_CASINO_SECRET=<paste-secret>
CASINO_AGENT_LLM=1
GROQ_API_KEY=gsk_...
DEEPSEEK_API_KEY=sk-...
LLM_TIMEOUT_SECONDS=12

systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
```

```bash
curl -sS https://masternoder.dk/api/agent/casino/models | jq .
curl -sS -X POST https://masternoder.dk/api/agent/casino/run-all \
  -H "Content-Type: application/json" \
  -H "X-Agent-Casino-Key: YOUR_AGENT_CASINO_SECRET" \
  -d '{"dry_run": true}' | jq .
```

### 6. Share big-win smoke test

```powershell
Invoke-RestMethod -Uri "https://masternoder.dk/api/casino/share/big-win" -Method POST `
  -ContentType "application/json" `
  -Body '{"user_id":"demo","game":"crash","net":500,"currency":"coins","multiplier":12.5}'
```

### 7. Production verification bundle

```bash
BASE=https://masternoder.dk
curl -sS -o /dev/null -w "casino %{http_code}\n" "$BASE/casino/"
curl -sS "$BASE/api/casino/social/links" | jq '.facebook, .mobile, (.follow_links | length)'
curl -sS "$BASE/api/casino/mobile/config" | jq '.app_store_url, .play_store_url, .assetlinks_url'
curl -sS "$BASE/.well-known/assetlinks.json" | jq .
curl -sS "$BASE/.well-known/apple-app-site-association" | jq .
curl -sS "$BASE/api/casino/marketing" | jq .
curl -sS "$BASE/api/agent/casino/models" | jq .
```

### 8. Android Capacitor build (local)

```bash
cd mobile/casino-app
npm install
npm run assets
npx cap sync android
npm run open:android
# Android Studio → Generate Signed Bundle / APK
```

### 9. Android TWA build (lighter Play-only option)

```bash
cd mobile/casino-twa
# Follow mobile/casino-twa/README.md for bubblewrap init + build
```

### 10. PR #43

```powershell
gh pr view 43
gh pr checks 43
# After review:
gh pr merge 43 --squash
```

### 11. Update social URLs (when accounts are confirmed)

Edit `data/casino_config.json` → `social_links` and `facebook.page_url`, then:

```powershell
python scripts/deploy.py --files data/casino_config.json --ask-pass
```

### 12. App Store URL after approval

Add to `data/casino_config.json` under `mobile`:

```json
"app_store_url": "https://apps.apple.com/app/id<NUMERIC_ID>"
```

Redeploy config + update `casino/manifest.webmanifest` `related_applications` if adding iOS store entry.

---

## Quick reference

| Item | Value / location |
|------|------------------|
| Android package | `dk.masternoder.casino` |
| assetlinks placeholder | `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` |
| AASA placeholder | `TEAMID` → `TEAMID.dk.masternoder.casino` |
| App Store placeholder | `https://apps.apple.com/app/id0000000000` |
| Meta pixel env | `META_PIXEL_ID` (optional, UI not wired) |
| Agent auth | `AGENT_CASINO_SECRET` + header `X-Agent-Casino-Key` |
| Agent LLM toggle | `CASINO_AGENT_LLM=1` |
| Ops shell checklist | `bash scripts/casino_ops_setup.sh` |
