"""Wallet downloads + full spork intelligence snapshot."""
from __future__ import annotations

from pathlib import Path

from flask import Flask

ROOT = Path(__file__).resolve().parents[2]


def _app():
    from backend.routes.mn2_routes import mn2_bp

    app = Flask(__name__)
    app.secret_key = "test-mn2-downloads"
    app.register_blueprint(mn2_bp)
    return app


def _release_cfg():
    import importlib.util
    import sys

    path = ROOT / "scripts" / "mn2_release_config.py"
    spec = importlib.util.spec_from_file_location("mn2_release_config", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["mn2_release_config"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_releases_from_fixture_manifests(monkeypatch):
    cfg = _release_cfg()
    import backend.routes.mn2_routes as routes

    routes._RELEASE_CACHE["at"] = 0.0
    routes._RELEASE_CACHE["payload"] = None

    daemon_manifest = {
        "files": {
            cfg.TARBALL_NAME: {"sha256": "aaa111"},
        }
    }
    qt_manifest = {
        "files": {
            "MasterNoder2-qt-linux.tar.gz": {"sha256": "bbb222"},
            "MasterNoder2-qt-win.zip": {"sha256": "ccc333"},
        }
    }
    flatpak_manifest = {
        "files": {
            "dk.masternoder.MasterNoder2.flatpak": {"sha256": "ddd444"},
        }
    }
    android_manifest = {
        "files": {
            "MasterNoder2-wallet-android.apk": {"sha256": "eee555"},
        }
    }

    def fake_fetch(url, timeout_sec=4.0):
        if url.endswith("QT_RELEASE_MANIFEST.json"):
            return qt_manifest
        if url.endswith("FLATPAK_RELEASE_MANIFEST.json"):
            return flatpak_manifest
        if url.endswith("ANDROID_RELEASE_MANIFEST.json"):
            return android_manifest
        return daemon_manifest

    monkeypatch.setattr("backend.routes.mn2_routes._fetch_release_manifest", fake_fetch)
    c = _app().test_client()
    r = c.get("/api/mn2/releases")
    assert r.status_code == 200
    data = r.get_json()
    assert data["success"] is True
    assert data["version"] == cfg.TARGET_VERSION
    assert data["manifest_unavailable"] is False
    assert "v1.2.2.0" not in str(data)
    by_id = {a["id"]: a for a in data["assets"]}
    assert by_id["daemon"]["sha256"] == "aaa111"
    assert by_id["qt-linux"]["sha256"] == "bbb222"
    assert by_id["qt-win"]["sha256"] == "ccc333"
    assert by_id["daemon-flatpak"]["sha256"] == "ddd444"
    assert by_id["android"]["sha256"] == "eee555"
    assert by_id["android"]["platform"] == "android"
    assert by_id["daemon"]["url"].startswith(cfg.RELEASE_BASE)
    assert data["platform_ui_version"] == "9.2.6.5"


def test_releases_manifest_error_keeps_target_version(monkeypatch):
    cfg = _release_cfg()
    import backend.routes.mn2_routes as routes

    routes._RELEASE_CACHE["at"] = 0.0
    routes._RELEASE_CACHE["payload"] = None

    monkeypatch.setattr("backend.routes.mn2_routes._fetch_release_manifest", lambda *a, **k: {})
    c = _app().test_client()
    data = c.get("/api/mn2/releases").get_json()
    assert data["version"] == cfg.TARGET_VERSION
    assert data["manifest_unavailable"] is True
    assert "v1.2.2.0" not in str(data)
    assert all(a["url"].startswith(cfg.RELEASE_BASE) for a in data["assets"])

def test_spork_snapshot_all_catalog_default_112_off(monkeypatch):
    from backend.services import mn2_spork_service as spork

    monkeypatch.setattr(spork, "_override_values", lambda: {})
    monkeypatch.setattr(spork, "_refresh_cache", lambda **kwargs: None)
    spork._cache["values"] = {}
    spork._cache["active"] = {}
    c = _app().test_client()
    data = c.get("/api/mn2/sporks").get_json()
    assert data["success"] is True
    assert data["count"] == len(spork.SPORK_IDS)
    by_name = {row["name"]: row for row in data["sporks"]}
    assert by_name["SPORK_112_EXCHANGE_LIVE_TRADING"]["active"] is False
    assert by_name["SPORK_112_EXCHANGE_LIVE_TRADING"]["value"] == spork.SPORK_OFF
    assert by_name["SPORK_112_EXCHANGE_LIVE_TRADING"]["source"] == "default"
    assert by_name["SPORK_114_PAYOUT_LIVE"]["value"] == spork.SPORK_OFF
    assert by_name["SPORK_5_MAX_VALUE"]["kind"] == "threshold"
    assert "summary" in by_name["SPORK_115_MAINTENANCE_MODE"]


def test_spork_snapshot_rpc_source(monkeypatch):
    from backend.services import mn2_spork_service as spork

    monkeypatch.setattr(spork, "_override_values", lambda: {})

    def fake_refresh(**kwargs):
        spork._cache["values"] = {
            "SPORK_112_EXCHANGE_LIVE_TRADING": 1_700_000_000,
        }
        spork._cache["active"] = {
            "SPORK_112_EXCHANGE_LIVE_TRADING": True,
        }
        spork._cache["at"] = 1_800_000_000

    monkeypatch.setattr(spork, "_refresh_cache", fake_refresh)
    c = _app().test_client()
    data = c.get("/api/mn2/sporks").get_json()
    row = next(r for r in data["sporks"] if r["name"] == "SPORK_112_EXCHANGE_LIVE_TRADING")
    assert row["source"] == "rpc"
    assert row["active"] is True


def test_spork_override_wins(monkeypatch):
    import json

    from backend.services import mn2_spork_service as spork

    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        json.dumps({"SPORK_115_MAINTENANCE_MODE": 1_600_000_000}),
    )
    spork.invalidate_cache()
    c = _app().test_client()
    data = c.get("/api/mn2/sporks").get_json()
    row = next(r for r in data["sporks"] if r["name"] == "SPORK_115_MAINTENANCE_MODE")
    assert row["source"] == "override"
    assert row["active"] is True


def test_sporks_route_rejects_post():
    c = _app().test_client()
    r = c.post("/api/mn2/sporks", json={"name": "SPORK_112_EXCHANGE_LIVE_TRADING", "value": 1})
    assert r.status_code in (405, 404)


def test_setup_doc_has_no_hardcoded_v122_asset_url():
    text = (ROOT / "docs" / "MN2_DAEMON_SETUP.md").read_text(encoding="utf-8")
    assert "releases/download/v1.2.2.0/" not in text
    assert "mn2_release_config" in text
