#!/usr/bin/env bash
# Build MasterNoder2 release tarball for Linux x86_64 (pinned to VERSION tag or patch).
#
# Run on Linux or WSL (not Windows native). Needs ~2 GB RAM.
#
# Usage:
#   bash scripts/mn2_build_release.sh
#   VERSION=v1.3.0.0 PATCH_FILE=/tmp/mn2.patch bash scripts/mn2_build_release.sh
#   BUILD_ROOT=/data/mn2-build JOBS=4 bash scripts/mn2_build_release.sh
#   USE_DEPENDS=0 bash scripts/mn2_build_release.sh          # faster, less portable
#   INSTALL_BUILD_DEPS=1 bash scripts/mn2_build_release.sh   # apt install on Debian/Ubuntu

set -euo pipefail

VERSION="${VERSION:-v1.3.0.0}"
BASE_TAG="${BASE_TAG:-v1.2.3.0}"
CHECKOUT_BRANCH="${CHECKOUT_BRANCH:-}"
PATCH_FILE="${PATCH_FILE:-}"
REPO_URL="${REPO_URL:-https://github.com/jonK341/MasterNoder2.git}"
BUILD_ROOT="${BUILD_ROOT:-/tmp/mn2-build}"
SRC_DIR="${BUILD_ROOT}/MasterNoder2"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 2)}"
USE_DEPENDS="${USE_DEPENDS:-1}"
INSTALL_BUILD_DEPS="${INSTALL_BUILD_DEPS:-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PATCHED=0

APT_BUILD_PACKAGES=(
  git build-essential g++ autoconf automake libtool pkg-config patch bzip2 ca-certificates
  libboost-all-dev libssl-dev libevent-dev libzmq3-dev
  libdb-dev libminiupnpc-dev libgmp-dev libbsd-dev
)

require_build_tools() {
  local missing=()
  for cmd in autoconf automake libtoolize g++ make; do
    command -v "${cmd}" >/dev/null || missing+=("${cmd}")
  done
  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "Missing build tools: ${missing[*]}" >&2
    echo "Set INSTALL_BUILD_DEPS=1 (remote default) or install: ${APT_BUILD_PACKAGES[*]}" >&2
    exit 1
  fi
}

ensure_build_deps() {
  if [[ "${INSTALL_BUILD_DEPS}" == "1" ]] && [[ "$(id -u)" -eq 0 ]] && command -v apt-get >/dev/null; then
    echo "=== Installing MN2 build dependencies (apt) ==="
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq "${APT_BUILD_PACKAGES[@]}"
    return 0
  fi
  require_build_tools
  if [[ "${USE_DEPENDS}" != "1" ]]; then
    for cmd in pkg-config; do
      command -v "${cmd}" >/dev/null || {
        echo "System-lib build needs ${cmd}. Set INSTALL_BUILD_DEPS=1 or install libboost-all-dev libssl-dev libgmp-dev libbsd-dev." >&2
        exit 1
      }
    done
  fi
}

is_boost_depends_failure() {
  local log="${1:-}"
  [[ -n "${log}" ]] || return 1
  grep -qiE 'Failed to build Boost\.Build engine|boost.*stamp_configured|funcs\.mk:.*boost' <<< "${log}"
}

run_depends_build() {
  local log="${BUILD_ROOT}/depends-build.log"
  echo "=== depends (static, NO_QT) — first run can take 30–60 min ==="
  cd depends
  set +e
  make -j"${JOBS}" HOST=x86_64-linux-gnu NO_QT=1 2>&1 | tee "${log}"
  local dep_status=${PIPESTATUS[0]}
  set -e
  cd ..
  if [[ "${dep_status}" -ne 0 ]]; then
    if is_boost_depends_failure "$(cat "${log}")"; then
      echo "" >&2
      echo "=== depends boost build failed (Boost.Build engine / gcc toolset) ===" >&2
      echo "Common on minimal VPS hosts even when autoconf is present." >&2
      echo "Retry with system libraries (faster, less portable):" >&2
      echo "  USE_DEPENDS=0 bash scripts/mn2_build_release.sh" >&2
      echo "  python scripts/mn2_build_release_remote.py --ask-pass --fast --publish --draft" >&2
    fi
    return "${dep_status}"
  fi
}

