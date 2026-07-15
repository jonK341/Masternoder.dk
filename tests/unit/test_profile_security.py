"""
Profile security — session ownership, sanitization, and blocked updates.
Run: pytest tests/unit/test_profile_security.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


@pytest.mark.slow
def test_require_profile_owner_without_session():
    from backend.services.profile_access_service import require_profile_owner

    with patch("backend.services.profile_access_service.session_user_id", return_value=None):
        err = require_profile_owner("alice")
        assert err is not None
        assert err[1] == 401


@pytest.mark.slow
def test_require_profile_owner_session_mismatch():
    from backend.services.profile_access_service import require_profile_owner

    with patch("backend.services.profile_access_service.session_user_id", return_value="bob"):
        err = require_profile_owner("alice")
        assert err is not None
        assert err[1] == 403


@pytest.mark.slow
def test_require_profile_owner_allows_match():
    from backend.services.profile_access_service import require_profile_owner

    with patch("backend.services.profile_access_service.session_user_id", return_value="alice"):
        assert require_profile_owner("alice") is None


@pytest.mark.slow
def test_validate_profile_update_blocks_scraped_info():
    from backend.services.profile_access_service import validate_profile_update

    err = validate_profile_update({"scraped_info": {"ip_address": "1.2.3.4"}})
    assert err is not None
    assert "protected" in err.lower()


@pytest.mark.slow
def test_sanitize_scraped_info_strips_ip():
    from backend.services.profile_access_service import sanitize_scraped_info

    raw = {"location": {"ip_address": "203.0.113.5", "city": "Copenhagen"}}
    clean = sanitize_scraped_info(raw)
    assert "ip_address" not in str(clean)
    assert clean.get("location", {}).get("city") == "Copenhagen"


@pytest.mark.slow
def test_sanitize_display_payload_hides_private_sections():
    from backend.services.profile_access_service import sanitize_display_payload

    payload = {
        "success": True,
        "profile": {"user_id": "x", "scraped_info": {"browser": {}}, "preferences": {"bio": "hi"}},
        "shop_summary": {"purchases": []},
        "password_status": {"has_password": True},
    }
    clean = sanitize_display_payload(payload, is_owner_view=False)
    assert "shop_summary" not in clean
    assert "password_status" not in clean
    assert "scraped_info" not in (clean.get("profile") or {})


@pytest.mark.slow
def test_check_profile_write_access_default_guest():
    from backend.services.profile_access_service import check_profile_write_access

    with patch("backend.services.profile_access_service.session_user_id", return_value=None):
        assert check_profile_write_access("default_user") is None


@pytest.mark.slow
def test_profile_services_health():
    from backend.services.profile_access_service import profile_services_health

    result = profile_services_health()
    assert "checks" in result
    assert "onboarding_storage" in result["checks"]
