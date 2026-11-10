"""12-minute AI-generated landing monitor pipeline — network sats + daemon trades + FX."""
from __future__ import annotations

import json
import os
import random
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Single ephemeral working copy only — never a history of movies.
_PIPELINE_PATH = os.path.join(_BASE, "data", "landing_monitor_pipeline.json")
_PPP_LEDGER = os.path.join(_BASE, "data", "crypto_exchange", "profit_path_ledger.jsonl")
_GRID_LEDGER = os.path.join(_BASE, "data", "crypto_exchange", "grid_bot_ledger.jsonl")
_VENUE_CACHE = os.path.join(_BASE, "data", "crypto_exchange", "venue_balance_monitor_cache.json")
_HEARTBEAT = os.path.join(_BASE, "logs", "daemon_all_profit_heartbeat.json")

SATS_PER_COIN = 100_000_000
PIPELINE_MINUTES = 12
PIPELINE_MS = PIPELINE_MINUTES * 60 * 1000  # 720_000
TARGET_SCENES = 60  # ~12s each → 12 minutes
BPM = 180
# Hard recount cadence: every movie window forces a fresh recount of live sats.
RECOUNT_SEC = PIPELINE_MINUTES * 60

# In-memory only current cut (disk is a crash-scratch mirror, overwritten in place).
_CURRENT: Dict[str, Any] = {}

# Category FX for pipeline scenes (lights + sounds).
SCENE_FX: Dict[str, Dict[str, Any]] = {
    "network": {
        "lightshow": "spectrum",
        "title": "Network sats spectrum",
        "explain": "Spectrum bars map on-chain / venue sats flowing across the lobby.",
        "color": "#00ff88",
        "sound": "coin_sparkle",
        "bars": 5,
    },
    "trade": {
        "lightshow": "chase",
        "title": "Daemon trade chase",
        "explain": "Chase nodes fire on every daemon fill — trade energy around the bezel.",
        "color": "#ffd166",
        "sound": "chime_cash",
        "bars": 6,
    },
    "profit": {
        "lightshow": "pulse",
        "title": "Profit pulse",
        "explain": "Deep pulse for realized PnL beats.",
        "color": "#ffd166",
        "sound": "chime_cash",
        "bars": 4,
    },
    "wallet": {
        "lightshow": "spectrum",
        "title": "Wallet spectrum",
        "explain": "Wallet / MN2 balance hits.",
        "color": "#00ff88",
        "sound": "coin_sparkle",
        "bars": 4,
    },
    "action": {
        "lightshow": "wave",
        "title": "Action waves",
        "explain": "Learned platform actions roll through as cyan waves.",
        "color": "#00d4ff",
        "sound": "whoosh_rise",
        "bars": 5,
    },
    "finale": {
        "lightshow": "rainbow",
        "title": "Pipeline finale",
        "explain": "Rainbow wash closes the 12-minute AI reel.",
        "color": "#c77dff",
        "sound": "bubble_ping",
        "bars": 8,
    },
    "system": {
        "lightshow": "pulse",
        "title": "System pulse",
        "explain": "Ops beat keeping the pipeline honest.",
        "color": "#9aa4b2",
        "sound": "tick_blip",
        "bars": 3,
    },
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any = None) -> Any:
    if default is None:
        default = {}
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


def _tail_jsonl(path: str, limit: int = 400) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        rows.append(row)
                except Exception:
                    continue
    except Exception:
        return []
    return rows[-max(1, limit) :]


def _coins_to_sats(amount: Any) -> int:
    try:
        return int(round(float(amount or 0) * SATS_PER_COIN))
    except (TypeError, ValueError):
        return 0


def _usd_to_btc_sats(usd: Any, btc_usd: float) -> int:
    try:
        u = float(usd or 0)
    except (TypeError, ValueError):
        return 0
    if btc_usd <= 0 or u == 0:
        return 0
    return int(round((u / btc_usd) * SATS_PER_COIN))


