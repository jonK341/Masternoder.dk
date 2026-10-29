"""
Shop Routes
API endpoints for shop functionality including currency and items.
Uses account resolution: session > request > user_identification.
"""
from flask import Blueprint, jsonify, request, send_file
import os
from typing import Any, Dict

from backend.services.shop_catalog_seed import build_seed_shop_items as _seed_shop_items

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
        booster_skus = _booster_sku_map()
        if item_id in booster_skus:
            _apply_booster_sku(unified_points_db, user_id, item_id, booster_skus[item_id], quantity)
            return
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

        packs = get_coin_packs_with_payment_rails(include_overage=False)
        if packs:
            return packs
    except Exception:
        pass
    return list(_PAYPAL_COIN_PACKS_LEGACY)


def get_coin_pack_map():
    try:
        from backend.services.monetization_config_service import get_coin_packs_with_payment_rails

        packs = get_coin_packs_with_payment_rails(include_overage=True)
        if packs:
            return {p["id"]: p for p in packs if p.get("id")}
    except Exception:
        pass
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
    try:
        from backend.services.nft_exchange_service import paypal_item_map

        result.update(paypal_item_map())
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
            "tags": ["digital_good", good.get("delivery") or "download", f"line_{str(good.get('line') or 'x').lower()}"]
            + list(good.get("tags_extra") or []),
            "payment_rails": good.get("payment_rails") or ["credits"],
            "delivery": good.get("delivery") or "download",
            "license": good.get("license") or "",
            "coins_granted": int(good.get("coins_granted") or 0),
        }
        if row.get("checkout_url"):
            row["checkout_url"] = good.get("checkout_url")
        if row["id"]:
            items.append(row)
    return items


