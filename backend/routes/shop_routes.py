"""
Shop Routes
API endpoints for shop functionality including currency and items.
Uses account resolution: session > request > user_identification.
"""
from flask import Blueprint, jsonify, request, send_file
import os

shop_bp = Blueprint('shop', __name__)

# Feature flag: use shop-v3 API when True, legacy game/shop when False (e.g. when MN2/PayPal deps are off)
USE_SHOP_V3 = os.environ.get("USE_SHOP_V3", "true").strip().lower() in ("1", "true", "yes")

# Shop front-end generation (bump when navigation/layout changes; exposed in /api/shop/config)
# Product line: Shop V.9 tabbed UI + unified purchase/inventory APIs — keep in sync with shop/index.html.
SHOP_UI_VERSION = "9.2.0"


def _resolve_user_id():
    """Resolve user_id from session, request, or identification."""
    from backend.services.account_resolution_service import resolve_user_id
    return resolve_user_id()


def _booster_sku_map():
    try:
        from backend.services.monetization_config_service import _load_raw

        cfg = _load_raw() or {}
        skus = cfg.get("shop_booster_skus") or []
        return {s.get("id"): s for s in skus if s.get("id")}
    except Exception:
        return {}


def _apply_booster_sku(unified_points_db, user_id: str, sku_id: str, sku: dict, quantity: int) -> None:
    effect = (sku.get("effect") or "booster").lower()
    minutes = int(sku.get("duration_minutes") or 60)
    name = sku.get("name") or sku_id
    for _ in range(max(1, quantity)):
        if effect == "game_time":
            unified_points_db.add_game_time_minutes(user_id, minutes)
        else:
            unified_points_db.add_booster(user_id, sku_id, minutes, name=name)


def _apply_shop_item_effects(user_id: str, item_id: str, item: dict, quantity: int, *, purchase_ref: str = None) -> None:
    """Apply boosters and game time to user when they purchase relevant shop items."""
    import re
    try:
        from backend.services.shop_mn2_fulfillment_service import apply_mn2_grants_for_purchase

        ref = (purchase_ref or "").strip() or None
        apply_mn2_grants_for_purchase(
            user_id,
            item_id,
            item,
            quantity,
            source="shop_purchase",
            reference=ref or f"shop_purchase:{item_id}:{max(1, int(quantity or 1))}",
            extra_metadata={"item_name": (item or {}).get("name"), "purchase_ref": ref},
        )
    except Exception:
        pass
    try:
        from backend.services.unified_points_database import unified_points_db
    except Exception:
        return
    if (item or {}).get("delivery") == "exchange_shop":
        try:
            from backend.services.exchange_shop_service import fulfill_item

            ex_id = (item or {}).get("exchange_item_id") or item_id
            if (item or {}).get("requires_agent_id"):
                return
            fulfill_item(user_id, ex_id, record_purchase=True, price_mn2=float((item or {}).get("price_mn2") or 0))
        except Exception:
            pass
        return
    try:
        name = (item.get("name") or item_id or "").lower()
        category = (item.get("category") or "").lower()
        bundle = _content_bundle_by_id(item_id)
        if bundle:
            qty = max(1, int(quantity or 1))
            coins_granted = int(bundle.get("coins_granted") or 0) * qty
            generation_credits = float(bundle.get("generation_credits_granted") or 0) * qty
            if coins_granted > 0:
                unified_points_db.add_points(
                    user_id=user_id,
                    point_type="coins",
                    amount=coins_granted,
                    source="content_bundle",
                    metadata={"bundle_id": item_id, "quantity": qty},
                )
            if generation_credits > 0:
                unified_points_db.add_points(
                    user_id=user_id,
                    point_type="generation_points",
                    amount=generation_credits * 100,
                    source="content_bundle",
                    metadata={"bundle_id": item_id, "quantity": qty, "generation_credits": generation_credits},
                )
            try:
                from backend.services.shop_db_service import add_to_inventory

                goods_by_id = {g.get("id"): g for g in _digital_goods_config()}
                booster_skus = _booster_sku_map()
                # Cheap name map for catalog collectibles (e.g. Top 25 Legends) so
                # bundle-granted items land in inventory with a real name, not their id.
                try:
                    seed_names = {s.get("id"): s.get("name") for s in _seed_shop_items()}
                except Exception:
                    seed_names = {}
                for entry in bundle.get("items") or []:
                    if not isinstance(entry, dict):
                        continue
                    child_id = (entry.get("item_id") or "").strip()
                    if not child_id:
                        continue
                    child_qty = max(1, int(entry.get("quantity") or 1)) * qty
                    sku = booster_skus.get(child_id)
                    if sku:
                        _apply_booster_sku(unified_points_db, user_id, child_id, sku, child_qty)
                        continue
                    child = goods_by_id.get(child_id) or {}
                    child_name = child.get("name") or seed_names.get(child_id) or child_id
                    add_to_inventory(user_id, child_id, child_name, child_qty, purchase_id=None)
            except Exception:
                pass
        dg = _digital_good_by_id(item_id)
        if dg and dg.get("delivery") == "coins_grant":
            grant = int(dg.get("coins_granted") or 0) * max(1, int(quantity or 1))
            if grant > 0:
                unified_points_db.add_points(
                    user_id=user_id,
                    point_type="coins",
                    amount=grant,
                    source="exclusive_digital_good",
                    metadata={"item_id": item_id, "quantity": quantity},
                )
        if dg and dg.get("delivery") == "vip_pass":
            try:
                from backend.services.shop_monetization_service import activate_vip, get_config

                days = int((get_config().get("vip_pass") or {}).get("duration_days") or 30)
                for _ in range(max(1, int(quantity or 1))):
                    activate_vip(user_id, days=days, source="shop_purchase")
            except Exception:
                pass
        if category == "marketing" and "ptc" in (item.get("tags") or []):
            try:
                from backend.services.ptc_ads_service import record_budget_event

                qty = max(1, int(quantity or 1))
                for _ in range(qty):
                    record_budget_event(
                        package_id=item_id,
                        campaign_id="",
                        provider="shop_purchase",
                        amount=float(item.get("price_usd") or 0),
                        actor=user_id,
                        metadata={
                            "user_id": user_id,
                            "item_name": item.get("name") or item_id,
                            "requires_admin_campaign_binding": True,
                        },
                    )
            except Exception:
                pass
        total_minutes = 0
        # Game time: +30m, +1h, +2h, +4h, Weekend Pass (48h), Theme Session +Xm/+Xh
        if (
            "game time" in name
            or "gametime" in name
            or "weekend pass" in name
            or "theme session" in name
            or "weekend bridge" in name
        ):
            if "weekend" in name or "48" in name:
                total_minutes = 48 * 60 * quantity
            else:
                m = re.search(r"\+(\d+)\s*h", name)
                if m:
                    total_minutes = int(m.group(1)) * 60 * quantity
                else:
                    m = re.search(r"\+(\d+)\s*m", name)
                    if m:
                        total_minutes = int(m.group(1)) * quantity
                    elif "+1h" in name or "+1 h" in name:
                        total_minutes = 60 * quantity
                    elif "+2h" in name or "+2 h" in name:
                        total_minutes = 120 * quantity
                    elif "+4h" in name or "+4 h" in name:
                        total_minutes = 240 * quantity
                    elif "+30m" in name or "+30 m" in name:
                        total_minutes = 30 * quantity
            if total_minutes > 0:
                unified_points_db.add_game_time_minutes(user_id, total_minutes)
        # Boosters: XP 1h/2h/24h, Battle 1h, Quest Booster (24h), Star Map 25 1h/6h/24h, seasonal 3h/4h/90m
        if ("booster" in name or category == "boosts") and "theme session" not in name and "weekend bridge" not in name:
            duration_minutes = 60
            if "24h" in name or "24 h" in name:
                duration_minutes = 24 * 60
            elif "6h" in name or "6 h" in name:
                duration_minutes = 6 * 60
            elif "4h" in name or "4 h" in name:
                duration_minutes = 4 * 60
            elif "3h" in name or "3 h" in name:
                duration_minutes = 3 * 60
            elif "2h" in name or "2 h" in name:
                duration_minutes = 120
            elif "90m" in name or "90 m" in name:
                duration_minutes = 90
            elif "1h" in name or "1 h" in name:
                duration_minutes = 60
            for _ in range(quantity):
                unified_points_db.add_booster(
                    user_id, item_id or ("booster-" + name[:30]), duration_minutes, name=item.get("name") or item_id
                )
    except Exception:
        pass


# Legacy fallback if data/monetization_config.json is missing or empty
_PAYPAL_COIN_PACKS_LEGACY = [
    {"id": "coin-pack-s", "name": "100 Coins", "description": "100 coins via PayPal", "price_usd": 0.99, "coins_granted": 100, "icon": "🪙"},
    {"id": "coin-pack-m", "name": "500 Coins", "description": "500 coins via PayPal — best value", "price_usd": 4.99, "coins_granted": 500, "icon": "🪙"},
    {"id": "coin-pack-l", "name": "2000 Coins", "description": "2000 coins via PayPal — best deal", "price_usd": 9.99, "coins_granted": 2000, "icon": "🪙"},
]


def get_paypal_coin_packs():
    """Coin pack SKUs from data/monetization_config.json (single config source)."""
    try:
        from backend.services.monetization_config_service import get_coin_packs_with_payment_rails

        packs = get_coin_packs_with_payment_rails()
        if packs:
            return packs
    except Exception:
        pass
    return list(_PAYPAL_COIN_PACKS_LEGACY)


def get_coin_pack_map():
    return {p["id"]: p for p in get_paypal_coin_packs()}


def get_mn2_packs():
    """MN2 packs from monetization_config.json (buy MN2 with PayPal or shop coins)."""
    try:
        from backend.services.monetization_config_service import get_mn2_packs_with_payment_rails

        packs = get_mn2_packs_with_payment_rails()
        if packs:
            return packs
    except Exception:
        pass
    return []


def get_mn2_pack_map():
    return {p["id"]: p for p in get_mn2_packs() if p.get("id")}


# Module-level aliases refreshed at import (tests expect PAYPAL_COIN_PACKS / COIN_PACK_MAP)
PAYPAL_COIN_PACKS = get_paypal_coin_packs()
COIN_PACK_MAP = get_coin_pack_map()


def _get_paypal_shop_items():
    """Items purchasable with PayPal (price_usd). Excludes coin packs."""
    items = _get_shop_items()
    result = {}
    for item in items or []:
        iid = item.get("id")
        if not iid or iid in get_coin_pack_map() or iid in get_mn2_pack_map():
            continue
        price = item.get("price")
        if isinstance(price, (int, float)) and price > 0:
            price_usd = max(0.99, round(float(price) / 100, 2))
            result[iid] = {"price_usd": price_usd, "name": item.get("name", iid)}
        elif isinstance(price, dict) and item.get("price_usd"):
            result[iid] = {"price_usd": float(item["price_usd"]), "name": item.get("name", iid)}

    # Dynamic top-agent offers are also purchasable with PayPal.
    try:
        from backend.services.agent_skillset import agent_skillset
        agents = agent_skillset.get_all_skillsets().get('agents', {})
        ranked = []
        for agent_id, data in agents.items():
            paypal_power = int(data.get('paypal_skill_power_total', 0))
            sales_power = int(data.get('sales_skill_power_total', 0))
            top25_power = int(data.get('top25_upgrade_power_total', 0))
            level = int(data.get('level', 1))
            score = (paypal_power * 1.2) + (sales_power * 0.6) + (top25_power * 0.35) + (level * 20)
            ranked.append((score, agent_id, data))
        ranked.sort(key=lambda x: x[0], reverse=True)
        for score, agent_id, data in ranked[:5]:
            offer_id = f"agent-offer-{agent_id}"
            offer_name = f"Agent License: {data.get('name', agent_id)}"
            price_usd = max(19.99, round((score / 180.0) + (int(data.get('level', 1)) * 1.75), 2))
            result[offer_id] = {"price_usd": price_usd, "name": offer_name}

        # Dynamic booster cards purchasable via PayPal.
        boosters = [
            ("booster-paypal-checkout-speed", "Booster: Checkout Speed", "Reduce checkout friction and drop-off", 9.99),
            ("booster-paypal-conversion-copy", "Booster: Conversion Copy", "Improve offer copy and CTA performance", 12.99),
            ("booster-paypal-cart-recovery", "Booster: Cart Recovery", "Recover abandoned carts faster", 11.99),
            ("booster-paypal-order-value-lift", "Booster: Order Value Lift", "Increase AOV through bundle logic", 14.99),
            ("booster-paypal-retention-loop", "Booster: Retention Loop", "Boost repeat purchases and loyalty", 13.99),
        ]
        for booster_id, booster_name, _, booster_price in boosters:
            result[booster_id] = {"price_usd": booster_price, "name": booster_name}
    except Exception:
        pass
    return result


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _digital_goods_config():
    try:
        from backend.services.monetization_config_service import get_digital_goods

        return get_digital_goods()
    except Exception:
        return []


