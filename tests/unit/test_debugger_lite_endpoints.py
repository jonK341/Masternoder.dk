"""LITE app coverage for the debugger page and the static JS it loads.

Every call uses the method the UI uses. A 5xx or the auto-fix stub
({auto_fixed: true} / "Endpoint auto-created") fails the test.
"""
import os
import time

import pytest

from src.app import create_app  # noqa: E402

_SLOW_BUDGET_S = 3.0


@pytest.fixture(scope="module")
def client():
    import src.app as appmod

    previous = os.environ.get("LITE_APP")
    os.environ["LITE_APP"] = "1"
    os.environ.pop("DAEMON_QUIET", None)
    appmod._daemon_cached_app = None
    try:
        app = create_app()
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        if previous is None:
            os.environ.pop("LITE_APP", None)
        else:
            os.environ["LITE_APP"] = previous
        appmod._daemon_cached_app = None


GETS = [
    "/api/health",
    "/api/health/system",
    "/api/health/data-schema",
    "/api/monitor/status",
    "/api/system/overview",
    "/api/system/overview?compact=1",
    "/api/ai/providers",
    "/api/ai/providers/test",
    "/api/agent/master-fix/personality",
    "/api/agent/master-fix/missions",
    "/api/agent/master-fix/quests",
    "/api/agent/master-fix/history",
    "/api/agent/master-fix/statistics",
    "/api/agent/master-fix/behavior-pattern",
    "/api/agents/manager/status",
    "/api/debug/all-systems",
    "/api/debug/all-routes",
    "/api/debug/check-duplicates",
    "/api/debug/report",
    "/api/debugger/scanner/scan",
    "/api/debugger/scanner/blueprints",
    "/api/debugger/scanner/routes",
    "/api/debugger/scanner/missing",
    "/api/debugger/scanner/suggestions",
    "/api/debugger/profile/points?user_id=default_user",
    "/api/debugger/profile/stats?user_id=default_user",
    "/api/debugger/profile/agent-points?agent_id=agent_manager",
    "/api/debugger/tasks/list",
    "/api/debugger/tasks/stats",
    "/api/errors/tasks/list",
    "/api/errors/tasks/stats",
    "/api/errors/stats?days=7",
    "/api/errors/list?limit=10",
    "/api/errors/handler-status",
    "/api/errors/handler-status/analyze",
    "/api/debugger/agent/analytics",
    "/api/debugger/agent/handling",
    "/api/system-skills/definition",
    "/api/system-skills/super-upgrade/blocks",
    "/api/system-skills/self-heal/status",
    "/api/agents/skillsets/all",
    "/api/agents/activity/all?limit=20",
    "/api/agent-tech/agent_electric_magnet/status",
    "/api/agent-tech/agent_event_tracker/status",
    "/api/game/hunters/profiling?user_id=default_user",
    "/api/quests/daily",
    "/api/leaderboard/ai-insights",
    "/api/shop/daily-deal",
    "/api/podcast/portal-lines?site=debugger",
    "/api/admin/risk/summary",
    "/api/admin/risk/withdrawals?limit=5",
    "/api/admin/risk/sybil?limit=5",
    "/api/notifications?user_id=default_user",
    "/api/notifications/count?user_id=default_user",
    "/api/stats/activity?user_id=default_user",
    "/api/game/battle/history?user_id=default_user&limit=5",
    "/api/points/all?user_id=default_user",
    "/api/user/profile/default_user",
    "/api/master-dashboard/top10",
    "/api/master-dashboard/stats",
    "/api/generator/jobs?user_id=default_user&limit=5",
    "/api/documentary/video/missing-doc",
    "/api/ai/intelligence/summary",
    "/api/ai/insights",
    "/api/debugging/stats",
]

