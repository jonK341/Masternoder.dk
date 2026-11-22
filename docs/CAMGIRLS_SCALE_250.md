# Camgirls 250-scale roster ops

Goal: grow from ~15 live performers toward **250** using **waves** of 15–50 stubs — not a single bulk JSON dump.

## Wave file

- Template: `data/camgirls_performers_wave.template.json`
- Wave 2 file: `data/camgirls_waves/wave2.json` (25 hosts).
- Wave 3 file: `data/camgirls_waves/wave3.json` (25 hosts).
- Wave 4 file: `data/camgirls_waves/wave4.json` (35 hosts).
- Waves 5–10: `data/camgirls_waves/wave{5..10}.json` via `scripts/camgirls_gen_scale_waves.py` (25 each; local roster **250**).

### Baseline (local, 2026-11-22)

| Check | Result |
|-------|--------|
| `--milestone 50` / `100` / `250` | PASS (250 performers, agents + media ready) |
| `list_performers_catalog(lite=True)` @100 | **~101 ms** local |
| Phase-2 `gallery-1.webp` | **250/250** slugs |
- CSV is also supported (`display_name` required; optional `slug`, `initials`, `c1`, `c2`, prices).

Each stub needs at least `display_name`. IDs default to `{id_prefix}{slug}` (prefix from `wave` / `--batch` / `id_prefix` field).

Brand colors for generated gallery/icon assets live under `media: { slug, initials, c1, c2 }`. The batch script writes these to `data/camgirls_performer_media_meta.json` (overlay on built-in meta in `camgirls_media_service.py`).

## Batch onboard

**Do not** run `bash scripts/camgirls_batch_onboard.py` — that file is Python. On the server use `camgirls_py.sh` or `camgirls_batch_onboard.sh`.

```bash
# Local — plan only
.venv/bin/python scripts/camgirls_batch_onboard.py \
  --file data/camgirls_performers_wave.template.json --dry-run

# Server — plan only (forward slashes for paths)
cd /var/www/html
bash scripts/camgirls_batch_onboard.sh --file data/camgirls_waves/wave2.json --batch 2 --wave-size 25 --dry-run

# Wave 2 apply — upsert JSON, media meta, DB, payout rails, raster assets
bash scripts/camgirls_batch_onboard.sh --file data/camgirls_waves/wave2.json --batch 2 --wave-size 25 \
  --provision-addresses --generate-media --full-catalog-sync
```

### Payout rails

- `--provision-addresses` calls `provision_payout_rails(performer_ids=…)` (MN2 `getnewaddress` + PayPal checkout metadata).
- On production: `bash scripts/camgirls_py.sh scripts/camgirls_provision_payout_addresses.py --check-rpc`
- Per-id repair: `scripts/camgirls_provision_payout_addresses.py --performer performer_wave2_studio_host_a`

### Media

- `--generate-media` runs `scripts/camgirls_generate_performer_media.py` (WebP/SVG/preview ZIPs).
- Drop real `gallery-*.webp` under `static/camgirls/media/<slug>/` and re-run the generator.

### Deploy (split uploads)

Do **not** push ~2k gallery files one-by-one. Use two manifests:

```bash
# 1) Code + catalog JSON + UI (fast)
python scripts/deploy.py camgirls

# 2) Media + brand-pack zips as tar batches (~40 slugs each)
python scripts/deploy.py camgirls_media

# Or both in one command (code first, then media batches):
python scripts/deploy.py camgirls camgirls_media
```

- Batch size: `CAMGIRLS_MEDIA_BATCH_SIZE` (default **40**).
- After code deploy: `python scripts/camgirls_prod_p2_ops.py` (catalog `db` + payouts + uwsgi restart).
- Media-only reloads nginx; it does not restart uWSGI.

## Single-performer path

`scripts/camgirls_onboard_performers.py --file …` remains valid for one-off JSON lists.
