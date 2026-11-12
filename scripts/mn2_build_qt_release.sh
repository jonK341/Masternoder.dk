#!/usr/bin/env bash
# Build MasterNoder2 Qt GUI release packages (Linux desktop and/or Windows cross-compile).
#
# Run on Linux (production server, WSL, or GitHub Actions). Not Windows native.
#
# Usage:
#   bash scripts/mn2_build_qt_release.sh --target linux
#   bash scripts/mn2_build_qt_release.sh --target win
#   bash scripts/mn2_build_qt_release.sh --target all
#   TARGET=linux USE_DEPENDS=0 bash scripts/mn2_build_qt_release.sh
#
# Env (same as mn2_build_release.sh):
#   VERSION, BASE_TAG, PATCH_FILE, CHECKOUT_BRANCH, BUILD_ROOT, JOBS, USE_DEPENDS, INSTALL_BUILD_DEPS

set -euo pipefail

TARGET="${TARGET:-linux}"
for arg in "$@"; do
  case "${arg}" in
    --target=*) TARGET="${arg#*=}" ;;
    --target) shift; TARGET="${1:?--target needs linux|win|all}" ;;
  esac
done

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

APT_DAEMON_PACKAGES=(
  git build-essential g++ autoconf automake libtool pkg-config patch bzip2 ca-certificates
  libboost-all-dev libssl-dev libevent-dev libzmq3-dev
  libdb-dev libminiupnpc-dev libgmp-dev libbsd-dev
)
APT_QT_LINUX_PACKAGES=(
  qtbase5-dev qttools5-dev-tools qttools5-dev libqrencode-dev
  libprotobuf-dev protobuf-compiler
)
APT_QT_WIN_PACKAGES=(g++-mingw-w64-x86-64 nsis)

