"""
MasterNoder2 (MN2) JSON-RPC client for deposit/withdraw and chain queries.
Bitcoin-style HTTP JSON-RPC. Credentials from env:
  MN2_RPC_URL      - e.g. http://127.0.0.1:9332 (mainnet) or :19332 (testnet)
  MN2_RPC_USER     - must match the wallet node's rpcuser (required if wallet requires auth)
  MN2_RPC_PASSWORD - must match the wallet node's rpcpassword
If you get HTTP 401: set MN2_RPC_USER and MN2_RPC_PASSWORD in the app environment (e.g. systemd/uwsgi) to the same values as in the MN2 wallet config.
Optional: MN2_PROFILE_LOG=1 to log each call to logs/mn2_rpc.jsonl.
"""
import os
import json
import time
import base64
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

# Default ports: mainnet 9332, testnet 19332 (common convention; confirm in MasterNoder2 repo)
_DEFAULT_URL_MAINNET = "http://127.0.0.1:9332"
_DEFAULT_URL_TESTNET = "http://127.0.0.1:19332"


def _rpc_url() -> str:
    try:
        from backend.services.mn2_rpc_failover import resolve_active_endpoint
        ep = resolve_active_endpoint()
        if ep and ep.get("url"):
            return ep["url"]
    except Exception:
        pass
    url = (os.environ.get("MN2_RPC_URL") or "").strip()
    if url:
        return url
    network = (os.environ.get("MN2_NETWORK") or "").strip().lower()
    return _DEFAULT_URL_TESTNET if network == "testnet" else _DEFAULT_URL_MAINNET


def _rpc_auth() -> tuple:
    try:
        from backend.services.mn2_rpc_failover import resolve_active_endpoint
        ep = resolve_active_endpoint()
        if ep:
            return (ep.get("user") or "").strip(), (ep.get("password") or "").strip()
    except Exception:
        pass
    return (
        (os.environ.get("MN2_RPC_USER") or "").strip(),
        (os.environ.get("MN2_RPC_PASSWORD") or "").strip(),
    )


def _rpc_timeout(default: float = 30.0, *, cap: float = 120.0) -> float:
    try:
        timeout_sec = float((os.environ.get("MN2_RPC_TIMEOUT") or str(default)).strip() or default)
    except (TypeError, ValueError):
        timeout_sec = default
    return max(1.0, min(timeout_sec, cap))


def _parse_rpc_response(status_code: int, body: str) -> Tuple[Optional[Any], Optional[str]]:
    if status_code != 200:
        raw = f"HTTP {status_code}: {body[:200]}" if body else f"HTTP {status_code}"
        if status_code == 401:
            raw = "Wallet RPC authentication failed. Set MN2_RPC_USER and MN2_RPC_PASSWORD to match the wallet node."
        elif status_code == 403:
            raw = "Wallet RPC access forbidden. Check MN2_RPC_USER and MN2_RPC_PASSWORD."
        return None, raw
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        return None, f"invalid_json: {exc}"
    err = data.get("error")
    if err:
        msg = err if isinstance(err, str) else (err.get("message") or str(err))
        return None, msg
    return data.get("result"), None


def _post_json_rpc(
    url: str,
    payload: Dict[str, Any],
    *,
    user: str = "",
    password: str = "",
    timeout_sec: float = 30.0,
) -> Tuple[int, str]:
    """POST JSON-RPC; returns (status_code, response_body_text)."""
    if requests is not None:
        r = requests.post(
            url,
            json=payload,
            auth=(user, password) if user or password else None,
            headers={"Content-Type": "application/json"},
            timeout=timeout_sec,
        )
        return r.status_code, r.text or ""

    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Connection": "close"}
    if user or password:
        cred = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        headers["Authorization"] = f"Basic {cred}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return 0, str(exc)


