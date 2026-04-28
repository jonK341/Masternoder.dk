"""
DNA Manipulation System
Implements two new tech actions:
- DNA Manipulation
- DNA Cloning

These actions award points into the Unified Points System.
"""
from typing import Dict, Any, Optional

from backend.services.unified_points_database import unified_points_db


class DNAManipulationSystem:
    """DNA tech actions that award points."""

    def dna_manipulation(self, user_id: str, intensity: int = 1, metadata: Optional[Dict[str, Any]] = None) -> Dict:
        intensity = max(1, int(intensity or 1))
        meta = metadata or {}

        # Award XP + Knowledge + DNA points
        unified_points_db.add_points(user_id, "xp", 180 * intensity, source="dna_manipulation", metadata=meta)
        unified_points_db.add_points(user_id, "knowledge_points", 40 * intensity, source="dna_manipulation", metadata=meta)
        unified_points_db.add_points(user_id, "dna_manipulation_points", 25 * intensity, source="dna_manipulation", metadata=meta)

        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('dna', extra={"tech": "dna_manipulation", "intensity": intensity})
        except Exception:
            pass

        return {
            "success": True,
            "user_id": user_id,
            "tech": "dna_manipulation",
            "intensity": intensity,
            "awarded": {
                "xp": 180 * intensity,
                "knowledge_points": 40 * intensity,
                "dna_manipulation_points": 25 * intensity,
            },
        }

    def dna_cloning(self, user_id: str, batch_size: int = 1, metadata: Optional[Dict[str, Any]] = None) -> Dict:
        batch_size = max(1, int(batch_size or 1))
        meta = metadata or {}

        unified_points_db.add_points(user_id, "xp", 220 * batch_size, source="dna_cloning", metadata=meta)
        unified_points_db.add_points(user_id, "knowledge_points", 55 * batch_size, source="dna_cloning", metadata=meta)
        unified_points_db.add_points(user_id, "dna_cloning_points", 30 * batch_size, source="dna_cloning", metadata=meta)

        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('dna', extra={"tech": "dna_cloning", "batch_size": batch_size})
        except Exception:
            pass

        return {
            "success": True,
            "user_id": user_id,
            "tech": "dna_cloning",
            "batch_size": batch_size,
            "awarded": {
                "xp": 220 * batch_size,
                "knowledge_points": 55 * batch_size,
                "dna_cloning_points": 30 * batch_size,
            },
        }


# Global instance
dna_manipulation_system = DNAManipulationSystem()

