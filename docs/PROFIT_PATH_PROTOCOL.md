# Profit Path Protocol (PPP)

Structured logging for cross-venue arb and trade research on MasterNoder exchange.

## Purpose

Every scan, quote evaluation, execution attempt, stash, and sweep can be recorded in an append-only ledger. Use it to:

- Compare routes (buy venue → sell venue) by net bps and hit rate
- See why paths were skipped (below threshold, insufficient balance, API errors)
- Feed rule-based improvement suggestions (funding, sizing, credential fixes)

## Files

| File | Role |
|------|------|
| `data/crypto_exchange/profit_path_protocol.json` | Config (enabled, retention, balance venues) |
| `data/crypto_exchange/profit_path_ledger.jsonl` | Append-only event ledger |

## Ledger row schema

```json
{
  "ts": "2026-07-02T12:00:00Z",
  "path_id": "a1b2c3d4",
  "phase": "scan",
  "agent_id": "arb_agent_btc_eth",
  "strategy": "spatial_arb",
  "venues": { "buy": "binance", "sell": "nonkyc" },
  "symbol": "BTC",
  "notional_usd": 250.0,
  "gross_bps": 45.2,
  "fee_bps": 20.0,
  "transfer_bps": 5.0,
  "net_bps": 20.2,
  "threshold_bps": 30.0,
  "decision": "skip",
  "skip_reason": "below_threshold",
  "balances_snapshot": { "binance_usdc": "100-499", "nonkyc_usdt": "25-99" },
  "execution": {},
  "mode": "paper",
  "latency_ms": null
}
```

**Phases:** `scan` | `quote` | `preflight` | `execute` | `stash` | `sweep` | `fail`

**Decisions:** `skip` | `attempt` | `fill` | `paper` | `live`

Balances are **masked bands** (`0`, `<25`, `25-99`, …) — never raw wallet values or secrets.

## API

### Search paths

```
GET /api/exchange/profit-path/search?agent=&symbol=&hours=24&decision=&venue=&min_net_bps=&limit=50
```

### Summary (24h default)

```
GET /api/exchange/profit-path/summary?hours=24
```

Returns scan/attempt/fill counts, hit rate, avg net bps, top skip reasons, best routes (24h / 7d).

### Suggestions

```
GET /api/exchange/profit-path/suggestions?hours=168
```

Rule-based hints: fund inventory, lower notional, fix 401 venues, pause weak routes.

### Admin export

```
GET /api/exchange/profit-path/export?limit=200
```

Requires `EXCHANGE_ADMIN_KEY` (or `admin_key` query param).

## UI

Exchange hub → **Bots** tab → **Profit Path research** panel:

- Summary tiles (scans, attempts, fills, avg net bps, top skip reason)
- Filterable table (last 50 paths)
- Suggestions panel

## Integration points

| Module | When |
|--------|------|
| `exchange_arbitrage_service.run_paper_tick` | One scan row per agent per tick; execution row on attempt |
| `exchange_live_execution_service` | Farm execution + stash events |
| `crypto_exchange_agent_service` | Lighter cross-trade swap rows |
| `exchange_payout_service.execute_sweep` | Sweep rows |

## Research workflow

1. **Run arb ticks** (daemon or `POST /api/exchange/arbitrage/run`) to populate the ledger.
2. **Open Bots → Profit Path research** or call `/profit-path/summary`.
3. **Filter by agent/symbol** to isolate a strategy.
4. **Read top skip reasons** — e.g. `insufficient_venue_balance` → pre-fund quote on buy venue.
5. **Compare routes** in `best_routes_24h` — promote high hit-rate pairs, drop noisy ones.
6. **Apply suggestions** — adjust `min_margin_bps`, notional, or venue list in connector config.
7. **Re-run and compare** summary hit rate and avg net bps week over week.

## Swap rotation (funding unlock)

When live arb scans find spreads but `arb_exec=0` due to venue inventory, the **swap rotation service** analyzes funding gaps and ranks capital moves.

| Function | Purpose |
|----------|---------|
| `analyze_funding_gaps(agent_id, symbol, notional_usd)` | Which leg is short (buy quote vs sell base) via `can_fund_arb_leg` |
| `suggest_swap_actions()` | Ranked list: external quote buy, internal USDC↔USDT, lower notional |
| `execute_rotation(action, dry_run=True)` | Internal stable swap or external market order (live only when `rotation_live_enabled`) |

**API:** `GET /api/exchange/swap-rotation/analyze`, `GET .../suggestions`, `POST .../execute` (admin key, dry_run default true).

**Daemon:** After each exchange tick with zero arb fills, `all_profit_daemons` logs top rotation suggestion and appends a PPP `rotation` phase row.

**Config:** `profit_path_protocol.json` → `rotation_live_enabled` (default false) or env `EXCHANGE_ROTATION_LIVE=1`.

**Top25 items addressed:** #7 arb_exec_zero, #14 nonkyc_doge_low, #15 binance_quote_cap, #22 skip_reason_funding (partial #1/#16 when stash fills after funded arbs).

## Python usage

```python
from backend.services.exchange_profit_path_service import (
    record_scan, record_execution, search_paths, profit_path_summary, suggest_improvements,
)

path_id = record_scan(
    agent_id="arb_agent_btc_eth",
    strategy="spatial_arb",
    best=opportunity_dict,
    threshold_bps=30,
    mode="paper",
    decision="skip",
    skip_reason="below_threshold",
)

rows = search_paths(agent_id="arb_agent_btc_eth", hours=48, min_net_bps=10)
summary = profit_path_summary(hours=24)
hints = suggest_improvements()
```

## Tests

```bash
pytest tests/unit/test_exchange_profit_path.py -q
pytest tests/unit/test_exchange_profit_agent_skills.py -q
```

## Live ledger mode

When `EXCHANGE_ARBITRAGE_LIVE=1`, PPP rows default to `mode: live` (`default_ledger_mode: auto` in config). Force with `default_ledger_mode: live` or `paper`.

## Skill evolution (profit agent skill sets)

Profitable **execute** rows trigger `exchange_profit_agent_skills_service.on_ledger_profit_event`:

- **Profit skills** — specialized per strategy/symbol/route/mode (e.g. `ppp_spatial_arb_btc_binance_to_nonkyc_live`)
- **Void skills** — gap specializations from skip reasons (e.g. `void_mn2_liquidity`, `void_spread_gate`)
- **Level up** — XP from stacked profit (`skill_stack_usd_step` default $0.25)

### API

```
GET  /api/exchange/profit-path/skills?agent=
POST /api/exchange/profit-path/skills/sync   (admin)
GET  /api/exchange/profit-path/critical-top25
POST /api/exchange/profit-path/critical-top25/check  {"id":"xeggex_401","checked":true}
```

### Ops checklist

See [PROFIT_CRITICAL_TOP25.md](./PROFIT_CRITICAL_TOP25.md) — auto-generated checkbox list synced from PPP + live readiness.

```python
from backend.services.exchange_profit_agent_skills_service import (
    sync_from_ledger_research, critical_problems_top25, write_critical_markdown_doc,
)
sync_from_ledger_research(hours=168)
write_critical_markdown_doc()
```
