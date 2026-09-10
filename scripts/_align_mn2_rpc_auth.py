#!/usr/bin/env python3
"""Align MN2 RPC auth on production: conf vs .env, restart, verify."""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh


def mask(s: str, show: int = 4) -> str:
    s = (s or "").strip()
    if not s:
        return "(empty)"
    if len(s) <= show * 2:
        return "*" * len(s)
    return f"{s[:show]}…{s[-show:]}"


REMOTE = r"""bash -s <<'ENDSCRIPT'
set -euo pipefail

WEB=/var/www/html
CONF="$WEB/config/masternoder2.conf"
ENV="$WEB/.env"
DEFAULT_USER=mn2rpc

mask_val() {
  local v="$1"
  local n=${#v}
  if [ -z "$v" ]; then echo "(empty)"; return; fi
  if [ "$n" -le 8 ]; then echo "****"; return; fi
  echo "${v:0:4}…${v: -4}"
}

read_kv() {
  local file="$1" key="$2"
  grep "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"' || true
}

set_env_kv() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV"
  else
    echo "${key}=${val}" >> "$ENV"
  fi
}

set_conf_kv() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$CONF"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$CONF"
  else
    echo "${key}=${val}" >> "$CONF"
  fi
}

echo "========== MN2 RPC AUTH ALIGN $(date -u) =========="
echo "conf=$CONF"
echo "env=$ENV"

CONF_USER=$(read_kv "$CONF" rpcuser)
CONF_PASS=$(read_kv "$CONF" rpcpassword)
ENV_USER=$(read_kv "$ENV" MN2_RPC_USER)
ENV_PASS=$(read_kv "$ENV" MN2_RPC_PASSWORD)

echo "--- BEFORE ---"
echo "conf rpcuser=$(mask_val "$CONF_USER") rpcpassword=$(mask_val "$CONF_PASS")"
echo "env  MN2_RPC_USER=$(mask_val "$ENV_USER") MN2_RPC_PASSWORD=$(mask_val "$ENV_PASS")"

FIXED=0
CANON_USER="${CONF_USER:-$ENV_USER}"
CANON_PASS="${CONF_PASS:-$ENV_PASS}"

# If rpcuser missing everywhere, set default
if [ -z "$CANON_USER" ]; then
  CANON_USER="$DEFAULT_USER"
  set_conf_kv rpcuser "$CANON_USER"
  FIXED=1
  echo "SET conf rpcuser=$DEFAULT_USER (was missing)"
fi

# If rpcpassword missing in conf but present in env, copy to conf
if [ -z "$CONF_PASS" ] && [ -n "$ENV_PASS" ]; then
  set_conf_kv rpcpassword "$ENV_PASS"
  CONF_PASS="$ENV_PASS"
  FIXED=1
  echo "SET conf rpcpassword from .env"
fi

# If rpcpassword missing everywhere, generate one
if [ -z "$CANON_PASS" ]; then
  CANON_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  set_conf_kv rpcpassword "$CANON_PASS"
  CONF_PASS="$CANON_PASS"
  FIXED=1
  echo "GENERATED new rpcpassword in conf"
fi

# Re-read after possible conf updates
CONF_USER=$(read_kv "$CONF" rpcuser)
CONF_PASS=$(read_kv "$CONF" rpcpassword)
CANON_USER="$CONF_USER"
CANON_PASS="$CONF_PASS"

# Align .env to conf (source of truth = daemon conf)
if [ "$ENV_USER" != "$CANON_USER" ]; then
  set_env_kv MN2_RPC_USER "$CANON_USER"
  FIXED=1
  echo "FIXED .env MN2_RPC_USER -> $(mask_val "$CANON_USER")"
fi
if [ "$ENV_PASS" != "$CANON_PASS" ]; then
  set_env_kv MN2_RPC_PASSWORD "$CANON_PASS"
  FIXED=1
  echo "FIXED .env MN2_RPC_PASSWORD -> $(mask_val "$CANON_PASS")"
fi

# Ensure MN2_RPC_URL present
if ! grep -q '^MN2_RPC_URL=' "$ENV"; then
  set_env_kv MN2_RPC_URL "http://127.0.0.1:9332"
  FIXED=1
  echo "ADDED MN2_RPC_URL to .env"
fi

chown root:www-data "$ENV" "$CONF" 2>/dev/null || true
chmod 640 "$ENV" "$CONF" 2>/dev/null || true

ENV_USER=$(read_kv "$ENV" MN2_RPC_USER)
ENV_PASS=$(read_kv "$ENV" MN2_RPC_PASSWORD)
echo "--- AFTER ---"
echo "conf rpcuser=$(mask_val "$CONF_USER") rpcpassword=$(mask_val "$CONF_PASS")"
echo "env  MN2_RPC_USER=$(mask_val "$ENV_USER") MN2_RPC_PASSWORD=$(mask_val "$ENV_PASS")"
echo "FIXED=$FIXED"

# Check other RPC cred locations
echo "--- OTHER RPC CONFIG LOCATIONS ---"
for f in \
  "$WEB/data/mn2_rpc_failover.json" \
  /root/.masternoder2/masternoder2.conf \
  /var/lib/masternoder2/masternoder2.conf; do
  if [ -f "$f" ]; then
    u=$(read_kv "$f" rpcuser 2>/dev/null || true)
    p=$(read_kv "$f" rpcpassword 2>/dev/null || true)
    uenv=$(grep -o '"user"[[:space:]]*:[[:space:]]*"[^"]*"' "$f" 2>/dev/null | head -1 || true)
    echo "  $f: rpcuser=$(mask_val "$u") rpcpassword=$(mask_val "$p") $uenv"
  fi
done

# Direct RPC test (daemon may need restart if password changed in conf)
echo "--- DIRECT RPC TEST ---"
RPC_OK=0
for attempt in 1 2 3; do
  OUT=$(curl -sS -m 10 -u "$ENV_USER:$ENV_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"align","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ 2>&1) || true
  BC=$(echo "$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result','')); err=d.get('error'); sys.exit(0 if d.get('result') is not None and not err else 1)" 2>/dev/null && echo "$OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))" 2>/dev/null || echo "")
  if echo "$OUT" | grep -q '"result"'; then
    BC=$(echo "$OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))")
    RPC_OK=1
    echo "RPC getblockcount OK height=$BC (attempt $attempt)"
    break
  fi
  if echo "$OUT" | grep -qi '401\|Unauthorized'; then
    echo "RPC 401 on attempt $attempt — will restart daemon if conf was changed"
    if [ "$FIXED" = "1" ]; then
      systemctl restart masternoder2d 2>/dev/null || true
      sleep 15
    else
      break
    fi
  else
    echo "RPC fail attempt $attempt: ${OUT:0:200}"
    sleep 5
  fi
done

# Restart uwsgi + profit-daemon to pick up .env
echo "--- RESTART APP SERVICES ---"
systemctl restart uwsgi-vidgenerator 2>/dev/null || systemctl restart uwsgi 2>/dev/null || true
sleep 4
systemctl restart masternoder-profit-daemon.service 2>/dev/null || true
sleep 2
echo "uwsgi=$(systemctl is-active uwsgi-vidgenerator 2>/dev/null || echo unknown)"
echo "profit-daemon=$(systemctl is-active masternoder-profit-daemon.service 2>/dev/null || echo unknown)"
echo "masternoder2d=$(systemctl is-active masternoder2d 2>/dev/null || echo unknown)"

# Re-test RPC after possible daemon restart
if [ "$RPC_OK" != "1" ]; then
  OUT=$(curl -sS -m 10 -u "$ENV_USER:$ENV_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"align2","method":"getblockcount","params":[]}' \
    http://127.0.0.1:9332/ 2>&1) || true
  if echo "$OUT" | grep -q '"result"'; then
    BC=$(echo "$OUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('result',''))")
    RPC_OK=1
    echo "RPC getblockcount OK after restart height=$BC"
  else
    echo "RPC still failing: ${OUT:0:300}"
  fi
fi

# App API tests (local uwsgi)
echo "--- APP API TESTS ---"
sleep 3
for path in /api/mn2/masternode/health /api/mn2/network-overview; do
  BODY=$(curl -sS -m 20 "http://127.0.0.1:5000${path}" 2>&1) || true
  echo "GET $path -> ${BODY:0:500}"
done

# Masternode wallet queries via RPC
if [ "$RPC_OK" = "1" ]; then
  echo "--- MASTERNODE RPC ---"
  curl -sS -m 10 -u "$ENV_USER:$ENV_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"masternode","params":["count"]}' \
    http://127.0.0.1:9332/ 2>/dev/null | head -c 300; echo
  curl -sS -m 10 -u "$ENV_USER:$ENV_PASS" -H 'content-type: application/json' \
    -d '{"jsonrpc":"1.0","id":"t","method":"getnetworkinfo","params":[]}' \
    http://127.0.0.1:9332/ 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin).get('result',{}); print('network_enabled', d.get('networkactive'), 'connections', d.get('connections'))" 2>/dev/null || true
fi

# Optional CLI test
CLI=/opt/masternoder2d/masternoder2-cli
if [ -x "$CLI" ]; then
  echo "--- CLI TEST ---"
  "$CLI" -datadir="$WEB/config" -rpcuser="$ENV_USER" -rpcpassword="$ENV_PASS" getblockcount 2>&1 | head -1 || true
fi

echo "SUMMARY RPC_OK=$RPC_OK FIXED=$FIXED"
ENDSCRIPT"""


