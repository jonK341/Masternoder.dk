"""Plan 001 BM-U2 — block trophy media generation."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_ensure_block_media_skips_when_manifest_has_files():
    from backend.services import block_trophy_media_service as btm

    with tempfile.TemporaryDirectory() as tmp:
        img_dir = os.path.join(tmp, "static", "img", "trophies")
        os.makedirs(img_dir, exist_ok=True)
        with open(os.path.join(img_dir, "block-100.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        with open(os.path.join(img_dir, "block-100.gif"), "wb") as f:
            f.write(b"GIF89a")

        with patch.object(btm, "_BASE", tmp):
            with patch("backend.services.shop_media_service.load_manifest") as load_m:
                with patch("backend.services.shop_media_service.save_manifest"):
                    load_m.return_value = {
                        "block-100": {
                            "image_url": "/static/img/trophies/block-100.png",
                            "gif_url": "/static/img/trophies/block-100.gif",
                        }
                    }
                    result = btm.ensure_block_media(100)

        assert result["success"] is True
        assert result.get("skipped") is True


def test_ensure_block_media_unavailable_without_generators():
    from backend.services import block_trophy_media_service as btm

    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(btm, "_BASE", tmp):
            with patch.object(btm, "_ffmpeg", return_value=None):
                with patch.object(btm, "_generate_smiley_gif_pil", return_value=False):
                    with patch("backend.services.shop_media_service.load_manifest", return_value={}):
                        with patch("backend.services.shop_media_service.save_manifest"):
                            result = btm.ensure_block_media(9999)

    assert result["success"] is False
    assert result["error"] == "media_generation_unavailable"


def test_generate_media_route():
    from flask import Flask
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)

    with app.test_client() as client:
        with patch(
            "backend.services.block_trophy_media_service.ensure_block_media",
            return_value={"success": True, "item_id": "block-42", "height": 42},
        ):
            resp = client.post("/api/shop/block-mint/generate-media", json={"height": 42})

    assert resp.status_code == 200
    assert (resp.get_json() or {}).get("success") is True
