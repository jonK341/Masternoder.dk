#!/usr/bin/env bash
# Package masternoder2d as a Flatpak bundle from a release tarball (no C++ rebuild).
#
# Usage:
#   bash scripts/mn2_build_flatpak.sh
#   TARBALL=/tmp/mn2-build/dist/masternoder2d.tar.gz bash scripts/mn2_build_flatpak.sh
#   FLATPAK_OUT=/tmp/mn2-build/dist bash scripts/mn2_build_flatpak.sh
#
# Requires: flatpak, flatpak-builder, tar. Installs freedesktop 24.08 runtime/sdk if missing.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FLATPAK_DIR="${REPO_ROOT}/packaging/flatpak"
BUILD_ROOT="${BUILD_ROOT:-/tmp/mn2-build}"
DIST="${FLATPAK_OUT:-${BUILD_ROOT}/dist}"
TARBALL="${TARBALL:-${DIST}/masternoder2d.tar.gz}"
WORK="${BUILD_ROOT}/flatpak-work"
APP_ID="dk.masternoder.MasterNoder2"
BUNDLE_NAME="${APP_ID}.flatpak"

if [[ ! -f "${TARBALL}" ]]; then
  echo "ERROR: daemon tarball not found: ${TARBALL}" >&2
  echo "  Build first: bash scripts/mn2_build_release.sh" >&2
  exit 2
fi
if ! command -v flatpak-builder >/dev/null || ! command -v flatpak >/dev/null; then
  if [[ "$(id -u)" -eq 0 ]] && command -v apt-get >/dev/null; then
    echo "=== Installing flatpak + flatpak-builder ==="
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq flatpak flatpak-builder ostree
  else
    echo "ERROR: flatpak and flatpak-builder required" >&2
    exit 2
  fi
fi

mkdir -p "${WORK}/staging" "${DIST}"
rm -rf "${WORK}/staging"/* "${WORK}/build" "${WORK}/repo"
mkdir -p "${WORK}/staging"

echo "=== Extract ${TARBALL} into Flatpak staging ==="
EXTRACT="${WORK}/extract"
rm -rf "${EXTRACT}"
mkdir -p "${EXTRACT}" "${WORK}/staging"
tar -xzf "${TARBALL}" -C "${EXTRACT}"
# Tarball layouts vary: binaries at top-level or under a folder (often masternoder2d/).
found="$(find "${EXTRACT}" -type f -name masternoder2d | head -1 || true)"
if [[ -z "${found}" ]]; then
  echo "ERROR: masternoder2d binary missing after extract" >&2
  find "${EXTRACT}" -maxdepth 3 -type f >&2 || true
  exit 2
fi
base="$(dirname "${found}")"
# Copy only the binaries we need into a flat staging dir (avoid dir/file name clash).
for bin in masternoder2d masternoder2-cli masternoder2-tx; do
  if [[ -f "${base}/${bin}" ]]; then
    install -m755 "${base}/${bin}" "${WORK}/staging/${bin}"
  fi
done
if [[ ! -x "${WORK}/staging/masternoder2d" ]]; then
  echo "ERROR: staged masternoder2d not executable" >&2
  ls -la "${WORK}/staging" >&2 || true
  exit 2
fi
cp -a "${FLATPAK_DIR}/dk.masternoder.MasterNoder2.desktop" "${WORK}/staging/"
cp -a "${FLATPAK_DIR}/dk.masternoder.MasterNoder2.metainfo.xml" "${WORK}/staging/"
# Manifest expects sources under staging relative to its own dir — copy yaml into work
cp -a "${FLATPAK_DIR}/dk.masternoder.MasterNoder2.yml" "${WORK}/"

echo "=== Ensure Flathub remotes + freedesktop runtime ==="
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo || true
flatpak install -y flathub org.freedesktop.Platform//24.08 org.freedesktop.Sdk//24.08 || true

echo "=== flatpak-builder ==="
(
  cd "${WORK}"
  flatpak-builder --force-clean --repo=repo build dk.masternoder.MasterNoder2.yml
  flatpak build-bundle repo "${DIST}/${BUNDLE_NAME}" "${APP_ID}"
)

sha256sum "${DIST}/${BUNDLE_NAME}" | awk '{print $1}' > "${DIST}/${BUNDLE_NAME}.sha256"
python3 - "${DIST}" "${BUNDLE_NAME}" <<'PY'
import hashlib, json, os, sys
dist, name = sys.argv[1:3]
path = os.path.join(dist, name)
h = hashlib.sha256()
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
doc = {
    "version": os.environ.get("VERSION", "v1.3.0.0"),
    "files": {
        name: {"sha256": h.hexdigest(), "size": os.path.getsize(path)},
    },
}
# Merge into RELEASE_MANIFEST extras if present
manifest_path = os.path.join(dist, "FLATPAK_RELEASE_MANIFEST.json")
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
print(f"Wrote {manifest_path}")
print(f"Flatpak bundle: {path}")
PY

echo "=== Flatpak OK ==="
ls -lh "${DIST}/${BUNDLE_NAME}" "${DIST}/${BUNDLE_NAME}.sha256"
