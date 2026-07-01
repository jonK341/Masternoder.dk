# Casino master TODO — Masternoder.dk

Branch: `feat/casino-mega-expansion` · Updated: **2026-07-01**

Progress table: [CASINO_OPS_PROGRESS.md](CASINO_OPS_PROGRESS.md)

---

## Waves

### Wave 1 ✅ (197523f)
- [x] Daily revenue dashboard, slot of the day, hall of fame, referral LB, news ticker, RG banner, achievements, jackpot ticker, shop RTP audit, ledger reconcile, agent rate limit, Discord dry_run default

### Wave 2 ✅ (5b81c54)
- [x] Seasonal slot skins, referral quests v2, crew leaderboards, VIP lounge, fairness CSV export, SSE activity ticker v2, revenue digest email stub

### Wave 3 ✅ (2026-06-30)
- [x] Crash crew mode — `/api/casino/crash-crew/*`
- [x] Big-win clip cards — SVG + share URL
- [x] Plinko battle — `/api/casino/duels/plinko-battle/*`
- [x] Mines duel — `/api/casino/duels/mines/*`
- [x] Battle pass casino track — bet-volume XP + Compete tab
- [x] Lab coupons — `/api/casino/coupons/redeem-lab`
- [x] Agent spectator — `/api/casino/agents/spectate` + `run_casino_agent_daemon.cmd`
- [x] Tests — `tests/unit/test_casino_ideas_wave3.py` (8 tests)

### Wave 4 ✅ (2026-06-30)
- [x] Keno syndicate — `/api/casino/keno-syndicate/*` + Compete tab
- [x] Friend challenge links — duel invite tokens + `?duel=TOKEN`
- [x] Blackjack tournaments — `/api/casino/blackjack-tournaments/*`
- [x] Wheel raid boss — spin counter + jackpot seed + Compete progress
- [x] Roulette side bets — hot/cold config on roulette engine
- [x] MN2 rake rebate progress bar — `/api/casino/trophy-rake-rebate/progress`
- [x] Podcast portal tie-in — bonus coins during live tournament window
- [x] Global hub affiliate nodes — `POST /api/casino/global/hub-node`
- [x] Tests — `tests/unit/test_casino_ideas_wave4.py` (8 tests)

### Wave 5 ✅ (2026-06-30)
- [x] Video poker ladder — `/api/casino/video-poker/ladder` + cosmetic tier on draw
- [x] PayPal deposit bundles — `deposit_packs` starter offers + `/api/casino/deposit/packs`
- [x] Tests — `tests/unit/test_casino_ideas_wave5.py` (6 tests)

**All 25 casino feature ideas complete.** Ops-only items remain below.

---

## Ops (actionable)

### Ops 1 — Deploy casino slice

- [x] Deploy manifest complete — **68 files** (`agent_casino_routes.py`, seed JSON, UI, cron fanout); `python scripts/deploy.py casino --list-files`
- [x] Casino test suite — **111 passed**, 2 skipped (2026-07-01)
- [ ] **USER:** `python scripts/deploy.py casino --ask-pass` (Wave 5 routes + `casino.js` + config)
- [ ] **USER:** Verify `curl -sS https://masternoder.dk/api/agent/casino/models | jq .`

Walkthrough: [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md)

---

### Ops 2 — Play Store / assetlinks — **SAVED / READY** ✅

Repo prep complete. SHA update blocked on Play Console until $25 payment + first AAB upload.

- [x] `scripts/casino_play_assetlinks_update.py` — validates 64-char SHA, rejects placeholders
- [x] `static/.well-known/assetlinks.json` — placeholder `REPLACE_WITH_PLAY_APP_SIGNING_SHA256`
- [x] Walkthrough — [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md)
- [x] Listing drafts — [mobile/casino-twa/PLAY_STORE_LISTING.md](../mobile/casino-twa/PLAY_STORE_LISTING.md), [mobile/casino-app/PLAY_STORE_LISTING.md](../mobile/casino-app/PLAY_STORE_LISTING.md)
- [ ] **USER:** Pay **$25** at [Play Console signup](https://play.google.com/console/signup)
- [ ] **USER:** Create app **`dk.masternoder.casino`** and upload first AAB (Internal testing)
- [ ] **USER:** Copy **App signing key certificate** SHA-256 → `python scripts/casino_play_assetlinks_update.py "<SHA>"`
- [ ] **USER:** `python scripts/deploy.py well_known --ask-pass` and verify assetlinks

---

### Ops 3 — Agent daemon

- [x] `scripts/run_casino_agent_daemon.cmd` + `scripts/casino_agent_daemon.py`
- [x] Wired into `scripts/all_profit_daemons.py` (casino loop, `--casino-dry-run`, `--skip-casino`)
- [x] `scripts/run_daemons.cmd` — options **a** (all profit), **5** (one tick), **7**/**8** (separate windows)
- [x] Seed data in deploy manifest — `data/casino_agents.json`, `data/casino_agent_models.json`
- [ ] **USER:** Set `AGENT_CASINO_SECRET`, optional `CASINO_AGENT_LLM=1` on server
- [ ] **USER:** Dry-run first (`CASINO_AGENT_DRY_RUN=1` or `--dry-run`); then enable live bets

Setup: [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md)

---

### Ops 4 — Merge PR #43

- [ ] Review and merge — [PR #43](https://github.com/jonK341/Masternoder.dk/pull/43) (Casino mega expansion) — **OPEN**

---

### Ops 5 — Apple AASA — **PAUSED**

- [x] Placeholder `TEAMID` in `static/.well-known/apple-app-site-association` documented
- [ ] **BLOCKED:** Apple Developer account; PWA + `masternoder://` works without it

---

### Ops 6 — Discord fanout live

- [x] Cron `cron/discord_casino_fanout.sh` defaults `dry_run=true`
- [x] `CASINO_FANOUT_LIVE=1` documented — see [CASINO_OPS_PROGRESS.md § CASINO_FANOUT_LIVE](CASINO_OPS_PROGRESS.md#casino_fanout_live-discord-big-win-posts)
- [ ] **USER:** Verify dry-run fanout on server; then set `CASINO_FANOUT_LIVE=1` in cron env for live `#casino` posts

---

## Ideas backlog

Full wave roadmap: [CASINO_IDEAS.md](CASINO_IDEAS.md) (**Waves 1–5 ✅ — all 25 ideas complete**).

---

## Next 3 actions (user)

1. **Deploy casino** — `python scripts/deploy.py casino --ask-pass`; confirm `/api/agent/casino/models` on production.
2. **Play Store ($25)** — upload Internal AAB, paste App Signing SHA, deploy `well_known`.
3. **Agents + Discord** — dry-run casino agents; set server secrets; enable `CASINO_FANOUT_LIVE=1` when fanout verified.

---

## Verify after deploy

```powershell
python -m pytest tests/unit/test_casino_ideas_wave5.py -q
curl -s "https://masternoder.dk/api/casino/video-poker/ladder?user_id=u1"
curl -s "https://masternoder.dk/api/casino/deposit/packs?user_id=u1"
curl -sS "https://masternoder.dk/api/agent/casino/models" | jq .
```
