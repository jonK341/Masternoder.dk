"""Jon Film appointments + actor leveling."""
from __future__ import annotations


def test_daily_appointments_and_levels(tmp_path, monkeypatch):
    from backend.services import jon_film_service as jf

    monkeypatch.setattr(jf, "_ACTORS_PATH", str(tmp_path / "actors.json"))
    monkeypatch.setattr(jf, "_APPTS_PATH", str(tmp_path / "appts.json"))
    monkeypatch.setattr(jf, "_LEVELS_PATH", str(tmp_path / "levels.json"))

    a = jf.generate_daily_appointments(force=True, count=10)
    assert a["success"] is True
    assert a["count"] == 10
    assert a["reused"] is False
    titles = [x["title"] for x in a["appointments"]]
    assert len(set(titles)) == 10
    assert all(x["movie"] == "Jon Film" for x in a["appointments"])
    assert all(x.get("agent_id") for x in a["appointments"])
    assert all(x.get("performer_id") for x in a["appointments"])

    levels = jf.get_actor_levels()
    assert levels["success"] is True
    assert levels["assignments_per_level"] == 20
    total = sum(int(x["assignments"]) for x in levels["actors"])
    assert total == 10

    # Force another fresh batch — levels keep climbing.
    b = jf.generate_daily_appointments(force=True, count=10)
    assert b["batch_id"] != a["batch_id"]
    levels2 = jf.get_actor_levels()
    total2 = sum(int(x["assignments"]) for x in levels2["actors"])
    assert total2 == 20

    # 20 assignments on one actor → level 2
    jf.credit_assignment("actor_jon", amount=20, reason="test")
    row = next(x for x in jf.get_actor_levels()["actors"] if x["id"] == "actor_jon")
    assert row["level"] >= 2
