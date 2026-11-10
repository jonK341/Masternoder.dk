# The Profit Daemon Jon — finished-product roadmap

```bash
.venv/bin/python profit_daemon_jon/run.py --backlog
```

All **25/25** finished-product checklist items are marked **done** in
`product_improvement_backlog()` (strategy upgrades, packaging, Docker/Grafana
compose, wizard, tray, vault gate, sales API, macOS+signed Windows release
workflow, 5-minute install guide, CI smoke).

## Keep improving (beyond the checklist)

- [x] Calibrate fill-model online from new fills each hour (`run_desk_maintenance_tick` in `all_profit_daemons`)
- [x] Auto NonKYC dust conversion schedules (same desk loop; also ladder top-up)
- One-click GitHub Release publish from `pdj-v*` tags (already wired)
- Prefunded arb sender at 15–30s when `EXCHANGE_LIVE_PROFIT_MAX=1` (withdraw-latency plan)
- Chain rebalance stays advisory until fee ≤30 bps and move ≥~$500
