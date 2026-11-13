# Profit daemon body

## Anatomy

| Part | Loop | Role |
|------|------|------|
| **Head** | `head` | Steer arms/legs/tools — quote gate, budget, enable, quarantine awareness, kill-shot, prefund/courier hints, heartbeat, learn/log, kill switch |
| **Arm 1** | `hunter` | Multi-assignment: **backfill** + **hunt** + **technique executor** + residual-edge gate + execute |
| **Arm 2** | `dual_farm` | Dual-venue farm + prefund + residual-edge gate |
| **Arm 3** | `courier` | Keep **Binance** current + **quote-bridge** for unfunded top route + equalize floors |
| **Tool** | `latch` | Arm on skew/phantom residual; **maker** rest while waiting; strike when residual clears |
| **Tool** | `closer` | Finish half-filled spatial legs (micro-clips) + harvest dust into quote |
| **Tool** | `executor` | Apply pbook techniques (prefund / quote-bridge / size-to-funded) for top deal |
| **Leg 1** | `pbook` | Top5 profit order book / techniques map — **APPLY on** in live (executor stack) |
| **Leg 2** | `grid` | Maker ladders — thin-quote = fully quiet until auto-resume+reseed |

## Head control file

`data/crypto_exchange/profit_head_control.json` — limbs enabled flags, quote budget, kill_shot, prefund_hint, manual_body_pause.

Arms/legs call `limb_allowed(name)` at tick start.

## Learning + logs

- Head ledger: `profit_head_ledger.jsonl` + agent `arb_profit_head`
- Grid ledger events: `thin_quote_pause/resume`, `asset_quarantine`, `universe_shrink` + agent `arb_grid_leg`
- Hunter prioritizes head kill-shot symbol; clears it after a successful fill
- Hunter owns backfill when quote is thin / head posts `prefund_hint` / last skip was funding — ledger `spread_hunter_ledger.jsonl`, clears hint after a raise
- Courier ledger: `courier_arm_ledger.jsonl` · Latch: `latch_sniper_ledger.jsonl` · Closer: `closer_claw_ledger.jsonl` + `closer_open_legs.json`
- Technique executor ledger: `technique_executor_ledger.jsonl`
- Residual edge = `net_bps − |mid_skew_bps|` (floor `TECH_RESIDUAL_EDGE_BPS`, default 15) — filters phantom OP-like edges
- Cron fallback (when daemon is down): `cron/exchange_technique_executor.sh`

## Ops

```bash
.venv/bin/python scripts/all_profit_daemons.py --profile max --skip-feed
# skip head: --skip-head
# skip technique executor loop: --skip-executor
```
