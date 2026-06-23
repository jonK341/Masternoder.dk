"""
Pay-to-click ads, traffic rotator, and sponsored click rewards.

This module intentionally keeps advertiser budgets, user rewards, and MN2
wallet movements in separate ledgers. The first release rewards internal
points only; crypto redemption can be layered on top after fraud controls
have real traffic data.
"""
import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse


_CONFIG_LOCK = threading.Lock()
_LEDGER_LOCK = threading.Lock()
_CAMPAIGN_CONFIG = "ptc_campaigns.json"
_LOG_DIR = "ptc_ads"
_MIN_DWELL_SECONDS = 8
_MAX_USER_VERIFIED_PER_DAY = 20
_MAX_USER_VERIFIED_PER_CAMPAIGN_DAY = 3
_MAX_IP_VERIFIED_PER_CAMPAIGN_DAY = 10


def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _data_dir() -> str:
    return os.path.join(_base_dir(), "data")


def _log_dir() -> str:
    root = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_base_dir(), "logs")
    return os.path.join(root, _LOG_DIR)


def _config_path() -> str:
    return os.environ.get("PTC_ADS_CONFIG_PATH") or os.path.join(_data_dir(), _CAMPAIGN_CONFIG)


def _utcnow() -> datetime:
    return datetime.utcnow()


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _utcnow()).replace(microsecond=0).isoformat() + "Z"


def _today_key() -> str:
    return _utcnow().date().isoformat()


def _hash_ip(ip: str) -> str:
    salt = os.environ.get("PTC_ADS_IP_SALT") or "masternoder-ptc"
    return hashlib.sha256(f"{salt}:{ip or ''}".encode("utf-8")).hexdigest()[:24]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _append_jsonl(name: str, row: Dict[str, Any]) -> None:
    os.makedirs(_log_dir(), exist_ok=True)
    path = os.path.join(_log_dir(), name)
    with _LEDGER_LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def _read_jsonl(name: str) -> List[Dict[str, Any]]:
    path = os.path.join(_log_dir(), name)
    if not os.path.exists(path):
        return []
    rows: List[Dict[str, Any]] = []
    with _LEDGER_LOCK:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(item, dict):
                        rows.append(item)
        except Exception:
            return []
    return rows


def _default_campaigns() -> Dict[str, Any]:
    return {
        "version": 1,
        "campaigns": [
            {
                "id": "internal-generator-growth",
                "name": "Try the AI Video Generator",
                "advertiser": "MasterNoder",
                "status": "active",
                "destination_url": "/generator",
                "title": "Generate a video with MasterNoder",
                "description": "Open the generator, explore the workflow, and earn a small sponsored-click reward.",
                "cta": "Open generator",
                "category": "internal",
                "reward_points": 12,
                "total_budget_clicks": 500,
                "daily_cap_clicks": 80,
                "weight": 10,
                "placements": ["home_smartlinks", "news_inline", "aggregator_ideas", "social_feed"],
                "tags": ["internal", "generator", "growth"],
            },
            {
                "id": "internal-mn2-wallet",
                "name": "MN2 Wallet Explainer",
                "advertiser": "MasterNoder",
                "status": "active",
                "destination_url": "/shop?tab=mn2",
                "title": "Learn how MN2 works in the shop",
                "description": "Visit the MN2 wallet section and see deposits, in-app balance, and shop checkout options.",
                "cta": "View MN2 wallet",
                "category": "crypto",
                "reward_points": 15,
                "total_budget_clicks": 300,
                "daily_cap_clicks": 50,
                "weight": 8,
                "placements": ["shop_mn2", "home_smartlinks", "news_inline"],
                "tags": ["mn2", "crypto", "shop"],
            },
            {
                "id": "internal-aggregator-traffic",
                "name": "Aggregator Traffic Loop",
                "advertiser": "MasterNoder",
                "status": "active",
                "destination_url": "/aggregator",
                "title": "Explore the intelligence aggregator",
                "description": "Use the aggregator monitor and intelligence feed as a traffic-discovery surface.",
                "cta": "Open aggregator",
                "category": "traffic",
                "reward_points": 10,
                "total_budget_clicks": 400,
                "daily_cap_clicks": 60,
                "weight": 7,
                "placements": ["aggregator_ideas", "home_smartlinks", "social_feed"],
                "tags": ["traffic", "rotator", "intel"],
            },
        ],
        "placements": {
            "home_smartlinks": {"label": "Homepage smart links", "max_items": 2},
            "news_inline": {"label": "News sponsored card", "max_items": 1},
            "aggregator_ideas": {"label": "Aggregator ideas sponsor", "max_items": 2},
            "shop_mn2": {"label": "Shop MN2 crypto section", "max_items": 1},
            "social_feed": {"label": "Social feed sponsor", "max_items": 1},
            "click_quest": {"label": "Sponsored click quests", "max_items": 3},
        },
        "advertiser_packages": [
            {
                "id": "ptc-verified-visits-100",
                "name": "100 verified visits",
                "description": "Managed PTC package for up to 100 verified sponsored visits after admin approval.",
                "price_usd": 19.99,
                "budget_clicks": 100,
                "placements": ["home_smartlinks", "news_inline", "social_feed"],
            },
            {
                "id": "ptc-crypto-section-feature",
                "name": "Crypto section feature",
                "description": "Managed feature slot in the MN2/shop crypto section with verified-click reporting.",
                "price_usd": 29.99,
                "budget_clicks": 150,
                "placements": ["shop_mn2", "home_smartlinks"],
            },
            {
                "id": "ptc-rotator-growth-pack",
                "name": "Traffic rotator growth pack",
                "description": "Rotates one approved URL across homepage, aggregator, news, and social placements.",
                "price_usd": 49.99,
                "budget_clicks": 300,
                "placements": ["home_smartlinks", "news_inline", "aggregator_ideas", "social_feed"],
            },
        ],
    }