def _content_bundles_config():
    try:
        from backend.services.monetization_config_service import get_content_bundles

        return get_content_bundles()
    except Exception:
        return []


def _content_bundle_by_id(item_id: str):
    iid = (item_id or "").strip()
    return next((b for b in _content_bundles_config() if (b.get("id") or "") == iid), None)


def _digital_good_by_id(item_id: str):
    iid = (item_id or "").strip()
    return next((g for g in _digital_goods_config() if (g.get("id") or "") == iid), None)


def _digital_goods_shop_items():
    """Expose configured digital goods in the normal shop catalog."""
    items = []
    for good in _digital_goods_config():
        price_coins = int(good.get("price_coins") or 0)
        row = {
            "id": good.get("id"),
            "name": good.get("name") or good.get("id"),
            "description": good.get("description") or "",
            "category": "exclusive" if str(good.get("line") or "").lower() == "exclusive" else "digital_goods",
            "price": price_coins,
            "price_usd": float(good.get("price_usd") or 0),
            "icon": "💎" if str(good.get("line") or "").lower() == "exclusive" else "📦",
            "rarity": "legendary" if str(good.get("line") or "").lower() == "exclusive" else ("rare" if price_coins else "common"),
            "tags": ["digital_good", good.get("delivery") or "download", f"line_{str(good.get('line') or 'x').lower()}"],
            "payment_rails": good.get("payment_rails") or ["credits"],
            "delivery": good.get("delivery") or "download",
            "license": good.get("license") or "",
            "coins_granted": int(good.get("coins_granted") or 0),
        }
        if row["id"]:
            items.append(row)
    return items


def _content_bundle_shop_items():
    """Expose configured content bundles in the normal shop catalog."""
    items = []
    for bundle in _content_bundles_config():
        price_coins = int(bundle.get("price_coins") or 0)
        row = {
            "id": bundle.get("id"),
            "name": bundle.get("name") or bundle.get("id"),
            "description": bundle.get("description") or "",
            "category": "bundles",
            "price": price_coins,
            "price_usd": float(bundle.get("price_usd") or 0),
            "icon": "🧰",
            "rarity": "legendary" if price_coins >= 1000 else "rare",
            "tags": ["bundle", "digital_good", "credits"],
            "payment_rails": bundle.get("payment_rails") or ["credits"],
            "bundle_items": bundle.get("items") or [],
            "coins_granted": int(bundle.get("coins_granted") or 0),
            "generation_credits_granted": float(bundle.get("generation_credits_granted") or 0),
            "mn2_granted": float(bundle.get("mn2_granted") or 0),
            "attribution": bundle.get("attribution") or {},
        }
        if row["id"]:
            items.append(row)
    return items


def _mn2_pack_shop_items():
    """Expose MN2 packs in the shop catalog (coins or PayPal → in-wallet MN2)."""
    items = []
    for pack in get_mn2_packs():
        price_coins = int(pack.get("price_coins") or 0)
        row = {
            "id": pack.get("id"),
            "name": pack.get("name") or pack.get("id"),
            "description": pack.get("description") or "",
            "category": "mn2_crypto",
            "price": price_coins,
            "price_usd": float(pack.get("price_usd") or 0),
            "icon": pack.get("icon") or "🪙",
            "rarity": "legendary" if price_coins >= 2000 else "epic",
            "tags": ["mn2_pack", "crypto", "mn2"],
            "payment_rails": pack.get("payment_rails") or ["paypal", "credits"],
            "mn2_granted": float(pack.get("mn2_granted") or 0),
            "featured": bool(pack.get("featured")),
        }
        if row["id"]:
            items.append(row)
    return items


def _exchange_shop_items():
    """Expose exchange shop SKUs in the main /shop catalog."""
    try:
        from backend.services.exchange_shop_service import shop_items_for_catalog

        return shop_items_for_catalog()
    except Exception:
        return []


def _ptc_advertiser_package_shop_items():
    """Expose managed traffic packages as PayPal/MN2-ready shop catalog items."""
    try:
        from backend.services.ptc_ads_service import get_advertiser_packages

        packages = get_advertiser_packages()
    except Exception:
        packages = []
    items = []
    for package in packages:
        package_id = package.get("id")
        if not package_id:
            continue
        budget_clicks = int(package.get("budget_clicks") or 0)
        price_usd = float(package.get("price_usd") or 0)
        price_coins = max(1, int(round(price_usd * 100))) if price_usd > 0 else 0
        items.append({
            "id": package_id,
            "name": package.get("name") or package_id,
            "description": package.get("description") or "",
            "category": "marketing",
            "price": price_coins,
            "price_usd": price_usd,
            "icon": "📣",
            "rarity": "rare",
            "tags": ["ptc", "advertising", "traffic", "managed"],
            "payment_rails": ["paypal", "mn2", "managed_admin"],
            "marketing_clicks": budget_clicks,
            "budget_clicks": budget_clicks,
            "placements": package.get("placements") or [],
        })
    return items


def _user_owns_shop_item(user_id: str, item_id: str) -> bool:
    if not (user_id or "").strip() or not (item_id or "").strip():
        return False
    try:
        from backend.services.shop_db_service import get_inventory

        for inv in get_inventory(user_id) or []:
            if inv.get("item_id") == item_id and int(inv.get("quantity") or 0) > 0:
                return True
    except Exception:
        pass
    return False


def _artifact_abs_path(good: dict) -> str:
    rel = (good.get("artifact_path") or "").strip().replace("\\", "/")
    if not rel:
        return ""
    root = os.path.realpath(_project_root())
    path = os.path.realpath(os.path.join(root, rel))
    allowed_root = os.path.realpath(os.path.join(root, "content", "digital_goods"))
    if not (path == allowed_root or path.startswith(allowed_root + os.sep)):
        return ""
    return path


