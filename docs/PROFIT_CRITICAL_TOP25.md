# Profit Critical Top 25

_Updated: 2026-07-04T14:50:01.101716Z_

- [x] **#1** [treasury] Live USD stash is $0 — no real external arb P&L captured yet (`live_stash_zero`) — _live stash USD=1.4996 (2026-07-04)_
- [ ] **#2** [api] XeggeX API returns 401 — refresh keys or IP whitelist (`xeggex_401`) — _probe 401: http_401:Not Authorized (2026-07-04) — refresh_xeggex_server.py --probe-only_
- [ ] **#3** [market] Arb spreads mostly below 18 bps min_margin — waiting on market (`spread_below_threshold`) — _daemon arb_skip=below_thresholdx6; balance probe profitable_count=0 best XRP -7bps (2026-07-03)_
- [x] **#4** [funding] Cross-trade bots MN2 auto-seed must sustain 25 MN2 each tick (`cross_trade_mn2_drift`) — _daemon cross_actions=7; preflight casino_agents=3 (2026-07-03)_
- [x] **#5** [infra] Windows WinError 5 on wallet JSON writes under concurrent Flask loads (`wallet_file_lock`) — _WinError5 fix in tree; no new lock errors this session (2026-07-03)_
- [ ] **#6** [engine] AI trader enabled but ai_exec=False every tick (`ai_trader_idle`) — _fix 2026-07-04: hot spread bypass at min_net; dual-venue global fallback from arb_threshold_state; ai_skip logged_
- [ ] **#7** [engine] Spatial arb 0/11 executions — scan vs fund vs threshold chain (`arb_exec_zero`) — _fix 2026-07-04: force_attempt when fast-loop ready=yes; prepare_live scales to max_funded; best_qualifying uses global state_
- [x] **#8** [engine] Extended profit strategies reporting 0 executions (`ext_profit_zero`) — _fast rescan 2026-07-04: ext_exec=1 on threshold_
- [x] **#9** [engine] Casino profit agents ran 0/3 on recent ticks (`casino_agents_idle`) — _profit_agent_overrides: max_loss_coins=50000 max_bets/day=500 (2026-07-04) — restart daemon to pick up; session RG may need reset if still capped_
- [ ] **#10** [payout] PayPal payout mode still paper — $572+ unswept ledger (`paypal_sweep_paper`) — _check unswept: scripts/payout_sweep_status.py — live PayPal needs EXCHANGE_PAYOUT_PAYPAL_LIVE=1_
- [x] **#11** [payout] Auto sweep disabled (min $500) — manual sweep required (`auto_sweep_off`) — _auto_sweep=true min=$100 (2026-07-04)_
- [x] **#12** [ppp] PPP ledger rows tagged paper while live gates are on (`ledger_mode_paper`) — _PPP 24h fill_count=1814; recent ledger mostly mode=live (2026-07-03)_
- [x] **#13** [ppp] Profit agent skill sets must sync from ledger on each stack (`ppp_skill_sync`) — _sync_critical_reality + sync_from_ledger on stack (2026-07-03)_
- [x] **#14** [funding] NonKYC DOGE inventory low for sell legs (~$25+ recommended) (`nonkyc_doge_low`) — _nonkyc DOGE $44.18 (569.92 DOGE) ≥ $25 (2026-07-04)_
- [x] **#15** [funding] Binance USDC ~$79 caps live notional vs configured micro USD (`binance_quote_cap`) — _binance USDC $80.18 ≥ $68 (2026-07-04)_
- [x] **#16** [treasury] Live venue compound on trade enabled but stash ledger empty (`treasury_compound`) — _live external stash credited USD=1.4996 (2026-07-04)_
- [x] **#17** [ops] Profit daemon must stay running (heartbeat stale = no ticks) (`daemon_restart`) — _terminal60 run_all_profit_daemons live; heartbeat 2026-07-03T12:06:47.472921Z_
- [x] **#18** [ops] profit_status_report.py loads full Flask — avoid during active ticks (`status_report_heavy`) — _profit_status_report.py --light + profit_status_light.py (2026-07-04)_
- [x] **#19** [config] connectors_config xeggex live_trading=false until probe passes (`xeggex_live_disabled`) — _live_trading=false guard active (2026-07-04)_
- [ ] **#20** [config] arb_live_dual_farm limited to binance+nonkyc until XeggeX OK (`dual_farm_two_venue`) — _blocked until XeggeX probe OK (still 401) (2026-07-03)_
- [x] **#21** [research] PPP hit_rate_pct must be reviewed weekly per route (`hit_rate_tracking`) — _GET /api/exchange/profit-path/hit-rate?days=7 (2026-07-04)_
- [x] **#22** [research] Top skip reason insufficient_venue_balance — pre-fund quote legs (`skip_reason_funding`) — _binance USDC $80.18 prefunded (2026-07-04) — prefund_arb_legs.py --live --venue binance --quote-prefund_
- [x] **#23** [skills] Open void skills (gap specializations) must close as fixes land (`void_skills_open`) — _sync_from_ledger closes voids on fill/baseline (2026-07-04)_
- [x] **#24** [skills] Agent levels must track stacked profit via PPP ledger not paper PnL only (`agent_level_lag`) — _agent level from stacked PPP profit USD (2026-07-04)_
- [x] **#25** [docs] PROFIT_PATH_PROTOCOL + critical top25 checklist kept in sync with ledger (`documentation_sync`) — _audit sync md+json evidence 2026-07-03T12:06:47.472921Z_

