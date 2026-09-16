# Casino global sync architecture

**Status:** First slice shipped (2026-06-26) · Hub: `masternoder-main`

---

## Goal

One **MasterNoder Network** identity and leaderboard across all casino instances:

- Same `user_id` / auth everywhere (`unified_points_database`, `account_resolution_service`)
- Global leaderboards merged by `user_id`
- Global social graph (future: follow/friend across peers)
- Config-driven hub membership — no hard-coded single-site assumptions in routes

---

## Components

| Piece | Location | Role |
|-------|----------|------|
| Hub config | `data/casino_hub_config.json` | `hub_id`, `instances`, `peers`, `network_label` |
| Casino config flag | `data/casino_config.json` → `global_sync` | Enable/disable + default hub id |
| Controller | `backend/services/casino_global_controller.py` | Merge stats, format global leaderboard |
| Ledger source | `logs/casino_ledger.db` (+ JSONL fallback) | Indexed bets per user/currency |
| Public API | `GET /api/casino/global/leaderboard` | Top 25 net winners, network scope |
| Public API | `GET /api/casino/global/stats` | Site-wide totals per currency rail |
| Agent parity | `GET /api/agent/casino/global/*` | Same payloads for autonomous agents |
| UI | `casino/index.html` + `casino.js` | Scope tabs: **This site** / **MasterNoder Network** |

---

## API examples

```bash
curl -sS "https://masternoder.dk/api/casino/global/leaderboard?period=week&limit=25&currency=coins"
curl -sS "https://masternoder.dk/api/casino/global/stats"
```

Response includes `hub_id`, `network_label`, `instance_count`, and `scope: "global"`.

---

## Multi-site rollout (future)

1. Deploy this codebase on peer domains (e.g. `casino.example.com`).
2. Each peer sets its own `casino_hub_config.json` `instance_id` and shares the same `hub_id`.
3. Add peer entries:

```json
"peers": [
  {
    "hub_id": "masternoder-main",
    "api_base": "https://peer.example.com",
    "leaderboard_path": "/api/casino/global/leaderboard"
  }
]
```

4. Extend `casino_global_controller._merge_peer_leaderboards()` to `GET` peer APIs and merge rows by `user_id` (sum net/wagered).
5. Unified auth: peers trust the same user registry or SSO token — document in ops runbook before go-live.

**Today:** only `masternoder-main` is local; peers list is empty; merge stub returns local ledger only.

---

## Currency rails

Global stats and leaderboards respect the three play rails: **coins**, **mn2**, **usd**.  
**Never** `mn2_staked` — staked MN2 is outside casino liquidity.

---

## Related docs

- [CASINO_REVENUE_REPORTS.md](CASINO_REVENUE_REPORTS.md) — daily house P&amp;L
- [CASINO_INTEGRATIONS_CHECKLIST.md](CASINO_INTEGRATIONS_CHECKLIST.md) — mobile, social, agents
- [CASINO_EXPANSION_PLAN.md](CASINO_EXPANSION_PLAN.md) — ledger migration roadmap
