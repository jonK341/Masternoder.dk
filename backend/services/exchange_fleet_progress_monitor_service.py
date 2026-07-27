"""Public-safe 5D fleet progress monitor — no PII, no admin secrets."""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_SENSITIVE_RE = re.compile(
    r"(paypal|email|@|api[_-]?key|secret|password|wallet|0x[a-fA-F0-9]{8,}|user_id)",
    re.I,
)


def monitor_public_enabled() -> bool:
    return os.environ.get("FLEET_PROGRESS_MONITOR_PUBLIC", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def embed_token_required() -> bool:
    return bool((os.environ.get("FLEET_MONITOR_EMBED_TOKEN") or "").strip())


def embed_authorized(got: str) -> bool:
    want = (os.environ.get("FLEET_MONITOR_EMBED_TOKEN") or "").strip()
    if not want:
        return True
    return bool((got or "").strip()) and got.strip() == want


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _scrub_text(text: str, *, max_len: int = 160) -> str:
    t = (text or "").strip()
    if _SENSITIVE_RE.search(t):
        return "Fleet activity signal"
    return t[:max_len]


def _anon_handle(seed: str, *, prefix: str = "Player") -> str:
    raw = (seed or "").strip()
    if not raw or _SENSITIVE_RE.search(raw):
        return prefix
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:6]
    return f"{prefix}-{digest}"


def _coarse_amount(val: Any) -> str:
    try:
        v = float(val or 0)
    except (TypeError, ValueError):
        return "—"
    if v < 1:
        return "<1"
    if v < 100:
        return f"~{int(round(v))}"
    if v < 10000:
        return f"~{int(round(v / 10) * 10)}"
    return "1k+"


def _coarse_profit_band(usd: float) -> str:
    v = float(usd or 0)
    sign = "+" if v >= 0 else "−"
    a = abs(v)
    if a < 0.5:
        return f"{sign}under $1"
    if a < 10:
        return f"{sign}~${int(round(a))}"
    if a < 100:
        return f"{sign}~${int(round(a / 5) * 5)}"
    if a < 1000:
        return f"{sign}~${int(round(a / 25) * 25)}"
    return f"{sign}$1k+"


def _coarse_skill_edge(bps: Any) -> str:
    try:
        v = float(bps or 0)
    except (TypeError, ValueError):
        return "—"
    if v < 20:
        return "low"
    if v < 50:
        return "mid"
    if v < 90:
        return "high"
    return "elite"


