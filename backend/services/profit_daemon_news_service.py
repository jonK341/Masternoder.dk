"""Publish profit daemon ticks to platform news (home + /news)."""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.services import crypto_exchange_service as ex

_CHANNEL = "profit"
_COOLDOWN_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_news_state.json")
_MIN_INTERVAL_SEC = int(os.environ.get("PROFIT_NEWS_MIN_SEC", "900"))


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_state() -> Dict[str, Any]:
    data = ex._read_json(_COOLDOWN_PATH, {})
    return data if isinstance(data, dict) else {}


def _save_state(data: Dict[str, Any]) -> None:
    ex._write_json(_COOLDOWN_PATH, data)


def _parse_kv(summary: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for part in (summary or "").split():
        if "=" in part:
            k, _, v = part.partition("=")
            out[k] = v
    return out


def _cooldown_ok(event_key: str) -> bool:
    st = _load_state()
    last = float(st.get("last_ts") or 0)
    now = datetime.now(timezone.utc).timestamp()
    if now - last < _MIN_INTERVAL_SEC and st.get("last_key") == event_key:
        return False
    st["last_ts"] = now
    st["last_key"] = event_key
    _save_state(st)
    return True


def maybe_publish_tick_news(loop: str, summary: str, *, res: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Emit platform news on meaningful profit events (throttled)."""
    if loop != "exchange":
        return None

    kv = _parse_kv(summary)
    arb_exec = kv.get("arb_exec", "")
    m = re.match(r"(\d+)/(\d+)", arb_exec)
    fills = int(m.group(1)) if m else 0
    cross = kv.get("cross_actions")
    ext = kv.get("ext_exec")
    best_bps = kv.get("best_bps")
    sweep_mode = kv.get("mode")
    sweep_amt = kv.get("amount")

    title = ""
    summary_text = ""
    featured = False
    event_key = ""

    if fills > 0:
        event_key = f"arb_fills_{fills}"
        title = f"Live arb: {arb_exec} fills this tick"
        summary_text = f"Best spread {best_bps or '?'} bps · cross-trade {cross or 0} · extended {ext or 0}"
        featured = True
    elif sweep_mode == "live" and sweep_amt:
        event_key = f"sweep_live_{sweep_amt}"
        title = f"PayPal sweep live: ${sweep_amt}"
        summary_text = "Platform profit swept to PayPal (live gate on)."
        featured = True
    elif cross and int(cross) >= 7:
        event_key = f"cross_{cross}"
        title = f"Cross-trade engine: {cross} swaps"
        summary_text = f"7-bot cross-trade active · arb {arb_exec} · best {best_bps or '?'} bps"
    elif best_bps:
        try:
            bps = float(best_bps)
            if bps >= float(kv.get("min_margin") or 14) - 1:
                event_key = f"near_{int(bps)}"
                title = f"Arb near threshold: {bps:.1f} bps"
                summary_text = f"Watching {arb_exec} · funded={kv.get('funded', '?')} · min {kv.get('min_margin', '14')} bps"
        except ValueError:
            pass

    if res and not event_key:
        plat = (res.get("platform") or {}).get("results") or {}
        rot = plat.get("rotation") or {}
        if rot.get("executed"):
            event_key = "rotation"
            act = rot.get("action") or {}
            title = f"Capital rotation: {act.get('label') or act.get('type')}"
            summary_text = str(act.get("reason") or "Funding rebalance for live arb legs.")[:160]

    if not title or not _cooldown_ok(event_key):
        return None

    item_id = "profit_" + hashlib.sha256(event_key.encode()).hexdigest()[:12]
    try:
        from backend.services.platform_news_publish import publish
        return publish(
            item_id=item_id,
            title=title,
            summary=summary_text,
            channel=_CHANNEL,
            href="/profit/",
            featured=featured,
        )
    except Exception:
        return None
