"""
API monitor: GET /api/ serves a categorized dashboard of live API endpoints.
Endpoints come from the same catalog rules as API Lab; probes run client-side.
"""
from flask import Blueprint, request, render_template_string, jsonify, current_app
import urllib.request
import urllib.error
import json
import time
from datetime import datetime

from backend.routes.api_lab_routes import build_catalog, is_try_safe

api_monitor_bp = Blueprint("api_monitor", __name__)

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
  <title>API Monitor — MasterNoder</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #061018; --card: rgba(10, 22, 34, 0.92); --text: #e8f1f8; --muted: #8aa0b6;
      --ok: #2ad4a2; --err: #ef6b78; --accent: #2ad4a2; --border: #1e3348; --ink: #041018;
    }
    * { box-sizing: border-box; }
    body {
      font-family: "Outfit", system-ui, sans-serif;
      background:
        radial-gradient(900px 420px at 8% -8%, rgba(42, 212, 162, 0.16), transparent 55%),
        radial-gradient(700px 380px at 92% 0%, rgba(56, 140, 210, 0.14), transparent 50%),
        var(--bg);
      color: var(--text); margin: 0; padding: 1.25rem; line-height: 1.45; font-size: 14px;
    }
    .header { display: flex; align-items: flex-end; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1rem; max-width: 1200px; margin-left: auto; margin-right: auto; }
    .brand { font-size: 0.72rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--accent); margin: 0 0 0.35rem; font-weight: 600; }
    h1 { font-size: 1.7rem; font-weight: 700; margin: 0; letter-spacing: -0.03em; }
    .sub { color: var(--muted); font-size: 0.9rem; margin: 0.35rem 0 0; max-width: 40rem; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 0.7rem; margin: 0 auto 1rem; max-width: 1200px; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 0.85rem 0.9rem; text-align: center; }
    .card .val { font-size: 1.35rem; font-weight: 700; line-height: 1.2; font-variant-numeric: tabular-nums; }
    .card .lbl { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.2rem; }
    .card.ok .val { color: var(--ok); }
    .card.fail .val { color: var(--err); }
    .card.skip .val, .card.ts .val { color: var(--muted); }
    .actions { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
    .btn { padding: 0.5rem 1rem; background: var(--accent); color: var(--ink); border: none; border-radius: 10px; cursor: pointer; font-size: 0.875rem; font-weight: 700; font-family: inherit; }
    .btn:hover { filter: brightness(1.06); }
    .btn:disabled { opacity: 0.55; cursor: not-allowed; }
    .btn.ghost { background: transparent; color: var(--muted); border: 1px solid var(--border); font-weight: 600; }
    .toolbar { display: flex; gap: 0.6rem; flex-wrap: wrap; max-width: 1200px; margin: 0 auto 0.85rem; }
    input[type="search"], select {
      background: #081522; color: var(--text); border: 1px solid var(--border); border-radius: 10px;
      padding: 0.55rem 0.75rem; font: inherit; min-width: 180px;
    }
    .wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 12px; background: var(--card); max-width: 1200px; margin: 0 auto; }
    table { width: 100%; border-collapse: collapse; min-width: 640px; }
    th { text-align: left; padding: 0.6rem 0.85rem; background: #0a1824; color: var(--muted); font-weight: 600; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--border); }
    td { padding: 0.5rem 0.85rem; border-bottom: 1px solid var(--border); font-size: 0.875rem; }
    tr:last-child td { border-bottom: none; }
    tr:hover { background: rgba(255,255,255,0.02); }
    tr.hidden { display: none; }
    .path { word-break: break-all; font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.78rem; }
    .cat { color: var(--muted); font-size: 0.78rem; }
    .badge { display: inline-block; padding: 0.18rem 0.5rem; border-radius: 6px; font-size: 0.72rem; font-weight: 600; }
    .badge.ok { background: rgba(42,212,162,0.14); color: var(--ok); }
    .badge.fail { background: rgba(239,107,120,0.14); color: var(--err); }
    .badge.pending, .badge.skip { background: rgba(138,160,182,0.15); color: var(--muted); }
    .code-ok { color: var(--ok); font-variant-numeric: tabular-nums; }
    .code-fail { color: var(--err); font-variant-numeric: tabular-nums; }
    .time { font-variant-numeric: tabular-nums; color: var(--muted); }
    #loading { color: var(--muted); font-size: 0.875rem; padding: 0.85rem 0; max-width: 1200px; margin: 0.6rem auto 0; }
    .method { font-family: "IBM Plex Mono", monospace; font-size: 0.68rem; font-weight: 600; color: var(--muted); }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <p class="brand">MasterNoder</p>
      <h1>API Monitor</h1>
      <p class="sub">Probe live <code>/api</code> routes. Pages, redirects, and tooling clutter are removed. Try endpoints in the <a href="/api-lab/">API Lab</a>.</p>
    </div>
    <div class="actions">
      <button class="btn ghost" id="btn-other" type="button">Show other</button>
      <button class="btn" id="btn-run" onclick="runProbes()">Probe visible</button>
    </div>
  </div>
  <div class="cards">
    <div class="card ok"><div class="val" id="ok-count">0</div><div class="lbl">OK</div></div>
    <div class="card fail"><div class="val" id="fail-count">0</div><div class="lbl">Fail</div></div>
    <div class="card skip"><div class="val" id="skip-count">0</div><div class="lbl">Skip</div></div>
    <div class="card total"><div class="val" id="total-count">0</div><div class="lbl">Visible</div></div>
    <div class="card ts"><div class="val" id="ts">—</div><div class="lbl">Last check</div></div>
  </div>
  <div class="toolbar">
    <input id="q" type="search" placeholder="Filter path or category" autocomplete="off">
    <select id="cat"><option value="all">All categories</option></select>
  </div>
  <div class="wrap">
    <table>
      <thead><tr><th>Method</th><th>Endpoint</th><th>Category</th><th>Status</th><th>Code</th><th>Time</th></tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
  <p id="loading">Loading endpoints…</p>
  <script>
    var base = window.location.origin || '';
    var BATCH = 6;
    var allRows = [];
    var showOther = false;
    function el(id) { return document.getElementById(id); }
    var FALLBACK_ENDPOINTS = ['/api/health','/api/version','/api/points/all','/api/stats/summary','/api/trophies/list','/api/frontpage/init','/api/battle/stats','/api/mn2/balance','/api/lab/v2/status'];
    function fetchEndpoints() {
      return fetch(base + '/api/monitor/endpoints?internal=' + (showOther ? '1' : '0'), { headers: { 'Accept': 'application/json' } })
        .then(function(r) {
          if (!r.ok) throw new Error('Endpoints request failed: ' + r.status);
          return r.json();
        })
        .then(function(data) {
          var eps = (data && data.endpoints) ? data.endpoints : [];
          if (eps.length === 0) eps = FALLBACK_ENDPOINTS.map(function(p) { return { path: p, methods: ['GET'], probe: true, category: 'health', label: 'Health', internal: false }; });
          return { endpoints: eps, categories: (data && data.categories) || [] };
        });
    }
    function fillCategories(categories) {
      var sel = el('cat');
      var current = sel.value || 'all';
      sel.innerHTML = '<option value="all">All categories</option>';
      categories.forEach(function(c) {
        var opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.label + ' (' + c.count + ')';
        sel.appendChild(opt);
      });
      sel.value = current;
      if (![].some.call(sel.options, function(o) { return o.value === current; })) sel.value = 'all';
    }
    function applyFilter() {
      var q = (el('q').value || '').trim().toLowerCase();
      var cat = el('cat').value || 'all';
      var visible = 0, skip = 0;
      allRows.forEach(function(r) {
        var matchCat = cat === 'all' || r.category === cat;
        var matchQ = !q || r.path.toLowerCase().indexOf(q) >= 0 || (r.category || '').indexOf(q) >= 0 || (r.label || '').toLowerCase().indexOf(q) >= 0;
        var show = matchCat && matchQ;
        r.tr.classList.toggle('hidden', !show);
        if (show) {
          visible++;
          if (!r.probe) skip++;
        }
      });
      el('total-count').textContent = visible;
      el('skip-count').textContent = skip;
    }
    function renderTable(endpoints, categories) {
      var tbody = el('tbody');
      tbody.innerHTML = '';
      allRows = endpoints.map(function(ep) {
        var tr = document.createElement('tr');
        var methods = (ep.methods || ['GET']).join(',');
        tr.innerHTML =
          '<td class="method">' + methods + '</td>' +
          '<td class="path">' + ep.path + '</td>' +
          '<td class="cat">' + (ep.label || ep.category || '') + '</td>' +
          '<td><span class="badge ' + (ep.probe ? 'pending' : 'skip') + '" data-status>' + (ep.probe ? '—' : 'Skip') + '</span></td>' +
          '<td class="time" data-code>—</td>' +
          '<td class="time" data-time>—</td>';
        tbody.appendChild(tr);
        return { tr: tr, path: ep.path, probe: !!ep.probe, category: ep.category || '', label: ep.label || '' };
      });
      fillCategories(categories);
      applyFilter();
      el('loading').textContent = endpoints.length + ' endpoints loaded. Click “Probe visible” when you want live checks (avoids flooding the server).';
      el('ok-count').textContent = '0';
      el('fail-count').textContent = '0';
      el('ts').textContent = '—';
    }
    function runProbes() {
      el('loading').textContent = 'Probing…';
      el('btn-run').disabled = true;
      var toProbe = allRows.filter(function(r) { return r.probe && !r.tr.classList.contains('hidden'); });
      var skip = allRows.filter(function(r) { return !r.tr.classList.contains('hidden') && !r.probe; }).length;
      el('skip-count').textContent = skip;
      var ok = 0, fail = 0;
      el('ok-count').textContent = '0';
      el('fail-count').textContent = '0';
      function runBatch(offset) {
        var batch = toProbe.slice(offset, offset + BATCH);
        if (batch.length === 0) {
          el('loading').textContent = 'Done.';
          el('btn-run').disabled = false;
          el('ts').textContent = new Date().toLocaleTimeString();
          return;
        }
        Promise.all(batch.map(function(r) {
          var start = performance.now();
          return fetch(base + r.path, { method: 'GET', headers: { 'Accept': 'application/json' } })
            .then(function(res) {
              var time = Math.round(performance.now() - start);
              var ok_ = res.status >= 200 && res.status < 400;
              if (ok_) ok++; else fail++;
              var statusEl = r.tr.querySelector('[data-status]');
              var codeEl = r.tr.querySelector('[data-code]');
              var timeEl = r.tr.querySelector('[data-time]');
              statusEl.textContent = ok_ ? 'OK' : 'Fail';
              statusEl.className = 'badge ' + (ok_ ? 'ok' : 'fail');
              codeEl.textContent = res.status;
              codeEl.className = ok_ ? 'code-ok' : 'code-fail';
              timeEl.textContent = time + ' ms';
            })
            .catch(function(e) {
              fail++;
              r.tr.querySelector('[data-status]').textContent = 'Err';
              r.tr.querySelector('[data-status]').className = 'badge fail';
              r.tr.querySelector('[data-code]').textContent = '—';
              r.tr.querySelector('[data-code]').className = 'code-fail';
              r.tr.querySelector('[data-time]').textContent = (e.message || String(e)).slice(0, 18);
            })
            .finally(function() {
              el('ok-count').textContent = ok;
              el('fail-count').textContent = fail;
            });
        })).then(function() { runBatch(offset + BATCH); });
      }
      runBatch(0);
    }
    function reload() {
      el('loading').textContent = 'Loading endpoints…';
      el('btn-run').disabled = true;
      fetchEndpoints()
        .then(function(payload) {
          renderTable(payload.endpoints, payload.categories);
          el('btn-run').disabled = false;
        })
        .catch(function(e) {
          el('loading').textContent = 'Error: ' + (e.message || e);
          el('btn-run').disabled = false;
        });
    }
    el('q').addEventListener('input', applyFilter);
    el('cat').addEventListener('change', applyFilter);
    el('btn-other').addEventListener('click', function() {
      showOther = !showOther;
      el('btn-other').textContent = showOther ? 'Hide other' : 'Show other';
      reload();
    });
    reload();
  </script>
</body>
</html>
"""


def _monitor_payload(include_internal: bool = False) -> dict:
    """Build monitor endpoints from the shared API Lab catalog."""
    try:
        catalog = build_catalog(current_app.url_map.iter_rules())
    except Exception:
        catalog = {
            "endpoints": [
                {"method": "GET", "path": p, "category": "health", "try_safe": True, "internal": False}
                for p in MONITOR_ENDPOINTS_FALLBACK
            ],
            "categories": [{"id": "health", "label": "Health", "count": len(MONITOR_ENDPOINTS_FALLBACK), "internal": False}],
        }

    by_path = {}
    for row in catalog.get("endpoints") or []:
        if not include_internal and row.get("internal"):
            continue
        path = row["path"]
        entry = by_path.get(path)
        if entry is None:
            entry = {
                "path": path,
                "methods": [],
                "category": row.get("category") or "more",
                "label": next(
                    (c["label"] for c in catalog.get("categories", []) if c["id"] == row.get("category")),
                    row.get("category") or "Other",
                ),
                "internal": bool(row.get("internal")),
                "probe": False,
            }
            by_path[path] = entry
        method = row["method"]
        if method not in entry["methods"]:
            entry["methods"].append(method)
        if is_try_safe(method, path):
            entry["probe"] = True

    endpoints = sorted(by_path.values(), key=lambda item: (item["category"], item["path"]))
    for item in endpoints:
        item["methods"] = sorted(item["methods"])

    categories = catalog.get("categories") or []
    if not include_internal:
        categories = [c for c in categories if not c.get("internal")]
    # Recompute counts for filtered set
    counts = {}
    for item in endpoints:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    categories = [
        {**c, "count": counts.get(c["id"], 0)}
        for c in categories
        if counts.get(c["id"], 0) > 0
    ]
    return {
        "success": True,
        "endpoints": endpoints,
        "categories": categories,
        "count": len(endpoints),
        "internal_hidden": not include_internal,
    }


@api_monitor_bp.route("/api/monitor/endpoints", methods=["GET"])
def monitor_endpoints_json():
    """Return cleaned API endpoints (path, methods, category, probe) for the table."""
    include_internal = (request.args.get("internal") or "").strip().lower() in (
        "1", "true", "yes", "all",
    )
    return jsonify(_monitor_payload(include_internal=include_internal))


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
    """Mounted-route census for the debugger health card.

    The previous implementation HTTP-probed every API route from inside the
    request. On a single uWSGI worker that calls back into the same process
    and hangs until the proxy times out. This reports routes that are actually
    registered, which is what the health card can answer without a self-request.
    """
    rules = []
    try:
        for rule in current_app.url_map.iter_rules():
            path = rule.rule or ""
            if not path.startswith("/api/"):
                continue
            methods = sorted(m for m in (rule.methods or set()) if m not in {"HEAD", "OPTIONS"})
            rules.append({
                "path": path,
                "methods": methods,
                "ok": True,
                "mounted": True,
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "check": "mounted_routes",
            "live_probe": False,
            "ok": 0,
            "fail": 1,
            "total": 0,
            "endpoints": [],
        }), 200
    rules.sort(key=lambda item: item["path"])
    return jsonify({
        "success": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "check": "mounted_routes",
        "live_probe": False,
        "ok": len(rules),
        "fail": 0,
        "total": len(rules),
        "endpoints": rules,
    })
