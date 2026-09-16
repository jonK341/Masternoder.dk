"""Plan 002 WR-G1 — 4D Trophy Monitor BFF."""
from __future__ import annotations

from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_monitor_payload_guest():
    from backend.services.wallet_v2_trophy_monitor_service import build_4d_trophy_monitor

    with patch("backend.services.wallet_v2_service._network_snapshot", return_value={"block_height": 42}):
        with patch("backend.services.block_mint_service.get_block_drops", return_value={"drops": []}):
            out = build_4d_trophy_monitor("guest")

    assert out["success"] is True
    assert out["guest"] is True
    assert out["network"]["block_height"] == 42
    assert out["trophies"] == []


def test_monitor_route():
    from flask import Flask
    from backend.routes.wallet_v2_routes import wallet_v2_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(wallet_v2_bp)

    payload = {"success": True, "trophies": [], "network": {"block_height": 1}}
    with app.test_client() as client:
        with patch("backend.routes.wallet_v2_routes.resolve_user_id", return_value="u1"):
            with patch(
                "backend.services.wallet_v2_trophy_monitor_service.build_4d_trophy_monitor",
                return_value=payload,
            ):
                resp = client.get("/api/wallet/v2/trophy-monitor/4d")

    assert resp.status_code == 200
    assert (resp.get_json() or {}).get("success") is True
