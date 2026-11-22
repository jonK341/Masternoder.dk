#!/usr/bin/env bash
# Install and start MasterNoder2 daemon inside WSL (avoids Windows Smart App Control).
# Usage (from PowerShell after WSL is installed):
#   wsl -d Ubuntu -- bash -lc 'bash /mnt/c/Users/jonkh/Documents/Masternoder.dk/scripts/setup_mn2_daemon_wsl.sh'
set -euo pipefail

RELEASE_URL="${MN2_RELEASE_URL:-https://github.com/jonK341/MasterNoder2/releases/download/v1.2.2.0/masternoder2d.tar.gz}"
INSTALL_DIR="${HOME}/mn2-daemon"
DATADIR="${HOME}/.masternoder2"
RPC_USER="${MN2_RPC_USER:-mn2rpc}"
RPC_PASSWORD="${MN2_RPC_PASSWORD:-}"

if [[ -z "${RPC_PASSWORD}" ]]; then
  RPC_PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-28)"
fi

mkdir -p "${INSTALL_DIR}" "${DATADIR}"
cd "${INSTALL_DIR}"

if [[ ! -f masternoder2d.tar.gz ]]; then
  echo "[1/5] Downloading daemon..."
  curl -fsSL -o masternoder2d.tar.gz "${RELEASE_URL}"
else
  echo "[1/5] Using existing masternoder2d.tar.gz"
fi

echo "[2/5] Extracting..."
tar -xzf masternoder2d.tar.gz
if [[ -x "${INSTALL_DIR}/masternoder2d/masternoder2d" ]]; then
  BIN="${INSTALL_DIR}/masternoder2d/masternoder2d"
elif [[ -x "${INSTALL_DIR}/masternoder2d" && -f "${INSTALL_DIR}/masternoder2d" ]]; then
  BIN="${INSTALL_DIR}/masternoder2d"
else
  BIN="$(find "${INSTALL_DIR}" -maxdepth 3 -type f -name masternoder2d | head -n 1)"
fi
if [[ -z "${BIN}" || ! -f "${BIN}" ]]; then
  echo "ERROR: masternoder2d binary not found after extract" >&2
  exit 1
fi
chmod +x "${BIN}"

echo "[3/5] Writing ${DATADIR}/masternoder2.conf"
cat > "${DATADIR}/masternoder2.conf" <<EOF
server=1
daemon=1
rpcuser=${RPC_USER}
rpcpassword=${RPC_PASSWORD}
rpcport=9332
rpcallowip=127.0.0.1
rpcbind=127.0.0.1
listen=1
port=17646
dns=1
dnsseed=1
discover=1
addnode=explorer.masternoder.dk:17646
addnode=192.46.237.230:17646
addnode=213.136.90.158:17646
EOF
chmod 600 "${DATADIR}/masternoder2.conf"

# Stop any previous instance
pkill -f "${BIN}" 2>/dev/null || true
sleep 1

echo "[4/5] Starting daemon: ${BIN}"
"${BIN}" -datadir="${DATADIR}"

echo "[5/5] Checking RPC..."
sleep 3
if curl -s -u "${RPC_USER}:${RPC_PASSWORD}" \
  --data-binary '{"jsonrpc":"1.0","id":"wsl","method":"getblockchaininfo","params":[]}' \
  -H "content-type: text/plain;" \
  http://127.0.0.1:9332/ | grep -q '"result"'; then
  echo "OK — daemon RPC is up on 127.0.0.1:9332"
else
  echo "WARN — RPC not ready yet (sync may still be starting). Retry in a minute."
fi

CREDS_FILE="${DATADIR}/local-rpc-credentials.txt"
cat > "${CREDS_FILE}" <<EOF
MN2_RPC_URL=http://127.0.0.1:9332
MN2_RPC_USER=${RPC_USER}
MN2_RPC_PASSWORD=${RPC_PASSWORD}
EOF
chmod 600 "${CREDS_FILE}"

echo
echo "Done."
echo "  Binary:  ${BIN}"
echo "  Datadir: ${DATADIR}"
echo "  Creds:   ${CREDS_FILE}"
echo
echo "Useful commands:"
echo "  # status"
echo "  curl -s -u '${RPC_USER}:****' --data-binary '{\"jsonrpc\":\"1.0\",\"id\":\"x\",\"method\":\"getblockchaininfo\",\"params\":[]}' -H 'content-type: text/plain;' http://127.0.0.1:9332/"
echo "  # new address"
echo "  curl -s -u '${RPC_USER}:****' --data-binary '{\"jsonrpc\":\"1.0\",\"id\":\"x\",\"method\":\"getnewaddress\",\"params\":[]}' -H 'content-type: text/plain;' http://127.0.0.1:9332/"
echo "  # stop"
echo "  ${BIN} -datadir=${DATADIR} stop"