def load_config() -> Dict[str, Any]:
    path = _config_path()
    with _CONFIG_LOCK:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("campaigns", [])
                    data.setdefault("placements", {})
                    data.setdefault("advertiser_packages", [])
                    return data
            except Exception:
                pass
        return _default_campaigns()


def save_config(config: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_config_path()), exist_ok=True)
    with _CONFIG_LOCK:
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, sort_keys=True)


def get_advertiser_packages() -> List[Dict[str, Any]]:
    return list(load_config().get("advertiser_packages") or [])


def _campaigns() -> List[Dict[str, Any]]:
    return [c for c in (load_config().get("campaigns") or []) if isinstance(c, dict)]


def _campaign_by_id(campaign_id: str) -> Optional[Dict[str, Any]]:
    cid = (campaign_id or "").strip()
    return next((c for c in _campaigns() if (c.get("id") or "").strip() == cid), None)


def _is_valid_destination(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url)
    if not parsed.scheme and url.startswith("/"):
        return True
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _verified_reward_rows() -> List[Dict[str, Any]]:
    return [r for r in _read_jsonl("rewards.jsonl") if r.get("status") == "credited"]


def _count_verified(
    campaign_id: Optional[str] = None,
    user_id: Optional[str] = None,
    day: Optional[str] = None,
    ip_hash: Optional[str] = None,
) -> int:
    count = 0
    for row in _verified_reward_rows():
        if campaign_id and row.get("campaign_id") != campaign_id:
            continue
        if user_id and row.get("user_id") != user_id:
            continue
        if day and (row.get("created_at") or "")[:10] != day:
            continue
        if ip_hash and row.get("ip_hash") != ip_hash:
            continue
        count += 1
    return count


def _campaign_available(campaign: Dict[str, Any], placement: Optional[str] = None) -> Tuple[bool, str]:
    if (campaign.get("status") or "draft").lower() != "active":
        return False, "inactive"
    destination_url = campaign.get("destination_url") or ""
    if not _is_valid_destination(destination_url):
        return False, "invalid_destination"
    if placement:
        placements = campaign.get("placements") or []
        if placement not in placements and "all" not in placements:
            return False, "placement_not_allowed"
    cid = campaign.get("id")
    total_cap = _safe_int(campaign.get("total_budget_clicks"), 0)
    if total_cap > 0 and _count_verified(campaign_id=cid) >= total_cap:
        return False, "budget_exhausted"
    daily_cap = _safe_int(campaign.get("daily_cap_clicks"), 0)
    if daily_cap > 0 and _count_verified(campaign_id=cid, day=_today_key()) >= daily_cap:
        return False, "daily_cap_reached"
    return True, "ok"


