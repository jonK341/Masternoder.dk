"""5D monitor pulse feed — short narrative beats for /aggregator and profit TV."""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PULSE_PATH = os.path.join(_BASE, "data", "monitor_5d_pulse.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load() -> Dict[str, Any]:
    if not os.path.isfile(_PULSE_PATH):
        return {"items": []}
    try:
        import json
        with open(_PULSE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"items": []}
    except Exception:
        return {"items": []}


def _save(data: Dict[str, Any]) -> None:
    import json
    os.makedirs(os.path.dirname(_PULSE_PATH), exist_ok=True)
    tmp = _PULSE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _PULSE_PATH)


def emit_pulse(
    title: str,
    *,
    summary: str = "",
    sigma: float = 0.55,
    context: str = "aggregator",
    href: str = "/business-control/",
    source: str = "unified_daemon",
) -> Dict[str, Any]:
    """Append a pulse row for the 5D story monitor UI."""
    title = (title or "").strip()[:160]
    if not title:
        return {"success": False, "error": "empty_title"}
    row = {
        "ts": _iso(),
        "title": title,
        "summary": (summary or title)[:240],
        "sigma": max(0.05, min(0.99, float(sigma))),
        "context": (context or "aggregator")[:32],
        "href": href or "/aggregator/",
        "source": source,
    }
    with _LOCK:
        data = _load()
        items = data.get("items") if isinstance(data.get("items"), list) else []
        items.insert(0, row)
        data["items"] = items[:120]
        data["updated_at"] = _iso()
        _save(data)
    return {"success": True, "pulse": row}


def recent(limit: int = 30) -> Dict[str, Any]:
    data = _load()
    items = data.get("items") if isinstance(data.get("items"), list) else []
    safe = max(1, min(int(limit or 30), 80))
    return {"success": True, "items": items[:safe], "updated_at": data.get("updated_at")}


def publish_unified_event(
    event_kind: str,
    headline: str,
    *,
    detail: str = "",
    featured: bool = False,
) -> None:
    """Fan-out to 5D pulse (news handled by profit_daemon_news_service)."""
    kind = (event_kind or "ops").strip()
    sigma_map = {
        "arb_fill": 0.82,
        "grid_fill": 0.68,
        "stuck_unstick": 0.74,
        "micro_chain": 0.61,
        "casino": 0.58,
        "unified": 0.5,
    }
    try:
        emit_pulse(
            headline,
            summary=detail or headline,
            sigma=sigma_map.get(kind, 0.55),
            context="aggregator",
            href="/business-control/",
            source=f"unified_{kind}",
        )
    except Exception:
        pass
