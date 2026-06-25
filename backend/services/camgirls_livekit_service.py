"""LiveKit voice status stub for camgirls studio."""
from __future__ import annotations

import os
from typing import Any, Dict


def public_status() -> Dict[str, Any]:
    configured = bool(os.environ.get("LIVEKIT_URL") and os.environ.get("LIVEKIT_API_KEY"))
    return {
        "configured": configured,
        "mode": "live" if configured else "stub",
        "note": "Voice live when LIVEKIT_URL and LIVEKIT_API_KEY are set.",
    }
