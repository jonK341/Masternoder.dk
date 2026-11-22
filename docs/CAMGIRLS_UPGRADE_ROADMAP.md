# Camgirls upgrade roadmap (categorized)

Human-readable mirror of `data/camgirls_next_todos.json`. The studio info bar loads categories from `GET /api/camgirls/status` (`next_todos_by_category`). Flat `next_todos` remains for older clients.

**Updated:** 2026-11-22 · **Branch context:** wave 2 roster + explorer bridge

## Priority legend

| Tag | Meaning |
|-----|---------|
| `done` | Shipped in repo and/or prod per MN2_TODO / deploy verify |
| `P1` | Next product-facing slice |
| `P2` | Ops or polish after P1 |
| `P3` | Scale / backlog |

---

### Platform core

Phase 0 studio: **15 AI performers**, PayPal checkout, SSE chat, landings, catalog lite perf. All **done**.

### Media & content

Phase 2 raster + preview generator **done**. WebP galleries for all **250** hosts **done** (photographic overrides still optional drop-ins).

### Payments & payouts

**15/15** MN2 rails and Phase 1c daemon pattern **done**. Wave payout provision on prod **done** (`camgirls_prod_p2_ops.py`, RPC OK).

### Voice (LiveKit)

Browser E2E (Phase 3) **done**. Prod LiveKit **confirmed live** (`mode=live`, token gate unlock-required).

### Catalog & data

SQLite sync script and deploy hook **done**. Prod **`catalog=db` / 250 performers** after full uwsgi restart (`camgirls_prod_p2_ops.py`).

### Shop & resell

SKU generator service **done**. **P1:** surface 16 `dg-camgirls-brand-*` packs on `/app/shop/` (`digital_goods` + tag `camgirls`).

### Studio UI & links

Phase 4 nav/link fix **done**. Nginx `/app/` move is **declined**: studio stays on `/camgirls/`. The snippet remains unused.

### Ops, deploy & verify

Manifest, fast sync, and **4/4** verify **done**. Roster **@50 / @100 / @250** verify **done** (250 hosts).

### Scale to 250

Batch onboard, wave template, and media meta overlay **done** (see [CAMGIRLS_SCALE_250.md](CAMGIRLS_SCALE_250.md)). Waves 2–10 **done** (roster **250**).

### Future / backlog

Discord spotlight **done**. Explorer lookup on the studio page **done** (address or tx, no nginx).

---

## Editing the roadmap

1. Edit `data/camgirls_next_todos.json` — keep `categories[].items[]` with stable `id` strings.
2. Deploy includes the JSON via `deploy.py camgirls` and `camgirls_prod_fast_sync.sh`.
3. No code change needed for copy-only updates; UI groups by category automatically.
