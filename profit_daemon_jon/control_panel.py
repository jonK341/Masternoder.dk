#!/usr/bin/env python3
"""Local 127.0.0.1 browser control for The Profit Daemon Jon.

Started automatically with the daemon (unless --no-control). Lets operators
enable/disable exchanges, add a venue by reusing a known ticker parser, and
see companion service health (Redis, Prometheus, Grafana, vault, WS feed).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_PORT = int(os.environ.get("PROFIT_DAEMON_TRAY_PORT") or os.environ.get("PROFIT_DAEMON_CONTROL_PORT") or 8787)
_SERVER: Optional[ThreadingHTTPServer] = None
_THREAD: Optional[threading.Thread] = None


def _control_bind() -> tuple[str, int]:
    from backend.services.exchange_registry_service import load_registry
    ctrl = (load_registry().get("control") or {})
    host = str(ctrl.get("host") or "127.0.0.1")
    # Always loopback unless explicitly overridden via env for advanced ops.
    if os.environ.get("PROFIT_DAEMON_CONTROL_BIND", "").strip():
        host = os.environ["PROFIT_DAEMON_CONTROL_BIND"].strip()
    else:
        host = "127.0.0.1"
    port = int(os.environ.get("PROFIT_DAEMON_CONTROL_PORT") or ctrl.get("port") or DEFAULT_PORT)
    return host, port


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: Any) -> None:
    body = json.dumps(payload, default=str).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter
        return

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/api/status":
            from backend.services.exchange_registry_service import control_snapshot
            return _json_response(self, 200, control_snapshot())
        if path == "/api/exchanges":
            from backend.services.exchange_registry_service import list_exchanges, known_parsers
            return _json_response(self, 200, {
                "success": True,
                "exchanges": list_exchanges(),
                "parsers": known_parsers(),
            })
        if path == "/api/services":
            from backend.services.exchange_registry_service import companion_services_status
            return _json_response(self, 200, companion_services_status())
        if path == "/api/sales":
            qs = parse_qs(parsed.query)
            hours = float((qs.get("hours") or ["3"])[0])
            from scripts.exchange_sales_report import build_report
            return _json_response(self, 200, build_report(hours))
        if path == "/api/health":
            return _json_response(self, 200, {"status": "healthy", "brand": "The Profit Daemon Jon"})
        if path != "/":
            return _json_response(self, 404, {"error": "not_found"})
        body = _HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        data = _read_json_body(self)
        if path == "/api/exchanges/enable":
            from backend.services.exchange_registry_service import set_exchange_enabled
            out = set_exchange_enabled(str(data.get("id") or ""), bool(data.get("enabled")))
            return _json_response(self, 200 if out.get("success") else 400, out)
        if path == "/api/exchanges/ladder":
            from backend.services.exchange_registry_service import set_ladder_participation
            out = set_ladder_participation(str(data.get("id") or ""), bool(data.get("ladder")))
            return _json_response(self, 200 if out.get("success") else 400, out)
        if path == "/api/exchanges/add":
            from backend.services.exchange_registry_service import add_exchange
            out = add_exchange(data)
            return _json_response(self, 200 if out.get("success") else 400, out)
        return _json_response(self, 404, {"error": "not_found"})


_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>The Profit Daemon Jon — Control</title>
  <style>
    :root {
      --bg0: #0b1220;
      --bg1: #121a2b;
      --ink: #e8eef8;
      --muted: #9aa8bf;
      --line: #243149;
      --accent: #3ecf8e;
      --warn: #f0b429;
      --bad: #f07178;
      --good: #3ecf8e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; color: var(--ink);
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background:
        radial-gradient(1200px 600px at 10% -10%, #1a3a2a 0%, transparent 55%),
        radial-gradient(900px 500px at 100% 0%, #1a2740 0%, transparent 50%),
        linear-gradient(180deg, #0b1220, #0e1626 40%, #0b1220);
      min-height: 100vh;
    }
    header {
      padding: 1.5rem 1.75rem 0.5rem;
      border-bottom: 1px solid var(--line);
      background: rgba(11,18,32,.72);
      backdrop-filter: blur(8px);
      position: sticky; top: 0; z-index: 2;
    }
    h1 { margin: 0; font-size: 1.45rem; letter-spacing: .02em; }
    h1 span { color: var(--accent); }
    .sub { color: var(--muted); margin-top: .35rem; font-size: .92rem; }
    main { padding: 1.25rem 1.75rem 3rem; display: grid; gap: 1.25rem; }
    @media (min-width: 980px) {
      main { grid-template-columns: 1.4fr 1fr; align-items: start; }
      .full { grid-column: 1 / -1; }
    }
    section {
      background: rgba(18,26,43,.88);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 1rem 1.1rem 1.15rem;
    }
    h2 { margin: 0 0 .85rem; font-size: 1.05rem; font-weight: 600; }
    .grid { display: grid; gap: .55rem; }
    .row {
      display: grid; grid-template-columns: 1.2fr .7fr .7fr auto auto;
      gap: .5rem; align-items: center;
      padding: .55rem .65rem; border-radius: 10px; background: #0f1726;
      border: 1px solid #1c2740;
    }
    @media (max-width: 720px) {
      .row { grid-template-columns: 1fr 1fr; }
    }
    .name { font-weight: 600; }
    .meta { color: var(--muted); font-size: .82rem; }
    .pill {
      display: inline-block; padding: .15rem .5rem; border-radius: 999px;
      font-size: .75rem; border: 1px solid var(--line); color: var(--muted);
    }
    .pill.on { color: #0b1220; background: var(--good); border-color: transparent; }
    .pill.off { color: var(--bad); border-color: #5a2a33; }
    button, .btn {
      appearance: none; border: 1px solid var(--line); background: #182338;
      color: var(--ink); border-radius: 8px; padding: .4rem .7rem; cursor: pointer;
      font: inherit; font-size: .85rem;
    }
    button:hover { border-color: #3a4f73; }
    button.primary { background: var(--accent); color: #062016; border-color: transparent; font-weight: 600; }
    form.add { display: grid; gap: .55rem; }
    form.add .fields { display: grid; gap: .5rem; grid-template-columns: 1fr 1fr; }
    @media (max-width: 720px) { form.add .fields { grid-template-columns: 1fr; } }
    label { display: grid; gap: .25rem; font-size: .8rem; color: var(--muted); }
    input, select {
      background: #0c1422; color: var(--ink); border: 1px solid var(--line);
      border-radius: 8px; padding: .45rem .55rem; font: inherit;
    }
    .svc {
      display: flex; justify-content: space-between; gap: 1rem; align-items: baseline;
      padding: .55rem 0; border-bottom: 1px solid #1a2438;
    }
    .svc:last-child { border-bottom: 0; }
    .ok { color: var(--good); } .bad { color: var(--bad); } .warn { color: var(--warn); }
    .stats { display: flex; flex-wrap: wrap; gap: .75rem; }
    .stat { min-width: 8rem; padding: .7rem .85rem; background: #0f1726; border-radius: 10px; border: 1px solid #1c2740; }
    .stat b { display: block; font-size: 1.15rem; }
    .stat span { color: var(--muted); font-size: .8rem; }
    .hint { color: var(--muted); font-size: .85rem; line-height: 1.4; }
    .err { color: var(--bad); font-size: .85rem; min-height: 1.1em; }
  </style>
</head>
<body>
  <header>
    <h1>The <span>Profit Daemon Jon</span></h1>
    <div class="sub">Local control · bound to 127.0.0.1 · refresh every 15s</div>
  </header>
  <main>
    <section class="full">
      <h2>Status</h2>
      <div class="stats" id="stats"></div>
    </section>
    <section>
      <h2>Exchanges</h2>
      <p class="hint">Toggle venues used by the daemon. Ladder participation is separate — only enable ladder when private order APIs are wired.</p>
      <div class="grid" id="exchanges"></div>
    </section>
    <section>
      <h2>Add exchange</h2>
      <p class="hint">Reuse a known ticker <code>parser</code> (Binance-shaped, OKX-shaped, …). Public market data works immediately; live trading needs a matching auth mode.</p>
      <form class="add" id="add-form">
        <div class="fields">
          <label>Id <input name="id" required placeholder="mexc" /></label>
          <label>Name <input name="name" placeholder="MEXC" /></label>
          <label>Quote <input name="quote" value="USDT" /></label>
          <label>Parser
            <select name="parser" id="parser"></select>
          </label>
          <label>Pair template <input name="pair_template" value="{base}{quote}" /></label>
          <label>Fee taker bps <input name="fee_taker_bps" type="number" value="20" step="1" /></label>
        </div>
        <label>Ticker URL (must include {pair})
          <input name="ticker_url" required placeholder="https://api.example.com/ticker?symbol={pair}" />
        </label>
        <div class="fields">
          <label>Auth (optional)
            <select name="auth" id="auth"><option value="">— public only —</option></select>
          </label>
          <label>API base (optional) <input name="api_base" placeholder="https://api.example.com" /></label>
        </div>
        <label><input type="checkbox" name="enabled" checked /> Enabled for public prices / arb scan</label>
        <label><input type="checkbox" name="ladder" /> Include in ladder maker</label>
        <button class="primary" type="submit">Add exchange</button>
        <div class="err" id="add-err"></div>
      </form>
    </section>
    <section class="full">
      <h2>Companion services</h2>
      <p class="hint">Best stack for this daemon: Redis bus, Prometheus (:9108), Grafana, encrypted vault, Binance WS feed, and this local control. Docker Compose can bring Redis/Prometheus/Grafana up together.</p>
      <div id="services"></div>
    </section>
  </main>
  <script>
    async function jget(url) {
      const r = await fetch(url, {cache:'no-store'});
      return r.json();
    }
    async function jpost(url, body) {
      const r = await fetch(url, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      return r.json();
    }
    function esc(s) {
      return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }
    function renderStats(snap) {
      const tech = snap.tech || {};
      const sales = (snap.sales_3h || {}).totals || {};
      const mode = snap.mode || {};
      const svc = snap.services || {};
      document.getElementById('stats').innerHTML = `
        <div class="stat"><b>${mode.live ? 'LIVE' : 'PAPER'}</b><span>mode · ${esc(mode.profile||'')}</span></div>
        <div class="stat"><b>${esc(tech.ok||0)}/${esc(tech.total||0)}</b><span>top-25 tech OK</span></div>
        <div class="stat"><b>${esc(sales.fills||0)}</b><span>fills · 3h</span></div>
        <div class="stat"><b>$${esc(sales.realized_pnl_usd||0)}</b><span>realized · 3h</span></div>
        <div class="stat"><b>${esc(snap.heartbeat_age_sec ?? 'n/a')}s</b><span>heartbeat age</span></div>
        <div class="stat"><b>${esc(svc.ok||0)}/${esc(svc.total||0)}</b><span>services OK</span></div>
      `;
    }
    function renderExchanges(rows) {
      const box = document.getElementById('exchanges');
      box.innerHTML = rows.map(r => `
        <div class="row">
          <div>
            <div class="name">${esc(r.name||r.id)} <span class="meta">(${esc(r.id)})</span></div>
            <div class="meta">quote ${esc(r.quote)} · parser ${esc(r.parser||r.id)} · fee ${esc(r.fee_taker_bps)}bps</div>
          </div>
          <div><span class="pill ${r.enabled?'on':'off'}">${r.enabled?'enabled':'disabled'}</span></div>
          <div><span class="pill ${r.ladder?'on':'off'}">ladder ${r.ladder?'on':'off'}</span></div>
          <button data-act="enable" data-id="${esc(r.id)}" data-val="${r.enabled?0:1}">${r.enabled?'Disable':'Enable'}</button>
          <button data-act="ladder" data-id="${esc(r.id)}" data-val="${r.ladder?0:1}">Ladder ${r.ladder?'off':'on'}</button>
        </div>
      `).join('') || '<div class="hint">No exchanges in registry.</div>';
      box.querySelectorAll('button[data-act]').forEach(btn => {
        btn.onclick = async () => {
          const id = btn.getAttribute('data-id');
          const val = btn.getAttribute('data-val') === '1';
          const act = btn.getAttribute('data-act');
          if (act === 'enable') await jpost('/api/exchanges/enable', {id, enabled: val});
          if (act === 'ladder') await jpost('/api/exchanges/ladder', {id, ladder: val});
          refresh();
        };
      });
    }
    function renderServices(payload) {
      const box = document.getElementById('services');
      const rows = (payload && payload.services) || [];
      box.innerHTML = rows.map(s => {
        const st = s.status || {};
        const cls = st.ok ? 'ok' : 'bad';
        return `<div class="svc"><div><b>${esc(s.title||s.id)}</b><div class="meta">${esc(s.why||'')}</div></div>
          <div class="${cls}">${st.ok?'OK':'DOWN'} · ${esc(st.detail||'')}</div></div>`;
      }).join('');
    }
    async function refresh() {
      const snap = await jget('/api/status');
      renderStats(snap);
      renderExchanges(snap.exchanges || []);
      renderServices(snap.services || {});
      const parsers = snap.parsers || [];
      const auth = snap.auth_modes || [];
      const psel = document.getElementById('parser');
      const asel = document.getElementById('auth');
      if (psel.options.length <= 1) {
        psel.innerHTML = parsers.map(p => `<option value="${esc(p)}">${esc(p)}</option>`).join('');
        if ([...psel.options].some(o => o.value === 'binance')) psel.value = 'binance';
      }
      if (asel.options.length <= 1) {
        asel.innerHTML = '<option value="">— public only —</option>' +
          auth.map(a => `<option value="${esc(a)}">${esc(a)}</option>`).join('');
      }
    }
    document.getElementById('add-form').onsubmit = async (ev) => {
      ev.preventDefault();
      const fd = new FormData(ev.target);
      const body = Object.fromEntries(fd.entries());
      body.enabled = fd.get('enabled') === 'on';
      body.ladder = fd.get('ladder') === 'on';
      body.fee_taker_bps = Number(body.fee_taker_bps || 20);
      const out = await jpost('/api/exchanges/add', body);
      const err = document.getElementById('add-err');
      if (!out.success) {
        err.textContent = out.error + (out.hint ? ' — ' + out.hint : '');
        return;
      }
      err.textContent = '';
      ev.target.reset();
      refresh();
    };
    refresh();
    setInterval(refresh, 15000);
  </script>
</body>
</html>
"""


