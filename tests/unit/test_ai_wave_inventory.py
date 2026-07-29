"""Phase 13 AI wave inventory tests."""
from flask import Flask


def test_wave_inventory_counts():
    from backend.services.ai_wave_inventory_service import wave_inventory
    data = wave_inventory()
    assert data["success"] is True
    assert len(data["core_25"]) == 25
    assert len(data["monetization_waves"]) == 25
    totals = data["counts"]["total"]
    assert totals["live"] + totals["partial"] + totals["deferred"] == 50


def test_waves_route():
    from backend.routes.ai_intelligence_dashboard_routes import ai_intelligence_dashboard_bp
    app = Flask(__name__)
    app.register_blueprint(ai_intelligence_dashboard_bp)
    c = app.test_client()
    r = c.get("/api/ai-intelligence/waves")
    assert r.status_code == 200
    assert r.get_json().get("success") is True
