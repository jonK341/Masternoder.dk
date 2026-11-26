"""Contract tests for MN2 ledger balance / USD price field preference in chrome JS."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_site_bridge_exposes_ledger_pick_helpers():
    src = _read("static/js/mn2-site-bridge.js")
    assert "function pickLedgerBalance" in src
    assert "function pickUsdPrice" in src
    assert "pickLedgerBalance: pickLedgerBalance" in src
    assert "mn2_usd_price" in src
    # Must not treat casino coins `balance` as MN2 when currency=coins
    assert "d.currency !== 'coins'" in src


def test_chrome_strips_prefer_mn2_balance_not_coins_balance():
    files = [
        "static/js/mn2-global-bar.js",
        "static/js/mn2-page-strip-init.js",
        "static/js/battlegrounds-mn2.js",
        "static/js/gallery-mn2-paywall.js",
        "static/js/chat-mn2-tips.js",
    ]
    for rel in files:
        src = _read(rel)
        assert "d.balance != null ? d.balance : d.mn2_balance" not in src, rel
        assert "pickLedgerBalance" in src or "mn2_balance" in src, rel


def test_chrome_strips_read_mn2_usd_price():
    for rel in (
        "static/js/mn2-global-bar.js",
        "static/js/mn2-page-strip-init.js",
        "static/js/battlegrounds-mn2.js",
        "static/js/chat-mn2-tips.js",
    ):
        src = _read(rel)
        assert "mn2_usd_price" in src, rel


def test_lab_hub_reads_mn2_balance():
    src = _read("static/js/lab-hub-v2.js")
    assert "mn2R.mn2_balance" in src


def test_game_and_map_copy_credit_profile_ledger():
    game = _read("game/index.html")
    assert "profile MN2 wallet" in game or "profile MN2 ledger" in game
    assert "internal game balance" not in game

    starmap = _read("starmap25/index.html")
    assert "wallet deposits and withdrawals stay separate" not in starmap
    assert "profile ledger" in starmap or "profile MN2" in starmap

    battle = _read("battle/index.html")
    assert "same ledger" in battle or "profile MN2 wallet" in battle


def test_micro_tx_balance_refresh_passes_user_id():
    src = _read("static/js/mn2-micro-tx.js")
    assert "/api/mn2/balance" in src
    assert "user_id=" in src