def _mn2_services_shop_items():
    """MN2 platform services (masternode hosting, on-ramp, explorer deep links)."""
    try:
        from backend.services.monetization_config_service import get_mn2_services

        services = get_mn2_services()
    except Exception:
        services = []
    hosting_price = None
    try:
        import json
        import os

        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cfg_path = os.path.join(base, "data", "mn2_masternode_config.json")
        if os.path.isfile(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                mcfg = json.load(f)
            paypal = mcfg.get("paypal") if isinstance(mcfg.get("paypal"), dict) else {}
            if paypal.get("price_usd_per_slot") is not None:
                hosting_price = float(paypal.get("price_usd_per_slot"))
    except Exception:
        hosting_price = None
    items = []
    for svc in services:
        price_coins = int(svc.get("price_coins") or 0)
        price_usd = float(svc.get("price_usd") or 0)
        if svc.get("service_id") == "masternode_hosting" and hosting_price is not None:
            price_usd = hosting_price
        delivery = (svc.get("delivery") or "external_link").lower()
        row = {
            "id": svc.get("id"),
            "name": svc.get("name") or svc.get("id"),
            "description": svc.get("description") or "",
            "category": "mn2_services",
            "price": price_coins,
            "price_usd": price_usd,
            "icon": svc.get("icon") or "🪙",
            "rarity": "legendary" if delivery == "external_checkout" else "epic",
            "tags": ["mn2_service", delivery, f"line_{str(svc.get('line') or 'h').lower()}", svc.get("service_id") or ""],
            "payment_rails": svc.get("payment_rails") or [],
            "delivery": delivery,
            "checkout_url": svc.get("checkout_url") or "",
            "service_id": svc.get("service_id") or "",
            "billing_label": svc.get("billing_label") or "",
            "checkout_mode": svc.get("checkout_mode") or "",
            "max_slots_per_order": int(svc.get("max_slots_per_order") or 0) or None,
        }
        if row["id"]:
            items.append(row)
    return items


def _booster_sku_catalog_items():
    """Standalone catalog rows for configured booster SKUs (e.g. staking surges) not already seeded."""
    items = []
    for sku_id, sku in _booster_sku_map().items():
        price_coins = int(sku.get("price_coins") or 0)
        if price_coins <= 0:
            continue
        row = {
            "id": sku_id,
            "name": sku.get("name") or sku_id,
            "description": sku.get("description") or f"Active for {int(sku.get('duration_minutes') or 60)} minutes after purchase.",
            "category": sku.get("category") or "boosts",
            "price": price_coins,
            "price_usd": float(sku.get("price_usd") or 0),
            "icon": "⚡" if sku.get("effect") == "staking_boost" else "🚀",
            "rarity": "epic" if sku.get("effect") == "staking_boost" else "rare",
            "tags": ["booster_sku", sku.get("effect") or "booster"],
            "payment_rails": ["paypal", "mn2", "credits"],
            "delivery": "booster_sku",
            "boost_multiplier": sku.get("boost_multiplier"),
        }
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
    allowed_roots = [
        os.path.realpath(os.path.join(root, "content", "digital_goods")),
    ]
    for allowed_root in allowed_roots:
        if path == allowed_root or path.startswith(allowed_root + os.sep):
            return path
    return ""


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
            get_public_mn2_services,
        )

        monetization_shop = {
            "payment_rails_catalog": get_payment_rails_catalog(),
            "digital_goods": get_public_digital_goods(),
            "content_bundles": get_public_content_bundles(),
            "mn2_services": get_public_mn2_services(),
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
    nft_editions = []
    try:
        from backend.services import nft_exchange_service as nft

        nft_editions = nft.catalog().get("skus") or []
    except Exception:
        pass
    return jsonify({
        'success': True,
        'paypal_items': items,
        'nft_editions': nft_editions,
    }), 200


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

        ext = os.path.splitext(path)[1].lower()
        mime = "application/zip" if ext == ".zip" else "text/markdown"
        return send_file(
            path,
            as_attachment=True,
            download_name=good.get("download_filename") or os.path.basename(path),
            mimetype=mime,
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
    for svc_item in _mn2_services_shop_items():
        if svc_item.get("id") not in existing_ids:
            items.append(svc_item)
            existing_ids.add(svc_item.get("id"))
    for booster_item in _booster_sku_catalog_items():
        if booster_item.get("id") not in existing_ids:
            items.append(booster_item)
            existing_ids.add(booster_item.get("id"))
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
        if item.get("delivery") in ("external_checkout", "external_link", "free_info"):
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


@shop_bp.route('/api/shop/discord/promo/redeem', methods=['POST'])
@shop_bp.route('/vidgenerator/api/shop/discord/promo/redeem', methods=['POST'])
def shop_discord_promo_redeem():
    """Redeem M8 #52 shop-wide Discord promo code."""
    data = request.get_json(silent=True) or {}
    user_id = (data.get("user_id") or request.args.get("user_id") or _resolve_user_id()).strip()
    code = (data.get("code") or data.get("promo_code") or "").strip()
    from backend.services.shop_discord_promo_service import redeem
    result = redeem(user_id, code)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


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

        delivery = (item.get("delivery") or "").lower()
        if delivery in ("external_checkout", "external_link", "free_info"):
            checkout_url = item.get("checkout_url") or "/shop"
            return jsonify({
                'success': False,
                'error': 'This item uses external checkout — open the linked page to continue.',
                'checkout_url': checkout_url,
                'delivery': delivery,
            }), 400
        
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


def _merge_mn2_service_purchases(user_id: str, purchases: list, limit: int = 50) -> list:
    """Append masternode hosting PayPal orders to shop purchase history."""
    try:
        from backend.services.mn2_masternode_hosting_service import list_user_orders

        existing = {str(p.get("order_id") or "") for p in purchases if p.get("source") == "mn2_masternode_hosting"}
        for order in list_user_orders(user_id, limit=limit):
            oid = str(order.get("order_id") or "")
            if not oid or oid in existing:
                continue
            slots = int(order.get("slots") or 1)
            status = str(order.get("status") or "")
            method = str(order.get("payment_method") or "paypal")
            price_type = {
                "paypal": "paypal_mn2_hosting",
                "credits": "coins",
                "mn2": "mn2",
                "mn2_onchain": "mn2_onchain",
            }.get(method, "paypal_mn2_hosting")
            price_points: Dict[str, Any] = {}
            if method == "credits":
                price_points = {"coins": int(order.get("coins_total") or 0)}
            elif method == "mn2":
                price_points = {"mn2": float(order.get("mn2_total") or 0)}
            elif method == "mn2_onchain":
                price_points = {"mn2": float(order.get("mn2_paid_onchain") or order.get("mn2_total") or 0)}
            else:
                price_points = {"usd": order.get("usd_total")}
            purchases.append({
                "id": f"mn-host-{oid}",
                "item_id": "svc-mn2-masternode-hosting",
                "item_name": f"Masternode Hosting × {slots}",
                "quantity": slots,
                "price_type": price_type,
                "price_paid_coins": int(order.get("coins_total") or 0) if method == "credits" else 0,
                "price_paid_points": price_points,
                "purchase_status": status,
                "created_at": order.get("paid_at") or order.get("created_at"),
                "source": "mn2_masternode_hosting",
                "order_id": oid,
                "host_ids": order.get("host_ids") or [],
                "payment_method": method,
            })
            existing.add(oid)
    except Exception:
        pass
    purchases.sort(key=lambda p: str(p.get("created_at") or ""), reverse=True)
    return purchases[:limit]


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
        purchases = _merge_mn2_service_purchases(user_id, list(purchases or []), limit=limit)
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
        dg_by_id = {g.get("id"): g for g in _digital_goods_config()}
        enriched = []
        for row in inventory or []:
            ent = dict(row)
            iid = ent.get("item_id")
            good = dg_by_id.get(iid) if iid else None
            if good and good.get("delivery") in ("download", "free_info", "inventory"):
                path = _artifact_abs_path(good)
                if path and os.path.isfile(path):
                    ent["download_url"] = f"/api/shop/digital-goods/{iid}/download?user_id={user_id}"
                    ent["digital_good"] = True
            enriched.append(ent)
        return jsonify({'success': True, 'user_id': user_id, 'inventory': enriched}), 200
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
