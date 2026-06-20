#!/usr/bin/env bash
# Offline smoke test for MN2 release binaries (no running daemon required).
# Usage: bash scripts/mn2_build_smoke.sh /path/to/masternoder2d/dir

set -euo pipefail

BIN_DIR="${1:?usage: mn2_build_smoke.sh <binary-dir>}"

fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }
ok() { echo "SMOKE OK: $*"; }

[[ -d "${BIN_DIR}" ]] || fail "not a directory: ${BIN_DIR}"

DAEMON="${BIN_DIR}/masternoder2d"
CLI="${BIN_DIR}/masternoder2-cli"
TX="${BIN_DIR}/masternoder2-tx"

[[ -x "${DAEMON}" ]] || fail "missing executable ${DAEMON}"
[[ -x "${CLI}" ]] || fail "missing executable ${CLI}"

VER_D=$("${DAEMON}" -version 2>&1 | head -1 || true)
VER_C=$("${CLI}" -version 2>&1 | head -1 || true)
[[ -n "${VER_D}" ]] || fail "masternoder2d -version produced no output"
[[ -n "${VER_C}" ]] || fail "masternoder2-cli -version produced no output"
ok "daemon version: ${VER_D}"
ok "cli version: ${VER_C}"

if strings "${DAEMON}" 2>/dev/null | grep -q "getstakinginfo"; then
  ok "getstakinginfo symbol present in daemon"
else
  fail "getstakinginfo not found in daemon binary (v1.2.3.0 required)"
fi

if strings "${CLI}" 2>/dev/null | grep -q "getstakinginfo"; then
  ok "getstakinginfo symbol present in cli"
else
  echo "SMOKE WARN: getstakinginfo not in cli strings (may still work via RPC table)" >&2
fi

if [[ -x "${TX}" ]]; then
  TXV=$("${TX}" -version 2>&1 | head -1 || true)
  [[ -n "${TXV}" ]] || fail "masternoder2-tx -version failed"
  ok "tx version: ${TXV}"
else
  echo "SMOKE WARN: masternoder2-tx not bundled (optional)" >&2
fi

# Minimum size guards (stripped binary should still be multi-MB)
SZ_D=$(stat -c%s "${DAEMON}" 2>/dev/null || stat -f%z "${DAEMON}")
(( SZ_D > 500000 )) || fail "masternoder2d suspiciously small (${SZ_D} bytes)"

echo ""
echo "=== All smoke checks passed ==="
