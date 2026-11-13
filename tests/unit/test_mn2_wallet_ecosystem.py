"""MN2 wallet ecosystem: ledger receive fallback, soft RPC, peer transfer."""

from __future__ import annotations

import json


def test_rpc_url_empty_without_env(monkeypatch):
    from backend.services import mn2_rpc_client as rpc

    monkeypatch.delenv("MN2_RPC_URL", raising=False)
    monkeypatch.delenv("MN2_ALLOW_DEFAULT_RPC_URL", raising=False)
    monkeypatch.setattr(rpc, "_DOTENV_LOADED", True)
    monkeypatch.setattr(
        "backend.services.mn2_rpc_failover.resolve_active_endpoint",
        lambda: None,
    )
    assert rpc._rpc_url() == ""
    out = rpc._call("getblockcount")
    assert out.get("result") is None
    assert out.get("code") == "rpc_unconfigured"
    assert "MN2_RPC_URL" in (out.get("error") or "")


def test_ledger_receive_when_rpc_unconfigured(tmp_path, monkeypatch):
    from backend.services import mn2_wallet_service as ws

    addr_path = tmp_path / "mn2_user_addresses.json"
    addr_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(ws, "_addresses_path", lambda: str(addr_path))
    monkeypatch.setattr(ws, "_wallet_mode", lambda: "ledger")
    monkeypatch.setattr(
        ws,
        "generate_daemon_address",
        lambda: {
            "success": False,
            "error": "rpc_unconfigured: set MN2_RPC_URL",
            "code": "rpc_unconfigured",
            "deposit_address": None,
            "address": None,
        },
    )

    created = ws.get_or_create_deposit_address("eco_user_alice")
    assert created.get("success") is True
    assert created.get("ledger_only") is True
    assert str(created.get("deposit_address") or "").startswith("LGR")

    framed = ws.frame_user_mn2_wallet("eco_user_alice")
    assert framed.get("success") is True
    assert framed.get("ledger_only") is True
    assert framed.get("deposit_address") == created["deposit_address"]

    saved = json.loads(addr_path.read_text(encoding="utf-8"))
    assert saved["eco_user_alice"]["ledger_only"] is True


def test_ledger_peer_transfer_moves_balance(tmp_path, monkeypatch):
    from backend.services import mn2_gift_service as gift
    from backend.services.unified_points_database import unified_points_db

    monkeypatch.setattr(gift, "_DAILY_PATH", str(tmp_path / "mn2_gift_daily.json"))
    monkeypatch.setattr(gift, "_load_config", lambda: {
        "enabled": True,
        "max_per_transfer_mn2": 1000,
        "max_per_day_mn2": 5000,
        "min_balance_after_mn2": 0,
    })
    monkeypatch.setattr(
        "backend.services.mn2_hold_registry.assert_withdrawable",
        lambda user, amt: {"allowed": True},
    )

    sender = "eco_transfer_sender"
    recipient = "eco_transfer_recipient"
    unified_points_db.add_points(sender, "mn2_balance", 5.0, source="test_seed")
    before_s = float((unified_points_db.get_all_points(sender).get("points") or {}).get("mn2_balance") or 0)
    before_r = float((unified_points_db.get_all_points(recipient).get("points") or {}).get("mn2_balance") or 0)

    out = gift.transfer(sender, recipient, 1.25, note="ecosystem smoke")
    assert out.get("success") is True
    assert out.get("amount_mn2") == 1.25

    after_s = float((unified_points_db.get_all_points(sender).get("points") or {}).get("mn2_balance") or 0)
    after_r = float((unified_points_db.get_all_points(recipient).get("points") or {}).get("mn2_balance") or 0)
    assert round(after_s, 8) == round(before_s - 1.25, 8)
    assert round(after_r, 8) == round(before_r + 1.25, 8)


