"""MasterNoder custodial crypto exchange — 25 assets, fees, tax records, lawful bonuses."""
from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "crypto_exchange_config.json")
_DATA_DIR = os.path.join(_BASE, "data", "crypto_exchange")
if os.environ.get("EXCHANGE_DEV_PAPER", "").strip().lower() in ("1", "true", "yes"):
    _DATA_DIR = _DATA_DIR + "_PAPER"
    os.makedirs(_DATA_DIR, exist_ok=True)
_WALLETS_DIR = os.path.join(_DATA_DIR, "wallets")
_ORDERS_PATH = os.path.join(_DATA_DIR, "orders.json")
_TRADES_PATH = os.path.join(_DATA_DIR, "trades.jsonl")
_TAX_PATH = os.path.join(_DATA_DIR, "tax_ledger.jsonl")
_BONUS_PATH = os.path.join(_DATA_DIR, "bonus_claims.json")
_TREASURY_PATH = os.path.join(_DATA_DIR, "fee_treasury.json")
_PRICE_CACHE_PATH = os.path.join(_DATA_DIR, "price_cache.json")
_PAYPAL_CRYPTO_ORDERS_PATH = os.path.join(_DATA_DIR, "paypal_crypto_orders.json")
_PAYPAL_MN2_ORDERS_PATH = os.path.join(_DATA_DIR, "paypal_mn2_orders.json")
_AUDIT_PATH = os.path.join(_DATA_DIR, "audit_log.jsonl")
_STABLE_QUOTES = frozenset({"USDC", "USDT"})


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _append_jsonl(path: str, row: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def load_config() -> Dict[str, Any]:
    cfg = _read_json(_CONFIG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _asset_map(cfg: Optional[Dict] = None) -> Dict[str, dict]:
    cfg = cfg or load_config()
    return {a["symbol"]: a for a in (cfg.get("assets") or []) if a.get("symbol")}


def _mn2_usd() -> float:
    try:
        from backend.services.mn2_chainz import chainz_ticker_usd
        t = chainz_ticker_usd()
        if t and float(t) > 0:
            return float(t)
    except Exception:
        pass
    return float(_asset_map().get("MN2", {}).get("base_price_usd") or 0.05)


def _price_usd(symbol: str, cfg: Optional[Dict] = None) -> float:
    cfg = cfg or load_config()
    assets = _asset_map(cfg)
    asset = assets.get(symbol)
    if not asset:
        return 0.0
    base = float(asset.get("base_price_usd") or 0)
    cache = _read_json(_PRICE_CACHE_PATH, {})
    drift = float(cache.get(symbol, 1.0) or 1.0)
    return round(base * drift, 12)


def _stable_cross_rate(symbol: str, quote: str, cfg: Optional[Dict] = None) -> float:
    """USDC↔USDT and other stable-quoted prices via USD peg (with cache drift)."""
    sym_usd = _price_usd(symbol, cfg)
    quote_usd = _price_usd(quote, cfg)
    if sym_usd <= 0 or quote_usd <= 0:
        return 0.0
    return sym_usd / quote_usd


def _price_in_quote(symbol: str, quote: str, cfg: Optional[Dict] = None) -> float:
    usd = _price_usd(symbol, cfg)
    if quote == "MN2":
        mn2 = _mn2_usd()
        return usd / mn2 if mn2 > 0 else 0.0
    if quote == "COINS":
        mn2_cfg = _read_json(os.path.join(_BASE, "data", "mn2_config.json"), {})
        cpm = float(mn2_cfg.get("coins_per_mn2") or 100)
        return _price_in_quote(symbol, "MN2", cfg) * cpm
    if quote in _STABLE_QUOTES:
        return _stable_cross_rate(symbol, quote, cfg)
    return 0.0


def _wallet_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id))
    return os.path.join(_WALLETS_DIR, f"{safe}.json")


