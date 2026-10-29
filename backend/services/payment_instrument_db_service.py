"""Persist payment instrument tokens (provider refs only — never PAN/CVV)."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)


def save_instrument(
    user_id: str,
    *,
    provider: str,
    token_ref: str,
    instrument_type: str = "card",
    brand: Optional[str] = None,
    last4: Optional[str] = None,
    exp_month: Optional[int] = None,
    exp_year: Optional[int] = None,
    billing_name: Optional[str] = None,
    billing_country: Optional[str] = None,
    fingerprint: Optional[str] = None,
    is_default: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """Insert or update a vaulted payment instrument reference."""
    if not user_id or not provider or not token_ref:
        return False
    try:
        from src.db.models import db

        db.session.execute(
            text(
                """
                INSERT INTO payment_instruments (
                  user_id, provider, instrument_type, token_ref, fingerprint,
                  brand, last4, exp_month, exp_year, billing_name, billing_country,
                  is_default, status, metadata_json
                ) VALUES (
                  :user_id, :provider, :instrument_type, :token_ref, :fingerprint,
                  :brand, :last4, :exp_month, :exp_year, :billing_name, :billing_country,
                  :is_default, 'active', :metadata_json
                )
                ON CONFLICT(provider, token_ref) DO UPDATE SET
                  user_id=excluded.user_id,
                  brand=excluded.brand,
                  last4=excluded.last4,
                  exp_month=excluded.exp_month,
                  exp_year=excluded.exp_year,
                  billing_name=excluded.billing_name,
                  billing_country=excluded.billing_country,
                  is_default=excluded.is_default,
                  metadata_json=excluded.metadata_json,
                  updated_at=CURRENT_TIMESTAMP
                """
            ),
            {
                "user_id": user_id,
                "provider": provider.strip().lower(),
                "instrument_type": instrument_type.strip().lower(),
                "token_ref": token_ref.strip(),
                "fingerprint": fingerprint,
                "brand": brand,
                "last4": (last4 or "")[-4:] if last4 else None,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "billing_name": billing_name,
                "billing_country": billing_country,
                "is_default": 1 if is_default else 0,
                "metadata_json": json.dumps(metadata or {}),
            },
        )
        if is_default:
            db.session.execute(
                text(
                    """
                    UPDATE payment_instruments
                    SET is_default=0
                    WHERE user_id=:user_id AND provider=:provider AND token_ref != :token_ref
                    """
                ),
                {"user_id": user_id, "provider": provider.strip().lower(), "token_ref": token_ref.strip()},
            )
        db.session.commit()
        return True
    except Exception:
        logger.exception("save_instrument failed for user=%s provider=%s", user_id, provider)
        try:
            from src.db.models import db

            db.session.rollback()
        except Exception:
            pass
        return False


def list_instruments(user_id: str, *, active_only: bool = True) -> List[Dict[str, Any]]:
    if not user_id:
        return []
    try:
        from src.db.models import db

        clause = "AND status='active'" if active_only else ""
        rows = db.session.execute(
            text(
                f"""
                SELECT id, provider, instrument_type, brand, last4, exp_month, exp_year,
                       billing_name, billing_country, is_default, status, created_at
                FROM payment_instruments
                WHERE user_id=:user_id {clause}
                ORDER BY is_default DESC, id DESC
                """
            ),
            {"user_id": user_id},
        ).fetchall()
        return [
            {
                "id": r[0],
                "provider": r[1],
                "instrument_type": r[2],
                "brand": r[3],
                "last4": r[4],
                "exp_month": r[5],
                "exp_year": r[6],
                "billing_name": r[7],
                "billing_country": r[8],
                "is_default": bool(r[9]),
                "status": r[10],
                "created_at": str(r[11]) if r[11] else None,
            }
            for r in rows
        ]
    except Exception:
        logger.exception("list_instruments failed for user=%s", user_id)
        return []
