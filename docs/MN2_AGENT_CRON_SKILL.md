# MN2 Transaction Cron — Agent Skill

Use this skill when automating MN2 reward settlement, battle auto-claims, deposit scanning, or blockchain wallet payouts across game, battle, quests, generator, aggregator, and casino systems.

## Run settlement (ops API)

```bash
curl -X POST -H "X-Ops-Token: $MN2_OPS_SECRET" \
  "http://127.0.0.1:5000/api/mn2/ops/settle-ecosystem?systems=all"
```

Systems: `battle`, `chain`, `scan`, or `all`.

## Run via agent cron

```bash
curl -X POST -H "X-Agent-Cron-Token: $AGENT_CRON_SECRET" \
  "http://127.0.0.1:5000/api/agents/cron/run?jobs=mn2_settlement"
```

Presets: `mn2`, `mn2_settlement`, `game_battle_mn2`

## Shell cron

`cron/game_battle_mn2_settle.sh` — schedule every 5 minutes with `cron/mn2_scan_deposits.sh`.

## Key services

- `backend/services/agent_mn2_settlement_service.py`
- `backend/services/game_mn2_rewards.py` — instant credit + optional chain tx
- `backend/services/mn2_chain_rewards_service.py`
- `data/mn2_config.json` — `instant_deposits`, `chain_reward_payouts`

## Profile wallet APIs

- `GET /api/mn2/wallet/addresses`
- `POST /api/mn2/wallet/create` — `{ "label": "savings" }`
- `POST /api/mn2/wallet/refresh`
- `GET /api/mn2/profile-monitor?days=5`

See also `docs/AGENTS_MN2.md`.
