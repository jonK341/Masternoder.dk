# Casino deploy & ID setup (ops)

Copy-paste commands for **PR #43** / `feat/casino-mega-expansion`. Package id: `dk.masternoder.casino`.

**Never commit secrets.** Use placeholders below; set real values in local `.env` and on-server `/var/www/html/.env` only.

Related: `docs/MN2_OPS.md` (Discord cron patterns), `mobile/casino-app/README.md`, `mobile/casino-twa/README.md`.

---

## A. Pre-upload (local)

### Run tests

Focused casino slice (expand as needed before a big release):

```powershell
cd C:\Users\jonkh\UsecaseSampler\Masternoder.dk
python -m pytest tests/unit/test_casino_routes.py tests/unit/test_casino_discord_fanout.py tests/unit/test_casino_social_integration.py tests/unit/test_casino_crash.py -q
```

Broader gate:

```powershell
python -m pytest tests/ -q
```

### Inspect deploy manifest

```powershell
python scripts/deploy.py casino --list-files
```

(Current manifest: **49** paths — backend casino services/routes, `data/casino_*.json`, `casino/*`, static casino JS/CSS/icons, `cron/discord_casino_fanout.sh`. **Does not** include `static/.well-known/*`; ship via `well_known` manifest below.)

### SSH / auth (from `deploy_ssh_env.py`)

| Variable | Default / notes |
|----------|-----------------|
| `DEPLOY_HOST` | `masternoder.dk` |
| `DEPLOY_USER` | `root` |
| `DEPLOY_PASS` | Loaded from project `.env` if unset in shell |
| `DEPLOY_KEY_PATH` | Optional; tried before password |

Prompt for password (ignores `.env` `DEPLOY_PASS`):

```powershell
python scripts/deploy.py casino --ask-pass
```

---

## B. Upload to server

Remote tree: `/var/www/html/` (paths mirror repo).

### Full casino backend + web slice

```powershell
python scripts/deploy.py casino --ask-pass
```

With password in environment:

```powershell
$env:DEPLOY_PASS = '<ssh-password>'
python scripts/deploy.py casino
```

### What restarts

`casino` is in `RESTART_VIDGENERATOR_ONLY_FOR` — deploy restarts:

- `uwsgi-vidgenerator`
- `uwsgi-vidgenerator-5001`

(no default `python-proxy` restart for this manifest). Post-deploy script also probes `http://127.0.0.1:<port>/casino/` on the server.

### Upload only (no restart)

```powershell
python scripts/deploy.py casino --upload-only --ask-pass
```

### Well-known + icons (not in `casino` manifest)

**Recommended** — uploads to `static/.well-known/` and auto-syncs to nginx web root `/.well-known/`:

```powershell
python scripts/deploy.py well_known --upload-only --ask-pass
```

Same manifest with nginx reload (no uwsgi restart):

```powershell
python scripts/deploy.py well_known --ask-pass
```

Legacy `--files` (also triggers web-root sync):

```powershell
python scripts/deploy.py --files static/.well-known/assetlinks.json static/.well-known/apple-app-site-association --upload-only --ask-pass
```

Optional icons if missing in production:

```powershell
python scripts/deploy.py --files static/img/casino/icon-192.svg static/img/casino/icon-512.svg static/img/casino/icon-maskable.svg static/img/casino/og-share.svg casino/manifest.webmanifest --upload-only --ask-pass
```

**Nginx note:** Mobile API advertises `https://masternoder.dk/.well-known/assetlinks.json`. Repo source lives under `static/.well-known/`; deploy uploads to `/var/www/html/static/.well-known/` then copies to `/var/www/html/.well-known/` (nginx root). Flask fallback routes exist in `all_page_routes.py` but production nginx typically serves the root path directly.

Static-only HTML/CSS deploy (large; no uwsgi restart):

```powershell
python scripts/deploy.py static_pages --upload-only --ask-pass
```

---

## C. ID setup (step by step)

### C.1 Google Play / Android Digital Asset Links

**Placeholder in repo:** `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` in `static/.well-known/assetlinks.json`.

**Get SHA-256 (colon-separated, uppercase hex):**

