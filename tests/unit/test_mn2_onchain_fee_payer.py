"""Site-paid network fee and idempotent address backfill."""
from __future__ import annotations

import json

import pytest


def test_build_site_paid_outputs_user_does_not_pay_fee():
    from backend.services.mn2_onchain_wallet import build_site_paid_outputs

    user_utxos = [{"txid": "u1", "vout": 0, "amount": 2.0, "address": "UserAddr"}]
    payer_utxos = [{"txid": "p1", "vout": 1, "amount": 0.5, "address": "SiteFee"}]
    built = build_site_paid_outputs(
        user_utxos,
        payer_utxos,
        user_change_address="UserAddr",
        payer_address="SiteFee",
        to_address="FriendAddr",
        amount=1.25,
        network_fee=0.001,
    )
    assert built["success"] is True
    assert built["outputs"]["FriendAddr"] == pytest.approx(1.25)
    assert built["outputs"]["UserAddr"] == pytest.approx(0.75)
    assert built["outputs"]["SiteFee"] == pytest.approx(0.499)
    assert {row["txid"] for row in built["inputs"]} == {"u1", "p1"}
    assert built["network_fee_mn2"] == pytest.approx(0.001)


def test_fee_payer_insufficient_does_not_touch_user_coins():
    from backend.services.mn2_onchain_wallet import build_site_paid_outputs

    built = build_site_paid_outputs(
        [{"txid": "u1", "vout": 0, "amount": 3, "address": "UserAddr"}],
        [{"txid": "p1", "vout": 0, "amount": 0.0001, "address": "SiteFee"}],
        user_change_address="UserAddr",
        payer_address="SiteFee",
        to_address="FriendAddr",
        amount=1,
        network_fee=0.001,
    )
    assert built["success"] is False
    assert built["code"] == "fee_payer_insufficient"


def test_send_refuses_when_raw_rpc_missing(monkeypatch):
    from backend.services import mn2_onchain_wallet as onchain

    monkeypatch.setattr(
        onchain,
        "describe_send_support",
        lambda: {
            "raw_coin_control": False,
            "per_address_send": False,
            "note": "no raw tx",
            "methods": {},
        },
    )
    result = onchain.send_from_user_site_pays_fee("alice", "MxFriend", 1.0, kind="user_transfer")
    assert result["success"] is False
    assert result["code"] == "per_address_send_unsupported"


def test_send_records_site_expense_and_low_balance_alert(monkeypatch, tmp_path):
    from backend.services import mn2_onchain_wallet as onchain

    monkeypatch.setattr(
        onchain,
        "describe_send_support",
        lambda: {
            "raw_coin_control": True,
            "methods": {"signrawtransactionwithwallet": True},
            "note": "raw",
        },
    )
    monkeypatch.setattr(
        onchain,
        "fee_payer_config",
        lambda config=None: {
            "address": "SiteFee",
            "account": "",
            "user_id": "@site_fee_payer",
            "network_fee_mn2": 0.001,
            "low_balance_mn2": 1.0,
            "pay_external_withdrawal_fee": False,
        },
    )
    monkeypatch.setattr(onchain, "_user_addresses", lambda uid: ["UserAddr"])
    monkeypatch.setattr(
        onchain,
        "_list_unspent",
        lambda minconf=1: [
            {"txid": "u1", "vout": 0, "amount": 2.0, "address": "UserAddr", "spendable": True},
            {"txid": "p1", "vout": 0, "amount": 0.2, "address": "SiteFee", "spendable": True},
        ],
    )
    captured = {}

    class _Rpc:
        def createrawtransaction(self, inputs, outputs):
            captured["inputs"] = inputs
            captured["outputs"] = outputs
            return {"result": "deadbeef", "error": None}

    monkeypatch.setattr(onchain, "_sign_and_send", lambda raw, support: {"success": True, "txid": "txid-site-fee"})
    monkeypatch.setattr("backend.services.mn2_rpc_client.createrawtransaction", _Rpc().createrawtransaction)
    ledger = []
    monkeypatch.setattr(
        "backend.services.mn2_ledger.append_entry",
        lambda user_id, entry_type, amount, txid=None, address=None, metadata=None: ledger.append(
            {"user_id": user_id, "type": entry_type, "amount": amount, "txid": txid}
        ),
    )
    alert_path = tmp_path / "alerts.jsonl"
    monkeypatch.setattr(onchain, "_alert_path", lambda: str(alert_path))

    result = onchain.send_from_user_site_pays_fee("alice", "FriendAddr", 1.0, kind="user_transfer")
    assert result["success"] is True
    assert result["txid"] == "txid-site-fee"
    assert captured["outputs"]["FriendAddr"] == pytest.approx(1.0)
    assert captured["outputs"]["SiteFee"] == pytest.approx(0.199)
    assert any(row["type"] == "site_network_fee" and row["user_id"] == "@site_fee_payer" for row in ledger)
    assert result["low_balance_alert"] is not None
    assert "remaining_mn2" in alert_path.read_text(encoding="utf-8")


