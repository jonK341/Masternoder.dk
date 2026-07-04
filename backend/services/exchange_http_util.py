"""HTTP helpers for exchange REST clients (IPv4-only outbound when configured)."""
from __future__ import annotations

import os
import socket

_hooked = False


def force_ipv4_outbound_if_configured() -> None:
    """Use IPv4 only for urllib3/requests when EXCHANGE_FORCE_IPV4=1."""
    global _hooked
    if _hooked:
        return
    flag = os.environ.get("EXCHANGE_FORCE_IPV4", "").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return
    try:
        import urllib3.util.connection as urllib3_connection

        urllib3_connection.allowed_gai_family = lambda: socket.AF_INET
        _hooked = True
    except Exception:
        pass
