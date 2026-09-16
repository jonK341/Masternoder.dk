"""Block-height trophy drops — listener, manifest, claim path (plan 001 BM-U1–BM-U5)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MANIFEST_PATH = os.path.join(_BASE, "data", "block_mint_manifest.json")
_CONFIG_PATH = os.path.join(_BASE, "data", "block_mint_config.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with _LOCK:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        return True
    except Exception:
        return False


def get_config() -> Dict[str, Any]:
    return _read_json(
        _CONFIG_PATH,
        {
            "enabled": True,
            "lookback_blocks": 30,
            "one_per_block": True,
            "base_price_usd": 2.99,
            "floor_price_usd": 0.99,
            "claim_methods": ["mn2", "paypal"],
            "explorer_base_url": "/explorer?height=",
        },
    )


def _current_block_height() -> Optional[int]:
    try:
        from backend.services.mn2_rpc_client import getblockcount

        r = getblockcount(timeout_sec=4)
        if r.get("result") is not None:
            return int(r["result"])
    except Exception:
        pass
    try:
        from backend.services.mn2_chainz import chainz_getblockcount

        ch = chainz_getblockcount()
        if ch is not None:
            return int(ch)
    except Exception:
        pass
    return None


def block_item_id(height: int) -> str:
    return f"block-{int(height)}"


def _media_for_height(height: int, *, ensure_lazy: bool = False) -> Dict[str, str]:
    h = int(height)
    if ensure_lazy and get_config().get("lazy_media_generation", True):
        try:
            from backend.services.block_trophy_media_service import block_media_exists, ensure_block_media

            if not block_media_exists(h):
                ensure_block_media(h, force=False)
        except Exception:
            pass

    iid = block_item_id(h)
    media = _read_json(os.path.join(_BASE, "data", "shop_item_media.json"), {})
    row = media.get(iid) or {}
    return {
        "image_url": row.get("image_url") or row.get("poster_url") or f"/static/img/trophies/block-{h}.png",
        "gif_url": row.get("gif_url") or row.get("clip_url") or f"/static/img/trophies/block-{h}.gif",
    }


def _battle_stats_preview(height: int) -> Dict[str, Any]:
    try:
        from backend.services.block_trophy_battle_service import generate_battle_stats

        preview_key = f"TRO-{block_item_id(height)}-preview"
        return generate_battle_stats(height, preview_key, edition_no=1)
    except Exception:
        return {}


def _catalog_row(
    height: int,
    manifest_row: Optional[Dict[str, Any]] = None,
    *,
    ensure_lazy_media: bool = False,
) -> Dict[str, Any]:
    cfg = get_config()
    iid = block_item_id(height)
    media = _media_for_height(height, ensure_lazy=ensure_lazy_media)
    manifest_row = manifest_row or {}
    claimed = bool(manifest_row.get("claimed_by"))
    stats = manifest_row.get("battle_stats") or _battle_stats_preview(height)
    serial = stats.get("serial_number") or f"BLK-{int(height):07d}-E0001"
    lic = manifest_row.get("license_number") or ""
    row = {
        "id": iid,
        "name": f"Block Smiley Trophy #{height}",
        "kind": "trophy",
        "series": "block_mint",
        "tags": ["block_mint", "trophy", "block_trophy", "battle", "tradable"],
        "category": "trophies",
        "block_height": height,
        "supply": 1,
        "max_supply": 1,
        "one_per_block": True,
        "claimed": claimed,
        "claimed_by": manifest_row.get("claimed_by"),
        "base_price_usd": float(cfg.get("base_price_usd") or 2.99),
        "floor_price_usd": float(cfg.get("floor_price_usd") or 0.99),
        "price": max(99, int(float(cfg.get("base_price_usd") or 2.99) * 100)),
        "on_chain_mint": False,
        "platform_trophy": True,
        "ai_generated": True,
        "serial_number": serial,
        "serial_key": serial,
        "license_number": lic,
        "battle_stats": stats,
        "description": (
            f"One unique AI smiley trophy per MN2 block #{height}. "
            f"License {lic or 'pending'} · Serial {serial} · tradable on auction & peer transfer."
        ),
        "explorer_url": f"{cfg.get('explorer_base_url', '/explorer?height=')}{height}",
        "image_url": media.get("image_url"),
        "gif_url": media.get("gif_url"),
        "shop_url": f"/shop?tab=block-gallery&highlight={iid}",
    }
    try:
        from backend.services.block_trophy_registry_service import enrich_catalog_row

        return enrich_catalog_row(row, manifest_row)
    except Exception:
        return row


def sync_block_height() -> Dict[str, Any]:
    """Poll chain tip and append unseen block heights to manifest (BM-U1)."""
    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": True, "synced": False, "reason": "disabled"}

    height = _current_block_height()
    if height is None:
        return {"success": False, "error": "block_height_unavailable"}

    lookback = max(1, int(cfg.get("lookback_blocks") or 5))
    milestone = int(cfg.get("milestone_block") or 0)
    genesis = max(1, int(cfg.get("genesis_block") or 1))
    doc = _read_json(_MANIFEST_PATH, {"drops": {}, "last_height": 0})
    drops = doc.setdefault("drops", {})
    last = int(doc.get("last_height") or 0)

    genesis_mode = (
        milestone > 0
        and height >= milestone
        and cfg.get("backfill_from_genesis_at_milestone", True)
    )
    if genesis_mode and not doc.get("genesis_backfill_complete"):
        if not doc.get("genesis_backfill_started"):
            doc["genesis_backfill_started"] = True
            doc["genesis_backfill_cursor"] = genesis
            try:
                from backend.services.trophy_milestone_announcement_service import post_block_million_announcement

                if not cfg.get("milestone_discord_announced"):
                    post_block_million_announcement()
                    cfg_doc = _read_json(_CONFIG_PATH, {})
                    cfg_doc["milestone_discord_announced"] = True
                    _write_json(_CONFIG_PATH, cfg_doc)
            except Exception:
                pass
        batch = max(50, int(cfg.get("backfill_batch_size") or 500))
        cursor = int(doc.get("genesis_backfill_cursor") or genesis)
        start = cursor
        end = min(cursor + batch - 1, height)
    else:
        start = max(last, height - lookback + 1)
        end = height

    added: List[int] = []
    for h in range(start, end + 1):
        key = str(h)
        if key not in drops:
            entry = {
                "height": h,
                "item_id": block_item_id(h),
                "detected_at": _iso(),
                "claimed_by": None,
                "claimed_at": None,
            }
            try:
                from backend.services.block_trophy_registry_service import manifest_fields_for_block

                entry.update(manifest_fields_for_block(h))
            except Exception:
                pass
            drops[key] = entry
            added.append(h)
            if not cfg.get("lazy_media_generation", True):
                try:
                    from backend.services.block_trophy_media_service import ensure_block_media

                    ensure_block_media(h)
                except Exception:
                    pass
    if genesis_mode and not doc.get("genesis_backfill_complete"):
        doc["genesis_backfill_cursor"] = end + 1
        if end >= height:
            doc["genesis_backfill_complete"] = True
    doc["last_height"] = max(int(doc.get("last_height") or 0), height)
    doc["updated_at"] = _iso()
    _write_json(_MANIFEST_PATH, doc)
    return {
        "success": True,
        "block_height": height,
        "added": added,
        "total_drops": len(drops),
        "genesis_backfill": genesis_mode,
        "genesis_backfill_complete": bool(doc.get("genesis_backfill_complete")),
        "genesis_backfill_cursor": doc.get("genesis_backfill_cursor"),
    }


def get_genesis_backfill_status() -> Dict[str, Any]:
    cfg = get_config()
    doc = _read_json(_MANIFEST_PATH, {"drops": {}, "last_height": 0})
    drops = doc.get("drops") or {}
    total = len(drops)
    claimed = sum(1 for d in drops.values() if isinstance(d, dict) and d.get("claimed_by"))
    last_height = int(doc.get("last_height") or 0)
    genesis = int(cfg.get("genesis_block") or 1)
    cursor = int(doc.get("genesis_backfill_cursor") or genesis)
    milestone = int(cfg.get("milestone_block") or 0)
    chain_span = max(0, last_height - genesis + 1) if last_height >= genesis else 0
    genesis_index_percent = round(100.0 * total / chain_span, 2) if chain_span else 0.0
    if doc.get("genesis_backfill_complete"):
        genesis_index_percent = 100.0

    media_stats: Dict[str, Any] = {}
    try:
        from backend.services.block_trophy_media_service import count_block_media_stats

        heights = sorted(int(k) for k in drops.keys())
        media_stats = count_block_media_stats(heights)
    except Exception:
        media_stats = {
            "media_generated_count": 0,
            "media_pending_count": total,
            "media_total_drops": total,
            "media_percent_complete": 0.0,
        }

    return {
        "success": True,
        "milestone_block": milestone,
        "genesis_block": genesis,
        "lazy_media_generation": bool(cfg.get("lazy_media_generation", True)),
        "genesis_backfill_started": bool(doc.get("genesis_backfill_started")),
        "genesis_backfill_complete": bool(doc.get("genesis_backfill_complete")),
        "genesis_backfill_cursor": cursor,
        "genesis_index_percent": genesis_index_percent,
        "last_height": last_height,
        "total_drops": total,
        "claimed_drops": claimed,
        "unclaimed_drops": total - claimed,
        **media_stats,
    }


def get_block_drops(limit: int = 20) -> Dict[str, Any]:
    sync_block_height()
    doc = _read_json(_MANIFEST_PATH, {"drops": {}, "last_height": 0})
    drops_map = doc.get("drops") or {}
    rows: List[Dict[str, Any]] = []
    for key in sorted(drops_map.keys(), key=lambda x: int(x), reverse=True)[: max(1, min(limit, 100))]:
        manifest_row = drops_map[key]
        h = int(manifest_row.get("height") or key)
        row = _catalog_row(h, manifest_row)
        try:
            from backend.services.trophy_pricing_service import get_effective_price

            pricing = get_effective_price(row["id"])
            if pricing.get("success"):
                row["effective_price_usd"] = pricing.get("effective_price_usd")
                row["price_factors"] = pricing.get("price_factors") or {}
        except Exception:
            row["effective_price_usd"] = row["base_price_usd"]
        rows.append(row)
    return {
        "success": True,
        "block_height": doc.get("last_height"),
        "drops": rows,
        "series": "block_mint",
        "on_chain_mint": False,
    }


def block_mint_shop_items() -> List[Dict[str, Any]]:
    """Merge unclaimed manifest drops into shop catalog."""
    return [row for row in get_block_registry(limit=50).get("entries") or [] if not row.get("claimed")]


def get_block_registry(*, limit: int = 48, include_claimed: bool = True) -> Dict[str, Any]:
    """Full per-block trophy registry for shop gallery (one row per block)."""
    sync_block_height()
    doc = _read_json(_MANIFEST_PATH, {"drops": {}, "last_height": 0})
    drops_map = doc.get("drops") or {}
    entries: List[Dict[str, Any]] = []
    for key in sorted(drops_map.keys(), key=lambda x: int(x), reverse=True):
        manifest_row = drops_map[key]
        if manifest_row.get("claimed_by") and not include_claimed:
            continue
        h = int(manifest_row.get("height") or key)
        if not manifest_row.get("license_number"):
            try:
                from backend.services.block_trophy_registry_service import manifest_fields_for_block

                manifest_row = {**manifest_row, **manifest_fields_for_block(h)}
                drops_map[key] = manifest_row
            except Exception:
                pass
        entries.append(_catalog_row(h, manifest_row, ensure_lazy_media=False))
        if len(entries) >= max(1, min(limit, 200)):
            break

    lazy_cfg = get_config().get("lazy_media_generation", True)
    if lazy_cfg and entries:
        try:
            from backend.services.block_trophy_media_service import lazy_ensure_block_media_for_gallery

            heights = [int(e.get("block_height") or 0) for e in entries if e.get("block_height")]
            lazy_ensure_block_media_for_gallery(heights, max_generate=min(12, len(heights)))
            for idx, entry in enumerate(entries):
                h = int(entry.get("block_height") or 0)
                if h:
                    entries[idx] = _catalog_row(
                        h,
                        drops_map.get(str(h)) if isinstance(drops_map.get(str(h)), dict) else None,
                        ensure_lazy_media=True,
                    )
        except Exception:
            pass

    if drops_map != doc.get("drops"):
        doc["drops"] = drops_map
        doc["updated_at"] = _iso()
        _write_json(_MANIFEST_PATH, doc)

    available = sum(1 for e in entries if not e.get("claimed"))
    return {
        "success": True,
        "block_height": doc.get("last_height"),
        "one_per_block": True,
        "count": len(entries),
        "available_count": available,
        "claimed_count": len(entries) - available,
        "entries": entries,
        "series": "block_mint",
        "on_chain_mint": False,
    }


def claim_block_trophy_staking_reward(
    user_id: str,
    height: int,
    *,
    interval_id: str = "",
    reward_mn2: float = 0.0,
) -> Dict[str, Any]:
    """Grant block trophy to staking interval winner — no payment (wallet v2 reward)."""
    uid = (user_id or "").strip()
    if not uid or uid in ("default_user", "guest"):
        return {"success": False, "error": "guest_blocked"}

    h = int(height)
    iid = block_item_id(h)
    doc = _read_json(_MANIFEST_PATH, {"drops": {}})
    drops = doc.setdefault("drops", {})
    key = str(h)
    if key not in drops:
        sync_block_height()
        doc = _read_json(_MANIFEST_PATH, {"drops": {}})
        drops = doc.get("drops") or {}
        if key not in drops:
            return {"success": False, "error": "block_not_in_manifest", "height": h}

    row = drops[key]
    if row.get("claimed_by"):
        return {
            "success": False,
            "error": "already_claimed",
            "claimed_by": row.get("claimed_by"),
            "height": h,
        }

    catalog = _catalog_row(h, row)
    from backend.services.trophy_fulfillment_service import grant_platform_edition, patch_edition_fields

    grant = grant_platform_edition(
        uid,
        iid,
        catalog["name"],
        acquired_via="staking_winner",
        price_type="staking_reward",
        extra={
            "block_height": h,
            "platform_trophy": True,
            "ai_generated": True,
            "staking_interval_id": interval_id,
            "staking_reward_mn2": reward_mn2,
        },
    )
    if not grant.get("success"):
        return grant

    edition_no = grant.get("edition_no")
    edition_key = grant.get("edition_key")
    proof_hash = grant.get("proof_hash")
    edition = grant.get("edition") or {}

    battle_stats: Dict[str, Any] = {}
    lic = row.get("license_number") or catalog.get("license_number")
    trading: Optional[Dict[str, Any]] = None
    try:
        from backend.services.block_trophy_battle_service import generate_battle_stats
        from backend.services.block_trophy_registry_service import build_trading_profile

        battle_stats = generate_battle_stats(
            h,
            edition_key or f"TRO-{iid}-{edition_no}",
            edition_no=int(edition_no or 1),
        )
        trading = build_trading_profile(
            h,
            stats=battle_stats,
            claimed=True,
            claimed_by=uid,
            edition_key=edition_key,
            edition_no=int(edition_no or 1),
            proof_hash=proof_hash,
        )
        if lic:
            trading["license_number"] = lic
        patch_edition_fields(
            uid,
            iid,
            int(edition_no or 1),
            {
                "battle_stats": battle_stats,
                "serial_number": battle_stats.get("serial_number"),
                "license_number": lic or trading.get("license_number"),
                "trading_profile": trading,
                "block_height": h,
                "platform_trophy": True,
                "one_per_block": True,
                "acquired_via": "staking_winner",
            },
        )
        edition = {
            **edition,
            "battle_stats": battle_stats,
            "license_number": lic,
            "trading_profile": trading,
        }
    except Exception:
        pass

    row["claimed_by"] = uid
    row["claimed_at"] = _iso()
    row["edition_no"] = edition_no
    row["edition_key"] = edition_key
    row["proof_hash"] = proof_hash
    row["claimed_via"] = "staking_winner"
    if trading:
        row["trading_profile"] = trading
    drops[key] = row
    doc["updated_at"] = _iso()
    _write_json(_MANIFEST_PATH, doc)

    try:
        from backend.services.mn2_ledger import append_entry

        append_entry(
            uid,
            "staking_trophy_grant",
            0.0,
            txid=f"staking-trophy:{interval_id}:{h}",
            metadata={
                "item_id": iid,
                "block_height": h,
                "edition_key": edition_key,
                "interval_id": interval_id,
                "reward_mn2": reward_mn2,
            },
        )
    except Exception:
        pass

    enrichment: Dict[str, Any] = {}
    try:
        from backend.services.trophy_grant_enrichment_service import enrich_block_trophy_grant

        enrichment = enrich_block_trophy_grant(
            uid,
            iid,
            int(edition_no or 1),
            edition_key or "",
            proof_hash or "",
            h,
            acquired_via="staking_winner",
            battle_stats=battle_stats,
            license_number=lic or "",
            trading_profile=trading,
            interval_id=interval_id,
            reward_mn2=reward_mn2,
        )
        if enrichment.get("gif_url"):
            edition = {**edition, "gif_url": enrichment["gif_url"], "image_url": enrichment.get("image_url")}
    except Exception:
        pass

    return {
        "success": True,
        "height": h,
        "item_id": iid,
        "edition_no": edition_no,
        "edition_key": edition_key,
        "edition": edition,
        "battle_stats": enrichment.get("battle_stats") or battle_stats,
        "license_number": lic,
        "trading_profile": trading,
        "acquired_via": "staking_winner",
        "explorer_url": catalog.get("explorer_url"),
        "gif_url": enrichment.get("gif_url") or catalog.get("gif_url"),
        "enrichment": enrichment,
    }


def claim_block_trophy(
    user_id: str,
    height: int,
    *,
    payment_method: str = "mn2",
) -> Dict[str, Any]:
    """Claim a block trophy edition for a user (BM-U4)."""
    uid = (user_id or "").strip()
    if not uid or uid in ("default_user", "guest"):
        return {"success": False, "error": "guest_blocked"}

    h = int(height)
    iid = block_item_id(h)
    doc = _read_json(_MANIFEST_PATH, {"drops": {}})
    drops = doc.setdefault("drops", {})
    key = str(h)
    if key not in drops:
        sync_block_height()
        doc = _read_json(_MANIFEST_PATH, {"drops": {}})
        drops = doc.get("drops") or {}
        if key not in drops:
            return {"success": False, "error": "block_not_in_manifest", "height": h}

    row = drops[key]
    if row.get("claimed_by"):
        return {
            "success": False,
            "error": "already_claimed",
            "claimed_by": row.get("claimed_by"),
            "height": h,
        }

    method = (payment_method or "mn2").strip().lower()
    catalog = _catalog_row(h, row)

    if method == "mn2":
        from backend.services.trophy_pricing_service import get_effective_price
        from backend.services.unified_points_database import unified_points_db

        pricing = get_effective_price(iid)
        if not pricing.get("success"):
            price_coins = max(1, int(float(catalog.get("base_price_usd") or 2.99) * 100))
        else:
            price_coins = int(pricing.get("effective_price_coins") or 0)
        if price_coins <= 0:
            return {"success": False, "error": "price_not_configured", "item_id": iid}

        cfg_path = os.path.join(_BASE, "data", "mn2_config.json")
        coins_per_mn2 = 100.0
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    coins_per_mn2 = float(json.load(f).get("coins_per_mn2") or 100)
            except Exception:
                pass
        price_mn2 = price_coins / coins_per_mn2
        points = unified_points_db.get_all_points(uid).get("points", {})
        mn2_balance = float(points.get("mn2_balance") or 0)
        if mn2_balance < price_mn2:
            return {
                "success": False,
                "error": "insufficient_mn2",
                "price_mn2": price_mn2,
                "mn2_balance": mn2_balance,
            }
        debit = unified_points_db.add_points(
            user_id=uid,
            point_type="mn2_balance",
            amount=-price_mn2,
            source="block_trophy_claim",
            metadata={"item_id": iid, "block_height": h, "price_coins": price_coins},
        )
        if not debit.get("success", True):
            return {"success": False, "error": "mn2_debit_failed"}
    elif method == "paypal":
        return {
            "success": False,
            "error": "use_paypal_checkout",
            "item_id": iid,
            "shop_url": catalog.get("shop_url"),
        }
    else:
        return {"success": False, "error": "unsupported_payment_method", "method": method}

    from backend.services.trophy_fulfillment_service import grant_platform_edition

    grant = grant_platform_edition(
        uid,
        iid,
        catalog["name"],
        acquired_via="block_mint",
        price_type=method,
        extra={"block_height": h, "platform_trophy": True, "ai_generated": True},
    )
    if not grant.get("success"):
        return grant
    edition_no = grant.get("edition_no")
    edition_key = grant.get("edition_key")
    proof_hash = grant.get("proof_hash")
    edition = grant.get("edition") or {}

    battle_stats: Dict[str, Any] = {}
    lic = (drops.get(key) or {}).get("license_number") or catalog.get("license_number")
    trading: Optional[Dict[str, Any]] = None
    try:
        from backend.services.block_trophy_battle_service import generate_battle_stats
        from backend.services.trophy_fulfillment_service import patch_edition_fields

        battle_stats = generate_battle_stats(
            h,
            edition_key or f"TRO-{iid}-{edition_no}",
            edition_no=int(edition_no or 1),
        )
        try:
            from backend.services.block_trophy_registry_service import build_trading_profile

            trading = build_trading_profile(
                h,
                stats=battle_stats,
                claimed=True,
                claimed_by=uid,
                edition_key=edition_key,
                edition_no=int(edition_no or 1),
                proof_hash=proof_hash,
            )
            if lic:
                trading["license_number"] = lic
        except Exception:
            trading = None

        patch_edition_fields(
            uid,
            iid,
            int(edition_no or 1),
            {
                "battle_stats": battle_stats,
                "serial_number": battle_stats.get("serial_number"),
                "license_number": lic or (trading or {}).get("license_number"),
                "trading_profile": trading,
                "block_height": h,
                "platform_trophy": True,
                "one_per_block": True,
            },
        )
        edition = {**edition, "battle_stats": battle_stats, "serial_number": battle_stats.get("serial_number")}
    except Exception:
        pass

    row["claimed_by"] = uid
    row["claimed_at"] = _iso()
    row["edition_no"] = edition_no
    row["edition_key"] = edition_key
    row["proof_hash"] = proof_hash
    if trading:
        row["trading_profile"] = trading
    drops[key] = row
    doc["updated_at"] = _iso()
    _write_json(_MANIFEST_PATH, doc)

    try:
        from backend.services.mn2_ledger import append_entry

        append_entry(
            uid,
            "block_trophy_proof",
            float(catalog.get("effective_price_usd") or catalog.get("base_price_usd") or 0),
            txid=f"block:{h}:{uid}",
            metadata={
                "item_id": iid,
                "block_height": h,
                "edition_no": edition_no,
                "edition_key": edition_key,
                "proof_hash": proof_hash,
                "payment_method": method,
            },
        )
    except Exception:
        pass

    enrichment: Dict[str, Any] = {}
    try:
        from backend.services.trophy_grant_enrichment_service import enrich_block_trophy_grant

        enrichment = enrich_block_trophy_grant(
            uid,
            iid,
            int(edition_no or 1),
            edition_key or "",
            proof_hash or "",
            h,
            acquired_via="block_mint",
            battle_stats=battle_stats,
            license_number=lic or catalog.get("license_number") or "",
            trading_profile=trading,
        )
        if enrichment.get("gif_url"):
            edition = {**edition, "gif_url": enrichment["gif_url"], "image_url": enrichment.get("image_url")}
    except Exception:
        pass

    return {
        "success": True,
        "height": h,
        "item_id": iid,
        "edition_no": edition_no,
        "edition_key": edition_key,
        "edition": edition,
        "battle_stats": enrichment.get("battle_stats") or battle_stats,
        "serial_number": (enrichment.get("battle_stats") or battle_stats or {}).get("serial_number"),
        "license_number": lic or catalog.get("license_number"),
        "trading_profile": trading or catalog.get("trading_profile"),
        "explorer_url": catalog.get("explorer_url"),
        "gif_url": enrichment.get("gif_url") or catalog.get("gif_url"),
        "enrichment": enrichment,
    }