def test_transfer_route_uses_ledger_mode(tmp_path, monkeypatch):
    """POST /api/mn2/transfer must not require fee payer when wallet_mode=ledger."""
    from flask import Flask

    from backend.routes.mn2_routes import mn2_bp
    from backend.services import mn2_gift_service as gift
    from backend.services.unified_points_database import unified_points_db

    sender = "eco_route_sender"
    recipient = "eco_route_recipient"
    unified_points_db.add_points(sender, "mn2_balance", 3.0, source="test_seed")

    monkeypatch.setattr(gift, "_DAILY_PATH", str(tmp_path / "mn2_gift_daily.json"))
    monkeypatch.setattr(
        "backend.routes.mn2_routes.resolve_user_id",
        lambda **kwargs: sender,
    )
    monkeypatch.setattr(
        "backend.services.account_security_service.check_real_money_action",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "backend.services.mn2_onchain_wallet.wallet_mode",
        lambda *a, **k: "ledger",
    )
    monkeypatch.setattr(
        gift,
        "_load_config",
        lambda: {
            "enabled": True,
            "max_per_transfer_mn2": 1000,
            "max_per_day_mn2": 5000,
            "min_balance_after_mn2": 0,
        },
    )
    monkeypatch.setattr(
        "backend.services.mn2_hold_registry.assert_withdrawable",
        lambda user, amt: {"allowed": True},
    )

    app = Flask(__name__)
    app.register_blueprint(mn2_bp)
    client = app.test_client()
    res = client.post(
        "/api/mn2/transfer",
        json={"to": recipient, "amount": 0.5},
        content_type="application/json",
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body.get("success") is True
    assert body.get("mode") == "ledger"
    assert body.get("to_user") == recipient


def test_ledger_address_upgrades_when_rpc_returns(tmp_path, monkeypatch):
    from backend.services import mn2_wallet_service as ws

    addr_path = tmp_path / "mn2_user_addresses.json"
    uid = "eco_upgrade_user"
    lgr = ws._ledger_receive_id(uid)
    addr_path.write_text(json.dumps({
        uid: {
            "primary": lgr,
            "wallet_type": "ledger",
            "ledger_only": True,
            "addresses": [{"label": "primary", "address": lgr, "type": "ledger", "active": True, "ledger_only": True}],
        }
    }), encoding="utf-8")
    monkeypatch.setattr(ws, "_addresses_path", lambda: str(addr_path))
    monkeypatch.setattr(ws, "_wallet_mode", lambda: "ledger")
    monkeypatch.setattr(
        ws,
        "generate_daemon_address",
        lambda: {"success": True, "deposit_address": "JChainUpgradeAddress111111111111", "address": "JChainUpgradeAddress111111111111", "code": None},
    )
    monkeypatch.setattr(ws, "_address_validity", lambda addr: True)

    out = ws.get_or_create_deposit_address(uid)
    assert out.get("success") is True
    assert out.get("ledger_only") is False
    assert out.get("deposit_address") == "JChainUpgradeAddress111111111111"
    assert out.get("upgraded_from_ledger") is True
    saved = json.loads(addr_path.read_text(encoding="utf-8"))
    assert saved[uid]["ledger_only"] is False
    assert saved[uid]["primary"] == "JChainUpgradeAddress111111111111"


def test_scanner_credits_user_not_treasury(tmp_path, monkeypatch):
    from backend.services import mn2_deposit_scanner as scanner
    from backend.services import mn2_ledger as ledger
    from backend.services.unified_points_database import unified_points_db

    uid = "eco_deposit_user"
    chain_addr = "JEcoDepositAddr000000000000001"
    monkeypatch.setattr(scanner, "_load_config", lambda: {"confirmations": 1})
    monkeypatch.setattr(
        "backend.services.mn2_wallet_service.get_address_to_user_map",
        lambda: {chain_addr: uid, "LGRshouldNotCredit": uid},
    )
    monkeypatch.setattr(
        "backend.services.agent_wallet_service.get_treasury",
        lambda: {"address": ""},
    )
    monkeypatch.setattr(
        "backend.services.mn2_order_payment_service.get_address_to_order_map",
        lambda: {},
    )
    monkeypatch.setattr(
        "backend.services.mn2_rpc_client.listtransactions",
        lambda count=1000, skip=0: {
            "result": [
                {"category": "receive", "txid": "txid_eco_1", "address": chain_addr, "amount": 2.5, "confirmations": 6},
                {"category": "receive", "txid": "txid_eco_lgr", "address": "LGRshouldNotCredit", "amount": 9.0, "confirmations": 6},
            ],
            "error": None,
        },
    )
    ledger_path = tmp_path / "mn2_ledger.json"
    ledger_path.write_text(json.dumps({"entries": []}), encoding="utf-8")
    monkeypatch.setattr(ledger, "_ledger_path", lambda: str(ledger_path))

    before = float((unified_points_db.get_all_points(uid).get("points") or {}).get("mn2_balance") or 0)
    result = scanner.run_scanner()
    assert result.get("success") is True
    assert result.get("credits_applied") == 1
    after = float((unified_points_db.get_all_points(uid).get("points") or {}).get("mn2_balance") or 0)
    assert round(after - before, 8) == 2.5

    # Second scan must not double-credit
    again = scanner.run_scanner()
    assert again.get("credits_applied") == 0
    after2 = float((unified_points_db.get_all_points(uid).get("points") or {}).get("mn2_balance") or 0)
    assert round(after2, 8) == round(after, 8)


def test_credit_txids_connects_known_deposit(tmp_path, monkeypatch):
    from backend.services import mn2_deposit_scanner as scanner
    from backend.services import mn2_ledger as ledger
    from backend.services.unified_points_database import unified_points_db

    uid = "eco_txid_user"
    chain_addr = "JEcoTxidAddr00000000000000001"
    monkeypatch.setattr(scanner, "_load_config", lambda: {"confirmations": 1})
    monkeypatch.setattr(
        "backend.services.mn2_wallet_service.get_address_to_user_map",
        lambda: {chain_addr: uid},
    )
    monkeypatch.setattr(
        "backend.services.mn2_rpc_client.gettransaction",
        lambda txid: {
            "result": {
                "txid": txid,
                "confirmations": 8,
                "details": [
                    {"category": "receive", "address": chain_addr, "amount": 0.5},
                ],
            },
            "error": None,
        },
    )
    ledger_path = tmp_path / "mn2_ledger.json"
    ledger_path.write_text(json.dumps({"entries": []}), encoding="utf-8")
    monkeypatch.setattr(ledger, "_ledger_path", lambda: str(ledger_path))

    before = float((unified_points_db.get_all_points(uid).get("points") or {}).get("mn2_balance") or 0)
    out = scanner.credit_txids(["txid_connect_1"])
    assert out.get("success") is True
    assert out.get("credits_applied") == 1
    after = float((unified_points_db.get_all_points(uid).get("points") or {}).get("mn2_balance") or 0)
    assert round(after - before, 8) == 0.5
    again = scanner.credit_txids(["txid_connect_1"])
    assert again.get("credits_applied") == 0


def test_gift_resolves_ledger_receive_id(tmp_path, monkeypatch):
    from backend.services import mn2_gift_service as gift
    from backend.services import mn2_wallet_service as ws
    from backend.services.unified_points_database import unified_points_db

    addr_path = tmp_path / "mn2_user_addresses.json"
    uid = "eco_gift_recv"
    lgr = ws._ledger_receive_id(uid)
    addr_path.write_text(json.dumps({
        uid: {
            "primary": lgr,
            "wallet_type": "ledger",
            "ledger_only": True,
            "addresses": [{"label": "primary", "address": lgr, "type": "ledger", "active": True, "ledger_only": True}],
        }
    }), encoding="utf-8")
    monkeypatch.setattr(ws, "_addresses_path", lambda: str(addr_path))
    monkeypatch.setattr(gift, "_DAILY_PATH", str(tmp_path / "mn2_gift_daily.json"))
    monkeypatch.setattr(gift, "_load_config", lambda: {
        "enabled": True,
        "max_per_transfer_mn2": 1000,
        "max_per_day_mn2": 5000,
        "min_balance_after_mn2": 0,
    })
    monkeypatch.setattr(
        "backend.services.mn2_hold_registry.assert_withdrawable",
        lambda user, amt: {"allowed": True},
    )
    sender = "eco_gift_sender"
    unified_points_db.add_points(sender, "mn2_balance", 2.0, source="test_seed")
    out = gift.transfer(sender, lgr, 0.4, note="via LGR")
    assert out.get("success") is True
    assert out.get("to_user") == uid


def test_micro_burst_in_app_without_chain(monkeypatch):
    from backend.services import mn2_micro_transactions_service as micro

    monkeypatch.setattr(micro, "micro_config", lambda: {
        "enabled": True,
        "amount_mn2": 0.0001,
        "max_per_run": 2,
        "max_per_user_per_day": 10,
        "split_parts": 1,
        "actions": ["aggregator_pulse"],
        "chain_enabled": False,
        "min_chain_mn2": 0.0001,
    })
    monkeypatch.setattr(micro, "_discover_users", lambda limit=80: ["eco_micro_user"])
    monkeypatch.setattr(micro, "_load_state", lambda: {"users": {}, "runs": []})
    monkeypatch.setattr(micro, "_save_state", lambda state: None)
    monkeypatch.setattr(
        micro,
        "_credit_micro",
        lambda user_id, amount, action, slot=0, dry_run=False: {
            "success": True,
            "amount": amount,
            "user_id": user_id,
        },
    )
    out = micro.run_micro_transaction_burst(max_txs=1)
    assert out.get("success") is True
    assert out.get("mode") == "in_app_only"
    assert out.get("in_app_only") == 1
    assert out.get("skipped_reason") != "chain_reward_payouts_disabled"


def test_first_withdraw_skips_cooldown(tmp_path, monkeypatch):
    from backend.services import mn2_withdrawal_guard as guard

    monkeypatch.setattr(guard, "_PATH", str(tmp_path / "mn2_withdrawal_addresses.json"))
    uid = "eco_withdraw_first"
    assert guard.has_successful_withdrawal(uid) is False
    # Route applies cooldown=0 while user has no successful withdraw yet.
    gate = guard.check_address(uid, "JFirstPayoutAddr00000000000001", 0)
    assert gate.get("allowed") is True
    assert guard.has_successful_withdrawal(uid) is False
    # Same address retry before success still allowed with grace cooldown 0.
    again = guard.check_address(uid, "JFirstPayoutAddr00000000000001", 0)
    assert again.get("allowed") is True
    guard.record_success(uid, "JFirstPayoutAddr00000000000001")
    assert guard.has_successful_withdrawal(uid) is True
    # After a success, a brand-new address respects cooldown.
    blocked = guard.check_address(uid, "JSecondPayoutAddr0000000000002", 24)
    assert blocked.get("allowed") is False
    assert blocked.get("code") == "address_cooldown"


def test_pool_address_assigned_to_user(tmp_path, monkeypatch):
    from backend.services import mn2_wallet_service as ws

    addr_path = tmp_path / "mn2_user_addresses.json"
    addr_path.write_text(json.dumps({"pool_1": "JPoolAddressForUser000000000001"}), encoding="utf-8")
    monkeypatch.setattr(ws, "_addresses_path", lambda: str(addr_path))
    monkeypatch.setattr(ws, "_address_validity", lambda addr: True)
    monkeypatch.setattr(
        ws,
        "generate_daemon_address",
        lambda: {"success": False, "error": "should_not_call", "code": "unused", "deposit_address": None},
    )

    out = ws.get_or_create_deposit_address("eco_pool_user")
    assert out.get("success") is True
    assert out.get("deposit_address") == "JPoolAddressForUser000000000001"
    assert out.get("ledger_only") is False
    saved = json.loads(addr_path.read_text(encoding="utf-8"))
    assert "pool_1" not in saved
    assert saved["eco_pool_user"]["primary"] == "JPoolAddressForUser000000000001"


def test_unwritable_address_store_returns_error(tmp_path, monkeypatch):
    from backend.services import mn2_wallet_service as ws

    monkeypatch.setattr(ws, "_addresses_path", lambda: str(tmp_path / "mn2_user_addresses.json"))
    monkeypatch.setattr(ws, "_address_validity", lambda addr: True)
    monkeypatch.setattr(
        ws,
        "generate_daemon_address",
        lambda: {
            "success": True,
            "deposit_address": "JNewFromDaemon0000000000000001",
            "address": "JNewFromDaemon0000000000000001",
            "code": None,
        },
    )

    def raise_os(_addresses):
        raise OSError("Cannot write deposit address map: Permission denied")

    monkeypatch.setattr(ws, "_save_addresses", raise_os)
    out = ws.get_or_create_deposit_address("eco_perm_user")
    assert out.get("success") is False
    assert out.get("code") == "address_store_unwritable"
    assert "Permission denied" in (out.get("error") or "")
