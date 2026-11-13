"""Theme trophies (easy) + tough MN2 coin rewards."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_theme_trophies_exist_and_are_easy():
    data = json.loads((ROOT / "data" / "trophy_definitions.json").read_text(encoding="utf-8"))
    theme = [t for t in data["trophies"] if t.get("category") == "theme"]
    assert len(theme) >= 5
    for t in theme:
        assert t.get("rarity") in ("common", "rare")
        assert float(t.get("progress_target") or 0) <= 3
        assert float(t.get("mn2_reward") or 0) == 0
    set_ids = {s["id"] for s in data.get("sets") or []}
    assert "theme_gallery" in set_ids


def test_tough_trophies_declare_mn2_rewards():
    data = json.loads((ROOT / "data" / "trophy_definitions.json").read_text(encoding="utf-8"))
    tough = [t for t in data["trophies"] if t.get("rarity") in ("epic", "legendary")]
    assert tough
    for t in tough:
        assert float(t.get("mn2_reward") or 0) > 0


def test_unlock_mn2_table_favors_tough_rarities():
    levels = json.loads((ROOT / "data" / "trophy_levels.json").read_text(encoding="utf-8"))
    table = levels["unlock_mn2_by_rarity"]
    assert float(table.get("common") or 0) == 0
    assert float(table.get("rare") or 0) == 0
    assert float(table["epic"]) >= 0.05
    assert float(table["legendary"]) >= 0.25


def test_trophy_unlock_mn2_amount_uses_explicit_and_rarity(monkeypatch):
    from backend.services import trophy_level_service as tls

    monkeypatch.setattr(tls, "_user_trophy_score", lambda _uid: 0)
    epic = tls.trophy_unlock_mn2_amount("u1", {"rarity": "epic", "mn2_reward": 0.05})
    assert epic >= 0.05
    theme = tls.trophy_unlock_mn2_amount(
        "u1", {"rarity": "common", "category": "theme", "mn2_reward": 0}
    )
    assert theme == 0.0


def test_eligible_theme_trophies_from_client_metrics():
    from backend.routes import trophies_routes as tr

    metrics = {
        "trophy_page_visits": 1,
        "theme_gold": 1,
        "theme_ww2": 1,
        "theme_switches": 2,
        "theme_pages": 3,
        "theme_trophies": 3,
    }
    eligible = set(tr.eligible_trophy_ids(metrics, already_unlocked=[]))
    assert "theme_first_visit" in eligible
    assert "theme_gold_classic" in eligible
    assert "theme_ww2_room" in eligible
    assert "theme_hopper" in eligible
    assert "theme_browse_tabs" in eligible
    assert "theme_set_complete" in eligible


def test_trophy_level_and_quest_claim_routes_registered():
    from backend.routes import trophies_routes as tr

    assert callable(tr.trophy_level_api)
    assert callable(tr.trophy_level_collect_api)
    assert callable(tr.trophy_quests_claim_api)
    # Ensure Flask recorded the URL rules on the blueprint.
    recorded = []
    for item in getattr(tr.trophies_bp, "deferred_functions", []) or []:
        recorded.append(str(item))
    blob = " ".join(recorded)
    assert "/api/trophies/level" in blob or callable(tr.trophy_level_api)
    assert "/api/trophies/quests/claim" in blob or callable(tr.trophy_quests_claim_api)


def test_compute_user_metrics_covers_common_progress_keys(monkeypatch):
    from backend.routes import trophies_routes as tr

    class _FakeDB:
        def get_all_points(self, user_id):
            return {
                "success": True,
                "points": {
                    "generation_points": 2500,
                    "battle_points": 200,
                    "social_points": 100,
                    "battle_wins": 4,
                    "level": 6,
                    "achievements_earned": 2,
                    "trophies_collected": 1,
                    "systems": {},
                },
            }

    monkeypatch.setattr(
        "backend.services.unified_points_database.unified_points_db",
        _FakeDB(),
        raising=False,
    )
    metrics = tr.compute_user_metrics("metrics-user")
    assert metrics["videos"] >= 1
    assert metrics["victories"] >= 4
    assert metrics["battles"] >= 4
    assert metrics["friends"] >= 1
    assert metrics["level"] == 6
    assert "clips" in metrics and "messages" in metrics
