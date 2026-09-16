"""Community fulfillment ledger — 25 population source scanners."""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional, Set

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_POPULATION_CONFIG = os.path.join(_BASE, "data", "ledger_population_sources.json")
_YOUTUBE_LEADS = os.path.join(_BASE, "data", "youtube_leads.json")
_FACEBOOK_LEADS = os.path.join(_BASE, "data", "facebook_leads.json")


def _data_path(name: str) -> str:
    return os.path.join(_BASE, "data", name)


def _read_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_population_catalog() -> Dict[str, Any]:
    doc = _read_json(_POPULATION_CONFIG)
    if not doc.get("sources"):
        return {"version": 1, "sources": []}
    return doc


def list_population_source_ids() -> List[str]:
    return [str(s.get("id")) for s in load_population_catalog().get("sources") or [] if s.get("id")]


def _row(
    source_id: str,
    *,
    discord_id: Optional[str] = None,
    youtube_id: Optional[str] = None,
    facebook_id: Optional[str] = None,
    user_id: Optional[str] = None,
    display_name: Optional[str] = None,
    buyer_signals: Optional[List[str]] = None,
    buyer_score: float = 0.0,
) -> Dict[str, Any]:
    return {
        "source_id": source_id,
        "discord_id": (discord_id or "").strip() or None,
        "youtube_id": (youtube_id or "").strip() or None,
        "facebook_id": (facebook_id or "").strip() or None,
        "user_id": (user_id or "").strip() or None,
        "display_name": display_name,
        "buyer_signals": list(buyer_signals or []),
        "buyer_score": float(buyer_score or 0),
    }


def _rows_from_leads(
    source_id: str,
    items: List[Dict[str, Any]],
    *,
    id_field: str,
    name_field: str = "display_name",
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        lid = str(item.get(id_field) or "").strip()
        if not lid:
            continue
        out.append(
            _row(
                source_id,
                discord_id=item.get("discord_id"),
                youtube_id=item.get("youtube_id") if id_field.startswith("youtube") or "youtube" in id_field else item.get("youtube_id"),
                facebook_id=item.get("facebook_id") if "facebook" in id_field or id_field.startswith("fb") else item.get("facebook_id"),
                user_id=item.get("user_id"),
                display_name=item.get(name_field) or item.get("name"),
            )
        )
    return out


def scan_youtube_subscribers() -> List[Dict[str, Any]]:
    """YouTube subscribers — data/youtube_leads.json or YOUTUBE_API_KEY live sync stub."""
    api_key = (os.environ.get("YOUTUBE_API_KEY") or "").strip()
    doc = _read_json(_YOUTUBE_LEADS)
    rows = _rows_from_leads("youtube_subscriber", doc.get("subscribers") or [], id_field="youtube_id")
    if api_key and not rows:
        rows.append(_row("youtube_subscriber", youtube_id="yt_api_stub", display_name="API stub subscriber"))
    return rows


def scan_youtube_commenters() -> List[Dict[str, Any]]:
    doc = _read_json(_YOUTUBE_LEADS)
    return _rows_from_leads("youtube_commenter", doc.get("commenters") or [], id_field="youtube_id")


def scan_facebook_page_fans() -> List[Dict[str, Any]]:
    token = (os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()
    doc = _read_json(_FACEBOOK_LEADS)
    rows = _rows_from_leads("facebook_page_fan", doc.get("page_fans") or [], id_field="facebook_id")
    if token and not rows:
        rows.append(_row("facebook_page_fan", facebook_id="fb_api_stub", display_name="API stub fan"))
    return rows


def scan_facebook_group_members() -> List[Dict[str, Any]]:
    doc = _read_json(_FACEBOOK_LEADS)
    return _rows_from_leads("facebook_group_member", doc.get("group_members") or [], id_field="facebook_id")


def scan_facebook_messenger_leads() -> List[Dict[str, Any]]:
    doc = _read_json(_FACEBOOK_LEADS)
    return _rows_from_leads("facebook_messenger_lead", doc.get("messenger_leads") or [], id_field="facebook_id")


def scan_shop_checkout_abandoned() -> List[Dict[str, Any]]:
    doc = _read_json(_data_path("shop_checkout_abandoned.json"))
    rows: List[Dict[str, Any]] = []
    for item in doc.get("abandoned") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            _row(
                "shop_checkout_abandoned",
                user_id=item.get("user_id"),
                discord_id=item.get("discord_id"),
                buyer_signals=["shop_abandoned"],
                buyer_score=12.0,
            )
        )
    return rows


def scan_exchange_wallet_created() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    ledger = _read_json(_data_path("mn2_ledger.json"))
    entries = ledger.get("entries") if isinstance(ledger, dict) else ledger
    seen: Set[str] = set()
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        meta = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        if meta.get("destination") != "exchange_wallet" and entry.get("destination") != "exchange_wallet":
            continue
        uid = (entry.get("user_id") or "").strip()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        rows.append(_row("exchange_wallet_created", user_id=uid, buyer_signals=["exchange_wallet"], buyer_score=11.0))
    return rows


def scan_casino_discord_play() -> List[Dict[str, Any]]:
    from backend.services.discord_fulfillment_ledger_service import _DISCORD_CLICKS, _read_jsonl, _resolve_discord_id

    rows: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for click in _read_jsonl(_DISCORD_CLICKS):
        link_id = str(click.get("link_id") or "").lower()
        if "casino" not in link_id and "play" not in link_id:
            continue
        user_id = (click.get("user_id") or "").strip() or None
        if not user_id:
            continue
        did = _resolve_discord_id(user_id)
        key = did or user_id
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            _row(
                "casino_discord_play",
                discord_id=did,
                user_id=user_id,
                buyer_signals=["casino_discord_play"],
                buyer_score=10.0,
            )
        )
    return rows


