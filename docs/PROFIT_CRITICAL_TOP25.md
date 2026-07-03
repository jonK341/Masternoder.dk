# Profit Critical Top 25

_Updated: 2026-07-03T12:07:03.949246Z_

- [ ] **#1** [treasury] Live USD stash is $0 — no real external arb P&L captured yet (`live_stash_zero`) — _external live stash USD=0; stash ledger only paper_arbitrage credits (2026-07-03)_
- [ ] **#2** [api] XeggeX API returns 401 — refresh keys or IP whitelist (`xeggex_401`) — _refresh_xeggex_server.py --probe-only: 401 Not Authorized (2026-07-03)_
- [ ] **#3** [market] Arb spreads mostly below 18 bps min_margin — waiting on market (`spread_below_threshold`) — _daemon arb_skip=below_thresholdx6; balance probe profitable_count=0 best XRP -7bps (2026-07-03)_
- [x] **#4** [funding] Cross-trade bots MN2 auto-seed must sustain 25 MN2 each tick (`cross_trade_mn2_drift`) — _daemon cross_actions=7; preflight casino_agents=3 (2026-07-03)_
- [x] **#5** [infra] Windows WinError 5 on wallet JSON writes under concurrent Flask loads (`wallet_file_lock`) — _WinError5 fix in tree; no new lock errors this session (2026-07-03)_
- [ ] **#6** [engine] AI trader enabled but ai_exec=False every tick (`ai_trader_idle`) — _heartbeat ai_exec=False; no AI fill while spreads below min_net (2026-07-03)_
- [ ] **#7** [engine] Spatial arb 0/11 executions — scan vs fund vs threshold chain (`arb_exec_zero`) — _arb_exec=0/11 best_bps=24.1 arb_block=threshold (not inventory); fixes 21cceb5/d9d6239 (2026-07-03)_
- [x] **#8** [engine] Extended profit strategies reporting 0 executions (`ext_profit_zero`) — _fast+exchange ext_exec=1; near_threshold=yes best_bps=38-43 (2026-07-03)_
- [x] **#9** [engine] Casino profit agents ran 0/3 on recent ticks (`casino_agents_idle`) — _heartbeat casino ran=3/3 (2026-07-03)_
- [ ] **#10** [payout] PayPal payout mode still paper — $572+ unswept ledger (`paypal_sweep_paper`) — _payout_sweep_status: mode=paper net_unswept_usd=493013.05 (2026-07-03)_
- [ ] **#11** [payout] Auto sweep disabled (min $500) — manual sweep required (`auto_sweep_off`) — _daemon auto_sweep=False sweep=no; min_sweep_usd=500 (2026-07-03)_
- [x] **#12** [ppp] PPP ledger rows tagged paper while live gates are on (`ledger_mode_paper`) — _PPP 24h fill_count=1814; recent ledger mostly mode=live (2026-07-03)_
- [x] **#13** [ppp] Profit agent skill sets must sync from ledger on each stack (`ppp_skill_sync`) — _sync_critical_reality + sync_from_ledger on stack (2026-07-03)_
- [x] **#14** [funding] NonKYC DOGE inventory low for sell legs (~$25+ recommended) (`nonkyc_doge_low`) — _live API: nonkyc 458.96 DOGE + binance 413.59 DOGE (sell-leg guards OK) (2026-07-03)_
- [x] **#15** [funding] Binance USDC ~$79 caps live notional vs configured micro USD (`binance_quote_cap`) — _live Binance USDC free=79.05; paper_trade_usd capped ~82.6 (2026-07-03)_
- [ ] **#16** [treasury] Live venue compound on trade enabled but stash ledger empty (`treasury_compound`) — _compound_on_venues enabled; no non-paper external stash rows (2026-07-03)_
- [x] **#17** [ops] Profit daemon must stay running (heartbeat stale = no ticks) (`daemon_restart`) — _terminal60 run_all_profit_daemons live; heartbeat 2026-07-03T12:06:47.472921Z_
- [x] **#18** [ops] profit_status_report.py loads full Flask — avoid during active ticks (`status_report_heavy`) — _profit_status_report.py --light path documented (2026-07-03)_
- [x] **#19** [config] connectors_config xeggex live_trading=false until probe passes (`xeggex_live_disabled`) — _connectors xeggex live_trading=false until probe 200 (2026-07-03)_
- [ ] **#20** [config] arb_live_dual_farm limited to binance+nonkyc until XeggeX OK (`dual_farm_two_venue`) — _blocked until XeggeX probe OK (still 401) (2026-07-03)_
- [x] **#21** [research] PPP hit_rate_pct must be reviewed weekly per route (`hit_rate_tracking`) — _profit_path_summary 24h hit_rate_pct=97.2 fills=1814 (2026-07-03)_
- [~] **#22** [research] Top skip reason insufficient_venue_balance — pre-fund quote legs (`skip_reason_funding`) — _[partial] rotation 20/28 success; top skip below_threshold; insufficient_venue_balance 32x/24h (2026-07-03)_
- [x] **#23** [skills] Open void skills (gap specializations) must close as fixes land (`void_skills_open`) — _sync_from_ledger closes voids on fill/baseline (2026-07-03)_
- [x] **#24** [skills] Agent levels must track stacked profit via PPP ledger not paper PnL only (`agent_level_lag`) — _levels track stacked PPP profit USD (2026-07-03)_
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

### PayPal sweep (#10, #11)

- Status: `python scripts/payout_sweep_status.py`
- Enable: `run_all_profit_daemons.cmd --auto-sweep` + `EXCHANGE_AUTO_PAYPAL_SWEEP=1` (+ live PayPal gate).
