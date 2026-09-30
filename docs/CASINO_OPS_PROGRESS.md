# Casino ops progress — Masternoder.dk

Branch: `feat/casino-mega-expansion` · Updated: **2026-07-01**

Status table for deploy, mobile, agents, and integrations. Feature waves (1–5) are complete — see [CASINO_TODO.md](CASINO_TODO.md).

---

## Status summary

| Ops | Item | Repo status | Blocker / next action |
|-----|------|-------------|------------------------|
| **1** | Deploy casino slice | **READY** — manifest 68 files (`agent_casino_routes.py`, seed JSON, `casino.js`, cron fanout) | User: `python scripts/deploy.py casino --ask-pass` |
| **2** | Play Store / assetlinks | **SAVED / READY** — scripts + docs + listing drafts | User: $25 Play Console → upload AAB → paste SHA → `casino_play_assetlinks_update.py` → `deploy.py well_known` |
| **3** | Agent daemon | **READY** — dry_run default `CASINO_AGENT_DRY_RUN=1`, interval `CASINO_AGENT_INTERVAL`, wired in `all_profit_daemons.py` + `run_daemons.cmd` | User: deploy casino slice; set `AGENT_CASINO_SECRET` + optional `CASINO_AGENT_LLM=1` on server |
| **4** | PR #43 | **OPEN** — [Casino mega expansion](https://github.com/jonK341/Masternoder.dk/pull/43) | Review + merge after deploy smoke |
| **5** | Apple AASA | **PAUSED** — placeholder `TEAMID` in AASA | Apple Developer account required |
| **6** | Discord fanout live | **READY** — cron defaults `dry_run=true` | User: verify dry-run, then `CASINO_FANOUT_LIVE=1` on server |

---

## Tests (local, 2026-07-01)

```powershell
python -m pytest tests/unit/test_casino_routes.py tests/unit/test_casino_discord_fanout.py `
  tests/unit/test_casino_social_integration.py tests/unit/test_casino_crash.py `
  tests/unit/test_casino_agents.py tests/unit/test_casino_assetlinks.py `
  tests/unit/test_casino_ideas_wave3.py tests/unit/test_casino_ideas_wave4.py `
  tests/unit/test_casino_ideas_wave5.py -q
```

**Result:** 111 passed, 2 skipped (strict assetlinks tests skip until real SHA is set).

---

## Deploy manifest

```powershell
python scripts/deploy.py casino --list-files
```

Includes `backend/routes/agent_casino_routes.py`, `data/casino_agent_models.json`, `data/casino_agents.json`, `scripts/casino_agent_daemon.py`, `scripts/run_casino_agent_daemon.cmd`.  
`static/.well-known/*` ships via `python scripts/deploy.py well_known`.

Post-deploy verify:

```bash
curl -sS https://masternoder.dk/api/agent/casino/models | jq .
```

---

## Agent daemon (local)

| Entry | Command |
|-------|---------|
| All profit (exchange + casino) | `scripts\run_daemons.cmd` → **a** or `run_all_profit_daemons.cmd` |
| Casino one tick | `run_daemons.cmd` → **5** or `run_casino_agent_daemon.cmd --once` |
| Casino-only loop window | `run_daemons.cmd` → **8** |
| Dry-run (default) | `run_casino_agent_daemon.cmd` — sets `CASINO_AGENT_DRY_RUN=1` when unset |
| Live bets | `set CASINO_AGENT_DRY_RUN=0` then `run_casino_agent_daemon.cmd --live` |

Env (`.env` / server):

| Variable | Default | Purpose |
|----------|---------|---------|
| `CASINO_AGENT_DRY_RUN` | `1` | Safe default — simulate bets |
| `CASINO_AGENT_INTERVAL` | `300` | Daemon tick interval (seconds) |
| `AGENT_CASINO_SECRET` | — | API auth for `POST /api/agent/casino/run-all` |
| `CASINO_AGENT_LLM` | `0` | `1` = LLM bet planning |

Unit tests (agent stack):

```powershell
python -m pytest tests/unit/test_casino_agents.py tests/unit/test_casino_agent_llm.py -q
```

---

## `CASINO_FANOUT_LIVE` (Discord big-win posts)

Cron script: `cron/discord_casino_fanout.sh`

| Env | Effect |
|-----|--------|
| *(unset)* or `CASINO_FANOUT_LIVE` ≠ `1` | POST `{"dry_run":true}` — no Discord spam |
| `CASINO_FANOUT_LIVE=1` | POST `{"dry_run":false}` — live posts to `#casino` |

Requires `DISCORD_OPS_SECRET` (or `MN2_OPS_SECRET`) and `DISCORD_CHANNEL_ID_CASINO` webhook URL on server.

**Enable live** (after dry-run smoke):

```bash
# In crontab line or before script:
export CASINO_FANOUT_LIVE=1
```

Manual dry-run:

```bash
SECRET=$(grep '^DISCORD_OPS_SECRET=' /var/www/html/.env | cut -d= -f2-)
curl -sS -X POST -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" \
  -d '{"dry_run":true}' http://127.0.0.1:5000/api/discord/casino/fanout | jq .
```

---

## Play Store (saved state)

| Asset | Location |
|-------|----------|
| Walkthrough | [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md) |
| SHA update script | `scripts/casino_play_assetlinks_update.py` |
| assetlinks placeholder | `static/.well-known/assetlinks.json` → `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` |
| TWA listing draft | [mobile/casino-twa/PLAY_STORE_LISTING.md](../mobile/casino-twa/PLAY_STORE_LISTING.md) |
| Capacitor listing draft | [mobile/casino-app/PLAY_STORE_LISTING.md](../mobile/casino-app/PLAY_STORE_LISTING.md) |
| Deploy ops | [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) |

---

## Next 3 user actions

1. **Deploy casino slice** — `python scripts/deploy.py casino --ask-pass`; verify `/api/agent/casino/models` returns 200.
2. **Play Console ($25)** — create `dk.masternoder.casino`, upload Internal AAB, run `casino_play_assetlinks_update.py` with App Signing SHA, deploy `well_known`.
3. **Agent + Discord** — dry-run casino agents locally; on server set secrets; when fanout dry-run looks good, set `CASINO_FANOUT_LIVE=1`.