def _btc_usd_guess() -> float:
    for rel in (
        "data/crypto_exchange/btc_usd_cache.json",
        "data/btc_price_cache.json",
    ):
        doc = _read_json(os.path.join(_BASE, rel), {})
        if isinstance(doc, dict):
            for key in ("btc_usd", "price", "usd"):
                try:
                    v = float(doc.get(key) or 0)
                    if v > 0:
                        return v
                except (TypeError, ValueError):
                    pass
    return float(os.environ.get("BTC_USD_FALLBACK") or 95000)


def _mn2_network_sats() -> Dict[str, Any]:
    """On-chain MN2 daemon wallet → sats (1 MN2 = 1e8 sats)."""
    out: Dict[str, Any] = {
        "source": "mn2_daemon",
        "coins": 0.0,
        "sats": 0,
        "immature_sats": 0,
        "unconfirmed_sats": 0,
        "ok": False,
    }

    def _rpc() -> Dict[str, Any]:
        from backend.services import mn2_rpc_client as rpc

        info = rpc.getwalletinfo(timeout_sec=0.45) or {}
        if info.get("error") is None and isinstance(info.get("result"), dict):
            return info["result"]
        bal = rpc.getbalance() or {}
        if bal.get("error") is None and bal.get("result") is not None:
            return {"balance": bal.get("result")}
        return {}

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_rpc)
            result = fut.result(timeout=0.6)
        if result:
            coins = float(result.get("balance") or 0)
            imm = float(result.get("immature_balance") or 0)
            unc = float(result.get("unconfirmed_balance") or 0)
            out.update(
                {
                    "ok": True,
                    "coins": coins,
                    "sats": _coins_to_sats(coins),
                    "immature_sats": _coins_to_sats(imm),
                    "unconfirmed_sats": _coins_to_sats(unc),
                    "total_sats": _coins_to_sats(coins + imm + unc),
                }
            )
            return out
    except (FuturesTimeout, Exception):
        pass

    # Disk fallbacks (POR / float gate caches if present)
    for rel in (
        "data/mn2_proof_of_reserves_cache.json",
        "data/mn2_float_gate_cache.json",
        "data/mn2_network_snapshot.json",
    ):
        doc = _read_json(os.path.join(_BASE, rel), {})
        if not isinstance(doc, dict):
            continue
        for key in ("balance", "onchain_balance", "total_mn2", "wallet_balance_mn2"):
            try:
                coins = float(doc.get(key) or 0)
            except (TypeError, ValueError):
                coins = 0.0
            if coins > 0:
                out.update(
                    {
                        "ok": True,
                        "coins": coins,
                        "sats": _coins_to_sats(coins),
                        "total_sats": _coins_to_sats(coins),
                        "source": rel,
                    }
                )
                return out
        assets = doc.get("assets") if isinstance(doc.get("assets"), dict) else {}
        onchain = assets.get("onchain") if isinstance(assets.get("onchain"), dict) else {}
        try:
            coins = float(onchain.get("balance") or onchain.get("total") or 0)
        except (TypeError, ValueError):
            coins = 0.0
        if coins > 0:
            out.update(
                {
                    "ok": True,
                    "coins": coins,
                    "sats": _coins_to_sats(coins),
                    "total_sats": _coins_to_sats(coins),
                    "source": rel,
                }
            )
            return out
    return out


def _venue_btc_sats() -> Dict[str, Any]:
    """Venue BTC free balances from monitor cache → sats."""
    cache = _read_json(_VENUE_CACHE, {})
    venues = cache.get("venues") if isinstance(cache.get("venues"), dict) else {}
    per: Dict[str, int] = {}
    total = 0
    for vid, row in venues.items():
        if vid.startswith("_") or not isinstance(row, dict):
            continue
        btc = 0.0
        for key in ("btc", "BTC", "btc_free"):
            try:
                btc = float(row.get(key) or 0)
            except (TypeError, ValueError):
                btc = 0.0
            if btc > 0:
                break
        sats = _coins_to_sats(btc)
        if sats:
            per[vid] = sats
            total += sats
    return {
        "ok": bool(per),
        "sats": total,
        "venues": per,
        "cached_at": cache.get("cached_at"),
    }


