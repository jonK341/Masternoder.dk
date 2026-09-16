# MN2 Wallet — Downloads

Platform matrix for the **MN2 Wallet v2** web app (`wallet-app/` → `/wallets`).

| Platform | Download | Status |
|----------|----------|--------|
| **Web** | [/wallets](/wallets) | ✅ Available now |
| **Windows x64** | `MasterNoder-Wallet-x64.msi` | Stub — build from [`desktop/wallet-tauri/`](../desktop/wallet-tauri/README.md) |
| **macOS** | `MasterNoder-Wallet.dmg` | Stub — Tauri scaffold |
| **Linux x64** | `MasterNoder-Wallet-x86_64.AppImage` | Stub — Tauri scaffold |
| **Android** | [APK from GitHub Releases](#android) · [build from source](#build-android-apk) | Scaffold ready — CI on tag `wallet-mobile-v0.1.0-preview` |
| **iOS** | [TestFlight placeholder](#ios) · [PWA Add to Home Screen](#ios) | Capacitor scaffold — no store listing yet |

**Desktop release tag (future):** `wallet-v0.1.0-preview`  
**Mobile release tag (preview):** `wallet-mobile-v0.1.0-preview`

---

## Web wallet (available now)

- **Deployed:** `/wallets` on the live MasterNoder site
- **Local dev:** `/wallets` after `python run.py`

The web wallet is a Vite + Preact SPA built from `wallet-app/` into `static/wallet-v2/`.

Install as PWA: open `/wallets` in Chrome (Android) or Safari (iOS) → **Install app** / **Add to Home Screen**. Manifest: [`wallets/manifest.webmanifest`](../wallets/manifest.webmanifest).

---

## Android {#android}

### Download APK (when published)

After the first CI release on tag **`wallet-mobile-v0.1.0-preview`**, download **`MasterNoder-Wallet-android-v0.1.0-preview.apk`** from this repository’s GitHub **Releases** page (draft until first tag push).

Until that Release exists, build locally (below) or sideload a CI artifact from the workflow run.

### Build Android APK {#build-android-apk}

**Option A — Capacitor (recommended, Android + iOS):**

```bash
cd mobile/wallet-app
npm install
npx cap add android    # first time
npm run assets
npm run cap:sync
npm run build:android
# Sign output → MasterNoder-Wallet-android-v0.1.0-preview.apk
```

**Option B — TWA / Bubblewrap (Play-only, lighter APK):**

```bash
npm i -g @bubblewrap/cli
cd mobile/wallet-twa
bubblewrap init --manifest=https://[YOUR-DOMAIN]/wallets/manifest.webmanifest
bubblewrap build
```

See [`mobile/wallet-twa/README.md`](../mobile/wallet-twa/README.md) and [`mobile/wallet-app/README.md`](../mobile/wallet-app/README.md).

**Package ID:** `dk.masternoder.wallet`  
**Start URL:** `/wallets/?app=wallet-twa&tab=overview` (TWA) or `?app=wallet-capacitor` (Capacitor)

---

## iOS {#ios}

### TestFlight (placeholder)

Native shell: `mobile/wallet-app/` (Capacitor). Build on macOS with Xcode → Archive → TestFlight. Document the public TestFlight link here when the first build is uploaded.

See [`mobile/wallet-app/APP_STORE_LISTING.md`](../mobile/wallet-app/APP_STORE_LISTING.md).

### PWA — Add to Home Screen (available now)

1. Open **Safari** on iPhone/iPad → `/wallets`
2. Share → **Add to Home Screen**
3. Launches standalone with `wallets/manifest.webmanifest` (scope `/wallets/`)

No App Store review required; same web session as desktop browser.

---

## Desktop wallet (preview — build from source)

Desktop installers are planned for **`wallet-v0.1.0-preview`**. Until GitHub Release artifacts are published, build from source:

| Platform | Artifact | Docs |
|----------|----------|------|
| Windows x64 | `MasterNoder-Wallet-x64.msi` | [`desktop/wallet-tauri/`](../desktop/wallet-tauri/README.md) |
| macOS | `MasterNoder-Wallet.dmg` | Tauri stub |
| Linux | `MasterNoder-Wallet-x86_64.AppImage` | Tauri stub |

### Build web wallet assets

```bash
cd wallet-app
npm install
npm run build
```

Output: `static/wallet-v2/` (served at `/static/wallet-v2/` and mounted by `/wallets`).

### Build desktop shell (Tauri 2 — when scaffold is complete)

See [`desktop/wallet-tauri/README.md`](../desktop/wallet-tauri/README.md).

---

## Deploy mobile web assets

```powershell
python scripts/deploy.py wallet_mobile static_pages --ask-pass
```

Uploads: `wallets/index.html`, `wallets/manifest.webmanifest`, wallet icons, `wallet-mobile.js` / `.css`.

---

## Daemon / Qt wallet (node operators)

For on-chain node operation (not the custodial app wallet), see [`docs/MN2_RELEASE_BUILD.md`](MN2_RELEASE_BUILD.md).
