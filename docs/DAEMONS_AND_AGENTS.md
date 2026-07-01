# Daemons, bots & agents — local cmd guide

Quick reference for everything that runs on a loop in MasterNoder.dk.  
**Windows:** edit in Cursor, run from cmd → `run_daemons.cmd`

---

## Launcher (start here)

```cmd
cd c:\Users\jonkh\UsecaseSampler\Masternoder.dk
run_daemons.cmd
```

| Key | What |
|-----|------|
| **i** | Inventory — all bots, P&L, kill-switch |
| **1** | **Exchange master** (recommended) — full trading stack |
| **4** | One test tick (exchange + casino) |
| **7–9** | Open daemons in separate cmd windows |

One-shot from root:

```cmd
run_daemons_once.cmd
scripts\daemon_inventory.cmd
```

---

## What runs where

### Exchange master (`scripts/exchange_master_daemon.py`)

**One process replaces separate arbitrage/cross-trade loops for most use.**

Each tick (default 300s):

| Step | Engine | Bots |
|------|--------|------|
| 1 | `run_all_bots()` | 5 arbitrage paper agents, **AI multi-venue trader**, 3 cross-trade agents |
| 2 | `process_auto_renewals()` | Rental auto-renew |
| 3 | `run_all_user_agents()` | Every user's marketplace bots |
| 4 | optional `--auto-sweep` | Profit → Binance stash (paper until live) |

```cmd
scripts\run_exchange_master_daemon.cmd --once
scripts\run_exchange_master_daemon.cmd --interval 300
scripts\run_exchange_master_daemon.cmd --interval 300 --auto-sweep
```

Controlled by `data/crypto_exchange/trading_bots_control.json` (kill-switch, supervisors).

### Sub-daemons (optional — subset of master)

| Script | Scope | Interval |
|--------|-------|----------|
| `exchange_arbitrage_daemon.py` | 10-venue paper arbitrage only | 120s |
| `crypto_exchange_agent_daemon.py` | Stable Router, Layer-1 Scout, Casino Liquidity | 300s |

### AI trader

Not a separate process — runs inside **exchange master** via `run_ai_tick()` when the Arbitrage Director supervisor is enabled.

Config: `data/exchange_ai_trading_config.json`  
API: `/api/exchange/ai-trading/*`

### Casino agents (`scripts/casino_agent_daemon.py`)

Autonomous bettors: Nova, Luna, Sage, Ember, Iris.

```cmd
scripts\run_casino_agent_daemon.cmd --once
scripts\run_casino_agent_daemon.cmd --interval 300
scripts\run_casino_agent_daemon.cmd --dry-run --once
```

Production uses cron → `POST /api/agent/casino/run-all` with `AGENT_CASINO_SECRET`.

### Site agent daemon (`scripts/agent_daemon.py`)

Drives **site-wide** automation (not exchange/casino trading).

**Requires Flask** (`start_server.bat`) + `.env`:

```env
AGENT_DAEMON_SECRET=...
AGENT_DAEMON_URL=http://127.0.0.1:5000/api/agents/daemon/tick
AGENT_DAEMON_CONTROLS_AUTOMATION=1
```

```cmd
scripts\run_site_agent_daemon.cmd
```

### MN2 blockchain daemon (`masternoder2d`)

**Linux server only** — wallet RPC for deposits, staking, masternode pings.

See `docs/MN2_DAEMON_SETUP.md`. Not needed for local exchange bot dev.

### Legacy dev runners (avoid on production DB)

| Script | Purpose |
|--------|---------|
| `production_agent_runner.py` | 20 simulated player agents → real DB |
| `keep_agents_alive.py` | Same family, simpler loop |
| `start_agent_automation.py` | In-process automation bootstrap |

---

## Bot inventory (config files)