def _seed_shop_items():
    """Return 100+ shop items across categories (themes, boosts, cosmetic, etc.)."""
    items = []
    idx = 0

    def add(name, desc, cat, price, icon="🛍️", rarity="common", tags=None, item_id=None):
        nonlocal idx
        idx += 1
        row = {
            "id": item_id or f"shop-{idx}",
            "name": name,
            "description": desc,
            "category": cat,
            "price": price,
            "icon": icon,
            "rarity": rarity,
        }
        if tags:
            row["tags"] = tags
        items.append(row)

    themes = [
        ("Galaxy Dark", "Dark space theme for UI", "🎨"),
        ("Neon Green", "Neon green accent theme", "💚"),
        ("Ocean Blue", "Calm ocean blue theme", "🌊"),
        ("Sunset Purple", "Purple gradient theme", "🌅"),
        ("Electric Magnet", "Electric Magnet tech theme", "🧲"),
        ("Star Map", "Star map background theme", "⭐"),
        ("Trophy Gold", "Gold trophy hunter theme", "🏆"),
        ("Debugger Pro", "Debugger-style dark theme", "🔧"),
    ]
    for n, d, i in themes:
        add(n, d, "themes", 50 + idx * 5, i, "common" if idx % 3 else "rare")

    boosts = [
        ("XP Booster 1h", "+20% XP for 1 hour", "⚡"),
        ("XP Booster 2h", "+20% XP for 2 hours", "⚡"),
        ("XP Booster 24h", "+20% XP for 24 hours", "⚡"),
        ("Game Time +30m", "Extra 30 min game session", "⏱️"),
        ("Game Time +1h", "Extra 1 hour game session", "⏱️"),
        ("Game Time +2h", "Extra 2h game session", "⏱️"),
        ("Game Time +4h", "Extra 4h game session", "⏱️"),
        ("Weekend Pass", "48h extended game time (weekend)", "🎫"),
        ("Clickthrough Bonus", "Boost clickthrough rewards", "👆"),
        ("Generation Speed", "Faster video generation", "🎬"),
        ("Battle Power 1h", "Temporary battle boost 1 hour", "⚔️"),
        ("Quest Booster", "+25% quest rewards for 24h", "📜"),
        ("Progression Boost", "Faster progression", "📊"),
    ]
    for n, d, i in boosts:
        add(n, d, "boosts", 30 + idx * 3, i, "common")

    # Star Map 25: boosters, gametime, trophies
    starmap25_boosts = [
        ("Star Map 25 Booster 1h", "2x investigation points for 1 hour on Star Map 25", "🌟"),
        ("Star Map 25 Booster 6h", "2x investigation points for 6 hours", "🌟"),
        ("Star Map 25 Booster 24h", "2x investigation points for 24 hours", "🌟"),
        ("Star Map 25 Game Time +30m", "Extra 30 min Hunter game + Star Map 25 session", "⏱️"),
        ("Star Map 25 Game Time +1h", "Extra 1h Hunter game + Star Map 25 session", "⏱️"),
        ("Star Map 25 Game Time +2h", "Extra 2h Hunter game + Star Map 25 session", "⏱️"),
    ]
    for n, d, i in starmap25_boosts:
        add(n, d, "starmap25", 35 + idx * 2, i, "rare")
    starmap25_trophies = [
        ("Star Map 25 — Terra Trophy", "Trophy: First investigation (Terra)", "🏆"),
        ("Star Map 25 — Segmentum Clear", "Trophy: All 5 Segmentum fortresses investigated", "🏆"),
        ("Star Map 25 — Full Clear Trophy", "Trophy: All 25 points investigated", "🏆"),
        ("Star Map 25 — Lore Master", "Trophy: Unlock all 25 lore entries", "📜"),
    ]
    for n, d, i in starmap25_trophies:
        add(n, d, "starmap25", {"game_points": 50 + idx * 5}, i, "rare")
    starmap25_levels_calendar = [
        ("System Level Skip Token", "Unlock one system to next level (max 5)", "📈"),
        ("Daily Reset Bonus 24h", "2x buildup collect for 24h after next daily reset", "🔄"),
        ("High-Level Structure Unlock", "Unlock one Orbital Fortress / Cathedral / Primarch's Gate without level", "🏗️"),
        ("Calendar Slot — Agent Task", "Schedule one agent/AI appointment (content, learning, analytics)", "📅"),
        ("Star Map 25 Level Pack", "Bundle: 1 level skip + 1 daily reset bonus", "📦"),
    ]
    for n, d, i in starmap25_levels_calendar:
        add(n, d, "starmap25", 80 + idx * 10, i, "rare")

    cosmetics = [
        ("Avatar Frame Gold", "Gold avatar frame", "🖼️"),
        ("Avatar Frame Neon", "Neon avatar frame", "🖼️"),
        ("Profile Badge Star", "Star profile badge", "⭐"),
        ("Profile Badge Trophy", "Trophy profile badge", "🏆"),
        ("Chat Bubble Glow", "Glowing chat bubble", "💬"),
        ("Cursor Trail", "Custom cursor trail", "✨"),
    ]
    for n, d, i in cosmetics:
        add(n, d, "cosmetic", 25 + idx * 2, i, "common")

    tech = [
        ("Electric Magnet Module", "Agent tech: verification, DNA, star map", "🧲"),
        ("Event Tracker", "Track new tasks and events", "📡"),
        ("3D Monitor Plugin", "3D visual effects monitor", "📺"),
        ("Lab Access", "Unlock Lab experiments", "🔬"),
        ("API Scanner Pro", "Extended API scanning", "🔍"),
        ("Path Corrector", "Intelligent path correction", "🧭"),
    ]
    for n, d, i in tech:
        add(n, d, "tech", {"xp": 100 + idx * 20, "generation_points": 50}, i, "rare")

    battle = [
        ("Battle Ticket", "One battle entry", "🎫"),
        ("Strength Potion", "Temp battle strength", "🧪"),
        ("Shield Token", "One-time battle shield", "🛡️"),
        ("Victory Boost", "Post-victory bonus", "🏆"),
        ("Combat Points Pack", "100 combat points", "⚔️"),
    ]
    for n, d, i in battle:
        add(n, d, "battle", {"battle_points": 50 + idx * 10}, i, "rare")

    premium = [
        ("Valued Seller Badge", "Valued seller choice badge", "💎"),
        ("Premium Theme Pack", "All premium themes", "🎨"),
        ("Unified Points Bundle", "Mixed points bundle", "💎"),
        ("Legendary Avatar", "Legendary avatar unlock", "👤"),
    ]
    for n, d, i in premium:
        add(n, d, "premium", 200 + idx * 50, i, "legendary")

    gen = [
        ("Clip Pack 4–6s", "4–6 second clip generation pack", "🎬"),
        ("30s Video Credit", "One 30s video generation", "🎬"),
        ("Checkpoint Toggle", "Enable checkpoint in generator", "✅"),
        ("Service Worker Pro", "Enhanced generation worker", "⚙️"),
    ]
    for n, d, i in gen:
        add(n, d, "generation", {"generation_points": 80 + idx * 15}, i, "rare")

    skill = [
        ("Skill Point Pack S", "50 skill points", "🧠"),
        ("Skill Point Pack M", "150 skill points", "🧠"),
        ("Skill Point Pack L", "500 skill points", "🧠"),
    ]
    for n, d, i in skill:
        add(n, d, "skill", {"skill_points": 50 + idx * 25}, i, "common")

    progression = [
        ("Progression Boost S", "Small progression boost", "📊"),
        ("Progression Boost M", "Medium progression boost", "📊"),
        ("Progression Boost L", "Large progression boost", "📊"),
    ]
    for n, d, i in progression:
        add(n, d, "progression", {"progression_points": 30 + idx * 20}, i, "common")

    social = [
        ("Social Points Pack", "100 social points", "👥"),
        ("Friend Invite Bonus", "Bonus for inviting friends", "🤝"),
        ("Guild Crest", "Custom guild crest", "👥"),
    ]
    for n, d, i in social:
        add(n, d, "social", {"social_points": 40 + idx * 10}, i, "common")

    achievement = [
        ("Achievement Unlock", "Unlock hidden achievement", "🏆"),
        ("Trophy Display", "Extra trophy display slot", "🏆"),
        ("Milestone Marker", "Custom milestone marker", "📌"),
    ]
    for n, d, i in achievement:
        add(n, d, "achievement", {"achievement_points": 60 + idx * 15}, i, "rare")

    # Hunters trophies (shop trophies — display / collectibles)
    hunters_trophies = [
        ("Winter Wedding Trophy", "Trophy: Complete The Winter Wedding in London (1017) story or one-shot", "💒"),
        ("Medieval Crown Trophy", "Trophy: Unlock medieval sector spells and complete a medieval encounter", "👑"),
        ("Time Reversal Trophy", "Trophy: Use time reversal (rewind) at least once in a session", "⏪"),
        ("Power Combo Trophy", "Trophy: Trigger a power combo (e.g. Contract Seal + Jarl's Fury)", "⚡"),
        ("Jarl's Favor Trophy", "Trophy: Earn Thorkill's favor in Winter Wedding", "🪓"),
    ]
    for n, d, i in hunters_trophies:
        add(n, d, "trophies", {"game_points": 55 + idx * 5, "achievement_points": 30}, i, "rare")

    # Story unlocks (Hunters stories)
    stories_cat = [
        ("Winter Wedding Story Unlock", "Full Winter Wedding (1017) campaign: roles, conflicts, NPCs, twist, power combos", "📜"),
        ("Medieval Campaign Pack", "Medieval sector + Time Reversal rules + Power Combo reference", "🏰"),
    ]
    for n, d, i in stories_cat:
        add(n, d, "stories", {"game_points": 80, "xp": 50}, i, "epic")

    # New boosters: power combo, time reversal, medieval
    new_boosters = [
        ("Power Combo Booster 1h", "Unlock power combo effects for 1 hour in Hunters sessions", "⚡"),
        ("Time Reversal Booster 1h", "One extra narrative rewind per hour in story mode", "⏪"),
        ("Medieval Might 1h", "+1 to Persuasion and Intimidation in medieval-themed encounters for 1h", "🛡️"),
    ]
    for n, d, i in new_boosters:
        add(n, d, "boosts", 35 + idx * 2, i, "rare")

    # May 2026 wave — booster packs, game time, exclusive bonuses
    wave_boosters = [
        ("Casino Luck Booster 6h", "+15% casino quest rewards for 6 hours", "🎰", "booster-casino-luck-6h"),
        ("Generation Speed Booster 3h", "Faster video generation for 3 hours", "🎬", "booster-gen-speed-3h"),
        ("XP Surge Booster 3h", "+30% XP for 3 hours", "⚡", "booster-xp-surge-3h"),
        ("Quest Rush Booster 12h", "+35% quest rewards for 12 hours", "📜", "booster-quest-rush-12h"),
        ("Battle Fury Booster 2h", "2x battle points for 2 hours", "⚔️", "booster-battle-fury-2h"),
    ]
    for n, d, i, iid in wave_boosters:
        add(n, d, "boosts", 55 + idx * 4, i, "rare", tags=["shop_wave_may2026"], item_id=iid)

    wave_gametime = [
        ("Hunter Game Time +4h", "Extra 4h Hunter + Star Map session", "⏱️", "gametime-hunter-4h"),
        ("Creator Session +3h", "Extended generator and lab session time", "🎬", "gametime-creator-3h"),
        ("Weekend Marathon Pass", "72h extended game time (weekend marathon)", "🎫", "gametime-weekend-marathon"),
    ]
    for n, d, i, iid in wave_gametime:
        add(n, d, "boosts", 65 + idx * 5, i, "epic", tags=["game_time", "shop_wave_may2026"], item_id=iid)

    exclusive_items = [
        ("VIP Gold Badge", "Exclusive VIP badge for your profile — limited shop drop", "👑", "exclusive-vip-badge-shop"),
        ("Neon Crown Frame", "Exclusive neon avatar frame — not in regular rotation", "💎", "exclusive-neon-crown"),
        ("Casino High Roller Title", "Exclusive casino title shown on leaderboard", "🎰", "exclusive-casino-title"),
        ("Founder's Bonus Pack", "200 bonus coins + 1h XP booster — one-time exclusive", "🎁", "exclusive-founders-pack"),
    ]
    for n, d, i, iid in exclusive_items:
        add(n, d, "exclusive", 149 + idx * 25, i, "legendary", tags=["exclusive", "shop_wave_may2026"], item_id=iid)

    booster_packs = [
        ("Booster Trio Pack", "XP 2h + Quest 24h + Battle 1h bundled", "📦", "pack-booster-trio"),
        ("Pro Booster Pack", "XP 24h + Casino Luck 6h + Gen Speed 3h", "🧰", "pack-booster-pro"),
        ("Weekend Power Pack", "Weekend pass + Hunter 4h + Quest Rush 12h", "🎫", "pack-weekend-power"),
    ]
    for n, d, i, iid in booster_packs:
        add(n, d, "bundles", 199 + idx * 30, i, "legendary", tags=["booster_pack", "shop_wave_may2026"], item_id=iid)

    # Security & account
    security_items = [
        ("Password Protection Unlock", "Unlock password protection for your account (reward for progress)", "🔐"),
        ("Account Backup Token", "One-time backup code for account recovery", "📋"),
        ("Session Extender", "Extend current session by 2 hours", "⏱️"),
    ]
    for n, d, i in security_items:
        add(n, d, "premium", 60 + idx * 5, i, "rare")

    # More achievements & milestones
    more_achievement_items = [
        ("Achievement Reveal", "Reveal one hidden achievement", "🎯"),
        ("Milestone Badge Bronze", "Bronze milestone display badge", "🥉"),
        ("Milestone Badge Silver", "Silver milestone display badge", "🥈"),
        ("Milestone Badge Gold", "Gold milestone display badge", "🥇"),
        ("Progress Showcase", "Showcase your top 3 achievements on profile", "📊"),
    ]
    for n, d, i in more_achievement_items:
        add(n, d, "achievement", {"achievement_points": 45 + idx * 5, "game_points": 20}, i, "rare")

    # Seasonal & limited
    seasonal = [
        ("Spring Bloom Theme", "Limited spring theme with floral accents", "🌸"),
        ("Summer Solar Theme", "Bright summer solar theme", "☀️"),
        ("Autumn Harvest Theme", "Warm autumn harvest theme", "🍂"),
        ("Winter Frost Theme", "Cool winter frost theme", "❄️"),
        ("Lunar New Year Badge", "Limited Lunar New Year profile badge", "🧧"),
        ("Anniversary Frame", "Special anniversary avatar frame", "🎂"),
    ]
    for n, d, i in seasonal:
        add(n, d, "cosmetic", 70 + idx * 3, i, "rare")

    # More battle & PvP
    more_battle = [
        ("Double Battle Rewards 1h", "2x battle points for 1 hour", "⚔️"),
        ("Battle Shield 3x", "Three one-time battle shields", "🛡️"),
        ("Victory Streak Booster", "Bonus points for win streaks", "🔥"),
        ("Ranked Entry Ticket", "One ranked battle entry", "🎫"),
    ]
    for n, d, i in more_battle:
        add(n, d, "battle", {"battle_points": 40 + idx * 8}, i, "rare")

    # More social & crew
    more_social = [
        ("Crew Banner", "Custom crew banner for your guild", "🚩"),
        ("Friend Slot +5", "Expand friend list by 5 slots", "👥"),
        ("Activity Pin", "Pin one activity to your profile", "📌"),
        ("Challenge Issuer", "Issue a custom challenge to friends", "🎯"),
    ]
    for n, d, i in more_social:
        add(n, d, "social", {"social_points": 50 + idx * 6}, i, "rare")

    # Quick find: popular / featured
    featured = [
        ("Starter Bundle", "XP Booster 1h + Game Time 30m + 50 coins", "🎁"),
        ("Star Map Explorer Pack", "Star Map 25 Booster 6h + 2 investigations bonus", "🗺️"),
        ("Battle Starter Pack", "3 Battle Tickets + Strength Potion", "⚔️"),
        ("Creator Pack", "30s Video Credit + Generation Speed Booster", "🎬"),
    ]
    for n, d, i in featured:
        add(n, d, "premium", 120 + idx * 15, i, "epic")

    currency = [
        ("Coin Pack S", "100 coins", "🪙"),
        ("Coin Pack M", "500 coins", "🪙"),
        ("Coin Pack L", "2000 coins", "🪙"),
    ]
    for n, d, i in currency:
        add(n, d, "currency", 99 + idx * 50, i, "common")

    upgrades = [
        ("Upgrade Slot +1", "Extra upgrade slot", "⭐"),
        ("Storage Upgrade", "More storage space", "📦"),
        ("Speed Upgrade", "Faster processing", "⚡"),
    ]
    for n, d, i in upgrades:
        add(n, d, "upgrades", 75 + idx * 25, i, "rare")

    unified = [
        ("Unified Points Mix S", "Mixed points small", "💎"),
        ("Unified Points Mix M", "Mixed points medium", "💎"),
        ("Unified Points Mix L", "Mixed points large", "💎"),
    ]
    for n, d, i in unified:
        add(n, d, "unified_points", {"xp": 80, "battle_points": 40, "generation_points": 40}, i, "rare")

    # Inventory — ideas: Electric Magnet, Star Map, Lab, Verification, DNA, Rulebook, etc.
    inventory = [
        ("Electric Magnet Tech Download", "Download EM tech: verification, DNA test, star map specials", "🧲"),
        ("Verification Kit", "Run verification — validate tech integrity & endpoints", "✔️"),
        ("DNA Test Kit", "Run DNA test — biosignature check", "🧬"),
        ("Star Map — 7 Nearest Stars", "Host→b: Sun, Proxima, Alpha Cen, Barnard, Lalande, Sirius, Eps Eri, Ross 128", "🌟"),
        ("Star Map Flyers Pack", "Info & flyers for star map; Electric Magnet promo", "📄"),
        ("Event Tracker Module", "Track new tasks; agent event tracker", "🎯"),
        ("3D Monitor Access", "3D visual effects for vidgenerator (placeholder)", "🖥️"),
        ("Lab Experiments Pack", "Lab: EM download, Verification, DNA, Event Tracker", "🔬"),
        ("Rulebook V.2 — 19 Spells", "19 theme-based spells in 5 sectors", "📜"),
        ("Effect Clusters Pack", "Galactic, Verification, Combat, Support, Utility", "⚡"),
        ("Trophy Hunters Star Map", "Star map integrated with Trophy Hunters game", "🏆"),
        ("Agent Skills Upgrade", "Advance agent skill sets & abilities", "📋"),
        ("Geo Reference Unlock", "GPS coords & geo-reference via profile", "📍"),
        ("Aggregator Fulfill", "Fill missing Hunter game data via fulfill API", "🔗"),
        ("Hunters Profiling", "Agent tech, specials, level_info, geo_ref", "📊"),
        ("Unified Dashboard Verification", "Verification & plugin compatibility", "📊"),
        ("Generator Checkpoint Toggle", "Checkpoint on/off in generator", "✅"),
        ("Clip 4–6s + 30s Video", "Clip vs 30s vid service; service_worker", "🎬"),
        ("Point Triggers Bundle", "Triggers for run_verification, dna_test, view_star_map, etc.", "🔔"),
        ("Knowledge Base Expansion", "Database knowledge & new elements", "📚"),
        ("Communication Psychology — 25 Theories", "Agenda-setting, framing, influence; integrated with starmap, DNA, points", "🧠"),
        ("Comm-Psych Theory Unlock Pack", "Unlock 5 random Communication Psychology theories at once", "📋"),
        ("Framing & Influence Bundle", "Framing, Cultivation, Sleeper Effect, ELM — theory pack", "🎭"),
        ("Digital Power Pack", "Network effects, Echo chamber, Gamification, Scarcity — theory pack", "📡"),
        ("Monetization & Control Pack", "Reciprocity, FUD, Halo Effect, Symbolic Convergence — theory pack", "💎"),
    ]
    for j, (n, d, i) in enumerate(inventory):
        rare = "Tech" in n or "Module" in n or "Pack" in n or "Upgrade" in n or "Unlock" in n or "Bundle" in n
        add(n, d, "inventory", 55 + j * 8, i, "rare" if rare else "common")

    # Extra 40+ for 100+ total: Valued Seller's Choice, Game Time, Boosters
    for j in range(1, 15):
        add(f"Valued Seller's Choice #{j}", "Curated pick from valued sellers", "premium", 150 + j * 10, "🏅", "rare")
    for j in range(1, 15):
        add(f"Game Time +{j * 15}m", f"Extra {j * 15} min game session", "boosts", 20 + j * 2, "⏱️", "common")
    for j in range(1, 15):
        add(f"Booster Pack #{j}", "Assorted boosters pack", "boosts", 40 + j * 3, "📦", "common")

    # Super stack inventory expansion: large, structured inventory set.
    stack_lines = [
        ("Conversion Engine", "AI-assisted conversion module", "📈"),
        ("Retention Engine", "Lifecycle retention optimization module", "🔁"),
        ("Creative Engine", "Ad + content creative generation module", "🎨"),
        ("Video Factory", "Bulk short-video generation module", "🎬"),
        ("Battle Ops", "Battle readiness and tactical support module", "⚔️"),
        ("Growth Ops", "Cross-channel growth and scaling module", "🚀"),
        ("Commerce Ops", "Shop operations and merchandising module", "🛒"),
        ("Insight Ops", "Performance analytics and diagnostics module", "📊"),
        ("Automation Ops", "Workflow automation and trigger module", "🤖"),
        ("Trust Ops", "Quality, trust, and verification module", "🛡️"),
        ("Monetization Ops", "Offer and pricing optimization module", "💎"),
        ("Premium Vault", "Premium strategic assets module", "🏆"),
    ]
    for line_idx, (line_name, line_desc, icon) in enumerate(stack_lines, start=1):
        for tier in range(1, 11):
            add(
                f"{line_name} Pack T{tier}",
                f"{line_desc} tier {tier} with scalable stack bonuses",
                "inventory",
                120 + (line_idx * 14) + (tier * 22),
                icon,
                "legendary" if tier >= 8 else "rare",
            )

    add(
        "Super Stack Inventory Bundle",
        "One-click bundle for advanced inventory stacking and growth operations",
        "premium",
        4500,
        "🧱",
        "legendary",
    )
    add("Super Stack Core", "Core entitlement for inventory super-stack bundle", "inventory", 1200, "🧱", "legendary")
    add("Conversion Stack Pack", "Stacked conversion optimization assets", "inventory", 420, "📈", "rare")
    add("Retention Stack Pack", "Stacked retention optimization assets", "inventory", 420, "🔁", "rare")
    add("Creative Stack Pack", "Stacked creative production assets", "inventory", 420, "🎨", "rare")
    add("Video Stack Pack", "Stacked video production assets", "inventory", 420, "🎬", "rare")
    add("Battle Stack Pack", "Stacked battle operations assets", "inventory", 390, "⚔️", "rare")
    add("Growth Stack Pack", "Stacked growth operations assets", "inventory", 440, "🚀", "rare")
    add("Commerce Stack Pack", "Stacked commerce operations assets", "inventory", 440, "🛒", "rare")
    add("Insight Stack Pack", "Stacked analytics and diagnostics assets", "inventory", 440, "📊", "rare")
    add("Automation Stack Pack", "Stacked workflow automation assets", "inventory", 440, "🤖", "rare")
    add("Trust Stack Pack", "Stacked trust and quality assets", "inventory", 390, "🛡️", "rare")
    add("Premium Vault Stack", "Stacked premium strategic assets", "inventory", 980, "🏆", "legendary")

    # --- Seasonal themes + theme-tied boost & game time (append-only; keeps earlier shop-* ids stable) ---
    _wave_tags = ["seasonal_theme", "shop_wave_v5", "media_priority"]
    seasonal_theme_pack = [
        ("Spring Bloom", "Fresh spring UI palette — soft greens, petals, light rain glass", "🌸"),
        ("Summer Solaris", "Bright summer accents — gold, sky blue, heat shimmer", "☀️"),
        ("Autumn Ember", "Warm copper & amber leaves, cozy dusk", "🍂"),
        ("Winter Frost", "Ice-blue glass, frost edges, aurora hints", "❄️"),
        ("Aurora Borealis", "Northern lights shimmer across panels & nav", "🌌"),
        ("Crimson Night", "Deep red noir with subtle neon trim", "🌑"),
        ("Sage Matrix", "Matrix-style green code rain & terminal HUD", "🟩"),
        ("Coral Reef", "Teal bioluminescence & coral depth", "🪸"),
        ("Desert Mirage", "Dusk violet dunes & heat haze", "🏜️"),
        ("Cherry Blossom", "Soft pink sakura, lantern glow, calm UI", "🌺"),
        ("Midnight Velvet", "Luxury purple velvet with gold filigree", "🎩"),
    ]
    for n, d, icon in seasonal_theme_pack:
        add(
            n,
            d,
            "themes",
            72 + idx * 2,
            icon,
            "legendary" if idx % 5 == 0 else ("epic" if idx % 3 == 0 else "rare"),
            tags=_wave_tags,
        )

    season_boosters = [
        ("Spring Surge Booster 2h", "Seasonal: +18% XP & activity — spring bloom event (2 hours)", "🌸"),
        ("Solstice Blaze Booster 4h", "Seasonal: +22% generation points — summer solstice (4 hours)", "☀️"),
        ("Harvest Moon Booster 3h", "Seasonal: +25% quest rewards — autumn harvest (3 hours)", "🍂"),
        ("Winter Veil Booster 6h", "Seasonal: +15% battle & skill — winter veil (6 hours)", "❄️"),
        ("Equinox Balance Pack 24h", "Seasonal: mild boosts to all point types — equinox (24 hours)", "⚖️"),
    ]
    for n, d, icon in season_boosters:
        add(n, d, "boosts", 48 + idx * 3, icon, "epic", tags=["season_booster", "shop_wave_v5", "media_priority"])

    theme_synergy_boosts = [
        ("Aurora Synergy Booster 90m", "Synergy with Aurora Borealis theme — brighter FX & +XP pulse", "🌌"),
        ("Matrix Pulse Booster 1h", "Synergy with Sage Matrix — snappier HUD micro-feedback", "🟩"),
        ("Velvet Rush Booster 2h", "Synergy with Midnight Velvet — premium progression tick", "🎩"),
        ("Coral Current Booster 2h", "Synergy with Coral Reef — calmer focus, +activity", "🪸"),
        ("Crimson Edge Booster 1h", "Synergy with Crimson Night — contrast pop & +battle", "🌑"),
        ("Mirage Drift Booster 90m", "Synergy with Desert Mirage — exploration bonus", "🏜️"),
    ]
    for n, d, icon in theme_synergy_boosts:
        add(n, d, "boosts", 52 + idx * 3, icon, "rare", tags=["theme_synergy", "shop_wave_v5", "media_priority"])

    theme_game_time = [
        ("Theme Session +45m — Seasonal Pass", "Extra play time while any seasonal wave-v5 theme is equipped", "⏱️"),
        ("Theme Session +90m — Aurora Pack", "Stacked time when Aurora Borealis theme is active", "⏱️"),
        ("Theme Session +2h — Matrix Session", "Long session for Matrix / terminal HUD themes", "⏱️"),
        ("Theme Weekend Bridge +12h", "Bridge session across weekend — pairs with seasonal boosters", "🎫"),
    ]
    for n, d, icon in theme_game_time:
        add(n, d, "boosts", 40 + idx * 4, icon, "rare", tags=["theme_gametime", "shop_wave_v5", "media_priority"])

    # Dynamic "best agent for sale" offer
    try:
        from backend.services.agent_skillset import agent_skillset
        best = agent_skillset.get_best_agent_for_sale()
        if best:
            items.append({
                "id": "shop-best-agent-offer",
                "name": f"Best Agent License: {best.get('name', 'Elite Agent')}",
                "description": (
                    f"Top performer with level {best.get('level', 1)}, "
                    f"sales power {best.get('sales_skill_power_total', 0)}, "
                    f"battle power {best.get('battle_skill_power_total', 0)}."
                ),
                "category": "premium",
                "price": 1500 + int(best.get('level', 1)) * 100,
                "icon": "🤖",
                "rarity": "legendary",
                "agent_offer": best,
            })
    except Exception:
        pass

    # Tabletop-inspired themes (stable ids; append-only)
    add(
        "Magic: The Gathering",
        "Mana gems, duels, and spell-slinging chrome for your UI — tabletop CCG-inspired look. Fan tribute; not affiliated with Wizards of the Coast.",
        "themes",
        198,
        "🃏",
        "legendary",
        tags=["tabletop", "tcg", "mtg", "shop_wave_v6"],
        item_id="theme-magic-the-gathering",
    )
    add(
        "D&D",
        "Dungeon crawl chrome for your UI — dragons, polyhedral dice, maps, and scroll energy (former D6D line folded in). Fan tribute inspired by Dungeons & Dragons; not affiliated with Wizards of the Coast.",
        "themes",
        198,
        "🐉",
        "legendary",
        tags=["tabletop", "trpg", "dnd", "d6", "dice", "shop_wave_v6"],
        item_id="theme-dnd",
    )
    add(
        "Mafia",
        "Noir smoke, pinstripes, and low-lit backroom UI — cinematic organized-crime aesthetic (generic tribute; not an endorsement of real-world crime).",
        "themes",
        175,
        "🎩",
        "epic",
        tags=["cinema", "noir", "mafia", "shop_wave_v6"],
        item_id="theme-mafia",
    )
    add(
        "AI Core",
        "Neural lattice, glass HUD, and copilot glow — futurist AI workspace chrome for panels and nav.",
        "themes",
        175,
        "🤖",
        "epic",
        tags=["ai", "futurist", "copilot", "shop_wave_v6"],
        item_id="theme-ai-core",
    )
    add(
        "Christmas",
        "Pine, ribbon, frost glass, and warm lights — seasonal holiday UI theme.",
        "themes",
        120,
        "🎄",
        "rare",
        tags=["seasonal", "holiday", "christmas", "shop_wave_v6"],
        item_id="theme-christmas",
    )
    add(
        "Home Base",
        "Cozy desk lamp, wood tones, and calm neutrals — home office / studio feel for your UI.",
        "themes",
        120,
        "🏠",
        "rare",
        tags=["home", "workspace", "cozy", "shop_wave_v6"],
        item_id="theme-home-base",
    )

    # Monthly themes: one for each month (append-only)
    monthly_theme_pack = [
        ("January Aurora", "Crisp arctic glow and clean new-year energy for the UI.", "🧊"),
        ("February Velvet Hearts", "Soft velvet reds and warm highlights for a romantic winter mood.", "💘"),
        ("March Clover Rain", "Fresh rain, clover greens, and early-spring contrast.", "☘️"),
        ("April Blossom Rain", "Pastel blossom tones with rainy spring window light.", "🌸"),
        ("May Meadow", "Bright meadow greens with long-day calm and floral accents.", "🌿"),
        ("June Solstice", "Sunlit gold and sky tones inspired by midsummer evenings.", "🌞"),
        ("July Fireworks", "Neon night sky with festive spark trails and bold contrast.", "🎆"),
        ("August Sunset Coast", "Warm coastal dusk palette with amber and ocean haze.", "🏖️"),
        ("September Harvest Gold", "Harvest fields, warm amber, and structured autumn focus.", "🌾"),
        ("October Midnight Ember", "Spooky ember glow, moonlit shadows, and noir-orange accents.", "🎃"),
        ("November Hearth", "Cozy hearth browns, wool textures, and low-light comfort.", "🪵"),
        ("December Snowlight", "Snow glow, festive lights, and winter-glass shimmer.", "❄️"),
    ]
    month_ids = [
        "theme-january", "theme-february", "theme-march", "theme-april", "theme-may", "theme-june",
        "theme-july", "theme-august", "theme-september", "theme-october", "theme-november", "theme-december",
    ]
    for m_i, (name, desc, icon) in enumerate(monthly_theme_pack):
        add(
            name,
            desc,
            "themes",
            130 + (m_i % 4) * 10,
            icon,
            "rare" if m_i < 8 else "epic",
            tags=["monthly_theme", "shop_wave_v7", "calendar_theme"],
            item_id=month_ids[m_i],
        )

    # Profile MN2 "5-day" wallet monitor (UTC bars) — thematic shop tie-ins (append-only)
    add(
        "5D Monitor — Dual-Bar Pro",
        "Tie-in flair for the Profile MN2 5-day chart (per-day in/out bars). Cosmetic-telemetry vibe; does not change on-chain balances.",
        "tech",
        140,
        "📊",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-dual-bar-pro",
    )
    add(
        "5D Monitor — UTC Rail Skin",
        "Skin pack language for UTC midnight alignment on the 5-day wallet strip labels.",
        "cosmetic",
        95,
        "🕛",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-utc-rail-skin",
    )
    add(
        "5D Monitor — Net Flow Pulse 24h",
        "24h UI pulse that highlights net MN2 direction on your next Profile refresh (stacks narratively with other boosts).",
        "boosts",
        110,
        "📈",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-net-flow-24h",
    )
    add(
        "5D Monitor — Deep Stack Ledger",
        "Ledger-styled inventory ribbon echoing five-day depth on the MN2 card (read-only presentation token).",
        "inventory",
        130,
        "📒",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-deep-stack-ledger",
    )
    add(
        "5D Monitor — Withdrawal Beacon",
        "Reminder token: pair with the 5-day chart before MN2 withdraw — emphasizes safety checks on Profile.",
        "tech",
        125,
        "📡",
        "rare",
        tags=["mn2_5d", "profile_wallet", "wallet_monitor"],
        item_id="mn2-5d-withdrawal-beacon",
    )

    # ---- Top 25 Legends: flagship numbered collectible series (June 2026 wave) ----
    # 25 ranked, escalating items spanning every MasterNoder surface. Coin-priced so
    # they work with coins / in-wallet MN2 / on-chain MN2 / PayPal and earn loyalty.
    top25_series = [
        ("Genesis Node Sigil", "Founding-block sigil — proof you were here from the start.", "🌱"),
        ("Hunter's First Mark", "Engraved mark for completing your first Hunter contract.", "🎯"),
        ("Star Map Cartographer", "Charter badge for mapping the Star Map 25 frontier.", "🗺️"),
        ("Arena Gladiator Crest", "Crest forged in the weekly Arena.", "🛡️"),
        ("Casino High-Roller Chip", "Solid chip minted for the bold at the tables.", "🎰"),
        ("Lab Pioneer Seal", "Seal of the first experiments in the Lab.", "🔬"),
        ("Agent Commander Insignia", "Insignia for fielding a full agent squad.", "🎖️"),
        ("Quest Vanguard Banner", "Banner carried by the relentless quest-runner.", "🚩"),
        ("Skill Sage Emblem", "Emblem of mastery across the skill trees.", "🧠"),
        ("MN2 Holder's Token", "Token honoring committed MN2 holders.", "🪙"),
        ("Staking Architect Medal", "Medal for engineering a staking strategy.", "🏗️"),
        ("Generation Maestro Reel", "Reel celebrating prolific creators.", "🎬"),
        ("Trophy Hall Keystone", "Keystone for a stacked trophy hall.", "🏆"),
        ("Marketplace Magnate Ledger", "Ledger of a thriving auction trader.", "📒"),
        ("Loyalty Luminary Star", "Star awarded to top loyalty members.", "✨"),
        ("Battle Warlord Pennant", "Pennant of a feared arena warlord.", "⚔️"),
        ("Explorer Voyager Compass", "Compass for charting the deepest sectors.", "🧭"),
        ("Casino Fortune Crown", "Crown for legendary fortune at the tables.", "👑"),
        ("Hunter Apex Trophy", "Apex trophy for the elite Hunter.", "🦅"),
        ("Star Map Sovereign Orb", "Orb radiating control over the Star Map.", "🔮"),
        ("MN2 Whale Monolith", "Monolith reserved for true MN2 whales.", "🐋"),
        ("Eternal Founder Halo", "Halo for the eternal founders' circle.", "😇"),
        ("Mythic Agent Ascendant", "Mark of an ascended, mythic agent operator.", "🛰️"),
        ("Grandmaster Legend Plate", "Plate engraved for grandmasters of the platform.", "🥇"),
        ("Masternoder Sovereign Crown", "The pinnacle: #25 of the Top 25 Legends series.", "💠"),
    ]
    for n, (nm, desc, icon) in enumerate(top25_series, start=1):
        if n <= 10:
            price = 150 + n * 60
        elif n <= 20:
            price = 800 + (n - 10) * 150
        else:
            price = 2500 + (n - 20) * 600
        if n <= 8:
            rarity = "rare"
        elif n <= 16:
            rarity = "epic"
        else:
            rarity = "legendary"
        add(
            f"#{n:02d} {nm}",
            f"{desc} — Top 25 Legends, rank {n} of 25.",
            "top25",
            price,
            icon,
            rarity,
            tags=["top25", "collectible", "series_top25", "limited", f"rank_{n}", "shop_wave_jun2026"],
            item_id=f"top25-{n:02d}",
        )

    return items