1. **Play Console (recommended):** App → **Setup** → **App signing** → **App signing key certificate** → SHA-256.
2. **Upload key / local keystore:**

   ```bash
   keytool -list -v -keystore /path/to/release.keystore -alias <alias>
   ```

3. **Bubblewrap / TWA:** After `bubblewrap build`, use the certificate Play Console shows for the signing key you use in production (`mobile/casino-twa/`).

**Replace locally (recommended — validates 64 hex chars):**

```powershell
python scripts/casino_play_assetlinks_update.py "AA:BB:CC:..."
```

**Replace locally (PowerShell manual):**

```powershell
$sha = "AA:BB:CC:..."   # from Play Console
(Get-Content static\.well-known\assetlinks.json -Raw) `
  -replace 'REPLACE_WITH_PLAY_APP_SIGNING_SHA256', $sha |
  Set-Content static\.well-known\assetlinks.json -NoNewline
```

**Replace locally (bash):**

```bash
SHA="AA:BB:CC:..."
sed -i "s/REPLACE_WITH_PLAY_APP_SIGNING_SHA256/$SHA/" static/.well-known/assetlinks.json
```

**Re-deploy well-known:**

```powershell
python scripts/deploy.py well_known --upload-only --ask-pass
```

**Verify:** [Google Statement List Tester](https://developers.google.com/digital-asset-links/tools/generator) for `dk.masternoder.casino` + your domain.

---

### C.2 Apple Universal Links (AASA)

**Placeholder in repo:** `TEAMID` in `static/.well-known/apple-app-site-association` (bundle `dk.masternoder.casino`).

**Get Team ID:** [Apple Developer](https://developer.apple.com/account) → **Membership** → **Team ID** (10 characters).

**Replace (PowerShell):**

```powershell
$team = "ABCDE12345"
(Get-Content static\.well-known\apple-app-site-association -Raw) `
  -replace 'TEAMID', $team |
  Set-Content static\.well-known\apple-app-site-association -NoNewline
```

**Replace (bash):**

```bash
TEAM=ABCDE12345
sed -i "s/TEAMID/$TEAM/g" static/.well-known/apple-app-site-association
```

**Deploy:**

```powershell
python scripts/deploy.py well_known --upload-only --ask-pass
```

**Xcode / Capacitor:** Enable **Associated Domains** → `applinks:masternoder.dk` (and `webcredentials:masternoder.dk` if using password autofill). Rebuild iOS app after AASA is live.

Paths in file: `/casino`, `/casino/*`.

---

### C.3 Discord `#casino` webhook

**Full walkthrough (Discord UI clicks, testing, troubleshooting):** [DISCORD_WEBHOOK_SETUP.md](DISCORD_WEBHOOK_SETUP.md)

Config reference: `data/casino_config.json` → `discord_integration.webhook_env` = **`DISCORD_CHANNEL_ID_CASINO`**.

Despite the name, the value must be the **full Discord webhook URL**:

`https://discord.com/api/webhooks/<id>/<token>`

**Create webhook:** Discord server → channel **#casino** (or target channel) → **Edit channel** → **Integrations** → **Webhooks** → **New webhook** → copy URL.

**Set on server `.env` (SSH):**

```bash
cd /var/www/html
# Backup first
cp .env .env.bak.$(date +%Y%m%d)

# Append or update (use your real URL once)
grep -q '^DISCORD_CHANNEL_ID_CASINO=' .env && \
  sed -i 's|^DISCORD_CHANNEL_ID_CASINO=.*|DISCORD_CHANNEL_ID_CASINO=https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN|' .env || \
  echo 'DISCORD_CHANNEL_ID_CASINO=https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN' >> .env
```

**Or** edit `.env` locally and deploy env manifest:

```powershell
# After editing .env in repo root (deploy uploads to server)
python scripts/deploy.py mn2_env --ask-pass
```

**Ops secret for cron / fan-out API:** `DISCORD_OPS_SECRET` (required by `POST /api/discord/casino/fanout`). Also accepted on `/api/casino/discord/notify`: `MN2_OPS_SECRET`, `MN2_SCAN_SECRET`.

```bash
grep -q '^DISCORD_OPS_SECRET=' /var/www/html/.env || \
  echo 'DISCORD_OPS_SECRET=<generate-long-random-string>' >> /var/www/html/.env
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
```

