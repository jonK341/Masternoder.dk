# MN2 Wallet — Downloads

## Web wallet (available now)

- **Deployed:** `/wallets` on the live MasterNoder site
- **Local dev:** `/wallets` after `python run.py`

The web wallet is a Vite + Preact SPA built from `wallet-app/` into `static/wallet-v2/`.

## Desktop wallet (preview — build from source)

Desktop installers are planned for **v0.1.0-preview**. Until GitHub Release artifacts are published, build from source:

| Platform | Artifact (future release) | Status |
|----------|-------------------------|--------|
| Windows x64 | `MasterNoder-Wallet-x64.msi` | Stub — see `desktop/wallet-tauri/` |
| macOS | `MasterNoder-Wallet.dmg` | Stub |
| Linux | `MasterNoder-Wallet-x86_64.AppImage` | Stub |

**Future GitHub Release tag:** `wallet-v0.1.0-preview` under this repo’s Releases page (placeholder until CI publishes binaries).

### Build web wallet assets

```bash
cd wallet-app
npm install
npm run build
```

Output: `static/wallet-v2/` (served at `/static/wallet-v2/` and mounted by `/wallets`).

### Build desktop shell (Tauri 2 — when scaffold is complete)

See [`desktop/wallet-tauri/README.md`](../desktop/wallet-tauri/README.md).

## Daemon / Qt wallet (node operators)

For on-chain node operation (not the custodial app wallet), see [`docs/MN2_RELEASE_BUILD.md`](MN2_RELEASE_BUILD.md).
