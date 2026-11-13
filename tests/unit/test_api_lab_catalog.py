"""API Lab catalog grouping."""
import os

import pytest

from backend.routes.api_lab_routes import (
    build_catalog,
    category_for,
    is_catalog_path,
    is_try_safe,
    normalize_category,
)


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
    resp = lite_app_client.get("/api-lab/")
    assert resp.status_code == 200
    assert b"API Lab" in resp.data
    legacy = lite_app_client.get("/vidgenerator/api-lab/")
    assert legacy.status_code in (301, 302, 308)
    assert legacy.headers.get("Location", "").endswith("/api-lab/")
    catalog = lite_app_client.get("/api/lab/catalog")
    assert catalog.status_code == 200
    payload = catalog.get_json()
    assert payload.get("success") is True
    assert payload.get("total", 0) > 0
    # Default view hides tooling / Other noise.
    assert payload.get("internal_hidden") is True
    ids = {row["id"] for row in payload["categories"]}
    assert "more" not in ids
    paths = [row["path"] for row in payload["endpoints"]]
    assert all(p.startswith("/api/") for p in paths)
    assert not any(p.startswith("/api-lab") for p in paths)
    assert not any("/index.html" in p for p in paths)


def test_catalog_can_include_internal(lite_app_client):
    payload = lite_app_client.get("/api/lab/catalog?internal=1").get_json()
    ids = {row["id"] for row in payload["categories"]}
    assert "more" in ids or "debugger" in ids


def test_category_for_api_prefixes():
    assert category_for("/api/health") == "health"
    assert category_for("/api/shop/items") == "shop"
    assert category_for("/vidgenerator/api/mn2/balance") == "mn2"
    assert category_for("/api/lab/catalog") == "lab"


def test_normalize_merges_typos_and_aliases():
    assert normalize_category("trophie") == "trophies"
    assert normalize_category("debug") == "debugger"
    assert normalize_category("debugging") == "debugger"
    assert normalize_category("aggregators") == "aggregator"
    assert normalize_category("floor") == "camgirls"


def test_catalog_path_filters_noise():
    assert is_catalog_path("/api/health") is True
    assert is_catalog_path("/api-lab/") is False
    assert is_catalog_path("/battle/index.html") is False
    assert is_catalog_path("/vidgenerator/api/<path:path>") is False
    assert is_catalog_path("/api") is False


def test_try_safe_only_paramless_gets():
    assert is_try_safe("GET", "/api/health") is True
    assert is_try_safe("GET", "/api/user/<user_id>") is False
    assert is_try_safe("POST", "/api/shop/purchase") is False


def test_build_catalog_groups_and_skips_head():
    catalog = build_catalog([
        ("/api/health", ["GET", "HEAD", "OPTIONS"]),
        ("/api/shop/items", ["GET"]),
        ("/static/app.js", ["GET"]),
        ("/api-lab/", ["GET"]),
        ("/battle/index.html", ["GET"]),
        ("/vidgenerator/api/<path:path>", ["GET"]),
    ])
    assert catalog["total"] == 2
    ids = [row["id"] for row in catalog["categories"]]
    assert "health" in ids
    assert "shop" in ids
    assert "more" not in ids


def test_small_groups_fold_into_more():
    rules = [("/api/health", ["GET"])] + [
        ("/api/rare-%s/x" % i, ["GET"]) for i in range(3)
    ]
    catalog = build_catalog(rules)
    ids = {row["id"] for row in catalog["categories"]}
    assert "health" in ids
    assert "more" in ids
    assert "rare-0" not in ids
    assert catalog["categories"][-1]["id"] == "more"


def test_trophie_merges_into_trophies():
    catalog = build_catalog([
        ("/api/trophies/list", ["GET"]),
        ("/api/trophie/award", ["POST"]),
    ] + [("/api/trophies/item-%s" % i, ["GET"]) for i in range(12)])
    ids = {row["id"] for row in catalog["categories"]}
    assert "trophies" in ids
    assert "trophie" not in ids


def test_monitor_endpoints_use_cleaned_catalog(lite_app_client):
    payload = lite_app_client.get("/api/monitor/endpoints").get_json()
    assert payload.get("success") is True
    assert payload.get("count", 0) > 0
    paths = [row["path"] for row in payload["endpoints"]]
    assert all(p.startswith("/api/") for p in paths)
    assert "/api-lab" not in paths
    assert "/api-lab/" not in paths
    page = lite_app_client.get("/api")
    assert page.status_code == 200
    assert b"API Monitor" in page.data
    assert b"API Lab" in page.data
    assert b"/api-lab/?path=" in page.data
    assert b"Open API Lab" in page.data


def test_api_lab_page_links_out_and_supports_deep_link_markup(lite_app_client):
    page = lite_app_client.get("/api-lab/")
    assert page.status_code == 200
    body = page.data
    assert b'href="/api"' in body or b'href="/api/"' in body
    assert b"/api-lab/?path=/api/health" in body
    assert b"api-lab.js" in body


def test_hub_pages_link_to_api_lab(lite_app_client):
    home = lite_app_client.get("/")
    assert home.status_code == 200
    assert b'href="/api-lab/"' in home.data
    lab = lite_app_client.get("/lab/")
    assert lab.status_code in (200, 301, 302, 308)
    if lab.status_code == 200:
        assert b"/api-lab/" in lab.data
    debugger = lite_app_client.get("/debugger/")
    assert debugger.status_code in (200, 301, 302, 308)
    if debugger.status_code == 200:
        assert b"/api-lab/" in debugger.data
