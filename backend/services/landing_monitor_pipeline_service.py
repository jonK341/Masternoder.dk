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
TARGET_SCENES = 50  # ~14.4s each → exactly 12 minutes
BPM = 180
# Hard recount cadence: every movie window forces a fresh recount of live sats.
RECOUNT_SEC = PIPELINE_MINUTES * 60
_ART_DIR = os.path.join(_BASE, "static", "landing_monitor", "scene_art")

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
        "speaker": "performer_nova",
    },
    "trade": {
        "lightshow": "chase",
        "title": "Daemon trade chase",
        "explain": "Chase nodes fire on every daemon fill — trade energy around the bezel.",
        "color": "#ffd166",
        "sound": "chime_cash",
        "bars": 6,
        "speaker": "performer_ember",
    },
    "profit": {
        "lightshow": "pulse",
        "title": "Profit pulse",
        "explain": "Deep pulse for realized PnL beats.",
        "color": "#ffd166",
        "sound": "fanfare_rise",
        "bars": 4,
        "speaker": "performer_honey",
    },
    "wallet": {
        "lightshow": "spectrum",
        "title": "Wallet spectrum",
        "explain": "Wallet / MN2 balance hits.",
        "color": "#00ff88",
        "sound": "glitter_burst",
        "bars": 4,
        "speaker": "performer_luna",
    },
    "action": {
        "lightshow": "wave",
        "title": "Action waves",
        "explain": "Learned platform actions roll through as cyan waves.",
        "color": "#00d4ff",
        "sound": "whoosh_rise",
        "bars": 5,
        "speaker": "performer_iris",
    },
    "finale": {
        "lightshow": "rainbow",
        "title": "Pipeline finale",
        "explain": "Rainbow wash closes the 12-minute AI reel.",
        "color": "#c77dff",
        "sound": "sparkle_cascade",
        "bars": 8,
        "speaker": "performer_venus",
    },
    "system": {
        "lightshow": "pulse",
        "title": "System pulse",
        "explain": "Ops beat keeping the pipeline honest.",
        "color": "#9aa4b2",
        "sound": "tick_blip",
        "bars": 3,
        "speaker": "performer_sage",
    },
    "social": {
        "lightshow": "wave",
        "title": "Online leaderboard",
        "explain": "Recently active users climb the live board.",
        "color": "#c77dff",
        "sound": "bubble_ping",
        "bars": 5,
        "speaker": "performer_aurora",
    },
    "generator": {
        "lightshow": "wave",
        "title": "Generator glow",
        "explain": "Vidgenerator and MasterNoder2 creative stack.",
        "color": "#00d4ff",
        "sound": "whoosh_rise",
        "bars": 5,
        "speaker": "performer_iris",
    },
}

# Rotate camgirl hosts so spoken stats stay varied across the cut.
SPEAKER_ROTATION = (
    "performer_nova",
    "performer_luna",
    "performer_ember",
    "performer_iris",
    "performer_honey",
    "performer_storm",
    "performer_pixie",
    "performer_venus",
    "performer_sage",
    "performer_aurora",
)


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
        execution = row.get("execution") if isinstance(row.get("execution"), dict) else {}
        if not execution.get("success") and row.get("decision") not in ("paper",):
            # still count paper / attempted fills with fill_usd
            if not execution.get("fill_usd") and not row.get("notional_usd"):
                continue
        fill_usd = float(execution.get("fill_usd") or row.get("notional_usd") or 0)
        realized = float(execution.get("realized_pnl_usd") or 0)
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


def _fmt_compact(n: Any) -> str:
    try:
        v = float(n or 0)
    except (TypeError, ValueError):
        return "0"
    abs_v = abs(v)
    if abs_v >= 1e12:
        return f"{v / 1e12:.2f}".rstrip("0").rstrip(".") + "T"
    if abs_v >= 1e9:
        return f"{v / 1e9:.2f}".rstrip("0").rstrip(".") + "B"
    if abs_v >= 1e6:
        return f"{v / 1e6:.2f}".rstrip("0").rstrip(".") + "M"
    if abs_v >= 1e3:
        return f"{v / 1e3:.1f}".rstrip("0").rstrip(".") + "K"
    return str(int(round(v)))


