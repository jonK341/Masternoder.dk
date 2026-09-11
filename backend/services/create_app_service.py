"""Create App — Play Store + Podcast scaffold with Super Encoder (nr. 1) and AI API."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_APPS_FILE = os.path.join(_BASE, "data", "create_apps.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_apps() -> Dict[str, Any]:
    try:
        with open(_APPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"apps": [], "version": 1}


def _save_apps(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_APPS_FILE), exist_ok=True)
    with open(_APPS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _mn2_config() -> Dict[str, Any]:
    try:
        with open(os.path.join(_BASE, "data", "mn2_config.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _agents_for_template(template_id: str) -> List[str]:
    for tpl in catalog().get("templates") or []:
        if tpl.get("id") == template_id:
            return list(tpl.get("agents") or ["lab_create_agent"])
    return ["lab_create_agent"]


def catalog() -> Dict[str, Any]:
    """Templates for Create App wizard."""
    return {
        "success": True,
        "templates": [
            {
                "id": "playstore_podcast",
                "title": "Play Store + Podcast",
                "description": "TWA shells for Google Play plus podcast distribution with Super Encoder nr. 1.",
                "targets": ["playstore", "podcast"],
                "agents": ["google_play_agent", "podcast_producer_agent", "lab_create_agent"],
                "mobile_paths": {
                    "podcast_twa": "mobile/podcast-twa/twa-manifest.json",
                    "casino_twa": "mobile/casino-twa/twa-manifest.json",
                },
            },
            {
                "id": "podcast_only",
                "title": "Podcast App",
                "description": "Podcast TWA + AI audio encoder profiles.",
                "targets": ["podcast"],
                "agents": ["podcast_producer_agent", "content_generator_agent"],
            },
            {
                "id": "playstore_only",
                "title": "Play Store TWA",
                "description": "Trusted Web Activity wrapper for Play Console.",
                "targets": ["playstore"],
                "agents": ["google_play_agent", "lab_create_agent"],
            },
        ],
        "super_encoder": {
            "id": "new_encoder_nr_1",
            "label": "New encoder nr. 1",
            "features": ["E1_hardware_h264", "AI_profile_tuning", "podcast_audio_profiles"],
        },
    }


def list_user_apps(user_id: str) -> Dict[str, Any]:
    data = _load_apps()
    apps = [a for a in (data.get("apps") or []) if a.get("user_id") == user_id]
    return {"success": True, "user_id": user_id, "apps": apps}


def create_app(
    user_id: str,
    *,
    title: str,
    template_id: str = "playstore_podcast",
    quality_goal: str = "balanced",
    duration_sec: int = 120,
    content_hint: str = "",
    include_playstore: bool = True,
    include_podcast: bool = True,
) -> Dict[str, Any]:
    """Create a new app project with Super Encoder AI plan."""
    from backend.services.super_encoder_service import build_super_encode_package
    from backend.services.create_app_finish_checks import run_finish_checks

    title = (title or "").strip()
    if len(title) < 2:
        return {"success": False, "error": "title_required"}

    encode_pkg = build_super_encode_package({
        "target": "hybrid" if include_playstore and include_podcast else ("podcast" if include_podcast else "video"),
        "quality_goal": quality_goal,
        "duration_sec": duration_sec,
        "content_hint": content_hint,
        "user_id": user_id,
        "include_playstore": include_playstore,
        "include_podcast": include_podcast,
    })

    finish = run_finish_checks(user_id)
    app_id = "capp_" + uuid.uuid4().hex[:12]
    entry = {
        "id": app_id,
        "user_id": user_id,
        "title": title,
        "template_id": template_id,
        "status": "active",
        "progress": min(100, int(finish.get("finish_percent") or 0)),
        "product_finished": bool(finish.get("product_finished")),
        "targets": {
            "playstore": include_playstore,
            "podcast": include_podcast,
        },
        "super_encoder": encode_pkg,
        "finish_summary": {
            "total_checks": finish.get("total_checks"),
            "passed": finish.get("passed"),
            "failed": finish.get("failed"),
            "finish_percent": finish.get("finish_percent"),
        },
        "assigned_agents": _agents_for_template(template_id),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    data = _load_apps()
    apps: List[Dict[str, Any]] = list(data.get("apps") or [])
    apps.append(entry)
    data["apps"] = apps[-100:]
    _save_apps(data)

    # Join reward for first create-app per user
    join_reward = _award_create_join(user_id, app_id)

    try:
        from backend.services.activity_events_service import emit
        emit(
            "create_app_started",
            user_id=user_id,
            channel="lab",
            text=f"Create App: {title}",
            payload={"app_id": app_id, "template_id": template_id},
        )
    except Exception:
        pass

    return {
        "success": True,
        "app": entry,
        "finish_checks": finish,
        "join_reward": join_reward,
    }


def _award_create_join(user_id: str, app_id: str) -> Dict[str, Any]:
    cfg = (_mn2_config().get("create_app") or {})
    amount = float(cfg.get("join_reward_mn2") or 0.01)
    from backend.services.game_mn2_rewards import credit_mn2
    return credit_mn2(
        user_id,
        amount,
        source="create_app_join",
        reference=f"create-app-join:{user_id}",
        metadata={"app_id": app_id, "first_app_id": app_id},
    )


def finish_product(user_id: str, app_id: str) -> Dict[str, Any]:
    """Mark product finished when all 100 checks pass; award MN2 finish bonus."""
    from backend.services.create_app_finish_checks import run_finish_checks
    from backend.services.game_mn2_rewards import credit_mn2

    data = _load_apps()
    apps = data.get("apps") or []
    app = next((a for a in apps if a.get("id") == app_id and a.get("user_id") == user_id), None)
    if not app:
        return {"success": False, "error": "app_not_found"}

    finish = run_finish_checks(user_id)
    app["finish_summary"] = {
        "total_checks": finish.get("total_checks"),
        "passed": finish.get("passed"),
        "failed": finish.get("failed"),
        "finish_percent": finish.get("finish_percent"),
    }
    app["progress"] = int(finish.get("finish_percent") or 0)
    app["updated_at"] = _now_iso()

    if not finish.get("product_finished"):
        app["product_finished"] = False
        for i, a in enumerate(apps):
            if a.get("id") == app_id:
                apps[i] = app
                break
        data["apps"] = apps
        _save_apps(data)
        return {
            "success": False,
            "error": "finish_checks_incomplete",
            "app": app,
            "finish_checks": finish,
            "finish_reward": {"success": False, "skipped": True},
        }

    app["status"] = "finished"
    app["product_finished"] = True
    app["finished_at"] = _now_iso()
    cfg = (_mn2_config().get("create_app") or {})
    amount = float(cfg.get("finish_reward_mn2") or 0.025)
    reward_result = credit_mn2(
        user_id,
        amount,
        source="create_app_finish",
        reference=f"create-app-finish:{app_id}",
        metadata={"app_id": app_id, "checks_passed": finish.get("passed")},
    )
    try:
        from backend.services.agent_achievements import agent_achievements
        for aid in app.get("assigned_agents") or ["lab_create_agent"]:
            agent_achievements.check_achievements(aid, "task_completed", {"xp": 50, "activity_points": 25})
    except Exception:
        pass

    for i, a in enumerate(apps):
        if a.get("id") == app_id:
            apps[i] = app
            break
    data["apps"] = apps
    _save_apps(data)

    return {
        "success": True,
        "app": app,
        "finish_checks": finish,
        "finish_reward": reward_result,
    }


def super_encode_for_app(user_id: str, app_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Re-run Super Encoder AI plan for an existing app."""
    from backend.services.super_encoder_service import build_super_encode_package

    data = _load_apps()
    app = next((a for a in (data.get("apps") or []) if a.get("id") == app_id and a.get("user_id") == user_id), None)
    if not app:
        return {"success": False, "error": "app_not_found"}

    cfg = dict(body or {})
    cfg["user_id"] = user_id
    pkg = build_super_encode_package(cfg)
    app["super_encoder"] = pkg
    app["updated_at"] = _now_iso()
    for i, a in enumerate(data.get("apps") or []):
        if a.get("id") == app_id:
            data["apps"][i] = app
            break
    _save_apps(data)
    return {"success": True, "app_id": app_id, "super_encoder": pkg}
