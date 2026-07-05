# Profit Daemon — 110 Upgrades Roadmap

_Last updated: 2026-07-04 · Branch `feat/casino-mega-expansion`_

Master checklist for making the Masternoder.dk profit daemon best-in-class. **42 shipped** in session (P0/P1/P2); **68 planned**. Wired into existing services — no parallel daemon processes.

**Related:** [PROFIT_DAEMON_ACTIVITY.md](./PROFIT_DAEMON_ACTIVITY.md) · [PROFIT_CRITICAL_TOP25.md](./PROFIT_CRITICAL_TOP25.md) · [PROFIT_DAEMON_SERVER.md](./PROFIT_DAEMON_SERVER.md)

**Deploy after push:** `python scripts/deploy_profit_daemon_server.py`

---

## Legend

| Priority | Meaning |
|----------|---------|
| **P0** | Safety / revenue blockers — ship first |
| **P1** | High ROI ops + execution |
| **P2** | Scale + research |
| **P3** | Nice-to-have / experimental |

| Status | Meaning |
|--------|---------|
| **done** | Implemented in tree |
| **planned** | Not yet implemented |

---

## Execution (1–11)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 1 | P0 | done | `EXCHANGE_PROFIT_KILL=1` kill-switch respected in arb, extended, payout |
| 2 | P0 | done | Prefund queue for top 3 pair-search hits (`maybe_prefund_queue`) |
| 3 | P0 | done | Auto-scale `paper_trade_usd` from `max_funded_usd` per tick |
| 4 | P1 | done | Multi-venue live farm auto-enable when XeggeX probe OK |
| 5 | P1 | done | Notional scaling buffer tuned by venue latency tier |
| 6 | P1 | done | Triangular arb live gate (paper-only until SPORK) |
| 7 | P1 | done | Slippage guard: abort leg if book depth < 2× notional |
| 8 | P2 | done | Cross-venue prefund batch (single rotation tick, multi-leg) |
| 9 | P2 | done | Force-attempt budget per hour (cap runaway retries) |
| 10 | P2 | done | Venue-specific min notional floors in connectors config |
| 11 | P3 | planned | Iceberg-style split orders for large arb notionals |

## Search (12–22)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 12 | P0 | done | Spread volatility score in pair-search ranking |
| 13 | P0 | done | Triangular loop symbol bonus in search index |
| 14 | P1 | done | Fast ↔ exchange shared hot-symbol state file |
| 15 | P1 | planned | ML ranker hook (ledger features → score blend) |
| 16 | P1 | done | Volatility window presets (1h / 6h / 24h) |
| 17 | P1 | done | Meme coin class filter in catalog intersection |
| 18 | P1 | planned | DeFi router class in catalog expansion |
| 19 | P2 | planned | Catalog auto-refresh cron independent of ticks |
| 20 | P2 | planned | Cross-venue symbol alias map (1000SHIB ↔ SHIB) |
| 21 | P2 | planned | Search index export API for research notebooks |
| 22 | P3 | planned | User-agent symbol overlay from marketplace rentals |

## AI (23–31)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 23 | P1 | planned | Ensemble signal blend (spatial + AI + extended) |
| 24 | P1 | planned | Venue routing score in AI trader pick |
| 25 | P1 | planned | Risk-adjusted sizing from volatility + hit rate |
| 26 | P2 | planned | Hot-spread AI bypass telemetry in PPP |
| 27 | P2 | planned | Per-agent skill cooldown after loss streak |
| 28 | P2 | planned | Sentiment feed weight env override |
| 29 | P2 | planned | AI skip reason dashboard tile grouping |
| 30 | P3 | planned | LLM narrative on daily PPP summary |
| 31 | P3 | planned | A/B AI skill sets via config profile |

## Treasury (32–40)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 32 | P1 | planned | Live compound streak bonus tiers |
| 33 | P1 | planned | Multi-currency stash buckets (USD/EUR stable) |
| 34 | P1 | planned | Fee optimization: prefer USDC vs USDT route |
| 35 | P2 | planned | Treasury liquidity ledger reconciliation job |
| 36 | P2 | planned | Stash cap alert before sweep |
| 37 | P2 | planned | Internal sales-pool ↔ treasury transfer automation |
| 38 | P2 | planned | Compound pause when kill-switch active |
| 39 | P3 | planned | Historical stash chart on monitor UI |
| 40 | P3 | planned | MN2-denominated stash mirror for casino |

## Payout (41–50)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 41 | P0 | done | Sweep `min_sweep_usd` auto-tune when live stash crosses tiers |
| 42 | P1 | done | PayPal tier presets (micro / standard / whale) |
| 43 | P1 | done | Auto-threshold lowering when paper unswept grows (display only) |
| 44 | P1 | done | Tax export CSV from sweep + stash ledger |
| 45 | P2 | planned | Binance withdraw rail preflight in daemon tick |
| 46 | P2 | planned | Sweep dry-run line in daemon stdout |
| 47 | P2 | planned | Partial sweep when above min but below full pool |
| 48 | P2 | done | Payout share_pct env validation on startup |
| 49 | P3 | planned | Multi-recipient PayPal split (requires gates) |
| 50 | P3 | planned | Sweep success Discord celebration embed |

