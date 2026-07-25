# MN2 Ecosystem Report

Audit and status for the Masternoder.dk MN2 crypto stack (Stage 0 baseline).

**Date:** 2026-06-14  
**Repo:** Masternoder.dk Flask app

## Executive summary

The platform has a working custodial MN2 wallet layer, staking, P2P marketplace (disabled by default), generator MN2 pay/earn, casino MN2/USD rails, activity SSE, and agent control board. This report documents the end-to-end money path and Stage 0 gate status.

## Deposit path

1. User receives deposit address via `mn2_wallet_service` / `mn2_routes`
2. `mn2_deposit_scanner.run_scanner()` reads daemon RPC, credits via `unified_points_database.add_points(..., 'mn2_balance')`
3. `mn2_ledger.append_entry(..., type=deposit, txid=...)`
4. Idempotency: `mn2_ledger.is_txid_processed(txid)`

**Status:** Implemented. Scanner log: `logs/mn2_deposit_scanner.jsonl`

## Withdraw path

1. User requests withdraw via `/api/mn2/withdraw`
2. Risk checks: `mn2_withdrawal_security` (whitelist, TOTP)
3. Two-phase commit: `mn2_balance_commit` reserve → daemon broadcast → finalize/abort
4. Ledger entry type `withdrawal`

**Status:** Implemented with risk gates. Daily caps in `data/mn2_config.json`.

## Staking

- Service: `mn2_staking_service.py` — custodial pool + browser rig uptime weighting
- Routes: `mn2_staking_routes.py`
- Docs: `docs/MN2_STAKING_PLAN.md`
- M7 advisor: `ai_staking_advisor_service.py` (informational only)

**Status:** Implemented. Real yield requires daemon PoS online.

## Unified balance read path

- Canonical read: `unified_points_database.get_all_points(user_id)` merges file + DB with `max()` per scalar
- File store: `logs/unified_points/<user_id>.json`

**Status:** Implemented. **Gate S:** atomic writes + per-user lock + idempotency on money point types added.

## Ledger reconcile

- Append-only: `data/mn2_ledger.json`
- Conservation check: `mn2_conservation_gate.conservation_gate()`

**Status:** Implemented. Reconciliation cron via `security_cron_routes`. Gate S: `append_entry` is atomic under one lock; deposit/treasury_deposit txids are unique under concurrency.

## Generator MN2

- Pay: `generator_mn2_service.py` debits before encode, refunds on failure
- Earn: finish bonus credits `mn2_balance` + ledger

**Status:** Implemented. Tests: `tests/unit/test_generator_mn2.py`

## Casino MN2 rail

- `casino_service.py` supports `mn2_balance`, `coins`, `casino_fiat_balance`
- PayPal USD on-ramp via `mn2_onramp_routes` / `paypal_routes`

**Status:** Confirmed — MN2 rail active for casino play.

## Stage 0 Gate A checklist

| Check | Endpoint / test | Status |
|-------|-----------------|--------|
| Basic health | `GET /api/health` | Pass |
| MN2 health | `GET /api/mn2/health` | Pass (Hub contract: `daemon_staking`, `discord_outbox`, `network_alerts`; inactive mint → 503 degraded) |
| Themes user | `GET /api/themes/user` | Pass |
| Battle URLs | `tests/unit/test_02_battle.py` | Pass |
| Unified points | Gate S atomic `add_points` | Pass |
| Casino MN2 | `casino_service` currency rails | Pass |

## Critical / upgrades (see MN2_TODO.md)

Canonical board: **`docs/MN2_TODO.md` → Critical / Upgrades** (synced Option D, 2026-07-25).

- **Critical done:** Gate S load tests (B); health Hub contract (A); treasury config-only with `live_distribute=false` (C)
- **Critical open:** do not arm live agent distribute; daemon multi-ping; wallet refresh/connect routes; debugger quiz rewards
- **Upgrades:** Phase residuals (trader cron, news channels, casino cashback, security cron tests, game Monitor tab, AI waves, avatar backfill) + exchange P1 track