@shop_bp.route('/api/shop/config', methods=['GET'])
def get_shop_config():
    """Feature flags and config for shop UI (use_shop_v3, shop_ui_version, deep links)."""
    serial_classes: list = []
    try:
        from backend.services.shop_serial_service import serial_class_summary

        serial_classes = serial_class_summary(_get_shop_items())
    except Exception:
        pass
    try:
        from backend.services.shop_api_line_checks import load_shop_v4_api_line_checks

        api_line_checks = load_shop_v4_api_line_checks()
    except Exception:
        api_line_checks = {"version": 0, "checks": []}
    try:
        from backend.services.monetization_config_service import (
            get_payment_rails_catalog,
            get_public_content_bundles,
            get_public_digital_goods,
        )

        monetization_shop = {
            "payment_rails_catalog": get_payment_rails_catalog(),
            "digital_goods": get_public_digital_goods(),
            "content_bundles": get_public_content_bundles(),
        }
    except Exception:
        monetization_shop = {"payment_rails_catalog": {}, "digital_goods": [], "content_bundles": []}
    try:
        from backend.services.monetization_config_service import get_shop_monetization

        _mon = get_shop_monetization()
        monetization_shop["v92"] = {
            "version": _mon.get("version") or "9.2.0",
            "vip_pass": bool(_mon.get("vip_pass")),
            "mystery_boxes": len(_mon.get("mystery_boxes") or []),
            "spin_wheel": bool(_mon.get("spin_wheel")),
            "flash_sales": bool(_mon.get("flash_sales")),
            "loyalty": bool(_mon.get("loyalty")),
            "gifting": bool(_mon.get("gifting")),
            "auction_feature": bool(_mon.get("auction_feature")),
        }
    except Exception:
        pass
    return jsonify({
        "success": True,
        "use_shop_v3": USE_SHOP_V3,
        "shop_ui_version": SHOP_UI_VERSION,
        "profile_url": "/profile",
        "shop_url": "/shop",
        "api_line_checks": api_line_checks,
        "serial_classes": serial_classes,
        "monetization_shop": monetization_shop,
        "shop_media": {
            "manifest": "data/shop_item_media.json",
            "items_static_base": "/static/shop/items/",
            "clips_static_base": "/static/shop/clips/",
            "sounds_static_base": "/static/shop/sounds/",
            "integration_health": "/api/shop/integration-health",
        },
    }), 200


