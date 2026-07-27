"""Fleet livestream GPS + GPRS telemetry (public-safe, no PII)."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_GPRS_PATH = os.path.join(_BASE, "data", "fleet_gprs_nodes.json")
_GEO_LOG_DIR = os.path.join(_BASE, "logs", "fleet_stream_geo")
_GEO_LOG_FILE = os.path.join(_GEO_LOG_DIR, "pings.jsonl")
_MAX_PINGS = 400
_COORD_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _geo_config() -> Dict[str, Any]:
    from backend.services.fleet_stream_chat_service import live_config

    cfg = live_config()
    geo = cfg.get("geo") if isinstance(cfg.get("geo"), dict) else {}
    center = geo.get("default_center") if isinstance(geo.get("default_center"), dict) else {}
    return {
        "enabled": geo.get("enabled", True),
        "gps_poll_ms": int(geo.get("gps_poll_ms") or 15000),
        "gprs_poll_ms": int(geo.get("gprs_poll_ms") or 20000),
        "auto_assign_agent_on_stream": geo.get("auto_assign_agent_on_stream", True),
        "coarse_decimals": int(geo.get("coarse_decimals") or 2),
        "default_center": {
            "latitude": float(center.get("latitude") or 55.6761),
            "longitude": float(center.get("longitude") or 12.5683),
        },
        "map_zoom": int(geo.get("map_zoom") or 11),
    }


def coarse_coord(val: float, decimals: int = 2) -> float:
    return round(float(val), max(1, min(4, decimals)))


def _anon_marker_id(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]


def _load_gprs_nodes() -> List[Dict[str, Any]]:
    data = _read_json(_GPRS_PATH, {})
    return [n for n in (data.get("nodes") or []) if isinstance(n, dict) and n.get("id")]


def _gprs_live_position(node: Dict[str, Any], tick: float) -> Tuple[float, float]:
    """Simulate GPRS cell-sector jitter around anchor (public demo feed)."""
    lat = float(node.get("latitude") or 0)
    lon = float(node.get("longitude") or 0)
    r_m = float(node.get("radius_m") or 500)
    phase = tick * 0.00015 + hash(node.get("id") or "") % 100
    dlat = (math.sin(phase) * r_m) / 111_320.0
    dlon = (math.cos(phase * 1.3) * r_m) / (111_320.0 * max(0.2, math.cos(math.radians(lat))))
    return lat + dlat, lon + dlon


def _aggregate_user_gps(decimals: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        from backend.services.user_location_service import user_location_service

        data = user_location_service._load()
        for uid, entry in (data or {}).items():
            lat = entry.get("latitude")
            lon = entry.get("longitude")
            if lat is None or lon is None:
                continue
            clat = coarse_coord(lat, decimals)
            clon = coarse_coord(lon, decimals)
            out.append(
                {
                    "id": _anon_marker_id(f"gps:{uid}:{clat}:{clon}"),
                    "kind": "gps",
                    "source": "profile_gps",
                    "latitude": clat,
                    "longitude": clon,
                    "label": (entry.get("geo_ref") or "GPS fix")[:32],
                    "accuracy_m": entry.get("accuracy"),
                    "updated_at": entry.get("updated_at"),
                }
            )
    except Exception:
        pass
    return out[:48]


def _recent_pings(decimals: int, limit: int = 80) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not os.path.isfile(_GEO_LOG_FILE):
        return rows
    try:
        with open(_GEO_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                rows.append(row)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for row in rows[-limit:]:
        lat = row.get("latitude")
        lon = row.get("longitude")
        if lat is None or lon is None:
            continue
        kind = row.get("kind") or "gps"
        out.append(
            {
                "id": row.get("id") or _anon_marker_id(line),
                "kind": kind,
                "source": row.get("source") or "browser",
                "latitude": coarse_coord(lat, decimals),
                "longitude": coarse_coord(lon, decimals),
                "accuracy_m": row.get("accuracy_m"),
                "at": row.get("at"),
            }
        )
    return out


def record_geo_ping(
    *,
    latitude: float,
    longitude: float,
    accuracy_m: Optional[float] = None,
    source: str = "browser_gps",
    kind: str = "gps",
    guest_ref: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = _geo_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "geo_disabled"}
    if latitude is None or longitude is None:
        return {"success": False, "error": "missing_coords"}
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        return {"success": False, "error": "invalid_coords"}
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return {"success": False, "error": "out_of_range"}

    decimals = int(cfg.get("coarse_decimals") or 2)
    row = {
        "id": uuid.uuid4().hex[:12],
        "latitude": coarse_coord(lat, decimals),
        "longitude": coarse_coord(lon, decimals),
        "accuracy_m": float(accuracy_m) if accuracy_m is not None else None,
        "source": (source or "browser_gps")[:32],
        "kind": "gprs" if kind == "gprs" else "gps",
        "at": _iso(),
        "guest_ref": _anon_marker_id(guest_ref or uuid.uuid4().hex[:8]),
    }
    os.makedirs(_GEO_LOG_DIR, exist_ok=True)
    with open(_GEO_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"success": True, "ping": row}


def _map_urls(center_lat: float, center_lon: float, zoom: int) -> Dict[str, str]:
    lat = center_lat
    lon = center_lon
    z = max(8, min(15, zoom))
    pad = 0.04
    google = (
        f"https://maps.google.com/maps?q={lat},{lon}&hl=en&z={z}&output=embed"
    )
    osm = (
        "https://www.openstreetmap.org/export/embed.html?"
        f"bbox={lon - pad},{lat - pad * 0.7},{lon + pad},{lat + pad * 0.7}"
        f"&layer=mapnik&marker={lat},{lon}"
    )
    return {"google_embed": google, "osm_embed": osm, "google_maps_link": f"https://www.google.com/maps?q={lat},{lon}&z={z}"}


def public_geo_snapshot() -> Dict[str, Any]:
    cfg = _geo_config()
    if not cfg.get("enabled", True):
        return {"success": True, "enabled": False, "markers": [], "maps": {}}

    decimals = int(cfg.get("coarse_decimals") or 2)
    tick = time.time()
    gprs_markers: List[Dict[str, Any]] = []
    for node in _load_gprs_nodes():
        lat, lon = _gprs_live_position(node, tick)
        gprs_markers.append(
            {
                "id": str(node.get("id")),
                "kind": "gprs",
                "source": "gprs_cell",
                "label": str(node.get("label") or node.get("id")),
                "mcc_mnc": node.get("mcc_mnc"),
                "latitude": coarse_coord(lat, decimals + 1),
                "longitude": coarse_coord(lon, decimals + 1),
                "at": _iso(),
            }
        )

    profile_gps = _aggregate_user_gps(decimals)
    live_pings = _recent_pings(decimals)
    markers = gprs_markers + profile_gps + live_pings

    center = dict(cfg["default_center"])
    if markers:
        center["latitude"] = coarse_coord(
            sum(m["latitude"] for m in markers) / len(markers), decimals
        )
        center["longitude"] = coarse_coord(
            sum(m["longitude"] for m in markers) / len(markers), decimals
        )

    maps = _map_urls(center["latitude"], center["longitude"], int(cfg.get("map_zoom") or 11))
    gps_count = sum(1 for m in markers if m.get("kind") == "gps")
    gprs_count = sum(1 for m in markers if m.get("kind") == "gprs")

    return {
        "success": True,
        "enabled": True,
        "generated_at": _iso(),
        "center": center,
        "counts": {"gps": gps_count, "gprs": gprs_count, "total": len(markers)},
        "markers": markers[:64],
        "maps": maps,
        "poll_ms": {
            "gps": int(cfg.get("gps_poll_ms") or 15000),
            "gprs": int(cfg.get("gprs_poll_ms") or 20000),
        },
        "auto_assign_agent_on_stream": bool(cfg.get("auto_assign_agent_on_stream", True)),
    }


def start_livestream_session(user_id: str) -> Dict[str, Any]:
    """Assign YouTube stream agents and publish a fleet events line."""
    from backend.services.fleet_stream_chat_service import live_config, youtube_public_urls
    from backend.services.youtube_stream_agent_service import assign_youtube_stream_agents

    cfg = live_config()
    assign = assign_youtube_stream_agents(user_id, "youtube_stream_agent")
    geo = public_geo_snapshot()
    yt = youtube_public_urls(cfg)

    event_msg = None
    try:
        from backend.services.fleet_stream_chat_service import _append_message

        stream_meta = cfg.get("stream") if isinstance(cfg.get("stream"), dict) else {}
        title = stream_meta.get("title") or "Fleet livestream"
        event_msg = _append_message(
            {
                "id": uuid.uuid4().hex[:16],
                "channel": "events",
                "at": _iso(),
                "handle": "YouTube stream agent",
                "text": f"▶ Live session started — {title}. GPS/GPRS telemetry active. "
                f"Agents assigned: {assign.get('success')}.",
                "kind": "event",
                "event_id": "stream_go_live",
            }
        )
    except Exception:
        pass

    discord_result: Dict[str, Any] = {}
    try:
        from backend.services.fleet_stream_discord_service import publish_fleet_live_to_discord

        discord_result = publish_fleet_live_to_discord(
            message_id=f"fleet-live:go-live:{_iso()[:13]}",
        )
    except Exception:
        discord_result = {"success": False, "error": "discord_publish_failed"}

    return {
        "success": True,
        "assign": assign,
        "geo": geo,
        "youtube": yt,
        "event_message": event_msg,
        "discord": discord_result,
    }
