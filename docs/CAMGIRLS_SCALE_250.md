# Camgirls 250-scale roster ops

Goal: grow from ~15 live performers toward **250** using **waves** of 15–50 stubs — not a single bulk JSON dump.

## Wave file

- Template: `data/camgirls_performers_wave.template.json`
- Copy to e.g. `waves/wave2.json` (gitignored locally if it contains ops data).
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
bash scripts/camgirls_batch_onboard.sh --file waves/wave2.json --batch 2 --wave-size 25 --dry-run

# Wave 2 apply — upsert JSON, media meta, DB, payout rails, raster assets
bash scripts/camgirls_batch_onboard.sh --file waves/wave2.json --batch 2 --wave-size 25 \
  --provision-addresses --generate-media --full-catalog-sync
```

### Payout rails

- `--provision-addresses` calls `provision_payout_rails(performer_ids=…)` (MN2 `getnewaddress` + PayPal checkout metadata).
- On production: `bash scripts/camgirls_py.sh scripts/camgirls_provision_payout_addresses.py --check-rpc`
- Per-id repair: `scripts/camgirls_provision_payout_addresses.py --performer performer_wave2_studio_host_a`

### Media

- `--generate-media` runs `scripts/camgirls_generate_performer_media.py` (WebP/SVG/preview ZIPs).
- Drop real `gallery-*.webp` under `static/camgirls/media/<slug>/` and re-run the generator.

### Deploy

- `python scripts/deploy.py camgirls` includes batch script, wave template, and media meta overlay file.
- After deploy, run catalog sync on server if `CAMGIRLS_CATALOG_SOURCE=db`.

## Single-performer path

`scripts/camgirls_onboard_performers.py --file …` remains valid for one-off JSON lists.
