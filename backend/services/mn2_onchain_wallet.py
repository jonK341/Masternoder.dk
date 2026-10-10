"""
Per-user on-chain MN2 wallet.

One daemon-wallet address per site user (JSON map, plus setlabel/setaccount when
the daemon exposes them). Spends use coin control so the user's UTXOs pay the
amount and a configured site fee-payer address pays the miner fee.

If this MN2 build cannot build a raw transaction (or sendfrom) with an explicit
change address, sends are refused. They are not simulated with wallet-wide
sendtoaddress, which would take the fee from whichever coins the node picks.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

_log = logging.getLogger(__name__)

_MISSING_MARKERS = (
    "method not found",
    "unknown command",
    "not found",
    "unimplemented",
    "not recognized",
)
_SUPPORT_CACHE: Optional[Dict[str, Any]] = None
_DUST_MN2 = 0.00001


def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_mn2_config() -> Dict[str, Any]:
    path = os.path.join(_base_dir(), "data", "mn2_config.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def wallet_mode(config: Optional[Dict[str, Any]] = None) -> str:
    """Shop settlement mode. Default ledger so live shop purchases stay in-app."""
    cfg = config if config is not None else load_mn2_config()
    mode = str(cfg.get("wallet_mode") or "ledger").strip().lower()
    if mode not in ("ledger", "onchain"):
        return "ledger"
    return mode


def fee_payer_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = config if config is not None else load_mn2_config()
    block = cfg.get("onchain_fee_payer") if isinstance(cfg.get("onchain_fee_payer"), dict) else {}
    address = str(block.get("address") or "").strip()
    try:
        network_fee = float(block.get("network_fee_mn2") if block.get("network_fee_mn2") is not None else 0.001)
    except (TypeError, ValueError):
        network_fee = 0.001
    try:
        low_balance = float(block.get("low_balance_mn2") if block.get("low_balance_mn2") is not None else 5)
    except (TypeError, ValueError):
        low_balance = 5.0
    pay_withdrawal = bool(block.get("pay_external_withdrawal_fee"))
    return {
        "address": address,
        "account": str(block.get("account") or "").strip(),
        "user_id": str(block.get("user_id") or "@site_fee_payer").strip() or "@site_fee_payer",
        "network_fee_mn2": max(0.0, network_fee),
        "low_balance_mn2": max(0.0, low_balance),
        "pay_external_withdrawal_fee": pay_withdrawal,
    }


def site_pays_external_withdrawal_fee(config: Optional[Dict[str, Any]] = None) -> bool:
    """External withdrawals charge withdrawal_fee to the user unless this is true."""
    return bool(fee_payer_config(config).get("pay_external_withdrawal_fee"))


def _method_missing(err: str, body: str = "") -> bool:
    text = f"{err or ''} {body or ''}".lower()
    return any(marker in text for marker in _MISSING_MARKERS)


def clear_support_cache() -> None:
    global _SUPPORT_CACHE
    _SUPPORT_CACHE = None


def describe_send_support() -> Dict[str, Any]:
    """Which optional RPCs this daemon build actually exposes. Cached per process."""
    global _SUPPORT_CACHE
    if _SUPPORT_CACHE is not None:
        return dict(_SUPPORT_CACHE)

    from backend.services.mn2_rpc_client import rpc_help

    names = (
        "setlabel",
        "setaccount",
        "sendfrom",
        "getreceivedbyaddress",
        "createrawtransaction",
        "signrawtransactionwithwallet",
        "signrawtransaction",
        "sendrawtransaction",
        "listunspent",
    )
    methods: Dict[str, bool] = {}
    for name in names:
        probed = rpc_help(name)
        err = str(probed.get("error") or "")
        body = str(probed.get("result") or "")
        methods[name] = not _method_missing(err, body) and name.lower() in body.lower()

    raw_ok = bool(
        methods.get("createrawtransaction")
        and methods.get("sendrawtransaction")
        and (methods.get("signrawtransactionwithwallet") or methods.get("signrawtransaction"))
    )
    per_address = bool(raw_ok or methods.get("sendfrom"))
    note = (
        "Per-address sends use createrawtransaction coin control. "
        "The site fee-payer input covers the miner fee and change returns to that address."
        if raw_ok
        else (
            "sendfrom is available; the fee payer account must be labeled on the daemon."
            if methods.get("sendfrom")
            else (
                "This MN2 build does not expose createrawtransaction/sign/sendraw "
                "or sendfrom. Per-address sends are refused instead of falling back "
                "to wallet-wide sendtoaddress, which cannot charge the fee to the site."
            )
        )
    )
    _SUPPORT_CACHE = {
        "methods": methods,
        "raw_coin_control": raw_ok,
        "per_address_send": per_address,
        "labeling": bool(methods.get("setlabel") or methods.get("setaccount")),
        "note": note,
    }
    return dict(_SUPPORT_CACHE)


def _user_addresses(user_id: str) -> List[str]:
    from backend.services.mn2_wallet_service import _all_addresses_for_entry, _load_addresses

    entry = _load_addresses().get(str(user_id or "").strip())
    return _all_addresses_for_entry(entry)


def ensure_user_address(user_id: str) -> Dict[str, Any]:
    """Create the user's daemon address if missing, and label it when the RPC exists."""
    uid = str(user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "user_id required"}
    from backend.services.mn2_wallet_service import get_or_create_deposit_address

    created = get_or_create_deposit_address(uid)
    if not created.get("success"):
        return created
    address = str(created.get("deposit_address") or "")
    label = _try_label(address, uid)
    return {**created, "label": label}


