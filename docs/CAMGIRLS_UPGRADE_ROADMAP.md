# Camgirls upgrade roadmap (categorized)

Human-readable mirror of `data/camgirls_next_todos.json`. The studio info bar loads categories from `GET /api/camgirls/status` (`next_todos_by_category`). Flat `next_todos` remains for older clients.

**Updated:** 2026-10-10 · **Branch context:** PR #127 (Phase 3 LiveKit + scale ops)

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

Phase 2 raster + preview generator **done**. **P2:** drop real `gallery-*` photos per slug and re-run `camgirls_generate_performer_media.py`.

### Payments & payouts

**15/15** MN2 rails and Phase 1c daemon pattern **done**. **P2:** batch `--provision-addresses` after each wave + RPC check on prod.

### Voice (LiveKit)

Browser E2E (Phase 3) **done**. **P2:** SSH optionals confirm `LIVEKIT_*` on server (MN2_TODO).

### Catalog & data

SQLite sync script and deploy hook **done**. **P2:** set `CAMGIRLS_CATALOG_SOURCE=db` on prod after wave sync.

### Shop & resell

SKU generator service **done**. **P1:** surface 16 `dg-camgirls-brand-*` packs on `/app/shop/` (`digital_goods` + tag `camgirls`).

### Studio UI & links

Phase 4 nav/link fix **done**. **P2:** optional nginx `/app/` snippet if product moves studio to `camgirls.masternoder.dk/app/`.

### Ops, deploy & verify

Manifest, fast sync, and **4/4** verify **done**. **P2/P3:** extend verify for **50 / 100 / 250** roster milestones after waves.

### Scale to 250

Batch onboard, wave template, and media meta overlay **done** (see [CAMGIRLS_SCALE_250.md](CAMGIRLS_SCALE_250.md)). **P2:** run wave 2 file. **P3:** waves 3–N toward 250.

### Future / backlog

Discord spotlight **done**. Explorer/studio UX polish **P3**.

---

## Editing the roadmap

1. Edit `data/camgirls_next_todos.json` — keep `categories[].items[]` with stable `id` strings.
2. Deploy includes the JSON via `deploy.py camgirls` and `camgirls_prod_fast_sync.sh`.
3. No code change needed for copy-only updates; UI groups by category automatically.
