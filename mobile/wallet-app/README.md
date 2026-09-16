# MN2 Wallet — Capacitor (Android + iOS)

Cross-platform native shells that load the live MN2 Wallet v2 web app at `[REDACTED]/wallets/`.

| Path | Platform | Store |
|------|----------|-------|
| `mobile/wallet-app/` | **Android + iOS** (Capacitor) | Play + App Store / TestFlight |
| `mobile/wallet-twa/` | **Android only** (Bubblewrap TWA) | Play (lighter alternative) |

Both use package/bundle id **`dk.masternoder.wallet`**. Pick one Android store listing strategy — Capacitor is recommended when you also ship iOS.

## Prerequisites

- **Node.js 18+**
- **Android:** Android Studio, JDK 17, Android SDK
- **iOS (macOS only):** Xcode 15+, Apple Developer account
- Web assets deployed to [REDACTED] (`wallets/manifest.webmanifest`, wallet icons, mobile JS/CSS)

## Quick start

```bash
cd mobile/wallet-app
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

Release APK:

```bash
npm run build:android
# Output: android/app/build/outputs/apk/release/app-release-unsigned.apk
# Sign and align → MasterNoder-Wallet-android-v0.1.0-preview.apk
```

Release AAB (Play Store):

```bash
cd android && ./gradlew bundleRelease
# Output: android/app/build/outputs/bundle/release/app-release.aab
```

Configure signing in Android Studio (**Build → Generate Signed Bundle**) — **never commit keystores**.

### iOS build

```bash
npm run open:ios
```

In Xcode:

1. Set **Team** and **Bundle Identifier** `dk.masternoder.wallet`
2. **Signing & Capabilities** → enable **Associated Domains**: `applinks:[REDACTED]`
3. **Info** → URL Types → scheme `masternoder` (path `wallet`)
4. Archive → Distribute to TestFlight (placeholder until App Store listing)

## Configuration

`capacitor.config.ts` loads [REDACTED] wallet URL with `?app=wallet-capacitor&tab=overview`.

Local override (still hits [REDACTED] web — useful when testing shell only):

```bash
export WALLET_APP_LOCAL=1   # Linux/macOS
npm run cap:sync
```

## Deep links

| Type | Example |
|------|---------|
| HTTPS tab | `[REDACTED]/wallets/?tab=send` |
| Capacitor query | `[REDACTED]/wallets/?app=wallet-capacitor&tab=receive` |
| Custom scheme | `masternoder://wallet?tab=overview` |
| Universal Links (iOS) | `[REDACTED]/wallets/?tab=overview` |

Ops must deploy wallet package fingerprint in `static/.well-known/assetlinks.json` and `apple-app-site-association`.

## Web integration

| File | Role |
|------|------|
| `wallets/manifest.webmanifest` | PWA + store related apps |
| `static/js/wallet-mobile.js` | Install banner, deep links, Capacitor hooks |
| `static/css/wallet-mobile.css` | Safe areas, touch targets |

## Deploy web slice

```powershell
python scripts/deploy.py wallet_mobile static_pages --ask-pass
```

## Downloads

See [`docs/WALLET_DOWNLOAD.md`](../../docs/WALLET_DOWNLOAD.md) for the platform matrix and GitHub Release tag **`wallet-mobile-v0.1.0-preview`**.
