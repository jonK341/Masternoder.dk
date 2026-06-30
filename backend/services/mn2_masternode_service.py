"""
MN2 masternode hosting — platform-operated masternodes on the shared production daemon.

One masternoder2d datadir hosts N masternodes (PIVX-style); each requires a 5,000 MN2
collateral UTXO in the ops wallet. Registry in data/mn2_masternode_hosts.json; config in
data/mn2_masternode_config.json.

Never raises into request handlers; ops mutations return {success, error}.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger(__name__)
_LOCK = threading.RLock()
_COLLATERAL_MN2 = 5000.0
_CONFIG_FILE = "mn2_masternode_config.json"
_HOSTS_FILE = "mn2_masternode_hosts.json"


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _data_path(name: str) -> str:
    return os.path.join(_base(), "data", name)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def get_config() -> Dict[str, Any]:
    cfg = _read_json(_data_path(_CONFIG_FILE))
    cfg.setdefault("enabled", True)
    cfg.setdefault("collateral_mn2", _COLLATERAL_MN2)
    cfg.setdefault("max_hosted_nodes", 3)
    return cfg


def _load_hosts_doc() -> Dict[str, Any]:
    doc = _read_json(_data_path(_HOSTS_FILE))
    hosts = doc.get("hosts")
    if not isinstance(hosts, list):
        hosts = []
    return {"hosts": hosts, "updated_at": doc.get("updated_at")}


def _save_hosts_doc(hosts: List[Dict[str, Any]]) -> None:
    _write_json(_data_path(_HOSTS_FILE), {"hosts": hosts, "updated_at": _iso()})


def _parse_iso_ts(value: Optional[str]) -> Optional[datetime]:
    s = (value or "").strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _host_reserves_slot(host: Dict[str, Any]) -> bool:
    """Hosts that consume checkout capacity (excludes stuck empty provisioning rows)."""
    st = (host.get("status") or "").lower()
    if st in ("active", "queued", "planned"):
        return True
    if st == "provisioning":
        return bool(host.get("collateral_txid"))
    return False


def _count_slots_used(hosts: List[Dict[str, Any]]) -> int:
    return sum(1 for h in hosts if isinstance(h, dict) and _host_reserves_slot(h))


def purge_stale_provisioning_hosts(
    max_age_hours: float = 6,
    *,
    force_no_collateral: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Drop provisioning rows with no collateral (failed checkout ghosts)."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max(0.0, float(max_age_hours)))
    removed: List[str] = []
    with _LOCK:
        doc = _load_hosts_doc()
        hosts: List[Dict[str, Any]] = list(doc.get("hosts") or [])
        kept: List[Dict[str, Any]] = []
        for h in hosts:
            if not isinstance(h, dict):
                continue
            st = (h.get("status") or "").lower()
            hid = str(h.get("id") or "")
            if st != "provisioning" or h.get("collateral_txid"):
                kept.append(h)
                continue
            if force_no_collateral:
                removed.append(hid)
                continue
            ts = _parse_iso_ts(h.get("created_at") or h.get("updated_at"))
            if ts is None or ts <= cutoff:
                removed.append(hid)
            else:
                kept.append(h)
        if not dry_run and removed:
            _save_hosts_doc(kept)
    return {
        "success": True,
        "dry_run": dry_run,
        "removed": removed,
        "removed_count": len(removed),
        "registry_count": len(kept) if not dry_run else len(hosts) - len(removed),
        "slots_used": _count_slots_used(kept if not dry_run else [h for h in hosts if h.get("id") not in removed]),
    }


def list_hosts(include_internal: bool = False) -> List[Dict[str, Any]]:
    """Platform registry entries (may differ from live on-chain until broadcast)."""
    hosts = _load_hosts_doc().get("hosts") or []
    out: List[Dict[str, Any]] = []
    for h in hosts:
        if not isinstance(h, dict):
            continue
        row = dict(h)
        if not include_internal:
            row.pop("collateral_txid", None)
            row.pop("masternode_privkey", None)
            row.pop("notes", None)
        out.append(row)
    return out


def list_collateral_outputs() -> Dict[str, Any]:
    """10k MN2 UTXOs in the daemon wallet (candidates for new masternodes). Ops use."""
    collateral = float(get_config().get("collateral_mn2") or _COLLATERAL_MN2)
    try:
        from backend.services import mn2_rpc_client as rpc
        r = rpc.listunspent(1, 9999999)
        if r.get("error"):
            return {"success": False, "error": r["error"], "outputs": []}
        rows = r.get("result")
        if not isinstance(rows, list):
            rows = []
        by_key: Dict[tuple, Dict[str, Any]] = {}
        for utxo in rows:
            if not isinstance(utxo, dict):
                continue
            amt = float(utxo.get("amount") or 0)
            if abs(amt - collateral) > 1e-8:
                continue
            key = (str(utxo.get("txid")), int(utxo.get("vout")))
            by_key[key] = {
                "txid": key[0],
                "vout": key[1],
                "amount": amt,
                "address": utxo.get("address"),
                "confirmations": utxo.get("confirmations"),
                "locked": False,
            }
        locked_r = rpc.listlockunspent()
        locked_rows = locked_r.get("result") if not locked_r.get("error") else []
        if isinstance(locked_rows, list):
            for item in locked_rows:
                if not isinstance(item, dict):
                    continue
                key = (str(item.get("txid")), int(item.get("vout")))
                if key in by_key:
                    by_key[key]["locked"] = True
                    continue
                detail = rpc.gettxout(key[0], key[1])
                if detail.get("error") or not isinstance(detail.get("result"), dict):
                    continue
                val = float(detail["result"].get("value") or 0)
                if abs(val - collateral) > 1e-8:
                    continue
                spk = detail["result"].get("scriptPubKey") or {}
                addr = None
                addrs = spk.get("addresses")
                if isinstance(addrs, list) and addrs:
                    addr = addrs[0]
                by_key[key] = {
                    "txid": key[0],
                    "vout": key[1],
                    "amount": val,
                    "address": addr,
                    "confirmations": detail["result"].get("confirmations"),
                    "locked": True,
                }
        outputs = list(by_key.values())
        return {
            "success": True,
            "collateral_mn2": collateral,
            "count": len(outputs),
            "outputs": outputs,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "outputs": []}


def network_masternodes(limit: int = 50, *, fresh: bool = False) -> Dict[str, Any]:
    try:
        from backend.services import mn2_explorer_data
        data = mn2_explorer_data.masternodes(limit=limit, fresh=fresh)
        return {"success": True, **data}
    except Exception as exc:
        return {"success": False, "error": str(exc), "total": 0, "enabled": 0, "list": []}


def _match_on_chain(host: Dict[str, Any], chain_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    txid = (host.get("collateral_txid") or "").strip()
    if txid:
        for mn in chain_rows:
            if not isinstance(mn, dict):
                continue
            m_tx = str(mn.get("txhash") or mn.get("proTxHash") or "")
            if m_tx and m_tx == txid:
                return mn
    coll_addr = (host.get("collateral_address") or "").strip()
    if coll_addr:
        for mn in chain_rows:
            if not isinstance(mn, dict):
                continue
            if str(mn.get("addr") or "") == coll_addr:
                return mn
    addr = (host.get("broadcast_address") or host.get("masternode_address") or "").strip()
    if not addr:
        return None
    host_ip = addr.split(":")[0] if ":" in addr else addr
    for mn in chain_rows:
        mn_addr = str(mn.get("addr") or "")
        if mn_addr == addr or mn_addr.startswith(host_ip):
            return mn
    return None


def register_host(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ops: add or update a platform-hosted masternode record."""
    label = (payload.get("label") or "").strip()
    if not label:
        return {"success": False, "error": "label required"}

    cfg = get_config()
    max_nodes = int(cfg.get("max_hosted_nodes") or 3)
    with _LOCK:
        doc = _load_hosts_doc()
        hosts: List[Dict[str, Any]] = list(doc.get("hosts") or [])
        host_id = (payload.get("id") or "").strip() or ("mn-" + uuid.uuid4().hex[:10])
        existing_idx = next((i for i, h in enumerate(hosts) if h.get("id") == host_id), None)

        row = {
            "id": host_id,
            "label": label,
            "status": (payload.get("status") or "planned").strip().lower(),
            "collateral_address": (payload.get("collateral_address") or "").strip() or None,
            "collateral_txid": (payload.get("collateral_txid") or "").strip() or None,
            "collateral_vout": payload.get("collateral_vout"),
            "broadcast_address": (payload.get("broadcast_address") or payload.get("masternode_address") or "").strip() or None,
            "owner_user_id": (payload.get("owner_user_id") or "").strip() or None,
            "notes": (payload.get("notes") or "").strip() or None,
            "updated_at": _iso(),
        }
        if existing_idx is None:
            slots_used = _count_slots_used(hosts)
            if slots_used >= max_nodes:
                return {
                    "success": False,
                    "error": "max_hosted_nodes reached (%d)" % max_nodes,
                    "max_hosted_nodes": max_nodes,
                    "slots_used": slots_used,
                }
            row["created_at"] = _iso()
            hosts.append(row)
        else:
            prev = hosts[existing_idx]
            row["created_at"] = prev.get("created_at") or _iso()
            hosts[existing_idx] = row

        _save_hosts_doc(hosts)
        return {"success": True, "host": row, "hosted_count": len(hosts)}


