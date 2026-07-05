#!/usr/bin/env python3
"""Lightweight dev server for the unified Forum hub.

Serves the forum page + static assets and registers only the forum blueprint,
so the forum can be developed and tested without booting the full platform app.

    python3 scripts/forum_dev_server.py [--port 5055]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, send_from_directory

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SITE = os.path.join(_BASE, "site")


def create_dev_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=os.path.join(_SITE, "static"),
        static_url_path="/static",
    )
    app.config["TESTING"] = False

    from backend.routes.forum_routes import forum_bp
    app.register_blueprint(forum_bp)

    @app.route("/")
    def _root():
        return send_from_directory(os.path.join(_SITE, "pages", "forum"), "index.html")

    @app.route("/forum/")
    @app.route("/forum")
    def _forum():
        return send_from_directory(os.path.join(_SITE, "pages", "forum"), "index.html")

    @app.route("/api/health")
    def _health():
        return {"success": True, "service": "forum-dev"}

    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5055)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    app = create_dev_app()
    print(f"Forum dev server → http://{args.host}:{args.port}/forum/")
    app.run(host=args.host, port=args.port, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
