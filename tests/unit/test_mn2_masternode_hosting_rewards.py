"""Renter masternode payout credits (lastpaid → in-app MN2)."""
from __future__ import annotations

import json


def _hosts_doc(hosts):
    return {"hosts": hosts}


def test_accrue_credits_when_lastpaid_advances(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True)

    cfg = {
        "enabled": True,
        "renter_rewards": {
            "enabled": True,
            "use_block_subsidy": False,
            "fallback_reward_mn2": 8.0,
            "platform_fee_percent": 0,
        },
    }
    (data / "mn2_masternode_config.json").write_text(json.dumps(cfg), encoding="utf-8")
    (data / "mn2_masternode_hosts.json").write_text(
        json.dumps(
            _hosts_doc(
                [
                    {
                        "id": "platform-mn-1",
                        "status": "active",
                        "owner_user_id": "user_renter",
                        "collateral_txid": "abc123",
                        "collateral_vout": 0,
                    }
                ]
            )
        ),
        encoding="utf-8",
    )
    (data / "mn2_masternode_renter_rewards_state.json").write_text(
        json.dumps({"hosts": {"platform-mn-1": {"lastpaid": 100, "total_credited_mn2": 0}}}),
        encoding="utf-8",
    )

    import backend.services.mn2_masternode_service as mn
    import backend.services.mn2_masternode_hosting_rewards_service as rewards

    monkeypatch.setattr(mn, "_base", lambda: str(tmp_path))
    monkeypatch.setattr(rewards, "_base", lambda: str(tmp_path))

    chain_list = [{"txhash": "abc123", "outidx": 0, "lastpaid": 200, "status": "ENABLED"}]
    monkeypatch.setattr(mn, "network_masternodes", lambda **k: {"list": chain_list})

    credited = []

    def _credit(uid, amount, **kwargs):
        credited.append({"uid": uid, "amount": amount, "ref": kwargs.get("reference")})
        return {"success": True}

    monkeypatch.setattr("backend.services.game_mn2_rewards.credit_mn2", _credit)

    out = rewards.accrue_renter_rewards(limit=10)
    assert out["success"] is True
    assert out["payouts_credited"] == 1
    assert out["total_mn2_credited"] == 8.0
    assert credited and credited[0]["uid"] == "user_renter"
    assert credited[0]["ref"] == "masternode-payout:platform-mn-1:200"


def test_seed_baseline_skips_historic_payout(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True)

    cfg = {"enabled": True, "renter_rewards": {"enabled": True, "fallback_reward_mn2": 8.0}}
    (data / "mn2_masternode_config.json").write_text(json.dumps(cfg), encoding="utf-8")
    (data / "mn2_masternode_hosts.json").write_text(
        json.dumps(
            _hosts_doc(
                [
                    {
                        "id": "platform-mn-2",
                        "status": "active",
                        "owner_user_id": "user_lease",
                        "collateral_txid": "tx99",
                        "collateral_vout": 1,
                    }
                ]
            )
        ),
        encoding="utf-8",
    )

    import backend.services.mn2_masternode_service as mn
    import backend.services.mn2_masternode_hosting_rewards_service as rewards

    monkeypatch.setattr(mn, "_base", lambda: str(tmp_path))
    monkeypatch.setattr(rewards, "_base", lambda: str(tmp_path))
    monkeypatch.setattr(
        mn,
        "network_masternodes",
        lambda **k: {"list": [{"txhash": "tx99", "outidx": 1, "lastpaid": 50000}]},
    )

    seed = rewards.seed_renter_reward_baseline("platform-mn-2")
    assert seed["success"] is True
    assert seed["lastpaid"] == 50000

    monkeypatch.setattr(
        "backend.services.game_mn2_rewards.credit_mn2",
        lambda *a, **k: {"success": True},
    )
    out = rewards.accrue_renter_rewards(limit=10)
    assert out["payouts_credited"] == 0


def test_renter_rewards_summary(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True)

    (data / "mn2_masternode_config.json").write_text(json.dumps({"enabled": True}), encoding="utf-8")
    (data / "mn2_masternode_hosts.json").write_text(
        json.dumps(
            _hosts_doc(
                [{"id": "platform-mn-3", "status": "active", "owner_user_id": "u1", "rewards_total_mn2": 16}]
            )
        ),
        encoding="utf-8",
    )
    (data / "mn2_masternode_renter_rewards_state.json").write_text(
        json.dumps({"hosts": {"platform-mn-3": {"lastpaid": 42, "total_credited_mn2": 16}}}),
        encoding="utf-8",
    )

    import backend.services.mn2_masternode_service as mn
    import backend.services.mn2_masternode_hosting_rewards_service as rewards

    monkeypatch.setattr(mn, "_base", lambda: str(tmp_path))
    monkeypatch.setattr(rewards, "_base", lambda: str(tmp_path))

    summary = rewards.renter_rewards_summary("u1")
    assert summary["success"] is True
    assert summary["rewards_total_mn2"] == 16.0
    assert len(summary["hosts"]) == 1