def collect_online_leaderboard(*, limit: int = 10, recent_hours: int = 24) -> Dict[str, Any]:
    """Recently active users ranked with XP — soft 'online' leaderboard."""
    limit = max(1, min(25, int(limit or 10)))
    recent_hours = max(1, min(168, int(recent_hours or 24)))
    rows: List[Dict[str, Any]] = []
    source = "empty"

    try:
        from sqlalchemy import text
        from backend.extensions import db

        q = text(
            """
            SELECT user_id, username, last_login
            FROM user_accounts
            WHERE last_login IS NOT NULL
              AND last_login >= datetime('now', :window)
            ORDER BY last_login DESC
            LIMIT :lim
            """
        )
        # SQLite window; also try postgres-friendly fallback if needed.
        try:
            result = db.session.execute(q, {"window": f"-{recent_hours} hours", "lim": limit * 3})
            raw = result.fetchall()
        except Exception:
            q2 = text(
                """
                SELECT user_id, username, last_login
                FROM user_accounts
                WHERE last_login IS NOT NULL
                ORDER BY last_login DESC
                LIMIT :lim
                """
            )
            raw = db.session.execute(q2, {"lim": limit * 3}).fetchall()
        for r in raw:
            rows.append(
                {
                    "user_id": str(r[0] or ""),
                    "username": str(r[1] or r[0] or "user"),
                    "last_login": str(r[2]) if r[2] is not None else None,
                    "xp": 0,
                    "online": True,
                }
            )
        if rows:
            source = "user_accounts_recent"
    except Exception:
        rows = []

    # Merge / fill from XP points DB (same source as /api/leaderboard).
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:

            def _xp_board() -> List[Dict[str, Any]]:
                from backend.services.unified_points_database import unified_points_db

                all_data = unified_points_db.get_all_users_points() or {}
                players: List[Dict[str, Any]] = []
                for uid, data in all_data.items():
                    if not isinstance(data, dict):
                        continue
                    try:
                        xp = int(float(data.get("xp_total", data.get("xp", 0)) or 0))
                    except (TypeError, ValueError):
                        xp = 0
                    players.append(
                        {
                            "user_id": str(uid),
                            "username": str(data.get("display_name") or data.get("username") or uid),
                            "xp": xp,
                        }
                    )
                players.sort(key=lambda p: int(p.get("xp") or 0), reverse=True)
                return players[:80]

            fut = pool.submit(_xp_board)
            board = fut.result(timeout=0.9)
        xp_map = {str(p.get("user_id") or ""): int(p.get("xp") or 0) for p in board}
        name_map = {str(p.get("user_id") or ""): str(p.get("username") or "") for p in board}
        if rows:
            for row in rows:
                uid = row["user_id"]
                row["xp"] = int(xp_map.get(uid) or row.get("xp") or 0)
                if name_map.get(uid):
                    row["username"] = name_map[uid]
            rows.sort(key=lambda x: (-int(x.get("xp") or 0), str(x.get("username") or "")))
        else:
            for p in board[:limit]:
                rows.append(
                    {
                        "user_id": str(p.get("user_id") or ""),
                        "username": str(p.get("username") or p.get("user_id") or "player"),
                        "last_login": None,
                        "xp": int(p.get("xp") or 0),
                        "online": False,
                    }
                )
            if rows:
                source = "xp_leaderboard"
    except Exception:
        pass

    if not rows:
        # Visible lobby board even on cold DBs — marked offline seeds.
        seeds = [
            ("hunter_alpha", "Hunter Alpha", 12500),
            ("creator_01", "Creator Prime", 9800),
            ("noder_master", "NoderMaster", 7200),
            ("video_wizard", "VideoWizard", 5500),
            ("battle_king", "BattleKing", 3100),
        ]
        for uid, name, xp in seeds[:limit]:
            rows.append(
                {
                    "user_id": uid,
                    "username": name,
                    "last_login": None,
                    "xp": xp,
                    "online": False,
                }
            )
        source = "seed_board"

    for i, row in enumerate(rows[:limit]):
        row["rank"] = i + 1
    return {
        "success": True,
        "updated_at": _iso(),
        "source": source,
        "recent_hours": recent_hours,
        "count": len(rows[:limit]),
        "leaderboard": rows[:limit],
    }