def _try_label(address: str, user_id: str) -> Dict[str, Any]:
    if not address:
        return {"labeled": False, "method": None}
    support = describe_send_support()
    from backend.services import mn2_rpc_client as rpc

    if support.get("methods", {}).get("setlabel"):
        result = rpc.setlabel(address, user_id)
        if not result.get("error"):
            return {"labeled": True, "method": "setlabel"}
    if support.get("methods", {}).get("setaccount"):
        result = rpc.setaccount(address, user_id)
        if not result.get("error"):
            return {"labeled": True, "method": "setaccount"}
    return {
        "labeled": False,
        "method": None,
        "note": "Daemon has no setlabel/setaccount. user_id stays in data/mn2_user_addresses.json.",
    }


def _utxo_amount(utxo: Dict[str, Any]) -> float:
    try:
        return float(utxo.get("amount") or 0)
    except (TypeError, ValueError):
        return 0.0


def _select_coins(utxos: List[Dict[str, Any]], need: float) -> Tuple[List[Dict[str, Any]], float]:
    chosen: List[Dict[str, Any]] = []
    total = 0.0
    for utxo in sorted(utxos, key=_utxo_amount):
        if _utxo_amount(utxo) <= 0:
            continue
        chosen.append(utxo)
        total = round(total + _utxo_amount(utxo), 8)
        if total + 1e-12 >= need:
            break
    return chosen, round(total, 8)


def _list_unspent(minconf: int = 1) -> List[Dict[str, Any]]:
    from backend.services.mn2_rpc_client import _call

    result = _call("listunspent", [int(minconf), 9999999], timeout_sec=2.0)
    if result.get("error"):
        raise RuntimeError(str(result.get("error")))
    rows = result.get("result")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def chain_balance_for_user(user_id: str) -> Dict[str, Any]:
    """Confirmed and unconfirmed sums of UTXOs sitting on the user's addresses."""
    addresses = _user_addresses(user_id)
    if not addresses:
        return {
            "available": False,
            "confirmed_mn2": 0.0,
            "unconfirmed_mn2": 0.0,
            "addresses": [],
            "error": "no_deposit_address",
        }
    try:
        unspent = _list_unspent(0)
    except Exception as exc:
        return {
            "available": False,
            "confirmed_mn2": None,
            "unconfirmed_mn2": None,
            "addresses": addresses,
            "error": str(exc),
        }
    wanted = set(addresses)
    confirmed = 0.0
    unconfirmed = 0.0
    confirmations_required = int(load_mn2_config().get("confirmations") or 1)
    for utxo in unspent:
        if str(utxo.get("address") or "") not in wanted:
            continue
        amount = _utxo_amount(utxo)
        conf = int(utxo.get("confirmations") or 0)
        if conf >= confirmations_required:
            confirmed += amount
        else:
            unconfirmed += amount
    return {
        "available": True,
        "confirmed_mn2": round(confirmed, 8),
        "unconfirmed_mn2": round(unconfirmed, 8),
        "addresses": addresses,
        "confirmations_required": confirmations_required,
    }


