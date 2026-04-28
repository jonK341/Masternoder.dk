"""
API monitor: GET /api/ serves a table dashboard of all API endpoints (status, response times).
Endpoints list from Flask url_map; probes run client-side in batches to avoid slow load.
"""
from flask import Blueprint, request, render_template_string, jsonify, current_app
import urllib.request
import urllib.error
import json
import time
from datetime import datetime

api_monitor_bp = Blueprint("api_monitor", __name__)

# Fallback if url_map not available
MONITOR_ENDPOINTS_FALLBACK = [
    "/api/health", "/api/version", "/api/points/all", "/api/stats/summary",
    "/api/trophies/list", "/api/frontpage/init", "/api/battle/stats", "/api/mn2/balance",
    "/api/game/hunters/battle-bridge-snapshot",
    "/api/lab/chapter2-research",
    "/api/lab/technologies",
    "/api/lab/progression",
    "/api/lab/v2/status",
    "/api/lab/explore",
]


def _probe(url: str, timeout: float = 8) -> dict:
    """Probe one URL; return {ok, status_code, time_ms, error, body_preview}."""
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "API-Monitor/1"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            elapsed_ms = (time.perf_counter() - start) * 1000
            body = r.read()
            try:
                preview = json.dumps(json.loads(body.decode())[:1])[:120] if body else ""
            except Exception:
                preview = (body[:80].decode(errors="replace") + "…") if body else ""
            return {
                "ok": True,
                "status_code": r.status,
                "time_ms": round(elapsed_ms, 1),
                "error": None,
                "body_preview": preview,
            }
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "ok": False,
            "status_code": e.code,
            "time_ms": round(elapsed_ms, 1),
            "error": str(e.reason) if e.reason else str(e),
            "body_preview": None,
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "ok": False,
            "status_code": None,
            "time_ms": round(elapsed_ms, 1),
            "error": str(e),
            "body_preview": None,
        }


