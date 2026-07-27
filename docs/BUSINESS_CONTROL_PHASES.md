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

## Phase 5 — Fleet operations console

- **`fleet_meta`** persists last fleet-only run (`last_run_at`, `last_run_kind`, `last_results` with per-kind `ok_count`/`bot_count`, rolling `history`).
- Overview **`supervisor_fleet.health`** — bot counts, failed/never-ran telemetry; fleet roster cards respect kill-switch + supervisor pause (`enabled`).
- **Orchestration** tab shows fleet step detail as `ok/total bots` when `run_all_bots` includes fleet kinds.
- **Fleet ops** tab — health panel, per-kind run buttons, roster duplicate, recent fleet run history.
- Ops smoke: `python3 scripts/mn2_supervisor_fleet_smoke.py --local` (optional `--kind risk`).

## Phase 6 — Finish (tests, preflight, deploy, UI)

### Automated gate

On the app host (or CI with repo checkout):

```bash
cd /var/www/html   # or repo root
DAEMON_QUIET=1 LITE_APP=1 python3 scripts/mn2_business_control_finish.py
```

Runs Phase 6 unit tests, local preflight, prints deploy/activate hints. Options:

- `--skip-tests` / `--skip-preflight`
- `--http --base <app-url>` — also hits `GET /api/exchange/control-board/preflight` and light overview (needs `EXCHANGE_ADMIN_KEY`)
- `--deploy` — runs `python3 scripts/deploy.py business_control`
- `--prod-tick` — one local `run_supervisor_fleet(kind=risk)` smoke

### Preflight only

```bash
python3 scripts/mn2_business_control_preflight.py
python3 scripts/mn2_business_control_preflight.py --http --base <app-url>
```

`GET /api/exchange/control-board/preflight` (admin key) returns the same local check bundle.

### Deploy manifest

```bash
python3 scripts/deploy.py business_control
```

Uploads Business Control HTML/CSS/JS, control-board services, fleet + preflight, ops scripts, and restarts app workers.

### UI

- Styles moved to `static/css/business-control.css` (responsive tables, sticky header, focus rings, reduced motion).
- **Fleet ops** tab includes live **Preflight** panel.

### Unit test bundle (Phase 6)

- `tests/unit/test_business_control_preflight.py`
- `tests/unit/test_trading_bots_control.py`
- `tests/unit/test_exchange_control_board.py`
- `tests/unit/test_supervisor_fleet.py`

## Phase 7 — Fleet rewards & leveling

- **`exchange_fleet_progression_service.py`** — per-bot XP from fleet ticks (success, executions, streaks) and account trade/profit sync; level bands (200 XP/level); reward catalog M26–M27.
- Overview **`supervisor_fleet.progression_summary`** — fleet commander level/rank from total XP, avg bot level, rewards unlocked.
- Roster cards show **Lv**, rank title, XP bar, and reward tier count; Fleet ops tab shows commander XP strip.
- Tests: `tests/unit/test_fleet_progression.py`

## Phase 8 — 5D progress navigation monitor (public)

- **`GET /api/exchange/fleet-progress-monitor/public`** — audience-safe fleet XP, coarse trade bands, activity ticker; no PII.
- **`FLEET_PROGRESS_MONITOR_PUBLIC`** (default on); **`FLEET_MONITOR_EMBED_TOKEN`** optional for `?embed=1` API calls.
- Page **`/fleet-progress-monitor/`** — canvas 5D projection, opt-in Web Audio + speech narrator, `?mode=stream` for YouTube layout.
- **`/streamer/`** — broadcast hub: iframe to latest stream monitor, Camgirl co-host strip, copy OBS URL (`?obs=1` hides chrome). Alias **`/fleet-stream/`** → stream layout only.
- Podcast co-broadcast on streamer: latest verified episode audio + portal strip; discuss launches via platform news.
- **YouTube stream agents** — `youtube_stream_agent` skill set, `GET /api/exchange/youtube-stream/controls`, assign + preflight on Streamer hub and `?mode=stream` monitor layout.
- **Stream chapter composer** — six rotating chapters with base64-encoded AI copy (decoded server-side), `composer` block on public monitor + `GET /api/exchange/fleet-stream/composer`, live dock on streamer and stream layout.
- Homepage embed section loads stream iframe + summary pill.
- Stream merges **fleet**, **casino** (anonymized wins + daily stats), and **agents** (ability tracker + casino spectator lines).