@shop_bp.route('/api/shop/payment-health', methods=['GET'])
def shop_payment_health():
    """
    MN2 daemon RPC + PayPal configuration (optional live token probe).
    GET ?probe=1 to call PayPal OAuth (slower; use in ops scripts, not every page load).
    """
    probe = (request.args.get("probe") or "").strip().lower() in ("1", "true", "yes")
    payload = {
        "success": True,
        "shop_ui_version": SHOP_UI_VERSION,
        "mn2_daemon": {},
        "paypal": {},
    }
    try:
        from backend.services.mn2_rpc_client import health_check as mn2_health_check

        mn2 = mn2_health_check()
        payload["mn2_daemon"] = {
            "status": mn2.get("status"),
            "block_height": mn2.get("block_height"),
            "latency_ms": mn2.get("latency_ms"),
        }
        if mn2.get("error"):
            payload["mn2_daemon"]["error"] = mn2["error"]
        if mn2.get("credentials"):
            payload["mn2_daemon"]["credentials"] = mn2["credentials"]
        if mn2.get("status") == "unreachable":
            try:
                from backend.services.mn2_chainz import chainz_getblockcount

                ch = chainz_getblockcount()
                if ch is not None:
                    payload["mn2_daemon"]["chainz_block_height_fallback"] = ch
            except Exception:
                pass
    except Exception as e:
        payload["mn2_daemon"] = {"status": "error", "error": str(e)}

    paypal_id = (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
    paypal_secret = (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
    payload["paypal"] = {
        "credentials_configured": bool(paypal_id and paypal_secret),
        "mode": (os.environ.get("PAYPAL_MODE") or "sandbox").strip() or "sandbox",
    }
    if probe:
        try:
            from backend.services.paypal_service import get_access_token

            tok = get_access_token()
            payload["paypal"]["api_token_ok"] = bool(tok)
            if not tok:
                payload["paypal"]["api_error"] = "OAuth token not returned (check PAYPAL_* and network)"
        except Exception as e:
            payload["paypal"]["api_token_ok"] = False
            payload["paypal"]["api_error"] = str(e)

    try:
        from backend.services.shop_db_service import get_shop_storage_info

        payload["shop_storage"] = get_shop_storage_info()
    except Exception as e:
        payload["shop_storage"] = {"mode": "unknown", "error": str(e)}

    return jsonify(payload), 200


@shop_bp.route("/api/shop/integration-health", methods=["GET"])
def shop_integration_health():
    """
    Shop catalog + optional media manifest + generator pipeline readiness.
    Use for debugging API connections between Shop and AI video/image services.
    """
    out: dict = {
        "success": True,
        "shop_ui_version": SHOP_UI_VERSION,
        "shop": {},
        "media_manifest": {},
        "generator": {},
    }
    try:
        items = _get_shop_items()
        out["shop"]["items_count"] = len(items or [])
        out["shop"]["sample_item_ids"] = [i.get("id") for i in (items or [])[:5]]
    except Exception as e:
        out["shop"]["error"] = str(e)
    try:
        from backend.services.shop_media_service import load_manifest, manifest_path

        man = load_manifest()
        with_image = sum(1 for v in man.values() if isinstance(v, dict) and v.get("image_url"))
        with_clip = sum(1 for v in man.values() if isinstance(v, dict) and v.get("clip_url"))
        out["media_manifest"] = {
            "path": manifest_path(),
            "entries": len(man),
            "with_image_url": with_image,
            "with_clip_url": with_clip,
        }
    except Exception as e:
        out["media_manifest"] = {"error": str(e)}
    try:
        from backend.services.video_generator_service import _check_generation_services
        from backend.services.llm_service import configured_providers

        ok, msg, detail = _check_generation_services()
        providers = []
        try:
            providers = configured_providers()
        except Exception:
            pass
        out["generator"] = {
            "ready": ok,
            "message": msg,
            "service_check": detail,
            "configured_provider_count": len(providers),
        }
    except Exception as e:
        out["generator"] = {"ready": False, "error": str(e)}

    return jsonify(out), 200


@shop_bp.route('/api/shop/currency', methods=['GET'])
@shop_bp.route('/api/game/shop/currency', methods=['GET'])
def get_shop_currency():
    """Get user currency for shop"""
    try:
        user_id = request.args.get('user_id') or _resolve_user_id()
        
        # Try to get currency from unified points system
        try:
            from backend.services.unified_points_database import unified_points_db
            points_result = unified_points_db.get_all_points(user_id)
            if points_result.get('success'):
                user_points = points_result.get('points', {})
                currency = int(user_points.get('coins', 0) or 0)
                return jsonify({
                    'success': True,
                    'currency': currency,
                    'coins': currency,
                    'balance': {'coins': currency},
                    'user_id': user_id
                }), 200
        except ImportError:
            # Unified points system not available, return default
            pass
        except Exception as e:
            # Service available but error occurred, log and return default
            print(f"Error getting currency from unified_points_db: {e}")
        
        # Fallback: Default currency response
        return jsonify({
            'success': True,
            'currency': 0,
            'coins': 0,
            'balance': {'coins': 0},
            'user_id': user_id
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@shop_bp.route('/api/shop/coin-packs', methods=['GET'])
def get_coin_packs():
    """Get PayPal coin packs for buying coins with real money."""
    return jsonify({'success': True, 'coin_packs': get_paypal_coin_packs()}), 200


@shop_bp.route('/api/shop/mn2-packs', methods=['GET'])
def get_mn2_packs_route():
    """Get MN2 packs for buying in-wallet MN2 with PayPal or shop coins."""
    return jsonify({'success': True, 'mn2_packs': get_mn2_packs()}), 200


@shop_bp.route('/api/shop/paypal-items', methods=['GET'])
def get_paypal_shop_items():
    """Get shop items that can be purchased directly with PayPal (price_usd)."""
    items = _get_paypal_shop_items()
    return jsonify({'success': True, 'paypal_items': items}), 200


@shop_bp.route('/api/shop/digital-goods', methods=['GET'])
def get_digital_goods_catalog():
    """Digital goods catalog with ownership/download metadata for Phase 2 delivery."""
    try:
        user_id = request.args.get('user_id') or _resolve_user_id()
        goods = []
        for good in _digital_goods_config():
            iid = good.get("id")
            is_free = (good.get("delivery") == "free_info") or float(good.get("price_usd") or 0) <= 0 and int(good.get("price_coins") or 0) <= 0
            owned = bool(is_free or _user_owns_shop_item(user_id, iid))
            artifact_path = _artifact_abs_path(good)
            row = dict(good)
            row.pop("artifact_path", None)
            row["owned"] = owned
            row["artifact_available"] = bool(artifact_path and os.path.isfile(artifact_path))
            row["download_url"] = f"/api/shop/digital-goods/{iid}/download" if owned and row["artifact_available"] else None
            goods.append(row)
        return jsonify({'success': True, 'user_id': user_id, 'digital_goods': goods}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'digital_goods': []}), 500


@shop_bp.route('/api/shop/content-bundles', methods=['GET'])
def get_content_bundles_catalog():
    """Content bundles with one checkout SKU and expanded child item summary."""
    try:
        try:
            from backend.services.monetization_config_service import get_public_content_bundles

            bundles = get_public_content_bundles()
        except Exception:
            bundles = []
        return jsonify({'success': True, 'content_bundles': bundles}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'content_bundles': []}), 500


@shop_bp.route('/api/shop/digital-goods/<item_id>/download', methods=['GET'])
def download_digital_good(item_id):
    """Download a digital good if free or present in the user's inventory."""
    try:
        good = _digital_good_by_id(item_id)
        if not good:
            return jsonify({'success': False, 'error': 'Digital good not found'}), 404

        is_free = (good.get("delivery") == "free_info") or float(good.get("price_usd") or 0) <= 0 and int(good.get("price_coins") or 0) <= 0
        user_id = request.args.get('user_id') or _resolve_user_id()
        if not is_free and not _user_owns_shop_item(user_id, item_id):
            return jsonify({
                'success': False,
                'error': 'Digital good not owned',
                'item_id': item_id,
                'user_id': user_id,
            }), 403

        path = _artifact_abs_path(good)
        if not path or not os.path.isfile(path):
            return jsonify({'success': False, 'error': 'Artifact file missing', 'item_id': item_id}), 404

        return send_file(
            path,
            as_attachment=True,
            download_name=good.get("download_filename") or os.path.basename(path),
            mimetype="text/markdown",
            max_age=0,
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'item_id': item_id}), 500


@shop_bp.route('/api/game/shop/items', methods=['GET'])
def game_shop_items():
    """Get shop items (optionally filtered by category)."""
    try:
        category = (request.args.get('category') or '').strip().lower()
        items = _get_shop_items()
        if category:
            items = [i for i in items if (i.get('category') or '').lower() == category]
        return jsonify({'success': True, 'items': items}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'items': []}), 500


