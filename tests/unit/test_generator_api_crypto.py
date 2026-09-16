"""Generator API crypto profile and rewards."""
from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture
def api_crypto_env(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="gen_api_crypto_")
    monkeypatch.setenv("MASTERNODER_LOG_DIR", tmp)
    yield tmp


def test_crypto_rewards_info():
    from backend.services.generator_api_crypto_service import get_crypto_rewards_info

    out = get_crypto_rewards_info("test_user")
    assert out["success"] is True
    assert out["per_job_mn2"] > 0
    assert isinstance(out["integrations"], list)


def test_api_crypto_profile_requires_user():
    from backend.services.generator_api_crypto_service import get_api_crypto_profile

    out = get_api_crypto_profile("")
    assert out["success"] is False


def test_credit_api_job_reward_daily_cap(api_crypto_env, monkeypatch):
    from backend.services import generator_api_crypto_service as svc

    daily_path = os.path.join(api_crypto_env, "generator_api_crypto_daily.json")
    monkeypatch.setattr(svc, "_DAILY_FILE", daily_path)
    monkeypatch.setattr(svc, "_rewards_cfg", lambda: {
        "per_job_mn2": 0.1,
        "daily_cap_mn2": 0.05,
        "integration_bonus_mn2": 0,
        "external_link_reward_mn2": 0,
    })

    class FakeDB:
        def add_points(self, **kwargs):
            return {"success": True}

    monkeypatch.setattr(
        "backend.services.unified_points_database.unified_points_db",
        FakeDB(),
    )

    out = svc.credit_api_job_reward("cap_user", job_id="j1")
    assert out["success"] is True
    assert out["mn2_granted"] == 0.05

    out2 = svc.credit_api_job_reward("cap_user", job_id="j2")
    assert out2["success"] is False
    assert out2["error"] == "daily_cap_reached"


def test_a_plus_board():
    from backend.services.system_a_plus_board_service import get_a_plus_board

    out = get_a_plus_board()
    assert out["success"] is True
    assert out["version"] == "A+"
    assert len(out["boards"]) >= 3