def test_external_withdrawal_fee_stays_on_user_by_default():
    from backend.services.mn2_onchain_wallet import site_pays_external_withdrawal_fee

    assert site_pays_external_withdrawal_fee({"withdrawal_fee": 0.001}) is False
    assert site_pays_external_withdrawal_fee(
        {"onchain_fee_payer": {"pay_external_withdrawal_fee": True}}
    ) is True


def test_backfill_dry_run_is_idempotent_and_resumable(monkeypatch, tmp_path):
    from backend.services import mn2_onchain_wallet as onchain

    state = tmp_path / "state.json"
    missing = ["a_user", "b_user", "c_user"]
    monkeypatch.setattr(onchain, "users_missing_addresses", lambda user_ids=None: list(missing if user_ids is None else [u for u in user_ids if u in missing]))

    first = onchain.plan_address_backfill(batch_size=2, state_path=str(state))
    assert first["dry_run"] is True
    assert first["batch"] == ["a_user", "b_user"]
    assert not state.exists()

    created = []

    def _ensure(uid):
        created.append(uid)
        missing.remove(uid)
        return {"success": True, "deposit_address": "Mx" + uid}

    monkeypatch.setattr(onchain, "ensure_user_address", _ensure)
    applied = onchain.apply_address_backfill(batch_size=2, state_path=str(state))
    assert applied["dry_run"] is False
    assert [row["user_id"] for row in applied["created"]] == ["a_user", "b_user"]
    assert json.loads(state.read_text(encoding="utf-8"))["cursor"] == "b_user"

    again = onchain.plan_address_backfill(batch_size=2, state_path=str(state))
    assert again["batch"] == ["c_user"]
    second = onchain.apply_address_backfill(batch_size=2, state_path=str(state))
    assert [row["user_id"] for row in second["created"]] == ["c_user"]
    third = onchain.apply_address_backfill(batch_size=2, state_path=str(state))
    assert third["created"] == []
    assert created == ["a_user", "b_user", "c_user"]


def test_wallet_mode_defaults_to_ledger(monkeypatch):
    from backend.services.mn2_onchain_wallet import wallet_mode

    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.load_mn2_config",
        lambda: {},
    )
    assert wallet_mode() == "ledger"


def test_mn2_unknown_route_is_not_auto_created():
    from flask import Flask

    from backend.middleware.auto_fix_404_middleware import handle_404
    from backend.services.auto_fix_endpoints import auto_fix_endpoints

    assert auto_fix_endpoints.should_auto_fix("/api/mn2/transfer", "POST") is False
    app = Flask(__name__)
    app.register_error_handler(404, handle_404)
    response = app.test_client().get("/api/mn2/not-a-real-route")
    assert response.status_code == 404
    body = response.get_json()
    assert body["success"] is False
    assert body.get("auto_fixed") is not True


def test_generate_daemon_address_unlocks_then_returns_address(monkeypatch):
    from backend.services import mn2_wallet_service as wallet

    calls = {"new": 0, "unlock": 0}

    def _new():
        calls["new"] += 1
        if calls["new"] == 1:
            return {"result": None, "error": "Error: Please enter the wallet passphrase with walletpassphrase first."}
        return {"result": "MxFreshAddress", "error": None}

    def _unlock(passphrase, timeout_sec, staking_only):
        calls["unlock"] += 1
        assert passphrase == "secret"
        assert staking_only is False
        return {"result": True, "error": None}

    monkeypatch.setenv("MN2_WALLET_PASSPHRASE", "secret")
    monkeypatch.setattr("backend.services.mn2_rpc_client.getnewaddress", _new)
    monkeypatch.setattr("backend.services.mn2_rpc_client.walletpassphrase", _unlock)
    monkeypatch.setattr("backend.services.mn2_rpc_client.validateaddress", lambda addr: {"result": {"isvalid": True, "ismine": True}, "error": None})

    result = wallet.generate_daemon_address()
    assert result["success"] is True
    assert result["deposit_address"] == "MxFreshAddress"
    assert calls["unlock"] == 1