def reconcile_user(user_id: str, ledger_balance: float) -> Dict[str, Any]:
    chain = chain_balance_for_user(user_id)
    if not chain.get("available"):
        return {"ok": False, "ledger_mn2": ledger_balance, "onchain": chain}
    confirmed = float(chain.get("confirmed_mn2") or 0)
    delta = round(confirmed - float(ledger_balance or 0), 8)
    return {
        "ok": abs(delta) < 1e-8,
        "ledger_mn2": float(ledger_balance or 0),
        "onchain_confirmed_mn2": confirmed,
        "onchain_unconfirmed_mn2": chain.get("unconfirmed_mn2"),
        "delta_mn2": delta,
    }


def build_site_paid_outputs(
    user_utxos: List[Dict[str, Any]],
    payer_utxos: List[Dict[str, Any]],
    *,
    user_change_address: str,
    payer_address: str,
    to_address: str,
    amount: float,
    network_fee: float,
) -> Dict[str, Any]:
    """Pure coin selection. User inputs cover `amount` only. Payer inputs cover `network_fee`."""
    if amount <= 0:
        return {"success": False, "error": "amount_must_be_positive", "code": "invalid_amount"}
    if network_fee < 0:
        return {"success": False, "error": "network fee must be >= 0", "code": "invalid_fee"}
    if not payer_address:
        return {"success": False, "error": "onchain_fee_payer.address is not set", "code": "fee_payer_unconfigured"}

    user_inputs, user_sum = _select_coins(user_utxos, amount)
    if user_sum + 1e-12 < amount:
        return {
            "success": False,
            "error": "Insufficient confirmed MN2 on the sender address.",
            "code": "insufficient_onchain",
            "have_mn2": user_sum,
            "need_mn2": amount,
        }
    fee_inputs, fee_sum = _select_coins(payer_utxos, network_fee)
    if network_fee > 0 and fee_sum + 1e-12 < network_fee:
        return {
            "success": False,
            "error": "Site fee payer does not have enough MN2 to cover the network fee.",
            "code": "fee_payer_insufficient",
            "fee_payer_mn2": fee_sum,
            "network_fee_mn2": network_fee,
        }

    user_change = round(user_sum - amount, 8)
    payer_change = round(fee_sum - network_fee, 8)
    if 0 < user_change < _DUST_MN2:
        amount = round(amount + user_change, 8)
        user_change = 0.0
    if 0 < payer_change < _DUST_MN2:
        payer_change = 0.0

    outputs: Dict[str, float] = {}

    def _add_output(address: str, value: float) -> None:
        if value <= 0 or not address:
            return
        outputs[address] = round(float(outputs.get(address) or 0) + value, 8)

    _add_output(to_address, amount)
    _add_output(user_change_address, user_change)
    _add_output(payer_address, payer_change)

    inputs = [
        {"txid": str(utxo.get("txid")), "vout": int(utxo.get("vout"))}
        for utxo in user_inputs + fee_inputs
    ]
    return {
        "success": True,
        "inputs": inputs,
        "outputs": outputs,
        "network_fee_mn2": network_fee,
        "user_input_mn2": user_sum,
        "fee_payer_input_mn2": fee_sum,
        "amount_mn2": amount,
    }


def _alert_path() -> str:
    path = os.path.join(_base_dir(), "logs", "mn2_fee_payer_alerts.jsonl")
    return path


def record_fee_payer_alert(payer: Dict[str, Any], remaining_mn2: float, *, txid: str = "") -> Dict[str, Any]:
    row = {
        "address": payer.get("address"),
        "user_id": payer.get("user_id"),
        "remaining_mn2": remaining_mn2,
        "low_balance_mn2": payer.get("low_balance_mn2"),
        "txid": txid or None,
    }
    _log.warning("MN2 site fee payer low balance: %s", row)
    try:
        path = _alert_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
    except Exception:
        _log.exception("could not write fee payer alert")
    return row


