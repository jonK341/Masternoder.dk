"""Profit payout — wire realized exchange profit to owner PayPal (or Binance stash).

Primary owner rail: PayPal Payouts to ``EXCHANGE_PAYOUT_PAYPAL_EMAIL`` (or config).
Optional secondary: Binance USDT withdraw from sales pool via signed capital API.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_binance_withdraw_service import (
    binance_credentials,
    binance_withdraw_live_enabled,
    get_spot_usdt_free,
    mask_address,
    preflight_withdraw_usdt,
    withdraw_usdt,
)

_PAYOUT_PATH = os.path.join(ex._DATA_DIR, "payout_config.json")
_SWEEPS_PATH = os.path.join(ex._DATA_DIR, "payout_sweeps.jsonl")

_BINANCE_KEY = "binance_api_key"
_BINANCE_SECRET = "binance_api_secret"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _owner_paypal_email(cfg: Optional[Dict[str, Any]] = None) -> str:
    env_email = (os.environ.get("EXCHANGE_PAYOUT_PAYPAL_EMAIL") or "").strip()
    if env_email:
        return env_email
    cfg = cfg or _load()
    return str((cfg.get("paypal") or {}).get("email") or "").strip()


def _paypal_share_pct(cfg: Dict[str, Any]) -> float:
    env_pct = os.environ.get("EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT")
    if env_pct is not None and str(env_pct).strip() != "":
        try:
            v = float(env_pct)
            return max(0.0, min(1.0, v / 100.0 if v > 1 else v))
        except (TypeError, ValueError):
            pass
    try:
        v = float((cfg.get("paypal") or {}).get("share_pct", 1.0))
        return max(0.0, min(1.0, v))
    except (TypeError, ValueError):
        return 1.0


def _paypal_live_enabled(*, skip_spork: bool = False) -> bool:
    if os.environ.get("EXCHANGE_PAYOUT_PAYPAL_LIVE", "").strip() not in ("1", "true", "yes"):
        return False
    if not skip_spork:
        try:
            from backend.services import mn2_spork_service as spork
            ok, _reason = spork.payout_live_spork_ok()
            if not ok:
                return False
        except Exception:
            pass
    cid = (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
    secret = (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
    return bool(cid and secret and _owner_paypal_email())


def _default_binance_cfg() -> Dict[str, Any]:
    return {
        "connected": False,
        "account_label": "",
        "deposit_addresses": {},
        "withdraw_address": "",
        "withdraw_network": "TRC20",
        "withdraw_enabled": False,
        "max_withdraw_per_day_usdt": 10000.0,
        "withdrawn_today_usdt": 0.0,
        "withdraw_day": "",
    }


def _binance_withdraw_address(cfg: Optional[Dict[str, Any]] = None) -> str:
    env_addr = (os.environ.get("EXCHANGE_PAYOUT_BINANCE_ADDRESS") or "").strip()
    if env_addr:
        return env_addr
    cfg = cfg or _load()
    return str((cfg.get("binance") or {}).get("withdraw_address") or "").strip()


def _binance_withdraw_network(cfg: Optional[Dict[str, Any]] = None) -> str:
    env_net = (os.environ.get("EXCHANGE_PAYOUT_BINANCE_NETWORK") or "").strip()
    if env_net:
        return env_net.upper()
    cfg = cfg or _load()
    return str((cfg.get("binance") or {}).get("withdraw_network") or "TRC20").upper()


def _min_sweep_usd(cfg: Optional[Dict[str, Any]] = None) -> float:
    env_min = os.environ.get("EXCHANGE_AUTO_SWEEP_MIN_USD", "").strip()
    if env_min:
        try:
            return max(0.0, float(env_min))
        except (TypeError, ValueError):
            pass
    cfg = cfg or _load()
    return float(cfg.get("min_sweep_usd") or 5.0)


def _load() -> Dict[str, Any]:
    cfg = ex._read_json(_PAYOUT_PATH, None)
    if not isinstance(cfg, dict):
        cfg = {
            "destination": "paypal",
            "paypal": {"email": "", "share_pct": 1.0, "connected": False},
            "binance": _default_binance_cfg(),
            "stash_asset": "USDT",
            "min_sweep_usd": 5.0,
            "auto_sweep": False,
            "swept_total_usd": 0.0,
        }
        ex._write_json(_PAYOUT_PATH, cfg)
    cfg.setdefault("paypal", {"email": "", "share_pct": 1.0, "connected": False})
    b = cfg.setdefault("binance", _default_binance_cfg())
    for k, v in _default_binance_cfg().items():
        b.setdefault(k, v)
    cfg.setdefault("swept_total_usd", 0.0)
    cfg.setdefault("stash_asset", "USDT")
    cfg.setdefault("min_sweep_usd", 5.0)
    env_addr = _binance_withdraw_address(cfg)
    if env_addr:
        b["withdraw_address"] = env_addr
        b["withdraw_enabled"] = True
    env_net = (os.environ.get("EXCHANGE_PAYOUT_BINANCE_NETWORK") or "").strip()
    if env_net:
        b["withdraw_network"] = env_net.upper()
    if _owner_paypal_email(cfg):
        cfg["destination"] = "paypal"
        cfg["paypal"]["email"] = _owner_paypal_email(cfg)
        cfg["paypal"]["connected"] = True
    return cfg


def _save(cfg: Dict[str, Any]) -> None:
    cfg["updated_at"] = _iso()
    ex._write_json(_PAYOUT_PATH, cfg)


def _live_enabled() -> bool:
    try:
        from backend.services import mn2_spork_service as spork
        ok, _reason = spork.payout_live_spork_ok()
        if not ok:
            return False
    except Exception:
        pass
    try:
        from backend.services.exchange_arbitrage_service import live_enabled
        return live_enabled()
    except Exception:
        return False


def _realized_total_usd() -> float:
    try:
        from backend.services.trading_bots_control_service import business_overview
        return float(business_overview().get("totals", {}).get("total_realized_pnl_usd") or 0)
    except Exception:
        return 0.0


def _treasury_stashed_usd() -> float:
    try:
        from backend.services.exchange_treasury_service import treasury_status
        return float(treasury_status().get("ledger_stashed_usd") or 0)
    except Exception:
        return 0.0


def _treasury_stashed_usd_by_mode(mode: str) -> float:
    try:
        from backend.services.exchange_treasury_service import treasury_status
        st = treasury_status()
        if str(mode).lower() == "live":
            return float(st.get("ledger_stashed_usd_live") or st.get("live_stash_usd") or 0)
        return float(st.get("ledger_stashed_usd_paper") or 0)
    except Exception:
        return 0.0


def _sweep_ledger_mode() -> str:
    """Treasury ledger rows included in the next sweep (live PayPal → live rows only)."""
    return "live" if _paypal_live_enabled() else "paper"


def _swept_total_for_mode(cfg: Dict[str, Any], mode: str) -> float:
    key = f"swept_total_usd_{mode}"
    if key in cfg:
        return float(cfg.get(key) or 0)
    if mode == "paper":
        return float(cfg.get("swept_total_usd") or 0)
    return 0.0


def _sweep_pool_usd() -> float:
    """Treasury stash available to sweep — never agent paper PnL totals."""
    return round(_treasury_stashed_usd_by_mode(_sweep_ledger_mode()), 4)


def _net_unswept_usd(cfg: Dict[str, Any]) -> float:
    mode = _sweep_ledger_mode()
    pool = _treasury_stashed_usd_by_mode(mode)
    swept = _swept_total_for_mode(cfg, mode)
    return round(max(0.0, pool - swept), 4)


def configure_paypal(email: str, *, share_pct: Optional[float] = None) -> Dict[str, Any]:
    email = (email or "").strip()
    if not email or "@" not in email:
        return {"success": False, "error": "valid_paypal_email_required"}
    cfg = _load()
    cfg["destination"] = "paypal"
    cfg["paypal"]["email"] = email
    cfg["paypal"]["connected"] = True
    if share_pct is not None:
        try:
            pct = float(share_pct)
            cfg["paypal"]["share_pct"] = max(0.0, min(1.0, pct / 100.0 if pct > 1 else pct))
        except (TypeError, ValueError):
            pass
    _save(cfg)
    ex._audit("payout_paypal_configured", user_id="owner", email=email,
              share_pct=cfg["paypal"].get("share_pct"))
    return {"success": True, "email": email, "share_pct": cfg["paypal"].get("share_pct")}


def configure_binance(api_key: str, api_secret: str, *,
                      deposit_addresses: Optional[Dict[str, str]] = None,
                      account_label: str = "primary",
                      withdraw_address: str = "",
                      network: str = "",
                      withdraw_enabled: Optional[bool] = None,
                      max_withdraw_per_day: Optional[float] = None) -> Dict[str, Any]:
    from backend.services import exchange_secrets_vault_service as vault

    stored_keys = False
    if api_key and api_secret:
        r1 = vault.set_secret(_BINANCE_KEY, api_key)
        r2 = vault.set_secret(_BINANCE_SECRET, api_secret)
        stored_keys = bool(r1.get("success") and r2.get("success"))
        if not stored_keys:
            return {"success": False, "error": r1.get("error") or r2.get("error") or "vault_unavailable",
                    "hint": "Set EXCHANGE_VAULT_KEY and install 'cryptography' to store Binance keys."}

    cfg = _load()
    addrs = {str(k).upper(): str(v) for k, v in (deposit_addresses or {}).items() if v}
    cfg["binance"]["account_label"] = account_label
    cfg["binance"]["deposit_addresses"] = {**(cfg["binance"].get("deposit_addresses") or {}), **addrs}
    cfg["binance"]["connected"] = bool(stored_keys or cfg["binance"].get("connected"))
    waddr = (withdraw_address or "").strip()
    if waddr:
        cfg["binance"]["withdraw_address"] = waddr
        cfg["binance"]["withdraw_enabled"] = True
    if (network or "").strip():
        cfg["binance"]["withdraw_network"] = str(network).strip().upper()
    if withdraw_enabled is not None:
        cfg["binance"]["withdraw_enabled"] = bool(withdraw_enabled)
    if max_withdraw_per_day is not None:
        try:
            cfg["binance"]["max_withdraw_per_day_usdt"] = max(0.0, float(max_withdraw_per_day))
        except (TypeError, ValueError):
            pass
    if not _owner_paypal_email(cfg):
        cfg["destination"] = "binance"
    _save(cfg)

    for asset, addr in addrs.items():
        try:
            vault.register_wallet(f"binance_{asset.lower()}", addr, venue="binance", asset=asset, note="payout stash")
        except Exception:
            pass
    if waddr:
        try:
            vault.register_wallet("binance_withdraw_usdt", waddr, venue="binance", asset="USDT",
                                  note=f"payout withdraw {_binance_withdraw_network(cfg)}")
        except Exception:
            pass
    ex._audit("payout_binance_configured", user_id="owner", account_label=account_label,
              assets=list(addrs.keys()), keys_stored=stored_keys,
              withdraw_address_masked=mask_address(waddr) if waddr else None,
              network=cfg["binance"].get("withdraw_network"))
    return {
        "success": True,
        "connected": cfg["binance"]["connected"],
        "deposit_assets": list(cfg["binance"]["deposit_addresses"].keys()),
        "withdraw_address_masked": mask_address(_binance_withdraw_address(cfg)),
        "withdraw_network": _binance_withdraw_network(cfg),
        "withdraw_enabled": bool(cfg["binance"].get("withdraw_enabled")),
    }


def _sales_pool_usdt() -> float:
    try:
        from backend.services.exchange_sales_pool_service import sales_pool_user_id
        pool_uid = sales_pool_user_id()
        assets = (ex.get_wallet(pool_uid).get("assets") or {})
        return round(float(assets.get("USDT") or 0), 8)
    except Exception:
        return 0.0


def _reset_daily_withdraw_counter(cfg: Dict[str, Any]) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    b = cfg.setdefault("binance", _default_binance_cfg())
    if b.get("withdraw_day") != today:
        b["withdraw_day"] = today
        b["withdrawn_today_usdt"] = 0.0


def _daily_withdraw_remaining(cfg: Dict[str, Any]) -> Optional[float]:
    b = cfg.get("binance") or {}
    cap = b.get("max_withdraw_per_day_usdt")
    if cap is None:
        return None
    try:
        cap_f = float(cap)
    except (TypeError, ValueError):
        return None
    if cap_f <= 0:
        return None
    _reset_daily_withdraw_counter(cfg)
    used = float(b.get("withdrawn_today_usdt") or 0)
    return round(max(0.0, cap_f - used), 8)


def payout_monitor_snapshot() -> Dict[str, Any]:
    """Fast payout fields for profit daemon monitor — no venue RPC or business overview."""
    cfg = _load()
    ledger_mode = "live" if _paypal_live_enabled(skip_spork=True) else "paper"
    try:
        from backend.services.exchange_treasury_service import treasury_status
        st = treasury_status()
        pool = float(st.get("ledger_stashed_usd_live") or 0) if ledger_mode == "live" else float(
            st.get("ledger_stashed_usd_paper") or 0
        )
    except Exception:
        pool = 0.0
    swept = _swept_total_for_mode(cfg, ledger_mode)
    net = round(max(0.0, pool - swept), 4)
    paypal_email = _owner_paypal_email(cfg)
    share = _paypal_share_pct(cfg)
    sweepable = round(net * share, 4) if paypal_email else net
    dest = str(cfg.get("destination") or ("paypal" if paypal_email else "binance"))
    min_usd = _min_sweep_usd(cfg)
    paypal_live = _paypal_live_enabled(skip_spork=True)
    pay_mode = "live" if (paypal_live if dest == "paypal" else False) else "paper"
    return {
        "success": True,
        "destination": dest,
        "mode": pay_mode,
        "auto_sweep": bool(cfg.get("auto_sweep")),
        "min_sweep_usd": min_usd,
        "paypal": {
            "email": paypal_email,
            "connected": bool(paypal_email),
            "share_pct": round(share * 100, 2),
            "live_enabled": paypal_live,
        },
        "sweep_ledger_mode": ledger_mode,
        "sweep_pool_usd": round(pool, 4),
        "net_unswept_usd": net,
        "paypal_sweepable_usd": sweepable,
        "ready_to_sweep": bool(paypal_email and sweepable >= min_usd),
    }


def payout_status(*, light: bool = False) -> Dict[str, Any]:
    if light:
        return payout_monitor_snapshot()

    from backend.services import exchange_secrets_vault_service as vault

    cfg = _load()
    ledger_mode = _sweep_ledger_mode()
    realized = _realized_total_usd()
    pool = _sweep_pool_usd()
    net = _net_unswept_usd(cfg)
    swept = _swept_total_for_mode(cfg, ledger_mode)
    names = vault.list_secret_names()
    keys_present = _BINANCE_KEY in names and _BINANCE_SECRET in names
    if not keys_present:
        creds = binance_credentials()
        keys_present = bool(creds.get("api_key") and creds.get("api_secret"))
    addrs = cfg["binance"].get("deposit_addresses") or {}
    paypal_email = _owner_paypal_email(cfg)
    share = _paypal_share_pct(cfg)
    sweepable = round(net * share, 4) if paypal_email else net
    dest = str(cfg.get("destination") or ("paypal" if paypal_email else "binance"))
    min_usd = _min_sweep_usd(cfg)
    paypal_ready = bool(paypal_email and sweepable >= min_usd)
    waddr = _binance_withdraw_address(cfg)
    wnet = _binance_withdraw_network(cfg)
    w_enabled = bool(cfg["binance"].get("withdraw_enabled") or waddr)
    binance_ready = bool(keys_present and (addrs or waddr) and net >= min_usd)
    pool_usdt = _sales_pool_usdt()
    daily_left = _daily_withdraw_remaining(cfg)
    binance_spot_usdt_free: Optional[float] = None
    withdraw_preflight: Optional[Dict[str, Any]] = None
    if not light and keys_present and waddr:
        spot_res = get_spot_usdt_free(skip_live_gate=True)
        if spot_res.get("success") or spot_res.get("simulated"):
            binance_spot_usdt_free = float(spot_res.get("free") or 0)
        pf_amount = round(min(float(min_usd), pool_usdt if pool_usdt >= min_usd else min_usd), 8)
        pf = preflight_withdraw_usdt(
            pf_amount, waddr, wnet, skip_live_gate=True, sales_pool_usdt=pool_usdt,
        )
        withdraw_preflight = {
            "ready": pf.get("ready"),
            "amount_usdt": pf.get("amount_usdt"),
            "spot_usdt_free": pf.get("spot_usdt_free"),
            "network_fee_usdt": pf.get("network_fee_usdt"),
            "required_spot_usdt": pf.get("required_spot_usdt"),
            "blockers": pf.get("blockers") or [],
        }
    return {
        "success": True,
        "destination": dest,
        "paypal": {
            "email": paypal_email,
            "connected": bool(paypal_email),
            "share_pct": round(share * 100, 2),
            "live_enabled": _paypal_live_enabled(),
        },
        "binance": {
            "connected": bool(cfg["binance"].get("connected")),
            "keys_present": keys_present,
            "deposit_assets": list(addrs.keys()),
            "withdraw_address_masked": mask_address(waddr),
            "withdraw_network": wnet,
            "withdraw_enabled": w_enabled,
            "withdraw_live_enabled": binance_withdraw_live_enabled(),
            "wired": bool(keys_present and waddr and wnet and w_enabled),
            "sales_pool_usdt": pool_usdt,
            "binance_spot_usdt_free": binance_spot_usdt_free,
            "withdraw_preflight": withdraw_preflight,
            "max_withdraw_per_day_usdt": cfg["binance"].get("max_withdraw_per_day_usdt"),
            "withdrawn_today_usdt": float(cfg["binance"].get("withdrawn_today_usdt") or 0),
            "daily_withdraw_remaining_usdt": daily_left,
        },
        "stash_asset": cfg.get("stash_asset"),
        "min_sweep_usd": min_usd,
        "auto_sweep": bool(cfg.get("auto_sweep")),
        "live_enabled": _live_enabled(),
        "realized_total_usd": round(realized, 4),
        "treasury_stashed_usd": round(_treasury_stashed_usd(), 4),
        "live_stash_usd": round(_treasury_stashed_usd_by_mode("live"), 4),
        "paper_stash_usd": round(_treasury_stashed_usd_by_mode("paper"), 4),
        "sweep_ledger_mode": ledger_mode,
        "sweep_pool_usd": pool,
        "swept_total_usd": round(swept, 4),
        "net_unswept_usd": net,
        "paypal_sweepable_usd": sweepable,
        "ready_to_sweep": paypal_ready if dest == "paypal" else binance_ready,
        "mode": "live" if (_paypal_live_enabled() if dest == "paypal" else binance_withdraw_live_enabled()) else "paper",
    }


def plan_sweep(min_sweep_usd: Optional[float] = None) -> Dict[str, Any]:
    cfg = _load()
    ledger_mode = _sweep_ledger_mode()
    realized = _realized_total_usd()
    pool = _sweep_pool_usd()
    net = _net_unswept_usd(cfg)
    swept = _swept_total_for_mode(cfg, ledger_mode)
    threshold = float(min_sweep_usd if min_sweep_usd is not None else _min_sweep_usd(cfg))
    dest = str(cfg.get("destination") or "paypal")
    paypal_email = _owner_paypal_email(cfg)
    share = _paypal_share_pct(cfg)

    if dest == "paypal" or paypal_email:
        amount = round(net * share, 4)
        if amount < threshold:
            return {"success": True, "actionable": False, "reason": "below_min_sweep",
                    "net_unswept_usd": net, "paypal_sweepable_usd": amount, "min_sweep_usd": threshold}
        if not paypal_email:
            return {"success": True, "actionable": False, "reason": "no_paypal_email",
                    "net_unswept_usd": net, "hint": "Set EXCHANGE_PAYOUT_PAYPAL_EMAIL in .env"}
        return {
            "success": True,
            "actionable": True,
            "destination": "paypal",
            "receiver_email": paypal_email,
            "amount_usd": amount,
            "share_pct": round(share * 100, 2),
            "mode": "live" if _paypal_live_enabled() else "paper",
            "sweep_ledger_mode": ledger_mode,
            "sweep_pool_usd": pool,
            "net_unswept_usd": net,
            "note": "Live PayPal payout requires EXCHANGE_PAYOUT_PAYPAL_LIVE=1 and PayPal Payouts enabled on your app.",
        }

    asset = str(cfg.get("stash_asset") or "USDT").upper()
    addr = (cfg["binance"].get("deposit_addresses") or {}).get(asset)
    if net < threshold:
        return {"success": True, "actionable": False, "reason": "below_min_sweep",
                "net_unswept_usd": net, "min_sweep_usd": threshold}
    if not addr:
        return {"success": True, "actionable": False, "reason": "no_deposit_address",
                "net_unswept_usd": net, "stash_asset": asset}
    return {
        "success": True,
        "actionable": True,
        "destination": "binance",
        "stash_asset": asset,
        "deposit_address": addr,
        "amount_usd": net,
        "mode": "live" if binance_withdraw_live_enabled() else "paper",
        "note": "Live execution requires EXCHANGE_PAYOUT_BINANCE_LIVE=1, EXCHANGE_ARBITRAGE_LIVE=1, and withdraw-scoped API keys.",
    }


def _debit_treasury_for_payout(amount_usd: float) -> None:
    try:
        from backend.services.exchange_treasury_service import treasury_user_id
        uid = treasury_user_id()
        mn2_usd = max(ex._mn2_usd(), 1e-9)
        mn2_amt = round(float(amount_usd) / mn2_usd, 8)
        from backend.services.unified_points_database import unified_points_db
        unified_points_db.add_points(
            uid,
            "mn2_balance",
            -mn2_amt,
            source="paypal_profit_sweep",
            metadata={"amount_usd": amount_usd},
        )
    except Exception:
        pass


def execute_sweep(min_sweep_usd: Optional[float] = None) -> Dict[str, Any]:
    if os.environ.get("EXCHANGE_PROFIT_KILL", "").strip().lower() in ("1", "true", "yes", "on"):
        return {"success": False, "error": "profit_kill", "blocked": True}
    plan = plan_sweep(min_sweep_usd)
    if not plan.get("actionable"):
        return {"success": False, "error": plan.get("reason"), "plan": plan}

    cfg = _load()
    amount = float(plan["amount_usd"])
    dest = plan.get("destination") or "paypal"
    live = False
    payout_ref: Dict[str, Any] = {}

    if dest == "paypal":
        live = _paypal_live_enabled()
        if live:
            from backend.services.paypal_service import create_payout
            payout_ref = create_payout(
                plan["receiver_email"],
                amount,
                note=f"MasterNoder exchange profit ({plan.get('share_pct', 100)}%)",
            )
            if not payout_ref.get("success"):
                return {"success": False, "error": payout_ref.get("error", "paypal_payout_failed"), "plan": plan}
            _debit_treasury_for_payout(amount)
        record = {
            "ts": _iso(),
            "destination": "paypal",
            "receiver_email": plan["receiver_email"],
            "amount_usd": amount,
            "share_pct": plan.get("share_pct"),
            "mode": "live" if live else "paper",
            "payout_batch_id": payout_ref.get("payout_batch_id"),
        }
    else:
        live = binance_withdraw_live_enabled()
        waddr = plan.get("deposit_address") or _binance_withdraw_address(cfg)
        wnet = _binance_withdraw_network(cfg)
        withdraw_ref: Dict[str, Any] = {}
        if live:
            withdraw_ref = withdraw_usdt(amount, waddr, wnet)
            if not withdraw_ref.get("success"):
                return {"success": False, "error": withdraw_ref.get("error", "binance_withdraw_failed"),
                        "plan": plan, "binance": {k: v for k, v in withdraw_ref.items()
                                                  if k not in ("body",) and "secret" not in str(k).lower()}}
        record = {
            "ts": _iso(),
            "destination": "binance",
            "stash_asset": plan["stash_asset"],
            "deposit_address_masked": mask_address(waddr),
            "withdraw_network": wnet,
            "amount_usd": amount,
            "mode": "live" if live else "paper",
            "withdraw_id": withdraw_ref.get("withdraw_id"),
        }

    ex._append_jsonl(_SWEEPS_PATH, record)
    try:
        from backend.services.exchange_profit_path_service import record_event
        record_event(
            phase="sweep",
            agent_id="platform_treasury",
            strategy="payout",
            mode=str(record.get("mode") or "paper"),
            decision="fill",
            notional_usd=amount,
            execution={"destination": dest, "amount_usd": amount},
        )
    except Exception:
        pass
    ledger_mode = str(record.get("mode") or "paper").lower()
    prev_swept = _swept_total_for_mode(cfg, ledger_mode)
    cfg[f"swept_total_usd_{ledger_mode}"] = round(prev_swept + amount, 4)
    if ledger_mode == "paper":
        cfg["swept_total_usd"] = cfg["swept_total_usd_paper"]
    cfg["last_sweep"] = record
    _save(cfg)
    ex._audit("payout_sweep", user_id="owner", amount_usd=amount, destination=dest, mode=record["mode"])
    note = None
    if dest == "paypal" and not live:
        note = f"Paper PayPal sweep recorded for {plan['receiver_email']}; set EXCHANGE_PAYOUT_PAYPAL_LIVE=1 to send real payouts."
    elif dest == "binance" and not live:
        note = "Paper sweep recorded; no funds moved (EXCHANGE_PAYOUT_BINANCE_LIVE=0 or gates off)."
    return {
        "success": True,
        "swept": record,
        "swept_total_usd": cfg.get(f"swept_total_usd_{ledger_mode}", cfg.get("swept_total_usd")),
        "live": live,
        "paypal": payout_ref if dest == "paypal" else None,
        "binance": withdraw_ref if dest == "binance" and live else None,
        "note": note,
    }


def binance_preflight_status(amount_usdt: Optional[float] = None) -> Dict[str, Any]:
    """Preflight Binance USDT withdraw (spot balance + whitelist)."""
    cfg = _load()
    waddr = _binance_withdraw_address(cfg)
    wnet = _binance_withdraw_network(cfg)
    if not waddr:
        return {"success": False, "error": "missing_withdraw_address"}
    pool_usdt = _sales_pool_usdt()
    if amount_usdt is None:
        amount = pool_usdt
    else:
        amount = round(max(0.0, float(amount_usdt)), 8)
    pf = preflight_withdraw_usdt(
        amount, waddr, wnet, skip_live_gate=True, sales_pool_usdt=pool_usdt,
    )
    spot_res = get_spot_usdt_free(skip_live_gate=True)
    return {
        "success": True,
        "amount_usdt": amount,
        "withdraw_network": wnet,
        "withdraw_address_masked": mask_address(waddr),
        "sales_pool_usdt": pool_usdt,
        "binance_spot_usdt_free": float(spot_res.get("free") or 0) if spot_res.get("success") else None,
        "preflight": pf,
    }


def withdraw_binance(amount_usdt: Optional[float] = None, *,
                     min_amount: Optional[float] = None) -> Dict[str, Any]:
    """Withdraw USDT from exchange sales pool via Binance capital API (paper unless live)."""
    cfg = _load()
    if not cfg["binance"].get("withdraw_enabled") and not _binance_withdraw_address(cfg):
        return {"success": False, "error": "withdraw_not_configured",
                "hint": "Set EXCHANGE_PAYOUT_BINANCE_ADDRESS or POST configure-binance with address + network"}

    waddr = _binance_withdraw_address(cfg)
    wnet = _binance_withdraw_network(cfg)
    if not waddr:
        return {"success": False, "error": "missing_withdraw_address"}
    if not wnet:
        return {"success": False, "error": "missing_withdraw_network"}

    creds = binance_credentials()
    if not (creds.get("api_key") and creds.get("api_secret")):
        return {"success": False, "error": "missing_binance_credentials"}

    try:
        from backend.services.exchange_sales_pool_service import sales_pool_user_id
        pool_uid = sales_pool_user_id()
    except Exception:
        pool_uid = "exchange_sales_pool"

    pool_assets = (ex.get_wallet(pool_uid).get("assets") or {})
    pool_usdt = round(float(pool_assets.get("USDT") or 0), 8)
    threshold = float(min_amount if min_amount is not None else _min_sweep_usd(cfg))

    if amount_usdt is None:
        amount = pool_usdt
    else:
        amount = round(max(0.0, float(amount_usdt)), 8)

    if amount < threshold:
        return {"success": False, "error": "below_min_amount", "min_amount": threshold, "pool_usdt": pool_usdt}
    if amount > pool_usdt:
        return {"success": False, "error": "insufficient_sales_pool_usdt",
                "requested": amount, "pool_usdt": pool_usdt}

    _reset_daily_withdraw_counter(cfg)
    daily_left = _daily_withdraw_remaining(cfg)
    if daily_left is not None and amount > daily_left:
        return {"success": False, "error": "daily_cap_exceeded",
                "requested": amount, "daily_remaining": daily_left}

    live = binance_withdraw_live_enabled()
    order_id = f"mn2-pool-{pool_uid}-{int(datetime.now(timezone.utc).timestamp())}"

    if live:
        spot_res = get_spot_usdt_free(skip_live_gate=True)
        spot_free = float(spot_res.get("free") or 0) if spot_res.get("success") else 0.0
        if pool_usdt >= amount and spot_free < amount:
            return {
                "success": False,
                "error": "binance_spot_insufficient",
                "sales_pool_usdt": pool_usdt,
                "binance_spot_usdt_free": spot_free,
                "requested": amount,
                "message": (
                    f"Sales pool ledger holds {pool_usdt} USDT but Binance spot free is {spot_free}. "
                    "Deposit real USDT to the Binance API account before withdraw; "
                    "the internal sales pool is not on-chain Binance balance."
                ),
            }
        pf = preflight_withdraw_usdt(
            amount, waddr, wnet, skip_live_gate=True, sales_pool_usdt=pool_usdt,
        )
        if not pf.get("ready"):
            return {
                "success": False,
                "error": "preflight_failed",
                "preflight": pf,
                "sales_pool_usdt": pool_usdt,
                "binance_spot_usdt_free": pf.get("spot_usdt_free"),
            }

    with ex._LOCK:
        pool_assets = (ex.get_wallet(pool_uid).get("assets") or {})
        pool_usdt = round(float(pool_assets.get("USDT") or 0), 8)
        if amount > pool_usdt:
            return {"success": False, "error": "insufficient_sales_pool_usdt",
                    "requested": amount, "pool_usdt": pool_usdt}
        try:
            ex._adjust_balance(pool_uid, "USDT", -amount)
        except Exception as exc:
            return {"success": False, "error": "debit_failed", "detail": str(exc)}

        withdraw_ref: Dict[str, Any] = {}
        if live:
            withdraw_ref = withdraw_usdt(amount, waddr, wnet, withdraw_order_id=order_id)
            if not withdraw_ref.get("success"):
                try:
                    ex._adjust_balance(pool_uid, "USDT", amount)
                except Exception:
                    pass
                err_payload = {
                    k: v for k, v in withdraw_ref.items()
                    if k not in ("body",) and "secret" not in str(k).lower()
                }
                return {
                    "success": False,
                    "error": withdraw_ref.get("error", "binance_withdraw_failed"),
                    "binance_code": withdraw_ref.get("binance_code"),
                    "binance_msg": withdraw_ref.get("binance_msg"),
                    "http_status": withdraw_ref.get("http_status"),
                    "binance": err_payload,
                }
        else:
            withdraw_ref = withdraw_usdt(amount, waddr, wnet, dry_run=True, withdraw_order_id=order_id)

    record = {
        "ts": _iso(),
        "destination": "binance",
        "source": "sales_pool",
        "sales_pool_user_id": pool_uid,
        "stash_asset": "USDT",
        "amount_usdt": amount,
        "withdraw_network": wnet,
        "address_masked": mask_address(waddr),
        "mode": "live" if live else "paper",
        "withdraw_id": withdraw_ref.get("withdraw_id"),
        "withdraw_order_id": order_id,
    }
    ex._append_jsonl(_SWEEPS_PATH, record)
    cfg["binance"]["withdrawn_today_usdt"] = round(
        float(cfg["binance"].get("withdrawn_today_usdt") or 0) + amount, 8
    )
    cfg["last_withdraw"] = record
    _save(cfg)
    ex._audit("payout_binance_withdraw", user_id="owner", amount_usdt=amount,
              mode=record["mode"], withdraw_id=record.get("withdraw_id"),
              address_masked=mask_address(waddr), network=wnet)

    note = None
    if not live:
        note = "Paper withdraw: sales pool debited in ledger only; set EXCHANGE_PAYOUT_BINANCE_LIVE=1 for real Binance withdraw."

    return {
        "success": True,
        "withdrawn": record,
        "pool_usdt_after": round(pool_usdt - amount, 8),
        "live": live,
        "binance": {k: v for k, v in withdraw_ref.items()
                    if k not in ("body",) and "secret" not in str(k).lower()},
        "note": note,
    }


def sweep_history(limit: int = 20) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    if os.path.isfile(_SWEEPS_PATH):
        with open(_SWEEPS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    import json
                    rows.append(json.loads(line))
                except Exception:
                    continue
    return {"success": True, "count": len(rows), "sweeps": rows[-int(limit or 20):][::-1]}
