from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_mn2_balance_is_exposed_as_crypto_points(tmp_path):
    from backend.services.unified_points_database import UnifiedPointsDatabase

    db = UnifiedPointsDatabase(base_dir=str(tmp_path))
    db._award_points_file_fallback("user-a", "mn2_balance", 1.25, "test")

    with patch.object(db, "_points_payload_from_db", return_value=None):
        result = db.get_all_points("user-a")

    points = result["points"]
    assert points["mn2_balance"] == 1.25
    assert points["crypto_points"] == 1.25
    assert points["systems"]["mn2_balance"] == 1.25
    assert points["systems"]["crypto_points"] == 1.25


def test_crypto_points_alias_does_not_create_spendable_mn2(tmp_path):
    from backend.services.unified_points_database import UnifiedPointsDatabase

    db = UnifiedPointsDatabase(base_dir=str(tmp_path))
    db._award_points_file_fallback("user-a", "crypto_points", 3, "test")

    with patch.object(db, "_points_payload_from_db", return_value=None):
        result = db.get_all_points("user-a")

    points = result["points"]
    assert points["crypto_points"] == 3
    assert points["mn2_balance"] == 0