sha256_file() {
  if command -v sha256sum >/dev/null; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

checkout_source() {
  cd "${SRC_DIR}"
  git fetch --tags origin

  if git rev-parse "refs/tags/${VERSION}" >/dev/null 2>&1; then
    echo "Checkout tag ${VERSION}"
    git checkout -f "${VERSION}"
    return 0
  fi

  if [[ -n "${CHECKOUT_BRANCH}" ]]; then
    if git rev-parse "refs/remotes/origin/${CHECKOUT_BRANCH}" >/dev/null 2>&1; then
      echo "Checkout branch origin/${CHECKOUT_BRANCH}"
      git checkout -f "origin/${CHECKOUT_BRANCH}"
      return 0
    fi
    echo "Branch origin/${CHECKOUT_BRANCH} not found; trying patch path..." >&2
  fi

  if [[ -z "${PATCH_FILE}" ]]; then
    # Default patch from site repo when building v1.3 without upstream tag
    local default_patch="${REPO_ROOT}/${PATCH_FILE:-docs/patches/mn2-daemon-v1.3.0-multi-ping.patch}"
    if [[ -f "${default_patch}" ]]; then
      PATCH_FILE="${default_patch}"
    fi
  fi

  if [[ -z "${PATCH_FILE}" ]] || [[ ! -f "${PATCH_FILE}" ]]; then
    echo "Tag ${VERSION} not found and PATCH_FILE missing." >&2
    echo "  Push branch to MasterNoder2 or set PATCH_FILE=/path/to/mn2-daemon-v1.3.0-multi-ping.patch" >&2
    exit 1
  fi

  if ! git rev-parse "refs/tags/${BASE_TAG}" >/dev/null 2>&1; then
    echo "Base tag ${BASE_TAG} not found" >&2
    exit 1
  fi

  echo "=== Checkout ${BASE_TAG} + apply patch ==="
  git checkout -f "${BASE_TAG}"
  git clean -fdx
  patch -p1 --forward < "${PATCH_FILE}"
  PATCHED=1
}

ensure_build_deps

echo "=== MN2 release build ${VERSION} ==="
echo "BUILD_ROOT=${BUILD_ROOT}  JOBS=${JOBS}  USE_DEPENDS=${USE_DEPENDS}"
echo "BASE_TAG=${BASE_TAG}  PATCH_FILE=${PATCH_FILE:-none}  CHECKOUT_BRANCH=${CHECKOUT_BRANCH:-none}"

mkdir -p "${BUILD_ROOT}"
if [[ -d "${SRC_DIR}/.git" ]]; then
  echo "Updating existing clone..."
  git -C "${SRC_DIR}" fetch --tags origin
else
  echo "Cloning ${REPO_URL}..."
  git clone "${REPO_URL}" "${SRC_DIR}"
fi

checkout_source
GIT_SHA=$(git rev-parse HEAD)
GIT_SUBJECT=$(git log -1 --format=%s)
echo "Source: ${GIT_SHA:0:12} — ${GIT_SUBJECT}"
if [[ "${PATCHED}" == "1" ]]; then
  echo "Patch applied on ${BASE_TAG} → build as ${VERSION}"
fi

if [[ "${USE_DEPENDS}" == "1" ]]; then
  run_depends_build
  HOST_DIR="${SRC_DIR}/depends/x86_64-linux-gnu"
  ./autogen.sh
  CONFIGURE_FLAGS=(
    --prefix="${HOST_DIR}"
    --without-gui
    --disable-tests
    --disable-bench
    --enable-reduce-exports
  )
else
  echo "=== system libs (faster; binary may not be portable) ==="
  ./autogen.sh
  CONFIGURE_FLAGS=(--without-gui --disable-tests --disable-bench --with-unsupported-ssl)
fi

./configure "${CONFIGURE_FLAGS[@]}"
make -j"${JOBS}" src/masternoder2d src/masternoder2-cli src/masternoder2-tx

strip -s src/masternoder2d src/masternoder2-cli src/masternoder2-tx 2>/dev/null || \
  strip -s src/masternoder2d src/masternoder2-cli || true

echo "=== Post-build smoke test ==="
SMOKE_DIR="${BUILD_ROOT}/smoke-bin"
rm -rf "${SMOKE_DIR}"
mkdir -p "${SMOKE_DIR}"
cp src/masternoder2d src/masternoder2-cli "${SMOKE_DIR}/"
[[ -f src/masternoder2-tx ]] && cp src/masternoder2-tx "${SMOKE_DIR}/" || true
VER_PREFIX="${VERSION#v}"
bash "${SCRIPT_DIR}/mn2_build_smoke.sh" "${SMOKE_DIR}" "${VER_PREFIX}"

DIST="${BUILD_ROOT}/dist"
PKG="${DIST}/masternoder2d"
rm -rf "${PKG}"
mkdir -p "${PKG}"
cp src/masternoder2d src/masternoder2-cli "${PKG}/"
[[ -f src/masternoder2-tx ]] && cp src/masternoder2-tx "${PKG}/" || true
chmod +x "${PKG}/"*

BUILT_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BUILD_HOST=$(hostname 2>/dev/null || echo unknown)
MANIFEST="${DIST}/RELEASE_MANIFEST.json"
PATCH_SHA=""
if [[ "${PATCHED}" == "1" ]] && [[ -n "${PATCH_FILE}" ]] && [[ -f "${PATCH_FILE}" ]]; then
  PATCH_SHA=$(sha256_file "${PATCH_FILE}")
fi

python3 - "${MANIFEST}" "${VERSION}" "${GIT_SHA}" "${BUILT_AT}" "${BUILD_HOST}" "${USE_DEPENDS}" "${PKG}" "${BASE_TAG}" "${PATCHED}" "${PATCH_FILE}" "${PATCH_SHA}" <<'PY'
import json, os, sys
(manifest_path, version, git_sha, built_at, build_host, use_depends, pkg,
 base_tag, patched, patch_file, patch_sha) = sys.argv[1:12]

def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

binaries = {}
for name in ("masternoder2d", "masternoder2-cli", "masternoder2-tx"):
    p = os.path.join(pkg, name)
    if os.path.isfile(p):
        binaries[name] = {"sha256": sha256(p), "size": os.path.getsize(p)}

doc = {
    "version": version,
    "git_tag": version,
    "git_sha": git_sha,
    "built_at": built_at,
    "build_host": build_host,
    "use_depends": use_depends == "1",
    "binaries": binaries,
}
if patched == "1":
    doc["base_tag"] = base_tag
    doc["patch_applied"] = True
    doc["patch_file"] = os.path.basename(patch_file) if patch_file else None
    if patch_sha:
        doc["patch_sha256"] = patch_sha

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
print(f"Wrote {manifest_path}")
PY

cd "${DIST}"
rm -f masternoder2d.tar.gz masternoder2d.tar.gz.sha256
tar czf masternoder2d.tar.gz masternoder2d RELEASE_MANIFEST.json
TAR_SHA=$(sha256_file masternoder2d.tar.gz)
echo "${TAR_SHA}  masternoder2d.tar.gz" > masternoder2d.tar.gz.sha256

python3 - "${MANIFEST}" "${TAR_SHA}" <<'PY'
import json, sys
path, tar_sha = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    doc = json.load(f)
doc["tarball_sha256"] = tar_sha
doc["tarball_name"] = "masternoder2d.tar.gz"
with open(path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
PY

tar czf masternoder2d.tar.gz masternoder2d RELEASE_MANIFEST.json
sha256sum masternoder2d.tar.gz > masternoder2d.tar.gz.sha256 2>/dev/null || \
  shasum -a 256 masternoder2d.tar.gz > masternoder2d.tar.gz.sha256

echo ""
echo "=== Build OK (${VERSION}) ==="
echo "  ${DIST}/masternoder2d.tar.gz"
echo "  ${DIST}/RELEASE_MANIFEST.json"
cat masternoder2d.tar.gz.sha256
echo ""
echo "Next:"
echo "  python scripts/mn2_publish_release.py --tarball ${DIST}/masternoder2d.tar.gz --manifest ${DIST}/RELEASE_MANIFEST.json --draft --skip-tag"
echo "  python scripts/mn2_release_status.py --tarball ${DIST}/masternoder2d.tar.gz"
