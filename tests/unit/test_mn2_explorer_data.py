"""MN2 explorer data service tests."""
import pytest


def test_recent_blocks_mocked(monkeypatch):
    from backend.services import mn2_explorer_data as ex

    ex._CACHE.clear()

    class _Rpc:
        @staticmethod
        def getblockcount(timeout_sec=5):
            return {"result": 100}

        @staticmethod
        def getblockhash(h):
            return {"result": f"hash{h}"}

        def _call(self, method, params):
            if method == "getblock":
                return {
                    "result": {
                        "height": params[0] if isinstance(params[0], int) else 100,
                        "hash": params[0],
                        "time": 1,
                        "tx": ["a"],
                        "size": 512,
                    }
                }
            return {"error": "unsupported"}

    monkeypatch.setattr("backend.services.mn2_rpc_client.getblockcount", _Rpc.getblockcount)
    monkeypatch.setattr("backend.services.mn2_rpc_client.getblockhash", _Rpc.getblockhash)
    monkeypatch.setattr("backend.services.mn2_rpc_client._call", _Rpc()._call)

    rows = ex.recent_blocks(limit=2)
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert rows[0].get("height") is not None


def test_masternodes_empty_on_rpc_error(monkeypatch):
    from backend.services import mn2_explorer_data as ex

    ex._CACHE.clear()
    monkeypatch.setattr(
        "backend.services.mn2_rpc_client.listmasternodes",
        lambda timeout_sec=None: {"error": "down"},
    )
    out = ex.masternodes(limit=5)
    assert isinstance(out, dict)
    assert "list" in out
    assert out.get("rpc_error") == "down"


def test_masternodes_fresh_error_invalidates_cache(monkeypatch):
    from backend.services import mn2_explorer_data as ex

    ex._CACHE.clear()
    ex._CACHE["mn_5"] = {
        "value": {"total": 9, "enabled": 5, "list": [{"rank": 1}]},
        "ts": ex.time.time(),
    }
    monkeypatch.setattr(
        "backend.services.mn2_rpc_client.listmasternodes",
        lambda timeout_sec=None: {"error": "down"},
    )
    out = ex.masternodes(limit=5, fresh=True)
    assert out.get("rpc_error") == "down"
    assert "mn_5" not in ex._CACHE


def test_network_masternodes_passes_fresh(monkeypatch):
    from backend.services import mn2_masternode_service as mn

    seen = {}

    def fake_masternodes(limit=50, *, fresh=False):
        seen["fresh"] = fresh
        seen["limit"] = limit
        return {"total": 1, "enabled": 1, "list": []}

    monkeypatch.setattr("backend.services.mn2_explorer_data.masternodes", fake_masternodes)
    out = mn.network_masternodes(limit=25, fresh=True)
    assert out.get("success") is True
    assert seen == {"fresh": True, "limit": 25}
