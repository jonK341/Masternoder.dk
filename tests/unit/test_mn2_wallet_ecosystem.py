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
