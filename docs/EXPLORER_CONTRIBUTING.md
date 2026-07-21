# Contributing — MN2 Explorer Hub

Guide for adding a new tile to the Crypto Hub overview. (#225)

## 1. Backend (if new data)

1. Add field to `mn2_chainz.network_overview()` or merge in `_build_network_overview_payload()` (`mn2_staking_routes.py`).
2. Record provenance in `source` map: `out["source"]["my_field"] = "rpc"`.
3. If historical sparkline needed, add key to `_SNAPSHOT_KEYS` in `mn2_network_stats.py`.

## 2. HTML tile (`explorer/index.html`)

```html
<div class="ex-tile">
  <div class="label">My metric</div>
  <div class="value" id="t-mymetric">--</div>
  <div class="sub" id="s-mymetric"></div>
</div>
```

Use unique `id="t-*"` and optional `id="s-*"` for source label.

## 3. JavaScript (`static/js/mn2-explorer-overview.js`)

In the render path (after overview fetch):

```javascript
q('t-mymetric').textContent = d.my_field != null ? fmtNum(d.my_field, 2) : '—';
setSrc('s-mymetric', src, 'my_field');
```

Add JSDoc if the function is non-obvious.

## 4. CSS

Reuse `.ex-tile` in `static/css/mn2-crypto-hub.css`. Match existing label/value/sub pattern.

## 5. Tests

- Static: add assertion to `tests/unit/test_explorer_p5.py` or new P6 check for tile id in HTML + JS.
- API: extend overview schema test if new top-level field is required.

## 6. Deploy

Bump cache query on static assets (`?v=YYYYMMDD`) in `explorer/index.html`. Ship via `static_pages` manifest.

## API docs

Publish OpenAPI path in `EXPLORER_OPENAPI` (`mn2_explorer_data.py`) when adding endpoints.
