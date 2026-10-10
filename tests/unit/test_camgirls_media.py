"""Camgirls performer media packs."""
import os

from backend.services.camgirls_media_paths import pick_media_url
from backend.services.camgirls_media_service import (
    attach_media_to_row,
    media_paths_for_performer,
    resell_pack_for_performer,
)


def test_media_paths_nova():
    paths = media_paths_for_performer("performer_nova")
    assert paths["gallery"][0].startswith("/static/camgirls/media/nova/gallery-1.")
    assert paths["gallery"][0].endswith((".webp", ".svg", ".png", ".jpg"))
    assert paths["icon_url"].endswith((".webp", ".svg"))
    assert paths["logo_url"].endswith((".svg", ".webp", ".png"))
    if paths.get("media_tier") == "phase2_raster":
        assert paths["gallery"][0].endswith(".webp")


def test_pick_media_url_prefers_webp(tmp_path):
    d = str(tmp_path)
    with open(os.path.join(d, "gallery-1.svg"), "w", encoding="utf-8") as f:
        f.write("<svg/>")
    with open(os.path.join(d, "gallery-1.webp"), "wb") as f:
        f.write(b"RIFF" + b"\x00" * 20)
    url = pick_media_url(d, "/static/x", "gallery-1")
    assert url.endswith("/gallery-1.webp")


def test_attach_media_full():
    row = attach_media_to_row({"id": "performer_jade", "display_name": "Jade"}, lite=False)
    assert row["media"]["gallery"]
    assert row["resell"]["manifest_url"]
    assert row["resell"].get("shop_query")


def test_resell_pack_shape():
    pack = resell_pack_for_performer("performer_ember", "Ember Blaze")
    assert pack["display_name"] == "Ember Blaze"
    assert "assets" in pack
    assert pack["assets"]["logo"]
