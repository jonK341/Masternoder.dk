"""Guards for the live debugger error groups."""
from flask import Flask


def test_user_id_policy_statuses():
    from backend.services.user_id_policy import is_canonical_user_id, rejection_for

    assert is_canonical_user_id("user_b157a4c52652")
    assert rejection_for("user_b157a4c52652") is None

    missing, status = rejection_for("default_user")
    assert status == 401
    assert missing["code"] == "user_unauthenticated"
    assert rejection_for("")[1] == 401
    assert rejection_for("[object Promise]")[1] == 401

    display, status = rejection_for("Sander Sahk")
    assert status == 404
    assert display["error"] == "not a user id"
    assert rejection_for("jon")[1] == 404


def test_points_all_rejects_placeholder_and_display_name():
    from backend.routes.points_routes import points_bp

    app = Flask(__name__)
    app.register_blueprint(points_bp)
    client = app.test_client()

    placeholder = client.get("/api/points/all?user_id=default_user")
    assert placeholder.status_code == 401
    assert placeholder.get_json()["code"] == "user_unauthenticated"

    named = client.get("/api/points/all", query_string={"user_id": "Sander Sahk"})
    assert named.status_code == 404
    assert named.get_json()["error"] == "not a user id"
    assert "Endpoint auto-created" not in named.get_data(as_text=True)


def test_aggregated_profile_rejects_bad_ids():
    from backend.routes.user_profile_routes import user_profile_bp

    app = Flask(__name__)
    app.register_blueprint(user_profile_bp)
    client = app.test_client()

    response = client.get("/api/user/profile/Sander%20Sahk/aggregated")
    assert response.status_code == 404
    body = response.get_json()
    assert body["code"] == "user_not_found"
    assert body["error"] == "not a user id"

    empty = client.get("/api/user/profile/default_user")
    assert empty.status_code == 401


def test_social_user_route_rejects_promise_string():
    from backend.routes.social_routes import social_bp

    app = Flask(__name__)
    app.register_blueprint(social_bp)
    client = app.test_client()
    response = client.get("/api/social/user/[object Promise]")
    assert response.status_code == 401
    assert response.get_json()["code"] == "user_unauthenticated"


def test_handler_status_is_real():
    from backend.routes.error_handler_status_routes import error_handler_status_bp

    app = Flask(__name__)
    app.register_blueprint(error_handler_status_bp)
    response = app.test_client().get("/api/errors/handler-status")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["message"] == "handler status"
    assert "analysis" in body
    assert body.get("auto_fixed") is not True


def test_errors_index_route_registered():
    from backend.routes.error_logging_routes import error_logging_bp

    app = Flask(__name__)
    app.register_blueprint(error_logging_bp)
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/errors" in rules
    assert "/api/errors/list" in rules


def test_unknown_api_is_not_auto_created(monkeypatch):
    monkeypatch.delenv("AUTO_FIX_404_STUBS", raising=False)
    from backend.middleware.auto_fix_404_middleware import register_auto_fix_middleware

    app = Flask(__name__)
    register_auto_fix_middleware(app)
    response = app.test_client().get("/api/not-a-real-endpoint")
    assert response.status_code == 404
    body = response.get_json()
    assert body.get("message") != "Endpoint auto-created"
    assert body.get("auto_fixed") is not True


def test_paypal_mn2_packs_route_registered():
    from backend.routes.missing_endpoints_routes import missing_endpoints_bp

    app = Flask(__name__)
    app.register_blueprint(missing_endpoints_bp)
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/exchange/paypal/mn2-packs" in rules


def test_overview_cache(monkeypatch):
    import backend.services.game_hub_service as svc

    svc._OVERVIEW_CACHE.clear()
    calls = {"n": 0}

    def fake(uid):
        calls["n"] += 1
        return {"success": True, "user_id": uid, "tabs": {}}

    monkeypatch.setattr(svc, "_build_overview", fake)
    first = svc.get_overview("user_cachetest")
    second = svc.get_overview("user_cachetest")
    assert calls["n"] == 1
    assert first.get("cached") is not True
    assert second.get("cached") is True
    svc._OVERVIEW_CACHE.clear()


def test_point_ledger_schema_is_idempotent(tmp_path):
    from flask import Flask
    from sqlalchemy import inspect, text

    from src.db.models import db

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(tmp_path / "ledger.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        from backend.services.schema_bootstrap import ensure_point_ledger_schema

        assert ensure_point_ledger_schema() is True
        assert ensure_point_ledger_schema() is True
        names = set(inspect(db.engine).get_table_names())
        assert "point_transactions" in names
        assert "schema_migrations" in names
        cols = {col["name"] for col in inspect(db.engine).get_columns("point_transactions")}
        assert {"user_id", "system_name", "transaction_type", "amount", "metadata", "created_at"} <= cols
        row = db.session.execute(text("SELECT version, status FROM schema_migrations")).first()
        assert row[0] == "20261010_point_transactions_schema_migrations"
        assert row[1] == "applied"
        count = db.session.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar()
        assert count == 1


def test_fleet_stream_chat_string_is_closed():
    from pathlib import Path

    text = Path("static/js/fleet-stream-chat.js").read_text(encoding="utf-8")
    assert '</p>";' not in text
    assert "f5-stream-chat-meta" in text
