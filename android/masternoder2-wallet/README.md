# MasterNoder2 Android wallet

Thin WebView shell that opens the live site wallet portal (`/wallets`) so mobile users get on-chain deposit/balance flows without a native SPV stack.

## Build

```bash
# JDK 17+ and Android SDK required
export ANDROID_HOME=~/Android/Sdk
# Required for a usable APK — point at your public wallets URL:
export WALLET_URL="https://YOUR_SITE/wallets"
# once:
(cd android/masternoder2-wallet && gradle wrapper)
bash scripts/mn2_build_android_wallet.sh
```

APK lands in `/tmp/mn2-build/dist/MasterNoder2-wallet-android.apk` (override with `ANDROID_OUT` / `BUILD_ROOT`).

Without `WALLET_URL`, the build defaults to loopback (`https://127.0.0.1/wallets`) so the repository never embeds the public site hostname.
