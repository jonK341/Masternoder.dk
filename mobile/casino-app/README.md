# MasterNoder Casino — Capacitor (Android + iOS)

Cross-platform native shells that load the live casino web app at `https://masternoder.dk/casino/`.

| Path | Platform | Store |
|------|----------|-------|
| `mobile/casino-app/` | **Android + iOS** (Capacitor) | Play + App Store |
| `mobile/casino-twa/` | **Android only** (Bubblewrap TWA) | Play (lighter alternative) |

Both use package/bundle id **`dk.masternoder.casino`**. Pick one Android store listing strategy — Capacitor is recommended when you also ship iOS.

## Prerequisites

- **Node.js 18+**
- **Android:** Android Studio, JDK 17, Android SDK
- **iOS (macOS only):** Xcode 15+, Apple Developer account
- Web assets deployed to production (manifest, `.well-known`, casino JS/CSS)

## Quick start

```bash
cd mobile/casino-app
npm install
npx cap add android    # first time
npx cap add ios        # first time (macOS)
npm run assets         # generate PNG icons/splash from resources/*.svg
npm run cap:sync
```

### Android debug build

```bash
npm run open:android
# Android Studio → Run on device/emulator
```

Release AAB:

```bash
npm run build:android
# Output: android/app/build/outputs/bundle/release/app-release.aab
```

Configure signing in Android Studio (**Build → Generate Signed Bundle**) — **never commit keystores**.

### iOS build

```bash
npm run open:ios
```

In Xcode:

1. Set **Team** and **Bundle Identifier** `dk.masternoder.casino`
2. **Signing & Capabilities** → enable **Associated Domains**: `applinks:masternoder.dk`
3. **Info** → URL Types → scheme `masternoder`
4. Archive → Distribute to App Store Connect

## Configuration

`capacitor.config.ts` loads production casino URL with `?app=casino-capacitor&tab=lobby`.

Local override (still hits production web — useful when testing shell only):

```bash
set CASINO_APP_LOCAL=1   # Windows
npm run cap:sync
```

Runtime metadata: `GET /api/casino/mobile/config`

## Deep links

| Type | Example |
|------|---------|
| HTTPS query | `https://masternoder.dk/casino/?game=crash` |
| HTTPS tab | `https://masternoder.dk/casino/?tab=social` |
| Custom scheme | `masternoder://casino?game=crash` |
| Universal Links (iOS) | `https://masternoder.dk/casino/?game=plinko` |

Ops must deploy:

- `static/.well-known/assetlinks.json` — replace SHA256 fingerprints (Play App Signing)
- `static/.well-known/apple-app-site-association` — replace `TEAMID` with Apple Team ID

## Plugins

- `@capacitor/app` — `appUrlOpen` for custom URL scheme
- `@capacitor/haptics` — light tap on tab switch (web stub in `casino-mobile.js`)
- `@capacitor/splash-screen`, `@capacitor/status-bar`

## Web integration

| File | Role |
|------|------|
| `casino/manifest.webmanifest` | PWA + store related apps |
| `static/js/casino-mobile.js` | Install banner, deep links, Capacitor hooks |
| `static/js/casino-twa-shell.js` | Bottom nav for app shells |
| `static/css/casino-mobile.css` | Safe areas, touch targets |
| `static/css/casino-twa-shell.css` | TWA/Capacitor chrome |

## Deploy web slice

```powershell
python scripts/deploy.py mn2_staking static_pages --ask-pass
```

Ensure `casino/manifest.webmanifest`, `static/.well-known/*`, and `static/img/casino/*` are on the server. Add `static/img` to deploy manifest if icons are missing in production.

## TWA vs Capacitor (Android)

- **TWA** (`mobile/casino-twa/`): smallest APK, Chrome-powered, Play-only. Keep for a second listing or legacy track.
- **Capacitor**: same codebase as iOS, native plugins, standard WebView. Use when shipping both stores.

See `PLAY_STORE_LISTING.md` and `APP_STORE_LISTING.md` for store metadata checklists.
