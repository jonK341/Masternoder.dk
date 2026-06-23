"""
Unified conservation gate — aggregates reconcile checks across MN2, arena, and casino.

Surfaced at GET /api/mn2/ops/conservation-gate and used by scripts/verify_mn2_production_ready.py.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def _arena_reconcile_all() -> Dict[str, Any]:
    try:
        from backend.services import arena_economy

        state = arena_economy._load_state()
        events = state.get("events") or {}
        items: Dict[str, Any] = {}
        ok = True
        for eid in events:
            r = arena_economy.reconcile(eid)
            items[eid] = r
            if not r.get("balanced"):
                ok = False
        return {"ok": ok, "events": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e), "events": {}, "count": 0}


def conservation_gate() -> Dict[str, Any]:
    """Run all hard conservation checks. `verdict` is green | amber | red."""
    checks: List[Dict[str, Any]] = []
    hard_fail = False

    # 1. MN2 staking reconcile (canonical)
    staking = {"ok": False, "failed_checks": [], "error": None}
    try:
        from backend.services.mn2_staking_reconcile_service import reconcile as _recon

        r = _recon()
        staking = {
            "ok": bool(r.get("ok")),
            "failed_checks": r.get("failed_checks") or [],
            "totals": r.get("totals"),
        }
        checks.append({"name": "mn2_staking_reconcile", "ok": staking["ok"], "hard": True})
        if not staking["ok"]:
            hard_fail = True
    except Exception as e:
        staking["error"] = str(e)
        checks.append({"name": "mn2_staking_reconcile", "ok": False, "hard": True, "error": str(e)})
        hard_fail = True

    # 2. Casino tournaments pool conservation
    tournaments = {"ok": True, "tournaments": {}}
    try:
        from backend.services import casino_tournaments

        tr = casino_tournaments.reconcile()
        tournaments = tr
        tok = bool(tr.get("ok", True))
        checks.append({"name": "casino_tournaments_reconcile", "ok": tok, "hard": True})
        if not tok:
            hard_fail = True
    except Exception as e:
        tournaments = {"ok": False, "error": str(e)}
        checks.append({"name": "casino_tournaments_reconcile", "ok": False, "hard": True, "error": str(e)})
        hard_fail = True

    # 3. Arena escrow per-event (soft if no events)
    arena = _arena_reconcile_all()
    arena_ok = bool(arena.get("ok", True))
    checks.append({
        "name": "arena_escrow_reconcile",
        "ok": arena_ok,
        "hard": arena.get("count", 0) > 0,
        "event_count": arena.get("count", 0),
    })
    if arena.get("count", 0) > 0 and not arena_ok:
        hard_fail = True

    # 4. Generation pipeline readiness (amber if not ready — does not block green money gate)
    gen = {"ready": None, "message": None}
    try:
        from backend.services.video_generator_service import _check_generation_services

        ok, msg, detail = _check_generation_services()
        gen = {"ready": ok, "message": msg, "detail": detail}
        checks.append({"name": "generation_health", "ok": ok, "hard": False})
    except Exception as e:
        gen = {"ready": False, "error": str(e)}
        checks.append({"name": "generation_health", "ok": False, "hard": False, "error": str(e)})

    if hard_fail:
        verdict = "red"
    elif gen.get("ready") is False:
        verdict = "amber"
    else:
        verdict = "green"

    return {
        "success": True,
        "verdict": verdict,
        "ok": verdict == "green",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "checks": checks,
        "staking_reconcile": staking,
        "casino_tournaments": tournaments,
        "arena": arena,
        "generation_health": gen,
    }
