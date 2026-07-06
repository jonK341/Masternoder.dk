"""Venue credentials resolve from env vars when the vault has none (NonKYC via .env/config)."""


def test_venue_credentials_env_fallback(monkeypatch):
    from backend.services import exchange_venue_api_service as v
    from backend.services import exchange_secrets_vault_service as vault

    monkeypatch.setattr(vault, "get_secret", lambda name: None)  # empty vault
    monkeypatch.setenv("NONKYC_API_KEY", "envkey")
    monkeypatch.setenv("NONKYC_API_SECRET", "envsec")

    c = v.venue_credentials("nonkyc")
    assert c["api_key"] == "envkey"
    assert c["api_secret"] == "envsec"
    assert v.venue_has_credentials("nonkyc") is True

    monkeypatch.delenv("NONKYC_API_KEY")
    monkeypatch.delenv("NONKYC_API_SECRET")
    assert v.venue_has_credentials("nonkyc") is False
