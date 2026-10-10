# Supervisor fleet — 25 mechanics

Operational fleet under Business Control supervisors (see `exchange_supervisor_fleet_service.FLEET_MECHANICS`).

| Supervisor | Fleet bots | Role |
|------------|-------------|------|
| Profit Analyst | 5 | Symbol-lane spatial arb / trade execution |
| Extended Profit Director | 6 | One strategy each, same direction (`buy_cheap_sell_rich`) |
| Treasury Manager | 3 | Ledger audit, payout readiness, mid sync |
| Risk Officer | 5 | Withdrawal, velocity, caps, audit, steady heartbeat |
| Winnable Pairs Executor | 4 | Sharded pair-search hit execution |

Orchestrator `run_all_bots` runs the full fleet each tick. Overview lists fleet bots in the trading table (`fleet ·` badge).

Live Watch owner tab: fixed API response handling (`res.data`); feed includes control-board audit actions.
