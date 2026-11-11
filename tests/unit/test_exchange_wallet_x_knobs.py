"""50 × 12 exchange-wallet enrichment knob walkthrough."""
from __future__ import annotations

from flask import Flask


def test_knob_catalog_is_complete():
    from backend.services.exchange_wallet_x_knobs import MEGA_MIN_KNOBS, walkthrough

    full = walkthrough()
    assert full["success"] is True
    assert full["count"] == 50
    assert full["total_knob_slots"] == 600
    assert len(full["knob_glossary"]) == 12
    assert set(full["priority_ids"]) == {"X-03", "X-08", "X-40", "X-46"}

    for block in full["enrichments"]:
        assert block["success"] is True
        assert block["knob_count"] == 12
        knobs = {row["knob"]: row for row in block["knobs"]}
        for name in MEGA_MIN_KNOBS:
            assert knobs[name]["level"] == 1
            assert knobs[name]["mega_min"] is True
            assert knobs[name]["install"]


def test_priority_knob_install_texts_are_specific():
    from backend.services.exchange_wallet_x_knobs import knobs_for

    x03 = knobs_for("X-03")
    installs = " ".join(row["install"] for row in x03["knobs"])
    assert "PoR" in installs or "por" in installs.lower()

    x46 = knobs_for("X-46")
    assert any("broadcast" in row["install"].lower() or "block" in row["install"].lower() for row in x46["knobs"])


def test_wallet_mega_knob_routes():
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp

    app = Flask(__name__)
    app.register_blueprint(crypto_exchange_bp)
    c = app.test_client()

    all_knobs = c.get("/api/exchange/wallet-mega/knobs")
    assert all_knobs.status_code == 200
    body = all_knobs.get_json()
    assert body["success"] is True
    assert body["count"] == 50
    assert body["total_knob_slots"] == 600

    one = c.get("/api/exchange/wallet-mega/knobs/X-40")
    assert one.status_code == 200
    one_body = one.get_json()
    assert one_body["success"] is True
    assert one_body["count"] == 1
    assert one_body["enrichments"][0]["enrichment"]["id"] == "X-40"
    assert one_body["enrichments"][0]["knob_count"] == 12

    prio = c.get("/api/exchange/wallet-mega/priority")
    assert prio.status_code == 200
    prio_body = prio.get_json()
    assert prio_body["confirmed"] is True
    assert len(prio_body["enrichments"]) == 4