MONITOR_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>API Monitor — masternoder.dk</title>
  <style>
    :root { --bg: #0d0d0f; --card: #16161a; --text: #e4e4e7; --muted: #71717a; --ok: #22c55e; --err: #ef4444; --accent: #3b82f6; --row: #111113; --border: #252528; }
    * { box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 1.25rem; line-height: 1.45; font-size: 14px; }
    .header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1.25rem; }
    h1 { font-size: 1.5rem; font-weight: 600; margin: 0; letter-spacing: -0.02em; }
    .sub { color: var(--muted); font-size: 0.875rem; margin-top: 0.2rem; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.75rem; margin-bottom: 1.25rem; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 0.9rem 1rem; text-align: center; }
    .card .val { font-size: 1.5rem; font-weight: 700; line-height: 1.2; }
    .card .lbl { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; margin-top: 0.25rem; }
    .card.ok .val { color: var(--ok); }
    .card.fail .val { color: var(--err); }
    .card.skip .val { color: var(--muted); }
    .card.total .val { color: var(--text); }
    .card.ts .val { font-size: 0.9rem; font-weight: 500; color: var(--muted); }
    .actions { display: flex; align-items: center; gap: 0.5rem; }
    .btn { padding: 0.45rem 1rem; background: var(--accent); color: #fff; border: none; border-radius: 8px; cursor: pointer; font-size: 0.875rem; font-weight: 500; }
    .btn:hover { filter: brightness(1.08); }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }
    .wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; background: var(--card); }
    table { width: 100%; border-collapse: collapse; min-width: 520px; }
    th { text-align: left; padding: 0.6rem 0.85rem; background: #1c1c1f; color: var(--muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.03em; border-bottom: 1px solid var(--border); }
    td { padding: 0.5rem 0.85rem; border-bottom: 1px solid var(--border); font-size: 0.875rem; }
    tr:last-child td { border-bottom: none; }
    tr:hover { background: rgba(255,255,255,0.02); }
    .path { word-break: break-all; font-family: ui-monospace, monospace; font-size: 0.8rem; }
    .badge { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
    .badge.ok { background: rgba(34,197,94,0.15); color: var(--ok); }
    .badge.fail { background: rgba(239,68,68,0.15); color: var(--err); }
    .badge.pending { background: rgba(113,113,122,0.2); color: var(--muted); }
    .code-ok { color: var(--ok); font-variant-numeric: tabular-nums; }
    .code-fail { color: var(--err); font-variant-numeric: tabular-nums; }
    .time { font-variant-numeric: tabular-nums; color: var(--muted); }
    #loading { color: var(--muted); font-size: 0.875rem; padding: 0.85rem 1rem; }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>API Monitor</h1>
      <p class="sub">masternoder.dk · <a href="{{ base }}/api/">refresh</a></p>
    </div>
    <div class="actions">
      <button class="btn" id="btn-run" onclick="runProbes()">Probe all</button>
    </div>
  </div>
  <div class="cards">
    <div class="card ok"><div class="val" id="ok-count">0</div><div class="lbl">OK</div></div>
    <div class="card fail"><div class="val" id="fail-count">0</div><div class="lbl">Fail</div></div>
    <div class="card skip"><div class="val" id="skip-count">0</div><div class="lbl">Skip</div></div>
    <div class="card total"><div class="val" id="total-count">0</div><div class="lbl">Total</div></div>
    <div class="card ts"><div class="val" id="ts">—</div><div class="lbl">Last check</div></div>
  </div>
  <div class="wrap">
    <table>
      <thead><tr><th>Endpoint</th><th>Status</th><th>Code</th><th>Time</th></tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
  <p id="loading">Loading endpoints…</p>
  <script>
    var base = window.location.origin || '';
    var BATCH = 6;
    var rows = [];
    function el(id) { return document.getElementById(id); }
    var FALLBACK_ENDPOINTS = ['/api/health','/api/version','/api/points/all','/api/stats/summary','/api/trophies/list','/api/frontpage/init','/api/battle/stats','/api/mn2/balance','/api/mn2/deposit-address','/api/shop/currency','/api/game/hunters/battle-bridge-snapshot','/api/lab/chapter2-research','/api/lab/technologies','/api/lab/progression','/api/lab/v2/status','/api/lab/overview','/api/lab/research-log','/api/lab/share-card','/api/lab/projects','/api/lab/roundtable/messages','/api/lab/explore'];
    function fetchEndpoints() {
      return fetch(base + '/api/monitor/endpoints', { headers: { 'Accept': 'application/json' } })
        .then(function(r) {
          if (!r.ok) throw new Error('Endpoints request failed: ' + r.status);
          return r.json();
        })
        .then(function(data) {
          var eps = (data && data.endpoints) ? data.endpoints : [];
          if (eps.length === 0) eps = FALLBACK_ENDPOINTS.map(function(p) { return { path: p, methods: ['GET'], probe: true }; });
          return eps;
        });
    }
    function renderTable(endpoints) {
      const tbody = el('tbody');
      tbody.innerHTML = '';
      el('total-count').textContent = endpoints.length;
      rows = endpoints.map(ep => {
        const tr = document.createElement('tr');
        tr.innerHTML =
          '<td class="path">' + ep.path + '</td>' +
          '<td><span class="badge pending" data-status>—</span></td>' +
          '<td class="time" data-code>—</td>' +
          '<td class="time" data-time>—</td>';
        tbody.appendChild(tr);
        return { tr, path: ep.path, probe: ep.probe };
      });
      el('loading').textContent = rows.length + ' endpoints. Probing in batches…';
    }
    function runProbes() {
      el('loading').textContent = 'Probing…';
      el('btn-run').disabled = true;
      const toProbe = rows.filter(r => r.probe);
      const skip = rows.length - toProbe.length;
      el('skip-count').textContent = skip;
      let ok = 0, fail = 0;
      function runBatch(offset) {
        const batch = toProbe.slice(offset, offset + BATCH);
        if (batch.length === 0) {
          el('loading').textContent = 'Done.';
          el('btn-run').disabled = false;
          el('ts').textContent = new Date().toLocaleTimeString();
          return;
        }
        Promise.all(batch.map(r => {
          const start = performance.now();
          return fetch(base + r.path, { method: 'GET', headers: { 'Accept': 'application/json' } })
            .then(res => {
              const time = Math.round(performance.now() - start);
              const ok_ = res.status >= 200 && res.status < 400;
              if (ok_) ok++; else fail++;
              const statusEl = r.tr.querySelector('[data-status]');
              const codeEl = r.tr.querySelector('[data-code]');
              const timeEl = r.tr.querySelector('[data-time]');
              statusEl.textContent = ok_ ? 'OK' : 'Fail';
              statusEl.className = 'badge ' + (ok_ ? 'ok' : 'fail');
              codeEl.textContent = res.status;
              codeEl.className = ok_ ? 'code-ok' : 'code-fail';
              timeEl.textContent = time + ' ms';
              timeEl.className = 'time';
            })
            .catch(e => {
              fail++;
              r.tr.querySelector('[data-status]').textContent = 'Err';
              r.tr.querySelector('[data-status]').className = 'badge fail';
              r.tr.querySelector('[data-code]').textContent = '—';
              r.tr.querySelector('[data-code]').className = 'code-fail';
              r.tr.querySelector('[data-time]').textContent = (e.message || String(e)).slice(0, 18);
            })
            .finally(() => {
              el('ok-count').textContent = ok;
              el('fail-count').textContent = fail;
            });
        })).then(() => runBatch(offset + BATCH));
      }
      runBatch(0);
    }
    fetchEndpoints()
      .then(function(eps) { renderTable(eps); runProbes(); })
      .catch(function(e) { el('loading').textContent = 'Error: ' + (e.message || e); });
  </script>
</body>
</html>
"""


def _get_api_endpoints():
    """List all /api routes from Flask url_map. Returns list of {path, methods, probe}."""
    seen = set()
    out = []
    try:
        for rule in current_app.url_map.iter_rules():
            path = rule.rule
            if not path.startswith("/api") or path in ("/api", "/api/"):
                continue
            methods = [m for m in rule.methods if m not in ("HEAD", "OPTIONS")]
            if not methods:
                continue
            key = (path, tuple(sorted(methods)))
            if key in seen:
                continue
            seen.add(key)
            has_params = "<" in path
            out.append({
                "path": path,
                "methods": sorted(methods),
                "probe": not has_params and "GET" in methods,
            })
        out.sort(key=lambda x: x["path"])
        if not out:
            out = [{"path": p, "methods": ["GET"], "probe": True} for p in MONITOR_ENDPOINTS_FALLBACK]
    except Exception:
        out = [{"path": p, "methods": ["GET"], "probe": True} for p in MONITOR_ENDPOINTS_FALLBACK]
    return out


@api_monitor_bp.route("/api/monitor/endpoints", methods=["GET"])
def monitor_endpoints_json():
    """Return list of all API endpoints (path, methods, probe) for the table."""
    endpoints = _get_api_endpoints()
    return jsonify({"success": True, "endpoints": endpoints, "count": len(endpoints)})


@api_monitor_bp.route("/api/", methods=["GET"], strict_slashes=False)
@api_monitor_bp.route("/api", methods=["GET"])
def monitor_page():
    """Serve the API monitor table (HTML). Endpoints loaded via /api/monitor/endpoints."""
    base = request.url_root.rstrip("/")
    base_js = json.dumps(base)
    return render_template_string(
        MONITOR_HTML,
        base=base,
        base_js=base_js,
    ), 200, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store, max-age=0"}


@api_monitor_bp.route("/api/monitor/status", methods=["GET"])
def monitor_status_json():
    """Return JSON status of all probe-able endpoints (server-side)."""
    base = request.url_root.rstrip("/")
    endpoints = _get_api_endpoints()
    to_probe = [e["path"] for e in endpoints if e.get("probe")]
    results = []
    for path in to_probe:
        r = _probe(base + path)
        results.append({"path": path, "url": base + path, **r})
    ok = sum(1 for r in results if r.get("ok"))
    return jsonify({
        "success": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "base": base,
        "ok": ok,
        "fail": len(results) - ok,
        "total": len(results),
        "endpoints": results,
    })