def _public_campaign(campaign: Dict[str, Any], placement: Optional[str] = None) -> Dict[str, Any]:
    cid = campaign.get("id") or ""
    verified_total = _count_verified(campaign_id=cid)
    total_cap = _safe_int(campaign.get("total_budget_clicks"), 0)
    return {
        "id": cid,
        "name": campaign.get("name") or campaign.get("title") or cid,
        "title": campaign.get("title") or campaign.get("name") or cid,
        "description": campaign.get("description") or "",
        "cta": campaign.get("cta") or "Visit",
        "advertiser": campaign.get("advertiser") or "MasterNoder",
        "category": campaign.get("category") or "sponsored",
        "reward_points": _safe_int(campaign.get("reward_points"), 0),
        "placement": placement,
        "tags": list(campaign.get("tags") or []),
        "sponsored": True,
        "remaining_clicks": max(0, total_cap - verified_total) if total_cap > 0 else None,
    }


def get_rotator_campaigns(placement: str, limit: int = 2) -> List[Dict[str, Any]]:
    placement = (placement or "").strip()
    max_items = _safe_int((load_config().get("placements") or {}).get(placement, {}).get("max_items"), 2)
    limit = max(1, min(_safe_int(limit, max_items or 2), max_items or 5, 10))
    eligible: List[Dict[str, Any]] = []
    for campaign in _campaigns():
        ok, _reason = _campaign_available(campaign, placement=placement)
        if ok:
            eligible.append(campaign)
    eligible.sort(key=lambda c: (_safe_int(c.get("weight"), 1), c.get("id") or ""), reverse=True)
    return [_public_campaign(c, placement=placement) for c in eligible[:limit]]


def record_impression(campaign_id: str, placement: str, user_id: str, ip: str, user_agent: str = "") -> Dict[str, Any]:
    campaign = _campaign_by_id(campaign_id)
    if not campaign:
        return {"success": False, "error": "campaign not found"}
    ok, reason = _campaign_available(campaign, placement=placement)
    if not ok:
        return {"success": False, "error": reason}
    impression_id = str(uuid.uuid4())
    row = {
        "impression_id": impression_id,
        "campaign_id": campaign_id,
        "placement": placement,
        "user_id": user_id or "default_user",
        "ip_hash": _hash_ip(ip),
        "user_agent_hash": hashlib.sha256((user_agent or "").encode("utf-8")).hexdigest()[:16],
        "created_at": _iso(),
    }
    _append_jsonl("impressions.jsonl", row)
    return {"success": True, "impression_id": impression_id}


def start_click(
    campaign_id: str,
    placement: str,
    user_id: str,
    ip: str,
    user_agent: str = "",
    impression_id: str = "",
) -> Dict[str, Any]:
    campaign = _campaign_by_id(campaign_id)
    if not campaign:
        return {"success": False, "error": "campaign not found"}
    ok, reason = _campaign_available(campaign, placement=placement)
    if not ok:
        return {"success": False, "error": reason}

    uid = user_id or "default_user"
    ip_hash = _hash_ip(ip)
    today = _today_key()
    if _count_verified(user_id=uid, day=today) >= _MAX_USER_VERIFIED_PER_DAY:
        return {"success": False, "error": "daily user reward cap reached"}
    if _count_verified(campaign_id=campaign_id, user_id=uid, day=today) >= _MAX_USER_VERIFIED_PER_CAMPAIGN_DAY:
        return {"success": False, "error": "campaign user reward cap reached"}
    if _count_verified(campaign_id=campaign_id, ip_hash=ip_hash, day=today) >= _MAX_IP_VERIFIED_PER_CAMPAIGN_DAY:
        return {"success": False, "error": "campaign network reward cap reached"}

    click_id = str(uuid.uuid4())
    destination_url = campaign.get("destination_url") or "/"
    row = {
        "click_id": click_id,
        "campaign_id": campaign_id,
        "placement": placement,
        "user_id": uid,
        "ip_hash": ip_hash,
        "user_agent_hash": hashlib.sha256((user_agent or "").encode("utf-8")).hexdigest()[:16],
        "impression_id": impression_id or None,
        "destination_url": destination_url,
        "status": "started",
        "created_at": _iso(),
        "verify_after": _iso(_utcnow() + timedelta(seconds=_MIN_DWELL_SECONDS)),
    }
    _append_jsonl("clicks.jsonl", row)
    return {
        "success": True,
        "click_id": click_id,
        "destination_url": destination_url,
        "redirect_url": f"/api/ptc/click/redirect?click_id={click_id}",
        "verify_after_seconds": _MIN_DWELL_SECONDS,
        "reward_points": _safe_int(campaign.get("reward_points"), 0),
    }


def _click_rows(click_id: str) -> List[Dict[str, Any]]:
    return [r for r in _read_jsonl("clicks.jsonl") if r.get("click_id") == click_id]


