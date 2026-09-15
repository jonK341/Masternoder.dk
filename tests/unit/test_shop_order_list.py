"""Shop catalog purchases + stall listings + PDF export.

Run: pytest tests/unit/test_shop_order_list.py tests/unit/test_shop_order_lists.py tests/unit/test_shop_order_pdf.py tests/test_shop_taxonomy.py -v
"""
from __future__ import annotations

import inspect
import os
from pathlib import Path
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()

ROOT = Path(__file__).resolve().parents[2]


def _minimal_shop_app():
    from flask import Flask
    from backend.routes.shop_routes import shop_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(shop_bp)
    return app


def test_shop_purchases_source_is_shop_db_only():
    from backend.routes import shop_routes

    src = inspect.getsource(shop_routes.shop_purchases)
    assert "collect_shop_purchases" in src
    assert "list_user_orders" not in src
    assert "collect_hosting_orders" not in src
    assert not hasattr(shop_routes, "shop_orders")


def test_shop_purchases_api_enriches_taxonomy_and_status():
    fake = [
        {
            "id": 9,
            "item_id": "booster-1",
            "item_name": "Booster Pack #1",
            "quantity": 2,
            "price_type": "coins",
            "price_paid_coins": 80,
            "purchase_status": "pending",
            "created_at": "2026-09-15T12:00:00+00:00",
        },
        {
            "id": 10,
            "item_id": "shop-super-stack-core",
            "item_name": "Super Stack Core",
            "quantity": 1,
            "price_type": "mn2",
            "price_paid_points": {"mn2": 1.25},
            "purchase_status": "completed",
            "created_at": "2026-09-14T12:00:00+00:00",
        },
    ]
    app = _minimal_shop_app()
    with app.test_client() as client:
        with patch("backend.services.shop_db_service.get_purchases", return_value=fake):
            resp = client.get("/api/shop/purchases?user_id=order_list_user")
    assert resp.status_code == 200
    body = resp.get_json() or {}
    assert body.get("success") is True
    rows = body.get("purchases") or []
    assert len(rows) == 2
    pending = next(r for r in rows if r.get("item_id") == "booster-1")
    done = next(r for r in rows if r.get("item_id") == "shop-super-stack-core")
    assert pending.get("subcategory") == "boosts"
    assert pending.get("status_bucket") == "pending"
    assert pending.get("quantity") == 2
    assert done.get("subcategory") == "stacks"
    assert done.get("status_bucket") == "completed"


def test_shop_purchases_empty_and_error_payload():
    app = _minimal_shop_app()
    with app.test_client() as client:
        with patch("backend.services.shop_db_service.get_purchases", return_value=[]):
            ok = client.get("/api/shop/purchases?user_id=empty_user")
        assert ok.status_code == 200
        assert (ok.get_json() or {}).get("purchases") == []

        with patch(
            "backend.services.shop_db_service.get_purchases",
            side_effect=RuntimeError("db down"),
        ):
            still_ok = client.get("/api/shop/purchases?user_id=err_user")
        assert still_ok.status_code == 200
        payload = still_ok.get_json() or {}
        assert payload.get("success") is True
        assert payload.get("purchases") == []


def test_shop_and_profile_markup_has_three_order_lists():
    shop = (ROOT / "shop/index.html").read_text(encoding="utf-8")
    profile = (ROOT / "profile/index.html").read_text(encoding="utf-8")
    assert 'id="purchase-history-card"' in shop
    assert 'id="shop-orders-easy-view"' in shop
    assert 'id="shop-order-status-subnav"' in shop
    assert 'id="shop-history-subnav"' in shop
    assert 'id="stall-order-list"' in shop
    assert 'id="mn2-hosting-order-list"' in shop
    assert "Shop orders" in shop
    assert "Masternode hosting" in shop
    assert "Stall listings" in shop
    assert 'id="shop-order-pdf-btn"' in shop
    assert "shop-order-list.js" in shop
    assert "shop-taxonomy.js" in shop
    assert 'id="profile-shop-order-list"' in profile
    assert 'id="profile-mn2-hosting-order-list"' in profile
    assert 'id="profile-shop-stall-list"' in profile
    assert 'id="profile-shop-order-pdf-btn"' in profile
    assert "shop-order-list.js" in profile
    js = (ROOT / "static/js/shop-order-list.js").read_text(encoding="utf-8")
    assert "/api/shop/purchases" in shop
    assert "/api/shop/stall-orders" in shop
    assert "/api/shop/hosting-orders" in shop
    assert "loadHostingOrders" in shop
    assert "/api/shop/order-pdf" in js
    assert "/api/shop/orders" not in shop
    assert "/api/shop/orders" not in profile
    assert "formatPayment" in js
    assert "shop-order-check" in js


