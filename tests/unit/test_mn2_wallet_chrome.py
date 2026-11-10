"""Source-contract tests for lag-free MN2 wallet chrome."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_global_bar_prefers_mn2_usd_price_and_fast_read():
    src = _read("static", "js", "mn2-global-bar.js")
    assert "loadFastBalance" in src
    assert "mn2_usd_price" in src
    assert src.index("mn2_usd_price") < src.index("price_usd")
    assert src.index("price_usd") < src.index("d.usd")
    assert "90000" in src
    assert "EventSource" not in src
    assert "loadBalance()" not in src or "loadFastBalance" in src
    # Placeholder vs zero are separate
    assert "mn2_balance == null" in src
    assert "fmt(bal)" in src


def test_page_strip_uses_fast_read_and_90s_refresh():
    src = _read("static", "js", "mn2-page-strip-init.js")
    assert "loadFastBalance" in src
    assert "mn2_usd_price" in src
    assert "90000" in src
    assert "EventSource" not in src
    bridge = _read("static", "js", "mn2-site-bridge.js")
    assert "/api/mn2/balance/onchain" in bridge
    assert "loadOnchainBalance" in bridge


def test_toolbar_creates_mn2_wallet_chip():
    nav = _read("static", "js", "navigation-toolbar.js")
    assert "navToolbarMn2Wallet" in nav
    assert "loadFastBalance" in nav
    assert "/profile?tab=wallet&wallet=deposit" in nav


def test_profile_wallet_ensures_deposit_and_honors_query():
    src = _read("static", "js", "profile-mn2-wallet.js")
    assert "loadFastBalance" in src or "balance/onchain" in src or "balance/fast" in src
    assert "WALLET_TAB_ALLOW" in src
    assert "selectWalletTab" in src
    # On-chain mode: always request a deposit address so network deposits can land.
    assert "requestDepositAddress" in src
    assert src.rindex("requestDepositAddress") > src.index("startDetail")


def test_profile_scroll_maps_use_mn2_wallet():
    hub = _read("static", "js", "profile-hub.js")
    bar = _read("static", "js", "profile-hub-bar.js")
    assert "wallet: 'mn2-wallet'" in hub or "mn2-wallet" in hub
    assert "wallet: 'mn2-wallet'" in bar


def test_activity_stream_unchanged_for_balance():
    src = _read("static", "js", "mn2-activity-stream.js")
    assert "/api/activity/stream" in src
    assert "mn2_balance" not in src


def test_wallets_portal_links_mn2_wallet():
    html = _read("wallets", "index.html")
    assert "/profile#mn2-wallet" in html or "#mn2-wallet" in html
    assert "/api/mn2/balance/fast" in html or "loadFastBalance" in html
    assert "9.2.6.5" in html
