"""
User location (GPS) service.
Single source of truth for user latitude, longitude, and geo_ref.
File-backed with optional DB sync for agent_geo_refs compatibility.
"""
import os
import json
from typing import Dict, Optional, Any
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DATA_PATH = os.path.join(BASE_DIR, "data", "user_locations.json")


class UserLocationService:
    """Store and retrieve user GPS location (latitude, longitude, geo_ref)."""

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or DEFAULT_DATA_PATH
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save(self, data: Dict[str, Dict[str, Any]]) -> None:
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_location(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get latest location for user. Returns dict with latitude, longitude, geo_ref, accuracy, updated_at, source."""
        data = self._load()
        entry = data.get(user_id)
        if not entry:
            return None
        return {
            "latitude": entry.get("latitude"),
            "longitude": entry.get("longitude"),
            "geo_ref": entry.get("geo_ref") or "",
            "accuracy": entry.get("accuracy"),
            "updated_at": entry.get("updated_at"),
            "source": entry.get("source") or "manual",
        }

    def update_location(
        self,
        user_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        geo_ref: Optional[str] = None,
        accuracy: Optional[float] = None,
        source: str = "manual",
    ) -> Dict[str, Any]:
        """
        Update user location. All fields optional; only provided ones are updated.
        source: 'browser' | 'manual' | 'api'
        """
        data = self._load()
        entry = data.get(user_id) or {}
        if latitude is not None:
            entry["latitude"] = float(latitude)
        if longitude is not None:
            entry["longitude"] = float(longitude)
        if geo_ref is not None:
            entry["geo_ref"] = str(geo_ref).strip()
        if accuracy is not None:
            entry["accuracy"] = float(accuracy)
        entry["updated_at"] = datetime.utcnow().isoformat() + "Z"
        entry["source"] = source or "manual"
        data[user_id] = entry
        self._save(data)

        # Optional: sync to agent_geo_refs table for hunters_game / profile geo_ref
        self._sync_to_agent_geo_refs(user_id, entry)

        return self.get_location(user_id) or {}

    def _sync_to_agent_geo_refs(self, user_id: str, entry: Dict[str, Any]) -> None:
        """If DB is available, upsert into agent_geo_refs so existing geo-ref APIs still see it."""
        try:
            try:
                from src.db.models import db
            except ImportError:
                db = None
            from sqlalchemy import text
            if db and entry.get("latitude") is not None and entry.get("longitude") is not None:
                db.session.execute(
                    text("""
                        INSERT INTO agent_geo_refs (user_id, latitude, longitude, geo_ref, updated_at)
                        VALUES (:uid, :lat, :lon, :gr, CURRENT_TIMESTAMP)
                    """),
                    {
                        "uid": user_id,
                        "lat": entry["latitude"],
                        "lon": entry["longitude"],
                        "gr": entry.get("geo_ref") or "",
                    },
                )
                db.session.commit()
        except Exception:
            try:
                if db:
                    db.session.rollback()
            except Exception:
                pass


user_location_service = UserLocationService()
