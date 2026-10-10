"""Shared environment bootstrap for local/server daemon processes."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]


def load_dotenv() -> None:
    """Load .env into os.environ (does not override already-set vars)."""
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def is_arbitrage_live() -> bool:
    load_dotenv()
    flag = os.environ.get("EXCHANGE_ARBITRAGE_LIVE", "").strip()
    return flag in ("1", "true", "yes", "on")


def is_paypal_payout_live() -> bool:
    load_dotenv()
    flag = os.environ.get("EXCHANGE_PAYOUT_PAYPAL_LIVE", "").strip()
    return flag in ("1", "true", "yes", "on")


def daemon_mode_label() -> str:
    load_dotenv()
    if is_arbitrage_live() or is_paypal_payout_live():
        return "live"
    return "paper"


def live_status() -> Dict[str, object]:
    load_dotenv()
    try:
        from backend.services.exchange_live_execution_service import live_readiness
        from backend.services.exchange_payout_service import payout_status

        ready = live_readiness()
        payout = payout_status()
    except Exception as exc:
        return {"success": False, "error": str(exc), "mode": daemon_mode_label()}
    return {
        "success": True,
        "mode": daemon_mode_label(),
        "arbitrage_live": is_arbitrage_live(),
        "paypal_payout_live": is_paypal_payout_live(),
        "live_gate": ready.get("live_gate"),
        "live_venue_count": ready.get("live_venue_count"),
        "can_trade_external": ready.get("can_trade_external"),
        "payout_mode": payout.get("mode"),
        "ready_to_sweep": payout.get("ready_to_sweep"),
        "auto_sweep": (payout.get("config") or {}).get("auto_sweep"),
    }
