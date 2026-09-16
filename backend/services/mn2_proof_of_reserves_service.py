"""
MN2 proof-of-reserves & realized-yield report (plan §20 #11/#12, Top-10 #1).

Turns the conservation invariant (§8 reconcile), the daemon balance (§9), and the
realized-yield reserve into a public, regulator-friendly transparency artifact:

  - Proof of reserves: on-chain custodial assets vs total user liabilities (liquid
    `mn2_balance` + pooled `mn2_staked`), with a coverage ratio and the reconcile verdict.
  - Yield report:      realized daemon staking yield vs rewards paid vs site margin,
    lifetime and (optionally) per-day from the reward-rows table.

Read-only and defensive: never raises, serves a short TTL cache so a public page can't
hammer the daemon RPC, and clearly labels when the daemon balance is unavailable.
"""
import os
import json
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_POINTS_DIR = os.path.join(_BASE_DIR, "logs", "unified_points")

_CACHE_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {"por": None, "por_ts": 0.0, "yield": None, "yield_ts": 0.0}
_POR_TTL = 60.0      # seconds — RPC-backed, keep fresh-ish but cheap
_YIELD_TTL = 30.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(name: str, default: Any) -> Any:
    p = os.path.join(_BASE_DIR, "data", name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# --------------------------------------------------------------- liabilities

def _sum_user_liabilities() -> Tuple[float, float, int]:
    """
    Σ over all users of (mn2_balance, mn2_staked) from the file-backed points store.
    Pure file IO (no per-user SQL) so a public endpoint stays cheap. Returns
    (total_liquid, total_staked, holder_count).
    """
    total_liquid = 0.0
    total_staked = 0.0
    holders = 0
    try:
        names = [fn for fn in os.listdir(_POINTS_DIR) if fn.endswith(".json")]
    except Exception:
        names = []
    for fn in names:
        try:
            with open(os.path.join(_POINTS_DIR, fn), "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
        except Exception:
            continue
        systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
        bal = float(systems.get("mn2_balance", 0) or 0)
        staked = float(systems.get("mn2_staked", 0) or 0)
        if bal > 0 or staked > 0:
            holders += 1
        total_liquid += bal
        total_staked += staked
    return round(total_liquid, 8), round(total_staked, 8), holders


# ----------------------------------------------------------------- on-chain

def _onchain_balance() -> Dict[str, Any]:
    """
    Custodial assets the daemon controls. Prefer getwalletinfo (gives immature/
    unconfirmed splits); fall back to getbalance. status: ok | unavailable.
    """
    out = {
        "status": "unavailable",
        "balance": None,
        "immature_balance": None,
        "unconfirmed_balance": None,
        "total": None,
        "source": None,
        "error": None,
    }
    try:
        from backend.services import mn2_rpc_client as rpc
    except Exception as e:
        out["error"] = f"rpc import failed: {e}"
        return out

    try:
        wi = rpc.getwalletinfo()
        res = wi.get("result") if isinstance(wi, dict) else None
        if isinstance(res, dict) and res.get("balance") is not None:
            bal = float(res.get("balance") or 0)
            imm = float(res.get("immature_balance") or 0)
            unc = float(res.get("unconfirmed_balance") or 0)
            out.update({
                "status": "ok",
                "balance": round(bal, 8),
                "immature_balance": round(imm, 8),
                "unconfirmed_balance": round(unc, 8),
                "total": round(bal + imm + unc, 8),
                "source": "getwalletinfo",
            })
            return out
    except Exception:
        pass

    try:
        gb = rpc.getbalance()
        res = gb.get("result") if isinstance(gb, dict) else None
        if res is not None and not (isinstance(gb, dict) and gb.get("error")):
            bal = float(res or 0)
            out.update({
                "status": "ok",
                "balance": round(bal, 8),
                "total": round(bal, 8),
                "source": "getbalance",
            })
            return out
        if isinstance(gb, dict) and gb.get("error"):
            out["error"] = str(gb.get("error"))
    except Exception as e:
        out["error"] = str(e)
    return out


# -------------------------------------------------------------- public API

def _float_snapshot() -> Dict[str, Any]:
    try:
        from backend.services.mn2_float_gate import assess
        return assess(0)
    except Exception as e:
        return {"error": str(e)}


def proof_of_reserves(force: bool = False) -> Dict[str, Any]:
    """
    Assets (on-chain custodial balance + stabilization reserve) vs liabilities
    (Σ user liquid + pooled staked), coverage ratio, and the reconcile verdict.
    """
    with _CACHE_LOCK:
        if not force and _CACHE["por"] and (time.time() - _CACHE["por_ts"]) < _POR_TTL:
            return _CACHE["por"]

    liquid, staked, holders = _sum_user_liabilities()
    liabilities_total = round(liquid + staked, 8)

    onchain = _onchain_balance()
    reserve = _read_json("mn2_staking_reserve.json", {}) or {}
    reserve_mn2 = round(float(reserve.get("reserve_mn2", 0) or 0), 8)

    onchain_total = onchain.get("total")
    assets_total = round((onchain_total or 0) + reserve_mn2, 8) if onchain_total is not None else None
    coverage_ratio = None
    surplus = None
    if assets_total is not None and liabilities_total > 0:
        coverage_ratio = round(assets_total / liabilities_total, 6)
        surplus = round(assets_total - liabilities_total, 8)
    elif assets_total is not None and liabilities_total == 0:
        coverage_ratio = None  # nothing owed
        surplus = assets_total

    # Reconcile verdict gates the "healthy" claim.
    reconcile = {"ok": None, "failed_checks": [], "error": None}
    try:
        from backend.services.mn2_staking_reconcile_service import reconcile as _recon
        r = _recon()
        reconcile = {
            "ok": bool(r.get("ok")),
            "failed_checks": r.get("failed_checks", []),
            "generated_at": r.get("generated_at"),
        }
    except Exception as e:
        reconcile["error"] = str(e)

    fully_backed = (
        coverage_ratio is not None and coverage_ratio >= 1.0
        and onchain.get("status") == "ok"
        and reconcile.get("ok") is True
    )

    conservation = {"verdict": None, "ok": None}
    try:
        from backend.services.mn2_conservation_gate import conservation_gate
        cg = conservation_gate()
        conservation = {"verdict": cg.get("verdict"), "ok": cg.get("ok")}
    except Exception as e:
        conservation["error"] = str(e)

    out = {
        "success": True,
        "generated_at": _now_iso(),
        "assets": {
            "onchain": onchain,
            "stabilization_reserve_mn2": reserve_mn2,
            "total_mn2": assets_total,
        },
        "liabilities": {
            "user_liquid_mn2": liquid,
            "user_staked_mn2": staked,
            "total_mn2": liabilities_total,
            "holders": holders,
        },
        "coverage_ratio": coverage_ratio,
        "surplus_mn2": surplus,
        "fully_backed": fully_backed,
        "reconcile": reconcile,
        "conservation_gate": conservation,
        "gate_verdict": conservation.get("verdict"),
        "float_gate": _float_snapshot(),
        "notes": (
            "Assets are the MN2 the site's custodial daemon controls (including coins "
            "currently PoS-staked) plus the stabilization reserve. Liabilities are the sum "
            "of every user's in-app MN2 (liquid + staked). Coverage ≥ 1.0 with a green "
            "reconcile means all user MN2 is fully backed."
        ),
    }
    with _CACHE_LOCK:
        _CACHE["por"] = out
        _CACHE["por_ts"] = time.time()
    return out


def _reward_rows_by_day(limit_days: int = 30) -> List[Dict[str, Any]]:
    """Aggregate the append-only reward rows into per-UTC-day yield/paid buckets."""
    p = os.path.join(_BASE_DIR, "data", "mn2_staking_rewards.jsonl")
    buckets: Dict[str, Dict[str, float]] = {}
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                iid = str(row.get("interval_id") or "")
                day = iid[:10] if len(iid) >= 10 else (row.get("created_at") or "")[:10]
                if not day:
                    continue
                b = buckets.setdefault(day, {"reward_mn2": 0.0, "pool_budget_mn2": 0.0})
                b["reward_mn2"] += float(row.get("reward_mn2", 0) or 0)
                b["pool_budget_mn2"] += float(row.get("pool_budget_mn2", 0) or 0)
    except Exception:
        return []
    days = sorted(buckets.keys(), reverse=True)[:limit_days]
    return [{
        "date": d,
        "reward_mn2": round(buckets[d]["reward_mn2"], 8),
        "pool_budget_mn2": round(buckets[d]["pool_budget_mn2"], 8),
    } for d in days]


def yield_report(force: bool = False) -> Dict[str, Any]:
    """
    Realized daemon staking yield vs rewards paid vs site margin (lifetime + per day).
    """
    with _CACHE_LOCK:
        if not force and _CACHE["yield"] and (time.time() - _CACHE["yield_ts"]) < _YIELD_TTL:
            return _CACHE["yield"]

    reserve = _read_json("mn2_staking_reserve.json", {}) or {}
    lifetime_yield = round(float(reserve.get("lifetime_realized_yield", 0) or 0), 8)
    lifetime_paid = round(float(reserve.get("lifetime_paid", 0) or 0), 8)
    reserve_mn2 = round(float(reserve.get("reserve_mn2", 0) or 0), 8)

    margin_percent = 0.0
    mode = "unknown"
    try:
        from backend.services.mn2_staking_service import get_config
        cfg = get_config()
        margin_percent = float(cfg.get("site_margin_percent", 0) or 0)
        mode = cfg.get("reward_pool_mode") or "unknown"
    except Exception:
        pass

    site_margin_mn2 = round(max(0.0, lifetime_yield - lifetime_paid), 8)
    payout_ratio = round(lifetime_paid / lifetime_yield, 6) if lifetime_yield > 0 else None

    out = {
        "success": True,
        "generated_at": _now_iso(),
        "mode": mode,
        "site_margin_percent": margin_percent,
        "lifetime": {
            "realized_yield_mn2": lifetime_yield,
            "rewards_paid_mn2": lifetime_paid,
            "site_margin_mn2": site_margin_mn2,
            "payout_ratio": payout_ratio,
            "stabilization_reserve_mn2": reserve_mn2,
        },
        "by_day": _reward_rows_by_day(30),
        "notes": (
            "Rewards are paid only from realized daemon staking yield minus a stated site "
            "margin; payout_ratio is rewards paid ÷ realized yield. Estimated/variable — not "
            "a guaranteed return."
        ),
    }
    with _CACHE_LOCK:
        _CACHE["yield"] = out
        _CACHE["yield_ts"] = time.time()
    return out


def reserves_overview(force: bool = False) -> Dict[str, Any]:
    """Public aggregator: PoR + yield + exchange treasury + fee treasury + network ops."""
    por = proof_of_reserves(force=force)
    yield_r = yield_report(force=force)

    exchange_treasury: Dict[str, Any] = {}
    try:
        from backend.services.exchange_treasury_service import treasury_status
        exchange_treasury = treasury_status()
    except Exception as exc:
        exchange_treasury = {"success": False, "error": str(exc)}

    fee_treasury: Dict[str, Any] = {}
    try:
        from backend.services import crypto_exchange_service as ex
        tre = ex._read_json(ex._TREASURY_PATH, {"total_fees_mn2": 0, "updated_at": None})
        mn2_usd = ex._mn2_usd()
        fee_treasury = {
            "success": True,
            "total_fees_mn2": round(float(tre.get("total_fees_mn2") or 0), 8),
            "updated_at": tre.get("updated_at"),
            "total_fees_usd_est": round(float(tre.get("total_fees_mn2") or 0) * mn2_usd, 2),
        }
    except Exception as exc:
        fee_treasury = {"success": False, "error": str(exc)}

    network_ops: Dict[str, Any] = {}
    try:
        from backend.services.mn2_rpc_client import staking_health
        from backend.services import mn2_staking_service as _stk
        network_ops = {
            "staking_health": staking_health(),
            "pool": {
                "total_staked_mn2": _stk.total_staked(),
                "dynamic_apr_percent": _stk.dynamic_apr(),
            },
        }
    except Exception as exc:
        network_ops = {"error": str(exc)}

    return {
        "success": True,
        "generated_at": _now_iso(),
        "proof_of_reserves": por,
        "yield_report": yield_r,
        "exchange_treasury": exchange_treasury,
        "fee_treasury": fee_treasury,
        "network_ops": network_ops,
    }
