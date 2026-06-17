"""
MN2 masternode hosting — platform-operated masternodes on the shared production daemon.

One masternoder2d datadir hosts N masternodes (PIVX-style); each requires a 10,000 MN2
collateral UTXO in the ops wallet. Registry in data/mn2_masternode_hosts.json; config in
data/mn2_masternode_config.json.

Never raises into request handlers; ops mutations return {success, error}.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_COLLATERAL_MN2 = 10000.0
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
            return {"success": True, "outputs": [], "collateral_mn2": collateral}
        outputs = []
        for utxo in rows:
            if not isinstance(utxo, dict):
                continue
            amt = float(utxo.get("amount") or 0)
            if abs(amt - collateral) > 1e-8:
                continue
            outputs.append({
                "txid": utxo.get("txid"),
                "vout": utxo.get("vout"),
                "amount": amt,
                "address": utxo.get("address"),
                "confirmations": utxo.get("confirmations"),
            })
        return {
            "success": True,
            "collateral_mn2": collateral,
            "count": len(outputs),
            "outputs": outputs,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "outputs": []}


def network_masternodes(limit: int = 50) -> Dict[str, Any]:
    try:
        from backend.services import mn2_explorer_data
        data = mn2_explorer_data.masternodes(limit=limit)
        return {"success": True, **data}
    except Exception as exc:
        return {"success": False, "error": str(exc), "total": 0, "enabled": 0, "list": []}


def _match_on_chain(host: Dict[str, Any], chain_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
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
            if len(hosts) >= max_nodes:
                return {
                    "success": False,
                    "error": "max_hosted_nodes reached (%d)" % max_nodes,
                    "max_hosted_nodes": max_nodes,
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


def _broadcast_endpoint() -> str:
    ip = (os.environ.get("MN2_MASTERNODE_BROADCAST_IP") or _ops_cfg().get("external_ip") or "").strip()
    if not ip:
        ip = (os.environ.get("MN2_PUBLIC_IP") or "127.0.0.1").strip()
    try:
        port = int(os.environ.get("MN2_MASTERNODE_PORT") or _ops_cfg().get("masternode_port") or 9333)
    except (TypeError, ValueError):
        port = 9333
    return f"{ip}:{port}"


def _collateral_keys_in_use(hosts: List[Dict[str, Any]]) -> set:
    keys = set()
    for h in hosts:
        txid = h.get("collateral_txid")
        vout = h.get("collateral_vout")
        if txid is not None and vout is not None:
            keys.add((str(txid), int(vout)))
    return keys


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


def _send_collateral_utxo(collateral: float) -> Dict[str, Any]:
    from backend.services import mn2_rpc_client as rpc
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


def _append_masternode_conf_line(alias: str, ip_port: str, txid: str, vout: int, privkey: str) -> None:
    line = f"{alias} {ip_port} {txid} {vout} {privkey}\n"
    path = _masternode_conf_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        if alias in existing:
            return
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def _start_masternode_alias(alias: str) -> Optional[str]:
    from backend.services import mn2_rpc_client as rpc
    _unlock_wallet()
    last_err = "masternode start failed"
    for args in ((alias,), ("start", alias), ("start-all", "false")):
        r = rpc.masternode_command(*args)
        if not r.get("error"):
            return None
        last_err = str(r.get("error") or last_err)
    return last_err


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
        utxo = {
            "txid": host.get("collateral_txid"),
            "vout": host.get("collateral_vout"),
            "address": host.get("collateral_address"),
            "confirmations": min_conf,
        }
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

    from backend.services import mn2_rpc_client as rpc
    gen = rpc.masternode_command("genkey")
    if gen.get("error"):
        return {"success": False, "error": gen.get("error"), "status": "provisioning"}
    privkey = gen.get("result")
    if not privkey:
        return {"success": False, "error": "masternode genkey returned empty", "status": "provisioning"}

    alias = host_id.replace("-", "")[:16]
    ip_port = _broadcast_endpoint()
    txid = str(utxo.get("txid"))
    vout = int(utxo.get("vout"))
    try:
        _append_masternode_conf_line(alias, ip_port, txid, vout, str(privkey))
    except Exception as exc:
        return {"success": False, "error": f"masternode.conf write failed: {exc}", "status": "provisioning"}

    start_err = _start_masternode_alias(alias)
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
    """Cron/ops: retry auto-provision for paid hosts still provisioning."""
    pending_status = {"queued", "provisioning", "planned"}
    hosts = list_hosts(include_internal=True)
    todo = [h for h in hosts if (h.get("status") or "").lower() in pending_status][: max(1, int(limit))]
    results = []
    for h in todo:
        hid = h.get("id")
        if not hid:
            continue
        results.append({"host_id": hid, **provision_host(str(hid))})
    return {"success": True, "processed": len(results), "results": results}


def get_service_status() -> Dict[str, Any]:
    """Public + ops snapshot for hosting service."""
    cfg = get_config()
    enabled = bool(cfg.get("enabled", True))
    collateral = float(cfg.get("collateral_mn2") or _COLLATERAL_MN2)
    max_nodes = int(cfg.get("max_hosted_nodes") or 3)
    hosts = list_hosts(include_internal=False)
    net = network_masternodes(limit=100)
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
    try:
        from backend.services.mn2_rpc_client import staking_health
        sh = staking_health() or {}
        mnsync = sh.get("mnsync")
        staking_active = sh.get("staking_active")
    except Exception:
        pass

    slots_used = len(hosts)
    out = {
        "success": True,
        "enabled": enabled,
        "service_label": cfg.get("service_label"),
        "service_description": cfg.get("service_description"),
        "collateral_mn2": collateral,
        "max_hosted_nodes": max_nodes,
        "hosted_count": slots_used,
        "slots_available": max(0, max_nodes - slots_used),
        "platform_enabled_on_chain": enabled_platform,
        "collateral_outputs_available": avail_outputs,
        "hosting_fee_percent": float(cfg.get("hosting_fee_percent") or 0),
        "public_notes": cfg.get("public_notes"),
        "network": {
            "total": net.get("total", 0),
            "enabled": net.get("enabled", 0),
        },
        "daemon": {
            "mnsync": mnsync,
            "staking_active": staking_active,
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
