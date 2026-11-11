---
title: MN2 sporks recap — unused inventory + new exchange-wallet gates
type: feat
date: 2026-11-11
parent: docs/plans/2026-11-11-wallet-v1.6.6.0-giga-upgrade-plan.md
---

# MN2 sporks recap

## How sporks work here

- A spork is **active** when its value is **less than** current unix time.
- `4070908800` (`SPORK_OFF`, ~year 2099) means **OFF**.
- Site gates: `MN2_SPORK_GATES=1` (default). Override with `MN2_SPORK_OVERRIDE_JSON` for tests/ops.
- Daemon patch for 112–115: `docs/patches/mn2-daemon-v1.3.1-exchange-sporks.patch`.
- New gates 116–121: `docs/patches/mn2-daemon-v1.3.2-wallet-exchange-sporks.patch` (Python live now; daemon needs this patch + release).

## Platform gates already created (112–115)

| Spork | Default | Site use | Status |
| ----- | ------- | -------- | ------ |
| `SPORK_112_EXCHANGE_LIVE_TRADING` | OFF | Live cross-venue trading | **Exists, intentionally unused/off** until ops signs it |
| `SPORK_113_CASINO_REAL_MONEY` | ON | Casino real-money | **In use** |
| `SPORK_114_PAYOUT_LIVE` | OFF | Venue payout / sweep | **Exists, intentionally unused/off** |
| `SPORK_115_MAINTENANCE_MODE` | OFF | Kill-switch | **In use** (blocks exchange/casino/payout when on) |

Do **not** flip 112/114 defaults in app code.

## Defined in Python but unused by app gates

These live in `SPORK_IDS` for RPC show/active parity. The site does not enforce them (daemon/consensus only):

| Spork | Notes |
| ----- | ----- |
| `SPORK_2`…`SPORK_7`, `SPORK_9`…`SPORK_10`, `SPORK_13`…`SPORK_29` | Classic chain / quorum / protocol flags |
| `SPORK_104_MAX_BLOCK_TIME` | Value-style spork (600), not a boolean gate |
| `SPORK_106_STAKING_SKIP_MN_SYNC` | Referenced in tests; not an exchange gate |
| `SPORK_109`…`SPORK_111` | Masternode force/payment/IP policy |

Default **OFF** among those: payment enforcement (8, 9, 10), superblocks/protocol (13–16), MN2 server (25), force MN payment (110).

### Fixed from unused (advisory only)

| Spork | Fix |
| ----- | --- |
| `SPORK_101_SERVICES_ENFORCEMENT` | Surfaced on **X-09** mesh health as advisory (`services_enforcement_active`); still not a money gate |

### Intentional hold (exist, stay off)

| Spork | Why |
| ----- | --- |
| `SPORK_112_EXCHANGE_LIVE_TRADING` | Live venue legs — ops-signed only |
| `SPORK_114_PAYOUT_LIVE` | Venue payout/sweep — ops-signed only |

## ID gaps (never allocated on chain)

Between 10101–10115 the unused numeric IDs are: **10102, 10103, 10105, 10107, 10108**.  
We **do not** fill those gaps (unknown daemon history). New platform gates continue at **10116+**.

## New gates we create (good for exchange wallet)

| ID | Name | Default | Maps to | Purpose |
| -- | ---- | ------- | ------- | ------- |
| 10116 | `SPORK_116_WALLET_ONCHAIN_WITHDRAW` | OFF | X-40 / X-38 | Allow site on-chain MN2 withdraw **broadcast** (assess still runs) |
| 10117 | `SPORK_117_EXCHANGE_VENUE_FAILOVER` | OFF | X-08 | Allow auto RPC/venue promote (not just rank/display) |
| 10118 | `SPORK_118_ANOMALY_HARD_ENFORCE` | ON | X-46 | High anomaly always hard-blocks (fail closed) |
| 10119 | `SPORK_119_POR_PUBLIC_EXPORT` | OFF | X-03 | Public PoR/ledger glance without admin elevation |
| 10120 | `SPORK_120_GUIDED_TRADE_EXECUTE` | OFF | X-40 | Allow guided custodial trade **execute** (quote always ok) |
| 10121 | `SPORK_121_WITHDRAW_WHITELIST_REQUIRED` | OFF | X-38 | Withdrawals must hit whitelist when active |

All money-moving new gates default **OFF**. Safety gate `118` defaults **ON**.

## Ops activate (examples)

```bash
# After daemon patch + -sporkkey
python scripts/mn2_activate_spork_remote.py SPORK_118_ANOMALY_HARD_ENFORCE 1703122560
# Keep money gates off until ready:
# SPORK_116 / 117 / 119 / 120 / 121 stay 4070908800
```