| Fleet | Config / data |
|-------|----------------|
| Arbitrage paper | `data/exchange_connectors_config.json` → `arbitrage_agents` |
| AI trader | `data/exchange_ai_trading_config.json` |
| Cross-trade | `data/crypto_exchange_config.json` → `agent_trading.agents` |
| User marketplace | `data/crypto_exchange/user_agents/*.json` |
| Casino | `data/casino_agents.json`, `data/casino_agent_models.json` |
| Control board | `data/crypto_exchange/trading_bots_control.json` |

```cmd
python scripts\daemon_inventory.py
python scripts\daemon_inventory.py --json
```

---

## Recommended local setup (3 cmd windows)

```
[1] start_server.bat              ← Flask UI (optional)
[2] run_daemons.cmd → 7           ← exchange master (new window)
[3] run_daemons.cmd → 8           ← casino agents (new window)
```

Or single window for exchange only:

```cmd
scripts\run_exchange_master_daemon.cmd --interval 300
```

---

## Production (Linux systemd vs cron)

| Unit example | Process |
|--------------|---------|
| `systemd/masternoder2d.service.example` | MN2 wallet |
| `systemd/masternoder-agent-daemon.service.example` | Site agent POST loop |
| *(add similar)* | `exchange_master_daemon.py --interval 300` |

**systemd vs cron:** Use **systemd** for long-running daemons you want restarted on failure (`Restart=on-failure`, journald logs, `systemctl enable`). Use **cron** for idempotent **once-per-interval ticks** that must not overlap — e.g. `cron/exchange_master_tick.sh` runs `exchange_master_daemon.py --once` every 2 minutes and exits. Exchange master is **not yet** shipped as a systemd unit — copy the agent-daemon example and point `ExecStart` at `exchange_master_daemon.py --interval 300` if you prefer a persistent loop over cron.

Cron install (production):

```bash
cp cron/masternoder-exchange-master.cron.d /etc/cron.d/masternoder-exchange-master
chmod 644 /etc/cron.d/masternoder-exchange-master
```

---

## Kill-switch drill (runbook)

1. **Trading bots:** Dashboard → Agents control, or edit `data/trading_bots_control.json` → set agent `enabled: false` / global halt.
2. **Live exchange:** unset `EXCHANGE_ARBITRAGE_LIVE` or set `EXCHANGE_LIVE_PROFIT_MAX=0` in `.env`; restart profit daemons / cron.
3. **PayPal sweep:** `EXCHANGE_AUTO_PAYPAL_SWEEP=0` (default after live-profit-max tune).
4. **MN2 network gates (v1.3.1+):** `python scripts/mn2_activate_spork_remote.py SPORK_112_EXCHANGE_LIVE_TRADING 0` to disable live trading network-wide.
5. **Verify:** `python scripts/profit_status_report.py` → `live_enabled=False`; `python scripts/_check_live_balances_once.py` still read-only OK.
6. **Restore:** re-enable flags in reverse order after QA; never enable live + sweep together without manual review.

---

## Self-hosted explorer (optional)

Set in server `.env` when iquidus is synced (see `docs/MN2_EXPLORER_PLAN.md`):

```
MN2_EXPLORER_BASE_URL=https://camgirls.masternoder.dk/
MN2_EXPLORER_KIND=iquidus
```

Until cutover, Chainz fallback remains in `data/mn2_config.json`.

---

## Discord casino fanout (document only)

Cron `cron/discord_casino_fanout.sh` defaults **`dry_run=true`**. Set `CASINO_FANOUT_LIVE=1` and `DISCORD_OPS_SECRET` on the server only after dry-run QA — see `docs/CASINO_OPS_PROGRESS.md`.

---

## Safety

- Exchange/casino daemons default to **paper** / play coins.
- Live crypto: `EXCHANGE_ARBITRAGE_LIVE=1` + vault API keys.
- Kill-switch: control board or `trading_bots_control.json`.

See also: `docs/EXCHANGE_CROSS_VENUE_ARBITRAGE.md`, `docs/LIVE_PROFIT_TRADING.md`, `docs/MN2_DAEMON_SETUP.md`
