import json
from pathlib import Path


def test_registry_lists_seeded_exchanges():
    from backend.services.exchange_registry_service import list_exchanges, ladder_venues, known_parsers

    rows = list_exchanges()
    assert len(rows) >= 10
    ids = {r["id"] for r in rows}
    assert "binance" in ids and "nonkyc" in ids
    assert "binance" in ladder_venues() and "nonkyc" in ladder_venues()
    assert "binance" in known_parsers()


def test_add_exchange_reuses_parser(tmp_path, monkeypatch):
    from backend.services import exchange_registry_service as reg

    registry = tmp_path / "exchanges_registry.json"
    connectors = tmp_path / "exchange_connectors_config.json"
    venue_api = tmp_path / "exchange_venue_api_config.json"
    registry.write_text(json.dumps({
        "version": 1,
        "exchanges": [],
        "recommended_services": [],
        "control": {"host": "127.0.0.1", "port": 8787},
    }), encoding="utf-8")
    connectors.write_text(json.dumps({"venues": []}), encoding="utf-8")
    venue_api.write_text(json.dumps({"venues": {}}), encoding="utf-8")
    monkeypatch.setattr(reg, "_REGISTRY_PATH", str(registry))
    monkeypatch.setattr(reg, "_CONNECTORS_PATH", str(connectors))
    monkeypatch.setattr(reg, "_VENUE_API_PATH", str(venue_api))

    bad = reg.add_exchange({
        "id": "acme",
        "ticker_url": "https://example.com/t?s={pair}",
        "pair_template": "{base}_{quote}",
        "quote": "USDT",
        "parser": "not_a_parser",
    })
    assert bad["success"] is False

    out = reg.add_exchange({
        "id": "acme",
        "name": "AcmeX",
        "ticker_url": "https://api.acme.test/ticker?symbol={pair}",
        "pair_template": "{base}{quote}",
        "quote": "USDT",
        "parser": "binance",
        "enabled": True,
        "ladder": False,
        "fee_taker_bps": 12,
    })
    assert out["success"] is True
    assert out["exchange"]["parser"] == "binance"
    assert any(r["id"] == "acme" for r in reg.list_exchanges())
    conn = json.loads(connectors.read_text(encoding="utf-8"))
    assert any(v.get("id") == "acme" and v.get("parser") == "binance" for v in conn["venues"])

    toggled = reg.set_exchange_enabled("acme", False)
    assert toggled["success"] is True
    assert reg.get_exchange("acme")["enabled"] is False


def test_fetch_ticker_honors_parser_alias(monkeypatch):
    from backend.services import external_exchange_connector_service as conn

    monkeypatch.setattr(conn, "_venue_map", lambda: {
        "acme": {
            "id": "acme",
            "quote": "USDT",
            "pair_template": "{base}{quote}",
            "ticker_url": "https://example.test/{pair}",
            "parser": "binance",
        }
    })

    class _Resp:
        status_code = 200

        def json(self):
            return {"bidPrice": "1.2", "askPrice": "1.3"}

    class _Req:
        @staticmethod
        def get(*_a, **_k):
            return _Resp()

    monkeypatch.setitem(__import__("sys").modules, "requests", _Req)
    # force_ipv4 may import; ignore failures inside fetch
    out = conn.fetch_ticker("acme", "XRP", timeout=1.0)
    assert out is not None
    assert out["bid"] == 1.2 and out["ask"] == 1.3


def test_control_panel_health_endpoint():
    from profit_daemon_jon.control_panel import start_background
    import urllib.request
    import time

    started = start_background(open_browser=False)
    assert started.get("success") is True
    url = started["url"].rstrip("/") + "/api/health"
    # Give the thread a moment
    deadline = time.time() + 3
    last_err = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                body = json.loads(resp.read().decode())
                assert body.get("status") == "healthy"
                return
        except Exception as exc:
            last_err = exc
            time.sleep(0.1)
    raise AssertionError(f"control health failed: {last_err}")


def test_registry_file_exists_in_repo():
    root = Path(__file__).resolve().parents[2]
    path = root / "data" / "exchanges_registry.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data.get("exchanges") or []) >= 10
    assert any(s.get("id") == "local_control" for s in data.get("recommended_services") or [])
