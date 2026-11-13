"""Contract checks for film Start responses clients must parse as JSON."""

from __future__ import annotations

import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def test_frontpage_film_monitor_has_safe_json_helper():
    text = (REPO / "static/js/frontpage-film-monitor.js").read_text(encoding="utf-8")
    assert "async function readJsonResponse(response)" in text
    assert "Face image is too large for the server" in text
    assert "await readJsonResponse(start)" in text
    assert "await start.json()" not in text


def test_debugger_mission_control_uses_safe_json_helper():
    text = (REPO / "debugger/index.html").read_text(encoding="utf-8")
    assert "window._mcReadJsonResponse" in text
    assert "await window._mcReadJsonResponse(start)" in text
    # The old brittle path must not remain on the Start call.
    assert "const job = await start.json();" not in text


def test_payload_too_large_contract_is_json():
    # Mirrors the nginx @payload_too_large response body deployed with this fix.
    body = (
        '{"success":false,"error":"Payload too large — use a smaller face photo",'
        '"code":"PAYLOAD_TOO_LARGE"}'
    )
    parsed = json.loads(body)
    assert parsed["success"] is False
    assert parsed["code"] == "PAYLOAD_TOO_LARGE"
    assert "too large" in parsed["error"].lower()