def remove_host(host_id: str) -> Dict[str, Any]:
    host_id = (host_id or "").strip()
    if not host_id:
        return {"success": False, "error": "id required"}
    with _LOCK:
        doc = _load_hosts_doc()
        hosts = [h for h in (doc.get("hosts") or []) if isinstance(h, dict) and h.get("id") != host_id]
        if len(hosts) == len(doc.get("hosts") or []):
            return {"success": False, "error": "host not found"}
        _save_hosts_doc(hosts)
        return {"success": True, "removed": host_id, "hosted_count": len(hosts)}


def _ops_cfg() -> Dict[str, Any]:
    cfg = get_config()
    ops = cfg.get("ops") if isinstance(cfg.get("ops"), dict) else {}
    return ops


def _masternode_conf_path() -> str:
    ops = _ops_cfg()
    datadir = (ops.get("datadir") or os.environ.get("MN2_DATADIR") or "/var/www/html/config").strip()
    return os.path.join(datadir, "masternode.conf")


def _strip_masternode_conf_comment(line: str) -> str:
    """Drop trailing # comments; field values must not contain spaces."""
    return line.split("#", 1)[0].strip()


def _is_valid_masternode_conf_parts(parts: List[str]) -> bool:
    """
    PIVX/MN2 line: alias IP:port masternodeprivkey collateral_txid collateral_index (5 fields).
    Rejects legacy malformed rows (privkey before IP, missing vout, etc.).
    """
    if len(parts) != 5:
        return False
    alias, ip_port, privkey, txid, vout_s = parts
    if not alias or any(ch.isspace() for ch in alias):
        return False
    if ":" not in ip_port:
        return False
    _, _, port = ip_port.rpartition(":")
    if not port.isdigit():
        return False
    if not privkey or not txid:
        return False
    try:
        if int(vout_s) < 0:
            return False
    except (TypeError, ValueError):
        return False
    return True


