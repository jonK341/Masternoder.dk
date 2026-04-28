"""Unit tests for COGS metering + LLM usage aggregation (monetization investigation)."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

from backend.services.llm_service import LLMResponse, accumulate_llm_usage_from_response
from backend.services.cogs_metering_service import summarize_metering_jsonl


def test_accumulate_llm_usage_merges_totals():
    t: dict = {}
    accumulate_llm_usage_from_response(t, None)
    assert t == {}

    accumulate_llm_usage_from_response(
        t,
        LLMResponse(success=True, content="a", usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}),
    )
    assert t["total_tokens"] == 150

    accumulate_llm_usage_from_response(
        t,
        LLMResponse(success=True, content="b", usage={"prompt_tokens": 10, "completion_tokens": 20}),
    )
    assert t["total_tokens"] == 180
    assert t["prompt_tokens"] == 110


def test_summarize_metering_jsonl_percentiles():
    row = {
        "cogs_usd": {
            "total_usd": 0.1,
            "runway_video_api": 0.05,
            "encode_compute": 0.02,
            "storage_1mo": 0.01,
            "llm_blend": 0.02,
        },
        "ratio_vs_reference_job": 1.5,
    }
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
            f.write(json.dumps(row) + "\n")
        s = summarize_metering_jsonl(path=path)
        assert s["success"] is True
        assert s["count"] == 2
        assert s["total_usd"]["p90"] >= s["total_usd"]["p50"]
    finally:
        os.unlink(path)


def test_cogs_blueprint_routes_minimal_app():
    from flask import Flask

    from backend.routes.cogs_routes import cogs_bp

    app = Flask(__name__)
    app.register_blueprint(cogs_bp)
    client = app.test_client()

    r = client.get("/api/system/cogs/summary")
    assert r.status_code == 200
    assert r.get_json().get("success") is True

    r2 = client.get("/api/system/cogs/reference-job")
    assert r2.status_code == 200
    assert r2.get_json().get("success") is True

    prev = os.environ.get("COGS_ADMIN_REPORT_KEY")
    os.environ["COGS_ADMIN_REPORT_KEY"] = "test-secret-key"
    try:
        r3 = client.get("/api/system/cogs/metering-stats", headers={"X-Cogs-Admin-Key": "wrong"})
        assert r3.status_code == 401
        r4 = client.get("/api/system/cogs/metering-stats", headers={"X-Cogs-Admin-Key": "test-secret-key"})
        # No metering file locally → 404 or empty file path; accept 404 (missing file) or 200 (no_rows)
        assert r4.status_code in (200, 404)
    finally:
        if prev is None:
            os.environ.pop("COGS_ADMIN_REPORT_KEY", None)
        else:
            os.environ["COGS_ADMIN_REPORT_KEY"] = prev


def test_monetization_config_degrades_without_500(monkeypatch):
    from flask import Flask

    from backend.routes.cogs_routes import cogs_bp

    app = Flask(__name__)
    app.register_blueprint(cogs_bp)

    def boom():
        raise RuntimeError("config read failed")

    monkeypatch.setattr("backend.services.monetization_config_service.get_public_config", boom)

    r = app.test_client().get("/api/monetization/config")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("degraded") is True
    assert data.get("default_tier") == "creator"
