"""Platform migration 010 — wallets, NFT tables, payment instrument slots."""
import os
import sqlite3

import pytest


@pytest.fixture
def platform_db(tmp_path):
    db = tmp_path / "platform.db"
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data = os.path.join(root, "data")
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "m010",
        os.path.join(root, "migrations", "010_platform_wallet_nft_payments.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.run(str(db), data)
    mod.run(str(db), data)
    return str(db)


def test_platform_tables_exist(platform_db):
    conn = sqlite3.connect(platform_db)
    names = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()
    for table in (
        "crypto_assets",
        "user_wallet_accounts",
        "user_financial_profiles",
        "payment_instruments",
        "nft_catalog_skus",
        "nft_editions",
        "staking_positions",
        "hosting_capacity",
    ):
        assert table in names


def test_nft_catalog_loaded(platform_db):
    conn = sqlite3.connect(platform_db)
    count = conn.execute("SELECT COUNT(*) FROM nft_catalog_skus").fetchone()[0]
    conn.close()
    assert int(count) >= 9
