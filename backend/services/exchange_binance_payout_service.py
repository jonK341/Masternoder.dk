"""Binance fiat bank wire / SEPA off-ramp for owner profit sweeps.

PayPal cannot receive exchange profit directly from Binance; this path wires fiat
from the Binance account to a **registered bank beneficiary** via Binance Fiat API.

Binance Fiat API (signed SAPI, same vault keys as spot/capital withdraw):
  GET  /sapi/v1/fiat/get-fiat-deposit-withdraw-fee  — fee quote (currency, transactionType=1)
  GET  /sapi/v1/fiat/payments                       — registered fiat payment methods (transactionType=1)
  GET  /sapi/v1/fiat/orders                         — deposit/withdraw history (transactionType=1 withdraw)
  POST /sapi/v2/fiat/withdraw                       — submit bank_transfer withdraw (BRL/ARS/MX/EUR per region)
  GET  /sapi/v1/fiat/get-order-detail               — poll orderNo until complete

EUR/SEPA: register the destination bank on Binance web/app first (Wallet → Withdraw Fiat →
verify with a small inbound transfer). API withdraw uses the verified account number.

Paper by default. Live requires ``EXCHANGE_PAYOUT_BINANCE_LIVE=1``, arb live gate, SPORK payout
live, vault ``binance_api_key`` / ``binance_api_secret``, and a configured bank beneficiary.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_binance_withdraw_service import (
    binance_credentials,
    binance_withdraw_live_enabled,
    mask_address,
)

_PAYOUT_PATH = os.path.join(ex._DATA_DIR, "payout_config.json")
_SWEEPS_PATH = os.path.join(ex._DATA_DIR, "payout_sweeps.jsonl")

# Default wire fees (Binance SEPA ~1–2 EUR; DK bank ~20 DKK) — override in payout_config.json
_DEFAULT_BANK_CFG: Dict[str, Any] = {
    "enabled": True,
    "fee_eur": 2.0,
    "fee_dkk": 20.0,
    "min_withdraw_usd": 50.0,
    "currency": "EUR",
    "payment_method": "bank_transfer",
    "region": "SEPA",
    "bank_account_id": "",
    "account_number_masked": "",
    "account_type": "current",
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_payout_cfg() -> Dict[str, Any]:
    from backend.services.exchange_payout_service import _load

    return _load()


def _bank_cfg(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or _load_payout_cfg()
    raw = cfg.get("binance_bank_wire")
    b = dict(_DEFAULT_BANK_CFG)
    if isinstance(raw, dict):
        b.update({k: v for k, v in raw.items() if v is not None})
    env_acct = (os.environ.get("EXCHANGE_PAYOUT_BINANCE_BANK_ACCOUNT") or "").strip()
    if env_acct:
        b["bank_account_id"] = env_acct
        b["account_number_masked"] = mask_address(env_acct)
    return b


def _save_bank_cfg(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _load_payout_cfg()
    cur = _bank_cfg(cfg)
    cur.update({k: v for k, v in patch.items() if v is not None})
    if cur.get("bank_account_id"):
        cur["account_number_masked"] = mask_address(str(cur["bank_account_id"]))
    cfg["binance_bank_wire"] = cur
    cfg["updated_at"] = _iso()
    ex._write_json(_PAYOUT_PATH, cfg)
    return cur


def binance_bank_wire_live_enabled() -> bool:
    """Same live gates as crypto withdraw — never enable fiat wire without explicit opt-in."""
    if not _bank_cfg().get("enabled", True):
        return False
    return binance_withdraw_live_enabled()


def _signed_fiat_request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    body: Optional[Dict[str, Any]] = None,
    dry_run: Optional[bool] = None,
    skip_live_gate: bool = False,
) -> Dict[str, Any]:
    from backend.services.exchange_binance_withdraw_service import _signed_sapi_request

    if body is not None:
        # POST /sapi/v2/fiat/withdraw expects JSON body; capital helper uses query — use direct call
        import hashlib
        import hmac
        import time
        import urllib.parse

        creds = binance_credentials()
        has_creds = bool(creds.get("api_key") and creds.get("api_secret"))
        live_required = not skip_live_gate and not binance_bank_wire_live_enabled()
        use_paper = dry_run if dry_run is not None else (live_required or not has_creds)

        if use_paper:
            return {
                "success": True,
                "mode": "paper",
                "simulated": True,
                "path": path,
                "body": body,
                "order_no": f"paper-fiat-{int(time.time())}",
                "executed_at": _iso(),
            }
        if not skip_live_gate and not binance_bank_wire_live_enabled():
            return {"success": False, "error": "live_gated",
                    "hint": "Set EXCHANGE_PAYOUT_BINANCE_LIVE=1 and EXCHANGE_ARBITRAGE_LIVE=1"}
        if not has_creds:
            return {"success": False, "error": "missing_credentials"}

        from backend.services.exchange_binance_time_service import binance_timestamp_ms, recv_window_ms
        from backend.services.exchange_binance_withdraw_service import _http_request, _attach_binance_error

        api_key = creds["api_key"] or ""
        api_secret = creds["api_secret"] or ""
        qparams = {
            "timestamp": binance_timestamp_ms(),
            "recvWindow": recv_window_ms(),
        }
        qparams["signature"] = hmac.new(
            api_secret.encode("utf-8"),
            urllib.parse.urlencode(qparams).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        query = urllib.parse.urlencode(qparams)
        url = f"https://api.binance.com{path}?{query}"
        payload = json.dumps(body, separators=(",", ":"))
        headers = {"X-MBX-APIKEY": api_key, "Content-Type": "application/json"}
        res = _http_request("POST", url, headers=headers, data=payload)
        res.setdefault("mode", "live")
        return _attach_binance_error(res, path=path)

    return _signed_sapi_request(method, path, params or {}, dry_run=dry_run, skip_live_gate=skip_live_gate)


def estimate_bank_wire_fee(*, currency: Optional[str] = None) -> Dict[str, Any]:
    """Return configured or API-quoted fiat withdraw fee."""
    b = _bank_cfg()
    cur = str(currency or b.get("currency") or "EUR").upper()
    fee_eur = float(b.get("fee_eur") or 2.0)
    fee_dkk = float(b.get("fee_dkk") or 20.0)

    fee = fee_eur if cur == "EUR" else (fee_dkk if cur == "DKK" else fee_eur)
    api_fee: Optional[float] = None
    creds = binance_credentials()
    if creds.get("api_key") and creds.get("api_secret"):
        res = _signed_fiat_request(
            "GET",
            "/sapi/v1/fiat/get-fiat-deposit-withdraw-fee",
            {"currency": cur, "transactionType": 1},
            skip_live_gate=True,
        )
        if res.get("success") and not res.get("simulated"):
            body = res.get("body")
            if isinstance(body, dict):
                try:
                    api_fee = float(body.get("withdrawFee") or body.get("fee") or 0)
                except (TypeError, ValueError):
                    pass
            elif isinstance(body, list) and body:
                row = body[0] if isinstance(body[0], dict) else {}
                try:
                    api_fee = float(row.get("withdrawFee") or row.get("fee") or 0)
                except (TypeError, ValueError):
                    pass

    return {
        "success": True,
        "currency": cur,
        "fee": round(api_fee if api_fee is not None and api_fee > 0 else fee, 4),
        "fee_eur": fee_eur,
        "fee_dkk": fee_dkk,
        "source": "binance_api" if api_fee is not None else "config",
        "payment_method": b.get("payment_method") or "bank_transfer",
    }


def get_withdraw_methods(*, skip_live_gate: bool = True) -> Dict[str, Any]:
    """List fiat off-ramp methods for the configured region (SEPA EUR default)."""
    b = _bank_cfg()
    cur = str(b.get("currency") or "EUR").upper()
    region = str(b.get("region") or "SEPA")
    methods: List[Dict[str, Any]] = [{
        "id": "bank_transfer",
        "label": f"{region} bank wire ({cur})",
        "currency": cur,
        "payment_method": "bank_transfer",
        "fee": estimate_bank_wire_fee(currency=cur).get("fee"),
        "min_withdraw_usd": float(b.get("min_withdraw_usd") or 50),
        "note": "Register bank on Binance app before live withdraw.",
    }]

    registered: List[Dict[str, Any]] = []
    creds = binance_credentials()
    if creds.get("api_key") and creds.get("api_secret"):
        res = _signed_fiat_request(
            "GET",
            "/sapi/v1/fiat/payments",
            {"transactionType": 1, "rows": 50},
            skip_live_gate=skip_live_gate,
        )
        if res.get("simulated"):
            if b.get("bank_account_id"):
                registered.append({
                    "account_number_masked": b.get("account_number_masked") or mask_address(str(b["bank_account_id"])),
                    "currency": cur,
                    "source": "config",
                })
        elif res.get("success"):
            body = res.get("body")
            rows = body if isinstance(body, list) else (body.get("data") if isinstance(body, dict) else [])
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    acct = str(row.get("accountNumber") or row.get("accountNo") or "")
                    registered.append({
                        "account_number_masked": mask_address(acct) if acct else "—",
                        "currency": str(row.get("currency") or cur).upper(),
                        "payment_method": row.get("paymentMethod") or row.get("method"),
                        "source": "binance_api",
                    })

    return {
        "success": True,
        "enabled": bool(b.get("enabled", True)),
        "region": region,
        "currency": cur,
        "methods": methods,
        "registered_accounts": registered,
        "live_enabled": binance_bank_wire_live_enabled(),
        "keys_present": bool(creds.get("api_key") and creds.get("api_secret")),
        "bank_configured": bool(b.get("bank_account_id")),
    }


def configure_bank_beneficiary(
    bank_account_id: str,
    *,
    currency: Optional[str] = None,
    account_type: str = "current",
    region: Optional[str] = None,
) -> Dict[str, Any]:
    acct = (bank_account_id or "").strip()
    if not acct or len(acct) < 4:
        return {"success": False, "error": "valid_bank_account_required",
                "hint": "Use IBAN (EUR/SEPA) or account number registered on Binance."}
    patch: Dict[str, Any] = {
        "bank_account_id": acct,
        "account_type": account_type or "current",
    }
    if currency:
        patch["currency"] = str(currency).upper()
    if region:
        patch["region"] = region
    saved = _save_bank_cfg(patch)
    ex._audit("payout_binance_bank_configured", user_id="owner",
              account_masked=mask_address(acct), currency=saved.get("currency"))
    return {
        "success": True,
        "currency": saved.get("currency"),
        "region": saved.get("region"),
        "account_number_masked": saved.get("account_number_masked"),
    }


def bank_wire_status(*, light: bool = False) -> Dict[str, Any]:
    """Monitor snapshot fields for profit daemon / business control."""
    b = _bank_cfg()
    fee = estimate_bank_wire_fee()
    creds = binance_credentials()
    min_usd = float(b.get("min_withdraw_usd") or 50)
    try:
        from backend.services.exchange_treasury_service import treasury_status
        live_stash = float(treasury_status().get("live_stash_usd") or 0)
    except Exception:
        live_stash = 0.0

    ready = bool(
        b.get("enabled")
        and b.get("bank_account_id")
        and creds.get("api_key")
        and creds.get("api_secret")
        and live_stash >= min_usd
    )
    out = {
        "success": True,
        "enabled": bool(b.get("enabled", True)),
        "currency": b.get("currency"),
        "region": b.get("region"),
        "fee": fee.get("fee"),
        "fee_currency": fee.get("currency"),
        "min_withdraw_usd": min_usd,
        "live_stash_usd": round(live_stash, 4),
        "bank_configured": bool(b.get("bank_account_id")),
        "account_number_masked": b.get("account_number_masked") or "",
        "keys_present": bool(creds.get("api_key") and creds.get("api_secret")),
        "live_enabled": binance_bank_wire_live_enabled(),
        "ready_to_withdraw": ready,
        "mode": "live" if binance_bank_wire_live_enabled() else "paper",
    }
    if not light:
        out["methods"] = get_withdraw_methods(skip_live_gate=True).get("methods") or []
    return out


def plan_bank_wire_sweep(min_usd: Optional[float] = None) -> Dict[str, Any]:
    """Plan treasury → Binance fiat bank wire when PayPal is blocked."""
    b = _bank_cfg()
    if not b.get("enabled"):
        return {"success": True, "actionable": False, "reason": "bank_wire_disabled"}
    threshold = float(min_usd if min_usd is not None else b.get("min_withdraw_usd") or 50)
    if not b.get("bank_account_id"):
        return {"success": True, "actionable": False, "reason": "no_bank_account",
                "hint": "Register bank on Binance, then POST configure with bank_account_id"}

    try:
        from backend.services.exchange_payout_service import _net_unswept_usd, _load, _sweep_ledger_mode
        cfg = _load()
        mode = _sweep_ledger_mode()
        net = _net_unswept_usd(cfg)
    except Exception:
        net = 0.0
        mode = "live" if binance_bank_wire_live_enabled() else "paper"

    if net < threshold:
        return {"success": True, "actionable": False, "reason": "below_min_withdraw",
                "net_unswept_usd": net, "min_withdraw_usd": threshold}

    creds = binance_credentials()
    if not (creds.get("api_key") and creds.get("api_secret")):
        return {"success": True, "actionable": False, "reason": "missing_binance_credentials"}

    fee = estimate_bank_wire_fee()
    return {
        "success": True,
        "actionable": True,
        "method": "binance_bank_wire",
        "destination": "binance_bank_wire",
        "currency": b.get("currency"),
        "amount_usd": round(net, 4),
        "fee": fee.get("fee"),
        "fee_currency": fee.get("currency"),
        "bank_account_masked": b.get("account_number_masked"),
        "mode": "live" if binance_bank_wire_live_enabled() else "paper",
        "sweep_ledger_mode": mode,
        "note": "Live wire requires EXCHANGE_PAYOUT_BINANCE_LIVE=1 and verified bank on Binance.",
    }


def initiate_bank_withdraw(
    amount: float,
    currency: Optional[str] = None,
    bank_account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit fiat bank wire withdraw (paper ledger row unless live gates pass)."""
    if os.environ.get("EXCHANGE_PROFIT_KILL", "").strip().lower() in ("1", "true", "yes", "on"):
        return {"success": False, "error": "profit_kill", "blocked": True}

    b = _bank_cfg()
    if not b.get("enabled"):
        return {"success": False, "error": "bank_wire_disabled"}

    cur = str(currency or b.get("currency") or "EUR").upper()
    acct = (bank_account_id or b.get("bank_account_id") or "").strip()
    if not acct:
        return {"success": False, "error": "missing_bank_account",
                "hint": "Set bank_account_id in payout_config or EXCHANGE_PAYOUT_BINANCE_BANK_ACCOUNT"}

    amt = round(max(0.0, float(amount or 0)), 2)
    min_usd = float(b.get("min_withdraw_usd") or 50)
    if amt < min_usd:
        return {"success": False, "error": "below_min_withdraw", "min_withdraw_usd": min_usd}

    creds = binance_credentials()
    if not (creds.get("api_key") and creds.get("api_secret")):
        return {"success": False, "error": "missing_binance_credentials"}

    live = binance_bank_wire_live_enabled()
    fee_info = estimate_bank_wire_fee(currency=cur)
    body = {
        "currency": cur,
        "apiPaymentMethod": str(b.get("payment_method") or "bank_transfer"),
        "amount": amt,
        "accountInfo": {
            "accountNumber": acct,
            "accountType": str(b.get("account_type") or "current"),
        },
    }

    withdraw_ref: Dict[str, Any] = {}
    if live:
        withdraw_ref = _signed_fiat_request(
            "POST", "/sapi/v2/fiat/withdraw", body=body, dry_run=False,
        )
        if not withdraw_ref.get("success"):
            return {
                "success": False,
                "error": withdraw_ref.get("error", "binance_fiat_withdraw_failed"),
                "binance_code": withdraw_ref.get("binance_code"),
                "binance_msg": withdraw_ref.get("binance_msg"),
            }
        resp_body = withdraw_ref.get("body")
        order_no = None
        if isinstance(resp_body, dict):
            order_no = resp_body.get("orderNo") or resp_body.get("orderId")
        withdraw_ref["order_no"] = order_no
    else:
        withdraw_ref = _signed_fiat_request("POST", "/sapi/v2/fiat/withdraw", body=body, dry_run=True)

    record = {
        "ts": _iso(),
        "destination": "binance_bank_wire",
        "method": "binance_bank_wire",
        "currency": cur,
        "amount": amt,
        "amount_usd": amt,
        "fee": fee_info.get("fee"),
        "fee_currency": fee_info.get("currency"),
        "bank_account_masked": mask_address(acct),
        "mode": "live" if live else "paper",
        "order_no": withdraw_ref.get("order_no"),
    }
    ex._append_jsonl(_SWEEPS_PATH, record)

    if live:
        try:
            from backend.services.exchange_payout_service import _debit_treasury_for_payout
            _debit_treasury_for_payout(amt)
        except Exception:
            pass

    cfg = _load_payout_cfg()
    ledger_mode = str(record.get("mode") or "paper").lower()
    key = f"swept_total_usd_{ledger_mode}"
    prev = float(cfg.get(key) or cfg.get("swept_total_usd") or 0)
    cfg[key] = round(prev + amt, 4)
    if ledger_mode == "paper":
        cfg["swept_total_usd"] = cfg[key]
    cfg["last_bank_wire"] = record
    ex._write_json(_PAYOUT_PATH, cfg)

    ex._audit("payout_binance_bank_wire", user_id="owner", amount=amt, currency=cur,
              mode=record["mode"], order_no=record.get("order_no"))

    note = None
    if not live:
        note = (
            "Paper bank wire recorded; no fiat moved. Set EXCHANGE_PAYOUT_BINANCE_LIVE=1 "
            "and register bank beneficiary on Binance for live SEPA/wire."
        )

    return {
        "success": True,
        "withdrawn": record,
        "live": live,
        "binance": {k: v for k, v in withdraw_ref.items()
                    if k not in ("body",) and "secret" not in str(k).lower()},
        "note": note,
    }


def maybe_auto_sweep_bank_wire() -> Dict[str, Any]:
    """Daemon hook: bank wire when PayPal blocked but live stash >= min."""
    try:
        from backend.services.exchange_payout_service import payout_status, _paypal_live_enabled, _owner_paypal_email
    except Exception:
        return {"skipped": True, "reason": "payout_unavailable"}

    if os.environ.get("EXCHANGE_AUTO_BINANCE_BANK_SWEEP", "0").strip().lower() not in ("1", "true", "yes"):
        return {"skipped": True, "reason": "auto_bank_sweep_off"}

    st = payout_status(light=True)
    paypal_blocked = not _paypal_live_enabled() or not _owner_paypal_email()
    if not paypal_blocked and st.get("ready_to_sweep"):
        return {"skipped": True, "reason": "paypal_ready"}

    plan = plan_bank_wire_sweep()
    if not plan.get("actionable"):
        return {"skipped": True, "reason": plan.get("reason"), "plan": plan}

    return initiate_bank_withdraw(float(plan["amount_usd"]), currency=plan.get("currency"))
