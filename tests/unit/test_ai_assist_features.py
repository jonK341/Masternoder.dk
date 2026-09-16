"""Unit tests for support FAQ, copy assist, and risk ops services."""
import json
import os
import tempfile

import pytest


def test_faq_keyword_deposit():
    from backend.services.support_faq_service import faq_answer

    r = faq_answer("how do I deposit mn2", use_llm=False)
    assert r["success"] is True
    assert "deposit" in r.get("topic", "") or "Profile" in r["answer"]


def test_faq_empty_lists_topics():
    from backend.services.support_faq_service import faq_answer, list_topics

    r = faq_answer("", use_llm=False)
    assert r["success"] is True
    assert "topics" in r
    assert "deposit" in list_topics()


def test_discord_m8_faq_compat():
    from backend.services.discord_m8_streams import support_faq_answer

    r = support_faq_answer("market order book")
    assert r["success"] is True
    assert "market" in r.get("topic", "") or "market" in r["answer"].lower()


def test_copy_assist_pro_gate(monkeypatch):
    from backend.services import copy_assist_service as cas
    from backend.services import monetization_tier_service as mts

    monkeypatch.setenv("MONETIZATION_TIER_ENFORCEMENT", "1")
    monkeypatch.delenv("MONETIZATION_FORCE_TIER", raising=False)

    def fake_tier(uid):
        return "creator"

    monkeypatch.setattr(mts, "resolve_user_tier", fake_tier)

    out = cas.generate_copy("user_test", "video_title", {"subject": "Test"})
    assert out["success"] is False
    assert out["error"] == "pro_required"


def test_copy_assist_template_fallback(monkeypatch):
    from backend.services.copy_assist_service import generate_copy

    monkeypatch.setenv("MONETIZATION_FORCE_TIER", "pro")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    out = generate_copy("user_pro", "video_title", {"subject": "Nature doc"})
    assert out["success"] is True
    assert "Nature" in out["text"]


def test_risk_ops_read_log():
    from backend.services.mn2_risk_ops_service import read_withdrawal_assessments, risk_summary

    with tempfile.TemporaryDirectory() as tmp:
        log_dir = os.path.join(tmp, "logs")
        os.makedirs(log_dir)
        log_path = os.path.join(log_dir, "mn2_withdrawal_risk.jsonl")
        row = {
            "ts": "2026-06-24T12:00:00Z",
            "user_id": "u1",
            "level": "high",
            "score": 6,
            "reasons": ["new payout address"],
        }
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

        import backend.services.mn2_risk_ops_service as ros

        old = ros._LOG_PATH
        ros._LOG_PATH = log_path
        try:
            rows = read_withdrawal_assessments(limit=10)
            assert len(rows) == 1
            assert rows[0]["user_id"] == "u1"
            summary = risk_summary()
            assert summary["success"] is True
            assert summary["total_logged"] == 1
        finally:
            ros._LOG_PATH = old


def test_admin_risk_routes_unauthorized():
    from flask import Flask
    from backend.routes.ai_assist_routes import ai_assist_bp

    app = Flask(__name__)
    app.register_blueprint(ai_assist_bp)
    with app.test_client() as client:
        r = client.get("/api/admin/risk/summary")
        assert r.status_code in (401, 503)


def test_support_faq_route():
    from flask import Flask
    from backend.routes.ai_assist_routes import ai_assist_bp

    app = Flask(__name__)
    app.register_blueprint(ai_assist_bp)
    with app.test_client() as client:
        r = client.get("/api/support/faq?q=staking&llm=0")
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] is True
        assert "stak" in data["answer"].lower() or data.get("topic") == "staking"
