# Profit daemon body

## Anatomy

| Part | Loop | Role |
|------|------|------|
| **Head** | `head` | Steer arms/legs — quote gate, budget, enable, quarantine awareness, kill-shot, prefund hint, heartbeat, learn/log, kill switch |
| **Arm 1** | `hunter` | Multi-assignment: **backfill** thin quote (head `prefund_hint`) + wide BN↔NK **hunt** + execute |
| **Arm 2** | `dual_farm` | Dual-venue farm + prefund |
| **Leg 1** | `pbook` | Top5 profit order book / techniques map |
| **Leg 2** | `grid` | Maker ladders — thin-quote = fully quiet until auto-resume+reseed |

## Head control file

`data/crypto_exchange/profit_head_control.json` — limbs enabled flags, quote budget, kill_shot, prefund_hint, manual_body_pause.

Arms/legs call `limb_allowed(name)` at tick start.

## Learning + logs

- Head ledger: `profit_head_ledger.jsonl` + agent `arb_profit_head`
- Grid ledger events: `thin_quote_pause/resume`, `asset_quarantine`, `universe_shrink` + agent `arb_grid_leg`
- Hunter prioritizes head kill-shot symbol; clears it after a successful fill
- Hunter owns backfill when quote is thin / head posts `prefund_hint` / last skip was funding — ledger `spread_hunter_ledger.jsonl`, clears hint after a raise

## Ops

```bash
.venv/bin/python scripts/all_profit_daemons.py --profile max --skip-feed
# skip head: --skip-head
```
