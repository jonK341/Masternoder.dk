"""Site-issued NFT primary sale and coin resale book."""
import json

import pytest


@pytest.fixture
def nft_state(tmp_path, monkeypatch):
    from backend.services import nft_exchange_service as nft

    state = tmp_path / "nft_state.json"
    catalog = {
        "secondary_fee_percent": 5,
        "min_list_coins": 20,
        "skus": [
            {
                "sku": "nft-test",
                "name": "Test Edition",
                "series": "Test",
                "rarity": "common",
                "supply": 2,
                "price_usd": 4.99,
                "price_coins": 100,
                "description": "test",
            }
        ],
    }
    catalog_path = tmp_path / "nft_catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    monkeypatch.setattr(nft, "_STATE", str(state))
    monkeypatch.setattr(nft, "_CATALOG", str(catalog_path))
    return nft


@pytest.fixture
def points_db(tmp_path, monkeypatch):
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path))
    monkeypatch.setattr(upd, "unified_points_db", db)

    def _file_only_get(user_id: str):
        return {"success": True, "points": db._points_payload_from_file(user_id)}

    monkeypatch.setattr(db, "get_all_points", _file_only_get)
    return db


def test_primary_coin_buy_mints_serial_and_debits(nft_state, points_db):
    points_db.add_points("buyer1", "coins", 250, source="seed", metadata={"reference": "seed-nft-1"})
    minted = nft_state.buy_with_coins("buyer1", "nft-test")
    assert minted["success"] is True
    assert minted["edition"]["edition_id"] == "nft-test#1"
    bal = points_db.get_all_points("buyer1")
    assert float(bal["points"]["coins"]) == pytest.approx(150.0)


def test_paypal_mint_is_idempotent_and_rejects_underpay(nft_state):
    under = nft_state.grant_paypal_mint("buyer2", "nft-test", "ORDER1", 1.00)
    assert under["success"] is False
    assert under["error"] == "underpaid"
    first = nft_state.grant_paypal_mint("buyer2", "nft-test", "ORDER1", 4.99)
    second = nft_state.grant_paypal_mint("buyer2", "nft-test", "ORDER1", 4.99)
    assert first["success"] is True
    assert second.get("already_minted") is True
    assert first["edition"]["edition_id"] == second["edition"]["edition_id"]
    assert nft_state.catalog()["skus"][0]["minted"] == 1


def test_resale_pays_seller_and_keeps_fee(nft_state, points_db):
    points_db.add_points("seller", "coins", 100, source="seed", metadata={"reference": "seed-nft-s"})
    points_db.add_points("buyer", "coins", 500, source="seed", metadata={"reference": "seed-nft-b"})
    minted = nft_state.buy_with_coins("seller", "nft-test")
    edition_id = minted["edition"]["edition_id"]
    listed = nft_state.list_for_sale("seller", edition_id, 200)
    assert listed["success"] is True
    assert listed["listing"]["fee_coins"] == 10
    filled = nft_state.buy_listing("buyer", listed["listing"]["listing_id"])
    assert filled["success"] is True
    assert filled["edition"]["owner_id"] == "buyer"
    seller_bal = points_db.get_all_points("seller")
    buyer_bal = points_db.get_all_points("buyer")
    assert float(seller_bal["points"]["coins"]) == pytest.approx(190.0)
    assert float(buyer_bal["points"]["coins"]) == pytest.approx(300.0)
    book = nft_state.deals()
    assert book["open_count"] == 0
    assert book["house_fee_coins"] == 110
    assert book["recent_trades"][0]["kind"] == "resale"


def test_cannot_list_unowned_or_buy_own(nft_state, points_db):
    points_db.add_points("owner", "coins", 100, source="seed", metadata={"reference": "seed-nft-o"})
    minted = nft_state.buy_with_coins("owner", "nft-test")
    edition_id = minted["edition"]["edition_id"]
    denied = nft_state.list_for_sale("other", edition_id, 50)
    assert denied["error"] == "not_owner"
    listed = nft_state.list_for_sale("owner", edition_id, 50)
    own = nft_state.buy_listing("owner", listed["listing"]["listing_id"])
    assert own["error"] == "cannot_buy_own_listing"


def test_catalog_route(nft_state):
    from flask import Flask

    from backend.routes.nft_routes import nft_bp

    app = Flask(__name__)
    app.register_blueprint(nft_bp)
    with app.test_client() as client:
        response = client.get("/api/nft/catalog")
    assert response.status_code == 200
    body = response.get_json()
    assert body["skus"][0]["sku"] == "nft-test"
    assert body["skus"][0]["remaining"] == 2