def get_click_destination(click_id: str) -> Optional[str]:
    rows = _click_rows(click_id)
    if not rows:
        return None
    return rows[-1].get("destination_url") or "/"


def verify_click(click_id: str, user_id: str, ip: str) -> Dict[str, Any]:
    rows = _click_rows(click_id)
    if not rows:
        return {"success": False, "error": "click not found"}
    click = rows[-1]
    if click.get("user_id") != (user_id or "default_user"):
        return {"success": False, "error": "click belongs to another user"}
    if click.get("ip_hash") != _hash_ip(ip):
        return {"success": False, "error": "click network changed"}
    if any(r.get("click_id") == click_id for r in _verified_reward_rows()):
        return {"success": True, "already_credited": True, "reward_points": 0}

    created = (click.get("created_at") or "").replace("Z", "")
    try:
        created_at = datetime.fromisoformat(created)
    except Exception:
        created_at = _utcnow()
    elapsed = (_utcnow() - created_at).total_seconds()
    if elapsed < _MIN_DWELL_SECONDS:
        return {
            "success": False,
            "error": "verification too early",
            "remaining_seconds": max(1, int(_MIN_DWELL_SECONDS - elapsed)),
        }

    campaign_id = click.get("campaign_id") or ""
    campaign = _campaign_by_id(campaign_id)
    if not campaign:
        return {"success": False, "error": "campaign not found"}
    ok, reason = _campaign_available(campaign, placement=click.get("placement"))
    if not ok:
        return {"success": False, "error": reason}

    today = _today_key()
    ip_hash = click.get("ip_hash") or _hash_ip(ip)
    if _count_verified(user_id=user_id, day=today) >= _MAX_USER_VERIFIED_PER_DAY:
        return {"success": False, "error": "daily user reward cap reached"}
    if _count_verified(campaign_id=campaign_id, user_id=user_id, day=today) >= _MAX_USER_VERIFIED_PER_CAMPAIGN_DAY:
        return {"success": False, "error": "campaign user reward cap reached"}
    if _count_verified(campaign_id=campaign_id, ip_hash=ip_hash, day=today) >= _MAX_IP_VERIFIED_PER_CAMPAIGN_DAY:
        return {"success": False, "error": "campaign network reward cap reached"}

    reward_points = max(0, _safe_int(campaign.get("reward_points"), 0))
    if reward_points > 0:
        from backend.services.unified_points_database import unified_points_db

        award = unified_points_db.add_points(
            user_id=user_id,
            point_type="ptc_points",
            amount=reward_points,
            source="ptc_ads",
            metadata={
                "click_id": click_id,
                "campaign_id": campaign_id,
                "placement": click.get("placement"),
                "reward_kind": "internal_points",
            },
        )
        if not award.get("success"):
            return {"success": False, "error": award.get("error", "could not credit reward")}

    row = {
        "reward_id": str(uuid.uuid4()),
        "click_id": click_id,
        "campaign_id": campaign_id,
        "placement": click.get("placement"),
        "user_id": user_id or "default_user",
        "ip_hash": ip_hash,
        "reward_points": reward_points,
        "reward_kind": "internal_points",
        "status": "credited",
        "created_at": _iso(),
    }
    _append_jsonl("rewards.jsonl", row)
    return {"success": True, "reward_points": reward_points, "reward_kind": "internal_points"}


def campaign_report(campaign_id: Optional[str] = None) -> Dict[str, Any]:
    impressions = _read_jsonl("impressions.jsonl")
    clicks = _read_jsonl("clicks.jsonl")
    rewards = _verified_reward_rows()
    budget = _read_jsonl("budget_ledger.jsonl")
    campaigns = _campaigns()
    if campaign_id:
        campaigns = [c for c in campaigns if c.get("id") == campaign_id]

    rows = []
    for campaign in campaigns:
        cid = campaign.get("id")
        imp_count = sum(1 for r in impressions if r.get("campaign_id") == cid)
        click_count = sum(1 for r in clicks if r.get("campaign_id") == cid)
        reward_rows = [r for r in rewards if r.get("campaign_id") == cid]
        total_cap = _safe_int(campaign.get("total_budget_clicks"), 0)
        daily_cap = _safe_int(campaign.get("daily_cap_clicks"), 0)
        today_verified = sum(1 for r in reward_rows if (r.get("created_at") or "")[:10] == _today_key())
        rows.append({
            "id": cid,
            "name": campaign.get("name") or cid,
            "status": campaign.get("status") or "draft",
            "placements": list(campaign.get("placements") or []),
            "impressions": imp_count,
            "started_clicks": click_count,
            "verified_clicks": len(reward_rows),
            "reward_points_spent": sum(_safe_int(r.get("reward_points"), 0) for r in reward_rows),
            "total_budget_clicks": total_cap,
            "remaining_clicks": max(0, total_cap - len(reward_rows)) if total_cap > 0 else None,
            "daily_cap_clicks": daily_cap,
            "today_verified_clicks": today_verified,
            "ctr": round(click_count / imp_count, 4) if imp_count else 0,
        })

    return {
        "success": True,
        "campaigns": rows,
        "totals": {
            "campaigns": len(rows),
            "impressions": len(impressions),
            "started_clicks": len(clicks),
            "verified_clicks": len(rewards),
            "reward_points_spent": sum(_safe_int(r.get("reward_points"), 0) for r in rewards),
            "budget_events": len(budget),
        },
    }


