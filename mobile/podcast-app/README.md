# MasterNoder Podcast — Capacitor (Android + iOS)

Cross-platform native shells that load the live podcast web app at your deployed `/podcast/` URL.

| Path | Platform | Store |
|------|----------|-------|
| `mobile/podcast-app/` | **Android + iOS** (Capacitor) | Play + App Store |
| `mobile/podcast-twa/` | **Android only** (Bubblewrap TWA) | Play (lighter alternative) |

Both use package/bundle id **`dk.masternoder.podcast`**. Pick one Android store listing strategy — Capacitor is recommended when you also ship iOS.

## Prerequisites

- **Node.js 18+**
- **Android:** Android Studio, JDK 17, Android SDK
- **iOS (macOS only):** Xcode 15+, Apple Developer account
- Web assets on server (PWA manifest, asset links, podcast JS/CSS)

## Quick start

```bash
cd mobile/podcast-app
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

1. Set **Team** and **Bundle Identifier** `dk.masternoder.podcast`
2. **Signing & Capabilities** → enable **Associated Domains**: `applinks:YOUR_HOST`
3. **Info** → URL Types → scheme `masternoder`
4. Archive → Distribute to App Store Connect

## Configuration

- `capacitor.config.ts` — remote URL and Capacitor server settings
- `PODCAST_APP_LOCAL=1` — optional local override during development
- Create App encoder integration: `/create-app/` wires Super Encoder podcast + video jobs

## Related

- Create App wizard: `/create-app/`
- Podcast TWA (Bubblewrap): `../podcast-twa/`
- Super Encoder service: `backend/services/super_encoder_service.py`