def probe_endpoint(
    url: str,
    user: str = "",
    password: str = "",
    timeout_sec: Optional[float] = None,
) -> Dict[str, Any]:
    """Health probe for an arbitrary RPC endpoint (failover checks)."""
    if timeout_sec is None:
        try:
            timeout_sec = float((os.environ.get("MN2_RPC_HEALTH_TIMEOUT") or "5").strip() or 5)
        except (TypeError, ValueError):
            timeout_sec = 5.0
    timeout_sec = max(1.0, min(timeout_sec, 25.0))
    t0 = time.perf_counter()
    payload = {"jsonrpc": "1.0", "id": "probe", "method": "getblockcount", "params": []}
    out: Dict[str, Any] = {"status": "unknown", "block_height": None, "latency_ms": None, "error": None, "url": url}
    try:
        status, body = _post_json_rpc(
            url, payload, user=user, password=password, timeout_sec=timeout_sec,
        )
        out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        if status != 200:
            out["status"] = "auth_failed" if status in (401, 403) else "unreachable"
            out["error"] = f"HTTP {status}"
            return out
        result, err = _parse_rpc_response(status, body)
        if err:
            out["status"] = "unreachable"
            out["error"] = err
            return out
        out["block_height"] = int(result)
        out["status"] = "healthy"
        return out
    except Exception as e:
        out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        out["status"] = "unreachable"
        out["error"] = str(e)
        return out


def _profile_log_enabled() -> bool:
    return (os.environ.get("MN2_PROFILE_LOG") or "").strip() in ("1", "true", "yes")