def scan_referral_signups() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in ("social_structure.json", "social_networks.json"):
        doc = _read_json(_data_path(path))
        referrals = doc.get("referrals") or doc.get("referral_signups") or []
        if isinstance(referrals, dict):
            for uid, meta in referrals.items():
                if not isinstance(meta, dict):
                    continue
                rows.append(_row("referral_signup", user_id=str(uid), discord_id=meta.get("discord_id")))
        elif isinstance(referrals, list):
            for item in referrals:
                if isinstance(item, dict):
                    rows.append(
                        _row(
                            "referral_signup",
                            user_id=item.get("user_id") or item.get("referred_user_id"),
                            discord_id=item.get("discord_id"),
                        )
                    )
    return rows


def scan_p2p_listing_views() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    listings = _read_json(_data_path("mn2_p2p_listings.json"))
    views_doc = _read_json(_data_path("p2p_listing_views.json"))
    view_items = views_doc.get("views") or []
    if view_items:
        for item in view_items:
            if isinstance(item, dict):
                rows.append(_row("p2p_listing_view", user_id=item.get("user_id"), discord_id=item.get("discord_id")))
        return rows
    for listing in (listings.values() if isinstance(listings, dict) else []):
        if not isinstance(listing, dict):
            continue
        for viewer in listing.get("viewers") or listing.get("viewer_ids") or []:
            uid = viewer if isinstance(viewer, str) else (viewer.get("user_id") if isinstance(viewer, dict) else None)
            if uid:
                rows.append(_row("p2p_listing_view", user_id=str(uid)))
    return rows