def _daemon_trade_sats(*, btc_usd: float) -> Dict[str, Any]:
    """Daemon PPP + grid fills → trade sats (USD notional as BTC-sats equivalent)."""
    ppp_rows = _tail_jsonl(_PPP_LEDGER, 800)
    fills = []
    trade_sats = 0
    pnl_usd = 0.0
    for row in ppp_rows:
        if row.get("phase") != "execute":
            continue
        if row.get("decision") not in ("fill", "paper", "live"):
            continue
        exe = row.get("execution") if isinstance(row.get("execution"), dict) else {}
        if not exec.get("success") and row.get("decision") not in ("paper",):
            # still count paper / attempted fills with fill_usd
            if not exec.get("fill_usd") and not row.get("notional_usd"):
                continue
        fill_usd = float(exec.get("fill_usd") or row.get("notional_usd") or 0)
        realized = float(exec.get("realized_pnl_usd") or 0)
        sats = _usd_to_btc_sats(fill_usd, btc_usd)
        trade_sats += abs(sats)
        pnl_usd += realized
        fills.append(
            {
                "ts": row.get("ts"),
                "symbol": row.get("symbol"),
                "path_id": row.get("path_id"),
                "fill_usd": round(fill_usd, 4),
                "realized_pnl_usd": round(realized, 4),
                "sats": abs(sats),
                "mode": row.get("mode") or row.get("decision"),
                "source": "ppp",
            }
        )

    grid_rows = _tail_jsonl(_GRID_LEDGER, 400)
    grid_fills = 0
    for row in grid_rows:
        grid_fills += 1
        try:
            size = float(row.get("size_base") or 0)
            price = float(row.get("price") or 0)
            usd = abs(size * price)
        except (TypeError, ValueError):
            usd = 0.0
        try:
            pnl = float(row.get("realized_delta_usd") or 0)
        except (TypeError, ValueError):
            pnl = 0.0
        sats = _usd_to_btc_sats(usd, btc_usd)
        trade_sats += abs(sats)
        pnl_usd += pnl
        fills.append(
            {
                "ts": row.get("ts"),
                "symbol": row.get("asset") or row.get("symbol"),
                "fill_usd": round(usd, 4),
                "realized_pnl_usd": round(pnl, 4),
                "sats": abs(sats),
                "mode": row.get("mode"),
                "venue": row.get("venue"),
                "source": "grid",
            }
        )

    fills = list(reversed(fills))[:40]
    hb = _read_json(_HEARTBEAT, {})
    return {
        "ok": True,
        "trade_sats": trade_sats,
        "fill_count": len(fills),
        "ppp_fill_rows": sum(1 for f in fills if f.get("source") == "ppp"),
        "grid_fill_rows": grid_fills,
        "realized_pnl_usd": round(pnl_usd, 4),
        "pnl_sats": abs(_usd_to_btc_sats(pnl_usd, btc_usd)),
        "recent_fills": fills[:12],
        "daemon_updated_at": hb.get("updated_at"),
        "btc_usd": btc_usd,
    }


