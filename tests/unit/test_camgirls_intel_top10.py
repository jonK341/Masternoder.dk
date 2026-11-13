"""Camgirls UI intelligence Top 10 API."""
from backend.services.camgirls_ui_intel_service import top10_performers, _vibe


def test_vibe_cosmic():
    assert _vibe("performer_wave3_nebula_prime", "Nebula") == "cosmic"


def test_top10_contract():
    out = top10_performers(user_id="default_user")
    assert out.get("success") is True
    assert len(out.get("top10") or []) == 10
    row = out["top10"][0]
    assert row.get("rank") == 1
    assert "score" in row
    assert "technologies" in row
    assert "intel_stack" in out
