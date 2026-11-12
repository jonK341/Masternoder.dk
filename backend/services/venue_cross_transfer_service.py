"""Cross-venue deposit/withdraw address book for Binance ↔ NonKYC circle transfers.

Builds a registry of deposit addresses, checks Binance withdraw whitelist coverage,
and configures ``payout_config.withdraw_targets`` so fund circles / cross-trades can
move quote (USDC BSC, USDT TRC20) and priority coins when addresses are ready.

Note: Binance cannot add whitelist entries via API — missing rows must be added in
the Binance UI (and NonKYC withdraw whitelist in their UI for reverse legs).
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_REGISTRY_PATH = os.path.join(ex._DATA_DIR, "cross_venue_addresses.json")

# Preferred networks for low-fee cross-venue hops.
PREFERRED_ROUTES: List[Dict[str, str]] = [
    {"asset": "USDC", "from": "binance", "to": "nonkyc", "network": "BSC", "nk_ticker": "USDC-BEP20"},
    {"asset": "USDT", "from": "binance", "to": "nonkyc", "network": "TRX", "nk_ticker": "USDT-TRC20"},
    {"asset": "BNB", "from": "binance", "to": "nonkyc", "network": "BSC", "nk_ticker": "BNB"},
    {"asset": "LINK", "from": "binance", "to": "nonkyc", "network": "BSC", "nk_ticker": "LINK"},
    {"asset": "XRP", "from": "binance", "to": "nonkyc", "network": "XRP", "nk_ticker": "XRP"},
    {"asset": "ADA", "from": "binance", "to": "nonkyc", "network": "ADA", "nk_ticker": "ADA"},
    {"asset": "ALGO", "from": "binance", "to": "nonkyc", "network": "ALGO", "nk_ticker": "ALGO"},
    # Reverse quote hop (NonKYC → Binance)
    {"asset": "USDC", "from": "nonkyc", "to": "binance", "network": "BSC", "nk_ticker": "USDC-BEP20"},
    {"asset": "USDT", "from": "nonkyc", "to": "binance", "network": "TRX", "nk_ticker": "USDT-TRC20"},
]

# Known NonKYC deposits already used in ops (fallback if API fails).
_KNOWN_NK_DEPOSITS = {
    "USDC-BEP20": "0x2c0b81D2c9bf95Fc66DBC6e2527fD22AEA91aDC8",
    "USDT-TRC20": "TS7u7kVvLVyqEdeUPbwpJJVhYCRe4pitBj",
}


def _iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _mask(addr: str) -> str:
    a = str(addr or "")
    if len(a) <= 12:
        return a
    return f"{a[:8]}…{a[-6:]}"


def fetch_binance_deposit(coin: str, network: str) -> Dict[str, Any]:
    from backend.services.exchange_binance_withdraw_service import _signed_sapi_request

    res = _signed_sapi_request(
        "GET",
        "/sapi/v1/capital/deposit/address",
        {"coin": str(coin).upper(), "network": str(network).upper()},
        dry_run=False,
        skip_live_gate=True,
    )
    body = res.get("body") if isinstance(res.get("body"), dict) else {}
    return {
        "success": bool(res.get("success") and body.get("address")),
        "venue": "binance",
        "asset": str(coin).upper(),
        "network": str(network).upper(),
        "address": str(body.get("address") or ""),
        "tag": body.get("tag") or body.get("memo") or "",
        "raw_error": res.get("binance_msg") or res.get("error"),
    }


def fetch_nonkyc_deposit(ticker: str) -> Dict[str, Any]:
    from backend.services import exchange_venue_api_service as vapi

    tick = str(ticker or "").strip()
    res = vapi.venue_api_request("nonkyc", "deposit_address", {"ticker": tick}, dry_run=False)
    body = res.get("body")
    addr = ""
    tag = ""
    if isinstance(body, str):
        raw = body.strip()
        if raw.startswith("{"):
            try:
                body = json.loads(raw)
            except Exception:
                addr = raw if raw.startswith(("0x", "T")) else ""
        elif raw.startswith(("0x", "T")):
            addr = raw
    if isinstance(body, dict):
        addr = str(body.get("address") or body.get("depositAddress") or body.get("addr") or "")
        tag = str(
            body.get("paymentid")
            or body.get("paymentId")
            or body.get("memo")
            or body.get("tag")
            or ""
        )
    if not addr and tick in _KNOWN_NK_DEPOSITS:
        addr = _KNOWN_NK_DEPOSITS[tick]
        res = {**res, "success": True, "fallback": "known_ops_address"}
    return {
        "success": bool(addr),
        "venue": "nonkyc",
        "ticker": tick,
        "address": addr,
        "tag": tag,
        "raw_error": res.get("error") or (None if addr else "no_address"),
        "http_status": res.get("status_code"),
        "fallback": res.get("fallback"),
    }


def binance_whitelist_rows(coin: str = "USDC") -> List[Dict[str, Any]]:
    from backend.services.exchange_binance_withdraw_service import get_withdraw_address_list

    res = get_withdraw_address_list(coin, dry_run=False, skip_live_gate=True)
    return list(res.get("addresses") or []) if res.get("success") else []


def is_binance_whitelisted(address: str, network: str, *, coin: str = "USDC") -> bool:
    from backend.services.exchange_binance_withdraw_service import (
        _address_whitelisted,
        binance_network_code,
    )

    rows = binance_whitelist_rows(coin)
    if _address_whitelisted(address, binance_network_code(network), rows):
        return True
    # Some accounts return a coin-agnostic list; also probe USDC/USDT lists.
    for alt in ("USDC", "USDT"):
        if alt == str(coin).upper():
            continue
        if _address_whitelisted(address, binance_network_code(network), binance_whitelist_rows(alt)):
            return True
    return False


def build_address_registry(*, persist: bool = True) -> Dict[str, Any]:
    """Fetch deposits both ways and annotate Binance whitelist status for BN→NK hops."""
    deposits: Dict[str, Any] = {"binance": {}, "nonkyc": {}}
    routes: List[Dict[str, Any]] = []

    bn_pairs = sorted({(r["asset"], r["network"]) for r in PREFERRED_ROUTES})
    for asset, network in bn_pairs:
        dep = fetch_binance_deposit(asset, network)
        deposits["binance"][f"{asset}:{network}"] = {
            **dep,
            "address_masked": _mask(dep.get("address") or ""),
        }

    nk_tickers = sorted({r["nk_ticker"] for r in PREFERRED_ROUTES})
    for tick in nk_tickers:
        dep = fetch_nonkyc_deposit(tick)
        deposits["nonkyc"][tick] = {
            **dep,
            "address_masked": _mask(dep.get("address") or ""),
        }

    whitelist_usdc = binance_whitelist_rows("USDC")
    whitelist_usdt = binance_whitelist_rows("USDT")
    whitelist_summary = []
    for rows in (whitelist_usdc, whitelist_usdt):
        for r in rows:
            whitelist_summary.append(
                {
                    "address_masked": _mask(str(r.get("address") or "")),
                    "network": r.get("network"),
                    "coin": r.get("coin"),
                    "name": r.get("name"),
                }
            )

    for route in PREFERRED_ROUTES:
        asset, network = route["asset"], route["network"]
        src, dst = route["from"], route["to"]
        row: Dict[str, Any] = {
            **route,
            "ready": False,
            "blockers": [],
            "withdraw_from": src,
            "deposit_to": dst,
        }
        if src == "binance" and dst == "nonkyc":
            nk = deposits["nonkyc"].get(route["nk_ticker"]) or {}
            addr = str(nk.get("address") or "")
            row["deposit_address_masked"] = _mask(addr)
            row["deposit_address"] = addr
            row["deposit_tag"] = nk.get("tag") or ""
            if not addr:
                row["blockers"].append("missing_nonkyc_deposit")
            elif not is_binance_whitelisted(addr, network, coin=asset):
                row["blockers"].append("binance_whitelist_missing")
            if not row["blockers"]:
                row["ready"] = True
        elif src == "nonkyc" and dst == "binance":
            bn = deposits["binance"].get(f"{asset}:{network}") or {}
            addr = str(bn.get("address") or "")
            row["deposit_address_masked"] = _mask(addr)
            row["deposit_address"] = addr
            row["deposit_tag"] = bn.get("tag") or ""
            if not addr:
                row["blockers"].append("missing_binance_deposit")
            else:
                # NonKYC withdraw whitelist cannot be verified via API.
                row["blockers"].append("confirm_nonkyc_withdraw_whitelist_in_ui")
            row["ready_if_nk_whitelisted"] = bool(addr)
        routes.append(row)

    out = {
        "success": True,
        "updated_at": _iso(),
        "deposits": deposits,
        "binance_whitelist": whitelist_summary,
        "routes": routes,
        "ready_routes": [r for r in routes if r.get("ready")],
        "needs_binance_ui_whitelist": [
            r for r in routes if "binance_whitelist_missing" in (r.get("blockers") or [])
        ],
        "needs_nonkyc_ui_whitelist": [
            r for r in routes if "confirm_nonkyc_withdraw_whitelist_in_ui" in (r.get("blockers") or [])
        ],
    }
    if persist:
        os.makedirs(os.path.dirname(_REGISTRY_PATH), exist_ok=True)
        # strip full addresses from disk? keep them — needed for withdraw config; file is server-local
        with open(_REGISTRY_PATH, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, default=str)
            fh.write("\n")
    return out


def configure_withdraw_targets_from_registry(registry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Write ready BN→NK and BN-bound reverse targets into payout withdraw_targets."""
    from backend.services.exchange_payout_service import configure_venue_withdraw

    reg = registry or build_address_registry(persist=True)
    bn_targets: Dict[str, Any] = {}
    nk_targets: Dict[str, Any] = {}

    for route in reg.get("routes") or []:
        asset = route["asset"]
        if route["from"] == "binance" and route.get("ready") and route.get("deposit_address"):
            # Only wire BN→NK when address is on Binance whitelist (else withdraw fails).
            bn_targets[asset] = {
                "address": route["deposit_address"],
                "network": route["network"],
                "ticker": route.get("nk_ticker"),
            }
        if route["from"] == "nonkyc" and route.get("deposit_address"):
            # NK→BN: address is Binance deposit; operator must whitelist in NonKYC UI.
            nk_targets[asset] = {
                "address": route["deposit_address"],
                "network": route["network"],
                "ticker": route.get("nk_ticker"),
                "paymentId": route.get("deposit_tag") or None,
            }

    results = {}
    if bn_targets:
        results["binance"] = configure_venue_withdraw("binance", bn_targets)
    if nk_targets:
        results["nonkyc"] = configure_venue_withdraw("nonkyc", nk_targets)

    # Export env-friendly USDC BSC for fund circles
    usdc_route = next(
        (
            r for r in (reg.get("routes") or [])
            if r.get("asset") == "USDC" and r.get("from") == "binance" and r.get("network") == "BSC"
        ),
        None,
    )
    env_hint = {}
    if usdc_route and usdc_route.get("deposit_address"):
        env_hint["NONKYC_USDC_BEP20_DEPOSIT"] = usdc_route["deposit_address"]
        env_hint["CYCLE_CIRCLES_XFER_LIVE"] = "1" if usdc_route.get("ready") else "0"

    return {
        "success": True,
        "configured": results,
        "env_hint": env_hint,
        "ready_route_count": len(reg.get("ready_routes") or []),
        "needs_binance_ui": [
            {"asset": r["asset"], "network": r["network"], "address_masked": r.get("deposit_address_masked")}
            for r in (reg.get("needs_binance_ui_whitelist") or [])
        ],
        "needs_nonkyc_ui": [
            {"asset": r["asset"], "network": r["network"], "address_masked": r.get("deposit_address_masked")}
            for r in (reg.get("needs_nonkyc_ui_whitelist") or [])
        ],
    }


def sync_cross_venue_addresses() -> Dict[str, Any]:
    """Full sync: registry + payout withdraw targets + readiness summary."""
    reg = build_address_registry(persist=True)
    cfg = configure_withdraw_targets_from_registry(reg)
    return {
        "success": True,
        "updated_at": reg.get("updated_at"),
        "ready_routes": [
            {
                "asset": r["asset"],
                "network": r["network"],
                "from": r["from"],
                "to": r["to"],
                "address_masked": r.get("deposit_address_masked"),
            }
            for r in (reg.get("ready_routes") or [])
        ],
        "configure": cfg,
        "binance_whitelist_count": len(reg.get("binance_whitelist") or []),
    }