def _parse_masternode_conf_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse one masternode.conf row; None for blanks/comments."""
    raw = line.rstrip("\n")
    stripped = _strip_masternode_conf_comment(raw)
    if not stripped:
        return None
    if stripped.startswith("#"):
        return {"kind": "comment", "raw": raw}
    parts = stripped.split()
    if not parts:
        return None
    valid = _is_valid_masternode_conf_parts(parts)
    entry: Dict[str, Any] = {
        "kind": "entry",
        "raw": raw,
        "alias": parts[0],
        "parts": parts,
        "valid": valid,
    }
    if valid:
        entry["ip_port"] = parts[1]
        entry["privkey"] = parts[2]
        entry["txid"] = parts[3]
        entry["vout"] = int(parts[4])
    return entry


def _format_masternode_conf_line(alias: str, ip_port: str, privkey: str, txid: str, vout: int) -> str:
    return f"{alias} {ip_port} {privkey} {txid} {vout}\n"


def _alias_from_host_id(host_id: str) -> str:
    """
    Daemon masternode aliases must be a single token (no spaces).
    Host ids may include dashes and display names with spaces (e.g. user-Sander S-597747).
    """
    alias = re.sub(r"[^a-zA-Z0-9]", "", (host_id or "").strip())[:16]
    if alias:
        return alias
    return "mn" + uuid.uuid4().hex[:14]


def _validate_masternode_conf_fields(alias: str, ip_port: str, txid: str, vout: int, privkey: str) -> None:
    alias = (alias or "").strip()
    ip_port = (ip_port or "").strip()
    privkey = (privkey or "").strip()
    txid = (txid or "").strip()
    if not alias or any(ch.isspace() for ch in alias):
        raise ValueError(f"invalid masternode alias (no spaces allowed): {alias!r}")
    parts = [alias, ip_port, privkey, txid, str(int(vout))]
    if not _is_valid_masternode_conf_parts(parts):
        raise ValueError(
            f"invalid masternode.conf fields for {alias!r}: expected "
            f"'alias IP:port privkey txid vout', got {parts!r}"
        )


def _read_masternode_conf_entries() -> List[Dict[str, Any]]:
    path = _masternode_conf_path()
    rows: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return rows
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parsed = _parse_masternode_conf_line(line)
                if parsed is not None:
                    rows.append(parsed)
    except OSError:
        return []
    return rows


def _entry_for_alias(alias: str, *, valid_only: bool = True) -> Optional[Dict[str, Any]]:
    alias = (alias or "").strip()
    if not alias:
        return None
    match: Optional[Dict[str, Any]] = None
    for row in _read_masternode_conf_entries():
        if row.get("kind") != "entry" or row.get("alias") != alias:
            continue
        if valid_only and not row.get("valid"):
            continue
        match = row
    return match


def repair_masternode_conf(*, dry_run: bool = False) -> Dict[str, Any]:
    """
    Dedupe masternode.conf by alias; drop malformed duplicate rows.
    Keeps the last valid line per alias; removes invalid rows for aliases that have a valid line.
    """
    path = _masternode_conf_path()
    rows = _read_masternode_conf_entries()
    if not rows and not os.path.isfile(path):
        return {"success": True, "changed": False, "path": path, "removed": [], "kept": []}

    by_alias: Dict[str, List[Dict[str, Any]]] = {}
    preamble: List[str] = []
    for row in rows:
        if row.get("kind") == "comment":
            preamble.append(row["raw"])
            continue
        alias = row.get("alias")
        if not alias:
            continue
        by_alias.setdefault(str(alias), []).append(row)

    kept_entries: List[Dict[str, Any]] = []
    removed: List[str] = []
    kept: List[str] = []

    for alias, items in by_alias.items():
        valids = [i for i in items if i.get("valid")]
        if valids:
            chosen = valids[-1]
            for item in items:
                if item is not chosen:
                    removed.append(_strip_masternode_conf_comment(item["raw"]))
            kept_entries.append(chosen)
            kept.append(alias)
            continue
        # No valid line — keep the last row so ops can see/fix manually, but only one.
        chosen = items[-1]
        for item in items[:-1]:
            removed.append(_strip_masternode_conf_comment(item["raw"]))
        kept_entries.append(chosen)
        kept.append(alias)

    new_lines: List[str] = []
    if preamble:
        new_lines.extend(f"{ln}\n" if not ln.endswith("\n") else ln for ln in preamble)
    for entry in kept_entries:
        if entry.get("valid"):
            new_lines.append(
                _format_masternode_conf_line(
                    entry["alias"],
                    entry["ip_port"],
                    entry["privkey"],
                    entry["txid"],
                    int(entry["vout"]),
                )
            )
        else:
            new_lines.append(entry["raw"] + ("\n" if not str(entry["raw"]).endswith("\n") else ""))

    new_body = "".join(new_lines)
    old_body = ""
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                old_body = f.read()
        except OSError:
            old_body = ""

    changed = new_body != old_body
    if changed and not dry_run:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new_body)
        os.replace(tmp, path)

    return {
        "success": True,
        "changed": changed,
        "dry_run": dry_run,
        "path": path,
        "removed": removed,
        "kept": kept,
    }


def _masternoder2_conf_path() -> str:
    ops = _ops_cfg()
    datadir = (ops.get("datadir") or os.environ.get("MN2_DATADIR") or "/var/www/html/config").strip()
    return os.path.join(datadir, "masternoder2.conf")


def _privkey_for_alias(alias: str) -> Optional[str]:
    """Read masternode private key from masternode.conf for an existing alias (valid lines only)."""
    row = _entry_for_alias(alias, valid_only=True)
    if not row:
        return None
    return str(row.get("privkey") or "")


def _primary_ping_privkey() -> Optional[str]:
    """Private key for the daemon ping loop (``primary_ping_alias`` in masternode.conf)."""
    alias = _primary_ping_alias()
    if not alias:
        return None
    return _privkey_for_alias(alias)


def _read_masternoder2_privkey() -> Optional[str]:
    path = _masternoder2_conf_path()
    if not os.path.isfile(path):
        return None
    keys: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("masternodeprivkey="):
                    keys.append(line.split("=", 1)[1].strip())
    except OSError:
        return None
    if not keys:
        return None
    distinct = {k for k in keys if k}
    if len(distinct) > 1:
        _LOGGER.warning(
            "masternoder2.conf has conflicting masternodeprivkey lines (%d distinct)",
            len(distinct),
        )
    if len(keys) > 1:
        _LOGGER.warning(
            "masternoder2.conf has %d duplicate masternodeprivkey lines — normalize via "
            "scripts/mn2_fix_daemon_privkey.sh",
            len(keys),
        )
    return keys[-1]


def _parse_daemon_version_tuple(version: str) -> tuple:
    """Parse ``1.3.0.0-abc`` → ``(1, 3, 0, 0)`` for comparisons."""
    head = str(version or "").split("-", 1)[0].strip()
    parts: List[int] = []
    for piece in head.split("."):
        try:
            parts.append(int(piece))
        except (TypeError, ValueError):
            break
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def daemon_supports_multi_ping() -> bool:
    """True when connected daemon reports MasterNoder2 >= 1.3.0."""
    try:
        from backend.services import mn2_rpc_client as rpc

        r = rpc.getinfo()
        if r.get("error"):
            return False
        ver = (r.get("result") or {}).get("version")
        if ver is None:
            return False
        return _parse_daemon_version_tuple(str(ver)) >= (1, 3, 0, 0)
    except Exception:
        return False


def multi_ping_enabled() -> bool:
    """
    Fleet multi-ping: ping every masternode.conf alias from one daemon (v1.3+).
    ``ops.multi_ping_enabled`` overrides auto-detect; default False until binary deployed.
    """
    ops = _ops_cfg()
    flag = ops.get("multi_ping_enabled")
    if flag is True:
        return True
    if flag is False:
        return False
    env = (os.environ.get("MN2_MULTI_PING_ENABLED") or "").strip().lower()
    if env in ("1", "true", "yes"):
        return True
    if env in ("0", "false", "no"):
        return False
    return daemon_supports_multi_ping()


def _register_fleet_ping_targets() -> Optional[str]:
    """Broadcast + register all masternode.conf aliases in daemon ping set (v1.3+)."""
    if not multi_ping_enabled():
        return None
    from backend.services import mn2_rpc_client as rpc

    _unlock_wallet()
    _unlock_collateral_utxos()
    r = rpc.startmasternode("all", False)
    if r.get("error"):
        return str(r.get("error"))
    return None


def _collateral_for_alias(alias: str) -> Optional[tuple]:
    """Return (txid, vout) from masternode.conf for alias (valid lines only)."""
    row = _entry_for_alias(alias, valid_only=True)
    if not row:
        return None
    try:
        return (str(row["txid"]), int(row["vout"]))
    except (KeyError, TypeError, ValueError):
        return None


def _count_enabled_with_activetime(chain_list: List[Dict[str, Any]]) -> int:
    """Count ENABLED masternodes with activetime > 0 (multi-ping health)."""
    n = 0
    for mn in chain_list:
        if not isinstance(mn, dict):
            continue
        if str(mn.get("status") or "").upper() != "ENABLED":
            continue
        try:
            if int(mn.get("activetime") or 0) > 0:
                n += 1
        except (TypeError, ValueError):
            continue
    return n


def _primary_ping_alias() -> Optional[str]:
    """Alias whose privkey runs the daemon ping loop (activetime / ENABLED)."""
    ops = _ops_cfg()
    configured = (ops.get("primary_ping_alias") or os.environ.get("MN2_PRIMARY_PING_ALIAS") or "").strip()
    if configured:
        return configured
    path = _masternode_conf_path()
    if os.path.isfile(path):
        try:
            for row in _read_masternode_conf_entries():
                if row.get("kind") != "entry" or not row.get("valid"):
                    continue
                alias = str(row.get("alias") or "")
                if alias.startswith("platformmn"):
                    return alias
        except OSError:
            pass
    hosts = list_hosts(include_internal=True)
    for h in hosts:
        if not isinstance(h, dict):
            continue
        hid = str(h.get("id") or "")
        if hid.startswith("platform-mn-"):
            return hid.replace("-", "")[:16]
    return None


def _unlock_collateral_utxos() -> int:
    """Unlock wallet-locked UTXOs so startmasternode can see collateral."""
    from backend.services import mn2_rpc_client as rpc

    locked_r = rpc.listlockunspent()
    if locked_r.get("error"):
        return 0
    rows = locked_r.get("result")
    if not isinstance(rows, list) or not rows:
        return 0
    outputs = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        txid = item.get("txid")
        vout = item.get("vout")
        if txid is None or vout is None:
            continue
        outputs.append({"txid": str(txid), "vout": int(vout)})
    if not outputs:
        return 0
    rpc.lockunspent(True, outputs)
    return len(outputs)


def _ping_watch_path() -> str:
    return _data_path("mn2_ping_watch.json")


def _read_ping_watch() -> Dict[str, Any]:
    return _read_json(_ping_watch_path())


def _write_ping_watch(activetime: int) -> None:
    _write_json(_ping_watch_path(), {"activetime": int(activetime), "ts": _iso()})


def _max_enabled_activetime() -> int:
    net = network_masternodes(limit=100)
    rows = net.get("list") if isinstance(net.get("list"), list) else []
    best = 0
    for mn in rows:
        if not isinstance(mn, dict):
            continue
        if str(mn.get("status") or "").upper() != "ENABLED":
            continue
        try:
            best = max(best, int(mn.get("activetime") or 0))
        except (TypeError, ValueError):
            continue
    return best


def _primary_ping_activetime() -> int:
    """
    Activetime for ``primary_ping_alias`` collateral on chain — not the max across all ENABLED nodes.
    Returns 0 when the primary row is missing, not ENABLED, or has no rising ping yet.
    """
    alias = _primary_ping_alias()
    collateral = _collateral_for_alias(alias) if alias else None
    if not collateral:
        return _max_enabled_activetime()

    want_txid = str(collateral[0]).lower()
    net = network_masternodes(limit=100)
    rows = net.get("list") if isinstance(net.get("list"), list) else []
    for mn in rows:
        if not isinstance(mn, dict):
            continue
        tx = str(mn.get("txhash") or mn.get("proTxHash") or "").lower()
        if tx != want_txid:
            continue
        if str(mn.get("status") or "").upper() != "ENABLED":
            return 0
        try:
            return max(0, int(mn.get("activetime") or 0))
        except (TypeError, ValueError):
            return 0
    return 0


def _ping_loop_healthy() -> bool:
    """
    True when primary_ping_alias collateral is ENABLED and activetime is rising.
    Ignores other ENABLED nodes (stale/wrong collateral on the same network list).
    """
    ops = _ops_cfg()
    try:
        stall_min = int(ops.get("ping_stall_minutes") or 8)
    except (TypeError, ValueError):
        stall_min = 8

    current = _primary_ping_activetime()
    if current <= 0:
        return False

    prev = _read_ping_watch()
    prev_act = prev.get("activetime")
    prev_ts = _parse_iso_ts(prev.get("ts"))

    if prev_act is None:
        _write_ping_watch(current)
        return False

    if current > int(prev_act):
        _write_ping_watch(current)
        return True

    if prev_ts is None:
        _write_ping_watch(current)
        return False

    age_min = (datetime.now(timezone.utc) - prev_ts).total_seconds() / 60.0
    if age_min < stall_min:
        return True

    return False


def _sync_masternode_daemon_privkey() -> tuple:
    """
    Ensure ``masternoder2.conf`` ping privkey matches ``primary_ping_alias`` (not the alias
    being started). The daemon ping loop must always use the primary node key.

    Returns ``(conf_changed, error)``:
    - ``conf_changed`` True only when the file was successfully rewritten (restart daemon).
    - ``error`` set when a mismatch exists but the file could not be written (e.g. www-data).
    """
    privkey = (_primary_ping_privkey() or "").strip()
    if not privkey:
        alias = _primary_ping_alias() or "?"
        return False, f"no privkey for primary_ping_alias {alias} in masternode.conf"

    path = _masternoder2_conf_path()
    ops = _ops_cfg()
    external_ip = (os.environ.get("MN2_MASTERNODE_BROADCAST_IP") or ops.get("external_ip") or "140.82.39.124").strip()
    try:
        port = int(os.environ.get("MN2_MASTERNODE_PORT") or ops.get("masternode_port") or 17646)
    except (TypeError, ValueError):
        port = 17646
    ping_addr = (
        os.environ.get("MN2_MASTERNODE_PING_ADDR")
        or ops.get("masternode_ping_addr")
        or f"127.0.0.1:{port}"
    ).strip()

    lines: List[str] = []
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError as exc:
            return False, f"cannot read {path}: {exc}"

    drop_prefixes = (
        "listen=", "port=", "externalip=", "masternode=1", "masternodeprivkey=", "masternodeaddr=",
    )
    kept = [ln for ln in lines if not any(ln.startswith(p) for p in drop_prefixes)]
    block = [
        "listen=1",
        f"port={port}",
        f"externalip={external_ip}",
        "masternode=1",
        f"masternodeprivkey={privkey}",
        f"masternodeaddr={ping_addr}",
    ]
    new_body = "\n".join(kept + block) + "\n"
    old_body = "\n".join(lines) + ("\n" if lines else "")
    if new_body == old_body:
        return False, None

    current = _read_masternoder2_privkey()
    if current and current != privkey:
        _LOGGER.warning(
            "masternoder2.conf privkey mismatch (have %s… want %s… for %s)",
            current[:8],
            privkey[:8],
            _primary_ping_alias(),
        )

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_body)
        return True, None
    except PermissionError as exc:
        err = (
            f"cannot write {path}: {exc} — fix privkey as root "
            f"(scripts/mn2_fix_daemon_privkey.sh or fleet ops --fix-privkey)"
        )
        _LOGGER.error(err)
        return False, err
    except OSError as exc:
        err = f"cannot write {path}: {exc}"
        _LOGGER.error(err)
        return False, err


def _running_as_root() -> bool:
    try:
        return os.geteuid() == 0
    except AttributeError:
        return False


def _restart_masternode_daemon() -> Optional[str]:
    if (os.environ.get("MN2_SKIP_DAEMON_RESTART") or "").strip().lower() in ("1", "true", "yes"):
        return None
    ops = _ops_cfg()
    if ops.get("restart_daemon_on_provision") is False:
        return None
    unit = str(ops.get("daemon_unit") or "masternoder2d").strip() or "masternoder2d"
    try:
        subprocess.run(
            ["systemctl", "restart", unit],
            check=True,
            timeout=120,
            capture_output=True,
            text=True,
        )
        return None
    except (OSError, subprocess.SubprocessError) as exc:
        err_blob = str(exc).lower()
        if isinstance(exc, subprocess.CalledProcessError):
            err_blob = f"{err_blob} {(exc.stderr or '')}".lower()
        defer = not _running_as_root() or any(
            token in err_blob
            for token in (
                "interactive authentication",
                "access denied",
                "not permitted",
                "permission denied",
                "authentication required",
            )
        )
        if defer:
            _LOGGER.warning(
                "daemon restart deferred (non-root uWSGI cannot systemctl restart %s): %s",
                unit,
                exc,
            )
            return None
        return f"daemon restart failed: {exc}"


def _rpc_wait_timeout_sec() -> int:
    """Seconds to wait for RPC after daemon restart (env MN2_RPC_WAIT_SEC or ops.rpc_wait_sec)."""
    raw = (os.environ.get("MN2_RPC_WAIT_SEC") or _ops_cfg().get("rpc_wait_sec") or "180").strip()
    try:
        return max(30, int(raw))
    except (TypeError, ValueError):
        return 180


def _wait_for_rpc_ready(timeout_sec: Optional[int] = None) -> Optional[str]:
    from backend.services import mn2_rpc_client as rpc

    wait = _rpc_wait_timeout_sec() if timeout_sec is None else max(30, int(timeout_sec))
    deadline = time.time() + wait
    while time.time() < deadline:
        r = rpc.getblockcount()
        if not r.get("error") and r.get("result") is not None:
            return None
        time.sleep(5)
    return "RPC not ready after daemon restart"


def _broadcast_endpoint() -> str:
    ip = (os.environ.get("MN2_MASTERNODE_BROADCAST_IP") or _ops_cfg().get("external_ip") or "").strip()
    if not ip:
        ip = (os.environ.get("MN2_PUBLIC_IP") or "").strip()
    if not ip or ip in ("127.0.0.1", "localhost"):
        ip = "140.82.39.124"
    try:
        port = int(os.environ.get("MN2_MASTERNODE_PORT") or _ops_cfg().get("masternode_port") or 17646)
    except (TypeError, ValueError):
        port = 17646
    return f"{ip}:{port}"


def _collateral_keys_in_use(hosts: List[Dict[str, Any]]) -> set:
    keys = set()
    for h in hosts:
        txid = h.get("collateral_txid")
        vout = h.get("collateral_vout")
        if txid is not None and vout is not None:
            keys.add((str(txid), int(vout)))
    return keys


def _wallet_collateral_utxo(txid: str, vout: int) -> Optional[Dict[str, Any]]:
    """Return a 10k UTXO from the wallet if txid:vout exists and is spendable."""
    info = list_collateral_outputs()
    if not info.get("success"):
        return None
    want = (str(txid), int(vout))
    for utxo in info.get("outputs") or []:
        if not isinstance(utxo, dict):
            continue
        key = (str(utxo.get("txid")), int(utxo.get("vout")))
        if key == want:
            return utxo
    return None


def _pick_collateral_utxo(exclude: set, min_conf: int = 10) -> Optional[Dict[str, Any]]:
    info = list_collateral_outputs()
    if not info.get("success"):
        return None
    for utxo in info.get("outputs") or []:
        if not isinstance(utxo, dict):
            continue
        key = (str(utxo.get("txid")), int(utxo.get("vout")))
        if key in exclude:
            continue
        if int(utxo.get("confirmations") or 0) < min_conf:
            continue
        return utxo
    return None


def _lock_wallet_collateral_utxos() -> None:
    """Prevent coin selection from spending existing 10k collateral outputs when funding new ones."""
    collateral = float(get_config().get("collateral_mn2") or _COLLATERAL_MN2)
    info = list_collateral_outputs()
    if not info.get("success"):
        return
    outputs = []
    for utxo in info.get("outputs") or []:
        if not isinstance(utxo, dict):
            continue
        txid = utxo.get("txid")
        vout = utxo.get("vout")
        if txid is None or vout is None:
            continue
        outputs.append({"txid": str(txid), "vout": int(vout)})
    if not outputs:
        return
    from backend.services import mn2_rpc_client as rpc
    rpc.lockunspent(False, outputs)


def _send_collateral_utxo(collateral: float) -> Dict[str, Any]:
    from backend.services import mn2_rpc_client as rpc
    _lock_wallet_collateral_utxos()
    addr_r = rpc.getnewaddress()
    if addr_r.get("error"):
        return {"success": False, "error": addr_r["error"]}
    addr = addr_r.get("result")
    send_r = rpc.sendtoaddress(str(addr), float(collateral))
    if send_r.get("error"):
        return {"success": False, "error": send_r["error"]}
    return {"success": True, "address": addr, "txid": send_r.get("result")}


def _unlock_wallet() -> bool:
    pw = (os.environ.get("MN2_WALLET_PASSPHRASE") or "").strip()
    if not pw:
        return False
    from backend.services import mn2_rpc_client as rpc
    r = rpc.walletpassphrase(pw, 120, True)
    return not r.get("error")


def _append_masternode_conf_line(alias: str, ip_port: str, txid: str, vout: int, privkey: str) -> bool:
    # PIVX/MN2 format: alias IP:port masternodeprivkey collateral_txid collateral_index
    _validate_masternode_conf_fields(alias, ip_port, txid, vout, privkey)
    alias = alias.strip()
    ip_port = ip_port.strip()
    privkey = privkey.strip()
    txid = txid.strip()
    vout = int(vout)
    new_line = _format_masternode_conf_line(alias, ip_port, privkey, txid, vout)
    path = _masternode_conf_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    repair_masternode_conf()
    rows = _read_masternode_conf_entries()
    preamble: List[str] = []
    entries: List[Dict[str, Any]] = []
    for row in rows:
        if row.get("kind") == "comment":
            preamble.append(row["raw"])
        elif row.get("kind") == "entry":
            entries.append(row)

    existing = _entry_for_alias(alias, valid_only=True)
    if existing:
        same = (
            existing.get("ip_port") == ip_port
            and existing.get("privkey") == privkey
            and existing.get("txid") == txid
            and int(existing.get("vout") or -1) == vout
        )
        if same:
            return False

    replaced = False
    out_entries: List[Dict[str, Any]] = []
    for row in entries:
        if row.get("alias") == alias:
            if not replaced:
                out_entries.append({
                    "kind": "entry",
                    "alias": alias,
                    "valid": True,
                    "ip_port": ip_port,
                    "privkey": privkey,
                    "txid": txid,
                    "vout": vout,
                })
                replaced = True
            continue
        out_entries.append(row)

    if not replaced:
        out_entries.append({
            "kind": "entry",
            "alias": alias,
            "valid": True,
            "ip_port": ip_port,
            "privkey": privkey,
            "txid": txid,
            "vout": vout,
        })

    body_parts: List[str] = []
    if preamble:
        body_parts.extend(f"{ln}\n" if not ln.endswith("\n") else ln for ln in preamble)
    for row in out_entries:
        if row.get("valid"):
            body_parts.append(
                _format_masternode_conf_line(
                    str(row["alias"]),
                    str(row["ip_port"]),
                    str(row["privkey"]),
                    str(row["txid"]),
                    int(row["vout"]),
                )
            )
        else:
            body_parts.append(str(row.get("raw", "")) + "\n")

    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("".join(body_parts))
    os.replace(tmp, path)
    return True


def _start_masternode(
    alias: str,
    privkey: Optional[str] = None,
    *,
    conf_changed: bool = False,
    skip_privkey_sync: bool = False,
) -> Optional[str]:
    """
    Start a hosted masternode on the ops daemon.

    Restart is **not** required on every call — only when ``masternoder2.conf`` ping
    settings change or ``masternode.conf`` gained a new line (``conf_changed``).

    RPC note: ``startmasternode local false <name>`` is invalid. To target a named MN use
    ``startmasternode alias false <alias>`` then ``local false`` (privkey must match in conf).
    """
    from backend.services import mn2_rpc_client as rpc

    alias = (alias or "").strip()
    if not alias:
        return "masternode alias required"

    pk = (privkey or _privkey_for_alias(alias) or "").strip()
    if not pk:
        return f"no privkey for alias {alias} in masternode.conf"

    _unlock_wallet()
    _unlock_collateral_utxos()

    need_restart = False
    sync_err: Optional[str] = None
    if not skip_privkey_sync:
        conf_changed_by_sync, sync_err = _sync_masternode_daemon_privkey()
        # Only masternoder2.conf ping-block changes need a daemon restart — not new
        # masternode.conf lines (those use startmasternode alias via RPC).
        if conf_changed_by_sync and _ops_cfg().get("restart_daemon_on_conf_change", True):
            need_restart = True
    elif conf_changed:
        _LOGGER.debug(
            "masternode.conf changed for %s; RPC alias start only (no daemon restart)",
            alias,
        )

    if need_restart:
        restart_err = _restart_masternode_daemon()
        if restart_err:
            return restart_err
        wait_err = _wait_for_rpc_ready()
        if wait_err:
            return wait_err
    else:
        probe = rpc.getblockcount(timeout_sec=5)
        if probe.get("error") or probe.get("result") is None:
            return f"RPC unavailable: {probe.get('error') or 'no result'}"

    if sync_err:
        _LOGGER.warning(
            "RPC-only start for %s (daemon privkey not synced): %s",
            alias,
            sync_err,
        )

    last_err = "masternode start failed"
    rpc_ok = False
    attempts: List[tuple] = [
        ("alias", False, alias),
    ]
    if multi_ping_enabled():
        attempts.append(("local", False))
    else:
        attempts.extend([
            ("local", False),
            ("missing", False),
        ])
    for item in attempts:
        set_type, lock = item[0], item[1]
        alias_arg = item[2] if len(item) > 2 else None
        if alias_arg is not None:
            r = rpc.startmasternode(set_type, lock, alias_arg)
        else:
            r = rpc.startmasternode(set_type, lock)
        if not r.get("error"):
            rpc_ok = True
            if sync_err:
                return sync_err
            return None
        last_err = str(r.get("error") or last_err)
    if sync_err and not rpc_ok:
        return sync_err
    return last_err if last_err != "masternode start failed" else None


def maintain_ping_loop() -> Dict[str, Any]:
    """
    Watchdog: re-issue startmasternode when ENABLED activetime stops increasing.
    Does not replace the daemon's internal ping thread — only restarts it after stalls.
    """
    ops = _ops_cfg()
    if ops.get("maintain_ping_loop") is False:
        return {"success": True, "skipped": True, "reason": "disabled in ops config"}

    alias = _primary_ping_alias()
    if not alias:
        return {"success": False, "error": "no primary_ping_alias or masternode.conf entry"}

    if _ping_loop_healthy():
        return {
            "success": True,
            "skipped": True,
            "reason": "ping loop healthy (ENABLED activetime increasing)",
            "primary_alias": alias,
        }

    pk = _primary_ping_privkey()
    if not pk:
        return {"success": False, "error": f"no privkey for primary_ping_alias {alias}"}

    _unlock_wallet()
    unlocked = _unlock_collateral_utxos()
    err = _start_masternode(alias, pk, conf_changed=False, skip_privkey_sync=True)
    sync_err = None
    if err and "masternoder2.conf" in err and ("cannot write" in err or "cannot read" in err):
        sync_err = err
    fleet_reg_err = None
    if multi_ping_enabled() and err is None:
        fleet_reg_err = _register_fleet_ping_targets()
    return {
        "success": err is None and fleet_reg_err is None,
        "primary_alias": alias,
        "multi_ping": multi_ping_enabled(),
        "unlocked_utxos": unlocked,
        "error": err or fleet_reg_err,
        "sync_error": sync_err,
        "action": (
            "multi-ping: alias + fleet register (startmasternode all)"
            if multi_ping_enabled()
            else "sync primary privkey, restart if changed, startmasternode alias then local"
        ),
    }


def _start_masternode_alias(alias: str) -> Optional[str]:
    """Backward-compatible wrapper — prefer ``_start_masternode`` with privkey when available."""
    return _start_masternode(alias)


def provision_host(host_id: str, order_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fully automated post-payment provisioning: reserve collateral, write masternode.conf,
    start the node, and update the registry. Retries safely when collateral is confirming.
    """
    host_id = (host_id or "").strip()
    if not host_id:
        return {"success": False, "error": "host id required"}

    cfg = get_config()
    if not bool(cfg.get("auto_provision", True)):
        return {"success": True, "status": "queued", "skipped": True}

    with _LOCK:
        hosts = list(_load_hosts_doc().get("hosts") or [])
        host = next((h for h in hosts if isinstance(h, dict) and h.get("id") == host_id), None)
        if not host:
            return {"success": False, "error": "host not found"}

    chain = network_masternodes(limit=100).get("list") or []
    on_chain = _match_on_chain(host, chain if isinstance(chain, list) else [])
    if on_chain:
        register_host({
            "id": host_id,
            "label": host.get("label") or host_id,
            "status": "active",
            "broadcast_address": on_chain.get("addr") or host.get("broadcast_address"),
            "collateral_txid": host.get("collateral_txid"),
            "collateral_vout": host.get("collateral_vout"),
            "notes": host.get("notes") or "Live on network",
        })
        return {"success": True, "status": "active", "broadcast_address": on_chain.get("addr")}

    collateral = float(cfg.get("collateral_mn2") or _COLLATERAL_MN2)
    min_conf = int(_ops_cfg().get("min_collateral_confirmations") or 10)
    used = _collateral_keys_in_use(hosts)

    utxo = None
    if host.get("collateral_txid") is not None and host.get("collateral_vout") is not None:
        stored = _wallet_collateral_utxo(host.get("collateral_txid"), host.get("collateral_vout"))
        if stored:
            utxo = stored
        elif host.get("collateral_txid"):
            register_host({
                "id": host_id,
                "label": host.get("label") or host_id,
                "status": "provisioning",
                "collateral_txid": None,
                "collateral_vout": None,
                "collateral_address": None,
                "owner_user_id": host.get("owner_user_id"),
                "notes": "Stale collateral txid cleared — will rebind to wallet UTXO",
            })
    if not utxo:
        utxo = _pick_collateral_utxo(used, min_conf=min_conf)

    if not utxo:
        from backend.services import mn2_rpc_client as rpc
        bal_r = rpc.getbalance()
        balance = float(bal_r.get("result") or 0) if not bal_r.get("error") else 0.0
        if balance >= collateral + 1.0:
            created = _send_collateral_utxo(collateral)
            if created.get("success"):
                register_host({
                    "id": host_id,
                    "label": host.get("label") or host_id,
                    "status": "provisioning",
                    "collateral_address": created.get("address"),
                    "collateral_txid": created.get("txid"),
                    "collateral_vout": 0,
                    "owner_user_id": host.get("owner_user_id"),
                    "notes": f"Auto collateral from PayPal order {order_id or ''}".strip(),
                })
                return {
                    "success": True,
                    "status": "provisioning",
                    "message": "Collateral sent — node activates automatically after confirmations.",
                }
            return {"success": False, "error": created.get("error"), "status": "provisioning"}
        register_host({
            "id": host_id,
            "label": host.get("label") or host_id,
            "status": "provisioning",
            "owner_user_id": host.get("owner_user_id"),
            "notes": "Paid — waiting for collateral pool refill",
        })
        return {
            "success": True,
            "status": "provisioning",
            "message": "Slot reserved — activating when collateral is available.",
        }

    if int(utxo.get("confirmations") or 0) < min_conf:
        register_host({
            "id": host_id,
            "label": host.get("label") or host_id,
            "status": "provisioning",
            "collateral_address": utxo.get("address"),
            "collateral_txid": utxo.get("txid"),
            "collateral_vout": utxo.get("vout"),
            "owner_user_id": host.get("owner_user_id"),
        })
        return {
            "success": True,
            "status": "provisioning",
            "message": "Collateral confirming — node will start automatically.",
        }

    alias = _alias_from_host_id(host_id)
    from backend.services import mn2_rpc_client as rpc
    privkey = _privkey_for_alias(alias)
    if not privkey:
        gen = rpc.createmasternodekey()
        if gen.get("error"):
            return {"success": False, "error": gen.get("error"), "status": "provisioning"}
        privkey = gen.get("result")
        if not privkey:
            return {"success": False, "error": "createmasternodekey returned empty", "status": "provisioning"}
    ip_port = _broadcast_endpoint()
    txid = str(utxo.get("txid"))
    vout = int(utxo.get("vout"))
    try:
        conf_added = _append_masternode_conf_line(alias, ip_port, txid, vout, str(privkey))
    except Exception as exc:
        return {"success": False, "error": f"masternode.conf write failed: {exc}", "status": "provisioning"}

    start_err = _start_masternode(alias, str(privkey), conf_changed=conf_added)
    broadcast_address = ip_port
    register_host({
        "id": host_id,
        "label": host.get("label") or host_id,
        "status": "active" if not start_err else "provisioning",
        "collateral_address": utxo.get("address"),
        "collateral_txid": txid,
        "collateral_vout": vout,
        "broadcast_address": broadcast_address,
        "owner_user_id": host.get("owner_user_id"),
        "notes": None if not start_err else f"Conf written; start pending: {start_err}",
    })

    chain2 = network_masternodes(limit=100).get("list") or []
    matched = _match_on_chain({"broadcast_address": broadcast_address}, chain2 if isinstance(chain2, list) else [])
    if matched:
        register_host({
            "id": host_id,
            "label": host.get("label") or host_id,
            "status": "active",
            "broadcast_address": matched.get("addr") or broadcast_address,
            "collateral_txid": txid,
            "collateral_vout": vout,
            "collateral_address": utxo.get("address"),
            "owner_user_id": host.get("owner_user_id"),
        })
        return {
            "success": True,
            "status": "active",
            "broadcast_address": matched.get("addr") or broadcast_address,
            "message": "Your masternode is live on the network.",
        }

    return {
        "success": True,
        "status": "provisioning" if start_err else "active",
        "broadcast_address": broadcast_address,
        "message": "Slot provisioned — broadcasting to the network (usually under a minute).",
        "start_error": start_err,
    }