def _sanitize_bot(fb: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services.fleet_bot_visuals_service import enrich_bot_visuals

    prog = fb.get("progression") or {}
    visuals = enrich_bot_visuals(fb)
    return {
        "id": _scrub_text(str(fb.get("id") or "bot"), max_len=48),
        "label": fb.get("label") or "Fleet",
        "kind": fb.get("kind") or "fleet",
        "badge": visuals.get("badge") or fb.get("badge") or "",
        "type_label": fb.get("type_label") or "",
        "role_label": _scrub_text(str(fb.get("role_label") or ""), max_len=80),
        "enabled": bool(fb.get("enabled", True)),
        "last_tick_ok": None if not fb.get("last_run_at") else fb.get("last_run_ok") is not False,
        "level": int(prog.get("level") or 1),
        "rank_title": prog.get("rank_title") or "Recruit",
        "xp_progress_pct": float(prog.get("xp_progress_pct") or 0),
        "rewards_unlocked": int(prog.get("rewards_unlocked_count") or 0),
        "avatar_url": visuals.get("avatar_url"),
        "progress_image_url": visuals.get("progress_image_url"),
        "progress_tier": visuals.get("progress_tier"),
        "progress_label": visuals.get("progress_label"),
        "skill_count": int((fb.get("skill_meta") or {}).get("skill_count") or len(fb.get("skills") or [])),
        "skill_edge_band": _coarse_skill_edge((fb.get("skill_meta") or {}).get("blended_edge_bps")),
    }


def _activity_from_fleet_meta(meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for h in (meta.get("history") or [])[-12:]:
        out.append(
            {
                "at": h.get("ran_at"),
                "kind": h.get("kind") or "fleet",
                "ok": bool(h.get("ok")),
                "headline": _scrub_text(
                    f"Fleet run {h.get('kind') or 'all'} — {'ok' if h.get('ok') else 'partial'}"
                ),
            }
        )
    lr = meta.get("last_results") or {}
    for kind, row in lr.items():
        if not isinstance(row, dict):
            continue
        bc = row.get("bot_count")
        okc = row.get("ok_count")
        if bc is None:
            continue
        out.append(
            {
                "at": meta.get("last_run_at"),
                "kind": kind,
                "ok": bool(row.get("success")),
                "headline": _scrub_text(f"{kind}: {okc}/{bc} bots reported ok"),
            }
        )
    return out[-20:]


def _public_audit_ticks(limit: int = 12) -> List[Dict[str, Any]]:
    try:
        from backend.services import crypto_exchange_service as ex

        tail = ex.get_audit_tail(limit=80).get("records") or []
    except Exception:
        return []
    safe_actions = {
        "swap",
        "spatial_arbitrage",
        "arb_tick",
        "fleet_tick",
        "risk_denied",
    }
    out: List[Dict[str, Any]] = []
    for rec in reversed(tail):
        action = str(rec.get("action") or "")
        if action not in safe_actions and "arb" not in action and "fleet" not in action:
            continue
        out.append(
            {
                "at": rec.get("ts") or rec.get("at"),
                "action": action,
                "headline": _scrub_text(f"Trade lane · {action.replace('_', ' ')}"),
                "amount_band": _coarse_profit_band(float(rec.get("amount_usd") or 0)),
            }
        )
        if len(out) >= limit:
            break
    return out


def _public_casino_snapshot() -> Dict[str, Any]:
    recent: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"bets_today": 0, "tournament_joins": 0, "currencies": []}
    try:
        from backend.services.casino_service import get_activity_feed, get_activity_stats

        feed = get_activity_feed(limit=10)
        for row in feed.get("feed") or []:
            game = _scrub_text(str(row.get("game") or "casino"))
            cur = str(row.get("currency") or "coins")
            recent.append(
                {
                    "at": row.get("created_at"),
                    "source": "casino",
                    "headline": _scrub_text(
                        f"Casino · {game} · {_anon_handle(str(row.get('user_id') or ''))} · "
                        f"payout {_coarse_amount(row.get('payout'))} {cur}"
                    ),
                    "game": game,
                    "currency": cur,
                }
            )
        st = get_activity_stats(days=1)
        daily = st.get("daily") or []
        day_row = daily[-1] if daily else {}
        stats = {
            "bets_today": int(day_row.get("bets") or 0),
            "tournament_joins": int(st.get("tournament_joins") or 0),
            "wins_today": int(day_row.get("wins") or 0),
        }
        stats["volume_band"] = _coarse_amount(abs(float(day_row.get("total_net") or 0)))
    except Exception:
        pass

    try:
        from backend.services import casino_global_controller

        g = casino_global_controller.get_global_stats()
        totals = g.get("totals") or {}
        stats["total_bets"] = int(totals.get("bets") or 0)
        stats["active_players_band"] = _coarse_amount(totals.get("unique_players"))
        stats["house_band"] = _coarse_profit_band(float(totals.get("house_edge_profit") or 0))
    except Exception:
        pass

    return {"stats": stats, "recent": recent}


def _public_agents_snapshot() -> Dict[str, Any]:
    recent: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"total_agents": 0, "total_executions": 0, "skills_tracked": 0}
    try:
        from backend.services.agent_ability_tracker import agent_ability_tracker

        platform = agent_ability_tracker.get_all_stats()
        stats = {
            "total_agents": int(platform.get("total_agents") or 0),
            "total_executions": int(platform.get("total_executions") or 0),
            "skills_tracked": int(platform.get("total_skills_tracked") or 0),
        }
        for row in reversed(agent_ability_tracker.get_recent_activity(12)):
            aid = _scrub_text(str(row.get("agent_id") or "agent"), max_len=40)
            skill = _scrub_text(str(row.get("skill") or "skill"), max_len=40)
            ok = row.get("success")
            from backend.services.fleet_bot_visuals_service import agent_activity_avatar

            recent.append(
                {
                    "at": row.get("timestamp"),
                    "source": "agents",
                    "headline": _scrub_text(
                        f"Agent · {aid} · {skill} · {'ok' if ok else 'retry'}"
                    ),
                    "agent": aid,
                    "skill": skill,
                    "avatar_url": agent_activity_avatar(aid),
                }
            )
    except Exception:
        pass

    try:
        from backend.services import casino_agents_service as agents_svc

        spec = agents_svc.get_spectator_feed(limit=8)
        for row in spec.get("events") or spec.get("feed") or []:
            if not isinstance(row, dict):
                continue
            name = _scrub_text(str(row.get("agent_name") or row.get("agent_id") or "Agent"), max_len=48)
            game = _scrub_text(str(row.get("game") or "casino"))
            line = row.get("spectator_line") or f"{name} on {game}"
            recent.append(
                {
                    "at": row.get("ts"),
                    "source": "agents",
                    "headline": _scrub_text(f"Casino agent · {line}"),
                    "game": game,
                }
            )
    except Exception:
        pass

    return {"stats": stats, "recent": recent[:16]}


def _merge_activity_streams(
    fleet: List[Dict[str, Any]],
    casino: List[Dict[str, Any]],
    agents: List[Dict[str, Any]],
    *,
    limit: int = 28,
) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for block in fleet, casino, agents:
        for row in block:
            item = dict(row)
            item.setdefault("source", "fleet")
            merged.append(item)
    merged.sort(key=lambda r: str(r.get("at") or ""), reverse=True)
    return merged[:limit]


