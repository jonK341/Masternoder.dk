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
- **Winnable Pairs Executor** (`sup_winnable`) runs profit pair search and executes spatial arb on ranked winnable routes only (`exchange_winnable_pairs_service`).
- Business Control UI shows last tick on supervisor cards and an **Orchestration** tab with step results.

## Phase 2 — Live profit pack

- `scripts/configure_live_profit_max.py` — env flags, vault import, connectors/extended/AI tuning, **profit pair search** enabled in PPP config.
- `scripts/mn2_live_pack_verify.py` — JSON report; exit `0` when `profit_live_ready`.
- Business Control overview includes `live_pack` (mode, blockers, venue readiness).


## Phase 3 — Live pack & winnable UI

- **Live pack** tab: env flags, venue readiness, blockers, winnable pairs radar (top hits from pair search).
- Ops smoke: `python3 scripts/mn2_winnable_pairs_smoke.py` (exit 0 when tick succeeds).

## Phase 4 — Supervisor fleet console

- **23 labeled fleet bots** (PA-α…ε, EXT-1…6, TRE-1…3, RSK-1…5, WIN-A…D) with `name`, `label`, `type_label`, `supervisor_name`, and `role_label` merged into `trading_bots_control.json` (`fleet_bots`).
- Business Control **Overview** shows a fleet roster (cards grouped by supervisor) and bot table columns use human names instead of raw `sup_*` ids.
- **`POST /api/exchange/control-board/run-fleet`** — optional JSON `{ "kind": "analytics" | "extended_profit" | "treasury" | "risk" | "winnable_pairs" }`; omit `kind` to tick all fleet kinds. Runs pair search when needed for winnable/analyst/extended lanes. Lighter than **Run all bots** (skips arbitrage paper, AI, cross-trade).
- UI **Run fleet** button triggers the fleet-only tick.

