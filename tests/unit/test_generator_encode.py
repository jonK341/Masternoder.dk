"""Unit tests for generator encode profiles (E8)."""
from backend.services.generator_encode_service import (
    ENCODE_CRF,
    build_write_kwargs,
    is_fast_encode_profile,
    resolve_encode_profile,
)


def test_crf_ladder_values():
    assert ENCODE_CRF["fast_ai"] == 28
    assert ENCODE_CRF["premium"] == 23
    assert ENCODE_CRF["ultra"] == 18


def test_resolve_from_quality_mode():
    assert resolve_encode_profile({"quality_mode": "fast"}) == "fast_ai"
    assert resolve_encode_profile({"quality_mode": "high"}) == "premium"
    assert resolve_encode_profile({"quality_mode": "max"}) == "ultra"


def test_resolve_explicit_profile():
    assert resolve_encode_profile({"encode_profile": "ultra", "quality_mode": "fast"}) == "ultra"


def test_build_write_kwargs_includes_crf():
    kw = build_write_kwargs("job-1", "premium", add_audio=False, videos_dir="/tmp")
    params = kw["ffmpeg_params"]
    assert "-crf" in params or "cq" in params or "-global_quality" in params
    if "-crf" in params:
        idx = params.index("-crf")
        assert params[idx + 1] == "23"
    assert kw.get("preset") == "medium" or str(kw.get("codec", "")).startswith("h264_")


def test_moviepy_write_kwargs_strips_internal():
    from backend.services.generator_encode_service import build_write_kwargs, moviepy_write_kwargs
    raw = build_write_kwargs("x", "fast_ai", add_audio=False, videos_dir="/tmp")
    mp = moviepy_write_kwargs(raw)
    assert "hw_encode" not in mp or mp.get("codec") in ("libx264", "h264_nvenc", "h264_qsv", "h264_vaapi", "h264_amf")
