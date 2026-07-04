# Profit Daemon — Activity & Upgrade Checklist

_Last updated: 2026-07-04_

Canonical ops checklist for Masternoder.dk profit engines. For the **110-upgrade roadmap** (22 done / 88 planned), see [PROFIT_DAEMON_110_UPGRADES.md](./PROFIT_DAEMON_110_UPGRADES.md). For the full 25-item audit (auto-synced from PPP ledger), see [PROFIT_CRITICAL_TOP25.md](./PROFIT_CRITICAL_TOP25.md). For PPP schema and research workflow, see [PROFIT_PATH_PROTOCOL.md](./PROFIT_PATH_PROTOCOL.md). For 24/7 server systemd plan, see [PROFIT_DAEMON_SERVER.md](./PROFIT_DAEMON_SERVER.md).

---

## Quick ops (daily)

- **Confirm daemon is running**
  - Local: terminal running `scripts/run_all_profit_daemons.cmd --auto-sweep` (or menu `a` in `scripts/run_daemons.cmd`)
  - Server: `systemctl status masternoder-profit-daemon.service` and `tail -f /var/www/html/logs/profit_daemon_stdout.log`
- **Check heartbeat** (should update every exchange tick, ~120–300s)
  - `logs/daemon_all_profit_heartbeat.json` or `GET /api/profit-daemon/status`
  - Stale > 5 min → restart daemon