def build_narration(payload: Dict[str, Any]) -> str:
    ps = payload.get("progression") or {}
    trades = payload.get("trades") or {}
    fleet = payload.get("fleet") or {}
    casino = payload.get("casino") or {}
    agents = payload.get("agents") or {}
    cstats = casino.get("stats") or {}
    astats = agents.get("stats") or {}
    mode = "paper simulation" if payload.get("paper_mode") else "live operations"
    return (
        f"Fleet progress monitor. Commander level {ps.get('commander_level', 1)}, "
        f"{ps.get('fleet_total_xp', 0)} total experience. "
        f"{fleet.get('active_bots', 0)} of {fleet.get('bot_count', 0)} bots active. "
        f"Aggregate trades {trades.get('total_trades', 0)}. "
        f"Profit band {trades.get('profit_band', 'under one dollar')}. "
        f"Casino bets today {cstats.get('bets_today', 0)}. "
        f"Agents online {astats.get('total_agents', 0)} with "
        f"{astats.get('total_executions', 0)} skill executions. "
        f"Running in {mode}."
    )


def public_fleet_progress_monitor(*, light: bool = True) -> Dict[str, Any]:
    from backend.services.trading_bots_control_service import _load_controls, list_bots

    controls = _load_controls()
    bots = list_bots(light=light)
    fleet_bots: List[Dict[str, Any]] = []
    sf: Dict[str, Any] = {}
    try:
        from backend.services.exchange_supervisor_fleet_service import fleet_overview
        from backend.services.trading_bots_control_service import _effective_enabled

        sf = fleet_overview(controls, persist_sync=light is False)
        for fb in sf.get("bots") or []:
            fb["enabled"] = _effective_enabled(
                {
                    "id": fb.get("id"),
                    "supervisor": fb.get("supervisor"),
                    "config_enabled": bool(fb.get("enabled", True)),
                },
                controls,
            )
            fleet_bots.append(_sanitize_bot(fb))
    except Exception:
        fleet_bots = [_sanitize_bot({"id": b["id"], "label": b.get("label"), **b}) for b in bots if b.get("fleet")]

    ps = sf.get("progression_summary") or {}
    meta = sf.get("meta") or {}
    total_trades = sum(int(b.get("trade_count") or 0) for b in bots)
    total_pnl = sum(float(b.get("total_pnl_usd") or 0) for b in bots)
    active_fleet = sum(1 for b in fleet_bots if b.get("enabled"))

    hot: List[str] = []
    try:
        from backend.services.exchange_profit_pair_search_service import read_index

        hot = [str(s).upper() for s in (read_index().get("hot_symbols") or [])[:8]]
    except Exception:
        hot = []

    paper = True
    try:
        from backend.services.exchange_arbitrage_service import live_enabled

        paper = not live_enabled()
    except Exception:
        pass

    casino_snap = _public_casino_snapshot()
    agents_snap = _public_agents_snapshot()
    fleet_activity = _activity_from_fleet_meta(meta) + _public_audit_ticks()
    for row in fleet_activity:
        row.setdefault("source", "fleet")

    payload: Dict[str, Any] = {
        "success": True,
        "generated_at": _iso(),
        "privacy": {
            "pii": False,
            "users_redacted": True,
            "financial_precision": "coarse_bands_only",
            "admin_fields": False,
        },
        "paper_mode": paper,
        "kill_switch": bool(controls.get("kill_switch")),
        "fleet": {
            "bot_count": len(fleet_bots),
            "active_bots": active_fleet,
            "mechanics_count": int(sf.get("mechanics_count") or 27),
            "last_run_at": meta.get("last_run_at"),
            "last_run_ok": meta.get("last_run_ok"),
            "bots": fleet_bots,
        },
        "progression": {
            "commander_level": int(ps.get("fleet_commander_level") or 1),
            "commander_rank": ps.get("fleet_commander_rank") or "Recruit",
            "fleet_total_xp": int(ps.get("fleet_total_xp") or 0),
            "avg_bot_level": float(ps.get("avg_bot_level") or 1),
            "rewards_unlocked": int(ps.get("total_rewards_unlocked") or 0),
            "xp_per_level": int(ps.get("xp_per_level") or 200),
        },
        "trades": {
            "total_trades": total_trades,
            "profit_band": _coarse_profit_band(total_pnl),
            "bot_count": len(bots),
        },
        "lanes": {"hot_symbols": hot},
        "casino": casino_snap,
        "agents": agents_snap,
        "activity": _merge_activity_streams(
            fleet_activity,
            casino_snap.get("recent") or [],
            agents_snap.get("recent") or [],
        ),
        "dimensions_5d": {
            "x": "fleet lane spread",
            "y": "supervisor depth",
            "z": "reward tier height",
            "w": "time pulse",
            "v": "experience intensity",
        },
    }
    payload["narration"] = build_narration(payload)
    try:
        from backend.services.fleet_stream_composer_service import composer_for_monitor_payload

        payload["composer"] = composer_for_monitor_payload(payload, stream_mode=True)
    except Exception:
        payload["composer"] = {"success": False, "chapters": []}
    try:
        from backend.services.fleet_stream_geo_service import public_geo_snapshot

        geo = public_geo_snapshot()
        if geo.get("enabled"):
            payload["geo"] = {
                "counts": geo.get("counts"),
                "center": geo.get("center"),
                "markers": (geo.get("markers") or [])[:24],
            }
    except Exception:
        pass
    return payload
