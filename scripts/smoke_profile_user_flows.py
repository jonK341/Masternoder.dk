#!/usr/bin/env python3
"""
Smoke checks for /profile, /user, and account-control APIs.

Usage:
  set PLATFORM_BASE_URL=http://127.0.0.1:5000
  python scripts/smoke_profile_user_flows.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


BASE = os.environ.get("PLATFORM_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
TIMEOUT = float(os.environ.get("PLATFORM_CHECK_TIMEOUT", "20"))
USER_ID = os.environ.get("PROFILE_SMOKE_USER_ID", "profile_smoke_user")


def request(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[int, str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            body = res.read().decode("utf-8", errors="replace")
            parsed: Any = None
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = None
            return res.status, body, parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        parsed = None
        try:
            parsed = json.loads(body)
        except Exception:
            pass
        return exc.code, body, parsed


def check(name: str, ok: bool, detail: str = "") -> bool:
    marker = "[OK]" if ok else "[FAIL]"
    print(f"{marker} {name}{': ' + detail if detail else ''}")
    return ok


def main() -> int:
    print(f"Profile/user smoke against {BASE} as {USER_ID}")
    failures = 0

    status, html, _ = request("/profile")
    failures += not check(
        "/profile HTML",
        status == 200
        and "profile-completeness-card" in html
        and "data-hub-scroll=\"account\"" in html
        and "data-hub-scroll=\"wallet\"" in html
        and "applyFocusedProfileRoute" in html,
        f"status={status}",
    )

    status, html, _ = request("/user/")
    failures += not check(
        "/user HTML",
        status == 200
        and "Privacy controls" in html
        and "Account password" in html
        and "account-password-setup" in html
        and "/api/user/account-privacy" in html,
        f"status={status}",
    )

    status, _, data = request("/api/user/bind-session", "POST", {"user_id": USER_ID})
    failures += not check("bind session", status in (200, 201) and data and data.get("success"), f"status={status}")

    status, _, data = request(f"/api/user/identity?user_id={USER_ID}")
    failures += not check("identity payload", status == 200 and data and data.get("identity_model") and isinstance(data.get("progress_stores"), list), f"status={status}")

    status, _, data = request(f"/api/user/profile/{USER_ID}/aggregated")
    failures += not check("aggregated profile password status", status == 200 and data and data.get("password_status") is not None, f"status={status}")

    status, _, data = request(f"/api/user/account-privacy?user_id={USER_ID}")
    failures += not check("account privacy GET", status == 200 and data and data.get("privacy"), f"status={status}")

    status, _, data = request("/api/user/account-privacy", "POST", {
        "user_id": USER_ID,
        "profile_visibility": "private",
        "preferred_language": "en",
        "notifications_enabled": True,
        "email_notifications": False,
        "featured_achievement": "smoke",
        "pinned_activity": "smoke",
        "featured_agents": ["content_generator_agent"],
        "profile_theme": "dark",
    })
    failures += not check("account privacy POST", status == 200 and data and data.get("success"), f"status={status}")

    status, _, data = request(f"/api/user/linked-providers?user_id={USER_ID}")
    failures += not check("linked providers", status == 200 and data and isinstance(data.get("linked_providers"), list) and isinstance(data.get("revocation_supported"), bool), f"status={status}")

    status, _, data = request(f"/api/user/sessions?user_id={USER_ID}")
    failures += not check("persistent sessions", status == 200 and data and data.get("persistent") and isinstance(data.get("sessions"), list), f"status={status}")

    status, _, data = request("/api/user/sessions/revoke", "POST", {"user_id": USER_ID, "session_id": ""})
    failures += not check("session revoke rejects missing id", status == 400 and data and not data.get("success"), f"status={status}")

    status, _, data = request(f"/api/auth/password/status?user_id={USER_ID}")
    failures += not check("password status", status == 200 and data and data.get("unlock_rule") is not None and data.get("recovery") is not None and data.get("unlock_progress") is not None, f"status={status}")

    status, _, data = request(f"/api/auth/password/recovery/status?user_id={USER_ID}")
    failures += not check("password recovery status", status == 200 and data and "token_reset_supported" in data, f"status={status}")

    status, _, data = request("/api/auth/password/recovery/reset", "POST", {"user_id": USER_ID, "token": "", "password": "short"})
    failures += not check("password recovery reset rejects bad token", status == 400 and data and not data.get("success"), f"status={status}")

    status, _, data = request(f"/api/user/export?user_id={USER_ID}")
    failures += not check("export", status == 200 and data and data.get("success") and data.get("profile") is not None, f"status={status}")

    status, _, data = request("/api/user/delete", "POST", {"user_id": USER_ID, "confirm": "NO"})
    failures += not check("delete rejects bad confirmation", status == 400 and data and not data.get("success"), f"status={status}")

    if failures:
        print(f"\n{failures} smoke check(s) failed.")
        return 1
    print("\nAll profile/user smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
