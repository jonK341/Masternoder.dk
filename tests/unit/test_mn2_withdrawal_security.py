"""Tests for MN2 withdrawal security (whitelist + TOTP)."""
import os
import tempfile

import pytest

from backend.services import mn2_withdrawal_security as sec


@pytest.fixture(autouse=True)
def isolated_security_store(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    monkeypatch.setattr(sec, "_PATH", path)
    yield
    try:
        os.remove(path)
    except OSError:
        pass


def test_whitelist_add_and_gate():
    sec.add_whitelist_address("user_a", "addr1")
    assert sec.is_address_whitelisted("user_a", "addr1")
    blocked = sec.check_whitelist_gate("user_a", "addr2", required=True)
    assert blocked["allowed"] is False
    allowed = sec.check_whitelist_gate("user_a", "addr1", required=True)
    assert allowed["allowed"] is True


def test_totp_setup_enable_verify():
    setup = sec.setup_totp("user_b")
    assert setup["success"]
    secret = setup["secret"]
    code = sec.totp_code(secret)
    enable = sec.enable_totp("user_b", code)
    assert enable["success"]
    gate_ok = sec.check_totp_gate("user_b", code)
    assert gate_ok["allowed"] is True
    gate_bad = sec.check_totp_gate("user_b", "000000")
    assert gate_bad["allowed"] is False
