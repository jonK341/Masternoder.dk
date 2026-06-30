# Casino master TODO — Masternoder.dk

Branch: `feat/casino-mega-expansion` · Updated: **2026-06-30**

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

- [ ] **Tuesday Play ($25)** — Pay fee → upload AAB → paste App Signing SHA into `assetlinks.json` → `python scripts/deploy.py well_known --ask-pass`. See [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md).
- [ ] **Deploy casino slice** — `python scripts/deploy.py casino --ask-pass` (Wave 5 routes + `casino.js` + config).
- [ ] **Agent daemon on server** — `scripts/run_casino_agent_daemon.cmd` or cron; set `AGENT_CASINO_SECRET`, `CASINO_AGENT_LLM=1`; dry-run first.
- [ ] **Merge PR #43** — critical infrastructure review (broadcast, fanout, revenue).
- [ ] **Apple AASA** — **paused** until Apple Developer account; PWA + `masternoder://` works without it.
- [ ] **Discord fanout live** — keep `dry_run=true` until verified; set `CASINO_FANOUT_LIVE=1` on server when ready for public big-win posts.

---

## Ideas backlog

Full wave roadmap: [CASINO_IDEAS.md](CASINO_IDEAS.md) (**Waves 1–5 ✅ — all 25 ideas complete**).

---

## Verify after deploy

```powershell
python -m pytest tests/unit/test_casino_ideas_wave5.py -q
curl -s "https://masternoder.dk/api/casino/video-poker/ladder?user_id=u1"
curl -s "https://masternoder.dk/api/casino/deposit/packs?user_id=u1"
```
