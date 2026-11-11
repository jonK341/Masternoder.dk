"""Train B tools & debuggers (W-11…W-20) smoke tests."""
from __future__ import annotations

from flask import Flask


def test_train_b_manifest_and_runners():
    from backend.services import wallet_train_b_service as train_b

    manifest = train_b.train_b_manifest()
    assert manifest["success"] is True
    assert manifest["count"] == 10
    assert manifest["ids"] == [f"W-{i:02d}" for i in range(11, 21)]
    assert manifest["target"] == "v1.5.0.0"

    run = train_b.run_train_b()
    assert run["ok_count"] == 10
    assert run["results"]["W-11"]["passed"] is True
    assert run["results"]["W-18"]["count"] >= 8
    assert run["results"]["W-19"]["passed"] is True

    acc = train_b.train_b_acceptance()
    assert acc["passed"] is True
    ids = [c["id"] for c in acc["checks"]]
    assert "static_check" in ids
    assert "rpc_regression_pack" in ids


def test_train_b_routes():
    from backend.routes.mn2_routes import mn2_bp

    app = Flask(__name__)
    app.register_blueprint(mn2_bp)
    c = app.test_client()

    ver = c.get("/api/mn2/train-b/version")
    assert ver.status_code == 200
    body = ver.get_json()
    assert body["target"] == "v1.5.0.0"
    assert body["train"] == "B"
    assert body["latest_wallet_download_unchanged"] is True

    run = c.get("/api/mn2/train-b/run")
    assert run.status_code == 200
    assert run.get_json()["ok_count"] == 10

    one = c.get("/api/mn2/train-b/W-16")
    assert one.status_code == 200
    assert one.get_json()["id"] == "W-16"
    assert one.get_json()["case_count"] == 4

    acc = c.get("/api/mn2/train-b/acceptance")
    assert acc.status_code == 200
    assert acc.get_json()["passed"] is True
