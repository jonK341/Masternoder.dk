#!/usr/bin/env bash
# Build the MasterNoder2 Android wallet (WebView shell) APK.
#
# Usage:
#   export WALLET_URL="https://YOUR_SITE/wallets"
#   bash scripts/mn2_build_android_wallet.sh
#   ANDROID_HOME=~/Android/Sdk bash scripts/mn2_build_android_wallet.sh
#
# Output:
#   $BUILD_ROOT/dist/MasterNoder2-wallet-android.apk (+ .sha256 + ANDROID_RELEASE_MANIFEST.json)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${REPO_ROOT}/android/masternoder2-wallet"
BUILD_ROOT="${BUILD_ROOT:-/tmp/mn2-build}"
DIST="${ANDROID_OUT:-${BUILD_ROOT}/dist}"
# Default is loopback — set WALLET_URL for release packaging.
WALLET_URL="${WALLET_URL:-https://127.0.0.1/wallets}"
APK_NAME="MasterNoder2-wallet-android.apk"

if [[ ! -d "${APP_DIR}" ]]; then
  echo "ERROR: Android project missing: ${APP_DIR}" >&2
  exit 2
fi

if [[ -z "${ANDROID_HOME:-}${ANDROID_SDK_ROOT:-}" ]]; then
  for candidate in "${HOME}/Android/Sdk" /opt/android-sdk /usr/lib/android-sdk; do
    if [[ -d "${candidate}" ]]; then
      export ANDROID_HOME="${candidate}"
      break
    fi
  done
fi
export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [[ -z "${ANDROID_SDK_ROOT}" ]] || [[ ! -d "${ANDROID_SDK_ROOT}" ]]; then
  echo "ERROR: ANDROID_HOME / ANDROID_SDK_ROOT not set (Android SDK required)." >&2
  echo "  Install Android SDK cmdline-tools, then retry." >&2
  exit 2
fi

if ! command -v java >/dev/null; then
  echo "ERROR: java not found (need JDK 17+)" >&2
  exit 2
fi

mkdir -p "${DIST}"
printf 'sdk.dir=%s\n' "${ANDROID_SDK_ROOT}" > "${APP_DIR}/local.properties"

echo "=== Assemble Android release APK (wallet URL: ${WALLET_URL}) ==="
cd "${APP_DIR}"
if [[ -x ./gradlew ]]; then
  GRADLE=(./gradlew)
elif command -v gradle >/dev/null; then
  GRADLE=(gradle)
else
  echo "ERROR: gradlew/gradle not found. Generate wrapper with: gradle wrapper" >&2
  exit 2
fi

"${GRADLE[@]}" --no-daemon assembleRelease -Pmn2.walletUrl="${WALLET_URL}"

CANDIDATE="$(find app/build/outputs/apk -type f -name '*.apk' | sort | tail -1 || true)"
if [[ -z "${CANDIDATE}" ]]; then
  echo "ERROR: no APK produced under app/build/outputs/apk" >&2
  exit 2
fi
cp -a "${CANDIDATE}" "${DIST}/${APK_NAME}"
sha256sum "${DIST}/${APK_NAME}" | awk '{print $1}' > "${DIST}/${APK_NAME}.sha256"

python3 - "${DIST}" "${APK_NAME}" <<'PY'
import hashlib, json, os, sys
dist, name = sys.argv[1:3]
path = os.path.join(dist, name)
h = hashlib.sha256()
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
doc = {
    "version": os.environ.get("VERSION", "v1.3.0.0"),
    "wallet_url": os.environ.get("WALLET_URL", "https://127.0.0.1/wallets"),
    "files": {name: {"sha256": h.hexdigest(), "size": os.path.getsize(path)}},
}
with open(os.path.join(dist, "ANDROID_RELEASE_MANIFEST.json"), "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
print(f"Android APK: {path}")
PY

ls -lh "${DIST}/${APK_NAME}"
echo "=== Android wallet OK ==="
