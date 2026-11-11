"""50 × 12 exchange-wallet enrichment knob walkthrough."""
from __future__ import annotations

from flask import Flask


def test_knob_catalog_is_complete():
    from backend.services.exchange_wallet_x_knobs import (
        MEGA_MIN_KNOBS,
        PRIORITY_BY_PILLAR,
        PRIORITY_IDS,
        walkthrough,
    )

    full = walkthrough()
    assert full["success"] is True
    assert full["count"] == 50
    assert full["total_knob_slots"] == 600
    assert len(full["knob_glossary"]) == 12
    assert full["priority_ids"] == list(PRIORITY_IDS)
    assert len(PRIORITY_IDS) == 18
    assert set(PRIORITY_IDS) == {
        eid for ids in PRIORITY_BY_PILLAR.values() for eid in ids
    }
    assert PRIORITY_BY_PILLAR["custody"] == ("X-03", "X-04", "X-27", "X-38")
    assert PRIORITY_BY_PILLAR["desk"] == ("X-02", "X-05", "X-08", "X-39", "X-40")
    assert PRIORITY_BY_PILLAR["risk"] == ("X-22", "X-41", "X-46", "X-48")
    assert PRIORITY_BY_PILLAR["ops"] == ("X-09", "X-31", "X-34", "X-35", "X-43")

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
    assert prio_body["count"] == 18
    assert len(prio_body["enrichments"]) == 18
    assert set(prio_body["by_pillar"]) == {"custody", "desk", "risk", "ops"}
    assert "SPORK_116_WALLET_ONCHAIN_WITHDRAW" in prio_body["live_gates_default_off"]
    assert "SPORK_118_ANOMALY_HARD_ENFORCE" in prio_body["safety_gates_default_on"]

    run = c.get("/api/exchange/wallet-mega/priority/run")
    assert run.status_code == 200
    run_body = run.get_json()
    assert run_body["count"] == 18
    assert run_body["ok_count"] == 18
    assert run_body["results"]["X-38"]["enrichment"] == "X-38"
    assert run_body["results"]["X-48"]["recommended"] is not None

    one = c.get("/api/exchange/wallet-mega/priority/X-27")
    assert one.status_code == 200
    one_body = one.get_json()
    assert one_body["success"] is True
    assert one_body["enrichment"] == "X-27"
    assert "files" in one_body

    sporks = c.get("/api/exchange/wallet-mega/sporks")
    assert sporks.status_code == 200
    spork_body = sporks.get_json()
    assert spork_body["success"] is True
    assert len(spork_body["new_wallet_gates"]) == 6
    assert "SPORK_101_SERVICES_ENFORCEMENT" in spork_body["fixed_advisory"]
    assert "SPORK_112_EXCHANGE_LIVE_TRADING" in spork_body["intentional_hold"]
    assert "SPORK_101_SERVICES_ENFORCEMENT" not in spork_body["unused_by_app"]
    assert "gate_status" in spork_body
    assert "SPORK_118_ANOMALY_HARD_ENFORCE" in spork_body["gate_status"]["sporks"]


def test_guided_trade_respects_spork_120(monkeypatch):
    from backend.services import exchange_wallet_mega_prototype_service as mega
    from backend.services import mn2_spork_service as spork

    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_120_GUIDED_TRADE_EXECUTE": %d}' % spork.SPORK_OFF,
    )
    spork.invalidate_cache()

    def fake_quote(uid, symbol, side, amt, quote="MN2"):
        return {"success": True, "quote_id": "q1", "symbol": symbol, "amount": amt}

    monkeypatch.setattr(
        "backend.services.crypto_exchange_service.quote_swap",
        fake_quote,
        raising=False,
    )
    # Import path used inside guided_onchain
    import backend.services.crypto_exchange_service as ex

    monkeypatch.setattr(ex, "quote_swap", fake_quote)

    called = {"execute": False}

    def fake_execute(*_a, **_k):
        called["execute"] = True
        return {"success": True}

    monkeypatch.setattr(ex, "execute_swap", fake_execute)

    out = mega.guided_onchain(user_id="u1", step="trade", amount_mn2=0.01)
    assert out["success"] is True
    assert out["trade"]["dry_run"] is True
    assert called["execute"] is False
    assert out["gates"]["spork_120"]["allowed"] is False


def test_withdraw_broadcast_respects_spork_116(monkeypatch):
    from backend.services import exchange_wallet_mega_prototype_service as mega
    from backend.services import mn2_spork_service as spork

    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_116_WALLET_ONCHAIN_WITHDRAW": %d, "SPORK_118_ANOMALY_HARD_ENFORCE": %d}'
        % (spork.SPORK_OFF, spork.SPORK_OFF),
    )
    spork.invalidate_cache()

    monkeypatch.setattr(
        mega,
        "assess_anomaly",
        lambda **_k: {"success": True, "blocked": False, "allow_broadcast": True},
    )

    out = mega.guided_onchain(
        user_id="u1",
        step="withdraw",
        amount_mn2=1.0,
        withdraw_address="MNtestaddr",
        execute_withdraw=True,
    )
    assert out["success"] is False
    assert out["withdraw"]["blocked"] is True
    assert "spork_wallet_onchain_withdraw_off" in (out.get("error") or "")


def test_train_f_core_and_acceptance_routes(monkeypatch):
    from backend.routes.crypto_exchange_routes import crypto_exchange_bp
    from backend.services import mn2_spork_service as spork
    from flask import Flask

    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    monkeypatch.delenv("MN2_SPORK_OVERRIDE_JSON", raising=False)
    spork.invalidate_cache()

    app = Flask(__name__)
    app.register_blueprint(crypto_exchange_bp)
    c = app.test_client()

    ver = c.get("/api/exchange/wallet-mega/version")
    assert ver.status_code == 200
    ver_body = ver.get_json()
    assert ver_body["mega_target"] == "v32.6.6.0"
    assert ver_body["channel"] == "draft"
    assert ver_body["latest_wallet_download_unchanged"] is True

    core = c.get("/api/exchange/wallet-mega/train-f-core")
    assert core.status_code == 200
    core_body = core.get_json()
    assert core_body["count"] == 10
    assert core_body["ok_count"] == 10
    assert core_body["results"]["X-01"]["enrichment"] == "X-01"
    assert core_body["results"]["X-10"]["compose"]["exists"] is True

    acc = c.get("/api/exchange/wallet-mega/acceptance")
    assert acc.status_code == 200
    acc_body = acc.get_json()
    assert acc_body["passed"] is True
    assert acc_body["gates"]["exchange_live"]["allowed"] is False
    assert acc_body["gates"]["payout_live"]["allowed"] is False
    ids = [row["id"] for row in acc_body["checks"]]
    assert "paper_trade" in ids
    assert "withdraw_dry_run" in ids
