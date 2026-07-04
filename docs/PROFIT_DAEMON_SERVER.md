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
- [ ] Public “rent daemon” CTA on exchange Bots tab → `/profit/#rent`

## Commands

```bash
# Local (dev only)
scripts/run_all_profit_daemons.cmd --auto-sweep

# Server install (SSH on box)
bash /var/www/html/scripts/install_profit_daemon_server.sh

# Deploy from laptop
python scripts/deploy_profit_daemon_server.py

# Status
curl https://masternoder.dk/vidgenerator/api/profit-daemon/status
systemctl status masternoder-profit-daemon.service
tail -f /var/www/html/logs/profit_daemon_stdout.log
```


## Troubleshooting (Windows CRLF)

If install fails with `set: -` / `$'\r': command not found` or paths containing `'\r'`, the script was saved with Windows line endings. Re-deploy from git (repo enforces `*.sh` LF via `.gitattributes`), or on the server:

```bash
sed -i 's/\r$//' /var/www/html/scripts/install_profit_daemon_server.sh
sed -i 's/\r$//' /var/www/html/scripts/run_profit_daemon_server.sh
```

## Cron fallback

Legacy `cron/exchange_master_tick.sh` runs a **single** `exchange_master_daemon.py --once` tick. Prefer **systemd** for full stack. Keep cron as backup only if systemd fails.