**Cron** (`cron/discord_casino_fanout.sh` → `POST /api/discord/casino/fanout`):

```bash
chmod +x /var/www/html/cron/discord_casino_fanout.sh
# Example: every 5 minutes
crontab -l 2>/dev/null | grep -v discord_casino_fanout; echo '*/5 * * * * /var/www/html/cron/discord_casino_fanout.sh' | crontab -
```

Script reads `DISCORD_OPS_SECRET` or `MN2_OPS_SECRET` from the environment — export in crontab or extend the script to source `/var/www/html/.env` (see `docs/MN2_OPS.md` for `mn2_read_ops_secret.sh` pattern on other fan-out scripts).

---

### C.4 Facebook / Meta Pixel (optional)

Config: `data/casino_config.json` → `facebook.pixel_id_env` = **`META_PIXEL_ID`**.

```bash
grep -q '^META_PIXEL_ID=' /var/www/html/.env || \
  echo 'META_PIXEL_ID=YOUR_PIXEL_ID' >> /var/www/html/.env
systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001
```

Pixel id is exposed to clients via `GET /api/casino/social/links` metadata (`pixel_id_env` name only unless your front-end reads env at build time).

---

### C.5 Store URLs after App Store approval

**Play:** Already set in `data/casino_config.json` → `mobile.play_store_url`  
`https://play.google.com/store/apps/details?id=dk.masternoder.casino`

**Apple:** Replace placeholder `https://apps.apple.com/app/id0000000000` in:

1. `data/casino_config.json` — add under `mobile`:

   ```json
   "app_store_url": "https://apps.apple.com/app/id<NUMERIC_APP_ID>"
   ```

2. Redeploy config + routes:

   ```powershell
   python scripts/deploy.py --files data/casino_config.json backend/services/casino_social_service.py --ask-pass
   ```

`GET /api/casino/mobile/config` returns `app_store_url` (falls back to `id0000000000` until set). Update `casino/manifest.webmanifest` `related_applications` if you add an iOS store entry.

---

## D. Verification

### Public HTTPS

```bash
BASE=https://masternoder.dk
curl -sS -o /dev/null -w "casino HTML %{http_code}\n" "$BASE/casino/"
curl -sS "$BASE/casino/manifest.webmanifest" | head -c 400
curl -sS "$BASE/.well-known/assetlinks.json" | jq .
curl -sS "$BASE/.well-known/apple-app-site-association" | jq .
curl -sS "$BASE/api/casino/mobile/config" | jq .
curl -sS "$BASE/api/casino/social/links" | jq '.discord.webhook_env, .facebook.pixel_id_env'
```

If `/.well-known/*` 404s but `/static/.well-known/*` works, run `python scripts/deploy.py well_known --upload-only --ask-pass`.

### On-server (uwsgi)

```bash
curl -sS http://127.0.0.1:5000/api/casino/mobile/config | jq .
curl -sS http://127.0.0.1:5000/api/discord/status | jq .
```

### Discord fan-out dry-run

Requires `DISCORD_OPS_SECRET` in uwsgi environment:

```bash
SECRET=$(grep '^DISCORD_OPS_SECRET=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
curl -sS -X POST -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" \
  -d '{"dry_run":true}' http://127.0.0.1:5000/api/discord/casino/fanout | jq .
```

Expect `"posted"` counts for dry-run ids, no Discord spam. Live run: omit `dry_run` or set `false`.

### Manual cron smoke

```bash
DISCORD_OPS_SECRET=$(grep '^DISCORD_OPS_SECRET=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"') \
  /var/www/html/cron/discord_casino_fanout.sh
```

---

## Quick reference

| Item | Location / env |
|------|----------------|
| Android package | `dk.masternoder.casino` |
| assetlinks placeholder | `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` |
| AASA placeholder | `TEAMID` → `TEAMID.dk.masternoder.casino` |
| Discord webhook | `DISCORD_CHANNEL_ID_CASINO` = full webhook URL |
| Fan-out auth | `DISCORD_OPS_SECRET` (+ cron script) |
| Meta pixel | `META_PIXEL_ID` (optional) |
| Deploy manifest | `python scripts/deploy.py casino` |

Checklist helper: `bash scripts/casino_ops_setup.sh`
