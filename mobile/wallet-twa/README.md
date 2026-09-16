# MN2 Wallet — Google Play App (TWA)

Trusted Web Activity shell for the **MN2 Wallet v2** web app at `/wallets`.

> **Also shipping iOS?** Use **`mobile/wallet-app/`** (Capacitor) for Android + iPhone from one project. Keep this TWA folder for a lightweight Play-only build.

## Product

- **Package:** `dk.masternoder.wallet`
- **Start URL:** `[REDACTED]/wallets/?app=wallet-twa&tab=overview`
- **Positioning:** Custodial MN2 wallet — send, receive, trophies, monitors (same session as web)
- **Shared account:** Same `user_id` / balances as web `/wallets`

## Repo assets

| Path | Purpose |
|------|---------|
| `wallets/manifest.webmanifest` | PWA manifest + Play related_application |
| `static/img/wallet/icon-*.svg` | Launcher / maskable icons |
| `static/js/wallet-mobile.js` | Deep links, install banner, Capacitor hooks |
| `static/css/wallet-mobile.css` | Safe areas, touch targets |
| `mobile/wallet-app/` | **Capacitor Android + iOS** (recommended dual-store) |
| `mobile/wallet-twa/twa-manifest.json` | [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap) input |
| `docs/WALLET_DOWNLOAD.md` | Download table + release tag |

## Build APK / AAB (local)

```bash
npm i -g @bubblewrap/cli
cd mobile/wallet-twa
# Edit twa-manifest.json — set signingKey path after keystore creation
bubblewrap init --manifest=[REDACTED]/wallets/manifest.webmanifest
# Or merge twa-manifest.json fields into generated project
bubblewrap build
# Output: app-release-signed.apk (rename to MasterNoder-Wallet-android-v0.1.0-preview.apk)
```

## GitHub Release (CI stub)

Tag **`wallet-mobile-v0.1.0-preview`** triggers `.github/workflows/wallet-mobile-build.yml` (upload artifact or attach to Release when signing secrets are configured).

## Play Console checklist

1. Create app **MN2 Wallet** · package `dk.masternoder.wallet`
2. Upload `assetlinks.json` fingerprint from **Play App Signing** cert (add wallet package to `static/.well-known/assetlinks.json`)
3. Deploy `static/.well-known/assetlinks.json` to [REDACTED] (nginx serves `/.well-known/`)
4. Content rating — finance / simulated crypto disclosure
5. Internal testing track → sideload APK from GitHub Releases until Play listing is live

See `mobile/wallet-app/PLAY_STORE_LISTING.md` for full metadata checklist.

## Deploy web slice

```powershell
python scripts/deploy.py wallet_mobile static_pages --ask-pass
```

Ensures: wallet HTML, manifest, icons, mobile shell JS/CSS.

## Deep links

| Type | Example |
|------|---------|
| HTTPS tab | `[REDACTED]/wallets/?tab=send` |
| TWA query | `[REDACTED]/wallets/?app=wallet-twa&tab=receive` |
| Custom scheme (Capacitor) | `masternoder://wallet?tab=overview` |