def _art_prompt(*, category: str, title: str, body: str) -> str:
    mood = {
        "network": "emerald neon blockchain city, satoshi rain, MasterNoder2 node glow",
        "trade": "daemon trading desk, amber charts, crypto fills sparks",
        "profit": "golden profit pulse, vault light, triumphant lobby",
        "wallet": "MN2 wallet hologram, green satoshis, sleek crypto wallet",
        "action": "live user activity streams, cyan motion trails",
        "social": "online leaderboard hologram, ranked avatars, social lobby",
        "generator": "AI video generator studio, MasterNoder2 creative lab",
        "finale": "rainbow lobby finale, MasterNoder2 billboard",
        "system": "ops monitor grid, cool steel HUD",
    }.get(category, "MasterNoder2 crypto lobby monitor")
    return (
        f"Cinematic still for MasterNoder2 lobby monitor, {mood}, "
        f"about {title}: {body[:120]}, no readable text, ultra detailed, soft film grain"
    )


def _scene_image_fields(*, category: str, title: str, body: str, seed: int) -> Dict[str, Any]:
    """Hotlink a freshly seeded Pollinations still; browser treats it as the clip art."""
    import urllib.parse

    prompt = _art_prompt(category=category, title=title, body=body)
    encoded = urllib.parse.quote(prompt[:360], safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=960&height=540&nologo=true&enhance=true&seed={int(seed) & 0x7FFFFFFF}"
    )
    return {
        "image_url": url,
        "image_prompt": prompt[:280],
        "image_seed": int(seed) & 0x7FFFFFFF,
        "image_kind": "ai_still",
    }


def _speak_line(
    *,
    category: str,
    title: str,
    body: str,
    sats: int,
    sats_kind: str,
    speaker_name: str = "",
) -> str:
    """Daemon-human spoken line — conversational, not robotic announce."""
    kind = sats_kind or category
    sats_txt = _fmt_compact(int(sats or 0))
    host = (speaker_name or "Host").split()[0]
    soft = body.strip().rstrip(".")
    if kind == "network" or category == "network":
        return (
            f"Hey, it's {host}. Network sats are sitting at {sats_txt} right now. "
            f"{title} — {soft}."
        )[:420]
    if kind == "trade" or category in ("trade", "profit"):
        return (
            f"{host} on the daemon desk. Trade sats just printed {sats_txt}. "
            f"{title}. {soft}."
        )[:420]
    if kind == "combined" or category == "finale":
        return (
            f"Alright — {host} wrapping this cut. Combined sats land at {sats_txt}. "
            f"{title}."
        )[:420]
    if category == "wallet":
        return f"{host} here with the wallet glow. {sats_txt} sats on MN2. {title}."[:420]
    if category == "social":
        return f"{host} checking who's online. {title}. {soft}."[:420]
    if category == "generator":
        return f"{host} peeking at MasterNoder2. {title}. {soft}."[:420]
    if category == "action":
        return f"{host} catching live activity. {title}. {soft[:140]}."[:420]
    return f"{host} on the monitor. {title}. {soft}."[:420]


