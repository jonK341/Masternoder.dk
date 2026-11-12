"""Unit tests for cross-venue deposit/withdraw address sync."""
from __future__ import annotations

import json

from backend.services import venue_cross_transfer_service as xfer


def test_nonkyc_deposit_falls_back_to_known_ops_address(monkeypatch):
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.venue_api_request",
        lambda *a, **k: {"success": False, "error": "boom"},
    )
    out = xfer.fetch_nonkyc_deposit("USDC-BEP20")
    assert out["success"] is True
    assert out["address"].startswith("0x2c0b")
    assert out.get("fallback") == "known_ops_address"


def test_path_template_formats_ticker():
    from backend.services import exchange_venue_api_service as vapi

    params = {"ticker": "USDC-BEP20", "extra": "1"}
    path = "/getdepositaddress/{ticker}"
    formatted = path.format(**{k: params[k] for k in params if f"{{{k}}}" in path})
    for k in list(params.keys()):
        if f"{{{k}}}" in path:
            params.pop(k, None)
    assert formatted == "/getdepositaddress/USDC-BEP20"
    assert params == {"extra": "1"}
    # Ensure config ships the deposit endpoint
    cfg = vapi.load_api_config()
    ep = ((cfg.get("venues") or {}).get("nonkyc") or {}).get("endpoints") or {}
    assert "deposit_address" in ep
    assert "{ticker}" in str(ep["deposit_address"].get("path") or "")


def test_configure_only_ready_binance_routes(monkeypatch, tmp_path):
    monkeypatch.setattr(xfer, "_REGISTRY_PATH", str(tmp_path / "reg.json"))

    def fake_bn_dep(coin, network):
        return {
            "success": True,
            "venue": "binance",
            "asset": coin,
            "network": network,
            "address": f"bn-{coin}-{network}",
            "tag": "",
        }

    def fake_nk_dep(ticker):
        addr = {
            "USDC-BEP20": "0x2c0b81D2c9bf95Fc66DBC6e2527fD22AEA91aDC8",
            "USDT-TRC20": "TS7u7kVvLVyqEdeUPbwpJJVhYCRe4pitBj",
        }.get(ticker, f"nk-{ticker}")
        return {"success": True, "venue": "nonkyc", "ticker": ticker, "address": addr, "tag": ""}

    monkeypatch.setattr(xfer, "fetch_binance_deposit", fake_bn_dep)
    monkeypatch.setattr(xfer, "fetch_nonkyc_deposit", fake_nk_dep)
    monkeypatch.setattr(
        xfer,
        "binance_whitelist_rows",
        lambda coin="USDC": (
            [
                {
                    "address": "0x2c0b81D2c9bf95Fc66DBC6e2527fD22AEA91aDC8",
                    "network": "BSC",
                    "coin": "USDC",
                    "name": "NK USDC",
                }
            ]
            if coin == "USDC"
            else []
        ),
    )

    configured = {}

    def fake_cfg(venue, targets):
        configured[venue] = targets
        return {"success": True, "configured_coins": list(targets.keys())}

    monkeypatch.setattr(
        "backend.services.exchange_payout_service.configure_venue_withdraw",
        fake_cfg,
    )

    out = xfer.sync_cross_venue_addresses()
    assert out["success"] is True
    ready_assets = {r["asset"] for r in out["ready_routes"]}
    assert "USDC" in ready_assets
    # BN→NK only wires ready (whitelisted) assets
    assert "USDC" in configured.get("binance", {})
    assert "BNB" not in configured.get("binance", {})
    # NK→BN gets Binance deposit addresses for reverse hops
    assert "USDC" in configured.get("nonkyc", {})
    assert configured["nonkyc"]["USDC"]["address"].startswith("bn-")
    assert out["configure"]["env_hint"].get("CYCLE_CIRCLES_XFER_LIVE") == "1"

    saved = json.loads((tmp_path / "reg.json").read_text())
    assert saved["success"] is True
