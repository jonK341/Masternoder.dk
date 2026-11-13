"""Sellable film pipeline — story, gate, and orchestrated compose."""
from __future__ import annotations

import os

import pytest

from backend.services import ai_provider_gate as gate
from backend.services import sellable_film_pipeline as sell


def test_design_sellable_story_is_prompt_locked():
    out = sell.design_sellable_story("two sailors on a red harbour boat at dawn", 12)
    assert out["success"] is True
    assert out["run_id"].startswith("sell_")
    assert 2 <= len(out["beats"]) <= 3
    assert "red harbour" in out["story"].lower()
    assert "Photoreal" in out["beats"][0]["image_prompt"]
    assert "red harbour" in out["beats"][0]["image_prompt"].lower()
    assert abs(sum(b["duration_sec"] for b in out["beats"]) - 12) < 0.6
    assert all(4.0 <= b["duration_sec"] <= 5.5 for b in out["beats"])
    assert len(out["narration"]) == len(out["beats"])
    assert "narrative" in out["beats"][0]["image_prompt"].lower() or "story beat" in out["beats"][0]["image_prompt"].lower()


def test_quality_gate_requires_audio_and_real_motion(tmp_path):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"0" * 200_000)
    bad = sell.evaluate_quality_gate(
        local_path=str(path),
        has_audio=False,
        motion_backends=["runway"],
        duration_sec=5,
    )
    assert bad["sellable"] is False
    assert "missing_audio" in bad["reasons"]

    good = sell.evaluate_quality_gate(
        local_path=str(path),
        has_audio=True,
        motion_backends=["runway", "pika"],
        duration_sec=5,
    )
    assert good["sellable"] is True
    assert good["quality"] == "sellable"

    local = sell.evaluate_quality_gate(
        local_path=str(path),
        has_audio=True,
        motion_backends=["premium_local"],
        duration_sec=5,
    )
    assert local["sellable"] is True
    assert local["quality"] == "sellable_local"

    gif_line = sell.evaluate_quality_gate(
        local_path=str(path),
        has_audio=True,
        motion_backends=["story_gif_line"],
        duration_sec=5,
        has_narration=True,
        sfx_count=12,
        fx_count=12,
        hero_frames=6,
        beats=2,
    )
    assert gif_line["sellable"] is True
    assert gif_line["quality"] == "sellable_local"
    assert gif_line["quality_pct"] > 90
    assert gif_line["sfx_count"] == 12
    assert gif_line["fx_count"] == 12


def test_auto_store_gallery_requires_quality_over_90(tmp_path, monkeypatch):
    src = tmp_path / "clip.mp4"
    src.write_bytes(b"0" * 250_000)
    videos = tmp_path / "videos"
    videos.mkdir()
    monkeypatch.setenv("VIDEOS_DIR", str(videos))

    class _VG:
        VIDEOS_DIR = str(videos)

    import sys
    monkeypatch.setitem(sys.modules, "backend.services.video_generator_service", _VG)

    gate_low = {
        "sellable": True,
        "quality": "sellable_local",
        "quality_pct": 88,
        "quality_score": 0.88,
    }
    low = sell._auto_store_gallery(
        local_path=str(src),
        prompt="harbour",
        story={"title": "Harbour", "story": "A short harbour tale"},
        gate_result=gate_low,
        duration_sec=8,
        motion_backends=["story_gif_line"],
    )
    assert low["stored"] is False

    gate_hi = dict(gate_low, quality_pct=93, quality_score=0.93)
    hi = sell._auto_store_gallery(
        local_path=str(src),
        prompt="harbour",
        story={"title": "Harbour Dawn", "story": "Sailors push off at sunrise"},
        gate_result=gate_hi,
        duration_sec=8,
        motion_backends=["story_gif_line"],
    )
    assert hi["stored"] is True
    assert hi["gallery_id"]
    assert os.path.isfile(hi["gallery_path"])
    assert os.path.isfile(hi["status_path"])


def test_provider_gate_blocks_credit_wallets():
    status = gate.ensure_defaults()
    assert gate.is_blocked("runway")
    assert gate.is_blocked("modelslab")
    assert gate.is_blocked("replicate")
    assert gate.is_blocked("heygen")
    assert gate.is_blocked("fal")
    assert "pollinations_flux" in status["active_image"]
    assert "story_gif_line" in status["active_motion"]


