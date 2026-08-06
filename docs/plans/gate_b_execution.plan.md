---
name: Gate B Execution (Stage 1 Economy Core)
overview: "Close Gate B: mn2_ledger + activity events, generator_pricing_service, game_mn2_rewards, wallet multi-address, agent treasury address."
todos:
  - id: economy-services
    content: "Verify generator_pricing, game_mn2_rewards, mn2_ledger, activity_events services"
    status: completed
  - id: wallet-multi-address
    content: "Expose GET /api/mn2/wallet/addresses, POST refresh, POST connect"
    status: completed
  - id: gate-b-health
    content: "GET /api/health/gate-b readiness endpoint + gate_b_status_service"
    status: completed
  - id: gate-b-tests
    content: "test_gate_b_orchestrator.py all green (9+ tests)"
    status: completed
  - id: prod-verify
    content: "Deploy + curl /api/health/gate-b on prod"
    status: completed
isProject: false
---

# Gate B Execution — Stage 1 Economy Core

**Prerequisites:** Gate A closed, Gate S hardening deployed.

**Unlocks:** Stage 2 money features (market, generator-crypto, game-rewards, casino-crypto).

---

## Gate B checklist

| Check | Implementation | Status |
|-------|----------------|--------|
| `mn2_ledger` append | `backend/services/mn2_ledger.py` | Done |
| `activity_events.jsonl` emitting | `activity_events_service.emit` | Done |
| `generator_pricing_service` | COGS-aware `pricing_suggestion()` | Done |
| `game_mn2_rewards` | Unified `credit_mn2()` path | Done |
| Wallet multi-address | `list_user_addresses`, `refresh_deposit_address`, `connect_external_wallet` | Done |
| Agent treasury address | `GET /api/agents/treasury/address` (ops-only) | Done |
| P2P market baseline | `p2p_market_service.list_orders()` | Done |
| Gate B health | `GET /api/health/gate-b` | Done |

---

## New API routes (Gate B)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health/gate-b` | Economy core readiness |
| GET | `/api/mn2/wallet/addresses` | List user deposit addresses |
| POST | `/api/mn2/wallet/refresh` | Rotate primary address |
| POST | `/api/mn2/wallet/connect` | Register external/watch wallet |
| GET | `/api/generator/pricing` | Public MN2 generation quotes |
| GET | `/api/cogs/pricing-suggestion` | COGS pricing advisory |

---

## Test command

```bash
python3 -m pytest tests/unit/test_gate_b_orchestrator.py -q
```

Expected: **9 passed**.

---

## Prod verification

```bash
curl -sS https://PROD_HOST/api/health/gate-b | jq .
curl -sS "https://PROD_HOST/api/mn2/wallet/addresses?user_id=test_user" | jq .
curl -sS "https://PROD_HOST/api/generator/pricing?duration=120" | jq .
```

---

## Next: Stage 2 / Gate C

- P2P market live orders + agent trader funding
- Generator MN2 pay/earn on request paths (Gate S compliant)
- Game crypto rewards wired to battle/starmap UI
- All money paths emit `activity_events.jsonl`
