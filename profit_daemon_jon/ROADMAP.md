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
- [x] Daemon-own resting book: ladder + maker loop in `all_profit_daemons` (cron limit-tick falls back)
- One-click GitHub Release publish from `pdj-v*` tags (already wired)
- Prefunded arb sender at 15–30s when `EXCHANGE_LIVE_PROFIT_MAX=1` (withdraw-latency plan)
- Chain rebalance stays advisory until fee ≤30 bps and move ≥~$500

## Strategy ownership calc (daemon-only)

| Strategy | Locked / size (snapshot) | Daemon-only? | Why |
|----------|--------------------------|--------------|-----|
| Ladder (NonKYC+Binance) | ~$143 on book, execute on | **Yes** | Product resting book; was cron-only → now `book` loop |
| Maker quotes | ~$11, clip $25, edge 18 bps | **Yes** | Same resting book; pairs with ladder |
| Extended max set | dual/fast/peg/meme/pay/tri/defi | Already in daemon | Keep in fast/exchange ticks |
| Ten spot frameworks | research TA | **No** | Leave cron/search; execute defaults off |
| Fast USDT watcher | watch-only UI | **No** | Desk companion, not an order engine |
| Triangular live | spatial live on loop symbols | **On** when `EXCHANGE_TRIANGULAR_LIVE=1` + SPORK |
| On-chain micro drip | portal MN2 micro-chain | **On** when `MN2_MICRO_CHAIN_LIVE=1` + destination |
| YouTube trade stream | OBS overlay `/trade-stream` | Opt-in interest votes (no auto go-live) |
