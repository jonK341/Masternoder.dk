# Upload and Deployment

This doc describes how to upload and deploy the generator, agents, and related assets to production (masternoder.dk).

## Prerequisites

- Python 3 with `paramiko` for SSH/SFTP: `pip install paramiko`
- Required for SSH deploy helpers: set `DEPLOY_PASS` in the environment (no default is embedded in the repo).

## Deploy Generator + Agents (recommended)

```bash
python scripts/deploy_vidgenerator_solution.py
```

**Deploys:**

- Backend: `video_generator_service.py`, `generator_agent_connections.py`, `missing_endpoints_routes.py`, `battle_routes.py`, `register_blueprints.py`
- Frontend: `vidgenerator/generator/index.html`, `vidgenerator/service-worker.js`, `vidgenerator/static/js/service-worker-gatherer.js`, lab, navigation toolbar

**Steps:** Connect via SSH → upload files → clear Python cache → restart `uwsgi-vidgenerator` and `python-proxy` → reload nginx.

**Verify:** https://masternoder.dk/vidgenerator/ (hard refresh Ctrl+F5). Check Generator → Agent Connections (20), Service Worker, Magic, Deployment tabs.

## Generator (Phase 2 — queue, crypto rewards, gallery)

```powershell
python scripts/deploy.py generator_recent --ask-pass
```

**One-time on server (job persistence):**

```bash
cd /var/www/html && python scripts/generator_migration.py --standalone
```

**Weekly stale artifact cleanup (cron):**

```bash
python scripts/generator_stale_cleanup.py --days 7 --apply
```

**Config:** `data/generator_config.json` — `queue_enabled: true` limits concurrent encodes.  
**Crypto earn:** MN2 finish bonus + multi-AI + daily-first + staking boost (`data/mn2_config.json` → `generator.crypto_rewards`).

**Verify:**

```powershell
python scripts/test_generator_after_deploy.py
python scripts/hard_test_generator_urls.py --quick
```

See [GENERATOR_UPGRADES_25.md](./GENERATOR_UPGRADES_25.md) · [GENERATOR_ENCODER_IDEAS.md](./GENERATOR_ENCODER_IDEAS.md).

## Full production pipeline

```bash
python scripts/production_deployment.py
```

Runs backup, migrations, code deploy, env config, restart, endpoint verification, health check, monitoring (steps are placeholders unless implemented).

## Deploy and restart all services

```bash
python scripts/full_deploy_and_restart.py
```

## Server layout

- **Host:** masternoder.dk  
- **Remote base:** `/var/www/html`  
- **Services:** `uwsgi-vidgenerator`, optional `uwsgi-vidgenerator-5001`, `python-proxy`, nginx  

Do not start the legacy `uwsgi` wrapper for this app. It can race `uwsgi-vidgenerator` for `127.0.0.1:5000` and trigger 500/502 failures.

## Manifest-based deploy (`scripts/deploy.py`)

Targeted uploads + uWSGI restart. Use `--ask-pass` when `DEPLOY_PASS` in `.env` is stale.

| Manifest | Ships | Doc |
|----------|-------|-----|
| `mn2_staking` | Trader market, Discord cross-roads, staking routes, explorer market UI | [MN2_TRADER_MARKET.md](MN2_TRADER_MARKET.md), [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md) |
| `camgirls` | Camgirls API, page, agents, payout services | [CAMGIRLS_PHASE1C.md](CAMGIRLS_PHASE1C.md) |
| `compendium` | Rulebook viewers, calm reader, progress APIs | [RULEBOOK_READERS.md](RULEBOOK_READERS.md) |
| `game_hub` | Game Hub panels, progress reader hooks | [GAME_HUB_UNIFIED_25.md](GAME_HUB_UNIFIED_25.md) |
| `mn2_env` | Daemon scripts, deposit scanner cron, accrue cron | [MN2_OPS.md](MN2_OPS.md) |

```powershell
python scripts/deploy.py mn2_staking --ask-pass
python scripts/deploy.py camgirls --ask-pass
```

List all manifests: `python scripts/deploy.py` (no args).

## Generator-specific deploy checklist

1. Run `python scripts/deploy_vidgenerator_solution.py`.
2. Open https://masternoder.dk/vidgenerator/generator/.
3. In Generation Summaries, check: **URL Test** (quick), **Agent Connections (20)**, **Service Worker** (status), **Magic** (one-click generate), **Deployment** (this doc).
4. Optional: run `python scripts/hard_test_generator_urls.py --base https://masternoder.dk --quick` from your machine to hard-test live URLs.
