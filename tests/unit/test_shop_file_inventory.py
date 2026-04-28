"""
When shop DB migrations are absent, shop_db_service persists under MASTERNODER_LOG_DIR/shop_file_mode/.

Run: pytest tests/unit/test_shop_file_inventory.py -v
"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_shop_file_mode_record_purchase_inventory_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MASTERNODER_LOG_DIR"] = tmp
        from backend.services import shop_db_service as sds

        with patch.object(sds, "shop_tables_exist", return_value=False):
            uid = "test_file_mode_uid"
            pid = sds.record_purchase(
                uid,
                "item_test_a",
                "Test Item A",
                2,
                "coins",
                100,
                None,
                None,
                None,
            )
            assert pid is not None
            assert sds.add_to_inventory(uid, "item_test_a", "Test Item A", 2, pid) is True

            inv = sds.get_inventory(uid)
            assert any(r.get("item_id") == "item_test_a" and int(r.get("quantity") or 0) >= 2 for r in inv)

            pur = sds.get_purchases(uid, 10)
            assert any(r.get("item_id") == "item_test_a" for r in pur)
