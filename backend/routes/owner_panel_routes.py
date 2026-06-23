"""Owner Cockpit — solo-owner private control panel at /owner.

Portal consolidation: public nav no longer links debugger/master_control/agents_control.
Those URLs gate here (ops session) or redirect to /owner#tools-* anchors.
User-facing portal stays: command-center, profile, /agents catalog, game pages.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request, session

from backend.services.ops_auth_service import (
    SESSION_KEY as _SESSION_KEY,
    ops_ok as _ops_ok,
    secret_matches as _secret_matches,
)

owner_panel_bp = Blueprint("owner_panel", __name__)

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_OWNER_HTML = os.path.join(_BASE, "dashboard", "owner", "index.html")


def _require_ops():
    if not _ops_ok():
        return jsonify({"success": False, "error": "unauthorized"}), 403
    return None


def _last_cron_snapshot() -> Optional[Dict[str, Any]]:
    log_dir = os.path.join(_BASE, "logs", "agent_cron")
    if not os.path.isdir(log_dir):
        return None
    best: Optional[Dict[str, Any]] = None
    best_ts = ""
    for fname in sorted(os.listdir(log_dir)):
        if not fname.endswith(".jsonl"):
            continue
        path = os.path.join(log_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            if not lines:
                continue
            row = json.loads(lines[-1])
            ts = str(row.get("at") or row.get("ran_at") or row.get("ts") or "")
            if ts >= best_ts:
                best_ts = ts
                best = {"source": fname, "at": ts, "row": row}
        except Exception:
            continue
    return best


def _recent_audit(limit: int = 8) -> List[Dict[str, Any]]:
    path = os.path.join(_BASE, "logs", "admin_audit.jsonl")
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return list(reversed(rows[-limit:]))


def _health_snapshot() -> Dict[str, Any]:
    out: Dict[str, Any] = {"ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    try:
        from backend.services.agent_kill_switch import get_status
        ks = get_status()
        out["agents_halted"] = bool(ks.get("global_halt"))
        out["kill_switch"] = ks
    except Exception as exc:
        out["agents_halted"] = None
        out["kill_switch"] = {"error": str(exc)}
    try:
        from backend.services.video_generator_service import _check_generation_services
        ok, msg, detail = _check_generation_services()
        out["generation"] = {"ready": ok, "message": msg, "detail": detail}
    except Exception as exc:
        out["generation"] = {"ready": False, "error": str(exc)}
    try:
        from backend.services.worker_pressure_service import worker_pressure
        wp = worker_pressure()
        out["worker_pressure"] = {
            "score": wp.get("score"),
            "recommendation": wp.get("recommendation"),
        }
    except Exception as exc:
        out["worker_pressure"] = {"error": str(exc)}
    try:
        from backend.services.mn2_conservation_gate import conservation_gate
        cg = conservation_gate()
        out["conservation"] = {"ok": cg.get("ok"), "verdict": cg.get("verdict")}
    except Exception as exc:
        out["conservation"] = {"error": str(exc)}
    out["app"] = {"status": "healthy"}
    return out


def _agents_snapshot() -> Dict[str, Any]:
    from backend.services.agent_kill_switch import get_status
    from backend.services.agent_wallet_service import (
        get_treasury,
        get_treasury_pool_balance,
        list_wallets,
    )
    from backend.services.agent_trader_service import list_strategies

    treasury = get_treasury()
    cust_stats: Dict[str, Any] = {}
    try:
        from backend.services.customer_aggregator_service import stats
        cust_stats = stats()
    except Exception as exc:
        cust_stats = {"error": str(exc)}

    return {
        "kill_switch": get_status(),
        "treasury": treasury,
        "treasury_pool_mn2": get_treasury_pool_balance(),
        "wallets": list_wallets(),
        "strategies": list_strategies(),
        "last_cron": _last_cron_snapshot(),
        "customer_aggregator": cust_stats,
        "links": {
            "agents_control": "/dashboard/agents_control",
            "agent_cron_presets": "/api/agents/cron/presets",
            "treasury": "/api/agents/treasury/address",
            "customers": "/api/customers/stats",
        },
    }


def _ai_snapshot() -> Dict[str, Any]:
    from backend.services.llm_service import get_provider_status, TASK_ROUTES

    providers = get_provider_status()
    configured = [p for p in providers if p.get("configured")]
    available = [p for p in providers if p.get("available")]
    queue: Dict[str, Any] = {}
    try:
        from backend.services.video_job_queue import queue_status
        queue = queue_status()
    except Exception as exc:
        queue = {"error": str(exc)}
    gen_ops: Dict[str, Any] = {}
    try:
        from backend.services.generator_agent_service import get_generator_ops_snapshot
        gen_ops = get_generator_ops_snapshot()
    except Exception as exc:
        gen_ops = {"error": str(exc)}
    generation: Dict[str, Any] = {}
    try:
        from backend.services.video_generator_service import _check_generation_services
        ok, msg, detail = _check_generation_services()
        generation = {"ready": ok, "message": msg, "detail": detail}
    except Exception as exc:
        generation = {"ready": False, "error": str(exc)}
    worker: Dict[str, Any] = {}
    try:
        from backend.services.worker_pressure_service import worker_pressure
        worker = worker_pressure()
    except Exception as exc:
        worker = {"error": str(exc)}

    return {
        "providers": providers,
        "summary": {
            "total": len(providers),
            "configured": len(configured),
            "available": len(available),
            "task_routes": {k: list(v) for k, v in TASK_ROUTES.items()},
        },
        "video_queue": queue,
        "generation": generation,
        "generator_ops": gen_ops,
        "worker_pressure": worker,
        "last_llm_snapshot": _last_llm_snapshot(),
        "links": {
            "providers": "/api/ai/providers",
            "capability_map": "/api/agents/capability-map",
            "queue_status": "/api/generator/queue-status",
            "ops_public_snapshot": "/api/ops/public-snapshot",
        },
    }


def _crypto_snapshot() -> Dict[str, Any]:
    from backend.services.agent_wallet_service import (
        get_treasury,
        get_treasury_pool_balance,
    )

    out: Dict[str, Any] = {}
    try:
        from backend.services.mn2_conservation_gate import conservation_gate
        out["conservation"] = conservation_gate()
    except Exception as exc:
        out["conservation"] = {"error": str(exc)}

    staking: Dict[str, Any] = {}
    try:
        import backend.services.mn2_staking_service as staking_svc
        cfg = staking_svc.get_config()
        staking = {
            "enabled": cfg.get("enabled"),
            "min_stake": cfg.get("min_stake"),
            "max_stake_per_user": cfg.get("max_stake_per_user"),
            "apr_percent": staking_svc.dynamic_apr(),
            "instant_unstake": cfg.get("instant_unstake"),
        }
    except Exception as exc:
        staking = {"error": str(exc)}
    out["staking"] = staking

    por: Dict[str, Any] = {}
    try:
        from backend.services.mn2_proof_of_reserves_service import proof_of_reserves
        raw = proof_of_reserves()
        por = {
            "coverage_ratio": raw.get("coverage_ratio"),
            "fully_backed": raw.get("fully_backed"),
            "liabilities_total_mn2": raw.get("liabilities_total_mn2"),
            "assets_total_mn2": raw.get("assets_total_mn2"),
            "reconcile_ok": (raw.get("reconcile") or {}).get("ok"),
        }
    except Exception as exc:
        por = {"error": str(exc)}
    out["proof_of_reserves"] = por

    price: Dict[str, Any] = {}
    try:
        from backend.services.mn2_chainz import mn2_usd_price_median
        bundle = mn2_usd_price_median()
        if isinstance(bundle, dict):
            price = {
                "mn2_usd_price": bundle.get("price"),
                "source": bundle.get("source_label"),
                "last_updated_iso": bundle.get("last_updated_iso"),
            }
    except Exception as exc:
        price = {"error": str(exc)}
    out["mn2_price"] = price

    treasury = get_treasury()
    out["treasury"] = {
        **treasury,
        "treasury_pool_mn2": get_treasury_pool_balance(),
    }

    monetization: Dict[str, Any] = {}
    try:
        from backend.services.monetization_config_service import get_public_config
        pub = get_public_config()
        monetization = {
            "paypal_webhook_configured": pub.get("paypal_webhook_configured"),
            "tier_enforcement_enabled": pub.get("tier_enforcement_enabled"),
            "subscription_pro_live": pub.get("subscription_pro_live"),
            "default_tier": pub.get("default_tier"),
            "coin_pack_count": len(pub.get("coin_packs") or []),
            "payment_rails": list((pub.get("payment_rails_catalog") or {}).get("rails") or []),
        }
    except Exception as exc:
        monetization = {"error": str(exc)}
    try:
        from backend.services.paypal_service import get_access_token
        monetization["paypal_api_reachable"] = get_access_token() is not None
    except Exception:
        monetization["paypal_api_reachable"] = False
    monetization["paypal_configured"] = bool(
        (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
        and (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
    )
    monetization["paypal_mode"] = (os.environ.get("PAYPAL_MODE") or "sandbox").strip()
    out["monetization"] = monetization

    out["links"] = {
        "mn2_balance": "/api/mn2/balance",
        "staking_config": "/api/mn2/staking/config",
        "proof_of_reserves": "/api/mn2/staking/proof-of-reserves",
        "conservation_gate": "/api/mn2/ops/conservation-gate",
        "treasury": "/api/agents/treasury/address",
        "monetization_config": "/api/shop/monetization/config",
    }
    return out


def _video_generation_providers() -> List[Dict[str, Any]]:
    """Mirror /api/ai/video-providers without a Flask request."""
    providers: List[Dict[str, Any]] = []
    try:
        from backend.services.runwayml_service import is_available as runway_ok
        providers.append({"name": "RunwayML Gen-4", "key_env": "RUNWAYML_API_KEY", "available": runway_ok(), "type": "video"})
    except Exception:
        providers.append({"name": "RunwayML Gen-4", "key_env": "RUNWAYML_API_KEY", "available": False, "type": "video"})
    try:
        from backend.services.modelslab_video_service import is_available as ml_ok
        providers.append({"name": "ModelsLab", "key_env": "MODELSLAB_API_KEY", "available": ml_ok(), "type": "video"})
    except Exception:
        providers.append({"name": "ModelsLab", "key_env": "MODELSLAB_API_KEY", "available": False, "type": "video"})
    try:
        from backend.services.replicate_video_service import is_available as replicate_ok
        providers.append({"name": "Replicate SVD", "key_env": "REPLICATE_API_TOKEN", "available": replicate_ok(), "type": "video"})
    except Exception:
        providers.append({"name": "Replicate SVD", "key_env": "REPLICATE_API_TOKEN", "available": False, "type": "video"})
    try:
        from backend.services.stability_image_service import is_available as stab_ok
        providers.append({"name": "Stability AI", "key_env": "STABILITY_AI_API_KEY", "available": stab_ok(), "type": "image"})
    except Exception:
        providers.append({"name": "Stability AI", "key_env": "STABILITY_AI_API_KEY", "available": False, "type": "image"})
    providers.append({"name": "Pollinations.ai", "key_env": None, "available": True, "type": "image", "note": "free/unlimited"})
    return providers


def _models_snapshot() -> Dict[str, Any]:
    from backend.services.llm_service import get_provider_status, TASK_ROUTES

    providers = get_provider_status()
    configured = [p for p in providers if p.get("configured")]
    available = [p for p in providers if p.get("available")]

    generation: Dict[str, Any] = {}
    try:
        from backend.services.video_generator_service import _check_generation_services
        ok, msg, detail = _check_generation_services()
        generation = {"ready": ok, "message": msg, "detail": detail}
    except Exception as exc:
        generation = {"ready": False, "error": str(exc)}

    video_providers = _video_generation_providers()
    gen_ops: Dict[str, Any] = {}
    try:
        from backend.services.generator_agent_service import get_generator_ops_snapshot
        gen_ops = get_generator_ops_snapshot()
    except Exception as exc:
        gen_ops = {"error": str(exc)}

    env_models = {
        "OPENAI_MODEL": (os.environ.get("OPENAI_MODEL") or "").strip() or None,
        "OPENAI_MODEL_BEST": (os.environ.get("OPENAI_MODEL_BEST") or "").strip() or None,
        "LLM_PREFER_FREE": (os.environ.get("LLM_PREFER_FREE") or "").strip() or None,
        "HF_TOKEN": bool((os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN") or "").strip()),
        "HF_MODEL_ID": (os.environ.get("HF_MODEL_ID") or os.environ.get("HUGGINGFACE_MODEL") or "").strip() or None,
    }

    return {
        "llm_providers": providers,
        "summary": {
            "llm_total": len(providers),
            "llm_configured": len(configured),
            "llm_available": len(available),
            "video_providers_total": len(video_providers),
            "video_providers_available": sum(1 for p in video_providers if p.get("available")),
            "task_routes": {k: list(v) for k, v in TASK_ROUTES.items()},
        },
        "video_providers": video_providers,
        "generation": generation,
        "generator_ops": gen_ops,
        "env_models": env_models,
        "links": {
            "llm_providers": "/api/ai/providers",
            "video_providers": "/api/ai/video-providers",
            "queue_status": "/api/generator/queue-status",
        },
    }


def _moderation_basics() -> Dict[str, Any]:
    path = os.path.join(_BASE, "data", "social_structure.json")
    if not os.path.isfile(path):
        return {"blocks": 0, "reports": 0, "hidden_activity_users": 0}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        mod = data.get("moderation") if isinstance(data.get("moderation"), dict) else {}
        blocks = mod.get("blocks") if isinstance(mod.get("blocks"), dict) else {}
        reports = mod.get("reports") if isinstance(mod.get("reports"), list) else []
        hidden = mod.get("hidden_activity") if isinstance(mod.get("hidden_activity"), dict) else {}
        block_pairs = sum(len(v) if isinstance(v, list) else 1 for v in blocks.values())
        return {
            "blocks": block_pairs,
            "reports": len(reports),
            "hidden_activity_users": len(hidden),
        }
    except Exception as exc:
        return {"error": str(exc)}


def _users_snapshot() -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import is_earn_eligible_user

    cust_stats: Dict[str, Any] = {}
    earn_eligible = 0
    sample: List[Dict[str, Any]] = []
    try:
        from backend.services.customer_aggregator_service import stats, list_customers
        cust_stats = stats()
        listing = list_customers(limit=5000, offset=0)
        customers = listing.get("customers") or []
        earn_eligible = sum(1 for c in customers if is_earn_eligible_user(c.get("user_id")))
        sample = customers[:8]
    except Exception as exc:
        cust_stats = {"error": str(exc)}

    oauth: Dict[str, Any] = {}
    try:
        from backend.services.social_auth_service import list_providers
        oauth = list_providers()
    except Exception as exc:
        oauth = {"error": str(exc)}

    return {
        "customer_aggregator": cust_stats,
        "earn_eligible_users": earn_eligible,
        "recent_customers": sample,
        "oauth": oauth,
        "moderation": _moderation_basics(),
        "links": {
            "customers": "/api/customers",
            "customer_stats": "/api/customers/stats",
            "auth_providers": "/api/auth/providers",
        },
    }


def _route_exists(fragment: str) -> bool:
    try:
        from flask import current_app
        frag = fragment.rstrip("/")
        for rule in current_app.url_map.iter_rules():
            r = str(rule.rule)
            if r == frag or r.startswith(frag + "/") or frag in r:
                return True
    except Exception:
        pass
    return False


def _tools_catalog() -> List[Dict[str, Any]]:
    """Static owner-ops tool registry with safe launch links."""
    return [
        {
            "id": "debugger",
            "name": "Production Debugger",
            "category": "diagnostics",
            "description": "Scanner, agent fixes, quiz, route diagnostics",
            "href": "/debugger",
            "action": "link",
            "dangerous": False,
        },
        {
            "id": "api_monitor",
            "name": "API Monitor",
            "category": "diagnostics",
            "description": "Live endpoint probe dashboard at /api/",
            "href": "/api/",
            "action": "link",
            "dangerous": False,
        },
        {
            "id": "point_control_board",
            "name": "Point Control Board",
            "category": "diagnostics",
            "description": "Unified points systems status",
            "href": "/api/control-board/status",
            "action": "read",
            "dangerous": False,
        },
        {
            "id": "register_intelligence",
            "name": "Register Intelligence Audit",
            "category": "registry",
            "description": "Blueprint/route discovery and frontend parity gaps",
            "href": "/api/register-intelligence/audit",
            "action": "read",
            "quick_run": "register_intelligence",
            "dangerous": False,
        },
        {
            "id": "route_scanner",
            "name": "Route Scanner",
            "category": "registry",
            "description": "List registered Flask routes",
            "href": "/api/debugger/scanner/routes",
            "action": "read",
            "dangerous": False,
        },
        {
            "id": "missing_routes",
            "name": "Missing Route Scanner",
            "category": "registry",
            "description": "Frontend API paths without backend handlers",
            "href": "/api/debugger/scanner/missing",
            "action": "read",
            "dangerous": False,
        },
        {
            "id": "404_log",
            "name": "404 Occurrence Log",
            "category": "registry",
            "description": "Tail register_intelligence 404 JSONL",
            "href": None,
            "action": "read",
            "quick_run": "404_tail",
            "dangerous": False,
        },
        {
            "id": "admin_audit",
            "name": "Admin Audit Log",
            "category": "ops",
            "description": "Recent owner/admin actions",
            "href": None,
            "action": "read",
            "quick_run": "audit_tail",
            "dangerous": False,
        },
        {
            "id": "ops_snapshot",
            "name": "Ops Public Snapshot",
            "category": "ops",
            "description": "Generator queue, worker pressure, conservation",
            "href": "/api/ops/public-snapshot",
            "action": "read",
            "dangerous": False,
        },
        {
            "id": "debugger_tools",
            "name": "Debugger Download Tools",
            "category": "diagnostics",
            "description": "Standalone debugger scripts (Python, bash, PS)",
            "href": "/api/debugger/tools",
            "action": "read",
            "dangerous": False,
        },
        {
            "id": "compendium",
            "name": "Compendium",
            "category": "content",
            "description": "Rulebook compendium pages and access",
            "href": "/compendium",
            "action": "link",
            "dangerous": False,
        },
        {
            "id": "rulebooks",
            "name": "Rulebooks Index",
            "category": "content",
            "description": "V1–V16 rulebook catalog API",
            "href": "/api/rulebooks/index",
            "action": "read",
            "dangerous": False,
        },
        {
            "id": "gallery",
            "name": "Gallery",
            "category": "content",
            "description": "Generated video gallery",
            "href": "/gallery",
            "action": "link",
            "dangerous": False,
        },
        {
            "id": "aggregator_catalog",
            "name": "Aggregator Catalog",
            "category": "content",
            "description": "Intel / agent aggregator seeds",
            "href": "/api/aggregators/catalog",
            "action": "read",
            "dangerous": False,
        },
        {
            "id": "debugger_agent_fix",
            "name": "Debugger Agent Fix",
            "category": "diagnostics",
            "description": "POST agent personality/mission/quest repairs",
            "href": "/api/debugger/agent/fix-all",
            "action": "write",
            "dangerous": True,
        },
        {
            "id": "deploy",
            "name": "Deploy Script",
            "category": "deploy",
            "description": "scripts/deploy.py — server-side only; uploads + restart",
            "href": None,
            "action": "write",
            "dangerous": True,
        },
    ]


def _tool_status(tool: Dict[str, Any]) -> str:
    tid = tool["id"]
    href = tool.get("href")
    if tid == "404_log":
        path = os.path.join(_BASE, "logs", "register_intelligence", "404_occurrences.jsonl")
        return "available" if os.path.isfile(path) else "unavailable"
    if tid == "admin_audit":
        path = os.path.join(_BASE, "logs", "admin_audit.jsonl")
        return "available" if os.path.isfile(path) else "unavailable"
    if tid == "deploy":
        path = os.path.join(_BASE, "scripts", "deploy.py")
        return "available" if os.path.isfile(path) else "unavailable"
    if tid == "register_intelligence":
        try:
            from backend.services.register_intelligence import run_register_intelligence  # noqa: F401
            return "available"
        except Exception:
            return "unavailable"
    if href:
        return "available" if _route_exists(href.split("?")[0]) else "unavailable"
    return "available"


def _tools_snapshot() -> Dict[str, Any]:
    tools: List[Dict[str, Any]] = []
    by_category: Dict[str, List[str]] = {}
    for raw in _tools_catalog():
        entry = dict(raw)
        entry["status"] = _tool_status(raw)
        tools.append(entry)
        cat = entry["category"]
        by_category.setdefault(cat, []).append(entry["id"])
    return {
        "tools": tools,
        "categories": {
            "diagnostics": "Diagnostics & debug",
            "registry": "Routes & registry",
            "ops": "Ops & audit",
            "content": "Content & catalogs",
            "deploy": "Deploy (dangerous)",
        },
        "by_category": by_category,
        "quick_runs": ["audit_tail", "404_tail", "register_intelligence"],
    }


def _tail_jsonl(rel_path: str, limit: int = 20) -> List[Dict[str, Any]]:
    path = os.path.join(_BASE, rel_path)
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return list(reversed(rows[-limit:]))


def _register_intelligence_summary() -> Dict[str, Any]:
    from backend.services.register_intelligence import run_register_intelligence
    report = run_register_intelligence(dry_run=True, discover_only=False)
    disc = report.get("discovery") or {}
    summary = report.get("summary") or {}
    missing = disc.get("potential_missing") or []
    return {
        "summary": summary,
        "discovery": {
            "blueprints_count": disc.get("blueprints_count"),
            "backend_routes_count": disc.get("backend_routes_count"),
            "frontend_api_count": disc.get("frontend_api_count"),
            "potential_missing_count": len(missing),
            "potential_missing_sample": list(missing)[:12],
        },
        "ran_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _last_llm_snapshot() -> Optional[Dict[str, Any]]:
    path = os.path.join(_BASE, "logs", "agent_cron", "llm_provider_status.jsonl")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        if not lines:
            return None
        row = json.loads(lines[-1])
        return {"at": row.get("at"), "provider_count": len(row.get("providers") or [])}
    except Exception:
        return None


@owner_panel_bp.route("/owner", methods=["GET"])
@owner_panel_bp.route("/owner/", methods=["GET"])
def owner_page():
    if os.path.isfile(_OWNER_HTML):
        with open(_OWNER_HTML, "r", encoding="utf-8") as f:
            content = f.read()
        return content, 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}
    return (
        "<html><body><h1>Owner Cockpit</h1><p>dashboard/owner/index.html not found</p></body></html>",
        404,
    )


@owner_panel_bp.route("/owner/api/session", methods=["GET"])
def owner_session():
    return jsonify({"success": True, "authenticated": bool(_ops_ok())}), 200


@owner_panel_bp.route("/owner/api/auth", methods=["POST"])
def owner_auth():
    body = request.get_json(silent=True) or {}
    provided = (
        (body.get("secret") or "").strip()
        or (request.headers.get("X-Ops-Secret") or "").strip()
    )
    if _secret_matches(provided):
        session[_SESSION_KEY] = True
        session.permanent = True
        try:
            from backend.services.admin_audit_service import log_action
            log_action("owner_panel_login", actor="owner", payload={"via": "session"})
        except Exception:
            pass
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": "unauthorized"}), 403


@owner_panel_bp.route("/owner/api/logout", methods=["POST"])
def owner_logout():
    session.pop(_SESSION_KEY, None)
    return jsonify({"success": True}), 200


@owner_panel_bp.route("/owner/api/health", methods=["GET"])
def owner_health():
    denied = _require_ops()
    if denied:
        return denied
    return jsonify({"success": True, "health": _health_snapshot(), "audit": _recent_audit()}), 200


@owner_panel_bp.route("/owner/api/agents", methods=["GET"])
def owner_agents():
    denied = _require_ops()
    if denied:
        return denied
    return jsonify({"success": True, "agents": _agents_snapshot()}), 200


@owner_panel_bp.route("/owner/api/agents/halt", methods=["POST"])
def owner_agents_halt():
    denied = _require_ops()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    from backend.services.agent_kill_switch import set_switch
    result = set_switch(
        global_halt=bool(body.get("global_halt", True)),
        reason=body.get("reason") or "owner_halt",
        set_by="owner",
    )
    try:
        from backend.services.admin_audit_service import log_action
        log_action("owner_agents_halt", actor="owner", payload={"reason": body.get("reason")})
    except Exception:
        pass
    return jsonify({"success": True, "kill_switch": result}), 200


@owner_panel_bp.route("/owner/api/agents/resume", methods=["POST"])
def owner_agents_resume():
    denied = _require_ops()
    if denied:
        return denied
    from backend.services.agent_kill_switch import set_switch
    result = set_switch(global_halt=False, reason="owner_resume", set_by="owner")
    try:
        from backend.services.admin_audit_service import log_action
        log_action("owner_agents_resume", actor="owner")
    except Exception:
        pass
    return jsonify({"success": True, "kill_switch": result}), 200


@owner_panel_bp.route("/owner/api/ai", methods=["GET"])
def owner_ai():
    denied = _require_ops()
    if denied:
        return denied
    return jsonify({"success": True, "ai": _ai_snapshot()}), 200


@owner_panel_bp.route("/owner/api/ai/providers/reset", methods=["POST"])
def owner_ai_reset_provider():
    denied = _require_ops()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    provider = (body.get("provider") or "").strip()
    if not provider:
        return jsonify({"success": False, "error": "provider required"}), 400
    from backend.services.llm_service import reset_circuit
    ok = reset_circuit(provider)
    if not ok:
        return jsonify({"success": False, "error": f"unknown provider: {provider}"}), 400
    try:
        from backend.services.admin_audit_service import log_action
        log_action("owner_ai_circuit_reset", actor="owner", payload={"provider": provider})
    except Exception:
        pass
    return jsonify({"success": True, "provider": provider}), 200


@owner_panel_bp.route("/owner/api/crypto", methods=["GET"])
def owner_crypto():
    denied = _require_ops()
    if denied:
        return denied
    return jsonify({"success": True, "crypto": _crypto_snapshot()}), 200


@owner_panel_bp.route("/owner/api/crypto/conservation/recheck", methods=["POST"])
def owner_crypto_conservation_recheck():
    """Read-only re-run of conservation gate (no state mutation)."""
    denied = _require_ops()
    if denied:
        return denied
    try:
        from backend.services.mn2_conservation_gate import conservation_gate
        result = conservation_gate()
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    try:
        from backend.services.admin_audit_service import log_action
        log_action("owner_crypto_conservation_recheck", actor="owner", payload={"verdict": result.get("verdict")})
    except Exception:
        pass
    return jsonify({"success": True, "conservation": result}), 200


@owner_panel_bp.route("/owner/api/crypto/treasury/scan", methods=["POST"])
def owner_crypto_treasury_scan():
    denied = _require_ops()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    if not body.get("confirm"):
        return jsonify({"success": False, "error": "confirm:true required"}), 400
    try:
        from backend.services.agent_wallet_service import (
            get_treasury_pool_balance,
            scan_treasury_onchain_deposits,
            sync_treasury_pool_from_ledger,
        )
        scan = scan_treasury_onchain_deposits()
        sync_treasury_pool_from_ledger()
        pool = get_treasury_pool_balance()
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
    try:
        from backend.services.admin_audit_service import log_action
        log_action("owner_crypto_treasury_scan", actor="owner", payload={"pool_mn2": pool})
    except Exception:
        pass
    return jsonify({"success": True, "scan": scan, "treasury_pool_mn2": pool}), 200


@owner_panel_bp.route("/owner/api/models", methods=["GET"])
def owner_models():
    denied = _require_ops()
    if denied:
        return denied
    return jsonify({"success": True, "models": _models_snapshot()}), 200


@owner_panel_bp.route("/owner/api/models/providers/reset", methods=["POST"])
def owner_models_reset_provider():
    denied = _require_ops()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    provider = (body.get("provider") or "").strip()
    if not provider:
        return jsonify({"success": False, "error": "provider required"}), 400
    if not body.get("confirm"):
        return jsonify({"success": False, "error": "confirm:true required"}), 400
    from backend.services.llm_service import reset_circuit
    ok = reset_circuit(provider)
    if not ok:
        return jsonify({"success": False, "error": f"unknown provider: {provider}"}), 400
    try:
        from backend.services.admin_audit_service import log_action
        log_action("owner_models_circuit_reset", actor="owner", payload={"provider": provider})
    except Exception:
        pass
    return jsonify({"success": True, "provider": provider}), 200


@owner_panel_bp.route("/owner/api/users", methods=["GET"])
def owner_users():
    denied = _require_ops()
    if denied:
        return denied
    return jsonify({"success": True, "users": _users_snapshot()}), 200


@owner_panel_bp.route("/owner/api/tools", methods=["GET"])
def owner_tools():
    denied = _require_ops()
    if denied:
        return denied
    return jsonify({"success": True, "tools": _tools_snapshot()}), 200


@owner_panel_bp.route("/owner/api/tools/run/<action>", methods=["GET"])
def owner_tools_run(action: str):
    denied = _require_ops()
    if denied:
        return denied
    action = (action or "").strip()
    limit = min(int(request.args.get("limit", 20)), 100)
    if action == "audit_tail":
        return jsonify({"success": True, "action": action, "rows": _recent_audit(limit)}), 200
    if action == "404_tail":
        return jsonify(
            {
                "success": True,
                "action": action,
                "rows": _tail_jsonl("logs/register_intelligence/404_occurrences.jsonl", limit),
            }
        ), 200
    if action == "register_intelligence":
        try:
            data = _register_intelligence_summary()
            try:
                from backend.services.admin_audit_service import log_action
                log_action("owner_tools_register_intelligence", actor="owner")
            except Exception:
                pass
            return jsonify({"success": True, "action": action, "report": data}), 200
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500
    return jsonify({"success": False, "error": f"unknown action: {action}"}), 400
