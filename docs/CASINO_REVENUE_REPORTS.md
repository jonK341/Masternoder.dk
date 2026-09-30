# Casino revenue reports

Daily rollup of house edge, jackpots, tournaments, reward grants, and big wins.

---

## Service

`backend/services/casino_revenue_report.py`

| Metric | Source |
|--------|--------|
| `house_edge_profit` | `casino_ledger.db` — `SUM(bet) - SUM(payout)` per rail |
| `player_plusses` / `player_minuses` | Sum of positive/negative player `net` per day |
| `push_equals` | Bets with neither win nor loss outcome |
| `big_win_count` / `big_win_total` | Wins ≥ threshold (`CASINO_BIG_WIN_THRESHOLD_*` env) |
| `jackpot_contributions` / `jackpot_awards` | `logs/casino_jackpot_ledger.jsonl` |
| `tournament_buyins` / `tournament_payouts` | `logs/casino_tournament_ledger.jsonl` |
| `reward_deductions` | `logs/casino_quest_claims.json` × quest config coin rewards |

`net_house_after_rewards` = house edge (all rails, mixed units in summary) minus quest coin grants.

---

## HTTP API

| Route | Description |
|-------|-------------|
| `GET /api/casino/revenue/daily?days=7` | Last N UTC calendar days (max 30) |
| `GET /api/casino/revenue/report/today` | Today + `summary` block for dashboards |
| `GET /api/agent/casino/revenue/daily` | Agent parity |
| `GET /api/agent/casino/revenue/report/today` | Agent parity |

Example:

```bash
curl -sS "https://masternoder.dk/api/casino/revenue/report/today" | jq .
curl -sS "https://masternoder.dk/api/casino/revenue/daily?days=7" | jq '.reports[].day, .reports[].house_edge_profit_total'
```

---

## Cron / Discord ops

`cron/casino_daily_revenue_report.sh` — dry-run by default.

```bash
CASINO_REVENUE_DRY_RUN=0 \
CASINO_REVENUE_BASE_URL=https://masternoder.dk \
DISCORD_OPS_WEBHOOK_URL=https://discord.com/api/webhooks/... \
bash cron/casino_daily_revenue_report.sh
```

---

## Tests

```bash
python -m pytest tests/unit/test_casino_global_revenue.py -q
```

---

## Ops notes

- Empty ledger → zeros (safe for new environments).
- Reward deductions are **quest coin grants** from claim logs; shop/achievement grants may be added in a later slice.
- Three rails only: coins, mn2, usd — never `mn2_staked`.
