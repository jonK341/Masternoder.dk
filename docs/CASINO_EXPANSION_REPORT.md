# Casino mega-expansion — delivery report

**Date:** 2026-06-30 · **Branch:** `feat/casino-mega-expansion` · **Site:** [masternoder.dk/casino/](https://masternoder.dk/casino/)

---

## Wave 2 summary (5b81c54)

Seasonal slot skins, referral quests v2, crew leaderboards, VIP lounge tab, provably-fair CSV export, SSE activity ticker v2, revenue digest email cron stub.

## Wave 3 summary (2026-06-30)

Crash crew lobbies, big-win SVG clip cards, **Plinko battle** and **mines duel** PvP escrow routes, battle-pass bet-volume XP (`casino_battle_pass` config), Lab coupon redeem-lab hook, **AI agent spectator feed** (`GET /api/casino/agents/spectate`), streak shields. Eight unit tests in `tests/unit/test_casino_ideas_wave3.py`.

---

## Executive summary

The **casino mega-expansion** ships a full entertainment platform layer on MasterNoder.dk: tabbed lounge UI, **35 slot machines**, global network leaderboard, daily revenue reports, social follow/share grid, mobile shells (Capacitor + TWA), Discord integration, and **three AI betting agents** (Kelly Optimizer, Safe Grinder, Meta Oracle). The product is positioned as a **high-engagement social casino** — virtual coins, tournaments, and community features — with optional MN2 and regulated fiat rails where licensed. Revenue and retention come from engagement loops (quests, jackpots, referrals, store listings), not false gambling promises.

---

## Latest news (post `.env` upload)

| Item | Status |
|------|--------|
| Discord casino fanout | **Live** — webhook + cron `discord_casino_fanout.sh` |
| uWSGI / `.env` permissions | **Fixed** — user confirmed restart OK |
| Server env (LLM, agent secret, pixel) | **Uploaded** — keys on server only, not in repo |
| Agent routes on prod | **Pending deploy** — prod still returns Register Intelligence stubs for `/api/agent/casino/models`, `/api/agent/casino/run-all` |
| Global / revenue / marketing APIs | **Pending deploy** — same stub pattern until `python scripts/deploy.py casino` |
| Digital Asset Links | **Placeholder** — `REPLACE_WITH_PLAY_APP_SIGNING_SHA256` until Tuesday Play payment |
| Meta Pixel | **Wired** — `fbq` loads when `META_PIXEL_ID` set in server `.env` |

---

## TODO (actionable)

1. **Tuesday (Play $25)** — Pay developer fee → upload AAB → paste App Signing SHA-256 into `assetlinks.json` → `python scripts/deploy.py well_known --ask-pass`. See [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md).
2. **Deploy Wave 3 slice** — `python scripts/deploy.py casino --ask-pass` (crash crew, plinko/mines duels, spectator, coupons, `casino.js`).
3. **Start agent daemon** — `scripts/run_casino_agent_daemon.cmd` on ops host (dry-run with `CASINO_AGENT_DRY_RUN=1` first).
4. **Merge PR #43** — after review of broadcast, Discord fanout, and revenue paths (critical infrastructure).
5. **Post-deploy curl** — spectate, plinko-battle list, crash-crew rooms (see [CASINO_TODO.md](CASINO_TODO.md)).

Master checklist: [CASINO_TODO.md](CASINO_TODO.md)

---

## Broadcast / PR warning

**Casino + Discord broadcast** and **PR #43** are **critical infrastructure**. They touch:

- Live bet ledger and social big-win fanout
- Revenue reporting and operator digests
- Monetization config and referral rewards
- uWSGI route registration affecting all `/api/casino/*` and `/api/agent/casino/*`

Review carefully before merge. A bad deploy can affect **live users** and public Discord channels. Always run the test bundle and production curl checklist after deploy.

---

## Platform status

### Android

| | |
|---|---|
| **DONE** | Capacitor app `mobile/casino-app/`, TWA `mobile/casino-twa/`, package `dk.masternoder.casino`, Play listing draft, `assetlinks.json` structure fixed |
| **TODO** | Tuesday $25 → first AAB upload → real Play App Signing SHA → deploy `well_known` |
| **Paused** | — |

### iPhone

| | |
|---|---|
| **DONE** | Capacitor iOS project, entitlements `applinks:masternoder.dk`, PWA install, custom scheme `masternoder://` |
| **TODO** | — |
| **Paused** | **Universal Links / AASA** — no Apple Developer account yet; `TEAMID` placeholder in AASA is intentional |

### Social networks

| | |
|---|---|
| **DONE** | Social tab, follow grid, share networks, big-win API, Discord opt-in, OG tags |
| **TODO** | OG banner PNG (SVG exists), verify live profile URLs, set `META_PIXEL_ID` on server if not already |
| **Paused** | Facebook webhook bot (MN2_TODO E3) |

### Web / PWA

| | |
|---|---|
| **DONE** | Tabbed UI, 35 slots, crash/plinko/mines roster, jackpots, tournaments, manifest, mobile CSS/JS |
| **TODO** | Deploy latest `casino.js` + global/revenue routes to prod |
| **Paused** | — |

### AI bots

| | |
|---|---|
| **DONE** | Routes, planner, seed `casino_agents.json` + `casino_agent_models.json` (Kelly, Safe Grinder, Meta Oracle), deploy manifest updated |
| **TODO** | Deploy casino slice, set `AGENT_CASINO_SECRET` + `CASINO_AGENT_LLM=1` on server, dry-run `run-all` |
| **Paused** | — |

### Revenue

| | |
|---|---|
| **DONE** | `casino_revenue_report`, daily API, cron script docs |
| **TODO** | Deploy + schedule `cron/casino_daily_revenue_report.sh` on server |
| **Paused** | — |

---

## GitHub update checklist

When all files are ready on `feat/casino-mega-expansion`:

```powershell
cd C:\Users\jonkh\UsecaseSampler\Masternoder.dk
git add static/.well-known/assetlinks.json
git add data/casino_agents.json data/casino_agent_models.json
git add backend/services/casino_social_service.py
git add static/js/casino.js
git add scripts/deploy.py
git add docs/CASINO_*.md data/platform_news.json
git add tests/unit/test_casino_social_integration.py
git commit -m "Casino mega-expansion: assetlinks, agents seed, Meta Pixel, deploy manifest"
git push -u origin feat/casino-mega-expansion
```

Then deploy:

```powershell
python -m pytest tests/unit/test_casino_routes.py tests/unit/test_casino_social_integration.py tests/unit/test_casino_agents.py -q
python scripts/deploy.py casino --ask-pass
python scripts/deploy.py well_known --ask-pass
```

---

## Brainstorm reference

See [CASINO_IDEAS.md](CASINO_IDEAS.md) for **25 feature ideas** and **10 critical considerations** (compliance, RTP, secrets, deploy discipline, ledger reconciliation, PR review, mobile association, pixel privacy, ops).

---

## Related docs

- [CASINO_INTEGRATIONS_CHECKLIST.md](CASINO_INTEGRATIONS_CHECKLIST.md)
- [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md)
- [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md)
- [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md)