def _write_profile_log(method: str, duration_ms: float, ok: bool, error: Optional[str] = None) -> None:
    if not _profile_log_enabled():
        return
    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(base, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "mn2_rpc.jsonl")
        line = json.dumps({
            "method": method,
            "duration_ms": round(duration_ms, 2),
            "ok": ok,
            "error": error,
        }) + "\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def _call(
    method: str,
    params: Optional[List[Any]] = None,
    *,
    timeout_sec: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Send a single JSON-RPC request. Returns {"result": ...} on success or {"error": "...", "result": None}.
    """
    url = _rpc_url()
    user, password = _rpc_auth()
    params = params if params is not None else []
    timeout = _rpc_timeout() if timeout_sec is None else max(1.0, min(float(timeout_sec), 120.0))
    payload = {"jsonrpc": "1.0", "id": "mn2", "method": method, "params": params}
    t0 = time.perf_counter()
    try:
        status, body = _post_json_rpc(
            url, payload, user=user, password=password, timeout_sec=timeout,
        )
        duration_ms = (time.perf_counter() - t0) * 1000
        if _profile_log_enabled():
            _write_profile_log(method, duration_ms, status == 200)
        result, err = _parse_rpc_response(status, body)
        if err:
            return {"error": err, "result": None}
        return {"result": result, "error": None}
    except Exception as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        if _profile_log_enabled():
            _write_profile_log(method, duration_ms, False, str(e))
        return {"error": str(e), "result": None}


def getblockcount(timeout_sec: Optional[float] = None) -> Dict[str, Any]:
    """Current block height. Use for health check and sync status."""
    if timeout_sec is not None:
        return _call("getblockcount", timeout_sec=timeout_sec)
    return _call("getblockcount")


def getbalance() -> Dict[str, Any]:
    """Wallet total balance (all addresses in the daemon wallet)."""
    return _call("getbalance")


def listunspent(minconf: int = 1, maxconf: int = 9999999) -> Dict[str, Any]:
    """List spendable wallet UTXOs. Used to find 10k MN2 masternode collateral outputs."""
    return _call("listunspent", [int(minconf), int(maxconf)])


def getnewaddress() -> Dict[str, Any]:
    """Generate a new receive address in the daemon wallet."""
    return _call("getnewaddress")


def sendtoaddress(address: str, amount: float) -> Dict[str, Any]:
    """Send MN2 to an address. amount in MN2 (e.g. 1.5)."""
    return _call("sendtoaddress", [address, amount])


def listtransactions(count: int = 100, skip: int = 0) -> Dict[str, Any]:
    """List recent wallet transactions."""
    return _call("listtransactions", ["*", count, skip])


def gettransaction(txid: str) -> Dict[str, Any]:
    """Get transaction details by txid."""
    return _call("gettransaction", [txid])


def validateaddress(address: str) -> Dict[str, Any]:
    """Validate an MN2 address. Not all chains implement this; may return unimplemented."""
    return _call("validateaddress", [address])


def getstakinginfo() -> Dict[str, Any]:
    """PoS staking info (weight, expected time, enabled). May be unimplemented on some chains."""
    return _call("getstakinginfo")


def getmininginfo() -> Dict[str, Any]:
    """Mining/network info incl. difficulty and networkhashps. Used as a network-weight proxy on PoS forks that lack getstakinginfo."""
    return _call("getmininginfo")


def getstakingstatus() -> Dict[str, Any]:
    """PIVX-style staking status booleans (staking status, mnsync, walletunlocked, mintablecoins, ...). Preferred on forks where getstakinginfo is unimplemented."""
    return _call("getstakingstatus")


def getstakingstatus() -> Dict[str, Any]:
    """PIVX-style staking status (staking_status, mintablecoins, walletunlocked, ...).
    This MN2 build implements getstakingstatus rather than getstakinginfo."""
    return _call("getstakingstatus")


def getwalletinfo() -> Dict[str, Any]:
    """Wallet info incl. balance, unconfirmed_balance, immature_balance. May be unimplemented on some chains."""
    return _call("getwalletinfo")


def staking_health() -> Dict[str, Any]:
    """
    Daemon staking health for ops (plan sec.9): is the pool actually minting?
    Reads getstakinginfo + getwalletinfo and normalizes PIVX/Bitcoin-style field names.
    Never raises; returns status='unsupported' if the chain lacks these RPCs.

    status: active | inactive | unsupported | unreachable
    """
    out: Dict[str, Any] = {
        "status": "unsupported",
        "staking_active": None,
        "staking_weight": None,
        "net_stake_weight": None,
        "expected_time_to_reward_sec": None,
        "mature_balance": None,
        "immature_balance": None,
        "unconfirmed_balance": None,
        "errors": None,
    }
    _CONN = ("connection refused", "timed out", "timeout", "unreachable", "failed to establish")
    si = getstakinginfo()
    if si.get("error"):
        el = str(si["error"]).lower()
        if any(x in el for x in _CONN):
            out["status"] = "unreachable"
            out["errors"] = si["error"]
            return out
        # getstakinginfo not implemented on this build -> fall back to PIVX getstakingstatus
        ss = getstakingstatus()
        if ss.get("error"):
            sl = str(ss["error"]).lower()
            if any(x in sl for x in _CONN):
                out["status"] = "unreachable"
                out["errors"] = ss["error"]
                return out
            out["errors"] = ss["error"]  # neither RPC available -> stays unsupported
        else:
            r = ss.get("result") or {}
            if isinstance(r, dict):
                # PIVX-style flags; some forks use "staking status" / "staking_status"
                active = bool(r.get("staking_status", r.get("staking status")))
                out["staking_active"] = active
                out["mnsync"] = r.get("mnsync")
                out["mintable_coins"] = r.get("mintablecoins")
                out["wallet_unlocked"] = r.get("walletunlocked")
                out["have_connections"] = r.get("haveconnections")
                out["walletunlocked"] = r.get("walletunlocked")
                out["enough_coins"] = r.get("enoughcoins")
                out["status"] = "active" if active else "inactive"
    else:
        r = si.get("result") or {}
        if isinstance(r, dict):
            enabled = r.get("enabled")
            staking = r.get("staking")
            active = bool(staking) if staking is not None else bool(enabled)
            out["staking_active"] = active
            out["staking_weight"] = r.get("weight")
            out["net_stake_weight"] = r.get("netstakeweight") or r.get("netstakewight")
            out["expected_time_to_reward_sec"] = r.get("expectedtime")
            out["errors"] = r.get("errors") or out["errors"]
            out["status"] = "active" if active else "inactive"

    # PIVX-style fork fallback: getstakinginfo missing -> use getstakingstatus booleans.
    if out["status"] == "unsupported":
        ss = getstakingstatus()
        if not ss.get("error") and isinstance(ss.get("result"), dict):
            r = ss["result"]
            active = bool(r.get("staking status", r.get("staking_status")))
            out["staking_active"] = active
            out["mnsync"] = r.get("mnsync")
            out["have_connections"] = r.get("haveconnections")
            out["walletunlocked"] = r.get("walletunlocked")
            out["status"] = "active" if active else "inactive"
            out["staking_status_detail"] = {
                "validtime": r.get("validtime"),
                "haveconnections": r.get("haveconnections"),
                "walletunlocked": r.get("walletunlocked"),
                "mintablecoins": r.get("mintablecoins"),
                "enoughcoins": r.get("enoughcoins"),
                "mnsync": r.get("mnsync"),
            }

    wi = getwalletinfo()
    if not wi.get("error"):
        w = wi.get("result") or {}
        if isinstance(w, dict):
            out["mature_balance"] = w.get("balance")
            out["immature_balance"] = w.get("immature_balance")
            out["unconfirmed_balance"] = w.get("unconfirmed_balance")
    return out


def getmasternodecount() -> Dict[str, Any]:
    """Masternode count. May be unimplemented on some chains."""
    return _call("getmasternodecount")


def listmasternodes() -> Dict[str, Any]:
    """Full masternode list (PIVX-style): rank, addr, status, lastpaid, activetime, version."""
    return _call("listmasternodes")


def masternode_command(*args: Any) -> Dict[str, Any]:
    """PIVX-style masternode subcommands (genkey, start, outputs, ...)."""
    return _call("masternode", list(args))


def walletpassphrase(passphrase: str, timeout_sec: int = 120, staking_only: bool = True) -> Dict[str, Any]:
    return _call("walletpassphrase", [passphrase, int(timeout_sec), bool(staking_only)])


def getbestblockhash() -> Dict[str, Any]:
    """Hash of the current chain tip."""
    return _call("getbestblockhash")


def getblockhash(height: int) -> Dict[str, Any]:
    """Block hash at a given height."""
    return _call("getblockhash", [int(height)])


def getblock(block_hash: str, verbosity: int = 1) -> Dict[str, Any]:
    """Block details. verbosity=1 returns tx ids only (light); pass the hash from getblockhash."""
    return _call("getblock", [str(block_hash), int(verbosity)])


def gettxoutsetinfo() -> Dict[str, Any]:
    """UTXO set summary incl. `total_amount` (circulating supply) and `height`. Can be slow on big chains."""
    return _call("gettxoutsetinfo")


def getdifficulty() -> Dict[str, Any]:
    """Network difficulty (may return a dict with PoW/PoS on hybrid chains)."""
    return _call("getdifficulty")


def getconnectioncount(timeout_sec: Optional[float] = None) -> Dict[str, Any]:
    """Number of peers the daemon is connected to. Cheap network-health signal."""
    return _call("getconnectioncount", timeout_sec=timeout_sec)


def getnetworkinfo() -> Dict[str, Any]:
    """Daemon network info: version, subversion, protocolversion, connections."""
    return _call("getnetworkinfo")


def getmempoolinfo() -> Dict[str, Any]:
    """Mempool summary: size (tx count), bytes, usage. May be unimplemented on some forks."""
    return _call("getmempoolinfo")


def getblockchaininfo() -> Dict[str, Any]:
    """Chain summary: chain, blocks, headers, verificationprogress, mediantime, size_on_disk."""
    return _call("getblockchaininfo")


def getinfo() -> Dict[str, Any]:
    """Legacy/PIVX getinfo: version, protocolversion, connections, moneysupply, difficulty."""
    return _call("getinfo")


def health_check() -> Dict[str, Any]:
    """
    Lightweight health check: call getblockcount and return status, block_height, latency_ms.
    For use in /api/health/system. Does not raise; returns dict with status and optional error.

    status values:
      healthy — RPC returned a block height
      auth_failed — HTTP 401/403 or message indicates bad MN2_RPC_USER / MN2_RPC_PASSWORD
      unreachable — connection error, timeout, or other RPC failure
    """
    t0 = time.perf_counter()
    user_set = bool((os.environ.get("MN2_RPC_USER") or "").strip())
    password_set = bool((os.environ.get("MN2_RPC_PASSWORD") or "").strip())
    out: Dict[str, Any] = {
        "status": "unknown",
        "block_height": None,
        "latency_ms": None,
        "error": None,
        "credentials": {"user_set": user_set, "password_set": password_set},
    }
    try:
        hc_to = float((os.environ.get("MN2_RPC_HEALTH_TIMEOUT") or "5").strip() or 5)
    except (TypeError, ValueError):
        hc_to = 5.0
    hc_to = max(1.0, min(hc_to, 25.0))
    r = getblockcount(timeout_sec=hc_to)
    out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    if r.get("error"):
        err = str(r["error"])
        out["error"] = err
        el = err.lower()
        if (
            "authentication failed" in el
            or "access forbidden" in el
            or "http 401" in el
            or "http 403" in el
        ):
            out["status"] = "auth_failed"
        elif any(x in el for x in ("connection refused", "connection aborted", "timed out", "timeout", "name or service not known", "failed to establish")):
            out["status"] = "unreachable"
        else:
            out["status"] = "unreachable"
        return out
    try:
        out["block_height"] = int(r["result"])
        out["status"] = "healthy"
    except (TypeError, ValueError):
        out["block_height"] = r.get("result")
        out["status"] = "healthy"
    return out