def scan_camgirl_tip_intents() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    tips_path = os.path.join(_BASE, "logs", "camgirls_tips.jsonl")
    if os.path.isfile(tips_path):
        try:
            with open(tips_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except Exception:
                        continue
                    if isinstance(item, dict) and item.get("status") in (None, "intent", "pending"):
                        rows.append(_row("camgirl_tip_intent", user_id=item.get("user_id"), buyer_score=9.0))
        except Exception:
            pass
    intents = _read_json(_data_path("camgirl_tip_intents.json")).get("intents") or []
    for item in intents:
        if isinstance(item, dict):
            rows.append(_row("camgirl_tip_intent", user_id=item.get("user_id"), discord_id=item.get("discord_id")))
    return rows


def scan_network_chat_active() -> List[Dict[str, Any]]:
    doc = _read_json(_data_path("network_chat_presence.json"))
    rows: List[Dict[str, Any]] = []
    for uid, meta in (doc.get("users") or {}).items():
        if not isinstance(meta, dict):
            continue
        if meta.get("status") in ("online", "away", "active"):
            rows.append(_row("network_chat_active", user_id=str(uid), display_name=meta.get("display_name")))
    return rows


def scan_podcast_subscribers() -> List[Dict[str, Any]]:
    doc = _read_json(_data_path("podcast_social.json"))
    rows: List[Dict[str, Any]] = []
    for item in doc.get("subscribers") or doc.get("listeners") or []:
        if isinstance(item, dict):
            rows.append(
                _row(
                    "podcast_subscriber",
                    user_id=item.get("user_id"),
                    discord_id=item.get("discord_id"),
                    display_name=item.get("display_name") or item.get("name"),
                )
            )
    return rows


def scan_newsletter_optins() -> List[Dict[str, Any]]:
    doc = _read_json(_data_path("newsletter_optins.json"))
    rows: List[Dict[str, Any]] = []
    for item in doc.get("optins") or []:
        if isinstance(item, dict):
            rows.append(_row("newsletter_optin", user_id=item.get("user_id"), discord_id=item.get("discord_id")))
    return rows


def scan_affiliate_clicks() -> List[Dict[str, Any]]:
    from backend.services.discord_fulfillment_ledger_service import _DISCORD_CLICKS, _read_jsonl, _resolve_discord_id

    rows: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for click in _read_jsonl(_DISCORD_CLICKS):
        meta = click.get("meta") if isinstance(click.get("meta"), dict) else {}
        link_id = str(click.get("link_id") or "")
        if meta.get("source") not in ("affiliate_rotator", "promo_rotator") and "affiliate" not in link_id.lower():
            continue
        user_id = (click.get("user_id") or "").strip() or None
        if not user_id:
            continue
        did = _resolve_discord_id(user_id)
        key = did or user_id
        if key in seen:
            continue
        seen.add(key)
        rows.append(_row("affiliate_click", discord_id=did, user_id=user_id, buyer_signals=["affiliate_click"], buyer_score=6.0))
    return rows


def scan_trophy_shop_views() -> List[Dict[str, Any]]:
    doc = _read_json(_data_path("trophy_shop_views.json"))
    rows: List[Dict[str, Any]] = []
    for item in doc.get("views") or []:
        if isinstance(item, dict):
            rows.append(_row("trophy_shop_view", user_id=item.get("user_id"), discord_id=item.get("discord_id")))
    return rows


def scan_wallet_earn_clicks() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    earn_log = os.path.join(_BASE, "logs", "wallet_micro_earn.jsonl")
    if not os.path.isfile(earn_log):
        return rows
    seen: Set[str] = set()
    try:
        with open(earn_log, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                uid = (item.get("user_id") or "").strip()
                if uid and uid not in seen:
                    seen.add(uid)
                    rows.append(_row("wallet_earn_click", user_id=uid, buyer_signals=["wallet_earn"], buyer_score=4.0))
    except Exception:
        pass
    return rows


def scan_hosting_inquiries() -> List[Dict[str, Any]]:
    doc = _read_json(_data_path("hosting_inquiries.json"))
    rows: List[Dict[str, Any]] = []
    for item in doc.get("inquiries") or []:
        if isinstance(item, dict):
            rows.append(_row("hosting_inquiry", user_id=item.get("user_id"), discord_id=item.get("discord_id")))
    return rows


def scan_masternode_interest() -> List[Dict[str, Any]]:
    doc = _read_json(_data_path("masternode_interest.json"))
    rows: List[Dict[str, Any]] = []
    for item in doc.get("interests") or []:
        if isinstance(item, dict):
            rows.append(_row("masternode_interest", user_id=item.get("user_id"), discord_id=item.get("discord_id")))
    return rows


def scan_support_ticket_mn2() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    support_path = os.path.join(_BASE, "data", "agent_support_data.json")
    doc = _read_json(support_path)
    for ticket in doc.get("support_tickets") or []:
        if not isinstance(ticket, dict):
            continue
        blob = f"{ticket.get('title', '')} {ticket.get('description', '')}".lower()
        if "mn2" not in blob and "masternode" not in blob and ticket.get("category") != "mn2":
            continue
        rows.append(
            _row(
                "support_ticket_mn2",
                user_id=ticket.get("user_id"),
                discord_id=ticket.get("discord_id"),
                buyer_signals=["support_mn2"],
                buyer_score=11.0,
            )
        )
    return rows


def scan_oauth_social_linked() -> List[Dict[str, Any]]:
    """Google pending, Facebook linked, YouTube OAuth — from oauth links registry."""
    rows: List[Dict[str, Any]] = []
    oauth_links = _read_json(_data_path("oauth_social_links.json"))
    for item in oauth_links.get("links") or []:
        if not isinstance(item, dict):
            continue
        provider = str(item.get("provider") or "").lower()
        source_id = {
            "google": "oauth_google_pending",
            "facebook": "oauth_facebook_linked",
            "youtube": "youtube_oauth_linked",
        }.get(provider, "oauth_social_linked")
        rows.append(
            _row(
                source_id if provider in ("google", "facebook", "youtube") else "oauth_social_linked",
                user_id=item.get("user_id"),
                discord_id=item.get("discord_id"),
                youtube_id=item.get("youtube_id"),
                facebook_id=item.get("facebook_id"),
                display_name=item.get("display_name"),
            )
        )
    oauth_state = _read_json(_data_path("oauth_state.json"))
    for _state, meta in oauth_state.items():
        if not isinstance(meta, dict):
            continue
        provider = str(meta.get("provider") or "").lower()
        uid = meta.get("user_id_hint")
        if provider == "google" and uid:
            rows.append(_row("oauth_google_pending", user_id=str(uid)))
        elif provider in ("facebook", "linked_role") and uid:
            rows.append(_row("oauth_facebook_linked", user_id=str(uid)))
    installs = _read_json(_data_path("wallet_installs.json"))
    for item in installs.get("installs") or []:
        if not isinstance(item, dict):
            continue
        platform = str(item.get("platform") or "").lower()
        sid = "mobile_wallet_install" if platform == "mobile" else "desktop_wallet_install"
        rows.append(_row(sid, user_id=item.get("user_id"), discord_id=item.get("discord_id")))
    waitlist = _read_json(_data_path("ledger_waitlist.json"))
    for item in waitlist.get("registrations") or []:
        if isinstance(item, dict):
            rows.append(_row("waitlist_register", user_id=item.get("user_id"), discord_id=item.get("discord_id")))
    return rows


def scan_discord_api_guild() -> List[Dict[str, Any]]:
    from backend.services.discord_fulfillment_ledger_service import fetch_discord_guild_members

    result = fetch_discord_guild_members()
    rows: List[Dict[str, Any]] = []
    for m in result.get("members") or []:
        rows.append(
            _row(
                "discord_api_guild",
                discord_id=m.get("discord_id"),
                user_id=m.get("user_id"),
                display_name=m.get("discord_username"),
            )
        )
    return rows


def scan_discord_api_channel() -> List[Dict[str, Any]]:
    from backend.services.discord_fulfillment_ledger_service import fetch_discord_channel_authors

    result = fetch_discord_channel_authors()
    rows: List[Dict[str, Any]] = []
    for m in result.get("members") or []:
        rows.append(
            _row(
                "discord_api_channel",
                discord_id=m.get("discord_id"),
                user_id=m.get("user_id"),
                display_name=m.get("discord_username"),
            )
        )
    return rows


_SCAN_REGISTRY: Dict[str, Callable[[], List[Dict[str, Any]]]] = {
    "scan_youtube_subscribers": scan_youtube_subscribers,
    "scan_youtube_commenters": scan_youtube_commenters,
    "scan_facebook_page_fans": scan_facebook_page_fans,
    "scan_facebook_group_members": scan_facebook_group_members,
    "scan_facebook_messenger_leads": scan_facebook_messenger_leads,
    "scan_shop_checkout_abandoned": scan_shop_checkout_abandoned,
    "scan_exchange_wallet_created": scan_exchange_wallet_created,
    "scan_casino_discord_play": scan_casino_discord_play,
    "scan_referral_signups": scan_referral_signups,
    "scan_p2p_listing_views": scan_p2p_listing_views,
    "scan_camgirl_tip_intents": scan_camgirl_tip_intents,
    "scan_network_chat_active": scan_network_chat_active,
    "scan_podcast_subscribers": scan_podcast_subscribers,
    "scan_newsletter_optins": scan_newsletter_optins,
    "scan_affiliate_clicks": scan_affiliate_clicks,
    "scan_trophy_shop_views": scan_trophy_shop_views,
    "scan_wallet_earn_clicks": scan_wallet_earn_clicks,
    "scan_hosting_inquiries": scan_hosting_inquiries,
    "scan_masternode_interest": scan_masternode_interest,
    "scan_support_ticket_mn2": scan_support_ticket_mn2,
    "scan_oauth_social_linked": scan_oauth_social_linked,
    "scan_discord_api_guild": scan_discord_api_guild,
    "scan_discord_api_channel": scan_discord_api_channel,
}


def scan_source(source_id: str) -> List[Dict[str, Any]]:
    catalog = load_population_catalog()
    entry = next((s for s in catalog.get("sources") or [] if s.get("id") == source_id), None)
    if not entry or not entry.get("enabled", True):
        return []

    if source_id == "local_linked":
        from backend.services.discord_fulfillment_ledger_service import scan_local_linked_users

        return [_row("local_linked", discord_id=r.get("discord_id"), user_id=r.get("user_id"), display_name=r.get("discord_username")) for r in scan_local_linked_users()]
    if source_id == "purchase_intent":
        from backend.services.discord_fulfillment_ledger_service import scan_purchase_intent_buyers

        return [
            _row(
                "purchase_intent",
                discord_id=r.get("discord_id"),
                user_id=r.get("user_id"),
                display_name=r.get("discord_username"),
                buyer_signals=r.get("buyer_signals"),
                buyer_score=float(r.get("buyer_score") or 0),
            )
            for r in scan_purchase_intent_buyers()
        ]

    scan_name = str(entry.get("scan") or "")
    fn = _SCAN_REGISTRY.get(scan_name)
    if fn:
        return fn()
    return []


def scan_all_enabled_sources(
    *,
    enabled_ids: Optional[Set[str]] = None,
    use_discord_api: bool = True,
) -> Dict[str, Any]:
    """Run all enabled population scans. Returns rows + per-source counts."""
    catalog = load_population_catalog()
    all_rows: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    api_used = False
    api_notes: List[str] = []

    for entry in catalog.get("sources") or []:
        sid = str(entry.get("id") or "")
        if not sid or not entry.get("enabled", True):
            continue
        if enabled_ids is not None and sid not in enabled_ids:
            continue
        if not use_discord_api and sid in ("discord_api_guild", "discord_api_channel"):
            continue

        try:
            rows = scan_source(sid)
        except Exception as exc:
            api_notes.append(f"{sid}: {exc}")
            rows = []
        counts[sid] = len(rows)
        if sid in ("discord_api_guild", "discord_api_channel") and rows:
            api_used = True
        all_rows.extend(rows)

    return {"rows": all_rows, "source_counts": counts, "api_used": api_used, "api_notes": api_notes}