def test_compose_sellable_movie_uses_motion_and_audio(tmp_path, monkeypatch):
    story = sell.design_sellable_story("harbour night", 6)

    def fake_still(prompt, dest_dir, seed):
        path = os.path.join(dest_dir, "still_%s.jpg" % seed)
        with open(path, "wb") as handle:
            handle.write(b"\xff\xd8\xff" + b"1" * 1200)
        return {"success": True, "local_path": path, "source": "test"}

    def fake_motion(**kwargs):
        dest = kwargs["dest_dir"]
        path = os.path.join(dest, "motion_%s.mp4" % uuid_hex())
        with open(path, "wb") as handle:
            handle.write(b"mp4" * 80_000)
        return {"success": True, "local_path": path, "motion_backend": "story_gif_line"}

    def fake_narr(story_obj, dest_dir):
        path = os.path.join(dest_dir, "narr.mp3")
        with open(path, "wb") as handle:
            handle.write(b"ID3" + b"a" * 4000)
        return path

    def fake_bed(dest_path, duration_sec):
        with open(dest_path, "wb") as handle:
            handle.write(b"aac" + b"b" * 4000)
        return dest_path

    def fake_mux(video_path, dest_path, narration_path, bed_path, sfx_path=None):
        with open(dest_path, "wb") as handle:
            handle.write(b"mp4" * 100_000)
        return {"success": True, "local_path": dest_path, "has_audio": True}

    def fake_sfx(dest_path, duration_sec, sfx_count):
        with open(dest_path, "wb") as handle:
            handle.write(b"aac" + b"s" * 4000)
        return dest_path

    def fake_gallery(**kwargs):
        return {
            "stored": True,
            "gallery_id": "film_test123",
            "quality_pct": 93,
        }

    def fake_grade(video_path, dest_path):
        with open(dest_path, "wb") as handle:
            with open(video_path, "rb") as src:
                handle.write(src.read())
        return {"success": True, "local_path": dest_path}

    def fake_concat(paths, dest_path):
        with open(dest_path, "wb") as handle:
            handle.write(b"mp4" * 120_000)
        return {"success": True, "local_path": dest_path}

    def fake_xvid(mp4_path, dest_path=None):
        path = dest_path or (mp4_path.replace(".mp4", "_xvid.avi"))
        with open(path, "wb") as handle:
            handle.write(b"avi" * 1000)
        return {"success": True, "local_path": path}

    monkeypatch.setattr(sell, "design_sellable_story", lambda *a, **k: {**story, "beats": story["beats"][:1]})
    monkeypatch.setattr(sell, "_make_hero_still", fake_still)
    monkeypatch.setattr(sell, "_render_motion_clip", fake_motion)
    monkeypatch.setattr(sell, "_synthesize_narration", fake_narr)
    monkeypatch.setattr(sell, "_build_music_bed", fake_bed)
    monkeypatch.setattr(sell, "_build_sfx_bed", fake_sfx)
    monkeypatch.setattr(sell, "_mux_soundtrack", fake_mux)
    monkeypatch.setattr(sell, "_normalize_delivery", fake_grade)
    monkeypatch.setattr(sell, "_auto_store_gallery", fake_gallery)

    import backend.services.film_canvas_service as canvas
    monkeypatch.setattr(canvas, "_ffmpeg_concat_movies", fake_concat)
    monkeypatch.setattr(canvas, "_ffmpeg_encode_xvid", fake_xvid)

    out = sell.compose_sellable_movie(
        "harbour night",
        dest_dir=str(tmp_path),
        duration_sec=6,
        timeout=30,
        allow_draft_fallback=False,
    )
    assert out["success"] is True
    assert out["pipeline"] == "sellable_v1"
    assert out["sellable"] is True
    assert out["has_audio"] is True
    assert out["motion_backends"] == ["story_gif_line"]
    assert out["quality"] == "sellable_local"
    assert out["sfx_count"] == out["fx_count"]
    assert out["fx_count"] >= 1
    assert out.get("gallery_id") == "film_test123"
    assert out.get("voice_profile") == "george"
    assert os.path.isfile(out["local_path"])


def uuid_hex():
    import uuid
    return uuid.uuid4().hex[:8]