def process_pending_hosts(limit: int = 20) -> Dict[str, Any]:
    """Cron/ops: retry auto-provision for paid hosts still provisioning + maintain ping loop."""
    ping = maintain_ping_loop()
    pending_status = {"queued", "provisioning", "planned"}
    hosts = list_hosts(include_internal=True)
    todo = [h for h in hosts if (h.get("status") or "").lower() in pending_status][: max(1, int(limit))]
    results = []
    for h in todo:
        hid = h.get("id")
        if not hid:
            continue
        results.append({"host_id": hid, **provision_host(str(hid))})
    return {"success": True, "processed": len(results), "results": results, "ping_loop": ping}


def _maybe_capacity_discord_alert(slots_available: int, max_nodes: int, hosted: int) -> None:
    """Push Discord #market alert when hosting slots drop below configured threshold."""
    cfg = get_config()
    ops = cfg.get("ops") if isinstance(cfg.get("ops"), dict) else {}
    threshold = int(ops.get("capacity_alert_threshold") or 5)
    if slots_available >= threshold:
        return
    cooldown_h = max(1, int(ops.get("capacity_alert_cooldown_hours") or 6))
    cursor_path = os.path.join(_base(), "logs", "hosting_capacity_alert.json")
    now = time.time()
    last_slots = None
    last_ts = 0.0
    if os.path.isfile(cursor_path):
        try:
            with open(cursor_path, "r", encoding="utf-8") as f:
                cur = json.load(f) or {}
            last_ts = float(cur.get("ts") or 0)
            last_slots = cur.get("slots_available")
        except Exception:
            pass
    if last_ts and (now - last_ts) < cooldown_h * 3600 and last_slots is not None and slots_available >= int(last_slots):
        return
    try:
        from backend.services.discord_service import post_message
        base_url = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
        post_message(
            "market",
            {
                "embeds": [{
                    "title": "Masternode hosting capacity low",
                    "description": (
                        f"Only **{slots_available}** slot(s) left "
                        f"({hosted}/{max_nodes} used).\n\n"
                        f"[Open hosting tab]({base_url}/explorer?tab=masternodes)"
                    ),
                    "color": 0xFEE75C,
                }],
            },
            message_id=f"hosting-capacity:{slots_available}",
        )
        os.makedirs(os.path.dirname(cursor_path), exist_ok=True)
        tmp = cursor_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"ts": now, "slots_available": slots_available}, f)
        os.replace(tmp, cursor_path)
    except Exception as exc:
        _LOGGER.debug("capacity discord alert skipped: %s", exc)


