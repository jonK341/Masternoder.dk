# Explorer ops — P4 runbook (deploy, cache, canary, staging)

Companion to [MN2_OPS.md §10](MN2_OPS.md) and [EXPLORER_UPGRADES_250.md](EXPLORER_UPGRADES_250.md).

## Deploy PR to live uwsgi (#168)

```bash
git checkout main && git pull
python scripts/deploy.py mn2_staking static_pages mn2_env --ask-pass
```

Restart is automatic for `mn2_staking`; `static_pages` reloads nginx only.

## Post-deploy verification (#169–171, #177)

```bash
POST_DEPLOY_BASE_URL=https://<your-site> python scripts/smoke_explorer_deploy.py
```

Checks: `network-overview`, `recent-blocks`, `/api/mn2/services` (explorer entry), `rich-list`, `explorer/status`, `/explorer/` shell, `/explorer/tx/<id>` shell.

## Rich list when eiquidus index syncing (#172)

`GET /api/mn2/explorer/status` exposes `checks.rich_list.index_synced`. When `false`, the hub shows the empty-state message until eiquidus finishes indexing.

## Nginx cache (#173)

Copy snippets from `config/nginx/mn2-explorer-cache.conf.example` into your site config. Respect Flask `Cache-Control` on overview (30s + SWR).

## Network snapshot cron (#174)

Deployed with `mn2_staking` manifest:

- `cron/mn2_network_snapshot.sh` — curls overview (server throttles to ~10 min)
- `cron/masternoder-mn2-network-snapshot.cron.d`

Fallback: `systemd/mn2-network-snapshot.{service,timer}.example`

## Explorer probe + Discord (#175)

- `scripts/mn2_explorer_probe_alert.py`
- `cron/mn2_explorer_probe.sh` + `masternoder-mn2-explorer-probe.cron.d` (every 15 min)
- Requires `DISCORD_WEBHOOK_URL` in server `.env`

## Grafana (#176)

Starter dashboard: `ops/grafana/mn2-network-history-dashboard.json` — wire to your metrics backend reading `network-history` API or JSONL.

## CDN / static purge (#183)

After `static_pages` deploy, purge edge cache for:

- `/static/js/mn2-explorer-*.js`
- `/static/css/mn2-crypto-hub.css`
- `/explorer/*.html`

Cloudflare example: zone purge by prefix or `scripts/deploy.py` note after nginx reload.

## Blue/green explorer_kind flip (#184)

1. Set `MN2_EXPLORER_KIND=chainz` on standby env; deploy code.
2. Smoke both hosts; flip DNS or nginx upstream weight.
3. Set `MN2_EXPLORER_KIND=iquidus` on primary; deploy `mn2_env`.
4. Roll back by restoring previous `.env` + `mn2_env` deploy.

## Staging mirror (#185)

Run the same manifests against a staging host with `POST_DEPLOY_BASE_URL` pointing at staging. Use `explorer_local_api_url` to a staging eiquidus instance.

## SSE load test (#186)

```bash
python scripts/load_test_explorer_sse.py --clients 100 --duration 30
```

## API latency logs (#187)

`logs/mn2_explorer_api.jsonl` — disable with `MN2_EXPLORER_METRICS=0`. Summary via `mn2_explorer_metrics.latency_summary()`.

## Feature flag + canary (#188, #189)

| Variable | Default | Purpose |
|----------|---------|---------|
| `EXPLORER_HUB_V2` | `1` | Master switch for hub v2 UI |
| `EXPLORER_HUB_V2_CANARY_PERCENT` | `100` | Hash-based canary (0–100) |

Overview JSON includes `hub_v2_enabled` for clients.

## eiquidus Mongo backup before reindex (#181)

```bash
sudo ./scripts/backup_eiquidus_mongo.sh /var/backups/eiquidus
```

## Runtime data gitignore (#180)

`data/mn2_network_history.jsonl` is gitignored — snapshots live on server only.
