"""Fast JSON helpers for the exchange bus / market feed.

Prefers ``orjson`` when installed; falls back to the stdlib ``json`` module so
paper ticks and hosts without the speed pack keep working.
"""
from __future__ import annotations

from typing import Any, Optional

_ORJSON = None
try:
    import orjson as _ORJSON  # type: ignore
except Exception:
    _ORJSON = None

import json as _json


def backend_name() -> str:
    return "orjson" if _ORJSON is not None else "json"


def dumps(value: Any) -> str:
    if _ORJSON is not None:
        return _ORJSON.dumps(value, default=str).decode("utf-8")
    return _json.dumps(value, default=str)


def loads(raw: Any) -> Any:
    if isinstance(raw, (bytes, bytearray)):
        if _ORJSON is not None:
            return _ORJSON.loads(raw)
        return _json.loads(raw.decode("utf-8"))
    text = str(raw or "")
    if _ORJSON is not None:
        return _ORJSON.loads(text)
    return _json.loads(text)


def try_loads(raw: Any, default: Optional[Any] = None) -> Any:
    try:
        return loads(raw)
    except Exception:
        return default
