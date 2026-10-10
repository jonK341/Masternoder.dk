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


def test_explicit_live_read_bypasses_gate(monkeypatch):
    """dry_run=False (explicit live, e.g. balance read) must NOT be blocked by the arb gate;
    dry_run=None must still be gated."""
    from backend.services import exchange_venue_api_service as v
    from backend.services import exchange_binance_time_service as t
    monkeypatch.setattr(v, "live_gate_ok", lambda rotation=False: False)  # arb gate OFF
    monkeypatch.setattr(v, "venue_credentials",
                        lambda vid: {"api_key": "k", "api_secret": "s", "passphrase": None})
    monkeypatch.setattr(t, "binance_timestamp_ms", lambda: 1)
    monkeypatch.setattr(t, "recv_window_ms", lambda: 5000)
    monkeypatch.setattr(v, "_http_request",
                        lambda *a, **k: {"success": True, "status_code": 200, "body": {"balances": []}})

    forced = v.venue_api_request("binance", "account", {}, dry_run=False)
    assert forced.get("error") != "live_gated"   # explicit live bypasses the gate
    assert forced.get("success") is True

    gated = v.venue_api_request("binance", "account", {}, dry_run=None)
    assert gated.get("simulated") is True         # default (gate off) falls back to paper, not live