def _scene(
    *,
    category: str,
    title: str,
    body: str,
    sats: int = 0,
    sats_kind: str = "",
    duration_ms: int = 14000,
    meta: Optional[Dict[str, Any]] = None,
    speaker_id: Optional[str] = None,
    speaker_index: int = 0,
    art_seed: Optional[int] = None,
) -> Dict[str, Any]:
    fx = dict(SCENE_FX.get(category) or SCENE_FX["system"])
    sid = speaker_id or fx.get("speaker") or SPEAKER_ROTATION[speaker_index % len(SPEAKER_ROTATION)]
    speak = _speak_line(
        category=category,
        title=title,
        body=body,
        sats=int(sats or 0),
        sats_kind=sats_kind,
        speaker_name=sid.replace("performer_", "").title(),
    )
    voice_budget_ms = max(5000, min(16000, 70 * max(24, len(speak))))
    dur = max(int(duration_ms), voice_budget_ms)
    seed = int(art_seed if art_seed is not None else (uuid.uuid4().int % 10_000_000))
    art = _scene_image_fields(category=category, title=title, body=body, seed=seed)
    return {
        "id": f"pipe_{uuid.uuid4().hex[:10]}",
        "category": category,
        "title": title[:160],
        "body": body[:400],
        "speak": speak[:420],
        "speaker_id": sid,
        "sats": int(sats or 0),
        "sats_kind": sats_kind,
        "sats_label": _fmt_sats(int(sats or 0)),
        "duration_ms": max(5000, dur),
        "sync": {
            "voice": True,
            "sfx": True,
            "lights": True,
            "hold_for_speech": True,
            "beat_ms": int(round(60_000 / BPM)),
        },
        "fx": fx,
        "image_url": art["image_url"],
        "image_prompt": art["image_prompt"],
        "image_seed": art["image_seed"],
        "image_kind": art["image_kind"],
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


def _platform_stat_scenes(rng: random.Random) -> List[Dict[str, Any]]:
    """Nice-to-know MasterNoder2 / platform clips (disk cache only — never block)."""
    stats: Dict[str, Any] = {}
    try:
        snap = _read_json(os.path.join(_BASE, "data", "landing_monitor_cache.json"), {})
        if isinstance(snap, dict):
            stats = snap.get("stats") if isinstance(snap.get("stats"), dict) else {}
    except Exception:
        stats = {}

    facts = [
        (
            "generator",
            "MasterNoder2 video lab",
            f"Vidgenerator holds {_fmt_compact(stats.get('total_videos') or 0)} videos — AI clips, music, and lobby FX.",
            int(stats.get("total_videos") or 0),
            "action",
        ),
        (
            "social",
            "Platform users",
            f"{_fmt_compact(stats.get('total_users') or 0)} profiles on the ledger — battles, wallets, and streams.",
            int(stats.get("total_users") or 0),
            "action",
        ),
        (
            "action",
            "Battle arena pulse",
            f"{_fmt_compact(stats.get('total_battles') or 0)} battles logged across the MasterNoder2 arena.",
            int(stats.get("total_battles") or 0),
            "action",
        ),
        (
            "wallet",
            "MN2 spot check",
            (
                f"MN2 prints around ${float(stats.get('mn2_usd_price') or 0):.4f} — "
                "one coin is one hundred million sats."
                if stats.get("mn2_usd_price") is not None
                else "One MN2 equals one hundred million sats on MasterNoder2."
            ),
            0,
            "wallet",
        ),
        (
            "system",
            "Daemon health",
            (
                "Chain daemon is online and feeding the lobby."
                if stats.get("daemon_ok") is True
                else "Daemon status is soft — pipeline still reads cached sats."
            ),
            int(stats.get("block_height") or 0),
            "action",
        ),
        (
            "generator",
            "MasterNoder2 stack",
            "Agents, shop, trophies, and the AI pipeline share one lobby — stats feed every clip.",
            0,
            "action",
        ),
        (
            "wallet",
            "Sats math",
            "MasterNoder2 treats MN2 like bitcoin math — eight decimals, sats on screen.",
            SATS_PER_COIN,
            "network",
        ),
    ]
    rng.shuffle(facts)
    out: List[Dict[str, Any]] = []
    for cat, title, body, sats_n, kind in facts:
        # Map accidental battle → action for FX table.
        if cat not in SCENE_FX:
            cat = "action"
        out.append(
            {
                "category": cat,
                "title": title,
                "body": body,
                "sats": int(sats_n or 0),
                "sats_kind": kind,
                "duration_ms": 12000 + rng.randint(0, 3000),
            }
        )
    return out


def _trim_to_target(scenes: List[Dict[str, Any]], target: int) -> List[Dict[str, Any]]:
    """Keep opener + finale and a diverse middle totaling exactly `target` scenes."""
    if len(scenes) <= target:
        return scenes
    if target <= 2:
        return scenes[:target]
    head = scenes[:1]
    tail = scenes[-1:]
    middle = scenes[1:-1]
    keep = target - 2
    if len(middle) <= keep:
        return head + middle + tail
    # Prefer category diversity while trimming.
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for s in middle:
        buckets.setdefault(str(s.get("category") or "system"), []).append(s)
    picked: List[Dict[str, Any]] = []
    while len(picked) < keep and any(buckets.values()):
        for cat in list(buckets.keys()):
            if len(picked) >= keep:
                break
            if buckets[cat]:
                picked.append(buckets[cat].pop(0))
    return head + picked[:keep] + tail


def _procedural_ai_pipeline(
    sats: Dict[str, Any],
    actions: List[Dict[str, Any]],
    *,
    entropy: Optional[str] = None,
) -> Dict[str, Any]:
    """Generative AI pipeline — 50 unique scenes / 12 min with art + online board."""
    network_sats = int((sats.get("totals") or {}).get("network_sats") or 0)
    trade_sats = int((sats.get("totals") or {}).get("trade_sats") or 0)
    fills = list(((sats.get("daemon_trades") or {}).get("detail") or {}).get("recent_fills") or [])
    venues = ((sats.get("network") or {}).get("venue_btc") or {}).get("venues") or {}
    mn2 = (sats.get("network") or {}).get("mn2") or {}
    seed_src = f"{entropy or ''}:{_sats_fingerprint(sats)}:{time.time_ns()}"
    rng = random.Random(seed_src)
    rng.shuffle(fills)
    online = collect_online_leaderboard(limit=10)
    board = list(online.get("leaderboard") or [])

    scenes: List[Dict[str, Any]] = []
    cut_id = rng.randint(1000, 9999)
    speaker_i = [rng.randint(0, len(SPEAKER_ROTATION) - 1)]

    def add_scene(**kwargs: Any) -> None:
        kwargs.setdefault("speaker_index", speaker_i[0])
        kwargs.setdefault("art_seed", rng.randint(1, 2_000_000_000))
        speaker_i[0] += 1
        scenes.append(_scene(**kwargs))

    add_scene(
        category="finale",
        title=f"AI lobby pipeline · cut {cut_id}",
        body=(
            f"Fifty fresh scenes, twelve minutes — network {_fmt_compact(network_sats)} sats, "
            f"trades {_fmt_compact(trade_sats)}, online board live. Nothing archived."
        ),
        sats=network_sats + trade_sats,
        sats_kind="combined",
        duration_ms=14000 + rng.randint(0, 2000),
    )
    add_scene(
        category="network",
        title="Network sats open",
        body=f"On-chain MN2 wallet reads {_fmt_compact(int(mn2.get('sats') or 0))} sats"
        f" ({float(mn2.get('coins') or 0):.4f} MN2).",
        sats=int(mn2.get("sats") or 0),
        sats_kind="network",
        duration_ms=14000,
    )
    if venues:
        for vid, vsats in list(venues.items())[:3]:
            add_scene(
                category="network",
                title=f"{vid} venue sats",
                body=f"Venue BTC free on {vid} maps to {_fmt_compact(vsats)} sats.",
                sats=int(vsats),
                sats_kind="network",
                duration_ms=12000,
                meta={"venue": vid},
            )
    else:
        add_scene(
            category="network",
            title="Venue sats pending",
            body="Venue BTC cache is quiet — MasterNoder2 still shows on-chain network sats.",
            sats=network_sats,
            sats_kind="network",
            duration_ms=12000,
        )

    add_scene(
        category="trade",
        title="Daemon trade desk",
        body=f"Profit daemon plus grid ledger print {_fmt_compact(trade_sats)} trade sats.",
        sats=trade_sats,
        sats_kind="trade",
        duration_ms=14000,
    )

    # Online users leaderboard — dedicated clips.
    if board:
        add_scene(
            category="social",
            title="Online users leaderboard",
            body=(
                "Top active players: "
                + ", ".join(
                    f"#{r.get('rank')} {r.get('username')} ({_fmt_compact(r.get('xp') or 0)} XP)"
                    for r in board[:5]
                )
            ),
            sats=len(board),
            sats_kind="action",
            duration_ms=15000,
            meta={"leaderboard": board[:10]},
        )
        for row in board[:8]:
            add_scene(
                category="social",
                title=f"#{row.get('rank')} {row.get('username')}",
                body=(
                    f"{row.get('username')} sits at {_fmt_compact(row.get('xp') or 0)} XP"
                    + (" and looks online right now." if row.get("online") else " on the board.")
                ),
                sats=int(row.get("xp") or 0),
                sats_kind="action",
                duration_ms=11000 + rng.randint(0, 2000),
                meta={"user": row},
            )
    else:
        add_scene(
            category="social",
            title="Online board warming up",
            body="Leaderboard is quiet — next logins will light the lobby ranks.",
            sats=0,
            sats_kind="action",
            duration_ms=12000,
        )

    for fact in _platform_stat_scenes(rng):
        add_scene(**fact)

    for i, fill in enumerate(fills[:12]):
        sym = fill.get("symbol") or "pair"
        add_scene(
            category="trade" if i % 3 else "profit",
            title=f"Fill · {sym}",
            body=(
                f"{fill.get('source', 'daemon')} {fill.get('mode') or ''} — "
                f"${float(fill.get('fill_usd') or 0):.2f} → {_fmt_compact(int(fill.get('sats') or 0))} sats"
                f", PnL ${float(fill.get('realized_pnl_usd') or 0):.4f}"
            ),
            sats=int(fill.get("sats") or 0),
            sats_kind="trade",
            duration_ms=11000 + (i % 4) * 800,
            meta={"fill": fill},
        )

    for i, act in enumerate((actions or [])[:10]):
        add_scene(
            category="action",
            title=str(act.get("title") or act.get("type") or "action"),
            body=str(act.get("text") or act.get("title") or "Learned platform action"),
            sats=0,
            sats_kind="action",
            duration_ms=10000 + (i % 3) * 1200,
            meta={"action_id": act.get("id"), "action_category": act.get("category")},
        )

    motifs = [
        ("network", "Sats pulse", "Network sats breathe with the spectrum lightshow."),
        ("trade", "Daemon echo", "Trade sats chase the bezel — one fill, one chime."),
        ("profit", "PnL heartbeat", "Realized PnL pulse keeps the lobby honest."),
        ("wallet", "Wallet glow", "MN2 wallet sats glow green on every beat."),
        ("system", "Pipeline tick", "Twelve-minute clock advances — recount on the next window."),
        ("action", "Action remix", "Learned actions remix into the live sats story."),
        ("generator", "AI clip lab", "MasterNoder2 spins a new still for every scene."),
        ("social", "Crowd energy", "Online ranks keep the lobby human."),
    ]
    rng.shuffle(motifs)
    idx = 0
    # Leave one slot for the closing finale.
    while len(scenes) < TARGET_SCENES - 1:
        cat, title, body = motifs[idx % len(motifs)]
        sats_val = network_sats if cat == "network" else trade_sats if cat in ("trade", "profit") else 0
        jitter = rng.randint(-800, 1800)
        add_scene(
            category=cat,
            title=f"{title} · beat {idx + 1} · cut {cut_id}",
            body=body + f" Live recount {_fmt_compact(network_sats + trade_sats)} sats.",
            sats=sats_val,
            sats_kind="network" if cat == "network" else "trade" if cat in ("trade", "profit") else "action",
            duration_ms=max(8000, 11000 + (idx % 5) * 600 + jitter),
        )
        idx += 1

    add_scene(
        category="finale",
        title=f"Cut {cut_id} complete — next movie will recount",
        body=(
            f"Window closed — network {_fmt_compact(network_sats)} · trades {_fmt_compact(trade_sats)}. "
            "Fifty scenes done; the next twelve minutes rebuild from fresh stats."
        ),
        sats=network_sats + trade_sats,
        sats_kind="combined",
        duration_ms=14000 + rng.randint(0, 2000),
    )

    scenes = _trim_to_target(scenes, TARGET_SCENES)
    out = _normalize_duration(scenes, generator="procedural_ai")
    out["cut_id"] = cut_id
    out["fingerprint"] = _sats_fingerprint(sats)
    out["online_leaderboard"] = board[:10]
    out["target_scenes"] = TARGET_SCENES
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
        f"Produce exactly {TARGET_SCENES} scenes covering network sats, daemon trades, online users, "
        "MasterNoder2 facts, actions, and a finale."
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
                    speaker_index=len(scenes),
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
