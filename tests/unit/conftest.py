"""Unit-test fixtures — keep unified points file-only (no create_app())."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

import pytest


@pytest.fixture(autouse=True)
def _fast_unified_points(monkeypatch):
    try:
        from backend.services import unified_points_database as upd
    except ImportError:
        yield
        return

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)

    def _file_add(self, user_id, point_type, amount, source="system", metadata=None):
        pt = (point_type or "").strip()
        amt = float(amount or 0)
        if not pt:
            return {"success": False, "error": "point_type is required"}
        if amt == 0:
            return {"success": True, "user_id": user_id, "point_type": pt, "amount": 0}

        meta = metadata if isinstance(metadata, dict) else {}
        ref = (meta.get("reference") or meta.get("idempotency_key") or "").strip()
        if ref and pt in upd._MONEY_POINT_TYPES:
            cache_key = f"{user_id}:{pt}:{ref}"
            with upd._IDEMPOTENCY_LOCK:
                if cache_key in upd._IDEMPOTENCY_CACHE:
                    return {
                        "success": True,
                        "duplicate": True,
                        "user_id": user_id,
                        "point_type": pt,
                        "amount": amt,
                        "message": "Idempotent duplicate skipped",
                    }
                upd._IDEMPOTENCY_CACHE[cache_key] = datetime.now().isoformat()

        with upd._user_lock(user_id):
            return self._award_points_file_fallback(user_id, pt, amt, source, metadata)

    def _file_get(self, user_id="default_user"):
        pts = self._points_payload_from_file(user_id)
        return {"success": True, "user_id": user_id, "points": pts}

    monkeypatch.setattr(upd.UnifiedPointsDatabase, "add_points", _file_add)
    monkeypatch.setattr(upd.UnifiedPointsDatabase, "get_all_points", _file_get)
    yield
