# The Profit Daemon Jon

Downloadable profit engine for MasterNoder: ladders, cross-venue scan, grid, fill model, Prometheus metrics, and sales reports — branded for easy GitHub download and local use.

**Version:** see `VERSION` · **Catalog:** `top25_technologies.json`

## Quick start (from source)

```bash
# Linux / macOS
bash profit_daemon_jon/install.sh
.venv/bin/python profit_daemon_jon/run.py --once --profile paper
.venv/bin/python profit_daemon_jon/run.py --sales --hours 3
.venv/bin/python profit_daemon_jon/run.py --status
```

```bat
REM Windows
profit_daemon_jon\install.cmd
.venv\Scripts\python profit_daemon_jon\run.py --once --profile paper
```

Paper mode is the default. Edit `.env` (copied from `profit_daemon_jon/.env.example`) before enabling live trading.

## Download compiled builds (GitHub Releases)

1. Open **Releases** on this project's GitHub repository.
2. Download the asset for your OS:
   - `TheProfitDaemonJon-linux-x64.zip`
   - `TheProfitDaemonJon-windows-x64.zip` (built on Windows runners)
   - `TheProfitDaemonJon-macos-arm64.zip` / `x64` when published
3. Unzip and run:

```bash
./TheProfitDaemonJon --status
./TheProfitDaemonJon --install-top25 --no-pip
./TheProfitDaemonJon --once --profile paper
```

Build locally if a Release asset is missing:

```bash
bash profit_daemon_jon/build_release.sh
# → dist/TheProfitDaemonJon/
```

> PyInstaller does **not** cross-compile. Windows `.exe` must be built on Windows (`build_release.cmd`).

## Top 25 technologies

`install.sh` / `run.py --install-top25` installs and marks the product stack (Redis bus, Prometheus, Grafana dashboard JSON, sklearn fill model, ladder + skew, WS feed, arb/grid, sales CLI, systemd unit, PPP, ops hooks, …).

```bash
.venv/bin/python profit_daemon_jon/run.py --status
.venv/bin/python profit_daemon_jon/run.py --backlog   # finished-product checklist
```

## 24/7 server

```bash
bash scripts/install_profit_daemon_server.sh
systemctl status masternoder-profit-daemon.service
```

Grafana (when deployed on your host): path `/grafana/d/masternoder-exchange/masternoder-exchange-daemon`

## Safety

- Starts **paper / non-live** unless you explicitly set live env flags and fund venues.
- Keep API keys in `.env` or an encrypted vault — never commit secrets.
- Ladder and arb can lose money in trends; size is capped by config and free balances.
