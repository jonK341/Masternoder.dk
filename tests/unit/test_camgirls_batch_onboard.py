"""Camgirls wave batch parse + dry-run normalization."""
import json
import os
import tempfile

import pytest

from backend.services.camgirls_wave_ops import build_wave_batch, normalize_wave_stub


def test_normalize_wave_stub_assigns_id_and_media():
    perf, media = normalize_wave_stub(
        {
            "slug": "host-z",
            "display_name": "Zara Host",
            "media": {"c1": "#111111", "c2": "#222222"},
        },
        index=1,
        id_prefix="performer_wave2_",
    )
    assert perf["id"] == "performer_wave2_host_z"
    assert perf["display_name"] == "Zara Host"
    assert media["slug"] == "host-z"
    assert media["initials"] == "ZH"
    assert perf["avatar_url"].endswith("/static/camgirls/media/host-z/icon.svg")


def test_build_wave_batch_skips_example_rows():
    doc = {
        "wave": 9,
        "performers": [
            {"_example": True, "display_name": "Skip Me"},
            {
                "slug": "live-one",
                "display_name": "Live One",
                "media": {"slug": "live-one", "initials": "LO", "c1": "#000", "c2": "#fff"},
            },
        ],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(doc, f)
        path = f.name
    try:
        performers, media, summary = build_wave_batch(path, batch=9)
        assert summary["id_prefix"] == "performer_wave9_"
        assert len(performers) == 1
        assert performers[0]["id"] == "performer_wave9_live_one"
        assert "performer_wave9_live_one" in media
    finally:
        os.unlink(path)


def test_build_wave_batch_csv():
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="") as f:
        f.write("display_name,slug,initials,c1,c2\n")
        f.write("CSV Star,csv-star,CS,#abc,#def\n")
        path = f.name
    try:
        performers, media, summary = build_wave_batch(path, id_prefix="performer_csv_")
        assert summary["normalized"] == 1
        assert performers[0]["display_name"] == "CSV Star"
        assert media[performers[0]["id"]]["initials"] == "CS"
    finally:
        os.unlink(path)


def test_example_row_raises_when_not_skipped():
    with pytest.raises(ValueError, match="_example"):
        normalize_wave_stub({"_example": True, "display_name": "X"}, index=1, id_prefix="p_")
