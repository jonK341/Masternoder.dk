# MN2 Ecosystem Report

Audit and status for the MN2 crypto stack through **Stage 4** (master build orchestrator).

**Date:** 2026-07-20  
**Repo:** MN2 Flask app (this repository)  
**Gate endpoints:** `GET /api/health/gate-c` · `GET /api/health/gate-d`

## Executive summary

The platform has a working custodial MN2 wallet layer, staking, P2P trader marketplace, generator MN2 pay/earn, game/battle/starmap crypto claims, casino MN2/USD rails, activity SSE monitor, customer aggregator with avatars, agents control board, security cron, and debugger quiz rewards. Stages 0–3 are implemented in code; Stage 4 hardens tests and documentation. Live treasury funding (600k MN2 → 6×100k agent wallets) remains an ops step.

## Money path (unified)

All MN2 credits/debits flow through `unified_points_database.add_points` with Gate S idempotency on money types, plus `mn2_ledger.append_entry` and `logs/activity_events.jsonl` for observability.

| Path | Service / route | Activity event |
|------|-----------------|----------------|
| Deposit | `mn2_deposit_scanner` → `add_points(mn2_balance)` | `wallet_deposit` |
| Withdraw | `mn2_withdrawal_security` + two-phase commit | `wallet_withdraw` |
| Generator pay/earn | `generator_mn2_service` | `generator_mn2_*` |
| Game rewards | `game_mn2_rewards.credit_mn2` | `game_mn2_reward` |
| Battle / Star Map claims | `battle_routes` / `star_map_routes` | `game_mn2_reward` |
| Casino buy-in | `casino_service.purchase_mn2_buyin_pack` | `casino_mn2_buyin` |
| Debugger quiz | `debugger_quiz_routes` | `debugger_quiz_reward` |
| P2P market | `agent_trader_service` | market trade events |
| Wallet rotate | `mn2_wallet_service.refresh_deposit_address` | `wallet_deposit_address_rotated` |

## Stage gates

### Gate A (Stage 0 — foundations)

| Check | Status |
|-------|--------|
| Basic health `GET /api/health` | Pass |
| MN2 health `GET /api/mn2/health` | Pass (503 when daemon staking inactive) |
| Battle / generator / casino baselines | Pass |

### Gate B (Stage 1 — economy core)

| Check | Status |
|-------|--------|
| Multi-address wallet + ledger | Pass |
| `generator_pricing_service` + `game_mn2_rewards` | Pass |
| Agent treasury address API | Pass (ops deposit pending) |

### Gate S (Stage 1.5 — hardening)

| Check | Status |
|-------|--------|
| Atomic `add_points` + per-user lock | Pass |
| Earn auth (`mn2_earn_auth`) | Pass |
| Idempotency on money point types | Pass |

### Gate C (Stage 2 — feature layers)

| Check | Status |
|-------|--------|
| P2P market + trader agents | Code complete; treasury sign-off + cron on server pending |
| Generator MN2 (`unified_generate_video` charges) | Pass |
| Game crypto (battle + starmap UI claims) | Pass |
| Casino crypto expansion + buy-in emit | Pass |
| Activity events on all earn paths | Pass |
| Debugger Q&A rewards | Pass (`POST /api/debugger/quiz/submit`) |

### Gate D (Stage 3–4 — cross-cutting + hardening)

`GET /api/health/gate-d` → `ready_for_stage_4` when all checks pass:

| Check | Component |
|-------|-----------|
| Gate C prerequisite | `gate_c_status_service` |
| Activity monitor tiles | `activity_monitor_service` + `mn2-activity-monitor.js` |
| Security cron sweep | `security_cron_service` + `cron/security_sweep.sh` |
| Agents control board | `agent_admin_service` |
| Customer avatar backfill | `customer_avatar_service` |
| Trader leveling | `agent_trader_service.trader_level_for_agent` |
| Activity events emit | `activity_events_service` |

**Stage 3 UI:** activity monitor on Profile and Game → Social tab; control board at `/dashboard/agents_control/`.

## Deposit path

1. User receives deposit address via `mn2_wallet_service` / `mn2_routes`
2. `mn2_deposit_scanner.run_scanner()` credits via `add_points(..., 'mn2_balance')`
3. `mn2_ledger.append_entry(..., type=deposit, txid=...)`
4. Rotate: `POST /api/mn2/wallet/refresh` → `wallet_deposit_address_rotated` event

## Withdraw path

Risk checks → two-phase commit → ledger `withdrawal`. Daily caps in `data/mn2_config.json`.

## Staking

`mn2_staking_service.py` — custodial pool + browser rig weighting. Real yield requires daemon PoS online (`daemon_staking` in `/api/mn2/health`).

## Activity monitor (Phase 8)

- SSE: `GET /api/activity/stream`
- Status tiles: `GET /api/activity/monitor`
- Customer events: `customer_new`, `customer_active` from aggregator hooks
- Frontend: `static/js/mn2-activity-monitor.js` on profile + game social tab

## Security cron (Phase 9)

`security_cron_service.run_security_sweep()` — withdrawal risk, reconciliation drift, avatar backfill, session cleanup. Cron: `masternoder-security-sweep.cron.d`.

## Agent treasury (ops pending)

1. `GET /api/agents/treasury/address` — single deposit address
2. User sends 600,000 MN2 (6 × 100,000)
3. `data/treasury_signoff.json` + `POST /api/agents/treasury/distribute`
4. Crons: `masternoder-agents-trader`, `masternoder-agents-treasury`

## Pytest status (Stage 4)

Last full run: **1035+ passed, ~13 failed** (exchange suite env/data drift). Ecosystem-focused tests pass:

- `test_stage2_closeout.py`, `test_stage3_gate_d.py`, `test_stage3_control_security.py`
- `test_game_crypto_claims.py`, `test_activity_stream.py`, `test_debugger_quiz_rewards.py`
- `test_gate_c_status.py`, `test_customer_aggregator.py`

See `docs/MN2_TODO.md` § Stage 4 for remediation backlog.

## Critical / upgrades

- **Critical:** Live treasury 600k deposit + distribute; install agent/security crons on prod via `deploy.py`
- **Critical:** Exchange test suite alignment (venue API cache helpers, swap rotation profit-first flags)
- **Upgrades:** `agent_crypto_rewards_service` stub for routed-chat MN2; Discord M8 streams 51–60 full rollout; Health Ops Hub tile for Gate D
