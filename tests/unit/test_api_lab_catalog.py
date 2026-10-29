"""API Lab catalog grouping."""
import os

import pytest

from backend.routes.api_lab_routes import build_catalog, category_for, is_try_safe


@pytest.fixture
def lite_app_client():
    previous = os.environ.get("LITE_APP")
    os.environ["LITE_APP"] = "1"
    try:
        from run import app

        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        if previous is None:
            os.environ.pop("LITE_APP", None)
        else:
            os.environ["LITE_APP"] = previous


def test_lite_app_serves_api_lab_page_and_catalog(lite_app_client):
    for path in ("/api-lab/", "/vidgenerator/api-lab/"):
        resp = lite_app_client.get(path)
        assert resp.status_code == 200
        assert b"API Lab" in resp.data
    catalog = lite_app_client.get("/api/lab/catalog")
    assert catalog.status_code == 200
    payload = catalog.get_json()
    assert payload.get("success") is True
    assert payload.get("total", 0) > 0


def test_category_for_api_prefixes():
    assert category_for("/api/health") == "health"
    assert category_for("/api/shop/items") == "shop"
    assert category_for("/vidgenerator/api/mn2/balance") == "mn2"
    assert category_for("/api/lab/catalog") == "lab"


def test_try_safe_only_paramless_gets():
    assert is_try_safe("GET", "/api/health") is True
    assert is_try_safe("GET", "/api/user/<user_id>") is False
    assert is_try_safe("POST", "/api/shop/purchase") is False


def test_build_catalog_groups_and_skips_head():
    catalog = build_catalog([
        ("/api/health", ["GET", "HEAD", "OPTIONS"]),
        ("/api/shop/items", ["GET"]),
        ("/static/app.js", ["GET"]),
    ])
    assert catalog["total"] == 2
    ids = [row["id"] for row in catalog["categories"]]
    assert "health" in ids
    assert "shop" in ids
def test_small_groups_fold_into_more():
    rules = [("/api/health", ["GET"])] + [
        ("/api/rare-%s/x" % i, ["GET"]) for i in range(3)
    ]
    catalog = build_catalog(rules)
    ids = {row["id"] for row in catalog["categories"]}
    assert "health" in ids
    assert "more" in ids
    assert "rare-0" not in ids