def _get_shop_items():
    """Items from DB if migration run, else seeded list."""
    try:
        from backend.services.shop_db_service import get_shop_items_from_db
        items = get_shop_items_from_db()
    except Exception:
        items = None
    items = items if items else _seed_shop_items()
    existing_ids = {i.get("id") for i in items or [] if isinstance(i, dict)}
    for digital_item in _digital_goods_shop_items():
        if digital_item.get("id") not in existing_ids:
            items.append(digital_item)
            existing_ids.add(digital_item.get("id"))
    for bundle_item in _content_bundle_shop_items():
        if bundle_item.get("id") not in existing_ids:
            items.append(bundle_item)
            existing_ids.add(bundle_item.get("id"))
    for mn2_pack_item in _mn2_pack_shop_items():
        if mn2_pack_item.get("id") not in existing_ids:
            items.append(mn2_pack_item)
            existing_ids.add(mn2_pack_item.get("id"))
    for package_item in _ptc_advertiser_package_shop_items():
        if package_item.get("id") not in existing_ids:
            items.append(package_item)
            existing_ids.add(package_item.get("id"))
    for exchange_item in _exchange_shop_items():
        if exchange_item.get("id") not in existing_ids:
            items.append(exchange_item)
            existing_ids.add(exchange_item.get("id"))
    # Add price_usd for items with coin price (enables direct PayPal purchase)
    for item in items or []:
        if item.get("id") in get_coin_pack_map() or item.get("id") in get_mn2_pack_map():
            continue
        price = item.get("price")
        if isinstance(price, (int, float)) and price > 0:
            item["price_usd"] = max(0.99, round(float(price) / 100, 2))
    try:
        from backend.services.shop_media_service import merge_into_items

        items = merge_into_items(items or [])
    except Exception:
        pass
    try:
        from backend.services.shop_serial_service import enrich_shop_items_serial

        items = enrich_shop_items_serial(items or [])
    except Exception:
        pass
    return items


def _super_stack_bundle_entries():
    """Server-side bundle definition for one-click inventory stacking."""
    return [
        {'item_id': 'shop-best-agent-offer', 'item_name': 'Best Agent License', 'quantity': 1},
        {'item_id': 'shop-super-stack-core', 'item_name': 'Super Stack Core', 'quantity': 1},
        {'item_id': 'shop-super-stack-conversion', 'item_name': 'Conversion Stack Pack', 'quantity': 3},
        {'item_id': 'shop-super-stack-retention', 'item_name': 'Retention Stack Pack', 'quantity': 3},
        {'item_id': 'shop-super-stack-creative', 'item_name': 'Creative Stack Pack', 'quantity': 3},
        {'item_id': 'shop-super-stack-video', 'item_name': 'Video Stack Pack', 'quantity': 3},
        {'item_id': 'shop-super-stack-battle', 'item_name': 'Battle Stack Pack', 'quantity': 2},
        {'item_id': 'shop-super-stack-growth', 'item_name': 'Growth Stack Pack', 'quantity': 4},
        {'item_id': 'shop-super-stack-commerce', 'item_name': 'Commerce Stack Pack', 'quantity': 4},
        {'item_id': 'shop-super-stack-insight', 'item_name': 'Insight Stack Pack', 'quantity': 4},
        {'item_id': 'shop-super-stack-automation', 'item_name': 'Automation Stack Pack', 'quantity': 4},
        {'item_id': 'shop-super-stack-trust', 'item_name': 'Trust Stack Pack', 'quantity': 2},
        {'item_id': 'shop-super-stack-premium', 'item_name': 'Premium Vault Stack', 'quantity': 1},
    ]


@shop_bp.route('/api/shop-v3/items', methods=['GET'])
def shop_v3_items():
    """Shop-v3: items, artifacts, boosters, category_counts (for overview), etc. (unified format)."""
    try:
        all_items = _get_shop_items()
        digital_goods_items = [i for i in (all_items or []) if i.get('category') == 'digital_goods']
        bundle_items = [i for i in (all_items or []) if i.get('category') == 'bundles']
        categories = {}
        for i in all_items or []:
            cat = (i.get('category') or 'other').strip().lower()
            categories[cat] = categories.get(cat, 0) + 1
        return jsonify({
            'success': True,
            'items': all_items,
            'category_counts': categories,
            'artifacts': digital_goods_items,
            'knowledge_items': digital_goods_items,
            'intelligence_items': [],
            'bundles': bundle_items,
            'boosters': [i for i in (all_items or []) if i.get('category') == 'boosts'],
            'unified_points_items': [i for i in (all_items or []) if i.get('category') == 'unified_points'],
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'items': [],
            'category_counts': {},
            'artifacts': [],
            'knowledge_items': [],
            'intelligence_items': [],
            'bundles': [],
            'boosters': [],
            'unified_points_items': [],
        }), 500


@shop_bp.route('/api/shop-v3/categories', methods=['GET'])
def shop_v3_categories():
    """Return category list with item counts for shop overview and filtering."""
    try:
        all_items = _get_shop_items()
        categories = {}
        for i in all_items or []:
            cat = (i.get('category') or 'other').strip().lower()
            categories[cat] = categories.get(cat, 0) + 1
        category_list = [{'id': k, 'name': k.replace('_', ' ').title(), 'count': v} for k, v in sorted(categories.items(), key=lambda x: -x[1])]
        return jsonify({'success': True, 'categories': category_list, 'total_items': len(all_items or [])}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'categories': [], 'total_items': 0}), 500


