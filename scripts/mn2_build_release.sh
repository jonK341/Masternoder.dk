#!/usr/bin/env bash
# Build MasterNoder2 release tarball for Linux x86_64 (pinned to VERSION tag or patch).
#
# Run on Linux or WSL (not Windows native). Needs ~2 GB RAM.
#
# Usage:
#   bash scripts/mn2_build_release.sh
#   VERSION=v1.3.0.0 PATCH_FILE=/tmp/mn2.patch bash scripts/mn2_build_release.sh
#   BUILD_ROOT=/tmp/mn2-build JOBS=4 bash scripts/mn2_build_release.sh
#   USE_DEPENDS=0 bash scripts/mn2_build_release.sh          # faster, less portable
#   INSTALL_BUILD_DEPS=1 bash scripts/mn2_build_release.sh   # apt install on Debian/Ubuntu
#
# Stages (MN2_BUILD_STAGE):
#   prepare   — clone/fetch, multi-ping patch, compat patch, verify UPNP
#   configure — depends (if USE_DEPENDS=1), autogen, ./configure
#   compile   — make -C src (single job on --fast)
#   package   — strip, smoke test, tarball, manifest
#   setup     — prepare + configure (alias)
#   build     — compile + package (alias)
#   all       — all four stages (default)
#
# Resume: each stage writes BUILD_ROOT/.stage-<name>-done; later stages error if a prior stage is missing.
#
#   MN2_BUILD_STAGE=prepare bash scripts/mn2_build_release.sh
#   MN2_BUILD_STAGE=configure bash scripts/mn2_build_release.sh
#   MN2_BUILD_STAGE=compile bash scripts/mn2_build_release.sh
#   MN2_BUILD_STAGE=package bash scripts/mn2_build_release.sh
#
# Legacy: CONFIGURE_ONLY=1 → setup; BUILD_ONLY=1 → compile

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
FAST_SINGLE_JOB="${FAST_SINGLE_JOB:-1}"
MN2_BUILD_STAGE="${MN2_BUILD_STAGE:-all}"
[[ "${CONFIGURE_ONLY:-0}" == "1" ]] && MN2_BUILD_STAGE=setup
[[ "${BUILD_ONLY:-0}" == "1" ]] && MN2_BUILD_STAGE=compile
BUILD_LOG="${BUILD_ROOT}/build.log"
PREPARE_META="${BUILD_ROOT}/.prepare-meta"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/../docs/patches/mn2-daemon-build-compat-modern-host.patch" ]]; then
  REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
  REPO_ROOT="${MN2_REPO_ROOT:-}"
fi
COMPAT_PATCH_DEFAULT="${REPO_ROOT}/docs/patches/mn2-daemon-build-compat-modern-host.patch"
PATCHED=0
MAKE_JOBS="${JOBS}"
GIT_SHA=""

RUN_PREPARE=0
RUN_CONFIGURE=0
RUN_COMPILE=0
RUN_PACKAGE=0

APT_BUILD_PACKAGES=(
  git build-essential g++ autoconf automake libtool pkg-config patch bzip2 ca-certificates
  libboost-all-dev libssl-dev libevent-dev libzmq3-dev
  libdb-dev libminiupnpc-dev libgmp-dev libbsd-dev
)

stage_marker() {
  echo "${BUILD_ROOT}/.stage-${1}-done"
}

mark_stage_done() {
  touch "$(stage_marker "$1")"
}

require_stage_done() {
  local stage="$1"
  local marker
  marker="$(stage_marker "${stage}")"
  if [[ ! -f "${marker}" ]]; then
    echo "ERROR: prerequisite stage '${stage}' not complete (missing ${marker})." >&2
    echo "  Run: MN2_BUILD_STAGE=${stage} bash scripts/mn2_build_release.sh" >&2
    echo "  Or:  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage ${stage}" >&2
    exit 1
  fi
}

resolve_run_stages() {
  case "${MN2_BUILD_STAGE}" in
    all)
      RUN_PREPARE=1; RUN_CONFIGURE=1; RUN_COMPILE=1; RUN_PACKAGE=1 ;;
    prepare)
      RUN_PREPARE=1 ;;
    configure)
      RUN_CONFIGURE=1 ;;
    compile)
      RUN_COMPILE=1 ;;
    package)
      RUN_PACKAGE=1 ;;
    setup)
      RUN_PREPARE=1; RUN_CONFIGURE=1 ;;
    build)
      RUN_COMPILE=1; RUN_PACKAGE=1 ;;
    *)
      echo "Unknown MN2_BUILD_STAGE='${MN2_BUILD_STAGE}'" >&2
      echo "  Valid: prepare, configure, compile, package, setup, build, all" >&2
      exit 1
      ;;
  esac
}

