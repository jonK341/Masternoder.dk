# Business Control activation phases

## Phase 0 — Ops activation

Run on the app host after deploy:

```bash
cd /var/www/html
DAEMON_QUIET=1 LITE_APP=1 python3 scripts/mn2_business_control_activate.py --local
```

Or via HTTP (uses `EXCHANGE_ADMIN_KEY` from `.env`):

```bash
python3 scripts/mn2_business_control_activate.py --base http://127.0.0.1:5000
```

This turns off the kill switch, enables all supervisors and bots, clears per-bot overrides, and runs one `run_all_bots` tick.

## Phase 1 — Orchestration visibility

- `run_all_bots()` persists `orchestration.last_run_*` and per-supervisor `last_run_at` / `last_run_ok` in `data/crypto_exchange/trading_bots_control.json`.
- Risk, Profit Analyst, and Treasury supervisors run lightweight ticks each orchestrator cycle (withdrawal risk summary, P&amp;L rollup, treasury ledger snapshot).
- Business Control UI shows last tick on supervisor cards and an **Orchestration** tab with step results.

## Phase 2 — Live profit pack

- `scripts/configure_live_profit_max.py` — env flags, vault import, connectors/extended/AI tuning, **profit pair search** enabled in PPP config.
- `scripts/mn2_live_pack_verify.py` — JSON report; exit `0` when `profit_live_ready`.
- Business Control overview includes `live_pack` (mode, blockers, venue readiness).


See [PROFIT_CRITICAL_TOP25.md](./PROFIT_CRITICAL_TOP25.md) for live-profit blockers (XeggeX 401, spreads, PayPal live, dual-venue farm).
