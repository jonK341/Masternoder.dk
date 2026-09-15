# MN2 Transaction Cron — Agent Skill

Use this skill when automating MN2 reward settlement, battle auto-claims, deposit scanning, daemon health probes, or blockchain wallet payouts across game, battle, quests, generator, aggregator, casino, and staking systems.

## Systems covered

| System | Settlement action |
|--------|-------------------|
| `daemon` | RPC health probe (`masternoder2d`) |
| `battle` | Auto-claim eligible crypto options |
| `aggregator` | Credit monitor-move / progress rewards |
| `generator` | Daily finish-bonus credits |
| `casino` | Run casino agent ticks |
| `staking` | Run staking agent ticks |
| `chain` | Push pending rewards on-chain |
| `scan` | Deposit scanner (0-conf when enabled) |
| `reconcile` | Staking conservation check |
| `activity` | Burst agent activity feed events |
| `shop` | Agent shop finish ticks |
| `masternodes` | Restore paid rentals + `startmasternode` (bring rented nodes online) |

## Daemon health

```bash
# CLI probe (exit 0 = healthy)
python scripts/mn2_daemon_test.py
python scripts/mn2_daemon_test.py --extended

# HTTP
curl http://127.0.0.1:5000/api/mn2/daemon/health
curl http://127.0.0.1:5000/api/agent/mn2/daemon/health?extended=1
```

## Rented masternodes (bring online)

```bash
# Snapshot (no explorer hang): registry + daemon RPC
python scripts/mn2_bring_rented_online.py
curl http://127.0.0.1:5000/api/mn2/masternode/rented-status
curl http://127.0.0.1:5000/api/agent/mn2/masternodes/status

# Restore paid-order hosts, provision pending, startmasternode (ops)
python scripts/mn2_bring_rented_online.py --start
curl -X POST -H "X-Ops-Token: $MN2_OPS_SECRET" \
  "http://127.0.0.1:5000/api/mn2/masternode/bring-online?limit=50"
curl -X POST -H "X-Agent-Cron-Token: $AGENT_CRON_SECRET" \
  "http://127.0.0.1:5000/api/agent/mn2/masternodes/bring-online"
```

Requires a healthy `masternoder2d` RPC, `auto_provision: true`, and either fleet registry rows or paid orders in `data/mn2_masternode_orders.json`. Each slot still needs a 5,000 MN2 collateral UTXO before it can go ENABLED.

## Run settlement (ops API)

```bash
curl -X POST -H "X-Ops-Token: $MN2_OPS_SECRET" \
  "http://127.0.0.1:5000/api/mn2/ops/settle-ecosystem?systems=all"
```

Systems: comma-separated list or `all`. Dry run: `?dry_run=1`

## Run via agent transaction API

```bash
curl -X POST -H "X-Agent-Cron-Token: $AGENT_CRON_SECRET" \
  "http://127.0.0.1:5000/api/agent/mn2/transactions/run?systems=all"
```

Auth also accepts `MN2_OPS_SECRET` / `MN2_SCAN_SECRET` via `X-Ops-Token` or `X-Scanner-Token`.

Activity burst (profile feed):

```bash
curl -X POST -H "X-Agent-Cron-Token: $AGENT_CRON_SECRET" \
  "http://127.0.0.1:5000/api/agent/mn2/activity/burst?max_events=12"
```

## Run via agent cron presets

```bash
curl -X POST -H "X-Agent-Cron-Token: $AGENT_CRON_SECRET" \
  "http://127.0.0.1:5000/api/agents/cron/run?jobs=mn2_transactions"
```

Presets (see `GET /api/agents/cron/presets`):

| Preset | Jobs |
|--------|------|
| `mn2`, `mn2_settlement`, `mn2_transactions`, `game_battle_mn2` | Full `mn2_ecosystem_settlement` |
| `mn2_fast` | Light settlement: daemon, battle, activity, scan |
| `daily` | Includes `mn2_ecosystem_settlement` |

## Shell cron

| Script | Schedule | Endpoint |
|--------|----------|----------|
| `cron/mn2_agent_transactions.sh` | Every 2 min (`masternoder-mn2-agent-tx.cron.d`) | `/api/agent/mn2/transactions/run?systems=all` |
| `cron/game_battle_mn2_settle.sh` | Every 5 min | Same (legacy alias) |
| `cron/mn2_scan_deposits.sh` | Every 5 min | Deposit scanner only |

## Key files

- `backend/services/agent_mn2_settlement_service.py` — settlement orchestrator
- `backend/services/mn2_daemon_health_service.py` — daemon RPC probes
- `backend/routes/agent_mn2_transaction_routes.py` — agent transaction API
- `scripts/mn2_daemon_test.py` — CLI health probe
- `data/mn2_config.json` — `instant_deposits`, `instant_rewards`, `chain_reward_payouts`

## Profile wallet APIs

- `GET /api/mn2/wallet/addresses`
- `POST /api/mn2/wallet/create` — `{ "label": "savings" }`
- `POST /api/mn2/wallet/refresh`
- `GET /api/mn2/profile-monitor?days=5`

See also `docs/AGENTS_MN2.md`.
