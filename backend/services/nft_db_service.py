"""Read NFT catalog and ownership from SQLite when tables exist (fallback: JSON files)."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from sqlalchemy import text

logger = logging.getLogger(__name__)


def catalog_skus_from_db() -> List[Dict[str, Any]]:
    try:
        from src.db.models import db

        rows = db.session.execute(
            text(
                """
                SELECT sku, name, series, rarity, supply, price_usd, price_coins,
                       trophy_id, emblem_icon, avatar_url, description
                FROM nft_catalog_skus
                WHERE is_active=1
                ORDER BY sku
                """
            )
        ).fetchall()
        if not rows:
            return []
        minted = {}
        for sku, count in db.session.execute(
            text("SELECT sku, COUNT(*) FROM nft_editions GROUP BY sku")
        ).fetchall():
            minted[str(sku)] = int(count or 0)
        out: List[Dict[str, Any]] = []
        for row in rows:
            sku = row[0]
            supply = int(row[4] or 0)
            m = minted.get(sku, 0)
            out.append(
                {
                    "sku": sku,
                    "name": row[1],
                    "series": row[2],
                    "rarity": row[3],
                    "supply": supply,
                    "minted": m,
                    "remaining": max(0, supply - m),
                    "price_usd": float(row[5] or 0),
                    "price_coins": int(row[6] or 0),
                    "trophy_id": row[7],
                    "emblem_icon": row[8],
                    "avatar_url": row[9],
                    "description": row[10],
                }
            )
        return out
    except Exception:
        logger.debug("catalog_skus_from_db unavailable", exc_info=True)
        return []


def user_editions_from_db(user_id: str) -> List[Dict[str, Any]]:
    if not user_id:
        return []
    try:
        from src.db.models import db

        rows = db.session.execute(
            text(
                """
                SELECT e.edition_id, e.sku, e.serial, e.status, e.minted_at,
                       c.name, c.trophy_id, c.emblem_icon, c.avatar_url
                FROM nft_editions e
                LEFT JOIN nft_catalog_skus c ON c.sku = e.sku
                WHERE e.owner_user_id = :uid
                ORDER BY e.minted_at DESC, e.serial ASC
                """
            ),
            {"uid": user_id},
        ).fetchall()
        return [
            {
                "edition_id": r[0],
                "sku": r[1],
                "serial": r[2],
                "status": r[3],
                "minted_at": r[4],
                "name": r[5],
                "trophy_id": r[6],
                "emblem_icon": r[7],
                "avatar_url": r[8],
            }
            for r in rows
        ]
    except Exception:
        logger.debug("user_editions_from_db unavailable", exc_info=True)
        return []
