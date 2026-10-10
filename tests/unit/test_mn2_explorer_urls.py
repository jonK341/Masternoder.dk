"""Unit tests for mn2_explorer_urls (Chainz vs iquidus URL shapes)."""
from backend.services.mn2_explorer_urls import (
    explorer_address_url,
    explorer_base_url,
    explorer_block_url,
    explorer_kind,
    explorer_tx_url,
)


def test_chainz_tx_and_address_urls():
    cfg = {
        "explorer_base_url": "https://chainz.cryptoid.info/mn2/",
        "explorer_kind": "chainz",
    }
    assert explorer_kind(cfg) == "chainz"
    assert explorer_tx_url("abc123", cfg) == "https://chainz.cryptoid.info/mn2/tx.dws?txid=abc123"
    assert explorer_address_url("MxAddr", cfg) == "https://chainz.cryptoid.info/mn2/address.dws?addr=MxAddr"
    assert explorer_block_url("900000", cfg) == "https://chainz.cryptoid.info/mn2/block.dws?id=900000"


def test_iquidus_tx_and_address_urls():
    cfg = {
        "explorer_base_url": "https://camgirls.masternoder.dk/",
        "explorer_kind": "iquidus",
    }
    assert explorer_kind(cfg) == "iquidus"
    assert explorer_tx_url("deadbeef", cfg) == "https://camgirls.masternoder.dk/tx/deadbeef"
    assert explorer_address_url("MxAddr", cfg) == "https://camgirls.masternoder.dk/address/MxAddr"
    assert explorer_block_url("hash123", cfg) == "https://camgirls.masternoder.dk/block/hash123"


def test_kind_inferred_from_base_when_omitted():
    cfg = {"explorer_base_url": "https://camgirls.masternoder.dk/"}
    assert explorer_kind(cfg) == "iquidus"
    assert explorer_base_url(cfg) == "https://camgirls.masternoder.dk/"


def test_env_overrides_base_url(monkeypatch):
    monkeypatch.setenv("MN2_EXPLORER_BASE_URL", "https://selfhosted.example/")
    from backend.services.mn2_explorer_urls import explorer_base_url, load_explorer_config
    assert explorer_base_url(load_explorer_config()) == "https://selfhosted.example/"
