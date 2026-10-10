#!/usr/bin/env python3
"""Prod url_map probe for monetization streams routes."""
from __future__ import annotations

import os
import sys

os.chdir("/var/www/html")
sys.path.insert(0, "/var/www/html")

from wsgi import application  # noqa: E402
from flask import request  # noqa: E402

paths = (
    "/api/monetization/config",
    "/api/monetization/streams/v1/ping",
    "/api/monetization/top-25",
)

for path in paths:
    with application.test_request_context(path):
        rule, _ = application.url_map.bind_to_environ(request.environ).match(return_rule=True)
        vf = application.view_functions.get(rule.endpoint)
        try:
            rv = vf()
            status = rv[1] if isinstance(rv, tuple) and len(rv) > 1 else getattr(rv, "status_code", "?")
            print(path, "->", rule.endpoint, "status", status)
        except Exception as exc:
            print(path, "->", rule.endpoint, "EXC", exc)