next_stage_hint() {
  case "${MN2_BUILD_STAGE}" in
    prepare)
      echo "Next: MN2_BUILD_STAGE=configure bash scripts/mn2_build_release.sh"
      echo "  Or:  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage configure"
      ;;
    configure|setup)
      echo "Next: MN2_BUILD_STAGE=compile bash scripts/mn2_build_release.sh"
      echo "  Or:  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage compile"
      ;;
    compile|build)
      echo "Next: MN2_BUILD_STAGE=package bash scripts/mn2_build_release.sh"
      echo "  Or:  python scripts/mn2_build_release_remote.py --ask-pass --fast --stage package --publish --draft"
      ;;
    package)
      echo "Next: python scripts/mn2_publish_release.py --tarball ${BUILD_ROOT}/dist/masternoder2d.tar.gz --manifest ${BUILD_ROOT}/dist/RELEASE_MANIFEST.json --draft --skip-tag"
      ;;
  esac
}

write_prepare_meta() {
  cat > "${PREPARE_META}" <<EOF
PATCHED=${PATCHED}
PATCH_FILE=${PATCH_FILE}
GIT_SHA=${GIT_SHA}
EOF
}

load_prepare_meta() {
  if [[ -f "${PREPARE_META}" ]]; then
    # shellcheck disable=SC1090
    source "${PREPARE_META}"
  elif [[ -d "${SRC_DIR}/.git" ]]; then
    GIT_SHA=$(git -C "${SRC_DIR}" rev-parse HEAD)
  fi
}

print_build_errors() {
  echo "" >&2
  echo "Full log: ${BUILD_LOG}" >&2
  if [[ -f "${BUILD_LOG}" ]]; then
    local lines
    lines="$(grep -iE 'error:|Failed to build|Error [0-9]+|fatal error|funcs\.mk:.*boost|stamp_configured|Boost\.Build engine' "${BUILD_LOG}" | head -10 || true)"
    if [[ -n "${lines}" ]]; then
      echo "=== Build errors (from log) ===" >&2
      printf '%s\n' "${lines}" >&2
    else
      echo "=== Last lines of build log ===" >&2
      tail -25 "${BUILD_LOG}" >&2 || true
    fi
  fi
}

die_build() {
  local code="${1:-1}"
  print_build_errors
  exit "${code}"
}

resolve_make_jobs() {
  MAKE_JOBS="${JOBS}"
  if [[ "${USE_DEPENDS}" == "0" ]] && [[ "${FAST_SINGLE_JOB}" == "1" ]]; then
    MAKE_JOBS=1
  fi
}

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
  echo "=== depends (static, NO_QT) — first run can take 30–60 min ==="
  cd depends
  set +e
  make -j"${JOBS}" HOST=x86_64-linux-gnu NO_QT=1 2>&1 | tee -a "${BUILD_LOG}"
  local dep_status=${PIPESTATUS[0]}
  set -e
  cd ..
  if [[ "${dep_status}" -ne 0 ]]; then
    if is_boost_depends_failure "$(cat "${BUILD_LOG}")"; then
      echo "" >&2
      echo "=== depends boost build failed (Boost.Build engine / gcc toolset) ===" >&2
      echo "Common on minimal VPS hosts even when autoconf is present." >&2
      echo "Retry with system libraries (faster, less portable):" >&2
      echo "  USE_DEPENDS=0 bash scripts/mn2_build_release.sh" >&2
      echo "  python scripts/mn2_build_release_remote.py --ask-pass --fast --no-auto-depends --publish --draft" >&2
    fi
    die_build "${dep_status}"
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
  if ! patch -p1 --forward < "${PATCH_FILE}"; then
    echo "ERROR: multi-ping patch failed to apply on ${BASE_TAG}." >&2
    exit 2
  fi
  PATCHED=1
}

apply_patch_file() {
  local label="$1"
  local patch_path="$2"
  local tmp log
  tmp="$(mktemp)"
  log="$(mktemp)"
  sed 's/\r$//' "${patch_path}" > "${tmp}"
  if ! patch -p1 --forward --batch --reject-file=- -i "${tmp}" >"${log}" 2>&1; then
    echo "ERROR: ${label} failed (patch -p1 rejected hunks or malformed diff)." >&2
    sed -n '1,40p' "${log}" >&2 || true
    rm -f "${tmp}" "${log}"
    exit 2
  fi
  if grep -qiE 'hunk FAILED|patch: \*\*\*\*|can.t find file to patch|Reversed \(or previously applied\) patch detected!' "${log}"; then
    echo "ERROR: ${label} reported patch failures:" >&2
    sed -n '1,40p' "${log}" >&2 || true
    rm -f "${tmp}" "${log}"
    exit 2
  fi
  rm -f "${tmp}" "${log}"
}

