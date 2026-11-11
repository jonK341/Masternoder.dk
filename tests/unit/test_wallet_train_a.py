"""Train A core rail (W-01…W-10) smoke tests."""
from __future__ import annotations

from flask import Flask


def test_train_a_manifest_and_runners():
    from backend.services import wallet_train_a_service as train_a

    manifest = train_a.train_a_manifest()
    assert manifest["success"] is True
    assert manifest["count"] == 10
    assert manifest["ids"] == [f"W-{i:02d}" for i in range(1, 11)]
    assert manifest["target"] == "v1.4.0.0"

    run = train_a.run_train_a(user_id="train_a_tester")
    assert run["ok_count"] == 10
    assert run["results"]["W-02"]["estimate"]["suggested_fee_mn2"] > 0
    assert run["results"]["W-10"]["compose"]["exists"] is True

    acc = train_a.train_a_acceptance(user_id="train_a_tester")
    assert acc["passed"] is True
    ids = [c["id"] for c in acc["checks"]]
    assert "multi_rpc_failover" in ids
    assert "ledger_por_glance" in ids
    assert "compose_profile" in ids


def test_train_a_routes():
    from backend.routes.mn2_routes import mn2_bp

    app = Flask(__name__)
    app.register_blueprint(mn2_bp)
    c = app.test_client()

    ver = c.get("/api/mn2/train-a/version")
    assert ver.status_code == 200
    body = ver.get_json()
    assert body["target"] == "v1.4.0.0"
    assert body["channel"] == "draft"
    assert body["latest_wallet_download_unchanged"] is True

    run = c.get("/api/mn2/train-a/run")
    assert run.status_code == 200
    run_body = run.get_json()
    assert run_body["ok_count"] == 10

    one = c.get("/api/mn2/train-a/W-08")
    assert one.status_code == 200
    assert one.get_json()["id"] == "W-08"

    acc = c.get("/api/mn2/train-a/acceptance")
    assert acc.status_code == 200
    assert acc.get_json()["passed"] is True
