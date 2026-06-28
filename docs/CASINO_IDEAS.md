# Casino ideas & critical considerations

Creative backlog for the MasterNoder entertainment platform — **social casino / virtual coins first**, with optional MN2 and regulated fiat rails where licensed. Not a promise of real-money gambling where not applicable.

---

## Wave 1 status (feat/casino-mega-expansion — 2026-06-28)

| Item | Status | Notes |
|------|--------|-------|
| Daily revenue dashboard (Activity tab) | ✅ | `/api/casino/revenue/report/today` + reconcile flag |
| Slot of the Day (config + home badge) | ✅ | `slot_of_the_day` in `casino_config.json`, `/api/casino/slot-of-the-day` |
| Big Win Hall of Fame (7d multipliers) | ✅ | `/api/casino/big-wins/hall-of-fame` from ledger mirror |
| Referral leaderboard | ✅ | `/api/casino/social/referral/leaderboard` — trophies only, no RTP |
| Casino news ticker | ✅ | `/api/casino/news/platform` → home marquee |
| Responsible gaming reminders | ✅ | `/api/casino/responsible-gaming/status` + session banner |
| Achievement showcase (home) | ✅ | Top 4 progress widgets from `/api/casino/achievements` |
| Network jackpot ticker | ✅ | Jackpot bar polls `/api/casino/jackpots` + global stats |
| Shop RTP audit | ✅ | `/api/casino/shop/rtp-audit` — all items `cosmetic_only` |
| Ledger reconcile check | ✅ | `/api/casino/revenue/reconcile` |
| Agent run-all rate limit | ✅ | 60s cooldown on non-`dry_run` POST |
| Discord fanout dry_run default | ✅ | Cron + routes default `dry_run=true` until `CASINO_FANOUT_LIVE=1` |

---

## 25 feature ideas (feasible next waves)

### Games & mechanics
1. **Seasonal slot skins** — reskin existing 35 machines with limited-time themes (Halloween, MN2 halving) without new engine code.
2. **Crash crew mode** — shared multiplier pool where friends cash out on the same round with split payouts.
3. **Plinko battle** — two players, same seed reveal, highest bin wins a pot.
4. **Mines duel** — turn-based tile picks on a shared board; bomb ends round.
5. **Keno syndicate** — group ticket: N players pick spots together, split wins by stake share.
6. **Roulette side bets** — config-only add-ons (hot/cold numbers) on existing roulette engine.
7. **Blackjack tournaments** — bracketed single-elimination using existing BJ engine + ledger.
8. **Video poker ladder** — daily escalating pay tables for ranked players.
9. **Wheel raid boss** — community jackpot triggered when aggregate spins hit a threshold.
10. **Provably-fair audit export** — one-click CSV of seeds/nonces for transparency-minded players.

### Social & retention
11. **Referral quests v2** — tiered rewards when referred users complete first 10 bets. *(✅ leaderboard slice — full quest tiers next)*
12. **Crew leaderboards** — Discord guild ID maps to a crew; aggregate weekly net for prizes.
13. **Big-win clip cards** — auto-generate share image (SVG/PNG) from `POST /api/casino/share/big-win`.
14. **Spectator mode** — watch AI agents (Kelly, Safe Grinder, Meta Oracle) with spectator lines from LLM.
15. **Friend challenges** — send duel invite link; winner takes configurable coin pot.
16. **Streak shields** — one loss-forgiving token per week for engagement (virtual coins only).
17. **VIP lounge tab** — unlock at XP threshold; cosmetic frames + higher daily wheel odds (house-edge neutral).
18. **Live activity ticker v2** — WebSocket or SSE feed from `casino_ledger` instead of poll. *(✅ ledger mirror + 7d big-win HOF; SSE next)*
19. **Cross-promo with Lab** — complete Lab quest → casino free bet coupon.
20. **Podcast portal tie-in** — bonus coins when listening during a live casino tournament window.

### Monetization & platform
21. **Battle pass (casino track)** — parallel to shop battle pass; cosmetic badges + coin bundles.
22. **MN2 rake rebate tiers** — extend trophy rake rebate with visible progress bar in rank tab.
23. **PayPal deposit bundles** — limited-time “starter packs” in `casino_config` deposit packs.
24. **Global hub affiliate nodes** — other MasterNoder sites report into `casino_global_controller` for network leaderboard.
25. **Revenue digest email** — optional weekly operator summary from `casino_revenue_report` (ops-only, no PII).

---

## 10 critical considerations when continuing

1. **Compliance & positioning** — Market as **entertainment / social casino** with virtual coins; disclose MN2/USD rails, age gates, and responsible-gaming tools. Never imply guaranteed profit. *(✅ RG status API + home banner)*
2. **RTP & fairness** — Keep house edge and provably-fair seeds documented; run `tests/unit/test_casino_*` before every deploy; spot-check new games with `engines/*.rtp()` helpers. *(✅ shop RTP audit endpoint)*
3. **Secret rotation** — `AGENT_CASINO_SECRET`, LLM keys, Discord webhooks, PayPal credentials: rotate on exposure; never commit `.env`.
4. **Deploy discipline** — Casino + Discord fanout + revenue routes affect **live users**. Always deploy `casino` manifest + restart uWSGI; verify with curl bundle in [CASINO_INTEGRATIONS_CHECKLIST.md](CASINO_INTEGRATIONS_CHECKLIST.md).
5. **Ledger reconciliation** — `casino_ledger.db` and JSONL logs must agree; investigate drift before changing payout tables. *(✅ `/api/casino/revenue/reconcile`)*
6. **Agent bet limits** — Seed agents with conservative `max_bet` in `data/casino_agents.json`; use `dry_run` before enabling cron `run-all`. *(✅ run-all rate limit + fanout dry_run default)*
7. **PR #43 review** — Mega-expansion PR touches broadcast, social fanout, and monetization paths — treat as **critical infrastructure**, not cosmetic UI.
8. **Mobile association files** — `assetlinks.json` needs **64-char** Play SHA (Tuesday); Apple AASA **paused** until Developer account; PWA + `masternoder://` scheme works without Apple.
9. **Meta Pixel privacy** — Only load `fbq` when `META_PIXEL_ID` is set server-side; respect cookie/consent requirements in target markets.
10. **Load & ops** — uWSGI workers, logrotate, and Discord cron (`cron/discord_casino_fanout.sh`) must stay healthy; monitor `logs/casino_bets.jsonl` growth.
