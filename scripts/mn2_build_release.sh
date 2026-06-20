#!/usr/bin/env bash
# Build MasterNoder2 release tarball for Linux x86_64 (pinned to VERSION tag).
#
# Run on Linux or WSL (not Windows native). Needs ~2 GB RAM.
#
# Usage:
#   bash scripts/mn2_build_release.sh
#   BUILD_ROOT=/data/mn2-build JOBS=4 bash scripts/mn2_build_release.sh
#   USE_DEPENDS=0 bash scripts/mn2_build_release.sh          # faster, less portable
#   INSTALL_BUILD_DEPS=1 bash scripts/mn2_build_release.sh   # apt install on Debian/Ubuntu

set -euo pipefail

VERSION="${VERSION:-v1.2.3.0}"
REPO_URL="${REPO_URL:-https://github.com/jonK341/MasterNoder2.git}"
BUILD_ROOT="${BUILD_ROOT:-/tmp/mn2-build}"
SRC_DIR="${BUILD_ROOT}/MasterNoder2"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 2)}"
USE_DEPENDS="${USE_DEPENDS:-1}"
INSTALL_BUILD_DEPS="${INSTALL_BUILD_DEPS:-1}"
SKIP_DEPENDS_BUILD="${SKIP_DEPENDS_BUILD:-0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ensure_build_deps() {
  if [[ "${INSTALL_BUILD_DEPS}" != "1" ]]; then
    if command -v autoconf >/dev/null && command -v automake >/dev/null && command -v libtoolize >/dev/null; then
      return 0
    fi
    echo "Missing autoconf/automake/libtool. Set INSTALL_BUILD_DEPS=1 or install build packages." >&2
    exit 1
  fi
  if [[ "$(id -u)" -ne 0 ]] || ! command -v apt-get >/dev/null; then
    echo "Run as root on Debian/Ubuntu, or install: autoconf automake libtool build-essential libboost-all-dev libssl-dev libevent-dev libbsd-dev" >&2
    exit 1
  fi
  echo "=== Installing MN2 build dependencies (apt) ==="
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq \
    git build-essential autoconf automake libtool pkg-config \
    libboost-all-dev libssl-dev libevent-dev libzmq3-dev \
    libdb-dev libminiupnpc-dev libbsd-dev libgmp-dev
}

# Static depends: libevent → libbsd; zerocoin → libgmp. Set before configure + make (do not override on make cmdline).
apply_depends_link_flags() {
  local host_dir="$1"
  export PKG_CONFIG_PATH="${host_dir}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
  export CPPFLAGS="-I${host_dir}/include"
  export LDFLAGS="-L${host_dir}/lib"
  export LIBS="-lbsd -lgmp"
  echo "Link flags: LDFLAGS=${LDFLAGS} LIBS=${LIBS}"
}

sha256_file() {
  if command -v sha256sum >/dev/null; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

ensure_build_deps

echo "=== MN2 release build ${VERSION} (tag-pinned) ==="
echo "BUILD_ROOT=${BUILD_ROOT}  JOBS=${JOBS}  USE_DEPENDS=${USE_DEPENDS}"

mkdir -p "${BUILD_ROOT}"
if [[ -d "${SRC_DIR}/.git" ]]; then
  echo "Updating existing clone..."
  git -C "${SRC_DIR}" fetch --tags origin
else
  echo "Cloning ${REPO_URL}..."
  git clone "${REPO_URL}" "${SRC_DIR}"
fi

cd "${SRC_DIR}"
if ! git rev-parse "refs/tags/${VERSION}" >/dev/null 2>&1; then
  echo "Tag ${VERSION} not found locally; fetching..."
  git fetch --tags origin
fi
git checkout -f "${VERSION}"
GIT_SHA=$(git rev-parse HEAD)
GIT_SUBJECT=$(git log -1 --format=%s)
echo "Source at tag ${VERSION}: ${GIT_SHA:0:12} — ${GIT_SUBJECT}"

if [[ "${USE_DEPENDS}" == "1" ]]; then
  HOST_DIR="${SRC_DIR}/depends/x86_64-linux-gnu"
  if [[ -d "${HOST_DIR}/lib" ]] && [[ "${SKIP_DEPENDS_BUILD}" == "1" ]]; then
    echo "=== depends already built — skipping (SKIP_DEPENDS_BUILD=1) ==="
  else
    echo "=== depends (static, NO_QT) — first run can take 30–60 min ==="
    cd depends
    make -j"${JOBS}" HOST=x86_64-linux-gnu NO_QT=1
    cd ..
  fi
  apply_depends_link_flags "${HOST_DIR}"
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
  CONFIGURE_FLAGS=(--without-gui --disable-tests --disable-bench)
fi

./configure "${CONFIGURE_FLAGS[@]}"
if [[ "${USE_DEPENDS}" == "1" ]]; then
  apply_depends_link_flags "${HOST_DIR}"
fi

build_target() {
  local target="$1"
  local required="${2:-1}"
  echo "=== make ${target} ==="
  if ! make -j"${JOBS}" "${target}"; then
    if [[ "${required}" == "1" ]]; then
      echo "BUILD FAIL: make ${target}" >&2
      exit 2
    fi
    echo "WARN: make ${target} failed (optional)" >&2
    return 1
  fi
  return 0
}

build_target src/masternoder2d 1
build_target src/masternoder2-cli 1
build_target src/masternoder2-tx 0 || true

for bin in masternoder2d masternoder2-cli; do
  [[ -x "src/${bin}" ]] || { echo "BUILD FAIL: src/${bin} missing after make" >&2; exit 2; }
done
if [[ -f src/masternoder2-tx ]]; then
  chmod +x src/masternoder2-tx 2>/dev/null || true
fi

strip -s src/masternoder2d src/masternoder2-cli src/masternoder2-tx 2>/dev/null || \
  strip -s src/masternoder2d src/masternoder2-cli || true

echo "=== Post-build smoke test ==="
SMOKE_DIR="${BUILD_ROOT}/smoke-bin"
rm -rf "${SMOKE_DIR}"
mkdir -p "${SMOKE_DIR}"
cp src/masternoder2d src/masternoder2-cli "${SMOKE_DIR}/"
[[ -f src/masternoder2-tx ]] && cp src/masternoder2-tx "${SMOKE_DIR}/" || true
bash "${SCRIPT_DIR}/mn2_build_smoke.sh" "${SMOKE_DIR}"

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

python3 - "${MANIFEST}" "${VERSION}" "${GIT_SHA}" "${BUILT_AT}" "${BUILD_HOST}" "${USE_DEPENDS}" "${PKG}" <<'PY'
import json, os, sys
manifest_path, version, git_sha, built_at, build_host, use_depends, pkg = sys.argv[1:8]

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
print(f"Manifest tarball_sha256={tar_sha}")
PY

echo ""
echo "=== Build OK ==="
echo "  ${DIST}/masternoder2d.tar.gz"
echo "  ${DIST}/RELEASE_MANIFEST.json"
cat masternoder2d.tar.gz.sha256
echo ""
echo "Smoke + manifest verified. Next:"
echo "  python scripts/mn2_publish_release.py --tarball ${DIST}/masternoder2d.tar.gz --manifest ${DIST}/RELEASE_MANIFEST.json --draft"
echo "  python scripts/mn2_release_status.py --tarball ${DIST}/masternoder2d.tar.gz"