sha256_file() {
  if command -v sha256sum >/dev/null; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

require_build_tools() {
  local missing=()
  for cmd in autoconf automake libtoolize g++ make; do
    command -v "${cmd}" >/dev/null || missing+=("${cmd}")
  done
  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "Missing build tools: ${missing[*]}" >&2
    exit 1
  fi
}

ensure_build_deps() {
  local extra=()
  if [[ "${TARGET}" == "linux" || "${TARGET}" == "all" ]]; then
    extra+=("${APT_QT_LINUX_PACKAGES[@]}")
  fi
  if [[ "${TARGET}" == "win" || "${TARGET}" == "all" ]]; then
    extra+=("${APT_QT_WIN_PACKAGES[@]}")
  fi
  if [[ "${INSTALL_BUILD_DEPS}" == "1" ]] && [[ "$(id -u)" -eq 0 ]] && command -v apt-get >/dev/null; then
    echo "=== Installing MN2 Qt build dependencies (apt) ==="
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq "${APT_DAEMON_PACKAGES[@]}" "${extra[@]}"
    if command -v update-alternatives >/dev/null; then
      update-alternatives --set x86_64-w64-mingw32-g++ /usr/bin/x86_64-w64-mingw32-g++-posix 2>/dev/null || true
    fi
    return 0
  fi
  require_build_tools
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
  fi

  if [[ -z "${PATCH_FILE}" ]]; then
    local default_patch="${REPO_ROOT}/docs/patches/mn2-daemon-v1.3.0-multi-ping.patch"
    if [[ -f "${default_patch}" ]]; then
      PATCH_FILE="${default_patch}"
    fi
  fi

  if [[ -z "${PATCH_FILE}" ]] || [[ ! -f "${PATCH_FILE}" ]]; then
    echo "Tag ${VERSION} not found and PATCH_FILE missing." >&2
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

COMPAT_PATCH_DIR="${COMPAT_PATCH_DIR:-/tmp/mn2-patches}"

apply_compat_patches() {
  local f
  if [[ ! -d "${COMPAT_PATCH_DIR}" ]]; then
    return 0
  fi
  cd "${SRC_DIR}"
  for f in "${COMPAT_PATCH_DIR}"/mn2-gcc15-*.patch; do
    [[ -f "${f}" ]] || continue
    echo "=== Applying compat patch $(basename "${f}") ==="
    if ! patch -p1 --forward < "${f}"; then
      echo "WARN: compat patch $(basename "${f}") failed or already applied" >&2
    fi
  done
  # GCC 15+: libstdc++ no longer pulls <deque> transitively
  if ! grep -q '#include <deque>' src/httpserver.cpp 2>/dev/null; then
    sed -i '/#include <sys\/types.h>/a #include <deque>' src/httpserver.cpp
    echo "Applied sed fallback: #include <deque> in httpserver.cpp"
  fi
}

build_linux_qt() {
  echo "=== Building Linux Qt (USE_DEPENDS=${USE_DEPENDS}) ==="
  cd "${SRC_DIR}"
  if [[ "${USE_DEPENDS}" == "1" ]]; then
    echo "=== depends (x86_64-linux-gnu, with Qt) — first run can take 60–120 min ==="
    cd depends
    make -j"${JOBS}" HOST=x86_64-linux-gnu
    cd ..
    HOST_DIR="${SRC_DIR}/depends/x86_64-linux-gnu"
    ./autogen.sh
    CONFIGURE_FLAGS=(
      --prefix="${HOST_DIR}"
      --with-gui
      --disable-tests
      --disable-bench
      --enable-reduce-exports
    )
  else
    ./autogen.sh
    CONFIGURE_FLAGS=(--with-gui --disable-tests --disable-bench --with-unsupported-ssl)
  fi

  ./configure "${CONFIGURE_FLAGS[@]}"
  make -j"${JOBS}" src/qt/masternoder2-qt
  strip -s src/qt/masternoder2-qt 2>/dev/null || true

  DIST="${BUILD_ROOT}/dist"
  PKG="${DIST}/MasterNoder2-qt-linux"
  rm -rf "${PKG}"
  mkdir -p "${PKG}/bin"
  cp src/qt/masternoder2-qt "${PKG}/bin/"
  chmod +x "${PKG}/bin/masternoder2-qt"
  if [[ -f share/setup.nsi ]]; then
    cp share/setup.nsi "${PKG}/" 2>/dev/null || true
  fi

  cd "${DIST}"
  rm -f MasterNoder2-qt-linux.tar.gz MasterNoder2-qt-linux.tar.gz.sha256
  tar czf MasterNoder2-qt-linux.tar.gz MasterNoder2-qt-linux
  sha256_file MasterNoder2-qt-linux.tar.gz > MasterNoder2-qt-linux.tar.gz.sha256
  echo "Linux Qt: ${DIST}/MasterNoder2-qt-linux.tar.gz"
  cat MasterNoder2-qt-linux.tar.gz.sha256
}

build_win_qt() {
  echo "=== Building Windows Qt cross-compile (USE_DEPENDS=${USE_DEPENDS}) ==="
  cd "${SRC_DIR}"
  if [[ "${USE_DEPENDS}" != "1" ]]; then
    echo "Windows Qt cross-compile requires USE_DEPENDS=1 (depends mingw toolchain)." >&2
    exit 1
  fi

  export PATH
  PATH="$(echo "${PATH}" | sed -e 's/:\/mnt.*//g')"

  echo "=== depends (x86_64-w64-mingw32, with Qt) — first run can take 60–120 min ==="
  cd depends
  make -j"${JOBS}" HOST=x86_64-w64-mingw32
  cd ..

  ./autogen.sh
  CONFIG_SITE="${SRC_DIR}/depends/x86_64-w64-mingw32/share/config.site" \
    ./configure --prefix=/ --with-gui --disable-tests --disable-bench
  make -j"${JOBS}" src/qt/masternoder2-qt.exe

  DIST="${BUILD_ROOT}/dist"
  PKG="${DIST}/MasterNoder2-win"
  rm -rf "${PKG}"
  mkdir -p "${PKG}"
  cp src/qt/masternoder2-qt.exe "${PKG}/"
  if [[ -d src/qt/res ]]; then
    cp -r src/qt/res "${PKG}/" 2>/dev/null || true
  fi
  for dll in $(ls "${SRC_DIR}/depends/x86_64-w64-mingw32/bin/"*.dll 2>/dev/null || true); do
    cp "${dll}" "${PKG}/" 2>/dev/null || true
  done

  cd "${DIST}"
  rm -f MasterNoder2-qt-win.zip MasterNoder2-qt-win.zip.sha256
  if command -v zip >/dev/null; then
    (cd MasterNoder2-win && zip -r ../MasterNoder2-qt-win.zip .)
  else
    apt-get install -y -qq zip
    (cd MasterNoder2-win && zip -r ../MasterNoder2-qt-win.zip .)
  fi
  sha256_file MasterNoder2-qt-win.zip > MasterNoder2-qt-win.zip.sha256
  echo "Windows Qt: ${DIST}/MasterNoder2-qt-win.zip"
  cat MasterNoder2-qt-win.zip.sha256
}

write_qt_manifest() {
  local manifest="${BUILD_ROOT}/dist/QT_RELEASE_MANIFEST.json"
  python3 - "${manifest}" "${VERSION}" "${TARGET}" "${BUILD_ROOT}/dist" <<'PY'
import json, os, sys
manifest_path, version, target, dist = sys.argv[1:5]

def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

assets = {}
for name in ("MasterNoder2-qt-linux.tar.gz", "MasterNoder2-qt-win.zip"):
    p = os.path.join(dist, name)
    if os.path.isfile(p):
        assets[name] = {"sha256": sha256(p), "size": os.path.getsize(p)}

doc = {"version": version, "target": target, "qt_assets": assets}
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
print(f"Wrote {manifest_path}")
PY
}

ensure_build_deps

echo "=== MN2 Qt release build ${VERSION} (target=${TARGET}) ==="
mkdir -p "${BUILD_ROOT}"
if [[ -d "${SRC_DIR}/.git" ]]; then
  git -C "${SRC_DIR}" fetch --tags origin
else
  git clone "${REPO_URL}" "${SRC_DIR}"
fi

checkout_source
apply_compat_patches
GIT_SHA=$(git -C "${SRC_DIR}" rev-parse HEAD)
echo "Source: ${GIT_SHA:0:12}"

case "${TARGET}" in
  linux) build_linux_qt ;;
  win) build_win_qt ;;
  all)
    build_linux_qt
    build_win_qt
    ;;
  *)
    echo "Unknown TARGET=${TARGET} (use linux|win|all)" >&2
    exit 1
    ;;
esac

write_qt_manifest

echo ""
echo "=== Qt build OK (${VERSION}, ${TARGET}) ==="
echo "Next:"
echo "  python scripts/mn2_publish_release.py --qt-assets --skip-tag"