POSTS = [
    ("/api/ai/chat", {"prompt": "ping"}),
    ("/api/ai/providers/reset", {"provider": "groq"}),
    ("/api/debugger/agent/fix-personality", {}),
    ("/api/debugger/agent/fix-missions", {}),
    ("/api/debugger/agent/fix-quests", {}),
    ("/api/debugger/agent/fix-history", {}),
    ("/api/debugger/agent/fix-behavior", {"behavior": "balanced"}),
    ("/api/debugger/agent/fix-all", {}),
    ("/api/agent/master-fix/diagnostic", {}),
    ("/api/agent/master-fix/run-full-diagnostic", {}),
    ("/api/user/logout", {}),
    ("/api/user/identify", {}),
    ("/api/video-generation/calculate", {"clips": [{"note": "segment"}]}),
    ("/api/video-generation/solve-problems", {"problems": ["pipeline check"]}),
    ("/api/game/battle/start", {"user_id": "default_user", "battle_type": "quick"}),
    ("/api/points/add", {"user_id": "lite_probe", "point_type": "activity_points", "amount": 1, "source": "test"}),
    ("/api/agent-tech/agent_electric_magnet/download", {"user_id": "default_user"}),
    ("/api/agent-tech/agent_electric_magnet/run_verification", {"user_id": "default_user"}),
    ("/api/agent-tech/agent_event_tracker/track_new_task", {"user_id": "default_user", "task_name": "debugger_probe"}),
    ("/api/debugging/session/start", {"metadata": {"url": "/debugger"}}),
]

SLOW_PATHS = {
    "/api/monitor/status",
    "/api/system/overview",
    "/api/system/overview?compact=1",
    "/api/agent/master-fix/diagnostic",
    "/api/agent/master-fix/run-full-diagnostic",
}


def _assert_real(response, elapsed, path):
    body = response.get_json(silent=True)
    bare = path.split("?", 1)[0]
    # /api/health/system uses 503 when a component is degraded. That JSON is the
    # health report (overall + components), not a crashed handler.
    health_report = (
        bare == "/api/health/system"
        and response.status_code == 503
        and isinstance(body, dict)
        and body.get("components")
        and body.get("auto_fixed") is not True
    )
    if not health_report:
        assert response.status_code < 500, f"{path} -> {response.status_code} {response.get_data(as_text=True)[:300]}"
    if isinstance(body, dict):
        assert body.get("auto_fixed") is not True, path
        assert body.get("message") != "Endpoint auto-created", path
    if bare in {p.split("?", 1)[0] for p in SLOW_PATHS} or path in SLOW_PATHS:
        assert elapsed < _SLOW_BUDGET_S, f"{path} took {elapsed:.2f}s"


@pytest.mark.parametrize("path", GETS)
def test_debugger_get(client, path):
    started = time.perf_counter()
    response = client.get(path)
    _assert_real(response, time.perf_counter() - started, path)


@pytest.mark.parametrize("path,payload", POSTS)
def test_debugger_post(client, path, payload):
    started = time.perf_counter()
    response = client.post(path, json=payload)
    _assert_real(response, time.perf_counter() - started, path)


def test_post_only_routes_are_405_not_500(client):
    for path in ("/api/ai/chat", "/api/ai/providers/reset", "/api/user/logout", "/api/debugger/agent/fix-all"):
        response = client.get(path)
        assert response.status_code == 405, path
        body = response.get_json(silent=True) or {}
        assert body.get("auto_fixed") is not True


def test_quiz_anonymous_is_forbidden_not_stub(client):
    response = client.post("/api/debugger/quiz/submit", json={"user_id": "default_user", "correct": 40, "total": 50})
    assert response.status_code == 403
    assert response.get_json().get("success") is False


def test_risk_panel_disabled_without_admin_key(client, monkeypatch):
    monkeypatch.delenv("COGS_ADMIN_REPORT_KEY", raising=False)
    response = client.get("/api/admin/risk/summary")
    assert response.status_code == 401
    body = response.get_json()
    assert body["success"] is False
    assert body["error"] == "admin_risk_disabled"
    assert body.get("auto_fixed") is not True


def test_monitor_status_is_registry_not_self_probe(client):
    response = client.get("/api/monitor/status")
    body = response.get_json()
    assert body["check"] == "mounted_routes"
    assert body["live_probe"] is False
    assert body["total"] == body["ok"]
    assert body["fail"] == 0
    assert body["total"] > 10