def get_service_status(*, fresh: bool = False) -> Dict[str, Any]:
    """Public + ops snapshot for hosting service."""
    cfg = get_config()
    enabled = bool(cfg.get("enabled", True))
    collateral = float(cfg.get("collateral_mn2") or _COLLATERAL_MN2)
    max_nodes = int(cfg.get("max_hosted_nodes") or 3)
    stale_hours = float(cfg.get("stale_provisioning_hours") or 6)
    purge_stale_provisioning_hosts(max_age_hours=stale_hours, dry_run=False)
    registry_hosts = list(_load_hosts_doc().get("hosts") or [])
    hosts = list_hosts(include_internal=False)
    net = network_masternodes(limit=100, fresh=fresh)
    chain_list = net.get("list") if isinstance(net.get("list"), list) else []

    synced_hosts: List[Dict[str, Any]] = []
    enabled_platform = 0
    for h in hosts:
        on_chain = _match_on_chain(h, chain_list)
        st = (on_chain or {}).get("status") or h.get("status") or "unknown"
        if str(st).upper() == "ENABLED":
            enabled_platform += 1
        synced_hosts.append({
            **h,
            "on_chain_status": (on_chain or {}).get("status"),
            "on_chain_rank": (on_chain or {}).get("rank"),
            "on_chain_activetime": (on_chain or {}).get("activetime"),
            "synced": on_chain is not None,
        })

    collateral_info = list_collateral_outputs()
    avail_outputs = int(collateral_info.get("count") or 0) if collateral_info.get("success") else 0

    mnsync = None
    staking_active = None
    daemon_version = None
    try:
        from backend.services.mn2_rpc_client import staking_health, getinfo
        sh = staking_health() or {}
        mnsync = sh.get("mnsync")
        staking_active = sh.get("staking_active")
        info = getinfo()
        if not info.get("error"):
            daemon_version = (info.get("result") or {}).get("version")
    except Exception:
        pass

    slots_used = _count_slots_used(registry_hosts)
    stale_provisioning = sum(
        1 for h in registry_hosts
        if isinstance(h, dict)
        and (h.get("status") or "").lower() == "provisioning"
        and not h.get("collateral_txid")
    )
    out = {
        "success": True,
        "enabled": enabled,
        "service_label": cfg.get("service_label"),
        "service_description": cfg.get("service_description"),
        "collateral_mn2": collateral,
        "max_hosted_nodes": max_nodes,
        "hosted_count": slots_used,
        "registry_count": len(registry_hosts),
        "stale_provisioning_count": stale_provisioning,
        "slots_available": max(0, max_nodes - slots_used),
        "platform_enabled_on_chain": enabled_platform,
        "collateral_outputs_available": avail_outputs,
        "hosting_fee_percent": float(cfg.get("hosting_fee_percent") or 0),
        "public_notes": cfg.get("public_notes"),
        "network": {
            "total": net.get("total", 0),
            "enabled": net.get("enabled", 0),
            "rpc_error": net.get("rpc_error"),
        },
        "daemon": {
            "mnsync": mnsync,
            "staking_active": staking_active,
            "version": daemon_version,
            "multi_ping_capable": daemon_supports_multi_ping(),
            "multi_ping_enabled": multi_ping_enabled(),
            "enabled_with_activetime": _count_enabled_with_activetime(chain_list),
        },
        "hosts": synced_hosts,
        "ops": cfg.get("ops") if isinstance(cfg.get("ops"), dict) else {},
    }
    try:
        from backend.services import mn2_masternode_hosting_service as hosting
        out["paypal"] = hosting.get_paypal_config()
        out["hosting_stats"] = hosting.hosting_stats()
    except Exception:
        pass
    try:
        _maybe_capacity_discord_alert(
            int(out.get("slots_available") or 0),
            int(out.get("max_hosted_nodes") or 0),
            int(out.get("hosted_count") or 0),
        )
    except Exception:
        pass
    return out