def start_background(*, open_browser: bool = True) -> Dict[str, Any]:
    """Start the control panel in a daemon thread (idempotent)."""
    global _SERVER, _THREAD
    if _THREAD and _THREAD.is_alive() and _SERVER is not None:
        host, port = _SERVER.server_address[0], _SERVER.server_address[1]
        return {"success": True, "already_running": True, "url": f"http://{host}:{port}/"}
    host, port = _control_bind()
    server = None
    last_err: Optional[BaseException] = None
    for candidate in (port, port + 1, port + 2, port + 3, 0):
        try:
            server = ThreadingHTTPServer((host, int(candidate)), Handler)
            port = server.server_address[1]
            break
        except OSError as exc:
            last_err = exc
            server = None
            continue
    if server is None:
        return {"success": False, "error": str(last_err), "host": host, "port": port}
    _SERVER = server

    def _serve() -> None:
        try:
            server.serve_forever(poll_interval=0.5)
        except Exception:
            pass

    _THREAD = threading.Thread(target=_serve, name="pdj-control", daemon=True)
    _THREAD.start()
    url = f"http://{host}:{port}/"
    print(f"[control] The Profit Daemon Jon → {url}")
    if open_browser and os.environ.get("PROFIT_DAEMON_OPEN_BROWSER", "1").strip() not in ("0", "false", "no"):
        try:
            webbrowser.open(url)
        except Exception:
            pass
    return {"success": True, "url": url, "host": host, "port": port}


def main() -> int:
    out = start_background(open_browser=True)
    if not out.get("success"):
        print(f"[control] failed: {out}")
        return 1
    print("[control] running (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        if _SERVER is not None:
            _SERVER.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
