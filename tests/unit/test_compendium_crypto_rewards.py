"""Compendium crypto (MN2) rewards for page reads and theory study."""
import os
import shutil

import pytest


@pytest.fixture
def compendium_crypto_user(monkeypatch):
    base = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".pytest-tmp",
        "compendium-crypto",
    )
    if os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base, exist_ok=True)

    daily_file = os.path.join(base, "compendium_crypto_daily.json")
    monkeypatch.setattr(
        "backend.services.compendium_crypto_rewards_service._DAILY_FILE",
        daily_file,
    )
    monkeypatch.setattr(
        "backend.services.game_mn2_rewards.credit_mn2",
        lambda *a, **k: {"success": True, "amount": a[1]},
    )
    return "reader_crypto"


def test_page_read_reward_includes_daily_first_bonus(compendium_crypto_user):
    from backend.services.compendium_crypto_rewards_service import award_page_read_reward

    r = award_page_read_reward(compendium_crypto_user, 1)
    assert r.get("success") is True
    # 0.0005 base + 0.005 daily first study
    assert r.get("awarded_mn2") == pytest.approx(0.0055, rel=1e-4)


def test_theory_study_reward(compendium_crypto_user):
    from backend.services.compendium_crypto_rewards_service import award_theory_study_reward

    r = award_theory_study_reward(compendium_crypto_user, "agenda_setting")
    assert r.get("success") is True
    assert r.get("awarded_mn2") == pytest.approx(0.001, rel=1e-3)


def test_crypto_rewards_info(compendium_crypto_user):
    from backend.services.compendium_crypto_rewards_service import get_crypto_rewards_info

    info = get_crypto_rewards_info(compendium_crypto_user)
    assert info.get("success") is True
    assert info["rates"]["page_read_mn2"] == 0.0005
    assert info["rates"]["theory_study_mn2"] == 0.001


def test_compendium_view_includes_crypto_reward(compendium_crypto_user, monkeypatch):
    from backend.routes.compendium_routes import compendium_bp
    from flask import Flask

    monkeypatch.setattr(
        "backend.services.compendium_access_service.can_access_page",
        lambda uid, page: True,
    )
    monkeypatch.setattr(
        "backend.services.unified_points_database.unified_points_db.add_points",
        lambda *a, **k: {"success": True},
    )
    monkeypatch.setattr(
        "backend.services.compendium_crypto_rewards_service.award_page_read_reward",
        lambda uid, page: {"success": True, "awarded_mn2": 0.0055},
    )

    app = Flask(__name__)
    app.register_blueprint(compendium_bp)
    client = app.test_client()
    r = client.post(
        "/api/compendium/view",
        json={"user_id": compendium_crypto_user, "page_number": 1},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("crypto_reward", {}).get("awarded_mn2") == 0.0055