def _sign_and_send(raw_hex: str, support: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services import mn2_rpc_client as rpc

    if support.get("methods", {}).get("signrawtransactionwithwallet"):
        signed = rpc.signrawtransactionwithwallet(raw_hex)
    else:
        signed = rpc.signrawtransaction(raw_hex)
    if signed.get("error"):
        return {"success": False, "error": signed["error"], "code": "sign_failed"}
    signed_body = signed.get("result")
    hex_tx = ""
    complete = True
    if isinstance(signed_body, dict):
        hex_tx = str(signed_body.get("hex") or "")
        complete = bool(signed_body.get("complete", True))
    elif isinstance(signed_body, str):
        hex_tx = signed_body
    if not complete or not hex_tx:
        return {"success": False, "error": "Wallet could not sign the fee-payer transaction.", "code": "sign_incomplete"}
    sent = rpc.sendrawtransaction(hex_tx)
    if sent.get("error"):
        return {"success": False, "error": sent["error"], "code": "broadcast_failed"}
    txid = sent.get("result")
    if not isinstance(txid, str) or not txid.strip():
        return {"success": False, "error": "sendrawtransaction returned no txid", "code": "no_txid"}
    return {"success": True, "txid": txid.strip()}


def send_from_user_site_pays_fee(
    user_id: str,
    to_address: str,
    amount: float,
    *,
    kind: str,
) -> Dict[str, Any]:
    """Send `amount` from the user's UTXOs. The site fee payer pays the miner fee."""
    support = describe_send_support()
    if not support.get("raw_coin_control"):
        return {
            "success": False,
            "code": "per_address_send_unsupported",
            "error": support.get("note"),
            "support": support,
        }
    payer = fee_payer_config()
    if not payer["address"]:
        return {
            "success": False,
            "code": "fee_payer_unconfigured",
            "error": "Set onchain_fee_payer.address in data/mn2_config.json to the site fee treasury address.",
        }
    addresses = _user_addresses(user_id)
    if not addresses:
        ensured = ensure_user_address(user_id)
        if not ensured.get("success"):
            return ensured
        addresses = [str(ensured.get("deposit_address"))]
    change_address = addresses[0]
    try:
        unspent = _list_unspent(1)
    except Exception as exc:
        return {"success": False, "error": str(exc), "code": "rpc_error"}
    wanted = set(addresses)
    user_utxos = [row for row in unspent if str(row.get("address") or "") in wanted and row.get("spendable", True) is not False]
    payer_utxos = [
        row for row in unspent
        if str(row.get("address") or "") == payer["address"] and row.get("spendable", True) is not False
    ]
    built = build_site_paid_outputs(
        user_utxos,
        payer_utxos,
        user_change_address=change_address,
        payer_address=payer["address"],
        to_address=to_address,
        amount=float(amount),
        network_fee=float(payer["network_fee_mn2"]),
    )
    if not built.get("success"):
        if built.get("code") == "fee_payer_insufficient":
            record_fee_payer_alert(payer, float(built.get("fee_payer_mn2") or 0))
        return built

    from backend.services import mn2_rpc_client as rpc

    raw = rpc.createrawtransaction(built["inputs"], built["outputs"])
    if raw.get("error"):
        return {"success": False, "error": raw["error"], "code": "createraw_failed"}
    raw_hex = raw.get("result")
    if not isinstance(raw_hex, str) or not raw_hex:
        return {"success": False, "error": "createrawtransaction returned no hex", "code": "createraw_failed"}
    broadcast = _sign_and_send(raw_hex, support)
    if not broadcast.get("success"):
        return broadcast
    txid = broadcast["txid"]
    _record_site_fee(payer, float(payer["network_fee_mn2"]), txid=txid, kind=kind, from_user=user_id, to_address=to_address)
    _record_user_send(user_id, float(amount), txid=txid, to_address=to_address, kind=kind)
    remaining = round(sum(_utxo_amount(row) for row in payer_utxos) - float(payer["network_fee_mn2"]), 8)
    alert = None
    if remaining < float(payer["low_balance_mn2"]):
        alert = record_fee_payer_alert(payer, remaining, txid=txid)
    return {
        "success": True,
        "txid": txid,
        "amount_mn2": float(amount),
        "network_fee_mn2": float(payer["network_fee_mn2"]),
        "fee_paid_by": payer["user_id"],
        "fee_payer_address": payer["address"],
        "low_balance_alert": alert,
        "kind": kind,
    }


def _record_site_fee(payer: Dict[str, Any], fee: float, *, txid: str, kind: str, from_user: str, to_address: str) -> None:
    if fee <= 0:
        return
    try:
        from backend.services.mn2_ledger import append_entry

        append_entry(
            payer["user_id"],
            "site_network_fee",
            fee,
            txid=txid,
            address=payer.get("address"),
            metadata={"kind": kind, "from_user": from_user, "to_address": to_address, "paid_by": "site"},
        )
    except Exception:
        _log.exception("site fee ledger write failed")


def _record_user_send(user_id: str, amount: float, *, txid: str, to_address: str, kind: str) -> None:
    try:
        from backend.services.mn2_ledger import append_entry

        append_entry(
            user_id,
            "onchain_transfer" if kind != "shop_payment" else "shop_payment",
            amount,
            txid=txid,
            address=to_address,
            metadata={"kind": kind, "fee_paid_by": "site"},
        )
    except Exception:
        _log.exception("user transfer ledger write failed")


def iter_known_user_ids() -> List[str]:
    """Stable list of site user ids that may need a deposit address."""
    found = set()
    try:
        from backend.services.unified_points_database import unified_points_db

        found.update(str(uid) for uid in (unified_points_db.get_all_users_points() or {}))
    except Exception:
        _log.exception("could not scan unified points for backfill")
    ident_dir = os.path.join(_base_dir(), "logs", "user_identifiers")
    if os.path.isdir(ident_dir):
        for name in os.listdir(ident_dir):
            if name.endswith(".json"):
                stem = name[:-5]
                if stem:
                    found.add(stem)
    cleaned = []
    for uid in found:
        text = str(uid or "").strip()
        if not text or text == "default_user" or text.startswith("pool_"):
            continue
        cleaned.append(text)
    cleaned.sort()
    return cleaned


def users_missing_addresses(user_ids: Optional[Iterable[str]] = None) -> List[str]:
    from backend.services.mn2_wallet_service import _entry_primary, _load_addresses

    assigned = _load_addresses()
    missing = []
    for uid in list(user_ids) if user_ids is not None else iter_known_user_ids():
        entry = assigned.get(uid)
        if _entry_primary(entry):
            continue
        missing.append(uid)
    return missing


def backfill_state_path() -> str:
    return os.path.join(_base_dir(), "logs", "mn2_address_backfill_state.json")


def _load_backfill_state(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _save_backfill_state(path: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    os.replace(tmp, path)


def plan_address_backfill(
    *,
    batch_size: int = 100,
    state_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Next idempotent batch. Does not call getnewaddress and does not move the cursor."""
    path = state_path or backfill_state_path()
    state = _load_backfill_state(path)
    cursor = str(state.get("cursor") or "")
    missing = users_missing_addresses()
    if cursor:
        missing = [uid for uid in missing if uid > cursor]
    size = max(1, min(int(batch_size or 100), 1000))
    batch = missing[:size]
    return {
        "success": True,
        "dry_run": True,
        "cursor": cursor or None,
        "batch_size": size,
        "batch": batch,
        "batch_count": len(batch),
        "remaining_after_cursor": len(missing),
        "would_create": len(batch),
    }


def apply_address_backfill(
    *,
    batch_size: int = 100,
    state_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Create addresses for the next batch. Safe to re-run: existing addresses are skipped."""
    path = state_path or backfill_state_path()
    plan = plan_address_backfill(batch_size=batch_size, state_path=path)
    created = []
    skipped = []
    errors = []
    cursor = str(plan.get("cursor") or "")
    for uid in plan["batch"]:
        existing = users_missing_addresses([uid])
        if not existing:
            skipped.append(uid)
            cursor = uid
            _save_backfill_state(path, {"cursor": cursor, "last_user_id": uid, "mode": "apply"})
            continue
        result = ensure_user_address(uid)
        cursor = uid
        _save_backfill_state(path, {"cursor": cursor, "last_user_id": uid, "mode": "apply"})
        if result.get("success"):
            created.append({"user_id": uid, "deposit_address": result.get("deposit_address")})
        else:
            errors.append({"user_id": uid, "error": result.get("error"), "code": result.get("code")})
    return {
        "success": len(errors) == 0,
        "dry_run": False,
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "cursor": cursor or None,
        "batch_count": len(plan["batch"]),
    }
