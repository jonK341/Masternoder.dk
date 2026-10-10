# Exchange trust system & Live Watch

Trust scores, tiers, activations, composite intelligence, and the owner/user review consoles for agents, bots, and traders.

## Overview

| Layer | What it measures | Where stored |
|-------|------------------|--------------|
| **User trust** | Level, achievements, agent profit, agents owned, crypto buys | Computed live from leveling + stats |
| **Agent trust** | Profit, ticks, game time, mastery, IQ, activation state | On each owned agent JSON |
| **Composite IQ** | Base IQ + trust multiplier + tier bonus | Refreshed each tick |
| **Activations** | Feature gates (run bots, super agents, premium auto, live payout) | Config + per-agent `activation` |

Paper mode only until live gates (`EXCHANGE_ARBITRAGE_LIVE=1`) are set.

## Trust tiers

| Score | Tier | Icon |
|-------|------|------|
| 0–19 | Unverified | ⚪ |
| 20–39 | Bronze | 🥉 |
| 40–59 | Silver | 🥈 |
| 60–79 | Gold | 🥇 |
| 80–100 | Platinum | 💎 |

Config: `data/exchange_trust_config.json`

## Activations

Users must **activate** each purchased bot (`pending` → `active`) when `require_manual_activation` is true (default).

| Activation ID | Min user trust | Min agent trust | Purpose |
|---------------|----------------|-----------------|---------|
| `run_bots` | 18 | — | Manual/daemon ticks |
| `super_agents` | 50 | 25 | Sentient / super-skill bots |
| `premium_auto` | 40 | — | Premium auto-run |
| `live_payout` | 75 | — | Request Binance stash (still owner-gated) |

Agent states: `pending` | `active` | `paused` | `suspended`

## Intelligence stack

Each tick blends edge from:

1. **Level bonus** — agent level from game time + profit XP  
2. **Learning bonus** — skill proficiency from realized profit (adaptive learning)  
3. **Trust bonus** — agent trust score → up to 12 bps  
4. **Premium / prediction** — premium templates + market uplift  

**Composite IQ** = base IQ + (user trust × 0.55) + tier bonus (Unverified 0 … Platinum +50)

## API routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/exchange/trust/me` | User | Trust profile + activation catalog |
| POST | `/api/exchange/trust/controls` | User | `global_auto_run`, `trust_alerts` |
| POST | `/api/exchange/trust/agent/activate` | User | Set agent activation |
| GET | `/api/exchange/live-watch` | User | User Live Watch (trust + bots + feed) |
| GET | `/api/exchange/live-watch/owner` | Admin | All users + global feed |
| GET/POST | `/api/exchange/trust/policy` | Admin | Owner policy (floor, suspend, manual activation) |
| GET | `/api/exchange/monitor/live` | User | Trading monitor (includes trust fields) |

## UI

- **Exchange → Agent marketplace**: Trust card, Live Watch review panel, enhanced Live trading monitor  
- **Business Control → Live Watch tab**: Owner view of all users, trust, pending activations, audit feed  

## Services

- `backend/services/exchange_trust_service.py` — scoring, gates, controls, policy  
- `backend/services/exchange_live_watch_service.py` — user + owner review consoles  
- `backend/services/exchange_agent_learning_service.py` — profit-based skill learning  
- `backend/services/exchange_trading_monitor_service.py` — unified activity feed  

## Owner policy

File: `data/crypto_exchange/exchange_trust_policy.json`

```json
{
  "min_user_trust_floor": 0,
  "require_manual_activation": true,
  "suspended_users": []
}
```

POST `/api/exchange/trust/policy` with admin key:

- `min_user_trust_floor` — global minimum  
- `require_manual_activation` — new bots start `pending`  
- `suspend_user` / `unsuspend_user` — block trading  

## User flow

1. Buy a bot → starts `pending` (if manual activation on)  
2. Build trust (level up, profit, achievements)  
3. Open **Live Watch** → **Activate**  
4. **Run my bots** or 24/7 master daemon ticks accrue profit  
5. Trust + IQ rise → higher composite edge on each cycle  

## Related docs

- `docs/EXCHANGE_CROSS_VENUE_ARBITRAGE.md` — cross-venue bots  
- `docs/MN2_TODO.md` — roadmap items  

## Tests

```bash
python -m pytest tests/unit/test_exchange_trust.py tests/unit/test_exchange_learning_monitor.py -q
```