def public_verify() -> dict:
    results = {}
    for name, url in (
        ("masternode_health", "https://masternoder.dk/api/mn2/masternode/health"),
        ("network_overview", "https://masternoder.dk/api/mn2/network-overview"),
        ("system_health", "https://masternoder.dk/api/health/system"),
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AlignRpcAuth/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
            results[name] = {"ok": True, "data": data}
        except Exception as exc:
            results[name] = {"ok": False, "error": str(exc)}
    return results


def summarize_public(results: dict) -> None:
    print("\n=== PUBLIC VERIFICATION ===")
    for name, r in results.items():
        if not r.get("ok"):
            print(f"{name}: FAIL — {r.get('error')}")
            continue
        d = r["data"]
        if name == "masternode_health":
            rpc_err = d.get("rpc_error") or d.get("error")
            print(
                f"masternode/health: success={d.get('success')} "
                f"rpc_ok={not bool(rpc_err)} "
                f"collateral_outputs_available={d.get('collateral_outputs_available')} "
                f"err={str(rpc_err)[:80] if rpc_err else 'none'}"
            )
        elif name == "network_overview":
            daemon = d.get("daemon") or {}
            print(
                f"network-overview: reachable={daemon.get('reachable')} "
                f"block={d.get('block_height')} connections={daemon.get('connections')} "
                f"rpc_error={str(d.get('rpc_error') or '')[:80] or 'none'}"
            )
        elif name == "system_health":
            mn2 = (d.get("components") or {}).get("mn2_rpc") or {}
            print(f"system health mn2_rpc: status={mn2.get('status')} detail={str(mn2.get('detail',''))[:100]}")


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=300)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    ssh.close()

    # Redact any accidental full password lines (belt-and-suspenders)
    out = re.sub(r"(rpcpassword=)(\S+)", lambda m: f"{m.group(1)}{mask(m.group(2))}", out)
    out = re.sub(r"(MN2_RPC_PASSWORD=)(\S+)", lambda m: f"{m.group(1)}{mask(m.group(2))}", out)

    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    if err.strip():
        print("\nSTDERR:", err[:500])

    print("\nWaiting 12s for public endpoints...")
    time.sleep(12)
    pub = public_verify()
    summarize_public(pub)

    rpc_ok = "RPC_OK=1" in out
    fixed = "FIXED=1" in out
    pub_ok = all(r.get("ok") for r in pub.values())
    return 0 if rpc_ok and pub_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