@shop_bp.route('/api/game/shop/purchase', methods=['POST'])
@shop_bp.route('/api/shop-v3/purchase', methods=['POST'])
def shop_purchase():
    """Purchase handler with currency/unified points deduction."""
    try:
        data = request.get_json() or {}
        item_id = data.get('item_id') or request.form.get('item_id')
        user_id = (
            data.get('user_id') or request.form.get('user_id') or request.args.get('user_id')
        ) or _resolve_user_id()
        quantity = int(data.get('quantity', 1))
        
        if not item_id:
            return jsonify({'success': False, 'error': 'Missing item_id'}), 400
        
        # Get all shop items to find the requested item (DB or seed)
        all_items = _get_shop_items()
        item = next((i for i in all_items if i.get('id') == item_id), None)
        
        if not item:
            return jsonify({'success': False, 'error': f'Item {item_id} not found'}), 404
        
        # Get item price
        item_price = item.get('price', 0)
        
        # Handle unified points pricing (object with multiple point types)
        if isinstance(item_price, dict):
            # Check and deduct unified points
            try:
                from backend.services.unified_points_database import unified_points_db
                
                # Get current user points
                points_result = unified_points_db.get_all_points(user_id)
                if not points_result.get('success'):
                    return jsonify({'success': False, 'error': 'Failed to retrieve user points'}), 500
                
                user_points = points_result.get('points', {})
                
                # Check if user has enough points for each required type
                insufficient_points = []
                for point_type, required_amount in item_price.items():
                    # Map point type names to database field names
                    point_type_map = {
                        'xp': 'xp_total',
                        'battle_points': 'battle_points',
                        'activity_points': 'activity_points',
                        'skill_points': 'skill_points',
                        'generation_points': 'generation_points',
                        'progression_points': 'progression_points',
                        'social_points': 'social_points',
                        'achievement_points': 'achievement_points',
                        'creative_points': 'creative_points',
                        'combat_points': 'combat_points',
                        'energy_points': 'energy_points'
                    }
                    
                    db_field = point_type_map.get(point_type, point_type)
                    current_balance = user_points.get(db_field, 0) or 0
                    total_required = float(required_amount) * quantity
                    
                    if current_balance < total_required:
                        insufficient_points.append(f"{point_type}: need {total_required}, have {current_balance}")
                
                if insufficient_points:
                    return jsonify({
                        'success': False,
                        'error': 'Insufficient points',
                        'details': insufficient_points
                    }), 400
                
                # Deduct points for each type
                deduction_results = []
                for point_type, required_amount in item_price.items():
                    point_type_map = {
                        'xp': 'xp',
                        'battle_points': 'battle_points',
                        'activity_points': 'activity_points',
                        'skill_points': 'skill_points',
                        'generation_points': 'generation_points',
                        'progression_points': 'progression_points',
                        'social_points': 'social_points',
                        'achievement_points': 'achievement_points',
                        'creative_points': 'creative_points',
                        'combat_points': 'combat_points',
                        'energy_points': 'energy_points'
                    }
                    
                    db_field = point_type_map.get(point_type, point_type)
                    total_deduction = float(required_amount) * quantity
                    
                    # Deduct points (negative amount)
                    result = unified_points_db.add_points(
                        user_id=user_id,
                        point_type=db_field,
                        amount=-total_deduction,
                        source='shop_purchase',
                        metadata={'item_id': item_id, 'item_name': item.get('name'), 'quantity': quantity}
                    )
                    
                    if not result.get('success'):
                        deduction_results.append(f"Failed to deduct {point_type}")
                
                if deduction_results:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to complete purchase',
                        'details': deduction_results
                    }), 500
                
                balance_after_pts = unified_points_db.get_all_points(user_id).get('points', {})

                # Record purchase and inventory. If this fails, refund the point deductions.
                try:
                    from backend.services.shop_db_service import fulfill_shop_purchase
                    purchase_id = fulfill_shop_purchase(
                        user_id=user_id, item_id=item_id, item_name=item.get('name', ''),
                        quantity=quantity, price_type='unified_points',
                        price_paid_coins=0, price_paid_points=item_price,
                        balance_before=user_points, balance_after=balance_after_pts
                    )
                except Exception as ex:
                    for point_type, required_amount in item_price.items():
                        point_type_map = {
                            'xp': 'xp',
                            'battle_points': 'battle_points',
                            'activity_points': 'activity_points',
                            'skill_points': 'skill_points',
                            'generation_points': 'generation_points',
                            'progression_points': 'progression_points',
                            'social_points': 'social_points',
                            'achievement_points': 'achievement_points',
                            'creative_points': 'creative_points',
                            'combat_points': 'combat_points',
                            'energy_points': 'energy_points'
                        }
                        db_field = point_type_map.get(point_type, point_type)
                        unified_points_db.add_points(
                            user_id=user_id,
                            point_type=db_field,
                            amount=float(required_amount) * quantity,
                            source='shop_purchase_refund',
                            metadata={'item_id': item_id, 'item_name': item.get('name'), 'quantity': quantity, 'reason': 'fulfillment_failed', 'error': str(ex)}
                        )
                    return jsonify({
                        'success': False,
                        'error': 'Shop fulfillment failed; point deductions were refunded',
                        'details': str(ex),
                    }), 500
                _apply_shop_item_effects(user_id, item_id, item, quantity, purchase_ref=str(purchase_id) if purchase_id else None)
                
                # Record agent activity for the shop purchase
                try:
                    from backend.services.agent_db_service import agent_db_service
                    from backend.services.user_agent_skills import user_agent_skills
                    _skills_data = user_agent_skills.get_user_skills(user_id)
                    _assigned = _skills_data.get('assigned_agents', [])
                    _agent = next((a for a in _assigned if 'social' in a or 'content' in a), _assigned[0] if _assigned else None)
                    if _agent:
                        agent_db_service.record_agent_activity(
                            user_id=user_id, agent_id=_agent,
                            action='shop_purchase', skill='shop_purchase',
                            xp_gained=10, points_gained=0,
                            metadata={'item_id': item_id, 'item_name': item.get('name'), 'quantity': quantity}
                        )
                except Exception:
                    pass

                try:
                    from backend.services.unified_points_sync import unified_points_sync_device
                    unified_points_sync_device.record_domain_sync('shop')
                except Exception:
                    pass
                # Purchase successful
                return jsonify({
                    'success': True,
                    'message': f'Purchased {quantity}x {item.get("name")}',
                    'item': item,
                    'item_id': item_id,
                    'user_id': user_id,
                    'quantity': quantity,
                    'price_paid': item_price,
                    'purchase_id': purchase_id
                }), 200
                
            except ImportError:
                return jsonify({
                    'success': False,
                    'error': 'Unified points system not available'
                }), 500
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Purchase failed: {str(e)}'
                }), 500
        
        # Handle traditional coin pricing (integer)
        else:
            total_cost = int(item_price) * quantity

            # Pay with MN2 (Phase 5): optional payment_method=mn2 for coin-priced items
            if (data.get('payment_method') or '').strip().lower() == 'mn2' and total_cost >= 0:
                try:
                    from backend.services.shop_mn2_purchase_core import purchase_with_mn2_balance

                    body, status = purchase_with_mn2_balance(user_id, item_id, quantity, agent_id=None)
                    return jsonify(body), status
                except Exception as e:
                    return jsonify({'success': False, 'error': f'MN2 purchase failed: {str(e)}'}), 500

            try:
                from backend.services.unified_points_database import unified_points_db
                
                # Get user currency from unified points
                points_result = unified_points_db.get_all_points(user_id)
                if not points_result.get('success'):
                    return jsonify({'success': False, 'error': 'Failed to retrieve user currency'}), 500
                
                user_points = points_result.get('points', {})
                user_currency = int(user_points.get('coins', 0) or 0)
                
                if user_currency < total_cost:
                    return jsonify({
                        'success': False,
                        'error': f'Insufficient coins. Need {total_cost}, have {user_currency}'
                    }), 400
                
                # Deduct currency using unified points system
                deduct_result = unified_points_db.add_points(
                    user_id=user_id,
                    point_type='coins',
                    amount=-total_cost,
                    source='shop_purchase',
                    metadata={'item_id': item_id, 'item_name': item.get('name'), 'quantity': quantity}
                )
                
                if not deduct_result.get('success'):
                    return jsonify({
                        'success': False,
                        'error': 'Failed to deduct currency'
                    }), 500

                balance_after_coins = unified_points_db.get_all_points(user_id).get('points', {})
                
                # Record purchase and inventory. If this fails, refund the coin deduction.
                try:
                    from backend.services.shop_db_service import fulfill_shop_purchase
                    purchase_id = fulfill_shop_purchase(
                        user_id=user_id, item_id=item_id, item_name=item.get('name', ''),
                        quantity=quantity, price_type='coins',
                        price_paid_coins=total_cost, price_paid_points=None,
                        balance_before=user_points, balance_after=balance_after_coins,
                    )
                except Exception as ex:
                    unified_points_db.add_points(
                        user_id=user_id,
                        point_type='coins',
                        amount=total_cost,
                        source='shop_purchase_refund',
                        metadata={'item_id': item_id, 'item_name': item.get('name'), 'quantity': quantity, 'reason': 'fulfillment_failed', 'error': str(ex)}
                    )
                    return jsonify({
                        'success': False,
                        'error': 'Shop fulfillment failed; coins were refunded',
                        'details': str(ex),
                    }), 500
                _apply_shop_item_effects(user_id, item_id, item, quantity, purchase_ref=str(purchase_id) if purchase_id else None)

                # Shop V9.2: award loyalty/cashback for coin spend on the whole catalog.
                loyalty_earned = 0
                try:
                    from backend.services.shop_monetization_service import accrue_purchase_loyalty

                    loyalty_earned = int((accrue_purchase_loyalty(user_id, total_cost) or {}).get('earned') or 0)
                except Exception:
                    loyalty_earned = 0

                try:
                    from backend.services.unified_points_sync import unified_points_sync_device
                    unified_points_sync_device.record_domain_sync('shop')
                except Exception:
                    pass
                # Purchase successful
                return jsonify({
                    'success': True,
                    'message': f'Purchased {quantity}x {item.get("name")}',
                    'item': item,
                    'item_id': item_id,
                    'user_id': user_id,
                    'quantity': quantity,
                    'price_paid': total_cost,
                    'remaining_currency': user_currency - total_cost,
                    'loyalty_earned': loyalty_earned,
                    'purchase_id': purchase_id
                }), 200
                
            except ImportError:
                # Unified points system not available - allow purchase without deduction
                return jsonify({
                    'success': True,
                    'message': f'Purchased {quantity}x {item.get("name")} (currency system unavailable)',
                    'item': item,
                    'item_id': item_id,
                    'user_id': user_id,
                    'quantity': quantity,
                    'price_paid': int(item_price) * quantity,
                    'warning': 'Currency deduction skipped - unified points system unavailable'
                }), 200
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Purchase failed: {str(e)}'
                }), 500
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/api/shop/purchases', methods=['GET'])
def shop_purchases():
    """Get purchase history for user (requires migration)."""
    try:
        user_id = request.args.get('user_id') or _resolve_user_id()
        limit = min(int(request.args.get('limit', 50)), 100)
        try:
            from backend.services.shop_db_service import get_purchases
            purchases = get_purchases(user_id, limit=limit)
        except Exception:
            purchases = []
        return jsonify({'success': True, 'user_id': user_id, 'purchases': purchases}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'purchases': []}), 500


@shop_bp.route('/api/shop/inventory', methods=['GET'])
def shop_inventory():
    """Get user inventory (requires migration)."""
    try:
        user_id = request.args.get('user_id') or _resolve_user_id()
        try:
            from backend.services.shop_db_service import get_inventory
            inventory = get_inventory(user_id)
        except Exception:
            inventory = []
        return jsonify({'success': True, 'user_id': user_id, 'inventory': inventory}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'inventory': []}), 500


@shop_bp.route('/api/shop/auction/listings', methods=['GET'])
def shop_auction_listings():
    """Shop v5 auction house: active fixed-price user listings."""
    try:
        seller_id = (request.args.get('seller_id') or '').strip() or None
        limit = min(int(request.args.get('limit', 100)), 200)
        from backend.services.shop_auction_service import list_active_listings
        listings = list_active_listings(seller_id=seller_id, limit=limit)
        # Shop V9.2: paid "featured" listings float to the top of the market.
        try:
            from backend.services.shop_monetization_service import get_featured_listing_ids

            featured = set(get_featured_listing_ids())
            if featured:
                for row in listings:
                    row['featured'] = row.get('listing_id') in featured
                listings.sort(key=lambda r: (not r.get('featured'), r.get('created_at') or ''), reverse=False)
                # keep newest-first within each group: re-sort featured then others by created_at desc
                feat = [r for r in listings if r.get('featured')]
                rest = [r for r in listings if not r.get('featured')]
                feat.sort(key=lambda r: r.get('created_at') or '', reverse=True)
                rest.sort(key=lambda r: r.get('created_at') or '', reverse=True)
                listings = feat + rest
        except Exception:
            pass
        return jsonify({'success': True, 'listings': listings, 'count': len(listings)}), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'listings': [],
            'count': 0,
            'warning': 'Auction listings are temporarily unavailable',
            'error': str(e),
        }), 200


@shop_bp.route('/api/shop/auction/my-listings', methods=['GET'])
def shop_auction_my_listings():
    """Shop v5 auction house: listings bought/sold/active for a profile."""
    try:
        user_id = request.args.get('user_id') or _resolve_user_id()
        limit = min(int(request.args.get('limit', 100)), 200)
        from backend.services.shop_auction_service import list_user_listings
        return jsonify({'success': True, 'user_id': user_id, **list_user_listings(user_id, limit=limit)}), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'user_id': request.args.get('user_id') or 'default_user',
            'selling': [],
            'bought': [],
            'sold': [],
            'warning': 'Auction listings are temporarily unavailable',
            'error': str(e),
        }), 200


