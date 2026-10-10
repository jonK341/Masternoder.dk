# Profit Daemon — 24/7 Server Plan

_Updated: 2026-07-04_

## Goal

Run **all profit engines on masternoder.dk** without a laptop: spatial arb, AI trader, cross-trade, extended strategies, casino, PayPal auto-sweep.

## Architecture

```mermaid
flowchart LR
  systemd[masternoder-profit-daemon.service]
  runner[run_profit_daemon_server.sh]
  daemon[all_profit_daemons.py]
  hb[heartbeat.json]
  news[platform_news.json]
  api[/api/profit-daemon/status]
  ui[/profit/ monitor]
  home[Front page news]

  systemd --> runner --> daemon
  daemon --> hb
  daemon --> news
  hb --> api --> ui
  news --> home
```

## Checklist

### Server ops (24/7)

- [x] `systemd/masternoder-profit-daemon.service` — restart always, logs under `logs/`
- [x] `scripts/run_profit_daemon_server.sh` — sources `.env`, runs `all_profit_daemons.py`
- [x] `scripts/install_profit_daemon_server.sh` — enable + start systemd unit
- [x] `scripts/deploy_profit_daemon_server.py` — upload + install on production
- [ ] **Run deploy** on server: `python scripts/deploy_profit_daemon_server.py`
- [x] `.env` gates: `EXCHANGE_ARBITRAGE_LIVE=1`, `EXCHANGE_PAYOUT_PAYPAL_LIVE=1`, `EXCHANGE_AUTO_PAYPAL_SWEEP=1`
- [x] `payout_config.json`: `auto_sweep=true`, `min_sweep_usd=100`
- [ ] Fix `.env` line 19 separator (`./.env: line 19: command not found` when sourcing)
- [ ] Stop laptop daemon after server systemd is healthy (avoid double ticks)

### Monitor & news

- [x] `GET /api/profit-daemon/status` — heartbeat, treasury, payout, PPP 24h
- [x] `GET /api/profit-daemon/news` — profit channel feed
- [x] `GET /api/profit-daemon/rentals` — daemon rental catalog
- [x] `/profit/` page — Monitor · Profit news · Rent/buy · Rewards tabs
- [x] Nav tab **Profit Daemon** in `navigation-toolbar.js`
- [x] Front page merges `/api/profit-daemon/news` into home news list
- [x] Daemon publishes profit news on fills / sweeps / cross-trade (throttled)
- [x] PayPal checkout capture loop (`PROFIT_DAEMON_PAYPAL_FINISH=1`, default) — `finish_pending_paypal_orders` every 10m
- [x] Stale PayPal pending prune (`PROFIT_DAEMON_PAYPAL_PRUNE=1`, default) — drops `RESOURCE_NOT_FOUND` / dead checkouts
- [x] Exchange tick ops wired (`run_exchange_tick_ops`) — auto-sweep backup, treasury alerts, catalog refresh
- [x] Background ops loop (`PROFIT_DAEMON_BACKGROUND_OPS=1`) — sync `payout_config` from `.env`, log rotate, worker health
- [x] `/api/health/system` includes `profit_daemon` + Discord alert when heartbeat stale
- [x] `POST /api/paypal/webhook` — `CHECKOUT.ORDER.APPROVED` immediate capture + rail fan-out (also via subscription webhook handler)
- [x] Dual-venue prefund tick (`PROFIT_DAEMON_VENUE_PREFUND=1`) — `fund_venue_legs_for_symbol` on hot symbols each exchange loop

### User integration (rent / shop / rewards)

- [x] Rentals: `rent_daemon_cross_7d`, `rent_daemon_ai_3d` in `exchange_rental_config.json`
- [x] Shop vouchers: cross daemon + AI daemon trial vouchers
- [x] Shop: Profit Monitor Pass (MN2 + XP reward)
- [x] Completion rewards on rentals (MN2 + XP in rental config)
- [ ] Link shop checkout → `exchange_shop_service.fulfill_item` for new voucher SKUs (verify in UI)

### Improvements (next)

- [ ] Email/Discord alert when daemon stale > 5 min
- [ ] Grafana-style chart on `/profit/` (24h PPP profit curve)
- [ ] User-owned daemon slice: per-user tick quota on marketplace agents
- [ ] XeggeX 401 → dual-venue farm (#2 critical)
- [x] Public “rent daemon” CTA on exchange Bots tab → `/profit/#rent` (`readiness-cta` API + `exchange-hub.js`)
- [x] Paper vs live payout ledger banner on `/profit/` monitor (`payout_ledger_split`)
- [x] Discord/news on PayPal capture batch + existing sweep/stale heartbeat alerts

## PayPal-first profile (production default)

`EXCHANGE_PROFIT_PROFILE=paypal` runs exchange ticks (deals + auto-sweep) and PayPal capture every ~10m, **without** the fast/grid/casino threads that burned CPU on `max` + `EXCHANGE_LIVE_PROFIT_MAX=1`.

- Pair search throttled: `EXCHANGE_PAIR_SEARCH_MIN_INTERVAL_SEC=120`
- Lower scheduler priority: `PROFIT_DAEMON_NICE=10`
- Use system Python on server: `PYTHON_BIN=python3` (broken `.venv` on box)
- Strip CRLF in `.env` when sourcing (`run_profit_daemon_server.sh`)

## Commands

```bash
# Local (dev only)
scripts/run_all_profit_daemons.cmd --auto-sweep

# Server install (SSH on box)
bash /var/www/html/scripts/install_profit_daemon_server.sh

# One-shot PayPal capture (after buyer APPROVED)
python3 scripts/finish_pending_paypal_orders.py

# Deploy from laptop
python scripts/deploy_profit_daemon_server.py

# Status
curl https://masternoder.dk/vidgenerator/api/profit-daemon/status
systemctl status masternoder-profit-daemon.service
tail -f /var/www/html/logs/profit_daemon_stdout.log
```

## Cron fallback

Legacy `cron/exchange_master_tick.sh` runs a **single** `exchange_master_daemon.py --once` tick. Prefer **systemd** for full stack. Keep cron as backup only if systemd fails.
