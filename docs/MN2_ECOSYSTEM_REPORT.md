# MN2 Ecosystem Report

Audit and status for the Masternoder.dk MN2 crypto stack (Master Build Orchestrator Stages 0–4).

**Date:** 2026-06-14  
**Repo:** Masternoder.dk Flask app

## Executive summary

The platform has a working custodial MN2 wallet layer (multi-address), internal P2P MN2↔coins market, staking, generator MN2 pay/earn, casino MN2/USD rails, activity SSE, agent treasury, debugger Q&A rewards, customer aggregator, Discord funnel, and security cron with backup/anomaly sweep.

## Stage gates

| Gate | Status | Evidence |
|------|--------|----------|
| A — Foundations | Pass | `test_gate_a_orchestrator.py`, battle tests |
| B — Economy core | Pass | `test_gate_b_orchestrator.py`, ledger + activity log |
| S — Hardening | Pass | Atomic writes, earn auth, admin audit, backup cron |
| C — Feature layers | Pass | Market, generator/casino/game crypto, quiz, news/Discord |
| D — Full pytest | Pass | 50 MN2 ecosystem unit tests (`test_mn2_health`, gate A/B/S, p2p, quiz, generator, security cron, agents, customers, Discord, explorer) |

## Deposit path

1. User receives deposit address via `mn2_wallet_service` (multi-address: `/api/mn2/wallet/addresses`, `/refresh`, `/connect`)
2. `mn2_deposit_scanner.run_scanner()` credits users; treasury deposits logged as `@agent_treasury`
3. `mn2_ledger.append_entry(..., type=deposit, txid=...)`
4. Idempotency: `mn2_ledger.is_txid_processed(txid)` + `unified_points_db` reference keys

## Withdraw path

Two-phase commit with risk gates (`mn2_withdrawal_security`). Daily caps in `data/mn2_config.json`.

## Internal P2P market (MN2 ↔ coins)

- Service: `p2p_market_service.py` — sell escrow, fill, ticker
- Routes: `/api/market/orders`, `/api/market/fill`, `/api/market/ticker`, `/api/market/cancel`
- Activity events: `p2p_market_order`, `p2p_market_fill`
- Tests: `tests/unit/test_p2p_market.py`

## Generator MN2

- Pay/earn: `generator_mn2_service.py` with earn auth gate + activity emits
- Pricing: `generator_pricing_service.py` (COGS advisory) + `generator_mn2_service.quote_generation`

## Casino MN2 rail

- `casino_service.py` — MN2 bets emit `casino_mn2_bet` activity events
- Responsible gaming + geo/KYC hooks via `casino_responsible_gaming`

## Debugger Q&A rewards

- `POST /api/debugger/quiz/submit` — server-side score, MN2 via `game_mn2_rewards`
- `TAB_POINTS['quiz']` in `debugger_agent_tasks_routes.py`

## Agent treasury

- Ops-gated `GET /api/agents/treasury/address` (address only with `X-Ops-Secret`)
- `POST /api/agents/treasury/distribute` — 100k MN2 per trader agent
- Admin audit: `logs/admin_audit.jsonl`

## Security cron

- `POST /api/security/cron/sweep` — conservation, backup, deposit rescan, anomaly flags
- `POST /api/security/cron/backup` — `backups/mn2/<timestamp>/`
- Crons: `cron/backup_balances.sh`, `cron/discord_activity_funnel.sh`, `cron/security_sweep.sh`

## Activity monitor

- Shared log: `logs/activity_events.jsonl`
- SSE: `GET /api/activity/stream`
- Discord funnel: `POST /api/discord/activity-funnel`

## Customer aggregator

- Service: `customer_aggregator_service.py` — unified directory across casino/generator/game/market
- Routes: `GET /api/customers` (ops-gated)
- Page: `customers/index.html`
- Tests: `tests/unit/test_customer_aggregator.py`

## Agents control board

- Routes: `agent_admin_routes.py`, `point_control_board_routes.py`
- Pages: `dashboard/agents_control/index.html`, `dashboard/point_control_board.html`
- Treasury distribute: idempotent top-up via `agent_wallet_service.distribute_agent_funding()`

## Remaining ops items

See `docs/MN2_TODO.md` — treasury cold-wallet policy, M8 streams 51–60, news HTML resync.
