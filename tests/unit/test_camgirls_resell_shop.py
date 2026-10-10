"""Camgirls brand pack shop SKUs."""
from backend.services.camgirls_resell_shop_service import (
    list_resell_digital_goods,
    shop_item_id_for_performer,
)
from backend.services.monetization_config_service import get_digital_goods


def test_shop_sku_per_performer():
    sku = shop_item_id_for_performer("performer_nova")
    assert sku == "dg-camgirls-brand-nova"


def test_resell_goods_count():
    goods = list_resell_digital_goods()
    assert len(goods) == 16
    assert any(g["id"] == "dg-camgirls-brand-all-15" for g in goods)


def test_merged_into_digital_goods():
    ids = {g["id"] for g in get_digital_goods()}
    assert "dg-camgirls-brand-nova" in ids