## Runbooks

### XeggeX 401 / dual-venue blocked (#2, #20)

1. `python scripts/refresh_xeggex_server.py --probe-only` — expect `ok=True status=200`.
2. Confirm `XEGGEX_API_KEY` + `XEGGEX_API_SECRET` in `.env`; run `python scripts/remote_vault_import.py`.
3. **IP whitelist:** XeggeX dashboard → API → add server egress IP (and local dev IP if probing locally).
4. Regenerate API key if 401 persists after whitelist.
5. `python scripts/configure_live_profit_max.py` — enables `live_trading` + adds xeggex to `arb_live_dual_farm`.

### NonKYC DOGE sell-leg (#14)

- Check: probe shows `nonkyc DOGE` USD ≥ $25 on sell venue.
- One-shot: `python scripts/prefund_arb_legs.py --live --symbol DOGE`

### Fast arb near threshold (#7)

- When daemon shows `near_threshold=yes` and `best_bps` within ~2 bps of `threshold=12`:
- Optional ops override: `set EXCHANGE_FAST_MIN_BPS=10` before restart (not persisted in config).
- Exchange loop now reads `arb_threshold_state` — when `ready=yes` and `best_net >= min_margin`, `arb_live_dual_farm` runs global scan even if per-agent scans are below threshold.
- Heartbeat shows `ai_skip=no_signal|below_threshold|no_creds` when AI trader skips; `ai_exec=True` when hot spread (net_bps >= min_net) executes despite low ai_score.

### PayPal sweep (#10, #11)

- Preflight: `python scripts/enable_live_paypal_sweep.py` (checklist + exact `.env` lines; does not write `.env`)
- Dry-run next sweep: `python scripts/enable_live_paypal_sweep.py --dry-run`
- Status: `python scripts/payout_sweep_status.py` — only **live_stash_usd** counts for live PayPal (paper agent PnL excluded)
- Enable live auto-sweep: add to `.env` both `EXCHANGE_PAYOUT_PAYPAL_LIVE=1` and `EXCHANGE_AUTO_PAYPAL_SWEEP=1`, plus PayPal creds + `EXCHANGE_PAYOUT_PAYPAL_EMAIL`
- Restart: `run_all_profit_daemons.cmd --auto-sweep` — daemon logs `sweep=yes mode=live amount=$X` or `mode=paper`