def probe_health() -> Dict[str, Any]:
    """Lightweight health for mn2_services_hub."""
    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"status": "disabled", "enabled": False}
    try:
        st = get_service_status()
        if not st.get("success"):
            return {"status": "degraded", "enabled": True, "error": st.get("error")}
        net_enabled = int(st.get("network", {}).get("enabled") or 0)
        platform = int(st.get("platform_enabled_on_chain") or 0)
        daemon = st.get("daemon") or {}
        if daemon.get("mnsync") is False:
            return {
                "status": "warn",
                "enabled": True,
                "hosted_count": st.get("hosted_count"),
                "network_enabled": net_enabled,
                "platform_enabled": platform,
                "detail": "mnsync pending",
            }
        if platform == 0 and st.get("hosted_count", 0) > 0:
            return {
                "status": "warn",
                "enabled": True,
                "hosted_count": st.get("hosted_count"),
                "network_enabled": net_enabled,
                "platform_enabled": platform,
                "detail": "registered hosts not yet enabled on-chain",
            }
        return {
            "status": "healthy" if net_enabled > 0 or st.get("hosted_count", 0) == 0 else "warn",
            "enabled": True,
            "hosted_count": st.get("hosted_count"),
            "slots_available": st.get("slots_available"),
            "network_enabled": net_enabled,
            "platform_enabled": platform,
        }
    except Exception as exc:
        return {"status": "degraded", "enabled": True, "error": str(exc)}
