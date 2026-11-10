# The Profit Daemon Jon — 5-minute install

## 1. Clone / download (30s)

- **Source:** clone this repo, then `cd` into it.
- **Binary:** GitHub Releases → download `TheProfitDaemonJon-<os>.zip` → unzip.

## 2. Install (1–2 min)

```bash
bash profit_daemon_jon/install.sh
# or Windows: profit_daemon_jon\install.cmd
```

Screenshot checkpoint: terminal shows `25/25 tech OK`.

## 3. Wizard (1 min)

```bash
.venv/bin/python profit_daemon_jon/run.py --wizard
```

Choose **paper**, skip live keys for first run. Screenshot: `.env` written.

## 4. Paper tick (1 min)

```bash
.venv/bin/python profit_daemon_jon/run.py --once --profile paper
```

Screenshot: banner `The Profit Daemon Jon` + tick summary.

## 5. Status / sales / tray (1 min)

```bash
.venv/bin/python profit_daemon_jon/run.py --status
.venv/bin/python profit_daemon_jon/run.py --sales --hours 3
.venv/bin/python profit_daemon_jon/run.py --tray
# open http://127.0.0.1:8787/
```

## 6. Optional observability (1 min)

```bash
docker compose -f profit_daemon_jon/docker-compose.yml up -d
# Grafana :3030  Prometheus :9090  Redis :6379
```

## Live unlock (later)

Re-run `--wizard`, choose **live**, set venue keys + `EXCHANGE_VAULT_KEY`. Live refuses to start without the vault.
