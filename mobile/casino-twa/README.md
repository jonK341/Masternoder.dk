# MasterNoder Casino Social — Google Play App 2 (TWA)

Trusted Web Activity shell for **App 2** on Google Play. App 1 (game shop) remains separate — see `docs/MN2_TODO.md` § Google Play game shop app.

> **Also shipping iOS?** Use **`mobile/casino-app/`** (Capacitor) for Android + iPhone from one project. Keep this TWA folder for a lightweight Play-only build or a second Android track.

## Product

- **Package:** `dk.masternoder.casino`
- **Start URL:** `https://masternoder.dk/casino/?app=casino-twa&tab=lobby`
- **Positioning:** Social casino lounge — virtual coins first; MN2/USD on web with policy disclosure
- **Shared account:** Same `user_id` / friends / crews as web (`/api/social/*`, `/api/casino/social/*`)

## Repo assets

| Path | Purpose |
|------|---------|
| `casino/manifest.webmanifest` | PWA manifest + Play related_application |
| `static/.well-known/assetlinks.json` | Digital Asset Links (replace SHA256) |
| `static/.well-known/apple-app-site-association` | iOS Universal Links (Capacitor) |
| `static/js/casino-mobile.js` | Deep links, install banner, Capacitor hooks |
| `static/js/casino-twa-shell.js` | Mobile bottom nav when `?app=casino-twa` or Capacitor/PWA |
| `static/css/casino-twa-shell.css` | TWA layout |
| `static/css/casino-mobile.css` | Safe areas, touch targets |
| `mobile/casino-app/` | **Capacitor Android + iOS** (recommended dual-store) |
| `mobile/casino-twa/twa-manifest.json` | [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap) input |

## Build AAB (local)

```bash
npm i -g @bubblewrap/cli
cd mobile/casino-twa
# Edit twa-manifest.json — set signingKey path after keystore creation
bubblewrap init --manifest=https://masternoder.dk/casino/manifest.webmanifest
# Or merge twa-manifest.json fields into generated project
bubblewrap build
```

## Migration to Capacitor Android

1. Ship iOS from `mobile/casino-app/` first.
2. Use the same `dk.masternoder.casino` package id for Play (or retire TWA listing).
3. Reuse `assetlinks.json` fingerprints; Capacitor APK signing cert must match deployed fingerprints.
4. Change start URL query from `app=casino-twa` to `app=casino-capacitor` in store listing only if UX differs.

## Play Console checklist

1. Create app **MasterNoder Casino Social** · package `dk.masternoder.casino`
2. Upload `assetlinks.json` fingerprint from **Play App Signing** cert
3. Deploy `static/.well-known/assetlinks.json` to production (nginx serves `/.well-known/`)
4. Content rating — gambling/simulated gambling disclosure
5. **Virtual currency only** in Play build; link to web for MN2/USD
6. Internal testing track → production

See `mobile/casino-app/PLAY_STORE_LISTING.md` for full metadata checklist.

## Deploy web slice

```powershell
python scripts/deploy.py mn2_staking static_pages --ask-pass
```

Ensures: casino HTML/CSS/JS, manifest, assetlinks, AASA, mobile API.

## API surface (casino mobile)

- `GET /api/casino/mobile/config` — app version, store URLs, deep link patterns
- `GET /api/casino/social/hub` — friends, feed, crew board, challenges
- `GET /api/casino/social/feed`
- Platform social: `POST /api/social/friends/add`, `GET /api/social/crews`, etc.
