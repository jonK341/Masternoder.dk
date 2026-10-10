"""Ops secret resolution tests."""
import os


def test_ops_secret_prefers_your_ops_secret(monkeypatch):
    monkeypatch.setenv("YOUR_OPS_SECRET", "your-secret")
    monkeypatch.setenv("DISCORD_OPS_SECRET", "discord-secret")
    monkeypatch.setenv("ADMIN_OPS_SECRET", "admin-secret")

    from backend.services.ops_secret_service import ops_secret, ops_auth_ok

    assert ops_secret() == "your-secret"
    assert ops_auth_ok("your-secret") is True
    assert ops_auth_ok("discord-secret") is False


def test_ops_auth_localhost_without_secret(monkeypatch):
    monkeypatch.delenv("YOUR_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)

    from backend.services.ops_secret_service import ops_auth_ok

    assert ops_auth_ok(None, remote_addr="127.0.0.1") is True
    assert ops_auth_ok(None, remote_addr="8.8.8.8") is False
