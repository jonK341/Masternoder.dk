"""Signup/identify deposit address provisioning must not fail silently."""

from __future__ import annotations

import json


def test_provision_retries_then_succeeds(tmp_path, monkeypatch):
    from backend.services import mn2_onchain_wallet as onchain
    from backend.services import mn2_wallet_service as ws

    addr_path = tmp_path / "mn2_user_addresses.json"
    addr_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(ws, "_addresses_path", lambda: str(addr_path))
    monkeypatch.setattr(ws, "_wallet_mode", lambda: "ledger")

    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            return {
                "success": False,
                "error": "temporary_rpc",
                "code": "rpc_error",
                "deposit_address": None,
            }
        return {
            "success": True,
            "deposit_address": "JSignupRetryAddr000000000000001",
            "address": "JSignupRetryAddr000000000000001",
            "code": None,
        }

    monkeypatch.setattr(ws, "generate_daemon_address", flaky)
    monkeypatch.setattr(onchain, "_try_label", lambda address, user_id: {"labeled": False, "method": None})

    out = onchain.provision_signup_deposit_address("signup_user_retry", attempts=3)
    assert out.get("success") is True
    assert out.get("assigned") is True
    assert out.get("attempts") == 3
    assert out.get("deposit_address") == "JSignupRetryAddr000000000000001"
    saved = json.loads(addr_path.read_text(encoding="utf-8"))
    assert "signup_user_retry" in saved


def test_provision_surfaces_failure(tmp_path, monkeypatch):
    from backend.services import mn2_onchain_wallet as onchain
    from backend.services import mn2_wallet_service as ws

    addr_path = tmp_path / "mn2_user_addresses.json"
    addr_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(ws, "_addresses_path", lambda: str(addr_path))
    # Force onchain mode so RPC failure does not fall back to LGR.
    monkeypatch.setattr(ws, "_wallet_mode", lambda: "onchain")
    monkeypatch.setattr(
        ws,
        "generate_daemon_address",
        lambda: {
            "success": False,
            "error": "rpc_unconfigured",
            "code": "rpc_unconfigured",
            "deposit_address": None,
        },
    )
    monkeypatch.setattr(onchain, "_try_label", lambda address, user_id: {"labeled": False, "method": None})

    out = onchain.provision_signup_deposit_address("signup_user_fail", attempts=2)
    assert out.get("success") is False
    assert out.get("assigned") is False
    assert out.get("retryable") is True
    assert out.get("attempts") == 2
    assert out.get("deposit_address") is None
    assert "rpc" in str(out.get("error") or "").lower() or out.get("code")


def test_repair_missing_only_when_absent(tmp_path, monkeypatch):
    from backend.services import mn2_onchain_wallet as onchain
    from backend.services import mn2_wallet_service as ws

    addr_path = tmp_path / "mn2_user_addresses.json"
    uid = "signup_user_existing"
    addr_path.write_text(
        json.dumps({uid: {"primary": "JAlreadyThere00000000000000001", "addresses": [
            {"label": "primary", "address": "JAlreadyThere00000000000000001", "type": "core", "active": True}
        ]}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ws, "_addresses_path", lambda: str(addr_path))
    monkeypatch.setattr(
        ws,
        "generate_daemon_address",
        lambda: (_ for _ in ()).throw(AssertionError("should not mint")),
    )

    out = onchain.repair_missing_deposit_address(uid)
    assert out.get("success") is True
    assert out.get("repaired") is False
    assert out.get("deposit_address") == "JAlreadyThere00000000000000001"


def test_identify_new_user_includes_mn2_wallet(tmp_path, monkeypatch):
    from backend.services import user_identification as uid_mod
    from backend.services.user_identification import UserIdentification

    service = UserIdentification(base_dir=str(tmp_path))
    monkeypatch.setattr(
        uid_mod,
        "provision_signup_deposit_address",
        lambda user_id, attempts=3: {
            "success": True,
            "assigned": True,
            "deposit_address": "JIdentifyNew000000000000000001",
            "ledger_only": False,
            "attempts": 1,
            "code": "chain_address",
        },
    )
    monkeypatch.setattr(service, "_find_existing_user", lambda identifiers: None)
    monkeypatch.setattr(service, "_generate_user_id", lambda identifiers: "user_identify_new_1")
    monkeypatch.setattr(service, "_save_identifier_mapping", lambda uid, identifiers: None)
    monkeypatch.setattr(
        service,
        "_extract_identifiers",
        lambda request_obj: {"ip_address": "127.0.0.1", "user_agent": "test"},
    )

    out = service.identify_or_create_user(request_obj=object())
    assert out.get("new_user") is True
    assert out.get("mn2_deposit_address") == "JIdentifyNew000000000000000001"
    assert out.get("mn2_wallet", {}).get("assigned") is True