@shop_bp.route('/api/shop/auction/list', methods=['POST'])
def shop_auction_create_listing():
    """Create a fixed-price listing by reserving an item from user inventory."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id') or _resolve_user_id()
        item_id = (data.get('item_id') or '').strip()
        quantity = int(data.get('quantity') or 1)
        price_coins = int(data.get('price_coins') or 0)
        from backend.services.shop_auction_service import AuctionError, create_listing
        try:
            listing = create_listing(user_id, item_id, quantity, price_coins)
        except AuctionError as ex:
            return jsonify({'success': False, 'error': str(ex)}), 400
        return jsonify({'success': True, 'listing': listing}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/api/shop/auction/buy', methods=['POST'])
def shop_auction_buy_listing():
    """Buy a fixed-price auction listing with coins."""
    try:
        data = request.get_json() or {}
        buyer_id = data.get('user_id') or data.get('buyer_id') or _resolve_user_id()
        listing_id = (data.get('listing_id') or '').strip()
        payment_method = (data.get('payment_method') or 'coins').strip().lower()
        from backend.services.shop_auction_service import AuctionError, buy_listing
        try:
            result = buy_listing(buyer_id, listing_id, payment_method=payment_method)
        except AuctionError as ex:
            return jsonify({'success': False, 'error': str(ex)}), 400
        return jsonify({'success': True, **result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/api/shop/auction/bid', methods=['POST'])
def shop_auction_place_bid():
    """Place a seller-accepted coin bid on an active auction listing."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id') or _resolve_user_id()
        listing_id = (data.get('listing_id') or '').strip()
        bid_coins = int(data.get('bid_coins') or 0)
        from backend.services.shop_auction_service import AuctionError, place_bid
        try:
            result = place_bid(user_id, listing_id, bid_coins)
        except AuctionError as ex:
            return jsonify({'success': False, 'error': str(ex)}), 400
        return jsonify({'success': True, **result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/api/shop/auction/accept-bid', methods=['POST'])
def shop_auction_accept_bid():
    """Seller accepts a bid; buyer pays coins and the item transfers."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id') or _resolve_user_id()
        listing_id = (data.get('listing_id') or '').strip()
        bid_id = (data.get('bid_id') or '').strip()
        from backend.services.shop_auction_service import AuctionError, accept_bid
        try:
            result = accept_bid(user_id, listing_id, bid_id)
        except AuctionError as ex:
            return jsonify({'success': False, 'error': str(ex)}), 400
        return jsonify({'success': True, **result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/api/shop/auction/price-history', methods=['GET'])
def shop_auction_price_history():
    """Recent completed sale prices, optionally scoped to one item."""
    try:
        item_id = (request.args.get('item_id') or '').strip() or None
        limit = min(int(request.args.get('limit', 20)), 100)
        from backend.services.shop_auction_service import price_history
        rows = price_history(item_id=item_id, limit=limit)
        return jsonify({'success': True, 'item_id': item_id, 'history': rows}), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'item_id': (request.args.get('item_id') or '').strip() or None,
            'history': [],
            'warning': 'Auction price history is temporarily unavailable',
            'error': str(e),
        }), 200


@shop_bp.route('/api/shop/auction/cancel', methods=['POST'])
def shop_auction_cancel_listing():
    """Cancel an active listing and restore the reserved item to seller inventory."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id') or _resolve_user_id()
        listing_id = (data.get('listing_id') or '').strip()
        from backend.services.shop_auction_service import AuctionError, cancel_listing
        try:
            listing = cancel_listing(user_id, listing_id)
        except AuctionError as ex:
            return jsonify({'success': False, 'error': str(ex)}), 400
        return jsonify({'success': True, 'listing': listing}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/api/shop/inventory/super-stack', methods=['POST'])
def super_stack_inventory():
    """One-click super stack inventory bundle for a user."""
    try:
        user_id = request.args.get('user_id') or _resolve_user_id()
        entries = _super_stack_bundle_entries()

        try:
            from backend.services.shop_db_service import add_to_inventory, shop_tables_exist

            if not shop_tables_exist():
                return jsonify({
                    'success': True,
                    'user_id': user_id,
                    'stacked': False,
                    'warning': 'Shop inventory tables not available yet; bundle prepared only.',
                    'bundle_entries': entries,
                }), 200

            added = 0
            for entry in entries:
                ok = add_to_inventory(
                    user_id=user_id,
                    item_id=entry['item_id'],
                    item_name=entry['item_name'],
                    quantity=int(entry.get('quantity', 1)),
                    purchase_id=None,
                )
                if ok:
                    added += 1

            return jsonify({
                'success': True,
                'user_id': user_id,
                'stacked': True,
                'bundle_size': len(entries),
                'entries_added': added,
                'bundle_entries': entries,
                'message': 'Super stack inventory applied.',
            }), 200
        except Exception:
            return jsonify({
                'success': True,
                'user_id': user_id,
                'stacked': False,
                'warning': 'Inventory service unavailable; bundle prepared only.',
                'bundle_entries': entries,
            }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------- Phase 5: Analytics ----------

@shop_bp.route('/api/shop/analytics', methods=['GET'])
def shop_analytics():
    """Aggregate analytics: popular items, revenue by item/category, refund stats. Optional user_id for that user's spending."""
    try:
        user_id = request.args.get('user_id')
        limit = min(int(request.args.get('limit', 10)), 50)
        days = request.args.get('days', type=int)
        from backend.services.shop_db_service import (
            get_analytics_popular_items,
            get_analytics_revenue_by_item,
            get_analytics_revenue_by_category,
            get_analytics_user_spending,
            get_analytics_refund_stats,
        )
        payload = {
            'success': True,
            'popular_items': get_analytics_popular_items(limit=limit),
            'revenue_by_item': get_analytics_revenue_by_item(),
            'revenue_by_category': get_analytics_revenue_by_category(days=days),
            'refund_stats': get_analytics_refund_stats(),
        }
        if user_id:
            payload['user_spending'] = get_analytics_user_spending(user_id)
        return jsonify(payload), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/api/shop/paypal/control-panel', methods=['GET'])
def shop_paypal_control_panel():
    """PayPal conversion control panel payload for profile/debugger cards."""
    try:
        user_id = request.args.get('user_id') or _resolve_user_id()
        best_agent = {}
        top_agent_offers = []
        booster_cards = []
        owned_offer_item_ids = []
        conversion = {
            'paypal_orders': 0,
            'paypal_completed': 0,
            'paypal_revenue_usd': 0.0,
            'paypal_capture_rate_percent': 0.0,
        }
        next_actions = []

        # Best agent selection from skillsets.
        try:
            from backend.services.agent_skillset import agent_skillset
            agents = agent_skillset.get_all_skillsets().get('agents', {})
            ranked = []
            for agent_id, data in agents.items():
                paypal_power = int(data.get('paypal_skill_power_total', 0))
                sales_power = int(data.get('sales_skill_power_total', 0))
                top25_power = int(data.get('top25_upgrade_power_total', 0))
                level = int(data.get('level', 1))
                score = (paypal_power * 1.2) + (sales_power * 0.6) + (top25_power * 0.35) + (level * 20)
                ranked.append((score, agent_id, data))
            ranked.sort(key=lambda x: x[0], reverse=True)
            if ranked:
                _, best_id, best_data = ranked[0]
                best_agent = {
                    'agent_id': best_id,
                    'name': best_data.get('name', best_id),
                    'level': int(best_data.get('level', 1)),
                    'paypal_skill_power_total': int(best_data.get('paypal_skill_power_total', 0)),
                    'sales_skill_power_total': int(best_data.get('sales_skill_power_total', 0)),
                }
                paypal_profiles = best_data.get('paypal_skill_profiles', []) or []
                weakest = sorted(
                    paypal_profiles,
                    key=lambda x: int(x.get('paypal_power', 0))
                )[:5]
                next_actions = [
                    f"Improve {p.get('domain', 'paypal_conversion')} flow and run A/B test"
                    for p in weakest
                ]

            for score, agent_id, data in ranked[:5]:
                level = int(data.get('level', 1))
                paypal_power = int(data.get('paypal_skill_power_total', 0))
                top25_power = int(data.get('top25_upgrade_power_total', 0))
                paypal_price_usd = max(19.99, round((score / 180.0) + (level * 1.75), 2))
                item_id = f"agent-offer-{agent_id}"
                item_name = f"Agent License: {data.get('name', agent_id)}"
                top_agent_offers.append({
                    'agent_id': agent_id,
                    'name': data.get('name', agent_id),
                    'item_id': item_id,
                    'item_name': item_name,
                    'level': level,
                    'paypal_skill_power_total': paypal_power,
                    'top25_upgrade_power_total': top25_power,
                    'paypal_price_usd': paypal_price_usd,
                })
        except Exception:
            pass

        # Conversion metrics from purchases when DB exists.
        try:
            from backend.services.shop_db_service import get_purchases
            purchases = get_purchases(user_id, limit=500) or []
            paypal_rows = [p for p in purchases if (p.get('price_type') or '').lower() == 'paypal']
            completed = [p for p in paypal_rows if (p.get('purchase_status') or '').lower() in ('completed', 'captured')]
            conversion['paypal_orders'] = len(paypal_rows)
            conversion['paypal_completed'] = len(completed)
            # price_paid_coins is not used for paypal; keep revenue as best-effort from recorded fields.
            revenue = 0.0
            for row in completed:
                try:
                    revenue += float(row.get('price_paid_coins') or 0)
                except Exception:
                    pass
            conversion['paypal_revenue_usd'] = round(revenue, 2)
            orders = conversion['paypal_orders']
            conversion['paypal_capture_rate_percent'] = round((conversion['paypal_completed'] / orders * 100.0), 2) if orders else 0.0
        except Exception:
            pass

        # Owned item IDs from inventory (for "Purchased" badges in UI).
        try:
            from backend.services.shop_db_service import get_inventory
            inv = get_inventory(user_id) or []
            owned_offer_item_ids = [
                str(i.get('item_id'))
                for i in inv
                if str(i.get('item_id', '')).startswith('agent-offer-') or str(i.get('item_id', '')).startswith('booster-paypal-')
            ]
        except Exception:
            owned_offer_item_ids = []

        # Booster cards with stable PayPal pricing.
        booster_cards = [
            {
                'item_id': 'booster-paypal-checkout-speed',
                'name': 'Booster: Checkout Speed',
                'description': 'Reduce checkout friction and drop-off',
                'paypal_price_usd': 9.99,
                'boost_value': '+8% checkout completion',
            },
            {
                'item_id': 'booster-paypal-conversion-copy',
                'name': 'Booster: Conversion Copy',
                'description': 'Improve offer copy and CTA performance',
                'paypal_price_usd': 12.99,
                'boost_value': '+10% click-to-checkout',
            },
            {
                'item_id': 'booster-paypal-cart-recovery',
                'name': 'Booster: Cart Recovery',
                'description': 'Recover abandoned carts faster',
                'paypal_price_usd': 11.99,
                'boost_value': '+9% cart recovery',
            },
            {
                'item_id': 'booster-paypal-order-value-lift',
                'name': 'Booster: Order Value Lift',
                'description': 'Increase AOV through bundle logic',
                'paypal_price_usd': 14.99,
                'boost_value': '+12% order value',
            },
            {
                'item_id': 'booster-paypal-retention-loop',
                'name': 'Booster: Retention Loop',
                'description': 'Boost repeat purchases and loyalty',
                'paypal_price_usd': 13.99,
                'boost_value': '+11% repeat purchase rate',
            },
        ]

        if not next_actions:
            next_actions = [
                'Run PayPal checkout copy test on top 3 products',
                'Prioritize coin pack upsell after first capture',
                'Reduce checkout friction on mobile payment step',
                'Trigger post-purchase cross-sell in 10 minutes',
                'Review PayPal capture failures and fix top cause',
            ]

        return jsonify({
            'success': True,
            'user_id': user_id,
            'best_agent': best_agent,
            'top_agent_offers': top_agent_offers,
            'booster_cards': booster_cards,
            'owned_offer_item_ids': owned_offer_item_ids,
            'conversion': conversion,
            'next_5_actions': next_actions[:5],
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# AI-Powered Shop Recommendations
# ---------------------------------------------------------------------------

@shop_bp.route('/api/shop/recommendations', methods=['GET', 'POST'])
def shop_ai_recommendations():
    """
    Groq-powered personalised shop recommendations.

    GET  ?user_id=X&budget=500&focus=xp|cosmetic|tech|value
    POST {"user_id": "X", "budget": 500, "focus": "value"}

    Returns top 5 recommended items with AI reasoning.
    """
    try:
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
        else:
            data = request.args.to_dict()

        user_id = (data.get('user_id') or _resolve_user_id() or 'default_user').strip()
        budget  = int(data.get('budget', 500))
        focus   = (data.get('focus') or 'value').strip()

        xp = level = 0
        systems = {}
        try:
            from backend.services.unified_points_database import unified_points_db
            snap = unified_points_db.get_all_points(user_id)
            if snap and snap.get('success'):
                xp      = int(snap.get('xp_total', 0))
                level   = int(snap.get('level', 1))
                systems = snap.get('systems', {})
        except Exception:
            pass

        owned_ids = set()
        try:
            from backend.services.shop_db_service import get_inventory
            inv = get_inventory(user_id) or []
            owned_ids = {str(i.get('item_id')) for i in inv}
        except Exception:
            pass

        all_items = _get_shop_items()[:30]
        available = [
            {'id': i.get('id'), 'name': i.get('name'), 'category': i.get('category'),
             'price': i.get('price'), 'rarity': i.get('rarity', 'common'),
             'description': i.get('description', '')}
            for i in all_items
            if str(i.get('id')) not in owned_ids
        ][:20]

        focus_map = {
            'xp':       'items that boost XP gain and progression speed',
            'cosmetic': 'visual/cosmetic items and themes',
            'tech':     'technology and automation upgrades',
            'value':    'best value-for-coins ratio',
        }
        focus_desc = focus_map.get(focus, 'overall best value and usefulness')

        from backend.services.llm_service import chat
        resp = chat(
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are the AI shop advisor for MasterNoder.dk. '
                        'Recommend exactly 5 shop items. '
                        'Return ONLY valid JSON: {"recommendations": [{"item_id": str, "name": str, '
                        '"reason": str (max 12 words), "priority": "must-have|great|nice-to-have"}]}'
                    ),
                },
                {
                    'role': 'user',
                    'content': (
                        f'User: level {level}, {xp} XP, budget {budget} coins. '
                        f'Focus: {focus_desc}.\n'
                        f'Available items:\n'
                        + '\n'.join(
                            f"- {i['id']}: {i['name']} ({i['category']}, price={i['price']}) — {i['description']}"
                            for i in available[:15]
                        )
                    ),
                },
            ],
            task_type='speed',
            max_tokens=500,
            temperature=0.7,
        )

        recs = []
        if resp.success:
            import json as _json
            raw = resp.content.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
            try:
                parsed = _json.loads(raw)
                recs   = parsed.get('recommendations', [])
            except Exception:
                pass

        item_map = {str(i.get('id')): i for i in all_items}
        for r in recs:
            full = item_map.get(r.get('item_id'), {})
            r['price']       = full.get('price', 0)
            r['category']    = full.get('category', '')
            r['rarity']      = full.get('rarity', 'common')
            r['description'] = full.get('description', '')

        if not recs:
            recs = [
                {'item_id': i.get('id'), 'name': i.get('name'), 'reason': 'Great value for new players',
                 'priority': 'great', 'price': i.get('price'), 'category': i.get('category')}
                for i in available[:5]
            ]

        return jsonify({
            'success':         True,
            'user_id':         user_id,
            'level':           level,
            'xp':              xp,
            'budget':          budget,
            'focus':           focus,
            'recommendations': recs[:5],
            'provider':        resp.provider if resp.success else 'fallback',
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@shop_bp.route('/api/shop/daily-deal', methods=['GET'])
def shop_daily_deal():
    """AI-curated daily deal — changes each day, 25-40% discount with AI copy."""
    try:
        from datetime import datetime, timezone
        import hashlib
        today    = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        day_hash = int(hashlib.md5(today.encode()).hexdigest()[:6], 16)
        items    = _get_shop_items()
        if not items:
            return jsonify({'success': False, 'error': 'No items available'}), 200

        item           = items[day_hash % len(items)]
        original_price = item.get('price', 100)
        discount_pct   = 25 + (day_hash % 16)
        deal_price = (
            max(10, int(original_price * (1 - discount_pct / 100)))
            if isinstance(original_price, (int, float)) else original_price
        )

        deal_copy = ''
        try:
            from backend.services.llm_service import chat
            resp = chat(
                messages=[{'role': 'user', 'content':
                    f"Write an exciting 12-word deal message for: '{item.get('name')}'. "
                    f"{discount_pct}% off today only. Be urgent."}],
                task_type='speed', max_tokens=40, temperature=0.8,
            )
            if resp.success:
                deal_copy = resp.content.strip().strip('"')
        except Exception:
            pass

        return jsonify({
            'success': True, 'date': today,
            'deal': {
                'item_id': item.get('id'), 'name': item.get('name'),
                'category': item.get('category'),
                'original_price': original_price, 'deal_price': deal_price,
                'discount_pct': discount_pct,
                'copy': deal_copy or f"{discount_pct}% off today only!",
                'expires': today + 'T23:59:59Z',
            },
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
