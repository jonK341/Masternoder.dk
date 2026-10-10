"""Phase 3 — LiveKit voice token and status."""


def test_livekit_status_shape():
    from backend.services.camgirls_livekit_service import public_status

    out = public_status()
    assert out["success"] is True
    assert out["mode"] in ("live", "stub")
    assert "configured" in out


def test_livekit_live_token_when_configured(monkeypatch):
    import backend.services.camgirls_livekit_service as lk_mod
    from backend.services.camgirls_livekit_service import issue_voice_token, is_configured

    class _FakeJwt:
        @staticmethod
        def encode(payload, secret, algorithm="HS256"):
            return "fake.jwt.token"

    monkeypatch.setattr(lk_mod, "pyjwt", _FakeJwt)
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "API_TEST_KEY")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret_test_value_32chars_min_ok")
    assert is_configured() is True

    out = issue_voice_token("fan_phase3", "performer_nova", require_unlock=False)
    assert out.get("success") is True
    assert out.get("mode") == "live"
    assert out.get("token")
    assert out.get("livekit_url") == "wss://example.livekit.cloud"
    assert out.get("room", "").startswith("cam_")


def test_livekit_unlock_gate(monkeypatch):
    from backend.services.camgirls_livekit_service import issue_voice_token

    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    out = issue_voice_token("nobody_unlocked", "performer_nova", require_unlock=True)
    assert out.get("success") is False
    assert out.get("error") in ("unlock_required", "unlock_check_failed")
