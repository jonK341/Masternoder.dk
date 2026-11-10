#!/usr/bin/env python3
"""Desktop status server / tray helper for The Profit Daemon Jon.

Opens a tiny local status page (default http://127.0.0.1:8787). On systems with
pystray+Pillow installed it also shows a tray icon; otherwise browser-only.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PORT = int(os.environ.get("PROFIT_DAEMON_TRAY_PORT") or 8787)


def _snapshot() -> dict:
    out = {"brand": "The Profit Daemon Jon", "ts": time.time()}
    try:
        from backend.services.profit_daemon_jon_product_service import status_report, product_improvement_backlog
        out["tech"] = status_report()
        out["backlog"] = product_improvement_backlog()
    except Exception as exc:
        out["tech_error"] = str(exc)
    try:
        from scripts.exchange_sales_report import build_report
        out["sales_3h"] = build_report(3.0)
    except Exception as exc:
        out["sales_error"] = str(exc)
    try:
        from backend.services.profit_daemon_paths import heartbeat_path
        path = heartbeat_path()
        if os.path.isfile(path):
            out["heartbeat_age_sec"] = round(time.time() - os.path.getmtime(path), 1)
            out["heartbeat_path"] = path
    except Exception as exc:
        out["heartbeat_error"] = str(exc)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter
        return

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/api/status"):
            body = json.dumps(_snapshot(), default=str).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        snap = _snapshot()
        sales = (snap.get("sales_3h") or {}).get("totals") or {}
        tech = snap.get("tech") or {}
        html = f"""<!doctype html><html><head><meta charset=utf-8>
<title>The Profit Daemon Jon</title>
<meta http-equiv=refresh content=30>
<style>body{{font-family:system-ui;margin:2rem;background:#0f1419;color:#e7ecf3}}
a{{color:#7dd3fc}}.card{{background:#1a2332;padding:1rem 1.25rem;border-radius:12px;margin:.75rem 0}}</style></head>
<body><h1>The Profit Daemon Jon</h1>
<div class=card><b>Tech</b>: {tech.get('ok',0)}/{tech.get('total',0)} OK</div>
<div class=card><b>Sales 3h</b>: fills {sales.get('fills',0)} · notional ${sales.get('notional_usd',0)} · pnl ${sales.get('realized_pnl_usd',0)}</div>
<div class=card><b>Heartbeat age</b>: {snap.get('heartbeat_age_sec','n/a')}s</div>
<p><a href=/api/status>JSON status</a></p></body></html>"""
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _maybe_tray(server: ThreadingHTTPServer) -> None:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        print(f"[tray] browser status at http://127.0.0.1:{PORT}/ (install pystray+Pillow for icon)")
        return
    img = Image.new("RGB", (64, 64), "#0f1419")
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill="#22c55e")

    def on_open(_icon, _item):
        webbrowser.open(f"http://127.0.0.1:{PORT}/")

    def on_quit(icon, _item):
        icon.stop()
        server.shutdown()

    menu = pystray.Menu(
        pystray.MenuItem("Open status", on_open, default=True),
        pystray.MenuItem("Quit", on_quit),
    )
    icon = pystray.Icon("profit_daemon_jon", img, "The Profit Daemon Jon", menu)
    threading.Thread(target=icon.run, daemon=True).start()


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    _maybe_tray(server)
    print(f"[tray] The Profit Daemon Jon status → http://127.0.0.1:{PORT}/")
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
    except Exception:
        pass
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
