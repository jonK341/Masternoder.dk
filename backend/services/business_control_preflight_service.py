"""Business Control Phase 6 — preflight checks (local + HTTP-shaped)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _check(checks: List[Dict[str, Any]], cid: str, ok: bool, detail: str = "", **extra: Any) -> bool:
    row: Dict[str, Any] = {"id": cid, "ok": bool(ok), "detail": detail or ""}
    row.update(extra)
    checks.append(row)
    return bool(ok)


def run_preflight(*, light_overview: bool = True) -> Dict[str, Any]:
    """Run local preflight checks. Does not mutate runtime state."""
    checks: List[Dict[str, Any]] = []
    all_ok = True

    try:
        from backend.services.trading_bots_control_service import (
            _load_controls,
            business_overview,
            live_pack_status,
        )

        controls = _load_controls()
        _check(checks, "controls_load", True, "trading_bots_control.json loaded")
        sups = controls.get("supervisors") or []
        all_ok &= _check(checks, "supervisors_present", len(sups) >= 7, f"{len(sups)} supervisors")

        ov = business_overview(light=light_overview)
        all_ok &= _check(checks, "overview", bool(ov.get("success")), "business_overview light")
        bots = ov.get("bots") or []
        all_ok &= _check(checks, "bots_list", len(bots) > 0, f"{len(bots)} bots in overview")

        sf = ov.get("supervisor_fleet") or {}
        fleet_bots = sf.get("bots") or []
        all_ok &= _check(
            checks, "fleet_count", len(fleet_bots) == 23,
            f"{len(fleet_bots)} fleet bots (expected 23)",
        )
        all_ok &= _check(
            checks, "fleet_mechanics", int(sf.get("mechanics_count") or 0) == 25,
            "M01–M25 registry",
        )
        health = sf.get("health") or {}
        all_ok &= _check(
            checks, "fleet_health", health.get("bot_count") == 23,
            f"health bot_count={health.get('bot_count')}",
        )

        orch = ov.get("orchestration")
        all_ok &= _check(checks, "orchestration_schema", isinstance(orch, dict), "orchestration object present")

        lp = live_pack_status(light=True)
        all_ok &= _check(checks, "live_pack_light", bool(lp.get("success")), f"mode={lp.get('mode')}")
        _check(
            checks, "profit_live_ready",
            bool(lp.get("profit_live_ready")),
            "optional live gate" if lp.get("profit_live_ready") else "paper/partial — not a hard fail",
            optional=True,
        )
    except Exception as exc:
        all_ok = False
        _check(checks, "preflight_exception", False, str(exc)[:240])

    hard_fail = any(not c.get("ok") for c in checks if not c.get("optional"))
    return {
        "success": not hard_fail,
        "checks": checks,
        "check_count": len(checks),
        "failed": [c["id"] for c in checks if not c.get("ok") and not c.get("optional")],
    }


def run_http_preflight(base_url: str, admin_key: str, *, timeout: float = 60.0) -> Dict[str, Any]:
    """GET overview + preflight route against a running app."""
    import json
    import urllib.error
    import urllib.request

    checks: List[Dict[str, Any]] = []
    base = (base_url or "").rstrip("/")
    headers = {"X-Exchange-Admin-Key": admin_key}

    def _get(path: str) -> Dict[str, Any]:
        req = urllib.request.Request(base + path, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    all_ok = True
    try:
        pf = _get("/api/exchange/control-board/preflight")
        all_ok &= _check(checks, "http_preflight_route", bool(pf.get("success")), "control-board/preflight")
    except Exception as exc:
        all_ok = False
        _check(checks, "http_preflight_route", False, str(exc)[:200])

    try:
        ov = _get("/api/exchange/control-board/overview?light=1")
        all_ok &= _check(checks, "http_overview", bool(ov.get("success")), "overview light=1")
        sf = ov.get("supervisor_fleet") or {}
        all_ok &= _check(
            checks, "http_fleet",
            len(sf.get("bots") or []) == 23,
            f"fleet bots={len(sf.get('bots') or [])}",
        )
    except Exception as exc:
        all_ok = False
        _check(checks, "http_overview", False, str(exc)[:200])

    return {"success": all_ok, "checks": checks, "base": base}