def get_wallet(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    data = _read_json(_wallet_path(uid), {"assets": {}, "staking": {}, "bonus": {}, "volume_usd_30d": 0})
    assets = data.get("assets") if isinstance(data.get("assets"), dict) else {}
    return {
        "success": True,
        "user_id": uid,
        "assets": assets,
        "staking": data.get("staking") or {},
        "bonus": data.get("bonus") or {},
        "volume_usd_30d": float(data.get("volume_usd_30d") or 0),
    }


def _save_wallet(user_id: str, data: dict) -> None:
    _write_json(_wallet_path(user_id), data)


def _get_balance(user_id: str, symbol: str) -> float:
    w = get_wallet(user_id)
    return float((w.get("assets") or {}).get(symbol) or 0)


def _set_balance(user_id: str, symbol: str, amount: float) -> None:
    path = _wallet_path(user_id)
    data = _read_json(path, {"assets": {}, "staking": {}, "bonus": {}, "volume_usd_30d": 0})
    assets = data.setdefault("assets", {})
    assets[symbol] = round(float(amount), 12)
    _save_wallet(user_id, data)


def _adjust_balance(user_id: str, symbol: str, delta: float) -> float:
    cur = _get_balance(user_id, symbol)
    new = round(cur + float(delta), 12)
    if new < -1e-12:
        raise ValueError(f"insufficient_{symbol}")
    _set_balance(user_id, symbol, max(0, new))
    return new


def _is_wallet_quote(quote: str) -> bool:
    return quote in _STABLE_QUOTES


def _quote_balance_field(quote: str) -> Optional[str]:
    if quote == "MN2":
        return "mn2_balance"
    if quote == "COINS":
        return "coins"
    return None


def _get_quote_balance(user_id: str, quote: str) -> float:
    if _is_wallet_quote(quote):
        return _get_balance(user_id, quote)
    field = _quote_balance_field(quote)
    if not field:
        return 0.0
    from backend.services.unified_points_database import unified_points_db
    bal = unified_points_db.get_all_points(user_id).get("points") or {}
    return float(bal.get(field) or 0)


def _adjust_quote_balance(user_id: str, quote: str, delta: float, source: str, meta: dict) -> None:
    if _is_wallet_quote(quote):
        _adjust_balance(user_id, quote, delta)
        return
    field = _quote_balance_field(quote)
    if not field:
        raise ValueError("invalid_quote")
    from backend.services.unified_points_database import unified_points_db
    unified_points_db.add_points(user_id, field, float(delta), source=source, metadata=meta)


def _fee_quote_to_mn2(fee_quote: float, quote: str, cfg: Optional[Dict] = None) -> float:
    if quote == "MN2":
        return fee_quote
    if quote == "COINS":
        cpm = float(_read_json(os.path.join(_BASE, "data", "mn2_config.json"), {}).get("coins_per_mn2") or 100)
        return fee_quote / max(cpm, 1)
    if quote in _STABLE_QUOTES:
        return fee_quote * _price_usd(quote, cfg) / max(_mn2_usd(), 1e-12)
    return 0.0


def _fee_quote_to_usd(fee_quote: float, quote: str, cfg: Optional[Dict] = None) -> float:
    if quote == "MN2":
        return fee_quote * _mn2_usd()
    if quote in _STABLE_QUOTES:
        return fee_quote * _price_usd(quote, cfg)
    return 0.0


def _fee_bps(side: str, is_maker: bool, cfg: dict, user_id: str) -> int:
    fees = cfg.get("platform_fees") or {}
    base = int(fees.get("maker_fee_bps" if is_maker else "taker_fee_bps") or 10)
    vol = get_wallet(user_id).get("volume_usd_30d") or 0
    rebate = 0
    for tier in sorted((cfg.get("rewards") or {}).get("volume_tiers") or [], key=lambda t: t.get("min_volume_usd", 0), reverse=True):
        if vol >= float(tier.get("min_volume_usd") or 0):
            rebate = int(tier.get("fee_rebate_bps") or 0)
            break
    if is_maker:
        rebate += int((cfg.get("rewards") or {}).get("maker_rebate_bps") or 0)
    return max(0, base - rebate)


def _record_tax(user_id: str, symbol: str, side: str, amount: float, usd_value: float, fee_usd: float) -> None:
    cfg = load_config()
    tax_cfg = cfg.get("tax") or {}
    if not tax_cfg.get("enabled"):
        return
    rate_bps = int(tax_cfg.get("capital_gains_rate_bps") or 0)
    taxable = usd_value if side == "sell" else 0.0
    record = {
        "ts": _iso(),
        "user_id": user_id,
        "symbol": symbol,
        "side": side,
        "amount": amount,
        "usd_value": round(usd_value, 4),
        "fee_usd": round(fee_usd, 4),
        "taxable_gain_usd": round(taxable, 4),
        "reference_rate_bps": rate_bps,
        "jurisdiction": tax_cfg.get("jurisdiction_label") or cfg.get("jurisdiction"),
    }
    _append_jsonl(_TAX_PATH, record)


def _collect_fee(fee_mn2: float) -> None:
    tre = _read_json(_TREASURY_PATH, {"total_fees_mn2": 0, "updated_at": None})
    tre["total_fees_mn2"] = round(float(tre.get("total_fees_mn2") or 0) + fee_mn2, 8)
    tre["updated_at"] = _iso()
    _write_json(_TREASURY_PATH, tre)


def _add_volume(user_id: str, usd: float) -> None:
    path = _wallet_path(user_id)
    data = _read_json(path, {"assets": {}, "staking": {}, "bonus": {}, "volume_usd_30d": 0})
    data["volume_usd_30d"] = round(float(data.get("volume_usd_30d") or 0) + usd, 4)
    _save_wallet(user_id, data)


def _emit(event: str, **kwargs) -> None:
    try:
        from backend.services.activity_events_service import emit
        emit(event, **kwargs)
    except Exception:
        pass


def _last_audit_hash() -> str:
    if not os.path.isfile(_AUDIT_PATH):
        return "genesis"
    last = None
    try:
        with open(_AUDIT_PATH, "rb") as f:
            for raw in f:
                raw = raw.strip()
                if raw:
                    last = raw
    except OSError:
        return "genesis"
    if not last:
        return "genesis"
    try:
        return json.loads(last).get("hash") or "genesis"
    except Exception:
        return "genesis"


def _audit(action: str, *, user_id: str = "", amount_usd: float = 0.0, **fields: Any) -> None:
    """Append a hash-chained audit record. Best-effort, never raises."""
    cfg = load_config()
    if not (cfg.get("audit") or {}).get("enabled", True):
        return
    try:
        with _LOCK:
            prev_hash = _last_audit_hash()
            record = {
                "ts": _iso(),
                "action": action,
                "user_id": str(user_id or ""),
                "amount_usd": round(float(amount_usd or 0), 6),
                "data": fields,
                "prev_hash": prev_hash,
            }
            digest_src = json.dumps(
                {k: record[k] for k in ("ts", "action", "user_id", "amount_usd", "data", "prev_hash")},
                sort_keys=True,
                default=str,
            )
            record["hash"] = hashlib.sha256(digest_src.encode("utf-8")).hexdigest()
            _append_jsonl(_AUDIT_PATH, record)
    except Exception:
        pass


def get_audit_tail(limit: int = 50) -> Dict[str, Any]:
    limit = max(1, min(int(limit or 50), 500))
    if not os.path.isfile(_AUDIT_PATH):
        return {"success": True, "records": [], "count": 0}
    rows: List[Dict[str, Any]] = []
    with open(_AUDIT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return {"success": True, "records": rows[-limit:][::-1], "count": len(rows)}


def verify_audit_chain() -> Dict[str, Any]:
    """Recompute the hash chain to confirm the audit log was not tampered with."""
    if not os.path.isfile(_AUDIT_PATH):
        return {"success": True, "valid": True, "count": 0}
    prev = "genesis"
    count = 0
    with open(_AUDIT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except Exception:
                return {"success": True, "valid": False, "count": count, "error": "corrupt_record"}
            count += 1
            if record.get("prev_hash") != prev:
                return {"success": True, "valid": False, "count": count, "error": "broken_chain"}
            digest_src = json.dumps(
                {k: record.get(k) for k in ("ts", "action", "user_id", "amount_usd", "data", "prev_hash")},
                sort_keys=True,
                default=str,
            )
            expected = hashlib.sha256(digest_src.encode("utf-8")).hexdigest()
            if expected != record.get("hash"):
                return {"success": True, "valid": False, "count": count, "error": "hash_mismatch"}
            prev = record.get("hash")
    return {"success": True, "valid": True, "count": count}


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(ts or "").replace("Z", "+00:00"))
    except Exception:
        return None


def _validate_paypal_capture(capture: Dict[str, Any], expected_usd: float, *, expected_currency: str = "USD") -> Optional[str]:
    if not capture.get("success"):
        return capture.get("error") or "PayPal capture failed"
    try:
        paid = round(float(capture.get("amount") or 0), 2)
    except (TypeError, ValueError):
        return "invalid_capture_amount"
    expected = round(float(expected_usd or 0), 2)
    currency = str(capture.get("currency") or expected_currency).upper()
    if currency != expected_currency.upper():
        return "capture_currency_mismatch"
    if paid + 0.01 < expected:
        return "capture_amount_mismatch"
    return None


def get_catalog() -> Dict[str, Any]:
    cfg = load_config()
    assets = []
    for a in cfg.get("assets") or []:
        sym = a.get("symbol")
        assets.append({
            **a,
            "price_usd": _price_usd(sym, cfg),
            "price_mn2": _price_in_quote(sym, "MN2", cfg),
            "price_coins": _price_in_quote(sym, "COINS", cfg),
        })
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "name": cfg.get("name"),
        "jurisdiction": cfg.get("jurisdiction"),
        "legal_notice": cfg.get("legal_notice"),
        "quote_currencies": cfg.get("quote_currencies") or ["MN2", "COINS"],
        "default_quote": cfg.get("default_quote") or "MN2",
        "fees": cfg.get("platform_fees"),
        "tax": cfg.get("tax"),
        "lawful_bonus": cfg.get("lawful_bonus"),
        "rewards": cfg.get("rewards"),
        "assets": assets,
        "asset_count": len(assets),
        "mn2_usd": _mn2_usd(),
    }


def get_ticker(symbol: str) -> Dict[str, Any]:
    sym = (symbol or "").strip().upper()
    assets = _asset_map()
    if sym not in assets:
        return {"success": False, "error": "unknown_asset"}
    cfg = load_config()
    return {
        "success": True,
        "symbol": sym,
        "price_usd": _price_usd(sym, cfg),
        "price_mn2": _price_in_quote(sym, "MN2", cfg),
        "price_coins": _price_in_quote(sym, "COINS", cfg),
        "change_24h_pct": 0.0,
        "volume_24h_usd": 0.0,
    }


def get_all_tickers() -> Dict[str, Any]:
    cfg = load_config()
    tickers = []
    for a in cfg.get("assets") or []:
        sym = a.get("symbol")
        tickers.append(get_ticker(sym))
    return {"success": True, "tickers": [t for t in tickers if t.get("success")]}


def quote_paypal_crypto(symbol: str, usd_amount: float, user_id: str = "") -> Dict[str, Any]:
    """Quote a direct PayPal USD -> exchange asset purchase."""
    cfg = load_config()
    sym = (symbol or "").strip().upper()
    assets = _asset_map(cfg)
    if sym not in assets:
        return {"success": False, "error": "unknown_asset"}
    usd = float(usd_amount or 0)
    limits = cfg.get("paypal_crypto_buy") or {}
    if not limits.get("enabled", True):
        return {"success": False, "error": "paypal_crypto_buy_disabled"}
    min_usd = float(limits.get("min_usd") or 5.0)
    max_usd = float(limits.get("max_usd") or 500.0)
    if usd < min_usd:
        return {"success": False, "error": "below_min_usd", "min_usd": min_usd}
    if usd > max_usd:
        return {"success": False, "error": "above_max_usd", "max_usd": max_usd}

    uid = (user_id or "").strip()
    if uid and uid.lower() != "default_user":
        try:
            from backend.services.crypto_exchange_risk_service import check_fiat_buy

            risk = check_fiat_buy(uid, usd)
            if not risk.get("ok"):
                _audit("risk_denied", user_id=uid, amount_usd=usd, kind="crypto", reason=risk.get("error"))
                return {"success": False, "error": risk.get("error", "risk_blocked"), "risk": risk}
        except Exception:
            pass

    price = _price_usd(sym, cfg)
    if price <= 0:
        return {"success": False, "error": "no_price"}
    fee_bps = int(limits.get("fee_bps") or (cfg.get("platform_fees") or {}).get("taker_fee_bps") or 25)
    fee_usd = round(usd * fee_bps / 10000, 4)
    net_usd = max(0.0, usd - fee_usd)
    amount = round(net_usd / price, 12)
    asset = assets[sym]
    if amount < float(asset.get("min_trade") or 0):
        return {"success": False, "error": "below_min_trade", "min_trade": asset.get("min_trade")}
    return {
        "success": True,
        "quote_id": uuid.uuid4().hex[:16],
        "symbol": sym,
        "usd_amount": round(usd, 2),
        "price_usd": price,
        "fee_bps": fee_bps,
        "fee_usd": fee_usd,
        "net_usd": round(net_usd, 4),
        "asset_amount": amount,
        "user_id": (user_id or "").strip(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
    }


def record_paypal_crypto_order(order_id: str, quote: Dict[str, Any], *, approve_url: str = "") -> Dict[str, Any]:
    order_id = (order_id or "").strip()
    if not order_id:
        return {"success": False, "error": "order_id required"}
    if not quote.get("success"):
        return {"success": False, "error": quote.get("error", "invalid_quote")}
    with _LOCK:
        rows = _read_json(_PAYPAL_CRYPTO_ORDERS_PATH, {"pending": {}, "captured": {}})
        rows.setdefault("pending", {})[order_id] = {
            "order_id": order_id,
            "quote": quote,
            "approve_url": approve_url,
            "created_at": _iso(),
        }
        _write_json(_PAYPAL_CRYPTO_ORDERS_PATH, rows)
    return {"success": True, "order_id": order_id}


def fulfill_paypal_crypto_order(user_id: str, order_id: str, capture: Dict[str, Any]) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    order_id = (order_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    if not order_id:
        return {"success": False, "error": "order_id required"}
    if not capture.get("success"):
        return {"success": False, "error": capture.get("error", "PayPal capture failed")}

    with _LOCK:
        rows = _read_json(_PAYPAL_CRYPTO_ORDERS_PATH, {"pending": {}, "captured": {}})
        if order_id in rows.get("captured", {}):
            prior = rows["captured"][order_id]
            return {"success": True, "duplicate": True, **prior}
        pending = (rows.get("pending") or {}).get(order_id)
        if not pending:
            return {"success": False, "error": "pending_order_not_found"}
        quote = pending.get("quote") or {}
        sym = quote.get("symbol")
        amount = float(quote.get("asset_amount") or 0)
        usd_value = float(quote.get("usd_amount") or 0)
        fee_usd = float(quote.get("fee_usd") or 0)
        quote_user = str(quote.get("user_id") or "").strip()
        if quote_user and quote_user != uid:
            return {"success": False, "error": "order_user_mismatch"}
        expires = _parse_iso(quote.get("expires_at"))
        if expires and expires < datetime.now(timezone.utc):
            return {"success": False, "error": "quote_expired"}
        capture_error = _validate_paypal_capture(capture, usd_value)
        if capture_error:
            return {"success": False, "error": capture_error}
        if sym not in _asset_map() or amount <= 0:
            return {"success": False, "error": "invalid_pending_quote"}

        ref = f"paypal-crypto:{capture.get('capture_id') or order_id}:{sym}"
        _adjust_balance(uid, sym, amount)
        _collect_fee(fee_usd / max(_mn2_usd(), 0.00000001))
        _add_volume(uid, usd_value)
        _record_tax(uid, sym, "buy", amount, usd_value, fee_usd)
        try:
            from backend.services.monetization_ledger_service import append_payment_event

            append_payment_event(
                provider="paypal",
                user_id=uid,
                order_id=order_id,
                capture_id=capture.get("capture_id"),
                amount_usd=usd_value,
                currency=capture.get("currency") or "USD",
                item_id=f"crypto:{sym}",
                item_name=f"Exchange buy {sym}",
                extra={"source": "exchange_paypal_crypto", "asset_amount": amount, "fee_usd": fee_usd},
            )
        except Exception:
            pass
        trade = {
            "ts": _iso(),
            "trade_id": ref,
            "user_id": uid,
            "type": "paypal_buy",
            "symbol": sym,
            "side": "buy",
            "amount": amount,
            "usd_value": usd_value,
            "fee_usd": fee_usd,
            "order_id": order_id,
            "capture_id": capture.get("capture_id"),
        }
        _append_jsonl(_TRADES_PATH, trade)
        captured = {
            "user_id": uid,
            "symbol": sym,
            "asset_amount": amount,
            "usd_amount": usd_value,
            "fee_usd": fee_usd,
            "capture_id": capture.get("capture_id"),
            "captured_at": _iso(),
        }
        rows.setdefault("captured", {})[order_id] = captured
        rows.get("pending", {}).pop(order_id, None)
        _write_json(_PAYPAL_CRYPTO_ORDERS_PATH, rows)

    _emit("exchange_paypal_crypto_buy", channel="exchange", user_id=uid, payload=trade)
    _audit("paypal_crypto_capture", user_id=uid, amount_usd=usd_value, symbol=sym, asset_amount=amount, order_id=order_id, capture_id=capture.get("capture_id"))
    try:
        from backend.services import exchange_leveling_service as _lvl
        _lvl.record_crypto_buy(uid, usd_value)
    except Exception:
        pass
    return {"success": True, "trade": trade, "wallet": get_wallet(uid), **captured}


def record_paypal_mn2_order(order_id: str, user_id: str, pack: Dict[str, Any], *, approve_url: str = "") -> Dict[str, Any]:
    order_id = (order_id or "").strip()
    uid = (user_id or "").strip()
    if not order_id or not uid:
        return {"success": False, "error": "order_id and user_id required"}
    pack_id = (pack.get("id") or "").strip()
    if not pack_id:
        return {"success": False, "error": "pack_id required"}
    pending = {
        "order_id": order_id,
        "user_id": uid,
        "pack": {
            "id": pack_id,
            "name": pack.get("name") or pack.get("label") or pack_id,
            "price_usd": float(pack.get("price_usd") or 0),
            "mn2_granted": float(pack.get("mn2_granted") or 0),
            "payment_rails": pack.get("payment_rails") or pack.get("rails") or ["paypal"],
        },
        "approve_url": approve_url,
        "created_at": _iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat().replace("+00:00", "Z"),
    }
    with _LOCK:
        rows = _read_json(_PAYPAL_MN2_ORDERS_PATH, {"pending": {}, "captured": {}})
        rows.setdefault("pending", {})[order_id] = pending
        _write_json(_PAYPAL_MN2_ORDERS_PATH, rows)
    return {"success": True, "order_id": order_id}


def fulfill_paypal_mn2_order(user_id: str, order_id: str, capture: Dict[str, Any]) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    order_id = (order_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    if not order_id:
        return {"success": False, "error": "order_id required"}
    with _LOCK:
        rows = _read_json(_PAYPAL_MN2_ORDERS_PATH, {"pending": {}, "captured": {}})
        if order_id in rows.get("captured", {}):
            prior = rows["captured"][order_id]
            return {"success": True, "duplicate": True, **prior}
        pending = (rows.get("pending") or {}).get(order_id)
        if not pending:
            return {"success": False, "error": "pending_order_not_found"}
        if str(pending.get("user_id") or "").strip() != uid:
            return {"success": False, "error": "order_user_mismatch"}
        expires = _parse_iso(pending.get("expires_at"))
        if expires and expires < datetime.now(timezone.utc):
            return {"success": False, "error": "order_expired"}
        pack = pending.get("pack") or {}
        capture_error = _validate_paypal_capture(capture, float(pack.get("price_usd") or 0))
        if capture_error:
            return {"success": False, "error": capture_error}

        from backend.services.shop_mn2_fulfillment_service import fulfill_mn2_purchase

        capture_id = capture.get("capture_id") or order_id
        pack_id = pack.get("id")
        grant = fulfill_mn2_purchase(
            uid,
            pack_id,
            1,
            source="exchange_paypal_mn2",
            reference=f"exchange_paypal_mn2:{capture_id}:{pack_id}",
            metadata={
                "order_id": order_id,
                "capture_id": capture_id,
                "amount_usd": capture.get("amount"),
                "currency": capture.get("currency") or "USD",
                "destination": "exchange_wallet",
            },
            item=pack,
        )
        if not grant.get("success"):
            return {"success": False, "error": grant.get("error", "MN2 fulfillment failed")}

        try:
            from backend.services.monetization_ledger_service import append_payment_event

            append_payment_event(
                provider="paypal",
                user_id=uid,
                order_id=order_id,
                capture_id=capture_id,
                amount_usd=float(capture.get("amount") or pack.get("price_usd") or 0),
                currency=capture.get("currency") or "USD",
                item_id=pack_id,
                item_name=pack.get("name") or pack_id,
                extra={"source": "exchange_paypal_mn2", "mn2_granted": grant.get("mn2_granted")},
            )
        except Exception:
            pass
        captured = {
            "user_id": uid,
            "pack_id": pack_id,
            "mn2_granted": float(grant.get("mn2_granted") or 0),
            "amount_usd": float(capture.get("amount") or pack.get("price_usd") or 0),
            "capture_id": capture_id,
            "captured_at": _iso(),
        }
        rows.setdefault("captured", {})[order_id] = captured
        rows.get("pending", {}).pop(order_id, None)
        _write_json(_PAYPAL_MN2_ORDERS_PATH, rows)
    _audit("paypal_mn2_capture", user_id=uid, amount_usd=float(capture.get("amount") or pack.get("price_usd") or 0), pack_id=pack_id, mn2_granted=float(grant.get("mn2_granted") or 0), order_id=order_id, capture_id=capture_id)
    return {"success": True, "order_id": order_id, **captured}


def quote_swap(user_id: str, symbol: str, side: str, amount: float, quote: str = "MN2") -> Dict[str, Any]:
    """side=buy: spend quote to receive symbol. side=sell: spend symbol to receive quote."""
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "exchange_disabled"}
    sym = (symbol or "").strip().upper()
    side = (side or "").strip().lower()
    quote = (quote or "MN2").strip().upper()
    if sym not in _asset_map(cfg):
        return {"success": False, "error": "unknown_asset"}
    if side not in ("buy", "sell"):
        return {"success": False, "error": "invalid_side"}
    amt = float(amount or 0)
    asset = _asset_map(cfg)[sym]
    if amt < float(asset.get("min_trade") or 0):
        return {"success": False, "error": "below_min_trade", "min_trade": asset.get("min_trade")}

    price_q = _price_in_quote(sym, quote, cfg)
    if price_q <= 0:
        return {"success": False, "error": "no_price"}

    spread_bps = int((cfg.get("platform_fees") or {}).get("swap_spread_bps") or 50)
    fee_bps = _fee_bps(side, False, cfg, user_id or "anon")
    total_bps = spread_bps + fee_bps

    if side == "buy":
        quote_cost = amt * price_q * (1 + total_bps / 10000)
        fee_quote = amt * price_q * (total_bps / 10000)
    else:
        quote_out = amt * price_q * (1 - total_bps / 10000)
        fee_quote = amt * price_q * (total_bps / 10000)
        quote_cost = 0
        quote_out = quote_out

    usd_val = amt * _price_usd(sym, cfg)
    qid = uuid.uuid4().hex[:16]
    payload = {
        "success": True,
        "quote_id": qid,
        "symbol": sym,
        "side": side,
        "amount": amt,
        "quote_currency": quote,
        "price_quote": round(price_q, 8),
        "fee_quote": round(fee_quote, 8),
        "fee_bps": total_bps,
        "usd_value": round(usd_val, 4),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
    }
    if side == "buy":
        payload["quote_cost"] = round(quote_cost, 8)
    else:
        payload["quote_received"] = round(quote_out, 8)
    return payload


def execute_swap(user_id: str, quote_id: str, symbol: str, side: str, amount: float, quote: str = "MN2") -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    q = quote_swap(uid, symbol, side, amount, quote)
    if not q.get("success"):
        return q

    sym = q["symbol"]
    side = q["side"]
    amt = float(q["amount"])
    quote_cur = q["quote_currency"]
    ref = f"ex-swap:{quote_id}:{uuid.uuid4().hex[:8]}"
    meta = {"reference": ref, "quote_id": quote_id, "symbol": sym, "side": side}

    try:
        with _LOCK:
            if side == "buy":
                cost = float(q.get("quote_cost") or 0)
                bal = _get_quote_balance(uid, quote_cur)
                if bal < cost:
                    return {"success": False, "error": f"insufficient_{quote_cur.lower()}"}
                _adjust_quote_balance(uid, quote_cur, -cost, "exchange_buy", meta)
                _adjust_balance(uid, sym, amt)
            else:
                if _get_balance(uid, sym) < amt:
                    return {"success": False, "error": f"insufficient_{sym.lower()}"}
                received = float(q.get("quote_received") or 0)
                _adjust_balance(uid, sym, -amt)
                _adjust_quote_balance(uid, quote_cur, received, "exchange_sell", meta)

            fee_mn2 = _fee_quote_to_mn2(float(q.get("fee_quote") or 0), quote_cur, load_config())
            _collect_fee(fee_mn2)
            _add_volume(uid, float(q.get("usd_value") or 0))
            _record_tax(uid, sym, side, amt, float(q.get("usd_value") or 0), _fee_quote_to_usd(float(q.get("fee_quote") or 0), quote_cur, load_config()))

            trade = {
                "ts": _iso(), "trade_id": ref, "user_id": uid, "type": "swap",
                "symbol": sym, "side": side, "amount": amt, "quote": quote_cur,
                "usd_value": q.get("usd_value"), "fee_bps": q.get("fee_bps"),
            }
            _append_jsonl(_TRADES_PATH, trade)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}

    _emit("exchange_swap", channel="exchange", user_id=uid, payload=trade)
    _audit("swap", user_id=uid, amount_usd=float(q.get("usd_value") or 0), symbol=sym, side=side, amount=amt, quote=quote_cur, trade_id=ref)
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = float(q.get("usd_value") or 0) * float((load_config().get("rewards") or {}).get("trade_activity_points_per_usd") or 0.5)
        if pts > 0:
            unified_points_db.add_points(uid, "activity_points", pts, source="exchange_trade", metadata=meta)
    except Exception:
        pass

    return {"success": True, "trade": trade, "wallet": get_wallet(uid)}


def _read_orders() -> List[dict]:
    rows = _read_json(_ORDERS_PATH, [])
    return rows if isinstance(rows, list) else []


def _write_orders(rows: List[dict]) -> None:
    _write_json(_ORDERS_PATH, rows)


def create_limit_order(user_id: str, symbol: str, side: str, amount: float, limit_price: float, quote: str = "MN2") -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    cfg = load_config()
    sym = (symbol or "").upper()
    side = (side or "").lower()
    quote = (quote or "MN2").upper()
    amt = float(amount or 0)
    price = float(limit_price or 0)
    if sym not in _asset_map(cfg) or side not in ("buy", "sell") or amt <= 0 or price <= 0:
        return {"success": False, "error": "invalid_order"}

    with _LOCK:
        ref = f"ex-order:{uuid.uuid4().hex[:12]}"
        if side == "sell":
            if _get_balance(uid, sym) < amt:
                return {"success": False, "error": f"insufficient_{sym.lower()}"}
            _adjust_balance(uid, sym, -amt)
        else:
            cost = amt * price
            if _get_quote_balance(uid, quote) < cost:
                return {"success": False, "error": f"insufficient_{quote.lower()}"}
            _adjust_quote_balance(uid, quote, -cost, "exchange_order_lock", {"reference": ref})

        order = {
            "order_id": uuid.uuid4().hex[:16],
            "user_id": uid,
            "symbol": sym,
            "side": side,
            "amount": amt,
            "remaining": amt,
            "limit_price": price,
            "quote": quote,
            "status": "open",
            "created_at": _iso(),
            "lock_ref": ref,
        }
        rows = _read_orders()
        rows.append(order)
        _write_orders(rows)

    _try_match(order)
    return {"success": True, "order": order}


def _try_match(new_order: dict) -> None:
    """Simple price-time matching against opposite side."""
    sym = new_order.get("symbol")
    quote = new_order.get("quote")
    side = new_order.get("side")
    opp = "sell" if side == "buy" else "buy"
    rows = _read_orders()
    candidates = [
        o for o in rows
        if o.get("status") == "open" and o.get("symbol") == sym and o.get("quote") == quote and o.get("side") == opp
    ]
    if side == "buy":
        candidates.sort(key=lambda o: float(o.get("limit_price") or 0))
    else:
        candidates.sort(key=lambda o: float(o.get("limit_price") or 0), reverse=True)

    for c in candidates:
        if new_order.get("status") != "open" or float(new_order.get("remaining") or 0) <= 0:
            break
        if side == "buy" and float(c.get("limit_price") or 0) > float(new_order.get("limit_price") or 0):
            break
        if side == "sell" and float(c.get("limit_price") or 0) < float(new_order.get("limit_price") or 0):
            break
        _fill_between(new_order, c)


def _fill_between(buy_order: dict, sell_order: dict) -> None:
    if buy_order.get("side") == "sell":
        buy_order, sell_order = sell_order, buy_order
    fill = min(float(buy_order.get("remaining") or 0), float(sell_order.get("remaining") or 0))
    if fill <= 0:
        return
    price = float(sell_order.get("limit_price") or 0)
    quote_total = fill * price
    cfg = load_config()
    buyer = buy_order.get("user_id")
    seller = sell_order.get("user_id")
    sym = buy_order.get("symbol")
    quote = buy_order.get("quote")
    fee_bps = _fee_bps("buy", True, cfg, buyer)
    fee = quote_total * fee_bps / 10000
    seller_receives = quote_total - fee

    ref = f"ex-match:{uuid.uuid4().hex[:10]}"
    meta = {"reference": ref, "buy_order": buy_order.get("order_id"), "sell_order": sell_order.get("order_id")}

    _adjust_balance(buyer, sym, fill)
    _adjust_quote_balance(seller, quote, seller_receives, "exchange_fill", meta)
    _collect_fee(fee if quote == "MN2" else fee / max(float(_read_json(os.path.join(_BASE, "data", "mn2_config.json"), {}).get("coins_per_mn2") or 100), 1))

    usd = fill * _price_usd(sym, cfg)
    _add_volume(buyer, usd)
    _add_volume(seller, usd)
    _record_tax(buyer, sym, "buy", fill, usd, fee * _mn2_usd())
    _record_tax(seller, sym, "sell", fill, usd, fee * _mn2_usd())

    buy_order["remaining"] = round(float(buy_order.get("remaining") or 0) - fill, 12)
    sell_order["remaining"] = round(float(sell_order.get("remaining") or 0) - fill, 12)
    if buy_order["remaining"] <= 0:
        buy_order["status"] = "filled"
    if sell_order["remaining"] <= 0:
        sell_order["status"] = "filled"

    trade = {"ts": _iso(), "trade_id": ref, "symbol": sym, "amount": fill, "price": price, "quote": quote, "buyer": buyer, "seller": seller, "fee": fee, "type": "limit"}
    _append_jsonl(_TRADES_PATH, trade)
    rows = _read_orders()
    for i, o in enumerate(rows):
        if o.get("order_id") == buy_order.get("order_id"):
            rows[i] = buy_order
        elif o.get("order_id") == sell_order.get("order_id"):
            rows[i] = sell_order
    _write_orders(rows)


def list_orders(symbol: Optional[str] = None, side: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    rows = [o for o in _read_orders() if o.get("status") == "open"]
    if symbol:
        rows = [o for o in rows if o.get("symbol") == symbol.upper()]
    if side:
        rows = [o for o in rows if o.get("side") == side.lower()]
    return {"success": True, "orders": rows[:limit]}


def cancel_order(user_id: str, order_id: str) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    with _LOCK:
        rows = _read_orders()
        order = next((o for o in rows if o.get("order_id") == order_id and o.get("status") == "open"), None)
        if not order:
            return {"success": False, "error": "order_not_found"}
        if order.get("user_id") != uid:
            return {"success": False, "error": "not_owner"}
        rem = float(order.get("remaining") or 0)
        sym = order.get("symbol")
        quote = order.get("quote")
        if order.get("side") == "sell" and rem > 0:
            _adjust_balance(uid, sym, rem)
        elif order.get("side") == "buy" and rem > 0:
            _adjust_quote_balance(uid, quote, rem * float(order.get("limit_price") or 0), "exchange_order_unlock", {"order_id": order_id})
        order["status"] = "cancelled"
        order["cancelled_at"] = _iso()
        _write_orders(rows)
    return {"success": True, "order": order}


def list_trades(limit: int = 30) -> Dict[str, Any]:
    limit = max(1, min(int(limit or 30), 200))
    if not os.path.isfile(_TRADES_PATH):
        return {"success": True, "trades": []}
    rows = []
    with open(_TRADES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return {"success": True, "trades": rows[-limit:][::-1]}


def claim_welcome_bonus(user_id: str, terms_version: str, accepted: bool) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    cfg = load_config()
    bonus = cfg.get("lawful_bonus") or {}
    if not bonus.get("enabled"):
        return {"success": False, "error": "bonus_disabled"}
    if not accepted:
        return {"success": False, "error": "terms_required"}
    if terms_version != bonus.get("terms_version"):
        return {"success": False, "error": "terms_version_mismatch", "expected": bonus.get("terms_version")}

    claims = _read_json(_BONUS_PATH, {})
    user_claims = claims.get(uid) or []
    if len(user_claims) >= int(bonus.get("max_claims_per_user") or 1):
        return {"success": False, "error": "already_claimed"}

    mn2_amt = float(bonus.get("mn2_amount") or 0)
    hold_until = (datetime.now(timezone.utc) + timedelta(days=int(bonus.get("hold_days_before_withdraw") or 7))).isoformat().replace("+00:00", "Z")
    ref = f"ex-bonus:{bonus.get('id')}:{uuid.uuid4().hex[:8]}"

    with _LOCK:
        from backend.services.unified_points_database import unified_points_db
        unified_points_db.add_points(uid, "mn2_balance", mn2_amt, source="exchange_welcome_bonus", metadata={"reference": ref, "hold_until": hold_until, "terms_version": terms_version})
        path = _wallet_path(uid)
        w = _read_json(path, {"assets": {}, "staking": {}, "bonus": {}, "volume_usd_30d": 0})
        w.setdefault("bonus", {})["welcome"] = {"claimed_at": _iso(), "mn2_amount": mn2_amt, "hold_until": hold_until, "terms_version": terms_version}
        _save_wallet(uid, w)
        user_claims.append({"claimed_at": _iso(), "mn2_amount": mn2_amt, "ref": ref})
        claims[uid] = user_claims
        _write_json(_BONUS_PATH, claims)

    return {"success": True, "bonus_mn2": mn2_amt, "hold_until": hold_until, "terms_version": terms_version}


def claim_staking_rewards(user_id: str, symbol: str) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid}

    sym = (symbol or "").strip().upper()
    asset = _asset_map().get(sym)
    if not asset:
        return {"success": False, "error": "unknown_asset"}
    apy_bps = int(asset.get("staking_apy_bps") or 0)
    if apy_bps <= 0:
        return {"success": False, "error": "not_stakeable"}

    bal = _get_balance(uid, sym)
    if bal <= 0:
        return {"success": False, "error": "no_balance_to_stake"}

    path = _wallet_path(uid)
    w = _read_json(path, {"assets": {}, "staking": {}, "bonus": {}, "volume_usd_30d": 0})
    staking = w.setdefault("staking", {})
    last = staking.get(sym)
    now = datetime.now(timezone.utc)
    if last:
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if (now - last_dt).total_seconds() < 86400:
                return {"success": False, "error": "claim_once_per_day"}
        except Exception:
            pass

    daily_rate = apy_bps / 10000 / 365
    reward = bal * daily_rate
    if reward <= 0:
        return {"success": False, "error": "reward_too_small"}

    _adjust_balance(uid, sym, reward)
    staking[sym] = _iso()
    _save_wallet(uid, w)
    return {"success": True, "symbol": sym, "reward": round(reward, 12), "apy_bps": apy_bps}


def get_tax_report(user_id: str, year: Optional[int] = None) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    year = year or datetime.now(timezone.utc).year
    rows = []
    if os.path.isfile(_TAX_PATH):
        with open(_TAX_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    if r.get("user_id") == uid and str(r.get("ts", "")).startswith(str(year)):
                        rows.append(r)
                except Exception:
                    pass
    total_taxable = sum(float(r.get("taxable_gain_usd") or 0) for r in rows)
    total_fees = sum(float(r.get("fee_usd") or 0) for r in rows)
    cfg = load_config()
    rate_bps = int((cfg.get("tax") or {}).get("capital_gains_rate_bps") or 0)
    return {
        "success": True,
        "user_id": uid,
        "year": year,
        "jurisdiction": (cfg.get("tax") or {}).get("jurisdiction_label"),
        "disclaimer": (cfg.get("tax") or {}).get("disclaimer"),
        "trade_count": len(rows),
        "total_taxable_gain_usd": round(total_taxable, 2),
        "total_fees_usd": round(total_fees, 2),
        "reference_rate_bps": rate_bps,
        "estimated_tax_usd": round(total_taxable * rate_bps / 10000, 2),
        "records": rows,
    }


def get_rewards_status(user_id: str) -> Dict[str, Any]:
    w = get_wallet(user_id)
    if not w.get("success"):
        return w
    cfg = load_config()
    vol = float(w.get("volume_usd_30d") or 0)
    tier = {"label": "Bronze", "fee_rebate_bps": 0}
    for t in sorted((cfg.get("rewards") or {}).get("volume_tiers") or [], key=lambda x: x.get("min_volume_usd", 0), reverse=True):
        if vol >= float(t.get("min_volume_usd") or 0):
            tier = t
            break
    bonus_cfg = cfg.get("lawful_bonus") or {}
    claims = _read_json(_BONUS_PATH, {})
    claimed = user_id in claims and len(claims[user_id]) >= int(bonus_cfg.get("max_claims_per_user") or 1)
    return {
        "success": True,
        "volume_usd_30d": vol,
        "tier": tier,
        "welcome_bonus_claimed": claimed,
        "welcome_bonus_available": bonus_cfg.get("enabled") and not claimed,
        "maker_rebate_bps": (cfg.get("rewards") or {}).get("maker_rebate_bps"),
    }


def _portfolio_value_usd(assets: Dict[str, Any], cfg: Optional[Dict] = None) -> float:
    cfg = cfg or load_config()
    total = 0.0
    for sym, raw in (assets or {}).items():
        try:
            total += float(raw or 0) * _price_usd(str(sym).upper(), cfg)
        except (TypeError, ValueError):
            continue
    return round(total, 4)


def _wallet_rankings(user_id: str, cfg: Optional[Dict] = None) -> Dict[str, Any]:
    cfg = cfg or load_config()
    rows = []
    if os.path.isdir(_WALLETS_DIR):
        for name in os.listdir(_WALLETS_DIR):
            if not name.endswith(".json"):
                continue
            uid = name[:-5]
            data = _read_json(os.path.join(_WALLETS_DIR, name), {})
            assets = data.get("assets") if isinstance(data.get("assets"), dict) else {}
            rows.append({
                "user_id": uid,
                "portfolio_value_usd": _portfolio_value_usd(assets, cfg),
                "volume_usd_30d": float(data.get("volume_usd_30d") or 0),
                "asset_count": len([v for v in assets.values() if float(v or 0) > 0]),
            })
    if not rows:
        return {
            "portfolio_rank": None,
            "volume_rank": None,
            "portfolio_leaderboard": [],
            "volume_leaderboard": [],
        }

    by_portfolio = sorted(rows, key=lambda r: r["portfolio_value_usd"], reverse=True)
    by_volume = sorted(rows, key=lambda r: r["volume_usd_30d"], reverse=True)

    def rank(rows_: List[dict]) -> Optional[int]:
        for i, row in enumerate(rows_, 1):
            if row.get("user_id") == user_id:
                return i
        return None

    return {
        "portfolio_rank": rank(by_portfolio),
        "volume_rank": rank(by_volume),
        "portfolio_leaderboard": by_portfolio[:10],
        "volume_leaderboard": by_volume[:10],
    }


def get_user_progress_report(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    cfg = load_config()
    wallet = get_wallet(uid)
    assets = wallet.get("assets") or {}
    portfolio_value = _portfolio_value_usd(assets, cfg)
    volume = float(wallet.get("volume_usd_30d") or 0)
    rewards = get_rewards_status(uid)
    rankings = _wallet_rankings(uid, cfg)
    orders = list_orders(limit=200).get("orders") or []
    user_orders = [o for o in orders if o.get("user_id") == uid]
    trades = list_trades(limit=200).get("trades") or []
    user_trades = [
        t for t in trades
        if t.get("user_id") == uid or t.get("buyer") == uid or t.get("seller") == uid
    ]

    tier = rewards.get("tier") if isinstance(rewards.get("tier"), dict) else {"label": "Bronze", "min_volume_usd": 0}
    tiers = sorted((cfg.get("rewards") or {}).get("volume_tiers") or [], key=lambda t: float(t.get("min_volume_usd") or 0))
    next_tier = None
    for row in tiers:
        if float(row.get("min_volume_usd") or 0) > volume:
            next_tier = row
            break
    next_goal = float((next_tier or {}).get("min_volume_usd") or volume or 1)
    tier_progress = 100.0 if not next_tier else max(0.0, min(100.0, (volume / next_goal) * 100.0))

    status_items = []
    if not assets:
        status_items.append({"level": "info", "text": "No exchange assets yet. Use PayPal buy or instant swap to start."})
    if user_orders:
        status_items.append({"level": "active", "text": f"{len(user_orders)} open limit order(s) on the book."})
    if rewards.get("welcome_bonus_available"):
        status_items.append({"level": "bonus", "text": "Welcome bonus is still available."})
    if next_tier:
        status_items.append({
            "level": "progress",
            "text": f"${max(0.0, next_goal - volume):.2f} volume until {next_tier.get('label')} tier.",
        })
    else:
        status_items.append({"level": "max", "text": "Top fee tier reached for current config."})

    return {
        "success": True,
        "user_id": uid,
        "portfolio_value_usd": portfolio_value,
        "asset_count": len([v for v in assets.values() if float(v or 0) > 0]),
        "volume_usd_30d": volume,
        "tier": tier,
        "next_tier": next_tier,
        "tier_progress_pct": round(tier_progress, 2),
        "trade_count": len(user_trades),
        "open_order_count": len(user_orders),
        "high_scores": {
            "portfolio_rank": rankings.get("portfolio_rank"),
            "volume_rank": rankings.get("volume_rank"),
            "portfolio_leaderboard": rankings.get("portfolio_leaderboard") or [],
            "volume_leaderboard": rankings.get("volume_leaderboard") or [],
        },
        "status_items": status_items,
        "recent_trades": user_trades[:10],
        "generated_at": _iso(),
    }


def deposit_from_mn2(user_id: str, symbol: str, mn2_amount: float) -> Dict[str, Any]:
    """Convert MN2 platform balance into exchange asset (instant at market price)."""
    price = max(_price_in_quote(symbol, "MN2"), 1e-12)
    asset_amt = float(mn2_amount) / price
    return execute_swap(user_id, uuid.uuid4().hex[:16], symbol, "buy", asset_amt, "MN2")


def health() -> Dict[str, Any]:
    cfg = load_config()
    tre = _read_json(_TREASURY_PATH, {})
    return {
        "success": True,
        "service": "crypto_exchange",
        "status": "healthy" if cfg.get("enabled", True) else "disabled",
        "asset_count": len(cfg.get("assets") or []),
        "treasury_fees_mn2": tre.get("total_fees_mn2"),
        "timestamp": _iso(),
    }