def upsert_campaign(campaign: Dict[str, Any], actor: str = "admin") -> Dict[str, Any]:
    cid = (campaign.get("id") or "").strip()
    if not cid:
        cid = str(uuid.uuid4())
        campaign["id"] = cid
    if not _is_valid_destination(campaign.get("destination_url") or ""):
        return {"success": False, "error": "destination_url must be internal or http(s)"}
    config = load_config()
    campaigns = [c for c in (config.get("campaigns") or []) if isinstance(c, dict)]
    now = _iso()
    campaign["updated_at"] = now
    campaign.setdefault("created_at", now)
    campaign.setdefault("status", "draft")
    campaign.setdefault("reward_points", 0)
    campaign.setdefault("placements", ["home_smartlinks"])
    campaign.setdefault("advertiser", "MasterNoder")
    replaced = False
    for idx, existing in enumerate(campaigns):
        if existing.get("id") == cid:
            merged = dict(existing)
            merged.update(campaign)
            campaigns[idx] = merged
            replaced = True
            break
    if not replaced:
        campaigns.append(campaign)
    config["campaigns"] = campaigns
    save_config(config)
    _append_jsonl("admin_events.jsonl", {
        "event_id": str(uuid.uuid4()),
        "event_type": "campaign_upserted",
        "campaign_id": cid,
        "actor": actor,
        "created_at": now,
    })
    return {"success": True, "campaign": _public_campaign(_campaign_by_id(cid) or campaign)}


def set_campaign_status(campaign_id: str, status: str, actor: str = "admin") -> Dict[str, Any]:
    status = (status or "").strip().lower()
    if status not in {"draft", "approved", "active", "paused", "completed"}:
        return {"success": False, "error": "invalid status"}
    campaign = _campaign_by_id(campaign_id)
    if not campaign:
        return {"success": False, "error": "campaign not found"}
    campaign["status"] = status
    result = upsert_campaign(campaign, actor=actor)
    if result.get("success"):
        _append_jsonl("admin_events.jsonl", {
            "event_id": str(uuid.uuid4()),
            "event_type": "campaign_status_changed",
            "campaign_id": campaign_id,
            "status": status,
            "actor": actor,
            "created_at": _iso(),
        })
    return result


def record_budget_event(package_id: str, campaign_id: str, provider: str, amount: float, actor: str = "admin", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    packages = {p.get("id"): p for p in get_advertiser_packages()}
    package = packages.get(package_id)
    if not package:
        return {"success": False, "error": "package not found"}
    row = {
        "budget_event_id": str(uuid.uuid4()),
        "package_id": package_id,
        "campaign_id": campaign_id or None,
        "provider": provider or "manual",
        "amount": _safe_float(amount),
        "budget_clicks": _safe_int(package.get("budget_clicks"), 0),
        "actor": actor,
        "metadata": metadata or {},
        "created_at": _iso(),
    }
    _append_jsonl("budget_ledger.jsonl", row)
    return {"success": True, "budget_event": row}


def click_quests(user_id: str, limit: int = 3) -> List[Dict[str, Any]]:
    campaigns = get_rotator_campaigns("click_quest", limit=limit)
    if not campaigns:
        campaigns = get_rotator_campaigns("home_smartlinks", limit=limit)
    return [
        {
            "id": f"ptc_quest_{c['id']}",
            "campaign_id": c["id"],
            "name": f"Sponsored click: {c['title']}",
            "description": c["description"],
            "target": 1,
            "reward": c["reward_points"],
            "type": "sponsored_click",
            "status": "available",
            "placement": "click_quest",
            "cta": c["cta"],
        }
        for c in campaigns
    ]
