"""Profit agent skills + critical top25 tests."""
import pytest


@pytest.fixture
def skills_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_path_service as ppp
    from backend.services import exchange_profit_agent_skills_service as pas

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    logs = tmp_path / "logs" / "profit_agent_skills"
    logs.mkdir(parents=True)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(ppp, "_CFG_PATH", str(data / "profit_path_protocol.json"))
    monkeypatch.setattr(ppp, "_LEDGER_PATH", str(data / "profit_path_ledger.jsonl"))
    monkeypatch.setattr(pas, "_REGISTRY_PATH", str(logs / "registry.json"))
    monkeypatch.setattr(pas, "_CRITICAL_PATH", str(data / "profit_critical_top25.json"))
    monkeypatch.setattr(pas, "_LEDGER_PATH", str(data / "profit_path_ledger.jsonl"))

    (data / "profit_path_protocol.json").write_text(
        '{"enabled":true,"default_ledger_mode":"live","skill_evolution_on_profit":true}',
        encoding="utf-8",
    )

    class FakeSkillset:
        def __init__(self):
            self.skills = {}

        def add_skill(self, agent_id, skill, agent_type="agents"):
            self.skills.setdefault(agent_id, []).append(skill)

        def level_up(self, agent_id, agent_type="agents", experience=100):
            pass

    fake = FakeSkillset()
    monkeypatch.setattr(
        "backend.services.exchange_profit_agent_skills_service.agent_skillset",
        fake,
        raising=False,
    )
    import backend.services.exchange_profit_agent_skills_service as pas_mod
    monkeypatch.setattr(pas_mod, "_apply_skill_to_agent_skillset", lambda aid, sk, **kw: fake.add_skill(aid, sk))

    return {"ppp": ppp, "pas": pas_mod, "fake": fake}


def test_ledger_mode_live_when_gate(monkeypatch, skills_env):
    monkeypatch.setenv("EXCHANGE_ARBITRAGE_LIVE", "1")
    ppp = skills_env["ppp"]
    assert ppp.ledger_mode() == "live"


def test_on_profit_event_adds_skill(skills_env):
    pas = skills_env["pas"]
    row = {
        "path_id": "abc12345",
        "agent_id": "arb_agent_btc_eth",
        "strategy": "spatial_arb",
        "symbol": "BTC",
        "mode": "live",
        "venues": {"buy": "binance", "sell": "nonkyc"},
        "execution": {"success": True, "realized_pnl_usd": 0.5},
        "notional_usd": 100,
    }
    res = pas.on_ledger_profit_event(row)
    assert res["success"] is True
    assert res["added_skills"]
    dup = pas.on_ledger_profit_event(row)
    assert dup.get("duplicate") is True


def test_critical_top25_checkboxes(skills_env):
    pas = skills_env["pas"]
    data = pas.critical_problems_top25(refresh=True)
    assert data["success"] is True
    assert len(data["problems"]) <= 25
    first_id = data["problems"][0]["id"]
    pas.update_critical_checkbox(first_id, True)
    updated = pas.critical_problems_top25(refresh=True)
    match = next(p for p in updated["problems"] if p["id"] == first_id)
    assert match["checked"] is True


def test_hit_rate_by_route(skills_env, monkeypatch):
    pas = skills_env["pas"]

    def fake_summary(*, hours=None):
        return {
            "hit_rate_pct": 33.3,
            "attempt_count": 9,
            "fill_count": 3,
            "best_routes_24h": [
                {"route": "DOGE:binance→nonkyc", "attempts": 6, "fills": 2, "hit_rate_pct": 33.3},
            ],
        }

    monkeypatch.setattr(
        "backend.services.exchange_profit_path_service.profit_path_summary",
        fake_summary,
    )
    data = pas.hit_rate_by_route(days=7)
    assert data["success"] is True
    assert data["routes"]
    assert data["hit_rate_pct"] == 33.3


def test_void_closes_on_baseline_success(skills_env):
    pas = skills_env["pas"]
    reg = pas._load_registry()
    pas._agent_bucket(reg, "arb_agent_btc_eth")["voids"] = ["void_venue_inventory_btc"]
    reg["voids"] = {"arb_agent_btc_eth:void_venue_inventory_btc": {"closed": False}}
    pas._save_registry(reg)

    row = {
        "baseline_id": "b1",
        "source": "rotation",
        "route": {"agent_id": "arb_agent_btc_eth", "symbol": "BTC", "mode": "live"},
        "executed": {"success": True, "fill_usd": 75.0},
    }
    res = pas.on_baseline_trade_event(row)
    assert res["success"] is True
    reg2 = pas._load_registry()
    assert reg2["voids"]["arb_agent_btc_eth:void_venue_inventory_btc"]["closed"] is True


def test_profit_status_collect_light():
    from scripts.profit_status_report import collect_light

    data = collect_light()
    assert data.get("light") is True
    assert "daemon_running" in data
    assert "critical_top25" in data