def test_shop_order_list_js_filters_and_renders():
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        return
    script = r"""
const fs = require('fs');
const vm = require('vm');
const context = { console, Date, setTimeout, clearTimeout };
context.window = context;
context.globalThis = context;
context.document = { querySelectorAll: () => [] };
vm.runInNewContext(fs.readFileSync('static/js/shop-taxonomy.js', 'utf8'), context);
vm.runInNewContext(fs.readFileSync('static/js/shop-order-list.js', 'utf8'), context);
const SOL = context.ShopOrderList;
const rows = [
  { id: 9, item_id: 'booster-1', item_name: 'Booster Pack #1', quantity: 2, price_type: 'coins', price_paid_coins: 80, purchase_status: 'pending', created_at: '2026-09-15T12:00:00Z', category: 'boosts' },
  { id: 10, item_id: 'shop-super-stack-core', item_name: 'Super Stack Core', quantity: 1, price_type: 'mn2', price_paid_points: { mn2: 1.25 }, purchase_status: 'completed', created_at: '2026-09-14T12:00:00Z', category: 'inventory' },
];
const classified = rows.map(SOL.classifyRow);
if (SOL.statusBucket(classified[0]) !== 'pending') throw new Error('pending bucket');
if (SOL.formatPrice(classified[0]) !== '80 coins') throw new Error('coins price');
if (!SOL.formatPrice(classified[1]).includes('MN2')) throw new Error('mn2 price');
const pending = SOL.filterOrders(classified, { status: 'pending', subcategory: 'all' });
if (pending.length !== 1 || pending[0].item_id !== 'booster-1') throw new Error('status filter');
const kits = SOL.filterOrders(classified, { status: 'all', subcategory: 'stacks' });
if (kits.length !== 1) throw new Error('subcat filter');
const empty = { innerHTML: '' };
SOL.render({ rows: [], listEl: empty });
if (!empty.innerHTML.includes('No shop orders yet')) throw new Error('empty state');
const err = { innerHTML: '' };
SOL.renderError(err, 'Could not load shop orders.');
if (!err.innerHTML.includes('Could not load shop orders')) throw new Error('error state');
const list = { innerHTML: '' };
const statusNav = { innerHTML: '', querySelectorAll: () => [] };
const subNav = { innerHTML: '', querySelectorAll: () => [] };
SOL.render({ rows: classified, listEl: list, statusNavEl: statusNav, subnavEl: subNav, subcategory: 'all', status: 'all' });
if (!list.innerHTML.includes('shop-order-table')) throw new Error('table missing');
if (!list.innerHTML.includes('Booster Pack #1')) throw new Error('item missing');
if (!list.innerHTML.includes('Qty')) throw new Error('qty header missing');
if (!list.innerHTML.includes('shop-order-check')) throw new Error('checkbox missing');
const listing = SOL.classifyRow({ listing_id: 'L1', item_name: 'Kit', quantity: 1, price_coins: 40, status: 'active', source: 'listing' });
if (SOL.statusBucket(listing) !== 'pending') throw new Error('listing pending');
if (SOL.formatPrice(listing) !== '40 coins') throw new Error('listing price');
if (SOL.selectedCount() !== 0) throw new Error('empty selection');
console.log('ok');
"""
    proc = subprocess.run(
        [node, "-e", script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "NO_COLOR": "1"},
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok" in proc.stdout
