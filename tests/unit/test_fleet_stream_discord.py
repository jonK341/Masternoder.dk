"""Fleet stream Discord fanout."""
from unittest.mock import patch


def test_build_discord_payload_has_gprs_and_monitor():
    from backend.services.fleet_stream_discord_service import build_discord_live_payload

    payload = build_discord_live_payload()
    assert payload.get("embeds")
    embed = payload["embeds"][0]
    assert "monitor" in embed.get("description", "").lower() or any(
        "monitor" in (f.get("name") or "").lower() for f in embed.get("fields") or []
    )
    names = [f.get("name") for f in embed.get("fields") or []]
    assert "GPRS live" in names or "GPRS cells" in names


def test_publish_dry_run():
    from backend.services.fleet_stream_discord_service import publish_fleet_live_to_discord

    with patch("backend.services.discord_service.post_message") as post:
        r = publish_fleet_live_to_discord(dry_run=True)
        post.assert_not_called()
    assert r.get("dry_run") is True
    assert r.get("payload", {}).get("embeds")


def test_gprs_tick_dry_run():
    from backend.services.fleet_stream_discord_service import publish_gprs_tick_to_discord

    r = publish_gprs_tick_to_discord(dry_run=True)
    assert r.get("success") is True
    if r.get("payload"):
        assert "GPRS" in r["payload"]["embeds"][0].get("title", "")
