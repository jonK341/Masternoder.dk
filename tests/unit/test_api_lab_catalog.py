"""API Lab catalog grouping."""
from backend.routes.api_lab_routes import build_catalog, category_for, is_try_safe


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
