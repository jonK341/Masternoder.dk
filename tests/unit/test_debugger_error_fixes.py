"""Guards for the live debugger error groups."""
from flask import Flask


def test_user_id_policy_statuses():
    from backend.services.user_id_policy import is_placeholder_user_id, rejection_for

    assert rejection_for("user_b157a4c52652") is None
    assert rejection_for("jon") is None
    assert rejection_for("Sander Sahk") is None
    assert is_placeholder_user_id("default_user")
    assert is_placeholder_user_id("undefined")
    assert is_placeholder_user_id("null")
    assert is_placeholder_user_id("[object Promise]")

    missing, status = rejection_for("default_user")
    assert status == 401
    assert missing["code"] == "user_unauthenticated"
    assert rejection_for("")[1] == 401
    assert rejection_for("undefined")[1] == 401
    assert rejection_for("null")[1] == 401
    assert rejection_for("[object Promise]")[1] == 401


def test_points_all_rejects_placeholder_and_display_name():
    from backend.routes.points_routes import points_bp

    app = Flask(__name__)
    app.register_blueprint(points_bp)
    client = app.test_client()

    placeholder = client.get("/api/points/all?user_id=default_user")
    assert placeholder.status_code == 401
    assert placeholder.get_json()["code"] == "user_unauthenticated"


def test_points_legacy_ids_lookup(monkeypatch):
    from backend.routes.points_routes import points_bp

    app = Flask(__name__)
    app.register_blueprint(points_bp)
    client = app.test_client()

    monkeypatch.setattr("backend.routes.points_routes.user_exists", lambda uid: False)
    absent = client.get("/api/points/all", query_string={"user_id": "Sander Sahk"})
    assert absent.status_code == 404
    assert absent.get_json()["code"] == "user_not_found"

    monkeypatch.setattr(
        "backend.routes.points_routes.user_exists",
        lambda uid: uid in {"jon", "Sander Sahk"},
    )
    for legacy in ("jon", "Sander Sahk"):
        found = client.get("/api/points/all", query_string={"user_id": legacy})
        assert found.status_code == 200, legacy
        assert found.get_json()["user_id"] in {legacy, "default_user"} or found.get_json().get("success") is not False


def test_aggregated_profile_rejects_bad_ids(monkeypatch):
    from backend.routes.user_profile_routes import user_profile_bp

    app = Flask(__name__)
    app.register_blueprint(user_profile_bp)
    client = app.test_client()
    monkeypatch.setattr("backend.routes.user_profile_routes.user_exists", lambda uid: False)

    response = client.get("/api/user/profile/Sander%20Sahk/aggregated")
    assert response.status_code == 404
    body = response.get_json()
    assert body["code"] == "user_not_found"

    present = client.get("/api/user/profile/jon")
    monkeypatch.setattr("backend.routes.user_profile_routes.user_exists", lambda uid: uid == "jon")
    # jon is not a placeholder; a confirmed miss was patched above. Re-bind and expect the lookup to proceed.
    monkeypatch.setattr("backend.routes.user_profile_routes.user_exists", lambda uid: uid == "jon")
    allowed = client.get("/api/user/profile/jon")
    assert allowed.status_code != 401

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


def test_handler_status_is_real(monkeypatch):
    from backend.routes.error_handler_status_routes import error_handler_status_bp

    monkeypatch.setenv("DEBUGGER_ADMIN_KEY", "test-admin-key")
    app = Flask(__name__)
    app.register_blueprint(error_handler_status_bp)
    client = app.test_client()
    locked = client.get("/api/errors/handler-status")
    assert locked.status_code == 401
    response = client.get("/api/errors/handler-status", headers={"X-Admin-Key": "test-admin-key"})
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


def test_legacy_user_exists_in_sqlite(tmp_path):
    from flask import Flask
    from sqlalchemy import text

    from src.db.models import db

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(tmp_path / "users.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.session.execute(text(
            "CREATE TABLE user_profiles (id INTEGER PRIMARY KEY, user_id VARCHAR(128) UNIQUE)"
        ))
        db.session.execute(text("INSERT INTO user_profiles (user_id) VALUES ('jon')"))
        db.session.execute(text("INSERT INTO user_profiles (user_id) VALUES ('Sander Sahk')"))
        db.session.commit()
        from backend.services.user_id_policy import user_exists

        assert user_exists("jon") is True
        assert user_exists("Sander Sahk") is True
        assert user_exists("missing-person") is False


def test_scanner_missing_is_frontend_calls_only():
    from backend.services.api_scanner import APIScanner

    missing = APIScanner().find_missing_frontend_calls()
    paths = {item["path"] for item in missing}
    assert len(missing) < 2783
    assert "/api/api_scanner/create" not in paths
    assert "/api/points/all" not in paths
    assert all("suggested_function" not in item for item in missing)


def test_check_duplicates_skips_page_redirects():
    from flask import Flask

    from backend.routes.all_page_routes import all_page_bp
    from backend.routes.debug_routes import check_duplicates

    app = Flask(__name__)
    app.register_blueprint(all_page_bp)
    with app.test_request_context():
        payload = check_duplicates().get_json()
    endpoints = []
    for item in payload.get("duplicates") or []:
        endpoints.extend(item.get("endpoints") or [])
    assert not any("redirect_" in name for name in endpoints)


def test_health_schema_columns_match_ledger():
    from backend.services.schema_bootstrap import SCHEMA_MIGRATIONS_HEALTH_COLUMNS

    assert SCHEMA_MIGRATIONS_HEALTH_COLUMNS == ("script_name", "status", "applied_at")


def test_fleet_stream_chat_string_is_closed():
    from pathlib import Path

    text = Path("static/js/fleet-stream-chat.js").read_text(encoding="utf-8")
    assert '</p>";' not in text
    assert "f5-stream-chat-meta" in text
