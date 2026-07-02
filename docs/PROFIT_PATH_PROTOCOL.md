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
```
