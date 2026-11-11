"""Train D monitors & navigation (W-31…W-40) smoke tests."""
from __future__ import annotations

from flask import Flask


def test_train_d_manifest_and_runners():
    from backend.services import wallet_train_d_service as train_d

    manifest = train_d.train_d_manifest()
    assert manifest["success"] is True
    assert manifest["count"] == 10
    assert manifest["ids"] == [f"W-{i:02d}" for i in range(31, 41)]
    assert manifest["target"] == "v1.6.0.0"

    run = train_d.run_train_d(user_id="train_d_tester")
    assert run["ok_count"] == 10
    assert "mn2_wallet_health" in (run["results"]["W-35"].get("openmetrics") or "")
    assert len(run["results"]["W-40"].get("steps") or []) >= 3

    acc = train_d.train_d_acceptance(user_id="train_d_tester")
    assert acc["passed"] is True
    ids = [c["id"] for c in acc["checks"]]
    assert "health_monitor" in ids
    assert "metrics_exporter" in ids
    assert "guided_flow" in ids


def test_train_d_routes():
    from backend.routes.mn2_routes import mn2_bp

    app = Flask(__name__)
    app.register_blueprint(mn2_bp)
    c = app.test_client()

    ver = c.get("/api/mn2/train-d/version")
    assert ver.status_code == 200
    body = ver.get_json()
    assert body["target"] == "v1.6.0.0"
    assert body["train"] == "D"

    run = c.get("/api/mn2/train-d/run")
    assert run.status_code == 200
    assert run.get_json()["ok_count"] == 10

    one = c.get("/api/mn2/train-d/W-40?step=status")
    assert one.status_code == 200
    assert one.get_json()["id"] == "W-40"

    acc = c.get("/api/mn2/train-d/acceptance")
    assert acc.status_code == 200
    assert acc.get_json()["passed"] is True
