# Google Play — Tuesday checklist ($25 developer account)

After the **$25 Google Play developer registration fee** is paid (scheduled **Tuesday**), follow these steps to fix Digital Asset Links and ship the Android TWA/Capacitor shell.

Related: [CASINO_INTEGRATIONS_CHECKLIST.md](CASINO_INTEGRATIONS_CHECKLIST.md) · [mobile/casino-app/PLAY_STORE_LISTING.md](../mobile/casino-app/PLAY_STORE_LISTING.md) · [CASINO_DEPLOY_OPS.md § C.1](CASINO_DEPLOY_OPS.md)

---

## Why assetlinks was broken

Production served a **truncated** SHA (`305253597`) instead of a full **64-character hex** SHA-256 fingerprint. Google Digital Asset Links require the complete App Signing certificate fingerprint for package `dk.masternoder.casino`.

The repo now uses placeholder `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` in `static/.well-known/assetlinks.json` until the real Play App Signing SHA is available.

---

## Step-by-step (after $25 payment)

### 1. Create developer account and app

1. Pay **$25** at [Google Play Console signup](https://play.google.com/console/signup) and complete developer account setup (can take a few hours after payment).
2. **Create the app** with package name **`dk.masternoder.casino`** (must match `assetlinks.json`, Capacitor, and TWA config).
3. Complete store listing basics (title, privacy policy URL, content rating questionnaire) as needed for internal testing.

### 2. Upload first AAB

Build and upload to **Internal testing** (either shell):

| Shell | Path |
|-------|------|
| Capacitor | `mobile/casino-app/` |
| TWA (Bubblewrap) | `mobile/casino-twa/` |

You do **not** need production release approval to see the App Signing certificate — uploading any AAB enables **App integrity → App signing**.

### 3. Copy SHA-256 from Play Console (production)

1. [Google Play Console](https://play.google.com/console) → **Your app**
2. **Release** → **Setup** → **App integrity** → **App signing**
3. Under **App signing key certificate**, copy **SHA-256 certificate fingerprint**
4. Format is either `AA:BB:CC:…` (with colons) or 64 hex chars without colons — both work with the update script.

**Important:** Use the **App signing key certificate** SHA, not the upload key, for production Digital Asset Links after Play App Signing is enabled.

### 4. Update `assetlinks.json` locally

Use the helper script (validates 64 hex chars; rejects placeholders and truncated values):

```powershell
cd C:\Users\jonkh\UsecaseSampler\Masternoder.dk
python scripts/casino_play_assetlinks_update.py "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB"
```

Validate only (no file write):

```powershell
python scripts/casino_play_assetlinks_update.py "YOUR_SHA_HERE" --check-only
```

The script writes `static/.well-known/assetlinks.json` and prints the deploy command.

### 5. Deploy well-known files

```powershell
python scripts/deploy.py well_known --ask-pass
```

### 6. Verify

[Google Digital Asset Links tester](https://developers.google.com/digital-asset-links/tools/generator):

- Site: `https://masternoder.dk`
- Package: `dk.masternoder.casino`
- Relation: `delegate_permission/common.handle_all_urls`

```bash
curl -sS https://masternoder.dk/.well-known/assetlinks.json | jq .
```

Run strict repo check after updating the SHA:

```powershell
$env:CASINO_ASSETLINKS_STRICT = "1"
python -m pytest tests/unit/test_casino_assetlinks.py -q
```

---

## If you paid today — when is the SHA available?

| Step | When |
|------|------|
| $25 payment processed | Usually immediate; account may show “pending” briefly |
| Create app + set package `dk.masternoder.casino` | Same session once account is active |
| Upload first AAB to Internal testing | Same day (local release build or debug upload for testing) |
| **App signing key SHA-256 visible** | **Immediately after first AAB upload** (Release → Setup → App integrity → App signing) |

You do **not** need to wait for Google review of the store listing to copy the App Signing fingerprint.

---

## Alternative: debug / upload keystore (local TWA only)

Until the app is on Play, use your **debug or upload keystore** SHA for **local Trusted Web Activity** testing on a dev/staging host. This is **not** valid for production Play-verified links.

### Debug keystore (Windows)

```powershell
keytool -list -v -keystore "$env:USERPROFILE\.android\debug.keystore" -alias androiddebugkey -storepass android -keypass android
```

Look for `SHA256:` under **Certificate fingerprints**.

### Capacitor Android — Gradle signing report

From `mobile/casino-app/android/`:

```powershell
cd mobile\casino-app\android
.\gradlew signingReport
```

Under **Variant: debug**, copy the **SHA-256** line. Use for local TWA/dev only — replace with Play App Signing SHA before public launch.

### Capacitor release keystore

```powershell
keytool -list -v -keystore path\to\release.keystore -alias your_alias
```

Use **upload key** SHA for pre-Play testing; after Play App Signing is enabled, always use **App signing key** SHA from the console.

---

## Deploy commands summary

| Step | Command |
|------|---------|
| Update assetlinks SHA | `python scripts/casino_play_assetlinks_update.py "<SHA-256>"` |
| Deploy casino slice (routes, agents, UI) | `python scripts/deploy.py casino --ask-pass` |
| Deploy assetlinks + AASA | `python scripts/deploy.py well_known --ask-pass` |
| Restart uWSGI (if env changed) | `python scripts/deploy_all_and_restart_uwsgi.py` or server `systemctl restart uwsgi-vidgenerator` |

---

## Do not commit fake SHAs

Do not put truncated values (e.g. `305253597`) or guessed fingerprints in the repo. The placeholder in git is intentional until you paste the real Play Console SHA locally, deploy, and optionally commit on a private branch.
