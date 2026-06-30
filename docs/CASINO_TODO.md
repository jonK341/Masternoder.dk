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

### Wave 4 (backlog)
- [ ] Keno syndicate (#5)
- [ ] Roulette side bets (#6)
- [ ] Blackjack tournaments (#7)
- [ ] Wheel raid boss (#9)
- [ ] Friend challenge links (#15)
- [ ] Podcast portal tie-in (#20)
- [ ] MN2 rake rebate progress bar (#22)
- [ ] Global hub affiliate nodes (#24)

---

## Ops (actionable)

- [ ] **Tuesday Play ($25)** — Pay fee → upload AAB → paste App Signing SHA into `assetlinks.json` → `python scripts/deploy.py well_known --ask-pass`. See [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md).
- [ ] **Deploy casino slice** — `python scripts/deploy.py casino --ask-pass` (Wave 3 routes + `casino.js` + config).
- [ ] **Agent daemon on server** — `scripts/run_casino_agent_daemon.cmd` or cron; set `AGENT_CASINO_SECRET`, `CASINO_AGENT_LLM=1`; dry-run first.
- [ ] **Merge PR #43** — critical infrastructure review (broadcast, fanout, revenue).
- [ ] **Apple AASA** — **paused** until Apple Developer account; PWA + `masternoder://` works without it.

---

## Verify after deploy

```powershell
python -m pytest tests/unit/test_casino_ideas_wave3.py -q
curl -s "https://masternoder.dk/api/casino/agents/spectate?limit=5"
curl -s "https://masternoder.dk/api/casino/duels/plinko-battle?status=open"
curl -s "https://masternoder.dk/api/casino/crash-crew/rooms?limit=3"
```