resolve_compat_patch() {
  local compat="${COMPAT_PATCH_FILE:-}"
  if [[ -z "${compat}" ]] && [[ -n "${REPO_ROOT}" ]] && [[ -f "${COMPAT_PATCH_DEFAULT}" ]]; then
    compat="${COMPAT_PATCH_DEFAULT}"
  fi
  if [[ -z "${compat}" ]] || [[ ! -f "${compat}" ]]; then
    echo "ERROR: compat patch not found (set COMPAT_PATCH_FILE=/path/to/mn2-daemon-build-compat-modern-host.patch)." >&2
    exit 2
  fi
  printf '%s' "${compat}"
}

verify_upnp_compat() {
  local net_cpp="${SRC_DIR}/src/net.cpp"
  if [[ ! -f "${net_cpp}" ]]; then
    echo "ERROR: ${net_cpp} missing — run prepare stage first." >&2
    exit 2
  fi
  if grep -qE 'UPNP_GetValidIGD\([^)]*nullptr,\s*0\)' "${net_cpp}"; then
    return 0
  fi
  if grep -q 'MINIUPNPC_API_VERSION >= 18' "${net_cpp}" && grep -q 'nullptr, 0' "${net_cpp}"; then
    return 0
  fi
  if grep -q 'defined(__linux__)' "${net_cpp}" && grep -q 'nullptr, 0' "${net_cpp}"; then
    return 0
  fi
  echo "ERROR: UPNP_GetValidIGD compat fix missing in src/net.cpp (expected 7-arg call or MINIUPNPC guard)." >&2
  echo "  Re-run prepare stage or ensure COMPAT_PATCH_FILE applies on this host." >&2
  exit 2
}

apply_compat_patch() {
  local compat
  compat="$(resolve_compat_patch)"
  echo "=== Apply modern-host build compat patch (${compat}) ==="
  apply_patch_file "modern-host compat patch" "${compat}"
  if [[ "${USE_DEPENDS}" == "0" ]] && ! grep -q '#include "util.h"' src/net.cpp; then
    echo "ERROR: compat patch did not update src/net.cpp (missing util.h for TraceThread)." >&2
    exit 2
  fi
  verify_upnp_compat
}

ensure_compat_patch() {
  cd "${SRC_DIR}"
  if verify_upnp_compat 2>/dev/null; then
    return 0
  fi
  echo "=== UPNP compat missing — re-applying modern-host patch before compile ==="
  apply_compat_patch
}

stage_prepare() {
  echo ""
  echo "=== STAGE 1/4: Prepare (clone, patch, compat) ==="

  if [[ -d "${SRC_DIR}/.git" ]]; then
    echo "Updating existing clone..."
    git -C "${SRC_DIR}" fetch --tags origin
  else
    echo "Cloning ${REPO_URL}..."
    git clone "${REPO_URL}" "${SRC_DIR}"
  fi

  checkout_source
  apply_compat_patch
  GIT_SHA=$(git -C "${SRC_DIR}" rev-parse HEAD)
  GIT_SUBJECT=$(git -C "${SRC_DIR}" log -1 --format=%s)
  echo "Source: ${GIT_SHA:0:12} — ${GIT_SUBJECT}"
  if [[ "${PATCHED}" == "1" ]]; then
    echo "Patch applied on ${BASE_TAG} → build as ${VERSION}"
  fi

  write_prepare_meta
  mark_stage_done prepare
}

stage_configure() {
  echo ""
  echo "=== STAGE 2/4: Configure (depends, autogen, configure) ==="

  if [[ ! -d "${SRC_DIR}/.git" ]]; then
    echo "Source tree missing at ${SRC_DIR}; run prepare stage first." >&2
    exit 1
  fi

  ensure_build_deps
  load_prepare_meta
  cd "${SRC_DIR}"

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
  mark_stage_done configure
}

stage_compile() {
  echo ""
  echo "=== STAGE 3/4: Compile (make -C src) ==="

  if [[ ! -d "${SRC_DIR}/.git" ]]; then
    echo "Source tree missing at ${SRC_DIR}; run prepare stage first." >&2
    exit 1
  fi

  load_prepare_meta
  cd "${SRC_DIR}"
  ensure_compat_patch
  run_compile
  mark_stage_done compile
}

