# MN2 Desktop Wallet (Tauri 2) — Stub

Thin native shell for Windows, macOS, and Linux loading the shared `wallet-app/` bundle.

## Status

**v0.1.0-preview** — scaffold only. Web wallet at `/wallets` is the primary surface until `tauri build` CI is wired.

## Planned release artifacts

| Platform | Filename |
|----------|----------|
| Windows x64 | `MasterNoder-Wallet-x64.msi` |
| macOS (Apple Silicon + Intel) | `MasterNoder-Wallet.dmg` |
| Linux x64 | `MasterNoder-Wallet-x86_64.AppImage` |

GitHub Releases path: `releases/tag/wallet-v0.1.0-preview`

## Build from source (future)

```bash
# 1. Build shared web UI
cd wallet-app
npm install
npm run build

# 2. Initialize Tauri project (when src-tauri/ is added)
cd ../desktop/wallet-tauri
# cargo install tauri-cli --version "^2"
# npm install
# npm run tauri build
```

## Configuration sketch

```
desktop/wallet-tauri/
  src-tauri/tauri.conf.json   # 1100×800, title "MN2 Wallet"
  src-tauri/src/main.rs       # wallet://tab/receive deep links, system tray
```

The WebView loads either the hosted `/wallets` page on the deployed site or bundled `static/wallet-v2/` for offline shell (send disabled offline).

## Auth

Session cookie bridge via Tauri secure store after browser/webview login. No local private-key custody in MVP — MN2 RPC stays server-side.
