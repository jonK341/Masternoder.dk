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
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None

# Default ports: mainnet 9332, testnet 19332 (common convention; confirm in MasterNoder2 repo)
_DEFAULT_URL_MAINNET = "http://127.0.0.1:9332"
_DEFAULT_URL_TESTNET = "http://127.0.0.1:19332"


def _rpc_url() -> str:
    url = (os.environ.get("MN2_RPC_URL") or "").strip()
    if url:
        return url
    network = (os.environ.get("MN2_NETWORK") or "").strip().lower()
    return _DEFAULT_URL_TESTNET if network == "testnet" else _DEFAULT_URL_MAINNET


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
    if requests is None:
        return {"error": "requests not installed", "result": None}
    url = _rpc_url()
    user = (os.environ.get("MN2_RPC_USER") or "").strip()
    password = (os.environ.get("MN2_RPC_PASSWORD") or "").strip()
    params = params if params is not None else []
    if timeout_sec is None:
        try:
            timeout_sec = float((os.environ.get("MN2_RPC_TIMEOUT") or "30").strip() or 30)
        except (TypeError, ValueError):
            timeout_sec = 30.0
    timeout_sec = max(1.0, min(timeout_sec, 120.0))
    payload = {"jsonrpc": "1.0", "id": "mn2", "method": method, "params": params}
    t0 = time.perf_counter()
    try:
        r = requests.post(
            url,
            json=payload,
            auth=(user, password) if user or password else None,
            headers={"Content-Type": "application/json"},
            timeout=timeout_sec,
        )
        duration_ms = (time.perf_counter() - t0) * 1000
        if _profile_log_enabled():
            _write_profile_log(method, duration_ms, r.status_code == 200)
        if r.status_code != 200:
            raw = f"HTTP {r.status_code}: {r.text[:200]}" if r.text else f"HTTP {r.status_code}"
            if r.status_code == 401:
                raw = "Wallet RPC authentication failed. Set MN2_RPC_USER and MN2_RPC_PASSWORD to match the wallet node."
            elif r.status_code == 403:
                raw = "Wallet RPC access forbidden. Check MN2_RPC_USER and MN2_RPC_PASSWORD."
            return {"error": raw, "result": None}
        data = r.json()
        err = data.get("error")
        if err:
            msg = err if isinstance(err, str) else (err.get("message") or str(err))
            return {"error": msg, "result": None}
        return {"result": data.get("result"), "error": None}
    except requests.exceptions.RequestException as e:
        duration_ms = (time.perf_counter() - t0) * 1000
        if _profile_log_enabled():
            _write_profile_log(method, duration_ms, False, str(e))
        return {"error": str(e), "result": None}
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
    si = getstakinginfo()
    if si.get("error"):
        el = str(si["error"]).lower()
        if any(x in el for x in ("connection refused", "timed out", "timeout", "unreachable", "failed to establish")):
            out["status"] = "unreachable"
            out["errors"] = si["error"]
            return out
        # method not found / unimplemented -> leave unsupported
        out["errors"] = si["error"]
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


def getdifficulty() -> Dict[str, Any]:
    """Network difficulty (may return a dict with PoW/PoS on hybrid chains)."""
    return _call("getdifficulty")


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