def collect_sats_snapshot() -> Dict[str, Any]:
    """Network sats + daemon trade sats for the lobby monitor."""
    btc_usd = _btc_usd_guess()
    network = _mn2_network_sats()
    venues = _venue_btc_sats()
    trades = _daemon_trade_sats(btc_usd=btc_usd)
    network_sats = int(network.get("total_sats") or network.get("sats") or 0) + int(venues.get("sats") or 0)
    trade_sats = int(trades.get("trade_sats") or 0)
    return {
        "success": True,
        "updated_at": _iso(),
        "unit": "sats",
        "sats_per_coin": SATS_PER_COIN,
        "network": {
            "sats": network_sats,
            "mn2": network,
            "venue_btc": venues,
            "label": "Network sats",
        },
        "daemon_trades": {
            "sats": trade_sats,
            "detail": trades,
            "label": "Daemon trade sats",
        },
        "totals": {
            "network_sats": network_sats,
            "trade_sats": trade_sats,
            "combined_sats": network_sats + trade_sats,
        },
        "btc_usd": btc_usd,
    }


def _fmt_sats(n: int) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def _scene(
    *,
    category: str,
    title: str,
    body: str,
    sats: int = 0,
    sats_kind: str = "",
    duration_ms: int = 12000,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    fx = dict(SCENE_FX.get(category) or SCENE_FX["system"])
    return {
        "id": f"pipe_{uuid.uuid4().hex[:10]}",
        "category": category,
        "title": title[:160],
        "body": body[:400],
        "sats": int(sats or 0),
        "sats_kind": sats_kind,
        "sats_label": _fmt_sats(int(sats or 0)),
        "duration_ms": max(4000, int(duration_ms)),
        "fx": fx,
        "meta": meta or {},
    }


def _sats_fingerprint(sats: Dict[str, Any]) -> str:
    totals = sats.get("totals") or {}
    trades = (sats.get("daemon_trades") or {}).get("detail") or {}
    return "|".join(
        [
            str(int(totals.get("network_sats") or 0)),
            str(int(totals.get("trade_sats") or 0)),
            str(int(trades.get("fill_count") or 0)),
            str(round(float(trades.get("realized_pnl_usd") or 0), 4)),
            str(trades.get("daemon_updated_at") or ""),
        ]
    )


def _procedural_ai_pipeline(
    sats: Dict[str, Any],
    actions: List[Dict[str, Any]],
    *,
    entropy: Optional[str] = None,
) -> Dict[str, Any]:
    """Generative AI pipeline — every cut is different; driven by live sats + entropy."""
    network_sats = int((sats.get("totals") or {}).get("network_sats") or 0)
    trade_sats = int((sats.get("totals") or {}).get("trade_sats") or 0)
    fills = list(((sats.get("daemon_trades") or {}).get("detail") or {}).get("recent_fills") or [])
    venues = ((sats.get("network") or {}).get("venue_btc") or {}).get("venues") or {}
    mn2 = (sats.get("network") or {}).get("mn2") or {}
    seed_src = f"{entropy or ''}:{_sats_fingerprint(sats)}:{time.time_ns()}"
    rng = random.Random(seed_src)
    rng.shuffle(fills)

    scenes: List[Dict[str, Any]] = []
    cut_id = rng.randint(1000, 9999)
    scenes.append(
        _scene(
            category="finale",
            title=f"AI lobby pipeline · cut {cut_id}",
            body=(
                f"Fresh 12-minute reel from live sats (network {_fmt_sats(network_sats)} · "
                f"trades {_fmt_sats(trade_sats)}) — lights + sounds, not archived."
            ),
            sats=network_sats + trade_sats,
            sats_kind="combined",
            duration_ms=12000 + rng.randint(0, 4000),
        )
    )
    scenes.append(
        _scene(
            category="network",
            title="Network sats open",
            body=f"On-chain MN2 wallet reads {_fmt_sats(int(mn2.get('sats') or 0))} sats"
            f" ({float(mn2.get('coins') or 0):.4f} MN2).",
            sats=int(mn2.get("sats") or 0),
            sats_kind="network",
            duration_ms=13000,
        )
    )
    if venues:
        for vid, vsats in list(venues.items())[:4]:
            scenes.append(
                _scene(
                    category="network",
                    title=f"{vid} venue sats",
                    body=f"Cached venue BTC free → {_fmt_sats(vsats)} sats on {vid}.",
                    sats=int(vsats),
                    sats_kind="network",
                    duration_ms=11000,
                    meta={"venue": vid},
                )
            )
    else:
        scenes.append(
            _scene(
                category="network",
                title="Venue sats pending",
                body="Venue BTC cache is empty — pipeline keeps network MN2 sats on screen.",
                sats=network_sats,
                sats_kind="network",
                duration_ms=10000,
            )
        )

    scenes.append(
        _scene(
            category="trade",
            title="Daemon trade desk",
            body=f"Profit daemon + grid ledger map to {_fmt_sats(trade_sats)} trade sats.",
            sats=trade_sats,
            sats_kind="trade",
            duration_ms=13000,
        )
    )

    # Expand fills into cinematic beats
    for i, fill in enumerate(fills[:24]):
        sym = fill.get("symbol") or "pair"
        scenes.append(
            _scene(
                category="trade" if i % 3 else "profit",
                title=f"Fill · {sym}",
                body=(
                    f"{fill.get('source', 'daemon')} {fill.get('mode') or ''} — "
                    f"${float(fill.get('fill_usd') or 0):.2f} → {_fmt_sats(int(fill.get('sats') or 0))} sats"
                    f" · PnL ${float(fill.get('realized_pnl_usd') or 0):.4f}"
                ),
                sats=int(fill.get("sats") or 0),
                sats_kind="trade",
                duration_ms=10000 + (i % 4) * 1000,
                meta={"fill": fill},
            )
        )

    # Learned actions interleaved
    for i, act in enumerate((actions or [])[:16]):
        scenes.append(
            _scene(
                category="action",
                title=str(act.get("title") or act.get("type") or "action"),
                body=str(act.get("text") or act.get("title") or "Learned platform action"),
                sats=0,
                sats_kind="action",
                duration_ms=9000 + (i % 3) * 1500,
                meta={"action_id": act.get("id"), "action_category": act.get("category")},
            )
        )

    # Pad to ~12 minutes with shuffled generative refrains (unique each cut).
    motifs = [
        ("network", "Sats pulse", "Network sats breathe with the spectrum lightshow."),
        ("trade", "Daemon echo", "Trade sats chase the bezel — one fill, one chime."),
        ("profit", "PnL heartbeat", "Realized PnL pulse keeps the lobby honest."),
        ("wallet", "Wallet glow", "MN2 wallet sats glow green on every beat."),
        ("system", "Pipeline tick", "Twelve-minute clock advances — recount on the next window."),
        ("action", "Action remix", "Learned actions remix into the live sats story."),
    ]
    rng.shuffle(motifs)
    idx = 0
    while len(scenes) < TARGET_SCENES:
        cat, title, body = motifs[idx % len(motifs)]
        sats_val = network_sats if cat == "network" else trade_sats if cat in ("trade", "profit") else 0
        jitter = rng.randint(-1200, 2400)
        scenes.append(
            _scene(
                category=cat,
                title=f"{title} · beat {idx + 1} · cut {cut_id}",
                body=body + f" Live recount {_fmt_sats(network_sats + trade_sats)} sats.",
                sats=sats_val,
                sats_kind="network" if cat == "network" else "trade" if cat in ("trade", "profit") else "action",
                duration_ms=max(5000, 10000 + (idx % 5) * 800 + jitter),
            )
        )
        idx += 1

    scenes.append(
        _scene(
            category="finale",
            title=f"Cut {cut_id} complete — next movie will recount",
            body=(
                f"Window closed — network {_fmt_sats(network_sats)} · trades {_fmt_sats(trade_sats)}. "
                "Nothing archived; the next 12 minutes rebuild from fresh stats."
            ),
            sats=network_sats + trade_sats,
            sats_kind="combined",
            duration_ms=14000 + rng.randint(0, 4000),
        )
    )

    out = _normalize_duration(scenes, generator="procedural_ai")
    out["cut_id"] = cut_id
    out["fingerprint"] = _sats_fingerprint(sats)
    return out


def _normalize_duration(scenes: List[Dict[str, Any]], *, generator: str) -> Dict[str, Any]:
    """Stretch or trim scene durations so the reel is exactly ~12 minutes."""
    if not scenes:
        scenes = [
            _scene(
                category="system",
                title="Empty pipeline",
                body="No sats yet — waiting for network + daemon data.",
                duration_ms=PIPELINE_MS,
            )
        ]
    total = sum(int(s.get("duration_ms") or 0) for s in scenes)
    if total <= 0:
        total = len(scenes) * 12000
        for s in scenes:
            s["duration_ms"] = 12000
    scale = PIPELINE_MS / float(total)
    # Keep scale near 1 unless far off; clamp so scenes stay watchable
    if scale < 0.55 or scale > 2.4:
        # Rebuild even durations
        each = max(5000, PIPELINE_MS // max(1, len(scenes)))
        running = 0
        for s in scenes[:-1]:
            s["duration_ms"] = each
            running += each
        scenes[-1]["duration_ms"] = max(5000, PIPELINE_MS - running)
    else:
        running = 0
        for s in scenes[:-1]:
            s["duration_ms"] = max(4000, int(round(int(s["duration_ms"]) * scale)))
            running += s["duration_ms"]
        scenes[-1]["duration_ms"] = max(4000, PIPELINE_MS - running)

    duration = sum(int(s.get("duration_ms") or 0) for s in scenes)
    return {
        "success": True,
        "generator": generator,
        "pipeline_minutes": PIPELINE_MINUTES,
        "duration_ms": duration,
        "duration_label": f"{PIPELINE_MINUTES} min",
        "scene_count": len(scenes),
        "bpm": BPM,
        "scenes": scenes,
        "updated_at": _iso(),
    }


def _ai_llm_pipeline(sats: Dict[str, Any], actions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Ask the LLM to narrate scene titles/bodies; durations filled locally to 12 min."""
    try:
        from backend.services import llm_service
    except Exception:
        return None
    if not llm_service.is_available():
        return None

    totals = sats.get("totals") or {}
    fills = ((sats.get("daemon_trades") or {}).get("detail") or {}).get("recent_fills") or []
    prompt = (
        "You generate a 12-minute entertainment pipeline for a crypto lobby monitor.\n"
        "Return ONLY JSON: {\"scenes\":[{\"category\":\"network|trade|profit|wallet|action|finale|system\","
        "\"title\":\"...\",\"body\":\"...\",\"sats\":0,\"sats_kind\":\"network|trade|combined|action\"}]}\n"
        f"Network sats: {totals.get('network_sats')}. Trade sats: {totals.get('trade_sats')}.\n"
        f"Recent fills: {json.dumps(fills[:8], default=str)[:1200]}\n"
        f"Actions: {json.dumps([{'title': a.get('title'), 'category': a.get('category')} for a in (actions or [])[:8]], default=str)[:800]}\n"
        f"Produce about {TARGET_SCENES} scenes covering network sats, daemon trades, actions, and a finale."
    )

    def _call():
        return llm_service.fast(
            prompt,
            system_prompt="You are a concise crypto lobby VJ. Output valid JSON only.",
            max_tokens=3500,
            timeout=7,
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_call)
            resp = fut.result(timeout=9.0)
        if not getattr(resp, "success", False):
            return None
        text = (
            getattr(resp, "text", None)
            or getattr(resp, "content", None)
            or (resp.raw.get("content") if isinstance(getattr(resp, "raw", None), dict) else None)
            or ""
        )
        if not text and hasattr(resp, "raw"):
            text = str(resp.raw)
        text = str(text or "")
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        data = json.loads(text[start : end + 1])
        raw = data.get("scenes") if isinstance(data, dict) else None
        if not isinstance(raw, list) or not raw:
            return None
        scenes = []
        for row in raw[:80]:
            if not isinstance(row, dict):
                continue
            cat = str(row.get("category") or "system")
            if cat not in SCENE_FX:
                cat = "system"
            try:
                sats_n = int(row.get("sats") or 0)
            except (TypeError, ValueError):
                sats_n = 0
            scenes.append(
                _scene(
                    category=cat,
                    title=str(row.get("title") or "Scene"),
                    body=str(row.get("body") or ""),
                    sats=sats_n,
                    sats_kind=str(row.get("sats_kind") or ""),
                    duration_ms=12000,
                )
            )
        if len(scenes) < 8:
            return None
        return _normalize_duration(scenes, generator="llm_ai")
    except Exception:
        return None


def build_pipeline(
    *,
    force: bool = False,
    use_llm: bool = True,
    reason: str = "manual",
) -> Dict[str, Any]:
    """Build the current 12-minute movie from live sats.

    - Regenerates when stats fingerprint changes
    - Hard recount every 12 minutes
    - Overwrites the single working cut — never keeps a history of movies
    """
    global _CURRENT
    with _LOCK:
        sats = collect_sats_snapshot()
        fp = _sats_fingerprint(sats)
        now = time.time()
        cached = _CURRENT if _CURRENT.get("scenes") else _read_json(_PIPELINE_PATH, {})
        age = now - float(cached.get("epoch") or 0)
        same_fp = cached.get("fingerprint") == fp
        within_window = age < RECOUNT_SEC

        if not force and cached.get("scenes") and same_fp and within_window:
            cached = dict(cached)
            cached["success"] = True
            cached["cache_age_sec"] = round(age, 2)
            cached["recount_in_sec"] = max(0, int(RECOUNT_SEC - age))
            cached["interactive"] = True
            return cached

        actions: List[Dict[str, Any]] = []
        try:
            from backend.services.landing_monitor_actions_service import list_actions

            actions = list_actions(limit=20).get("actions") or []
        except Exception:
            actions = []

        regen_reason = reason
        if force:
            regen_reason = reason or "force"
        elif not same_fp:
            regen_reason = "stats_changed"
        elif not within_window:
            regen_reason = "12m_recount"

        pipe = None
        if use_llm:
            pipe = _ai_llm_pipeline(sats, actions)
        if not pipe:
            pipe = _procedural_ai_pipeline(sats, actions, entropy=f"{regen_reason}:{now}")

        payload = {
            **pipe,
            "epoch": now,
            "fingerprint": fp,
            "regen_reason": regen_reason,
            "recount_every_sec": RECOUNT_SEC,
            "recount_in_sec": RECOUNT_SEC,
            "persist": False,
            "interactive": True,
            "sats": sats,
            "ai": {
                "mode": pipe.get("generator"),
                "label": "AI generative 12-minute pipeline (live recount)",
                "lights": True,
                "sounds": True,
                "unique_each_cut": True,
            },
        }
        _CURRENT = payload
        # Scratch mirror only — always overwrite the same file; no archive.
        try:
            scratch = {
                "epoch": payload["epoch"],
                "fingerprint": fp,
                "cut_id": payload.get("cut_id"),
                "generator": payload.get("generator"),
                "scene_count": payload.get("scene_count"),
                "duration_ms": payload.get("duration_ms"),
                "regen_reason": regen_reason,
                "sats_totals": (sats.get("totals") or {}),
                # Intentionally omit full scenes history from disk.
            }
            _write_json(_PIPELINE_PATH, scratch)
        except Exception:
            pass
        return payload


def get_pipeline(*, max_age_sec: Optional[float] = None) -> Dict[str, Any]:
    """Return current cut; rebuild on new stats or when the 12m window ends."""
    # max_age_sec kept for callers; recount cadence is the 12-minute window.
    _ = max_age_sec
    return build_pipeline(force=False, use_llm=False, reason="get")
