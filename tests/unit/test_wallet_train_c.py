"""Train C trackers & scanners (W-21…W-30) smoke tests."""
from __future__ import annotations

from flask import Flask


def test_train_c_manifest_and_runners():
    from backend.services import wallet_train_c_service as train_c

    manifest = train_c.train_c_manifest()
    assert manifest["success"] is True
    assert manifest["count"] == 10
    assert manifest["ids"] == [f"W-{i:02d}" for i in range(21, 31)]
    assert manifest["target"] == "v1.5.0.0"

    run = train_c.run_train_c(user_id="train_c_tester")
    assert run["ok_count"] == 10
    assert run["results"]["W-30"]["passed"] is True
    assert run["results"]["W-29"]["count"] >= 6

    acc = train_c.train_c_acceptance(user_id="train_c_tester")
    assert acc["passed"] is True
    ids = [c["id"] for c in acc["checks"]]
    assert "activity_feed" in ids
    assert "conf_lint" in ids
    assert "peer_panel" in ids


def test_train_c_routes():
    from backend.routes.mn2_routes import mn2_bp

    app = Flask(__name__)
    app.register_blueprint(mn2_bp)
    c = app.test_client()

    ver = c.get("/api/mn2/train-c/version")
    assert ver.status_code == 200
    body = ver.get_json()
    assert body["target"] == "v1.5.0.0"
    assert body["train"] == "C"
    assert body["finishes_hardened"] is True

    run = c.get("/api/mn2/train-c/run")
    assert run.status_code == 200
    assert run.get_json()["ok_count"] == 10

    one = c.get("/api/mn2/train-c/W-21")
    assert one.status_code == 200
    assert one.get_json()["id"] == "W-21"

    acc = c.get("/api/mn2/train-c/acceptance")
    assert acc.status_code == 200
    assert acc.get_json()["passed"] is True