run_compile() {
  resolve_make_jobs
  echo "=== make targets (MAKE_JOBS=${MAKE_JOBS}, log: ${BUILD_LOG}) ==="

  if [[ "${USE_DEPENDS}" == "1" ]]; then
    echo "=== make -C src depend ==="
    set +e
    make -j"${JOBS}" -C src depend 2>&1 | tee -a "${BUILD_LOG}"
    local dep_status=${PIPESTATUS[0]}
    set -e
    if [[ "${dep_status}" -ne 0 ]]; then
      die_build "${dep_status}"
    fi
  fi

  set +e
  make -j"${MAKE_JOBS}" -C src masternoder2d masternoder2-cli 2>&1 | tee -a "${BUILD_LOG}"
  local make_status=${PIPESTATUS[0]}
  set -e
  if [[ "${make_status}" -ne 0 ]]; then
    die_build "${make_status}"
  fi
}

stage_package() {
  echo ""
  echo "=== STAGE 4/4: Package (strip, smoke, tarball) ==="

  if [[ ! -d "${SRC_DIR}/.git" ]]; then
    echo "Source tree missing at ${SRC_DIR}; run prepare stage first." >&2
    exit 1
  fi

  load_prepare_meta
  cd "${SRC_DIR}"
  run_package
  mark_stage_done package
}

run_package() {
  strip -s src/masternoder2d src/masternoder2-cli 2>/dev/null || true

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

  echo "${TAR_SHA}  masternoder2d.tar.gz" > masternoder2d.tar.gz.sha256

  # Guard: manifest tarball_sha256 must match the tarball we just built.
  MANIFEST_SHA=$(python3 -c "import json; print(json.load(open('RELEASE_MANIFEST.json'))['tarball_sha256'])")
  VERIFY_SHA=$(sha256_file masternoder2d.tar.gz)
  if [[ "${MANIFEST_SHA}" != "${VERIFY_SHA}" ]]; then
    echo "FATAL: RELEASE_MANIFEST.json tarball_sha256 (${MANIFEST_SHA}) != tarball (${VERIFY_SHA})" >&2
    exit 1
  fi

  echo ""
  echo "=== Build OK (${VERSION}) ==="
  echo "  ${DIST}/masternoder2d.tar.gz"
  echo "  ${DIST}/RELEASE_MANIFEST.json"
  cat masternoder2d.tar.gz.sha256
}

# --- main ---

resolve_run_stages

echo "=== MN2 release build ${VERSION} ==="
echo "BUILD_ROOT=${BUILD_ROOT}  JOBS=${JOBS}  USE_DEPENDS=${USE_DEPENDS}  STAGE=${MN2_BUILD_STAGE}"
echo "BUILD_LOG=${BUILD_LOG}  FAST_SINGLE_JOB=${FAST_SINGLE_JOB}"
echo "BASE_TAG=${BASE_TAG}  PATCH_FILE=${PATCH_FILE:-none}  CHECKOUT_BRANCH=${CHECKOUT_BRANCH:-none}"

mkdir -p "${BUILD_ROOT}"
if [[ "${MN2_BUILD_STAGE}" == "all" ]]; then
  : > "${BUILD_LOG}"
else
  touch "${BUILD_LOG}"
fi

# Prerequisite checks for stages not run in this invocation
if [[ "${RUN_CONFIGURE}" == "1" ]] && [[ "${RUN_PREPARE}" != "1" ]]; then
  require_stage_done prepare
fi
if [[ "${RUN_COMPILE}" == "1" ]] && [[ "${RUN_CONFIGURE}" != "1" ]]; then
  require_stage_done configure
fi
if [[ "${RUN_PACKAGE}" == "1" ]] && [[ "${RUN_COMPILE}" != "1" ]]; then
  require_stage_done compile
fi

if [[ "${RUN_PREPARE}" == "1" ]]; then
  stage_prepare
fi

if [[ "${RUN_CONFIGURE}" == "1" ]]; then
  stage_configure
fi

if [[ "${RUN_COMPILE}" == "1" ]]; then
  stage_compile
fi

if [[ "${RUN_PACKAGE}" == "1" ]]; then
  stage_package
fi

if [[ "${MN2_BUILD_STAGE}" != "all" ]]; then
  echo ""
  echo "=== Stage '${MN2_BUILD_STAGE}' complete ==="
  next_stage_hint
fi
