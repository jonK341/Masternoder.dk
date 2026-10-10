# Upload and Deployment

This doc describes how to upload and deploy the generator, agents, and related assets to production (masternoder.dk).

## Prerequisites

- Python 3 with `paramiko` for SSH/SFTP: `pip install paramiko`
- Optional: set `DEPLOY_PASS` environment variable for SSH password (otherwise script default is used).

## Deploy Generator + Agents (recommended)

```bash
python scripts/deploy_vidgenerator_solution.py
```

**Deploys:**

- Backend: `video_generator_service.py`, `generator_agent_connections.py`, `missing_endpoints_routes.py`, `battle_routes.py`, `register_blueprints.py`
- Frontend: `vidgenerator/generator/index.html`, `vidgenerator/service-worker.js`, `vidgenerator/static/js/service-worker-gatherer.js`, lab, navigation toolbar

**Steps:** Connect via SSH → upload files → clear Python cache → restart `python-proxy`, `uwsgi-vidgenerator`, `uwsgi` → reload nginx.

**Verify:** https://masternoder.dk/vidgenerator/ (hard refresh Ctrl+F5). Check Generator → Agent Connections (20), Service Worker, Magic, Deployment tabs.

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
- **Services:** `python-proxy`, `uwsgi-vidgenerator`, `uwsgi`, nginx  

## Generator-specific deploy checklist

1. Run `python scripts/deploy_vidgenerator_solution.py`.
2. Open https://masternoder.dk/vidgenerator/generator/.
3. In Generation Summaries, check: **URL Test** (quick), **Agent Connections (20)**, **Service Worker** (status), **Magic** (one-click generate), **Deployment** (this doc).
4. Optional: run `python scripts/hard_test_generator_urls.py --base https://masternoder.dk --quick` from your machine to hard-test live URLs.
