"""Exchange-wallet mega prototype — X-03 / X-08 / X-40 / X-46 (on-chain capable).

Respects SPORK_112 / SPORK_114 default-off. On-chain deposit + MN2 withdraw paths
are real custody rails; external venue live trading stays gated.

Knob walkthrough (50 × 12) lives in ``exchange_wallet_x_knobs``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.services.exchange_wallet_x_knobs import (
    ALL_KNOBS,
    MEGA_MIN_KNOBS,
    knobs_for,
    walkthrough,
)

PRIORITY_IDS = ("X-03", "X-08", "X-40", "X-46")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def installed_knobs(enrichment_id: str) -> Dict[str, Any]:
    """Levels for an enrichment: mega-min knobs at 1, others at 0 until leveled up."""
    detail = knobs_for(enrichment_id)
    if not detail.get("success"):
        return {
            "id": enrichment_id,
            "success": False,
            "error": detail.get("error"),
            "knobs": {k: 0 for k in ALL_KNOBS},
            "installed_min": list(MEGA_MIN_KNOBS),
            "installed_count": 0,
        }
    meta = detail["enrichment"]
    levels = {row["knob"]: int(row.get("level") or 0) for row in detail.get("knobs") or []}
    return {
        "id": meta["id"],
        "tech": meta.get("tech"),
        "title": meta.get("title"),
        "pillar": meta.get("pillar"),
        "surfaces": list(meta.get("surfaces") or []),
        "priority": bool(meta.get("priority")),
        "knobs": levels,
        "knob_walkthrough": detail.get("knobs") or [],
        "installed_min": list(MEGA_MIN_KNOBS),
        "installed_count": sum(1 for v in levels.values() if v > 0),
        "success": True,
    }


def priority_install_set() -> Dict[str, Any]:
    return {
        "success": True,
        "confirmed": True,
        "target": "v32.6.6.0",
        "mode": "on_chain_trading_prototype",
        "enrichments": [installed_knobs(k) for k in PRIORITY_IDS],
        "knob_glossary_count": len(ALL_KNOBS),
        "mega_min_knobs": list(MEGA_MIN_KNOBS),
        "live_gates_default_off": ["SPORK_112_EXCHANGE_LIVE_TRADING", "SPORK_114_PAYOUT_LIVE"],
        "updated_at": _iso(),
    }


def knob_walkthrough(*, enrichment_id: Optional[str] = None, installed_min_only: bool = False) -> Dict[str, Any]:
    payload = walkthrough(enrichment_id=enrichment_id, installed_min_only=installed_min_only)
    payload["updated_at"] = _iso()
    payload["target"] = "v32.6.6.0"
    return payload


def por_glance(*, venue: Optional[str] = None, limit: int = 40) -> Dict[str, Any]:
    """X-03: join MN2 PoR with profit-path ledger rows (optional venue filter)."""
    from backend.services import exchange_profit_path_service as ppp
    from backend.services import mn2_proof_of_reserves_service as por
    from backend.services import mn2_spork_service as spork

    por_payload: Dict[str, Any] = {}
    try:
        por_payload = por.proof_of_reserves(force=False) or {}
    except Exception as exc:  # pragma: no cover
        por_payload = {"success": False, "error": str(exc)}

    export = ppp.export_rows(limit=max(1, min(int(limit or 40), 200))) or {}
    rows = list(export.get("rows") or [])
    venue_norm = (venue or "").strip().lower()
    filtered = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if venue_norm:
            blob = " ".join(
                str(row.get(k) or "")
                for k in ("venue_id", "venue", "buy_venue", "sell_venue", "route", "path")
            ).lower()
            if venue_norm not in blob:
                continue
        filtered.append(row)

    gates = {}
    try:
        gates = spork.gate_status()
    except Exception:
        gates = {}

    return {
        "success": True,
        "enrichment": "X-03",
        "venue": venue_norm or None,
        "por": por_payload,
        "ledger_count": len(filtered),
        "ledger_rows": filtered[: max(1, min(int(limit or 40), 200))],
        "gates": gates,
        "knobs": installed_knobs("X-03"),
        "updated_at": _iso(),
    }


def failover_status() -> Dict[str, Any]:
    """X-08: RPC failover + venue readiness ordered pick (no auto live broadcast)."""
    from backend.services import exchange_live_execution_service as live
    from backend.services import mn2_rpc_failover as failover
    from backend.services import mn2_spork_service as spork

    rpc = failover.status_summary()
    readiness = live.live_readiness() or {}
    venues = list(readiness.get("venues") or [])
    ranked = sorted(
        venues,
        key=lambda v: (
            0 if v.get("live_ready") else 1,
            0 if v.get("credentials_configured") else 1,
            str(v.get("venue_id") or ""),
        ),
    )
    preferred = ranked[0] if ranked else None
    standby = ranked[1] if len(ranked) > 1 else None
    ex_ok, ex_reason = spork.exchange_live_spork_ok()

    return {
        "success": True,
        "enrichment": "X-08",
        "rpc_failover": rpc,
        "venue_readiness": readiness,
        "preferred_venue": preferred,
        "standby_venue": standby,
        "live_trading_enabled": bool(readiness.get("live_gate")),
        "spork_112": {"allowed": ex_ok, "reason": ex_reason or None},
        "knobs": installed_knobs("X-08"),
        "updated_at": _iso(),
        "note": "Failover ranks venues for routing; live external legs stay SPORK_112 gated.",
    }


def assess_anomaly(
    *,
    user_id: str,
    kind: str = "withdraw",
    address: str = "",
    amount: float = 0.0,
    balance: float = 0.0,
    symbol: str = "MN2",
) -> Dict[str, Any]:
    """X-46: pre-broadcast anomaly assessment for withdraw or trade notional."""
    from backend.services import mn2_withdrawal_risk as risk

    kind_norm = "trade" if str(kind).lower() in ("trade", "swap", "order") else "withdraw"
    amount_f = float(amount or 0)
    balance_f = float(balance or 0)
    addr = (address or "").strip() or ("TRADE:" + (symbol or "MN2").upper())

    assessed = risk.assess(
        user_id=str(user_id or "anonymous"),
        address=addr,
        amount=amount_f,
        balance=balance_f if balance_f > 0 else max(amount_f, 1.0),
        config={},
    )
    blocked = bool(assessed.get("hard_block_if_no_password")) or (
        str(assessed.get("level") or "") == "high"
    )
    return {
        "success": True,
        "enrichment": "X-46",
        "kind": kind_norm,
        "blocked": blocked,
        "allow_broadcast": not blocked,
        "assessment": assessed,
        "knobs": installed_knobs("X-46"),
        "updated_at": _iso(),
    }


def guided_onchain(
    *,
    user_id: str,
    step: str,
    amount_mn2: float = 0.0,
    to_asset: str = "BTC",
    withdraw_address: str = "",
    execute_withdraw: bool = False,
) -> Dict[str, Any]:
    """X-40: guided deposit → on-chain-backed trade → withdraw (assess-first)."""
    from backend.services import crypto_exchange_service as ex
    from backend.services import mn2_spork_service as spork

    uid = str(user_id or "").strip() or "anonymous"
    step_norm = str(step or "status").strip().lower()
    ex_ok, ex_reason = spork.exchange_live_spork_ok()
    pay_ok, pay_reason = spork.payout_live_spork_ok()
    out: Dict[str, Any] = {
        "success": True,
        "enrichment": "X-40",
        "user_id": uid,
        "step": step_norm,
        "mode": "on_chain_custody",
        "knobs": installed_knobs("X-40"),
        "gates": {
            "spork_112": {"allowed": ex_ok, "reason": ex_reason or None},
            "spork_114": {"allowed": pay_ok, "reason": pay_reason or None},
        },
        "updated_at": _iso(),
    }

    if step_norm in ("status", "plan"):
        out["steps"] = [
            {"id": "deposit", "href": "/profile?tab=wallet&wallet=deposit", "api": "GET /api/mn2/deposit-address"},
            {"id": "trade", "href": "/exchange", "api": "POST /api/exchange/wallet-mega/guided"},
            {"id": "withdraw", "href": "/profile?tab=wallet&wallet=withdraw", "api": "POST /api/exchange/wallet-mega/guided"},
        ]
        out["failover"] = failover_status()
        glance = por_glance(limit=5)
        out["por_glance"] = {
            "success": glance.get("success"),
            "ledger_count": glance.get("ledger_count"),
            "venue": glance.get("venue"),
        }
        return out

    if step_norm == "deposit":
        try:
            from backend.services.mn2_wallet_service import get_or_create_deposit_address

            addr_info = get_or_create_deposit_address(uid) or {}
            out["deposit"] = addr_info
            out["next"] = "trade"
            return out
        except Exception as exc:
            out["success"] = False
            out["error"] = str(exc)
            out["hint"] = "Use GET /api/mn2/deposit-address from the profile wallet if RPC is down."
            return out

    if step_norm == "trade":
        amt = float(amount_mn2 or 0)
        if amt <= 0:
            amt = 0.01
        # Custodial sell of asset into MN2 quote — on-chain-backed ledger, not venue live.
        symbol = (to_asset or "BTC").strip().upper()
        if symbol == "MN2":
            symbol = "BTC"
        try:
            quote = ex.quote_swap(uid, symbol, "buy", amt, quote="MN2")
        except Exception as exc:
            out["success"] = False
            out["error"] = f"quote_failed:{exc}"
            return out
        swap_result: Dict[str, Any]
        if not quote.get("success"):
            swap_result = quote
        else:
            try:
                swap_result = ex.execute_swap(
                    uid,
                    str(quote.get("quote_id") or "mega"),
                    symbol,
                    "buy",
                    amt,
                    quote="MN2",
                )
            except Exception as exc:
                swap_result = {"success": False, "error": str(exc), "quote": quote}
        out["quote"] = quote
        out["trade"] = swap_result
        out["next"] = "withdraw"
        out["note"] = (
            "Custodial swap against MN2 ledger (funded by on-chain deposits). "
            "Venue live trading remains SPORK_112 gated."
        )
        return out

    if step_norm == "withdraw":
        amt = float(amount_mn2 or 0)
        bal = 0.0
        try:
            w = ex.get_wallet(uid) or {}
            bals = w.get("balances") if isinstance(w, dict) else {}
            if isinstance(bals, dict):
                bal = float(bals.get("MN2") or 0)
        except Exception:
            bal = 0.0
        assessment = assess_anomaly(
            user_id=uid,
            kind="withdraw",
            address=withdraw_address,
            amount=amt if amt > 0 else 1.0,
            balance=bal,
        )
        out["assessment"] = assessment
        if assessment.get("blocked"):
            out["withdraw"] = {"executed": False, "blocked": True, "reason": "anomaly_high"}
            return out
        if not execute_withdraw:
            out["withdraw"] = {
                "executed": False,
                "dry_run": True,
                "allow_broadcast": True,
                "hint": "Pass execute_withdraw=true to broadcast on-chain MN2 withdraw after assess.",
            }
            return out
        try:
            from backend.services import mn2_onchain_wallet as onchain

            if not withdraw_address:
                out["success"] = False
                out["error"] = "withdraw_address_required"
                return out
            if amt <= 0:
                out["success"] = False
                out["error"] = "amount_required"
                return out
            sent = onchain.send_from_user_site_pays_fee(uid, withdraw_address, amt)
            out["withdraw"] = {"executed": bool((sent or {}).get("success")), "result": sent}
            return out
        except Exception as exc:
            out["success"] = False
            out["error"] = str(exc)
            out["withdraw"] = {"executed": False}
            return out

    out["success"] = False
    out["error"] = "unknown_step"
    out["allowed_steps"] = ["status", "deposit", "trade", "withdraw"]
    return out


def prototype_bundle(*, user_id: str = "proto_user") -> Dict[str, Any]:
    """One-shot snapshot for tests and the wallets UI."""
    return {
        "success": True,
        "target": "v32.6.6.0",
        "priority": priority_install_set(),
        "knobs": knob_walkthrough(enrichment_id=None, installed_min_only=False),
        "x03": por_glance(limit=10),
        "x08": failover_status(),
        "x40": guided_onchain(user_id=user_id, step="status"),
        "x46": assess_anomaly(user_id=user_id, kind="withdraw", amount=1.0, balance=10.0, address=""),
        "updated_at": _iso(),
    }
