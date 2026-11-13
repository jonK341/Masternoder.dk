"""DataMaxi CEX–CEX spread playbook limb.

Installs the DataMaxi Premium playbook as a body leg:
* Prefer DataMaxi `/api/v1/premium` when ``DTMX_API_KEY`` is set.
* Always fall back to local BN↔NK books (inventory-prepositioned spot-spot).
* Apply playbook gates: min net bps, fee pad, depth proxy, cutting-edge band.

Refs: https://docs.datamaxiplus.com/strategies/cex-cex-spread
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import external_exchange_connector_service as conn

_STATE_PATH = os.path.join(ex._DATA_DIR, "datamaxi_cex_spread_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "datamaxi_cex_spread_ledger.jsonl")
_BOOK_PATH = os.path.join(ex._DATA_DIR, "datamaxi_cex_spread_book.json")
_DTMX_PREMIUM = "https://api.datamaxiplus.com/api/v1/premium"
_EXTERNAL = ("binance", "nonkyc")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cfg_float(key: str, default: float) -> float:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _cfg_int(key: str, default: int) -> int:
    return int(_cfg_float(key, float(default)))


def playbook_enabled() -> bool:
    try:
        from backend.services.exchange_profit_head_service import limb_allowed
        if not limb_allowed("datamaxi"):
            return False
    except Exception:
        pass
    raw = os.environ.get("DATAMAXI_CEX_SPREAD_ENABLED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "limb": "datamaxi"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _dtmx_key() -> str:
    return (os.environ.get("DTMX_API_KEY") or os.environ.get("DATAMAXI_API_KEY") or "").strip()


def fetch_datamaxi_premium(
    *,
    from_market: str = "binance",
    to_market: str = "nonkyc",
    limit: int = 25,
) -> Dict[str, Any]:
    """Pull Premium table when API key present; else empty with reason."""
    key = _dtmx_key()
    if not key:
        return {"ok": False, "reason": "no_dtmx_api_key", "rows": []}
    try:
        resp = requests.get(
            _DTMX_PREMIUM,
            headers={"X-DTMX-APIKEY": key},
            params={
                "fromMarket": from_market,
                "toMarket": to_market,
                "sort": "desc",
                "key": "premium",
                "limit": int(limit),
            },
            timeout=12,
        )
        if resp.status_code >= 400:
            return {"ok": False, "reason": f"http_{resp.status_code}", "rows": [], "body": resp.text[:200]}
        payload = resp.json() if resp.content else {}
        rows = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            rows = []
        return {"ok": True, "rows": rows, "source": "datamaxi"}
    except Exception as exc:
        return {"ok": False, "reason": str(exc)[:160], "rows": []}


def _local_premium_scan(*, notional_usd: float, scan_limit: int) -> Dict[str, Any]:
    """Inventory-prepositioned BN↔NK premium using our own books (DataMaxi fallback)."""
    from backend.services.exchange_spread_hunter_arm_service import (
        _annotate_opportunity,
        _batch_scan,
        _build_universe,
        mid_skew_bps,
    )

    uni = _build_universe(scan_limit=scan_limit)
    symbols = list(uni.get("symbols") or [])
    cfg = conn.load_connectors_config()
    xfer = float(arb._effective_transfer_cost_bps(cfg))
    annotated = _batch_scan(
        symbols,
        venues=list(_EXTERNAL),
        notional_usd=notional_usd,
        batch_size=_cfg_int("DATAMAXI_BATCH_SIZE", 25),
        xfer_bps=xfer,
        cfg=cfg,
    )
    rows: List[Dict[str, Any]] = []
    for o in annotated:
        if str(o.get("buy_venue") or "") not in _EXTERNAL:
            continue
        if str(o.get("sell_venue") or "") not in _EXTERNAL:
            continue
        skew = float(o.get("mid_skew_bps") or 0)
        if not skew:
            skew = mid_skew_bps(
                float(o.get("buy_ask") or 0),
                float(o.get("buy_bid") or o.get("buy_ask") or 0),
                float(o.get("sell_ask") or o.get("sell_bid") or 0),
                float(o.get("sell_bid") or 0),
            )
            o = _annotate_opportunity(dict(o), notional_usd=notional_usd, cfg=cfg, xfer_bps=xfer)
            o["mid_skew_bps"] = round(skew, 2)
        rows.append(o)
    rows.sort(key=lambda r: float(r.get("net_bps") or 0), reverse=True)
    return {"ok": True, "rows": rows, "source": "local_bn_nk", "universe": len(symbols)}


def _playbook_gate(row: Dict[str, Any], *, min_net_bps: float, min_profit: float) -> Dict[str, Any]:
    """DataMaxi gates: fees cleared, cutting-edge fire, profitable."""
    from backend.services.exchange_technique_executor_service import cutting_edge

    net = float(row.get("net_bps") or 0)
    # Playbook: majors need >~25 bps net after 0.1%/side; configurable.
    if net < min_net_bps:
        return {"ok": False, "reason": "below_playbook_min_net"}
    if float(row.get("est_profit_usd") or 0) < min_profit:
        return {"ok": False, "reason": "below_min_profit"}
    edge = cutting_edge(
        net_bps=net,
        mid_skew_bps=float(row.get("mid_skew_bps") or 0),
        buy_ask=float(row.get("buy_ask") or row.get("fromPrice") or 0),
        buy_bid=float(row.get("buy_bid") or 0),
        sell_ask=float(row.get("sell_ask") or 0),
        sell_bid=float(row.get("sell_bid") or row.get("toPrice") or 0),
        est_profit_usd=float(row.get("est_profit_usd") or 0),
    )
    if edge.get("band") != "fire":
        return {"ok": False, "reason": edge.get("reason") or edge.get("band"), "cutting_edge": edge}
    return {"ok": True, "cutting_edge": edge}


def _normalize_dtmx_row(row: Dict[str, Any], *, notional_usd: float) -> Optional[Dict[str, Any]]:
    sym = str(row.get("symbol") or row.get("base") or "").upper().replace("-USDT", "").replace("USDT", "")
    if not sym:
        return None
    # Premium APIs vary; map best-effort into our opportunity shape.
    from_px = float(row.get("fromPrice") or row.get("from_price") or 0)
    to_px = float(row.get("toPrice") or row.get("to_price") or 0)
    premium = float(row.get("premium") or 0)
    # If premium is a fraction (0.01 = 1%), convert to bps.
    prem_bps = premium * 10000.0 if abs(premium) < 2 else premium
    if from_px <= 0 or to_px <= 0:
        # Still keep symbol with premium-only signal for hunter hinting.
        return {
            "symbol": sym,
            "buy_venue": "binance" if prem_bps > 0 else "nonkyc",
            "sell_venue": "nonkyc" if prem_bps > 0 else "binance",
            "buy_ask": from_px or None,
            "sell_bid": to_px or None,
            "net_bps": abs(prem_bps),
            "gross_bps": abs(prem_bps),
            "est_profit_usd": abs(prem_bps) / 10000.0 * notional_usd,
            "notional_usd": notional_usd,
            "profitable": abs(prem_bps) > 0,
            "source": "datamaxi",
            "premium": premium,
        }
    buy_v, sell_v = ("binance", "nonkyc") if from_px <= to_px else ("nonkyc", "binance")
    buy_ask = min(from_px, to_px)
    sell_bid = max(from_px, to_px)
    return {
        "symbol": sym,
        "buy_venue": buy_v,
        "sell_venue": sell_v,
        "buy_ask": buy_ask,
        "sell_bid": sell_bid,
        "net_bps": abs(prem_bps),
        "gross_bps": abs(prem_bps),
        "est_profit_usd": abs(prem_bps) / 10000.0 * notional_usd,
        "notional_usd": notional_usd,
        "profitable": True,
        "source": "datamaxi",
        "premium": premium,
    }


def build_cex_spread_book(*, force: bool = False) -> Dict[str, Any]:
    notional = _cfg_float("DATAMAXI_NOTIONAL_USD", 15.0)
    min_net = _cfg_float("DATAMAXI_MIN_NET_BPS", 25.0)  # playbook majors floor
    min_profit = _cfg_float("DATAMAXI_MIN_PROFIT_USD", 0.02)
    top_n = _cfg_int("DATAMAXI_TOP_N", 5)
    scan_limit = _cfg_int("DATAMAXI_SCAN_LIMIT", 60)

    remote = fetch_datamaxi_premium(
        from_market=os.environ.get("DATAMAXI_FROM_MARKET", "binance"),
        to_market=os.environ.get("DATAMAXI_TO_MARKET", "bybit"),
        limit=max(top_n * 3, 15),
    )
    local = _local_premium_scan(notional_usd=notional, scan_limit=scan_limit)

    merged: List[Dict[str, Any]] = []
    if remote.get("ok"):
        for raw in remote.get("rows") or []:
            if isinstance(raw, dict):
                norm = _normalize_dtmx_row(raw, notional_usd=notional)
                if norm:
                    merged.append(norm)
    for row in local.get("rows") or []:
        merged.append(dict(row))

    hitlist: List[Dict[str, Any]] = []
    for row in merged:
        gate = _playbook_gate(row, min_net_bps=min_net, min_profit=min_profit)
        item = {
            **{k: row.get(k) for k in (
                "symbol", "buy_venue", "sell_venue", "buy_ask", "sell_bid",
                "net_bps", "est_profit_usd", "notional_usd", "mid_skew_bps", "source", "premium",
            )},
            "qualifies": bool(gate.get("ok")),
            "gate_reason": gate.get("reason"),
            "cut_bps": (gate.get("cutting_edge") or {}).get("cut_bps"),
            "edge_band": (gate.get("cutting_edge") or {}).get("band"),
            "playbook": "datamaxi_cex_cex_spread",
        }
        hitlist.append(item)

    hitlist.sort(
        key=lambda r: (1 if r.get("qualifies") else 0, float(r.get("cut_bps") or r.get("net_bps") or 0)),
        reverse=True,
    )
    top = hitlist[:top_n]
    book = {
        "updated_at": _iso(),
        "limb": "datamaxi",
        "playbook": "cex_cex_spread",
        "datamaxi_ok": bool(remote.get("ok")),
        "datamaxi_reason": remote.get("reason"),
        "local_source": local.get("source"),
        "deal_count": len(hitlist),
        "qualifying_count": sum(1 for r in hitlist if r.get("qualifies")),
        "min_net_bps": min_net,
        "top": top,
        "hitlist": hitlist[: max(top_n * 2, 10)],
    }
    ex._write_json(_BOOK_PATH, book)
    return book


def run_datamaxi_cex_spread_tick(*, force: bool = False) -> Dict[str, Any]:
    if not playbook_enabled() and not force:
        return {"success": False, "skipped": True, "reason": "arm_disabled", "limb": "datamaxi"}

    book = build_cex_spread_book(force=force)
    top = (book.get("top") or [None])[0]
    out: Dict[str, Any] = {
        "success": True,
        "limb": "datamaxi",
        "name": "datamaxi",
        "scanned_at": book.get("updated_at"),
        "deal_count": book.get("deal_count"),
        "qualifying_count": book.get("qualifying_count"),
        "datamaxi_ok": book.get("datamaxi_ok"),
        "top": top,
        "handed_to_hunter": False,
        "skip_reason": None,
    }
    if not top:
        out["skip_reason"] = "empty_book"
    elif not top.get("qualifies"):
        out["skip_reason"] = top.get("gate_reason") or "top_below_playbook"
    else:
        # Hand the best fire deal to hunter via head kill-shot / prefund hint.
        try:
            from backend.services.exchange_profit_head_service import set_kill_shot, set_prefund_hint

            hint = {
                "symbol": top.get("symbol"),
                "route": f"{top.get('buy_venue')}→{top.get('sell_venue')}",
                "net_bps": top.get("net_bps"),
                "cut_bps": top.get("cut_bps"),
                "technique": "datamaxi_cex_cex_spread",
                "reason": "playbook_fire",
            }
            set_kill_shot({
                "arm": "hunter",
                "symbol": top.get("symbol"),
                "reason": "datamaxi_premium",
                "net_bps": top.get("net_bps"),
            })
            set_prefund_hint(hint)
            out["handed_to_hunter"] = True
        except Exception as exc:
            out["skip_reason"] = f"handoff_error:{str(exc)[:80]}"

    _append(
        "tick",
        deals=out.get("deal_count"),
        qual=out.get("qualifying_count"),
        top=(top or {}).get("symbol"),
        handed=out.get("handed_to_hunter"),
        skip=out.get("skip_reason"),
    )
    state = {
        "updated_at": _iso(),
        "last_tick": {
            "deal_count": out.get("deal_count"),
            "qualifying_count": out.get("qualifying_count"),
            "top": top,
            "handed_to_hunter": out.get("handed_to_hunter"),
            "skip_reason": out.get("skip_reason"),
        },
    }
    ex._write_json(_STATE_PATH, state)
    out["summary"] = (
        f"deals={out.get('deal_count', 0)} qual={out.get('qualifying_count', 0)} "
        f"top={(top or {}).get('symbol') or '-'} "
        f"hand={'yes' if out.get('handed_to_hunter') else 'no'}"
    )
    if out.get("skip_reason"):
        out["summary"] += f" skip={out['skip_reason']}"
    return out


def datamaxi_cex_spread_status() -> Dict[str, Any]:
    return {
        "success": True,
        "enabled": playbook_enabled(),
        "has_api_key": bool(_dtmx_key()),
        "book": ex._read_json(_BOOK_PATH, {}),
        "state": ex._read_json(_STATE_PATH, {}),
    }
