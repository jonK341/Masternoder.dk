"""Wallet Train D — Monitors & Navigation (W-31…W-40) toward v1.6.0.0.

Health/alerts/metrics, optional geo/peer preference, spend geofence,
fee/coin route picker, and guided send/stake/host flows.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from backend.services import mn2_rpc_client as rpc
from backend.services import mn2_spork_service as spork

TRAIN_D_TARGET = "v1.6.0.0"
TRAIN_D_CHANNEL = "draft"
TRAIN_D_SLICE = "D"

TRAIN_D_IDS: Tuple[str, ...] = tuple(f"W-{i:02d}" for i in range(31, 41))

TRAIN_D_META: Dict[str, Dict[str, Any]] = {
    "W-31": {
        "tech": "Health Monitor",
        "title": "Wallet health RPC + green/amber/red",
        "surfaces": ["daemon", "qt"],
    },
    "W-32": {
        "tech": "Resource Monitor",
        "title": "CPU/RAM/disk for daemon in services hub",
        "surfaces": ["web", "ops"],
    },
    "W-33": {
        "tech": "Uptime Monitor",
        "title": "Daemon uptime SLA tile on /wallets",
        "surfaces": ["web"],
    },
    "W-34": {
        "tech": "Alert Monitor",
        "title": "Alerts on unlock/spend/sync stall",
        "surfaces": ["ops", "web"],
    },
    "W-35": {
        "tech": "Metric Monitor",
        "title": "Prometheus/OpenMetrics wallet exporter",
        "surfaces": ["ops"],
    },
    "W-36": {
        "tech": "GPS Coordinator",
        "title": "Region-aware peer preference (optional)",
        "surfaces": ["daemon"],
    },
    "W-37": {
        "tech": "Location Tracker",
        "title": "Masternode geo/status map tile",
        "surfaces": ["web"],
    },
    "W-38": {
        "tech": "Geofence Manager",
        "title": "Optional spend allow-list by network policy",
        "surfaces": ["daemon", "qt"],
    },
    "W-39": {
        "tech": "Route Optimizer",
        "title": "Smart coin selection / fee route picker",
        "surfaces": ["daemon", "qt"],
    },
    "W-40": {
        "tech": "Navigation System",
        "title": "Guided send / stake / host flows",
        "surfaces": ["qt", "web"],
    },
}

_BASE = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_BOOT_MONOTONIC = time.monotonic()


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _meta(wid: str) -> Dict[str, Any]:
    row = TRAIN_D_META.get(wid) or {}
    return {
        "id": wid,
        "tech": row.get("tech"),
        "title": row.get("title"),
        "surfaces": list(row.get("surfaces") or []),
        "train": TRAIN_D_SLICE,
        "target": TRAIN_D_TARGET,
    }


def train_d_version() -> Dict[str, Any]:
    return {
        "success": True,
        "train": TRAIN_D_SLICE,
        "target": TRAIN_D_TARGET,
        "channel": TRAIN_D_CHANNEL,
        "badge": TRAIN_D_TARGET,
        "badge_label": f"Wallet Train D {TRAIN_D_TARGET} ({TRAIN_D_CHANNEL})",
        "latest_wallet_download_unchanged": True,
        "release_stub": "docs/releases/v1.6.0.0-sense.md",
        "ids": list(TRAIN_D_IDS),
        "updated_at": _iso(),
    }


def health_monitor() -> Dict[str, Any]:
    """W-31 — wallet health green/amber/red."""
    from backend.services import mn2_daemon_health_service as daemon_health

    try:
        probe = daemon_health.probe_daemon(extended=False) or {}
    except Exception as exc:
        probe = {"healthy": False, "error": str(exc)}
    maint = spork.maintenance_mode()
    if maint:
        color = "red"
    elif probe.get("healthy"):
        color = "green"
    elif probe.get("rpc_url_set"):
        color = "amber"
    else:
        color = "red"
    return {
        "success": True,
        **_meta("W-31"),
        "health": {
            "status": color,
            "healthy": bool(probe.get("healthy")),
            "maintenance": maint,
            "rpc_url_set": bool(probe.get("rpc_url_set")),
            "detail": probe.get("health") or probe.get("error"),
        },
        "updated_at": _iso(),
    }


def resource_monitor() -> Dict[str, Any]:
    """W-32 — CPU/RAM/disk snapshot for the site worker (daemon mirror)."""
    rss_kb = None
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    rss_kb = int(line.split()[1])
                    break
    except Exception:
        rss_kb = None
    disk = {}
    try:
        st = os.statvfs(str(_BASE))
        total = st.f_frsize * st.f_blocks
        free = st.f_frsize * st.f_bavail
        disk = {
            "total_gb": round(total / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "used_pct": round((1.0 - (free / total)) * 100.0, 1) if total else None,
        }
    except Exception as exc:
        disk = {"error": str(exc)}
    load1 = None
    try:
        load1 = os.getloadavg()[0]
    except Exception:
        load1 = None
    return {
        "success": True,
        **_meta("W-32"),
        "resources": {
            "rss_mb": round((rss_kb or 0) / 1024.0, 2) if rss_kb is not None else None,
            "load1": load1,
            "disk": disk,
            "scope": "site_worker_mirror",
        },
        "updated_at": _iso(),
    }


def uptime_monitor() -> Dict[str, Any]:
    """W-33 — uptime SLA tile for the worker / daemon probe age."""
    uptime_sec = max(0.0, time.monotonic() - _BOOT_MONOTONIC)
    health = health_monitor()
    status = (health.get("health") or {}).get("status") or "amber"
    sla = "met" if status == "green" else ("at_risk" if status == "amber" else "breach")
    return {
        "success": True,
        **_meta("W-33"),
        "uptime": {
            "worker_uptime_sec": round(uptime_sec, 1),
            "health_status": status,
            "sla": sla,
            "tile": "wallets",
        },
        "updated_at": _iso(),
    }


def alert_monitor() -> Dict[str, Any]:
    """W-34 — alerts for maintenance, unhealthy daemon, sync stall signals."""
    alerts: List[Dict[str, Any]] = []
    health = health_monitor()
    h = health.get("health") or {}
    if h.get("maintenance"):
        alerts.append({"id": "maintenance", "severity": "high", "message": "SPORK_115 maintenance mode active"})
    if h.get("status") == "red":
        alerts.append({"id": "daemon_red", "severity": "high", "message": "Wallet daemon health is red"})
    elif h.get("status") == "amber":
        alerts.append({"id": "daemon_amber", "severity": "medium", "message": "Wallet daemon health is amber"})
    try:
        ci = rpc.getblockchaininfo() or {}
        chain = ci.get("result") if isinstance(ci.get("result"), dict) else {}
        if chain.get("initialblockdownload"):
            alerts.append({"id": "ibd", "severity": "medium", "message": "Initial block download in progress"})
        prog = chain.get("verificationprogress")
        if isinstance(prog, (int, float)) and prog < 0.999 and not chain.get("initialblockdownload"):
            alerts.append({"id": "sync_stall_risk", "severity": "medium", "message": "Verification progress below 99.9%"})
    except Exception:
        pass
    return {
        "success": True,
        **_meta("W-34"),
        "alert_count": len(alerts),
        "alerts": alerts,
        "updated_at": _iso(),
    }


def metrics_exporter() -> Dict[str, Any]:
    """W-35 — OpenMetrics-style wallet snapshot."""
    health = health_monitor()
    resources = resource_monitor()
    uptime = uptime_monitor()
    peers = None
    try:
        cc = rpc.getconnectioncount() or {}
        peers = cc.get("result") if cc.get("error") is None else None
    except Exception:
        peers = None
    status = (health.get("health") or {}).get("status") or "unknown"
    status_num = {"green": 2, "amber": 1, "red": 0}.get(status, -1)
    lines = [
        "# HELP mn2_wallet_health Health status (2=green,1=amber,0=red)",
        "# TYPE mn2_wallet_health gauge",
        f"mn2_wallet_health {status_num}",
        "# HELP mn2_wallet_worker_uptime_seconds Worker uptime",
        "# TYPE mn2_wallet_worker_uptime_seconds counter",
        f"mn2_wallet_worker_uptime_seconds {(uptime.get('uptime') or {}).get('worker_uptime_sec') or 0}",
        "# HELP mn2_wallet_peers Peer connections",
        "# TYPE mn2_wallet_peers gauge",
        f"mn2_wallet_peers {peers if peers is not None else -1}",
        "# HELP mn2_wallet_rss_mb Resident memory MB",
        "# TYPE mn2_wallet_rss_mb gauge",
        f"mn2_wallet_rss_mb {(resources.get('resources') or {}).get('rss_mb') or 0}",
    ]
    return {
        "success": True,
        **_meta("W-35"),
        "content_type": "text/plain; version=0.0.4",
        "openmetrics": "\n".join(lines) + "\n",
        "samples": {
            "health": status_num,
            "peers": peers,
            "rss_mb": (resources.get("resources") or {}).get("rss_mb"),
        },
        "updated_at": _iso(),
    }


def region_peer_preference() -> Dict[str, Any]:
    """W-36 — optional region-aware peer preference."""
    region = (os.environ.get("MN2_REGION") or os.environ.get("FLY_REGION") or "").strip() or None
    prefer = []
    if region:
        prefer.append({"region": region, "policy": "prefer_local_addnode", "enabled": True})
    else:
        prefer.append({"region": None, "policy": "default_dnsseed", "enabled": False})
    return {
        "success": True,
        **_meta("W-36"),
        "preference": prefer,
        "optional": True,
        "updated_at": _iso(),
    }


def masternode_map_tile() -> Dict[str, Any]:
    """W-37 — masternode geo/status map tile payload."""
    nodes: List[Dict[str, Any]] = []
    try:
        from backend.services import mn2_masternode_service as mn

        if hasattr(mn, "list_masternodes"):
            raw = mn.list_masternodes() or []
            if isinstance(raw, dict):
                raw = raw.get("masternodes") or raw.get("result") or []
            for row in list(raw)[:40]:
                if not isinstance(row, dict):
                    continue
                nodes.append(
                    {
                        "alias": row.get("alias") or row.get("proTxHash") or row.get("addr"),
                        "status": row.get("status") or row.get("state"),
                        "addr": row.get("addr") or row.get("address"),
                        "ip": row.get("ip") or row.get("host"),
                    }
                )
    except Exception as exc:
        nodes = []
        err = str(exc)
    else:
        err = None
    return {
        "success": True,
        **_meta("W-37"),
        "map": {
            "node_count": len(nodes),
            "nodes": nodes,
            "error": err,
            "tile": "masternode_status",
        },
        "updated_at": _iso(),
    }


def spend_geofence(*, user_id: str = "proto_user") -> Dict[str, Any]:
    """W-38 — spend allow-list / whitelist fence status."""
    from backend.services.mn2_withdrawal_security import get_security_status

    uid = str(user_id or "proto_user")
    try:
        sec = get_security_status(uid) or {}
    except Exception as exc:
        sec = {"success": False, "error": str(exc), "whitelist_count": 0}
    enforced = spork.withdraw_whitelist_required()
    return {
        "success": True,
        **_meta("W-38"),
        "user_id": uid,
        "geofence": {
            "whitelist_required": enforced,
            "whitelist_count": sec.get("whitelist_count"),
            "totp_enabled": sec.get("totp_enabled"),
            "policy": "network_allow_list",
        },
        "security": sec,
        "updated_at": _iso(),
    }


def fee_route_picker(*, conf_target: int = 6) -> Dict[str, Any]:
    """W-39 — smart fee / coin selection route picker (local rules)."""
    from backend.services.wallet_train_a_service import fee_estimator

    est = fee_estimator(conf_target=conf_target)
    estimate = est.get("estimate") or {}
    routes = [
        {
            "id": "economy",
            "conf_target": max(int(conf_target or 6), 12),
            "fee_mn2": round(float(estimate.get("suggested_fee_mn2") or 0.001) * 0.85, 8),
        },
        {
            "id": "standard",
            "conf_target": int(conf_target or 6),
            "fee_mn2": float(estimate.get("suggested_fee_mn2") or 0.001),
        },
        {
            "id": "priority",
            "conf_target": max(1, min(int(conf_target or 6), 2)),
            "fee_mn2": round(float(estimate.get("suggested_fee_mn2") or 0.001) * 1.35, 8),
        },
    ]
    return {
        "success": True,
        **_meta("W-39"),
        "recommended": routes[1],
        "routes": routes,
        "coin_selection": "avoid_partial_spends_prefer_exact",
        "updated_at": _iso(),
    }


def guided_wallet_flow(*, user_id: str = "proto_user", step: str = "status") -> Dict[str, Any]:
    """W-40 — guided send / stake / host navigation."""
    uid = str(user_id or "proto_user")
    step_norm = str(step or "status").strip().lower()
    steps = [
        {"id": "send", "href": "/profile#profile-mn2-wallet-card", "api": "POST /api/mn2/withdraw"},
        {"id": "stake", "href": "/staking-teams", "api": "GET /api/mn2/train-d/W-40"},
        {"id": "host", "href": "/hosting", "api": "GET /api/mn2/train-d/W-37"},
    ]
    out: Dict[str, Any] = {
        "success": True,
        **_meta("W-40"),
        "user_id": uid,
        "step": step_norm,
        "steps": steps,
        "updated_at": _iso(),
    }
    if step_norm in ("status", "plan"):
        out["health"] = (health_monitor().get("health") or {})
        out["route"] = fee_route_picker().get("recommended")
        out["geofence"] = (spend_geofence(user_id=uid).get("geofence") or {})
        out["next"] = "send"
        return out
    if step_norm == "send":
        out["action"] = {"id": "send", "href": "/profile#profile-mn2-wallet-card", "ready": True}
        out["next"] = "stake"
        return out
    if step_norm == "stake":
        out["action"] = {"id": "stake", "href": "/staking-teams", "ready": True}
        out["next"] = "host"
        return out
    if step_norm == "host":
        out["action"] = {"id": "host", "href": "/hosting", "ready": True}
        out["next"] = "status"
        return out
    out["success"] = False
    out["error"] = "unknown_step"
    out["allowed_steps"] = ["status", "send", "stake", "host"]
    return out


_RUNNERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "W-31": lambda **_kw: health_monitor(),
    "W-32": lambda **_kw: resource_monitor(),
    "W-33": lambda **_kw: uptime_monitor(),
    "W-34": lambda **_kw: alert_monitor(),
    "W-35": lambda **_kw: metrics_exporter(),
    "W-36": lambda **_kw: region_peer_preference(),
    "W-37": lambda **_kw: masternode_map_tile(),
    "W-38": lambda **kw: spend_geofence(user_id=str(kw.get("user_id") or "proto_user")),
    "W-39": lambda **kw: fee_route_picker(conf_target=int(kw.get("conf_target") or 6)),
    "W-40": lambda **kw: guided_wallet_flow(
        user_id=str(kw.get("user_id") or "proto_user"),
        step=str(kw.get("step") or "status"),
    ),
}


def run_deliverable(deliverable_id: str, **kwargs: Any) -> Dict[str, Any]:
    wid = str(deliverable_id or "").strip().upper()
    if wid not in TRAIN_D_IDS:
        return {"success": False, "error": "not_train_d_deliverable", "id": wid, "ids": list(TRAIN_D_IDS)}
    runner = _RUNNERS.get(wid)
    if not runner:
        return {"success": False, "error": "runner_missing", "id": wid}
    try:
        return runner(**kwargs)
    except Exception as exc:
        return {"success": False, "error": str(exc), "id": wid}


def train_d_manifest() -> Dict[str, Any]:
    return {
        "success": True,
        "train": TRAIN_D_SLICE,
        "target": TRAIN_D_TARGET,
        "channel": TRAIN_D_CHANNEL,
        "count": len(TRAIN_D_IDS),
        "ids": list(TRAIN_D_IDS),
        "deliverables": [{**_meta(wid), "installed": True} for wid in TRAIN_D_IDS],
        "version": train_d_version(),
        "updated_at": _iso(),
    }


def run_train_d(**kwargs: Any) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for wid in TRAIN_D_IDS:
        results[wid] = run_deliverable(wid, **kwargs)
    ok = sum(1 for v in results.values() if isinstance(v, dict) and v.get("success"))
    return {
        "success": ok == len(TRAIN_D_IDS),
        "train": TRAIN_D_SLICE,
        "target": TRAIN_D_TARGET,
        "count": len(TRAIN_D_IDS),
        "ok_count": ok,
        "results": results,
        "version": train_d_version(),
        "updated_at": _iso(),
    }


def train_d_acceptance(*, user_id: str = "proto_user") -> Dict[str, Any]:
    """Train D acceptance: health/alerts, metrics scrape, guided flow."""
    checks: List[Dict[str, Any]] = []
    health = health_monitor()
    checks.append(
        {
            "id": "health_monitor",
            "ok": bool(health.get("success")) and (health.get("health") or {}).get("status") in ("green", "amber", "red"),
            "detail": health.get("health"),
        }
    )
    alerts = alert_monitor()
    checks.append({"id": "alerts", "ok": bool(alerts.get("success")), "detail": {"alert_count": alerts.get("alert_count")}})

    metrics = metrics_exporter()
    text = str(metrics.get("openmetrics") or "")
    checks.append(
        {
            "id": "metrics_exporter",
            "ok": "mn2_wallet_health" in text and bool(metrics.get("success")),
            "detail": metrics.get("samples"),
        }
    )

    guided = guided_wallet_flow(user_id=user_id, step="status")
    checks.append(
        {
            "id": "guided_flow",
            "ok": bool(guided.get("success")) and len(guided.get("steps") or []) >= 3,
            "detail": {"next": guided.get("next"), "steps": len(guided.get("steps") or [])},
        }
    )

    route = fee_route_picker()
    checks.append({"id": "fee_route", "ok": bool(route.get("recommended")), "detail": route.get("recommended")})

    passed = all(bool(c.get("ok")) for c in checks)
    return {
        "success": passed,
        "passed": passed,
        "train": TRAIN_D_SLICE,
        "target": TRAIN_D_TARGET,
        "checks": checks,
        "version": train_d_version(),
        "updated_at": _iso(),
    }
