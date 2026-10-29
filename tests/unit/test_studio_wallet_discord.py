"""Camgirl pictures, one MN2 wallet, NFT shelf, hosting cap, Discord audio and Spiderbot."""
import json

import pytest


def test_hosting_cap_is_500_spots():
    with open("data/mn2_masternode_config.json", encoding="utf-8") as handle:
        cfg = json.load(handle)
    assert cfg["max_hosted_nodes"] == 500
    from backend.services.mn2_masternode_hosting_service import get_paypal_config

    assert get_paypal_config()["max_hosted_nodes"] == 500


def test_nft_catalog_has_new_editions():
    from backend.services.nft_exchange_service import catalog

    skus = {row["sku"] for row in catalog()["skus"]}
    assert len(skus) >= 9
    assert "nft-spider-sigil" in skus
    assert "nft-hosting-beacon" in skus
    assert "nft-discord-wave" in skus


def test_camgirl_cards_point_at_portrait_pictures():
    with open("data/camgirls_performers.json", encoding="utf-8") as handle:
        performers = json.load(handle)["performers"]
    assert performers
    for row in performers:
        assert row["avatar_url"].endswith("/icon.webp")
        assert "portrait_pictures" in row["studio_upgrades"]
    from backend.services.camgirls_media_service import media_paths_for_performer

    pack = media_paths_for_performer("performer_nova")
    assert pack["picture_url"]
    assert "close_up" in pack["studio_upgrades"]
    assert any(url.endswith("gallery-4.webp") or url.endswith("gallery-4.svg") for url in pack["gallery"])


def test_frame_creates_one_wallet_and_coins(tmp_path, monkeypatch):
    from backend.services import mn2_wallet_service as wallet

    monkeypatch.setattr(wallet, "_addresses_path", lambda: str(tmp_path / "addr.json"))
    monkeypatch.setattr(
        wallet,
        "generate_daemon_address",
        lambda: {"success": True, "deposit_address": "MxFrame1", "address": "MxFrame1"},
    )
    monkeypatch.setattr(wallet, "_address_validity", lambda addr: True)
    monkeypatch.setattr(
        wallet,
        "get_balance",
        lambda uid: {"success": True, "mn2_balance": 2.5, "user_id": uid},
    )
    monkeypatch.setattr(wallet, "_coins_per_mn2", lambda: 100.0)

    first = wallet.frame_user_mn2_wallet("user-a")
    second = wallet.frame_user_mn2_wallet("user-a")
    assert first["success"] is True
    assert first["created"] is True
    assert first["deposit_address"] == "MxFrame1"
    assert first["wallet_count"] == 1
    assert first["mn2_coins"] == 250
    assert second["created"] is False
    assert second["deposit_address"] == "MxFrame1"
    stored = json.loads((tmp_path / "addr.json").read_text(encoding="utf-8"))
    assert stored["user-a"]["primary"] == "MxFrame1"
    assert stored["user-a"]["framed"] is True


def test_discord_audio_is_indexed_and_posted(tmp_path, monkeypatch):
    from backend.services import discord_customer_ingest_service as ingest
    from backend.services.discord_service import prepare_webhook_body

    monkeypatch.setattr(ingest, "_AUDIO_FILE", str(tmp_path / "audio.json"))
    added = ingest.record_message_audio({
        "id": "m1",
        "channel_id": "c1",
        "author": {"id": "u1", "username": "nova"},
        "attachments": [{
            "id": "a1",
            "filename": "floor.mp3",
            "content_type": "audio/mpeg",
            "url": "https://cdn.discordapp.com/attachments/floor.mp3",
        }],
    })
    assert len(added) == 1
    listed = ingest.list_discord_audio()
    assert listed["clips"][0]["filename"] == "floor.mp3"
    body = prepare_webhook_body({"content": "Drop", "audio_url": listed["clips"][0]["url"]})
    assert "audio_url" not in body
    assert "floor.mp3" in body["content"]


def test_floor_ties_portrait_nft_hosting_and_audio(monkeypatch, tmp_path):
    from backend.services import discord_customer_ingest_service as ingest
    from backend.services.studio_floor_service import performer_link, snapshot

    monkeypatch.setattr(ingest, "_AUDIO_FILE", str(tmp_path / "audio.json"))
    ingest.record_message_audio({
        "id": "m2",
        "author": {"id": "u2", "username": "nova"},
        "attachments": [{
            "id": "a2",
            "filename": "floor.ogg",
            "content_type": "audio/ogg",
            "url": "https://cdn.discordapp.com/attachments/floor.ogg",
        }],
    })
    floor = snapshot(user_id="user-a")
    assert floor["hosting_spots"] == 500
    assert floor["nft_editions"] >= 9
    assert floor["wallet"]["wallet_count"] == 0
    nova = next(row for row in floor["performers"] if row["id"] == "performer_nova")
    assert nova["picture_url"].endswith("icon.webp") or "gallery" in nova["picture_url"]
    assert nova["nft_sku"] == "nft-discord-wave"
    assert floor["audio_url"].endswith("floor.ogg")
    link = performer_link("performer_venus")
    assert link["nft_sku"] == "nft-hosting-beacon"
    assert link["hosting_spots"] == 500
    from backend.services.nft_exchange_service import catalog

    wave = next(row for row in catalog()["skus"] if row["sku"] == "nft-discord-wave")
    assert wave["floor"]["performer_id"] == "performer_nova"
    assert wave["floor"]["wallet"] == "one_mn2_wallet"


def test_spiderbot_calculated_reply_uses_live_cap(monkeypatch):
    from backend.services import discord_spiderbot_service as bot

    monkeypatch.setattr(bot, "platform_facts", lambda: {
        "hosting_spots": 500,
        "nft_editions": 9,
        "nft_names": ["Spider Sigil"],
        "audio_clips": [{"filename": "floor.mp3", "username": "nova"}],
    })

    class _Quiet:
        success = False
        content = None

    monkeypatch.setattr(
        "backend.services.llm_service.complete",
        lambda *args, **kwargs: _Quiet(),
    )
    out = bot.reply("how many hosting spots?", discord_id="42")
    assert out["source"] == "calculated"
    assert "500" in out["text"]
    assert "floor.mp3" in out["text"]


def test_discord_spider_slash_command(monkeypatch):
    from backend.routes.discord_routes import discord_bp
    from flask import Flask

    monkeypatch.delenv("DISCORD_PUBLIC_KEY", raising=False)
    monkeypatch.setattr(
        "backend.services.discord_controller_service.spiderbot_reply",
        lambda query, discord_id="": {
            "success": True,
            "text": "Hosting is capped at 500 masternode spots.",
            "source": "calculated",
        },
    )
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(discord_bp)
    client = app.test_client()
    body = {
        "type": 2,
        "data": {"name": "spider", "options": [{"name": "prompt", "value": "hosting"}]},
        "member": {"user": {"id": "99"}},
    }
    response = client.post("/api/discord/interactions", json=body)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["type"] == 4
    assert "500" in payload["data"]["content"]