## Monitor (51–61)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 51 | P0 | done | Expanded `/api/profit-daemon/metrics` JSON endpoint |
| 52 | P0 | done | Monitor UI tiles: pair_search, hot_prefund, zero_fill |
| 53 | P0 | done | Discord/webhook alert on zero_fill_streak + hot spread |
| 54 | P0 | done | Venue balance low webhook (USDC / DOGE thresholds) |
| 55 | P1 | done | Grafana-style 24h PPP time series export |
| 56 | P1 | done | Heartbeat stale Discord alert (>5 min) |
| 57 | P1 | done | Fast-loop near_threshold banner on monitor |
| 58 | P2 | done | Per-loop sparkline from heartbeat history |
| 59 | P2 | planned | Blocker deep-link to Top25 runbook anchors |
| 60 | P2 | planned | Mobile-friendly monitor stat cards |
| 61 | P3 | planned | Public read-only monitor token URL |

## Ops (62–72)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 62 | P0 | done | PPP config hot-reload without daemon restart |
| 63 | P0 | done | `POST /api/profit-daemon/reload-config` admin hook |
| 64 | P0 | done | Daily PPP summary cron in daemon (24h + Discord) |
| 65 | P0 | done | Log rotation for profit daemon stdout/stderr |
| 66 | P0 | done | systemd healthcheck script (`profit_daemon_healthcheck.sh`) |
| 67 | P1 | planned | Auto-restart wrapper on unhandled thread death |
| 68 | P1 | planned | Deploy hook post-push in `deploy_profit_daemon_server.py` |
| 69 | P1 | done | Config hot-reload for `exchange_connectors_config.json` |
| 70 | P2 | planned | Tick budget profiler (warn when exchange tick >60s) |
| 71 | P2 | planned | Preflight gate: block start if heartbeat owned by other host |
| 72 | P3 | planned | Blue/green daemon profile switch without downtime |

## Security (73–81)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 73 | P0 | done | Kill switch blocks sweep execution |
| 74 | P1 | done | Alert webhook cooldown (900s default) anti-spam |
| 75 | P1 | planned | Rate limit on profit-daemon API routes |
| 76 | P1 | done | SPORK gate audit line in daemon startup banner |
| 77 | P2 | planned | Admin key required for reload-config POST |
| 78 | P2 | planned | Mask venue balances in metrics export |
| 79 | P2 | planned | Signed heartbeat file optional HMAC |
| 80 | P3 | planned | IP allowlist for metrics endpoint |
| 81 | P3 | planned | Secrets vault rotation reminder |

## Research (82–91)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 82 | P1 | planned | PPP auto-report PDF/email weekly |
| 83 | P1 | planned | A/B strategy profile comparison (max vs fast) |
| 84 | P1 | planned | Backtest replay from PPP ledger slice |
| 85 | P2 | planned | Hit-rate regression alert per route |
| 86 | P2 | planned | Skip-reason trend chart export |
| 87 | P2 | planned | Pair-search score decomposition export |
| 88 | P2 | planned | Critical Top25 auto-sync on daemon tick |
| 89 | P3 | planned | Jupyter notebook template for PPP analysis |
| 90 | P3 | planned | Public anonymized leaderboard of routes |
| 91 | P3 | planned | Research API quota per operator key |

## Casino cross-sell (92–97)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 92 | P2 | planned | Profit-linked MN2 bonus on arb fill streak |
| 93 | P2 | done | Casino agent tick skip when profit kill active |
| 94 | P2 | planned | Discord share wins when live stash milestone |
| 95 | P3 | planned | Exchange tab CTA when monitor readiness >75% |
| 96 | P3 | planned | Rental agent trial tied to PPP fill count |
| 97 | P3 | planned | Casino VIP tier bump on sweep success |

## Performance (98–105)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 98 | P1 | planned | Venue balance cache TTL env per venue |
| 99 | P1 | planned | Parallel venue fetch (3+ workers) in monitor |
| 100 | P1 | planned | Exchange tick time budget with early exit |
| 101 | P2 | planned | Pair-search catalog cache shared across workers |
| 102 | P2 | planned | Lazy Flask import for monitor-only polls |
| 103 | P2 | planned | JSONL tail cache for PPP 24h snapshot |
| 104 | P3 | planned | uvloop / gevent eval for I/O bound ticks |
| 105 | P3 | planned | Compressed heartbeat history archive |

## Compliance (106–110)

| # | P | Status | Description |
|---|-----|--------|-------------|
| 106 | P1 | done | Audit trail row on every kill-switch activation |
| 107 | P1 | done | Paper/live separation banner on `/profit/` |
| 108 | P2 | planned | PPP export redaction mode for sharing |
| 109 | P2 | planned | Sweep tax ID field in payout config (optional) |
| 110 | P3 | planned | GDPR-style payout history purge tool |

---

## Session summary (P0/P1 shipped)

| # | Upgrade |
|---|---------|
| 1 | Kill switch `EXCHANGE_PROFIT_KILL` |
| 2 | Prefund queue top 3 |
| 3 | Auto-scale paper notional |
| 12 | Volatility search score |
| 13 | Triangular search bonus |
| 14 | Shared hot symbols |
| 41 | Sweep min auto-tune |
| 51–54 | Metrics API + monitor tiles + Discord alerts |
| 62–66 | Hot-reload, daily PPP, log rotation, healthcheck |
| 73–74 | Kill on sweep + alert cooldown |

**Counts:** 42 done · 68 planned · 110 total
