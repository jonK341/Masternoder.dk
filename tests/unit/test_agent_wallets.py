"""Agent wallet service tests."""
import pytest


def test_credit_and_balance(tmp_path, monkeypatch):
    from backend.services import agent_wallet_service as aw

    monkeypatch.setattr(aw, "_WALLETS_FILE", str(tmp_path / "wallets.json"))
    r = aw.credit("trader_agent_1", 50.0, reference="test-ref", source="test")
    assert r.get("success") is True
    assert aw.get_balance("trader_agent_1") == pytest.approx(50.0)


def test_list_wallets(tmp_path, monkeypatch):
    from backend.services import agent_wallet_service as aw

    monkeypatch.setattr(aw, "_WALLETS_FILE", str(tmp_path / "wallets.json"))
    aw.credit("trader_agent_2", 1.0, reference="r1", source="test")
    rows = aw.list_wallets()
    assert any(w["agent_id"] == "trader_agent_2" for w in rows)
