"""One multi-wallet for every exchange catalog coin.

MN2 stays on the on-chain daemon rails. All other tradeable coins use the
platform Binance hot wallet for deposit addresses + withdraws. A single
multi-daemon tick keeps balances, deposit intents, and withdraws in sync —
you do not need one daemon per coin.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_binance_withdraw_service import (
    binance_credentials,
    binance_withdraw_live_enabled,
    deposit_network_for_asset,
    get_deposit_address,
    get_spot_asset_free,
    list_deposit_history,
    mask_address,
    preflight_withdraw_asset,
    withdraw_asset,
)

_INTENTS_PATH = os.path.join(ex._DATA_DIR, "multi_wallet_deposit_intents.json")
_CREDITED_PATH = os.path.join(ex._DATA_DIR, "multi_wallet_credited_txids.json")
_DEPOSIT_LEDGER = os.path.join(ex._DATA_DIR, "multi_wallet_deposits.jsonl")
_WITHDRAW_LEDGER = os.path.join(ex._DATA_DIR, "multi_wallet_withdrawals.jsonl")
_STATE_PATH = os.path.join(ex._DATA_DIR, "multi_wallet_daemon_state.json")

_INTENT_TTL_HOURS = 48
_AMOUNT_MATCH_TOL = 1e-8


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cfg() -> Dict[str, Any]:
    cfg = ex.load_config()
    row = cfg.get("multi_wallet") if isinstance(cfg.get("multi_wallet"), dict) else {}
    return row if isinstance(row, dict) else {}


def _tradeable_symbols() -> List[str]:
    return [str(s).upper() for s in ex._asset_map().keys() if str(s).upper() != "MN2"]


def default_network(asset: str) -> str:
    sym = (asset or "").strip().upper()
    cfg = _cfg()
    nets = cfg.get("default_networks") if isinstance(cfg.get("default_networks"), dict) else {}
    if sym in nets:
        return str(nets[sym]).upper()
    try:
        from backend.services.exchange_stable_markets_service import default_network as stable_net
        if sym in ("USDT", "USDC"):
            return stable_net(sym)
    except Exception:
        pass
    return deposit_network_for_asset(sym)


def min_withdraw(asset: str) -> float:
    sym = (asset or "").strip().upper()
    cfg = _cfg()
    mins = cfg.get("min_withdraw") if isinstance(cfg.get("min_withdraw"), dict) else {}
    if sym in mins:
        try:
            return max(0.0, float(mins[sym]))
        except (TypeError, ValueError):
            pass
    try:
        from backend.services.exchange_stable_markets_service import min_withdraw as stable_min
        if sym in ("USDT", "USDC"):
            return stable_min(sym)
    except Exception:
        pass
    asset_row = ex._asset_map().get(sym) or {}
    return max(float(asset_row.get("min_trade") or 0), 0.0)


def venue_credentials_ok() -> bool:
    creds = binance_credentials()
    return bool(creds.get("api_key") and creds.get("api_secret"))


def _read_intents() -> Dict[str, Any]:
    return ex._read_json(_INTENTS_PATH, {"intents": []})


def _write_intents(data: Dict[str, Any]) -> None:
    ex._write_json(_INTENTS_PATH, data)


def _read_credited() -> Dict[str, Any]:
    return ex._read_json(_CREDITED_PATH, {"txids": {}})


def _write_credited(data: Dict[str, Any]) -> None:
    ex._write_json(_CREDITED_PATH, data)


def _read_state() -> Dict[str, Any]:
    return ex._read_json(_STATE_PATH, {"last_tick_at": None, "tick_count": 0})


def _write_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def multi_wallet_overview(user_id: str) -> Dict[str, Any]:
    """Full multi-wallet view: every catalog coin + deposit/withdraw capability flags."""
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    wallet = ex.get_wallet(uid)
    capabilities = []
    for row in wallet.get("wallets") or []:
        sym = str(row.get("symbol") or "").upper()
        if sym == "MN2":
            capabilities.append({
                **row,
                "deposit": True,
                "withdraw": True,
                "rail": "mn2_onchain",
                "network": "MN2",
                "profile_deposit": "/api/mn2/deposit-address",
                "profile_withdraw": "/api/mn2/withdraw",
            })
            continue
        capabilities.append({
            **row,
            "deposit": True,
            "withdraw": True,
            "rail": "binance_custody",
            "network": default_network(sym),
            "min_withdraw": min_withdraw(sym),
        })
    return {
        "success": True,
        "user_id": uid,
        "wallet": wallet,
        "coins": capabilities,
        "coin_count": len(capabilities),
        "venue_credentials": venue_credentials_ok(),
        "withdraw_live": binance_withdraw_live_enabled(),
        "one_daemon": True,
        "note": (
            "One multi-wallet covers every tradeable coin. MN2 uses the chain daemon; "
            "other coins use Binance custody. Run exchange_multi_wallet_daemon (or the "
            "master daemon tick) — not one daemon per coin."
        ),
    }


def get_deposit_instructions(user_id: str, asset: str, *,
                             amount: Optional[float] = None,
                             network: Optional[str] = None) -> Dict[str, Any]:
    """Return deposit address / memo for a coin. MN2 uses on-chain address; others use Binance."""
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    sym = (asset or "").strip().upper()
    if not sym:
        return {"success": False, "error": "missing_asset"}

    if sym == "MN2":
        from backend.services.mn2_wallet_service import get_or_create_deposit_address
        res = get_or_create_deposit_address(uid)
        return {
            "success": bool(res.get("success")),
            "asset": "MN2",
            "rail": "mn2_onchain",
            "network": "MN2",
            "address": res.get("deposit_address") or res.get("address"),
            "tag": "",
            "error": res.get("error"),
            "message": "Send MN2 to this address. The MN2 deposit scanner credits after confirmations.",
        }

    if sym not in ex._asset_map():
        return {"success": False, "error": "unknown_asset"}

    net = (network or default_network(sym)).strip().upper()
    fetched = get_deposit_address(sym, net, skip_live_gate=True)
    address = str(fetched.get("address") or "").strip()
    tag = str(fetched.get("tag") or "").strip()

    intent = None
    if amount is not None and float(amount or 0) > 0:
        intent = create_deposit_intent(uid, sym, float(amount), network=net)
        if not intent.get("success"):
            return intent

    return {
        "success": bool(address) or bool(fetched.get("simulated")),
        "asset": sym,
        "rail": "binance_custody",
        "network": net,
        "address": address,
        "address_masked": mask_address(address) if address else "",
        "tag": tag,
        "memo_required": bool(tag),
        "mode": fetched.get("mode"),
        "simulated": bool(fetched.get("simulated")),
        "intent": intent.get("intent") if intent else None,
        "message": (
            f"Send {sym} on {net} to the platform deposit address"
            + (f" with memo/tag {tag}" if tag else "")
            + ". Create a deposit intent with the exact amount so the multi-daemon can credit you, "
            "or submit the txid after sending."
        ),
        "error": None if address else (fetched.get("error") or fetched.get("binance_msg")),
    }


def create_deposit_intent(user_id: str, asset: str, amount: float,
                          network: Optional[str] = None) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    sym = (asset or "").strip().upper()
    if sym == "MN2":
        return {"success": False, "error": "mn2_uses_onchain_scanner"}
    if sym not in ex._asset_map():
        return {"success": False, "error": "unknown_asset"}
    amt = round(max(0.0, float(amount or 0)), 8)
    if amt <= 0:
        return {"success": False, "error": "invalid_amount"}

    net = (network or default_network(sym)).strip().upper()
    intent_id = uuid.uuid4().hex[:16]
    expires = (datetime.now(timezone.utc) + timedelta(hours=_INTENT_TTL_HOURS)).isoformat().replace("+00:00", "Z")
    row = {
        "intent_id": intent_id,
        "user_id": uid,
        "asset": sym,
        "amount": amt,
        "network": net,
        "status": "open",
        "created_at": _iso(),
        "expires_at": expires,
        "txid": None,
        "credited_at": None,
    }
    store = _read_intents()
    intents = [i for i in (store.get("intents") or []) if isinstance(i, dict)]
    intents.append(row)
    store["intents"] = intents[-500:]
    _write_intents(store)
    ex._audit("multi_wallet_deposit_intent", user_id=uid, asset=sym, amount=amt, intent_id=intent_id)
    return {"success": True, "intent": row}


def confirm_deposit_txid(user_id: str, asset: str, txid: str,
                         amount: Optional[float] = None,
                         intent_id: Optional[str] = None) -> Dict[str, Any]:
    """Match a Binance deposit by txid and credit the user custodial wallet."""
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    sym = (asset or "").strip().upper()
    tx = (txid or "").strip()
    if not sym or not tx:
        return {"success": False, "error": "missing_asset_or_txid"}
    if sym == "MN2":
        return {"success": False, "error": "mn2_uses_onchain_scanner"}

    credited = _read_credited()
    if tx in (credited.get("txids") or {}):
        return {"success": False, "error": "already_credited", "prior": credited["txids"][tx]}

    hist = list_deposit_history(sym, skip_live_gate=True)
    deposits = hist.get("deposits") or []
    match = None
    for row in deposits:
        row_tx = str(row.get("txId") or row.get("txid") or row.get("id") or "").strip()
        if row_tx == tx:
            match = row
            break

    if not match and hist.get("simulated"):
        # Paper/dev: accept the txid and credit the requested amount.
        amt = round(float(amount or 0), 8)
        if amt <= 0:
            return {"success": False, "error": "amount_required_in_paper"}
        match = {"txId": tx, "amount": amt, "status": 1, "coin": sym, "simulated": True}
    if not match:
        return {
            "success": False,
            "error": "txid_not_found",
            "message": "Deposit not yet visible on Binance. Wait for network confirmations, then retry.",
        }

    status = match.get("status")
    # Binance: 1 = success
    if status not in (1, "1", None) and not match.get("simulated"):
        return {"success": False, "error": "deposit_not_confirmed", "status": status}

    try:
        amt = round(float(match.get("amount") or amount or 0), 8)
    except (TypeError, ValueError):
        amt = 0.0
    if amt <= 0:
        return {"success": False, "error": "invalid_deposit_amount"}

    with ex._LOCK:
        credited = _read_credited()
        if tx in (credited.get("txids") or {}):
            return {"success": False, "error": "already_credited", "prior": credited["txids"][tx]}
        ex._adjust_balance(uid, sym, amt)
        credited.setdefault("txids", {})[tx] = {
            "user_id": uid, "asset": sym, "amount": amt, "credited_at": _iso(),
        }
        _write_credited(credited)

    if intent_id:
        store = _read_intents()
        for row in store.get("intents") or []:
            if row.get("intent_id") == intent_id and row.get("user_id") == uid:
                row["status"] = "credited"
                row["txid"] = tx
                row["credited_at"] = _iso()
        _write_intents(store)

    record = {
        "ts": _iso(), "user_id": uid, "asset": sym, "amount": amt,
        "txid": tx, "source": "binance_deposit", "intent_id": intent_id,
    }
    ex._append_jsonl(_DEPOSIT_LEDGER, record)
    ex._audit("multi_wallet_deposit_credit", user_id=uid, asset=sym, amount=amt, txid=tx)
    return {"success": True, "credited": record, "wallet": ex.get_wallet(uid)}


def withdraw_user_asset(
    user_id: str,
    asset: str,
    amount: float,
    address: str,
    network: Optional[str] = None,
) -> Dict[str, Any]:
    """Withdraw any custodial exchange coin (except MN2 — use /api/mn2/withdraw)."""
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    sym = (asset or "").strip().upper()
    if sym == "MN2":
        return {
            "success": False,
            "error": "use_mn2_withdraw",
            "message": "Withdraw MN2 via Profile → Wallet → Withdraw (/api/mn2/withdraw).",
        }
    if sym not in ex._asset_map():
        return {"success": False, "error": "unknown_asset"}

    # Stables still respect paper_mode gate from stable markets.
    if sym in ("USDT", "USDC"):
        try:
            from backend.services.exchange_stable_markets_service import (
                paper_mode_enabled,
                withdraw_enabled,
            )
            if paper_mode_enabled():
                return {"success": False, "error": "paper_mode"}
            if not withdraw_enabled():
                return {"success": False, "error": "withdraw_disabled"}
        except ImportError:
            pass

    addr = (address or "").strip()
    if not addr or len(addr) < 8:
        return {"success": False, "error": "invalid_address"}

    amt = round(max(0.0, float(amount or 0)), 8)
    floor = min_withdraw(sym)
    if floor > 0 and amt < floor:
        return {"success": False, "error": "below_min_withdraw", "min_withdraw": floor}

    bal = float(ex._get_balance(uid, sym) or 0)
    if amt > bal + 1e-12:
        return {"success": False, "error": f"insufficient_{sym.lower()}", "balance": bal}

    net = (network or default_network(sym)).strip().upper()
    if not venue_credentials_ok():
        return {"success": False, "error": "missing_binance_credentials"}

    live = binance_withdraw_live_enabled()
    if not live:
        return {
            "success": False,
            "error": "live_gates_required",
            "message": (
                "Real withdraw needs EXCHANGE_PAYOUT_BINANCE_LIVE=1, "
                "EXCHANGE_ARBITRAGE_LIVE=1, and payout spork open."
            ),
        }

    spot = get_spot_asset_free(sym, skip_live_gate=True)
    spot_free = float(spot.get("free") or 0) if spot.get("success") else 0.0
    if spot_free + 1e-12 < amt:
        return {
            "success": False,
            "error": "venue_spot_insufficient",
            "requested": amt,
            "binance_spot_free": spot_free,
        }

    pf = preflight_withdraw_asset(sym, amt, addr, net, skip_live_gate=True, sales_pool_amount=None)
    if not pf.get("ready"):
        return {"success": False, "error": "preflight_failed", "preflight": pf}

    order_id = f"mn2-mw-{uid[:20]}-{sym}-{int(time.time())}"
    fee_bps = int((ex.load_config().get("platform_fees") or {}).get("withdrawal_fee_bps") or 15)
    fee = round(amt * fee_bps / 10000.0, 8)
    send_amt = round(max(0.0, amt - fee), 8)
    if send_amt <= 0:
        return {"success": False, "error": "amount_too_small_after_fee", "fee": fee}

    with ex._LOCK:
        bal = float(ex._get_balance(uid, sym) or 0)
        if amt > bal + 1e-12:
            return {"success": False, "error": f"insufficient_{sym.lower()}", "balance": bal}
        try:
            ex._adjust_balance(uid, sym, -amt)
        except Exception as exc:
            return {"success": False, "error": "debit_failed", "detail": str(exc)}

        wref = withdraw_asset(sym, send_amt, addr, net, dry_run=False, withdraw_order_id=order_id)
        if not wref.get("success"):
            try:
                ex._adjust_balance(uid, sym, amt)
            except Exception:
                pass
            return {
                "success": False,
                "error": wref.get("error", "binance_withdraw_failed"),
                "binance": {
                    k: v for k, v in wref.items()
                    if k not in ("body",) and "secret" not in str(k).lower()
                },
            }

    record = {
        "ts": _iso(),
        "user_id": uid,
        "asset": sym,
        "amount": amt,
        "fee": fee,
        "send_amount": send_amt,
        "network": net,
        "address_masked": mask_address(addr),
        "mode": "live",
        "withdraw_id": wref.get("withdraw_id"),
        "withdraw_order_id": order_id,
        "transferable": True,
    }
    ex._append_jsonl(_WITHDRAW_LEDGER, record)
    ex._audit("multi_wallet_withdraw", user_id=uid, asset=sym, amount=amt, withdraw_id=record.get("withdraw_id"))
    return {"success": True, "withdrawn": record, "wallet": ex.get_wallet(uid), "live": True}


def sync_platform_deposit_addresses(*, dry_run: bool = False) -> Dict[str, Any]:
    """Refresh Binance deposit addresses for every tradeable non-MN2 coin."""
    if not venue_credentials_ok() and not dry_run:
        # Still allow paper/simulated addresses.
        pass
    synced: List[Dict[str, Any]] = []
    for sym in _tradeable_symbols():
        net = default_network(sym)
        fetched = get_deposit_address(sym, net, dry_run=True if dry_run else None, skip_live_gate=True)
        synced.append({
            "asset": sym,
            "network": net,
            "address_masked": mask_address(str(fetched.get("address") or "")),
            "has_address": bool(fetched.get("address")),
            "tag": fetched.get("tag") or "",
            "mode": fetched.get("mode"),
            "success": bool(fetched.get("success")),
            "error": fetched.get("error") or fetched.get("binance_msg"),
        })
    return {"success": True, "synced": synced, "count": len(synced)}


def scan_open_intents(*, force: bool = False) -> Dict[str, Any]:
    """Match open deposit intents against Binance deposit history by amount."""
    store = _read_intents()
    intents = [i for i in (store.get("intents") or []) if isinstance(i, dict)]
    now = datetime.now(timezone.utc)
    credited_n = 0
    expired_n = 0
    checked = 0
    credited = _read_credited()

    # Prefetch recent deposits once.
    hist = list_deposit_history(skip_live_gate=True)
    deposits = hist.get("deposits") or []

    for intent in intents:
        if intent.get("status") != "open":
            continue
        checked += 1
        exp = intent.get("expires_at")
        try:
            exp_dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
            if exp_dt < now:
                intent["status"] = "expired"
                expired_n += 1
                continue
        except Exception:
            pass

        sym = str(intent.get("asset") or "").upper()
        want = float(intent.get("amount") or 0)
        uid = str(intent.get("user_id") or "")
        if not sym or want <= 0 or not uid:
            continue

        for dep in deposits:
            if str(dep.get("coin") or "").upper() != sym:
                continue
            status = dep.get("status")
            if status not in (1, "1") and not hist.get("simulated"):
                continue
            tx = str(dep.get("txId") or dep.get("txid") or dep.get("id") or "").strip()
            if not tx or tx in (credited.get("txids") or {}):
                continue
            try:
                got = float(dep.get("amount") or 0)
            except (TypeError, ValueError):
                continue
            if abs(got - want) > max(_AMOUNT_MATCH_TOL, want * 1e-6):
                continue

            with ex._LOCK:
                credited = _read_credited()
                if tx in (credited.get("txids") or {}):
                    continue
                ex._adjust_balance(uid, sym, got)
                credited.setdefault("txids", {})[tx] = {
                    "user_id": uid, "asset": sym, "amount": got,
                    "credited_at": _iso(), "intent_id": intent.get("intent_id"),
                }
                _write_credited(credited)
            intent["status"] = "credited"
            intent["txid"] = tx
            intent["credited_at"] = _iso()
            ex._append_jsonl(_DEPOSIT_LEDGER, {
                "ts": _iso(), "user_id": uid, "asset": sym, "amount": got,
                "txid": tx, "source": "intent_match", "intent_id": intent.get("intent_id"),
            })
            credited_n += 1
            break

    store["intents"] = intents
    _write_intents(store)
    return {
        "success": True,
        "checked": checked,
        "credited": credited_n,
        "expired": expired_n,
        "deposits_seen": len(deposits),
        "simulated": bool(hist.get("simulated")),
    }


def refresh_venue_balances() -> Dict[str, Any]:
    """Read Binance spot free for every tradeable coin (status only — no ledger inventing)."""
    out: Dict[str, Any] = {}
    for sym in _tradeable_symbols():
        spot = get_spot_asset_free(sym, skip_live_gate=True)
        out[sym] = {
            "free": float(spot.get("free") or 0) if (spot.get("success") or spot.get("simulated")) else None,
            "success": bool(spot.get("success") or spot.get("simulated")),
            "simulated": bool(spot.get("simulated")),
            "error": spot.get("error") or spot.get("binance_msg"),
        }
    return {"success": True, "balances": out}


def run_multi_wallet_tick(*, force: bool = False) -> Dict[str, Any]:
    """Single tick for ALL coin wallets: ensure slots, sync addresses, scan deposits, refresh balances."""
    state = _read_state()
    ensure = ex.ensure_agent_wallets()
    # Ensure every known user wallet file also has full slots.
    ensured_users = 0
    try:
        for name in os.listdir(ex._WALLETS_DIR):
            if not name.endswith(".json"):
                continue
            uid = name[:-5]
            ex.get_wallet(uid)
            ensured_users += 1
    except Exception:
        pass

    sync = sync_platform_deposit_addresses()
    scan = scan_open_intents(force=force)
    venue = refresh_venue_balances()

    mn2_scan = {"skipped": True}
    try:
        import importlib.util
        if importlib.util.find_spec("sqlalchemy") is None:
            mn2_scan = {
                "success": False,
                "skipped": True,
                "error": "sqlalchemy_missing",
                "hint": "Install sqlalchemy in the venv for MN2 deposit scanning, or ignore on exchange-only hosts.",
            }
        else:
            from backend.services.mn2_deposit_scanner import run_scanner
            mn2_scan = run_scanner()
    except Exception as exc:
        mn2_scan = {"success": False, "error": str(exc)}

    try:
        from backend.services.exchange_stable_markets_service import (
            paper_mode_enabled,
            sync_sales_pool_stables_from_venue,
        )
        pool_sync = (
            {"skipped": True, "reason": "paper_mode"}
            if paper_mode_enabled()
            else sync_sales_pool_stables_from_venue()
        )
    except Exception as exc:
        pool_sync = {"success": False, "error": str(exc)}

    agent_tick: Dict[str, Any] = {"skipped": True}
    try:
        from backend.services.crypto_exchange_agent_service import tick as agent_trading_tick
        agent_tick = agent_trading_tick(force=force)
    except Exception as exc:
        agent_tick = {"success": False, "error": str(exc)}

    state["last_tick_at"] = _iso()
    state["tick_count"] = int(state.get("tick_count") or 0) + 1
    state["last_result"] = {
        "ensure_agents": ensure.get("count"),
        "ensure_users": ensured_users,
        "scan_credited": scan.get("credited"),
        "venue_assets": len((venue.get("balances") or {})),
        "agent_mode": agent_tick.get("mode"),
        "agent_actions": len(agent_tick.get("actions") or []),
    }
    _write_state(state)

    return {
        "success": True,
        "tick_count": state["tick_count"],
        "last_tick_at": state["last_tick_at"],
        "ensure_agents": ensure,
        "ensure_users": ensured_users,
        "deposit_addresses": sync,
        "deposit_scan": scan,
        "venue_balances": venue,
        "mn2_deposit_scan": mn2_scan,
        "sales_pool_sync": pool_sync,
        "agent_trading": agent_tick,
        "one_daemon": True,
    }


def daemon_status() -> Dict[str, Any]:
    state = _read_state()
    store = _read_intents()
    open_n = sum(1 for i in (store.get("intents") or []) if i.get("status") == "open")
    return {
        "success": True,
        "one_daemon": True,
        "daemon_script": "scripts/exchange_multi_wallet_daemon.py",
        "last_tick_at": state.get("last_tick_at"),
        "tick_count": int(state.get("tick_count") or 0),
        "open_deposit_intents": open_n,
        "venue_credentials": venue_credentials_ok(),
        "withdraw_live": binance_withdraw_live_enabled(),
        "tradeable_coins": _tradeable_symbols(),
        "last_result": state.get("last_result"),
        "note": "Do not run one daemon per coin — this multi-daemon covers balances, deposits, and withdraws for all wallets.",
    }
