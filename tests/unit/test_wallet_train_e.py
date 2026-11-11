"""Train E advanced intelligence (W-41…W-50) smoke tests."""
from __future__ import annotations

from flask import Flask


def test_train_e_manifest_and_runners():
    from backend.services import wallet_train_e_service as train_e

    manifest = train_e.train_e_manifest()
    assert manifest["success"] is True
    assert manifest["count"] == 10
    assert manifest["ids"] == [f"W-{i:02d}" for i in range(41, 51)]
    assert manifest["target"] == "v1.6.6.0"

    run = train_e.run_train_e(user_id="train_e_tester")
    assert run["ok_count"] == 10
    assert run["results"]["W-46"]["success"] is True
    assert len(run["results"]["W-49"].get("pipeline") or []) >= 4

    # Fixture bad send should block under hard enforce (default ON).
    bad = train_e.anomaly_guard(
        user_id="train_e_tester",
        amount=99.0,
        balance=100.0,
        address="MNbad",
    )
    assert bad["fixture_large_out"] is True
    assert bad["blocked"] is True

    acc = train_e.train_e_acceptance(user_id="train_e_tester")
    assert acc["passed"] is True
    ids = [c["id"] for c in acc["checks"]]
    assert "anomaly_blocks_fixture" in ids
    assert "workflow_pipeline" in ids
    assert "latest_unchanged" in ids


def test_train_e_routes():
    from backend.routes.mn2_routes import mn2_bp

    app = Flask(__name__)
    app.register_blueprint(mn2_bp)
    c = app.test_client()

    ver = c.get("/api/mn2/train-e/version")
    assert ver.status_code == 200
    body = ver.get_json()
    assert body["target"] == "v1.6.6.0"
    assert body["giga"] is True
    assert body["latest_wallet_download_unchanged"] is True

    run = c.get("/api/mn2/train-e/run")
    assert run.status_code == 200
    assert run.get_json()["ok_count"] == 10

    one = c.get("/api/mn2/train-e/W-49?step=status")
    assert one.status_code == 200
    assert one.get_json()["id"] == "W-49"

    acc = c.get("/api/mn2/train-e/acceptance")
    assert acc.status_code == 200
    assert acc.get_json()["passed"] is True
