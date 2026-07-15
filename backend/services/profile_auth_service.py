"""
Profile auth — re-exports from profile_access_service for backward compatibility.
"""
from backend.services.profile_access_service import (  # noqa: F401
    check_profile_write_access,
    is_owner as is_session_bound,
    require_profile_owner,
    require_profile_read,
    sanitize_display_payload,
    sanitize_profile_record,
    sanitize_scraped_info,
    session_user_id,
    validate_profile_update,
)
