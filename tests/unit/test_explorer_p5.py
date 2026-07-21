"""P5 test suite upgrades (items 204–210)."""
import json
import os
import re

import pytest

from flask import Flask

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

OVERVIEW_TOP_KEYS = frozenset({
    "success",
    "block_height",
    "mn2_usd_price",
    "staking_weight",
    "masternode_count",
    "difficulty",
    "circulating_supply",
    "source",
    "daemon",
    "connections",
    "mempool_tx",
    "pool_total_staked",
    "pool_apr_percent",
    "explorer_base_url",
    "explorer_kind",
    "hub_v2_enabled",
})

HUB_TILE_IDS = (
    "t-price", "t-height", "t-diff", "t-mn", "t-weight", "t-supply",
    "t-conn", "t-mempool", "t-ver", "t-sync", "t-pool", "t-poolapr",
)


def _read(*parts):
    path = os.path.join(ROOT, *parts)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _staking_app():
    from backend.routes.mn2_staking_routes import mn2_staking_bp
    app = Flask(__name__)
    app.register_blueprint(mn2_staking_bp)
    return app


def _sample_overview():
    return {
        "block_height": 12345,
        "mn2_usd_price": 0.0123,
        "staking_weight": 1e6,
        "network_hashps": 1e6,
        "masternode_count": 42,
        "difficulty": 123.45,
        "circulating_supply": 9.75e7,
        "source": {"block_height": "rpc", "mn2_usd_price": "chainz"},
        "daemon": {"connections": 8, "mempool_tx": 2, "reachable": True},
        "connections": 8,
        "mempool_tx": 2,
    }


# 204 — integration: full overview JSON schema
def test_p5_204_overview_json_schema(monkeypatch):
    monkeypatch.setattr(
        "backend.services.mn2_chainz.network_overview",
        lambda: _sample_overview(),
    )
    monkeypatch.setattr("backend.services.mn2_staking_service.total_staked", lambda: 1000.0)
    monkeypatch.setattr("backend.services.mn2_staking_service.dynamic_apr", lambda: 12.5)
    monkeypatch.setenv("MN2_EXPLORER_KIND", "iquidus")
    monkeypatch.setenv("MN2_EXPLORER_BASE_URL", "https://explorer.example/")

    r = _staking_app().test_client().get("/api/mn2/network-overview")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    missing = OVERVIEW_TOP_KEYS - set(data.keys())
    assert not missing, f"missing keys: {sorted(missing)}"
    assert isinstance(data["source"], dict)
    assert data["pool_total_staked"] == 1000.0
    assert data["pool_apr_percent"] == 12.5
    assert data["explorer_kind"] == "iquidus"
    assert "ETag" in r.headers
    assert "max-age=30" in r.headers.get("Cache-Control", "")


# 205 — browser: hub tiles render (HTML shell + JS bindings)
def test_p5_205_hub_tiles_in_page_and_js():
    html = _read("explorer", "index.html")
    js = _read("static", "js", "mn2-explorer-overview.js")
    for tile_id in HUB_TILE_IDS:
        assert f'id="{tile_id}"' in html
        assert f"q('{tile_id}')" in js or f'q("{tile_id}")' in js
    assert 'class="ex-tile"' in html
    assert "t-price" in js and "t-height" in js


# 206 — browser: search routing
def test_p5_206_search_routing_js():
    js = _read("static", "js", "mn2-explorer-overview.js")
    html = _read("explorer", "index.html")
    assert 'id="ex-q"' in html
    assert 'id="ex-search"' in html or 'ex-search' in html
    assert "/api/mn2/explorer/search" in js
    assert "window.location.href = res.d.path" in js
    assert "/explorer/tx/" in js
    assert "/explorer/block/" in js
    assert "/explorer/address/" in js


# 207 — contract test against live eiquidus ext (skipped unless URL set)
@pytest.mark.integration
def test_p5_207_eiquidus_ext_contract_live():
    import urllib.error
    import urllib.request

    base = (
        os.environ.get("MN2_EXPLORER_LOCAL_API_URL")
        or os.environ.get("EQUIDUS_LIVE_EXT_URL")
        or ""
    ).rstrip("/")
    if not base:
        pytest.skip("Set MN2_EXPLORER_LOCAL_API_URL or EQUIDUS_LIVE_EXT_URL for live contract test")

    for path in ("/ext/getmoneysupply", "/ext/getblockcount"):
        url = base + path
        try:
            with urllib.request.urlopen(url, timeout=12) as resp:
                body = resp.read().decode("utf-8", errors="replace").strip()
        except urllib.error.URLError as exc:
            pytest.fail(f"eiquidus unreachable at {url}: {exc}")

        if path.endswith("getmoneysupply"):
            try:
                val = float(body)
            except ValueError:
                data = json.loads(body)
                val = float(data.get("supply") or data.get("result") or data)
            assert val > 0
        else:
            assert body
            num = int(body) if body.isdigit() else int(json.loads(body))
            assert num >= 0


# 208 — regression: ACTIVE masternode pill uses green .pill.on
def test_p5_208_active_masternode_pill_green():
    js = _read("static", "js", "mn2-explorer-overview.js")
    css = _read("static", "css", "mn2-crypto-hub.css")
    assert "isMnActive" in js
    assert "'ACTIVE'" in js or '"ACTIVE"' in js
    assert "pill ' + (on ? 'on' : 'off')" in js or 'pill \' + (on ? \'on\' : \'off\')' in js
    assert ".pill.on" in css
    assert "#00ff88" in css or "00ff88" in css


# 209 — regression: zero price shows em-dash
def test_p5_209_zero_price_shows_em_dash(monkeypatch):
    js = _read("static", "js", "mn2-explorer-overview.js")
    assert "price > 0" in js
    assert "'—'" in js or '"—"' in js
    monkeypatch.setattr(
        "backend.services.mn2_chainz.chainz_ticker_usd_with_updated",
        lambda: {"price": 0.0, "last_updated_iso": "x"},
    )
    from backend.services import mn2_chainz
    assert mn2_chainz.chainz_ticker_usd() is None


# 210 — CI job exists (workflow file)
def test_p5_210_ci_workflow_defined():
    wf = _read(".github", "workflows", "explorer-tests.yml")
    assert "pull_request" in wf
    assert "test_explorer_p" in wf or "explorer" in wf
    assert "pytest" in wf