- **Scan one exchange line** in stdout — see [Expected healthy daemon logs](#expected-healthy-daemon-logs)
- **Light status** (avoid full Flask load during active ticks): `python scripts/profit_status_report.py --light` or `python scripts/profit_status_light.py`
- **Payout unswept** (if live stash growing): `python scripts/payout_sweep_status.py`
- **Monitor UI**: `/profit/` → Monitor tab (heartbeat, treasury, PPP 24h)
- **Do not run** full `profit_status_report.py` or heavy Flask probes during active ticks (#18)

---

## Open items (from Top25 + session)

Full checklist: [PROFIT_CRITICAL_TOP25.md](./PROFIT_CRITICAL_TOP25.md) (21/25 done as of 2026-07-04).

| # | Item | Status | Next action |
|---|------|--------|-------------|
| **#2** | XeggeX API 401 — keys or IP whitelist | Open | `python scripts/refresh_xeggex_server.py --probe-only` → fix `.env` keys + dashboard IP whitelist → `python scripts/remote_vault_import.py` |
| **#3** | Arb spreads mostly below 18 bps min_margin | Open (market) | Wait for volatility; optional `EXCHANGE_FAST_MIN_BPS=10` before restart when `near_threshold=yes`; watch `arb_skip=below_threshold` |
| **#10** | PayPal sweep still paper — unswept ledger | Open | Preflight: `python scripts/enable_live_paypal_sweep.py`; set `EXCHANGE_PAYOUT_PAYPAL_LIVE=1` + creds; restart with `--auto-sweep` |
| **#20** | `arb_live_dual_farm` limited to binance+nonkyc | Blocked by #2 | After XeggeX probe OK: `python scripts/configure_live_profit_max.py` (enables xeggex in dual-farm) |

### Server deploy (from PROFIT_DAEMON_SERVER.md)

- [ ] Run deploy: `python scripts/deploy_profit_daemon_server.py`
- [ ] Windows: deploy script forces UTF-8 stdout so systemd status bullets do not crash on cp1252.
- [ ] Fix `.env` line 19 separator (`command not found` when sourcing on server)
- [ ] Stop laptop daemon once server systemd is healthy (avoid double ticks)

### Post-code-change restart

Several Top25 fixes (#6 AI trader, #7 arb exec, #9 casino agents) require **daemon restart** to pick up new config/overrides.

---

## How to upgrade the system

### 1. Pull latest code

```bash
git pull origin main   # or your feature branch
```

### 2. Local dev (Windows)

```cmd
scripts\configure_live_profit_max.cmd    # optional: tune live gates + vault
scripts\run_all_profit_daemons.cmd --auto-sweep
```

One-shot smoke test: `python scripts/all_profit_daemons.py --once`

### 3. Server deploy (production)

```bash
python scripts/deploy_profit_daemon_server.py
# SSH on box (if not automated):
bash /var/www/html/scripts/install_profit_daemon_server.sh
systemctl restart masternoder-profit-daemon.service
```

### 4. Environment & vault

- Ensure server `.env` has live gates (see table below)
- Import API keys: `python scripts/remote_vault_import.py`
- NonKYC / XeggeX: whitelist **server egress IP**; set `EXCHANGE_FORCE_IPV4=1` on VPS if 401 from IPv6

### 5. Verify

```bash
curl https://masternoder.dk/vidgenerator/api/profit-daemon/status
python scripts/profit_status_report.py --light
python scripts/payout_sweep_status.py
tail -20 /var/www/html/logs/profit_daemon_stdout.log
pytest tests/unit/test_exchange_profit_path.py tests/unit/test_exchange_swap_rotation.py -q
```

### 6. Kill-switch (if something looks wrong)

See [DAEMONS_AND_AGENTS.md](./DAEMONS_AND_AGENTS.md) — unset `EXCHANGE_ARBITRAGE_LIVE`, set `EXCHANGE_AUTO_PAYPAL_SWEEP=0`, restart daemon.

---

## Important env vars & config

| Setting | Purpose | Typical value |
|---------|---------|---------------|
| `EXCHANGE_ARBITRAGE_LIVE` | Enable live arb execution | `1` on prod |
| `EXCHANGE_FORCE_IPV4` | Avoid venue 401 on dual-stack VPS | `1` on server |
| `EXCHANGE_PAYOUT_PAYPAL_LIVE` | Real PayPal sweeps (not paper) | `1` when ready (#10) |
| `EXCHANGE_AUTO_PAYPAL_SWEEP` | Auto-sweep on tick when above min | `1` with live PayPal |
| `EXCHANGE_PAYOUT_PAYPAL_EMAIL` | PayPal recipient | operator email |
| `EXCHANGE_ROTATION_AUTO` | Auto-execute top rotation action | `1` (local max); `0` prod unless opted in |
| `EXCHANGE_ROTATION_LIVE` | Live rotation orders | `1` (local max); `0` prod unless opted in |
| `EXCHANGE_FAST_MIN_BPS` | Lower fast-rescan threshold (session only) | e.g. `10` when near threshold |
| `EXCHANGE_ZERO_FILL_WARN` | Consecutive hot ticks with arb_exec=0 before warn | default `3` |
| `EXCHANGE_PROFIT_KILL` | Emergency stop — blocks live exec + sweeps | `1` to activate |
| `PROFIT_OPS_DISCORD_CHANNEL` | Discord outbox channel for ops alerts | default `ops` |
| `PROFIT_ALERT_COOLDOWN_SEC` | Min seconds between duplicate ops webhooks | default `900` |
| `EXCHANGE_AUTO_TUNE_SWEEP_MIN` | Lower min_sweep when live stash grows | default `1` |
| `EXCHANGE_AUTO_SCALE_NOTIONAL` | Scale paper_trade_usd to max_funded | default `1` |
| `EXCHANGE_VAULT_KEY` | Fernet key for encrypted secrets vault | server-only, never commit |
| `EXCHANGE_ADMIN_KEY` | Admin PPP export / rotation execute | server-only |
| `XEGGEX_API_KEY` / `XEGGEX_API_SECRET` | XeggeX signed API (#2) | in `.env` + vault |

**Config files**

| File | Role |
|------|------|
| `data/crypto_exchange/profit_path_protocol.json` | PPP + rotation auto defaults |
| `data/exchange_connectors_config.json` | Per-venue `live_trading` (xeggex=false until probe OK) |
| `data/crypto_exchange/payout_config.json` | `auto_sweep`, `min_sweep_usd` (100) |
| `data/exchange_extended_profit_config.json` | Extended strategies, dual-farm venue list |

---

## Expected healthy daemon logs

Startup banner:

```
MasterNoder — ALL profit daemons (single process)
  profile=max mode=live auto_sweep=True
  exchange engines: ...
```

**Healthy exchange tick** (every interval):

```
[all-profit] pair_search ok=yes hits=N hot=BTC,ETH,...   # or hot=none when quiet
[all-profit] exchange platform_ok=True arb_exec=1/12 best_bps=22.5 best_net=20.1 min_margin=18 funded=yes ai_exec=True cross_actions=7 ext_exec=1 sweep=no
```

**When market is quiet but healthy** (#3):

```
arb_exec=0/12 best_bps=7.0 min_margin=18 arb_skip=below_thresholdx6 ai_skip=below_threshold sweep=no
```

**Rotation unlock** (funding gap, not an error):

```
[all-profit] rotation executed: Buy USDT on nonkyc ~$98 mode=live success=True
```

**Hot-pair prefund** (ec2743b monitor):

```
[all-profit] hot_pair_prefund: ...   # when unfunded hot route detected
```

**Fast rescan loop** (when enabled):

```
[all-profit] fast ext_exec=1 ready=yes best_bps=19.0 threshold=18 near_threshold=yes
```

**PayPal sweep** (when live + above min):

```
sweep=yes mode=live amount=$125.00
```

**Warning signs**

| Log pattern | Meaning |
|-------------|---------|
| Heartbeat stale > 5 min | Daemon crashed or blocked — restart |
| `platform_ok=False` | Flask/tick failure — check traceback |
| `arb_block=xeggex_401` or venue probe 401 | Fix #2 before dual-farm |
| `force=...` with `arb_exec=0` | Global threshold ready but execution blocked — check funding |
| `sweep=yes mode=paper` with live gates on | #10 — enable `EXCHANGE_PAYOUT_PAYPAL_LIVE=1` |
| `[all-profit] exchange error:` | Exception in tick — read stack trace |

---

## Deferred / do not do

- **Do not** enable XeggeX `live_trading` until probe returns 200 (#2, #19)
- **Do not** run laptop + server daemons simultaneously once systemd is healthy
- **Do not** set `EXCHANGE_ROTATION_LIVE=1` on production without explicit opt-in (local max defaults differ)
- **Do not** commit `.env`, vault keys, or raw wallet balances
- **Scope creep (nice-to-have)** — track in [PROFIT_DAEMON_SERVER.md](./PROFIT_DAEMON_SERVER.md#improvements-next), not here:
  - Email/Discord alert when daemon stale > 5 min
  - Grafana-style 24h PPP chart on `/profit/`
  - Per-user daemon tick quota on marketplace agents
  - Public “rent daemon” CTA on exchange Bots tab

---

## Session notes / recent wins

### ec2743b — Profit daemon monitor, hot-pair prefunding, live runtime

- Server 24/7 wiring: deploy script, monitor service, `/profit/` UI updates
- Hot unfunded routes get auto-prefund via swap rotation + pair search index
- Venue balance monitor cache, arb threshold state, extensive PPP ledger population
- Agent account tuning across all arb agents + payments_plus

### 2026-07-04 — 110-upgrade P0/P1 batch (22 shipped)

- Ops service: kill-switch, Discord zero-fill + low-balance alerts, sweep auto-tune, prefund queue
- Pair search: volatility score + triangular bonus; shared hot symbols across fast/exchange loops
- API: `/api/profit-daemon/metrics`, `POST /api/profit-daemon/reload-config`
- Monitor UI: pair_search, hot_prefund, zero_fill tiles; daily PPP summary hook
- Ops: log rotation, `scripts/profit_daemon_healthcheck.sh` for systemd
- Full list: [PROFIT_DAEMON_110_UPGRADES.md](./PROFIT_DAEMON_110_UPGRADES.md)

### ff76442 — Venue execution eligibility

- `venue_execution_eligible` gates private-API venues
- BingX blocked from rotation execution (scan-only); pytest coverage

### 13b49c1 — Profit pair search in arb + AI ticks

- `exchange_profit_pair_search_service` ranks pairs from ledger + catalog
- Hot symbols passed to spatial arb agents and AI trader
- Daemon logs `pair_search` / `search_hot` on each exchange tick

### 5894176 — Profit-first rotation + arb when spreads hot

- Balance refresh before arb/rotation ticks
- Bypass `reduce_notional` cooldown on hot spreads
- Improved `force_attempt` when global threshold is `ready=yes`
- Addresses Top25 #7 (arb_exec_zero) — **restart daemon** for live effect

### Already closed (see Top25 for evidence)

- Live stash credited (#1), WinError 5 wallet lock (#5), auto-sweep min $100 (#11)
- NonKYC DOGE + Binance USDC prefunded (#14, #15, #22)
- Light status report (#18), PPP skill sync (#13, #23, #24)

---

## Related docs

| Doc | Use when |
|-----|----------|
| [PROFIT_DAEMON_110_UPGRADES.md](./PROFIT_DAEMON_110_UPGRADES.md) | Full 110-item roadmap (P0–P3), done vs planned |
| [PROFIT_CRITICAL_TOP25.md](./PROFIT_CRITICAL_TOP25.md) | Full checkbox audit + runbooks (#2, #10, #14, #7) |
| [PROFIT_PATH_PROTOCOL.md](./PROFIT_PATH_PROTOCOL.md) | Ledger research, rotation API, skill evolution |
| [PROFIT_DAEMON_SERVER.md](./PROFIT_DAEMON_SERVER.md) | systemd 24/7 deploy, monitor/news/rentals |
| [LIVE_PROFIT_TRADING.md](./LIVE_PROFIT_TRADING.md) | Path B funding, referral links, live gates |
| [DAEMONS_AND_AGENTS.md](./DAEMONS_AND_AGENTS.md) | All daemon entry points, kill-switch drill |
