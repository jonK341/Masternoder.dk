# Profit Critical Top 25

_Updated: 2026-07-02T19:03:42.674785Z_

- [ ] **#1** [treasury] Live USD stash is $0 — no real external arb P&L captured yet (`live_stash_zero`)
- [ ] **#2** [api] XeggeX API returns 401 — refresh keys or IP whitelist (`xeggex_401`)
- [ ] **#3** [market] Arb spreads mostly below 18 bps min_margin — waiting on market (`spread_below_threshold`)
- [x] **#4** [funding] Cross-trade bots MN2 auto-seed must sustain 25 MN2 each tick (`cross_trade_mn2_drift`)
- [x] **#5** [infra] Windows WinError 5 on wallet JSON writes under concurrent Flask loads (`wallet_file_lock`)
- [ ] **#6** [engine] AI trader enabled but ai_exec=False every tick (`ai_trader_idle`)
- [ ] **#7** [engine] Spatial arb 0/11 executions — scan vs fund vs threshold chain (`arb_exec_zero`) — _rotation analyzes fund chain after zero-fill ticks_
- [ ] **#8** [engine] Extended profit strategies reporting 0 executions (`ext_profit_zero`) — _fast_arb_rescan executes on threshold when `ready=yes`; fast loop logs `best_bps` vs `threshold`_
- [ ] **#9** [engine] Casino profit agents ran 0/3 on recent ticks (`casino_agents_idle`)
- [ ] **#10** [payout] PayPal payout mode still paper — $572+ unswept ledger (`paypal_sweep_paper`)
- [ ] **#11** [payout] Auto sweep disabled (min $500) — manual sweep required (`auto_sweep_off`)
- [x] **#12** [ppp] PPP ledger rows tagged paper while live gates are on (`ledger_mode_paper`)
- [x] **#13** [ppp] Profit agent skill sets must sync from ledger on each stack (`ppp_skill_sync`)
- [ ] **#14** [funding] NonKYC DOGE inventory low for sell legs (~$25+ recommended) (`nonkyc_doge_low`) — _rotation service suggests DOGE buy_
- [ ] **#15** [funding] Binance USDC ~$79 caps live notional vs configured micro USD (`binance_quote_cap`) — _rotation suggests lower notional or quote top-up_
- [ ] **#16** [treasury] Live venue compound on trade enabled but stash ledger empty (`treasury_compound`)
- [x] **#17** [ops] Profit daemon must stay running (heartbeat stale = no ticks) (`daemon_restart`)
- [ ] **#18** [ops] profit_status_report.py loads full Flask — avoid during active ticks (`status_report_heavy`)
- [ ] **#19** [config] connectors_config xeggex live_trading=false until probe passes (`xeggex_live_disabled`)
- [ ] **#20** [config] arb_live_dual_farm limited to binance+nonkyc until XeggeX OK (`dual_farm_two_venue`)
- [ ] **#21** [research] PPP hit_rate_pct must be reviewed weekly per route (`hit_rate_tracking`)
- [ ] **#22** [research] Top skip reason insufficient_venue_balance — pre-fund quote legs (`skip_reason_funding`) — _swap rotation service + PPP rotation phase_
- [ ] **#23** [skills] Open void skills (gap specializations) must close as fixes land (`void_skills_open`)
- [ ] **#24** [skills] Agent levels must track stacked profit via PPP ledger not paper PnL only (`agent_level_lag`)
- [x] **#25** [docs] PROFIT_PATH_PROTOCOL + critical top25 checklist kept in sync with ledger (`documentation_sync`)

