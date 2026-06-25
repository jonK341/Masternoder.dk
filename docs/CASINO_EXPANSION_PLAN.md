# Casino expansion plan — "Max Entertainment" upgrade for Masternoder.dk

This plan upgrades the existing virtual casino into a full **entertainment hub**: more game types, live progressive jackpots, tournaments, a VIP/XP progression layer, social PvP, provably‑fair RNG, and a polished "show" (animation, sound, big‑win celebrations) — while staying inside the architecture and **locked product decisions** already in the codebase.

It builds on the current casino stack:
- UI: `casino/index.html`, `static/js/casino.js`, `static/css/casino.css`
- API: `backend/routes/casino_routes.py` (blueprint `virtual_casino`)
- Logic: `backend/services/casino_service.py` (~2.3k lines, all games)
- Config (functional spec): `data/casino_config.json`
- Balances: `backend/services/unified_points_database.py` (`coins`, `mn2_balance`, `casino_fiat_balance`)
- Real money: `backend/services/paypal_service.py`, `backend/services/account_security_service.py`
- Ledger: `logs/casino_bets.jsonl`, `logs/casino_quest_claims.json`, `logs/casino_paypal_deposits.json`
- Tests: `tests/unit/test_casino_routes.py`

**Related docs:** [MN2_STAKING_PLAN.md](MN2_STAKING_PLAN.md) · [MONETIZATION_PAYPAL.md](MONETIZATION_PAYPAL.md) · [PROJECT_RETHINK.md](PROJECT_RETHINK.md)

---

## ✅ Shipped — first vertical slice (C1 foundation + Crash + show layer)

Decisions locked for this slice: real money (MN2 **and** USD) enabled on the new roster, house-seeded progressive jackpots (**shipped**, see below), real-money tournaments (not yet built). The following is **implemented and tested**:

**Foundation (C1)**
- `backend/services/casino_rng.py` — provably-fair RNG: per-user server seed (committed as SHA-256 hash before play), user-settable client seed, incrementing nonce, `draw()`, `rotate()` (reveals old seed), and pure `verify()`. State in `logs/casino_fairness.json`.
- `backend/services/engines/` package + `engines/crash.py` — pure outcome engine (inverse-CDF bust distribution → RTP = 1 − house_edge for any cash-out target; exponential time curve; `settle()`).
- `backend/services/casino_ledger.py` — stdlib-SQLite indexed mirror of every bet (`logs/casino_ledger.db`), wired additively into `_append_ledger`. Powers the live winners feed without re-scanning JSONL. Existing leaderboard/quest reads left on JSONL (unchanged).

**Crash game (C2/C3 vertical slice)** — coins + MN2 + USD, real-money security gate inherited via `_validate_bet`.
- Service: `start_crash_round()` (validates, debits stake up front, draws provably-fair bust, single active round per user), `cashout_crash_round()` (server-authoritative: clamps client multiplier to server-measured elapsed time, settles win/loss with correct net), abandoned rounds auto-expire as a bust loss and are ledgered.
- Config block `crash` in `data/casino_config.json` (`house_edge`, `growth_per_second`, `max_round_seconds`, `max_auto_cashout`, `rtp_estimate`) exposed via `get_public_config()`.
- Routes on the existing `virtual_casino` blueprint: `POST /api/casino/play/crash`, `POST /api/casino/play/crash/cashout`, `GET /api/casino/fairness/seed`, `POST /api/casino/fairness/client-seed`, `POST /api/casino/fairness/rotate`, `POST /api/casino/fairness/verify`, `GET /api/casino/activity-feed`.

**Plinko game (C2/C3 roster)** — coins + MN2 + USD, single-call money path, config-driven payout tables (proves the "add a game via config + a pure engine" pattern).
- Engine `backend/services/engines/plinko.py` — pure: a single provably-fair float is binary-expanded into `rows` fair left/right bits; landing bin is binomial; payout = per-risk table lookup. `rtp()` helper for tests (all three risk tables ≈ 99% RTP).
- Service `play_plinko()` reuses `_validate_bet` + `_finalize_bet` (correct net for sub-1× bins), with the fairness proof recorded in the bet details.
- Config block `plinko` (`rows`, `rtp_estimate`, `risk_tables: {low, medium, high}`) exposed via `get_public_config()`; route `POST /api/casino/play/plinko`.
- Frontend: canvas peg board with animated ball drop, low/medium/high risk selector, live bin multiplier labels, big-win celebration, `prefers-reduced-motion` fallback.

**Mines game (C2/C3 roster)** — coins + MN2 + USD, stateful reveal/cash-out (same money pattern as crash).
- Engine `backend/services/engines/mines.py` — pure: bomb layout from a single provably-fair float via seeded Fisher-Yates (whole board committed at round start), fair `multiplier(k) = (1 − house_edge) · Π (N−i)/(N−m−i)`.
- Service: `start_mines_round` (validate, debit stake, single active round per user), `reveal_mines_tile` (bomb → bust loss + reveal; safe → raise multiplier; all-safe → auto cash-out), `cashout_mines_round`; abandoned rounds expire as a loss and are ledgered.
- Config block `mines` (`tiles`, `min/max/default_mines`, `house_edge`); routes `POST /api/casino/play/mines`, `/mines/reveal`, `/mines/cashout`.
- Frontend: 5×5 interactive grid (💎 / 💣), mine-count selector, live cash-out multiplier + next-tile preview, bust reveal.

**Wheel of Fortune game (C2/C3 roster)** — coins + MN2 + USD, single-call weighted spin (same pattern as plinko).
- Engine `backend/services/engines/wheel.py` — pure: weighted-segment selection from one provably-fair float; RTP = weight-averaged multiplier. Low/Medium/High tables tuned to ~97–99% RTP (verified by `rtp()` test).
- Service `play_wheel()`; config block `wheel` with `risk_tables` of `{multiplier, weight}` segments; route `POST /api/casino/play/wheel`.
- Frontend: animated spinning wheel `<canvas>` (wedges sized by weight, multiplier labels) decelerating onto the server-returned segment, with a fixed pointer.

**Progressive jackpot module (events slice)** — house-seeded, per-rail, fully ledgered & reconcilable.
- Engine `backend/services/casino_jackpot.py` — **separate pool per currency** (coins / MN2 / USD), each house-seeded. Every eligible bet contributes `contribution_rate × bet`; the pool drops on a **slot jackpot symbol** or a rare per-bet **must-drop** roll, awards the whole pool to the player, and re-seeds. Every contribution / award / seed is an entry in `logs/casino_jackpot_ledger.jsonl`; state in `logs/casino_jackpots.json`. Invariant `pool == seeded + contributed − awarded` is checked by `reconcile()`.
- Integration: hooked into the single `_append_ledger()` chokepoint so **all** games (classic, crash, mines, plinko, wheel) contribute and can trigger; the award is surfaced on the play result as `result["jackpot"]`. Awards pay out through the same `_apply_balance_delta()` path (never touches staked MN2). Free/excluded bets don't contribute.
- Config block `jackpot` (`enabled`, `slot_jackpot_symbol_awards`, per-rail `seed`/`contribution_rate`/`win_chance`/`reseed`); routes `GET /api/casino/jackpots` and `GET /api/casino/jackpots/reconcile`. MN2/USD pools only surface when the real-money rail is enabled.
- Frontend: live **jackpot meter bar** (polls every 12 s, highlights the active rail) and a **JACKPOT** mega-celebration + toast on any win, wired through the universal `setResult()` so every game shows it.

**Keno game (C2/C3 roster)** — coins + MN2 + USD, single-call, provably-fair draw with a hypergeometric pay table.
- Engine `backend/services/engines/keno.py` — pure: a single provably-fair float seeds an LCG partial Fisher-Yates to draw 10 distinct numbers from 40; payout = per-spots-count pay-table lookup on the hit count. `hyper_prob()` + `rtp()` give the exact return-to-player, so tables are calibrated precisely (all six spot levels land ~0.92–0.96 RTP).
- Service `play_keno()`; config block `keno` (`pool`, `draw`, `max_spots`, `pay_table`); route `POST /api/casino/play/keno`.
- Frontend: interactive 40-number grid (pick up to 6, quick-pick/clear), drawn numbers highlighted with hits flagged.

**Roulette game (C2/C3 roster)** — coins + MN2 + USD, single-call European single-zero.
- Engine `backend/services/engines/roulette.py` — pure: one provably-fair float picks a pocket 0–36; `evaluate()` returns the total-return multiplier for straight (36×), red/black/even/odd/low/high (2×), and dozen/column (3×). The single green zero gives every bet RTP = 36/37 ≈ 0.973 (verified by `rtp()`).
- Service `play_roulette()`; config block `roulette`; route `POST /api/casino/play/roulette`.
- Frontend: bet-type selector (with conditional number/dozen/column picker) and a coloured landing-pocket display.

**Hi-Lo game (C2/C3 roster)** — coins + MN2 + USD, stateful guess / cash-out (same money pattern as crash/mines).
- Engine `backend/services/engines/hilo.py` — pure: cards drawn uniformly with replacement; each correct higher/lower call multiplies the pot by the fair `(1 − house_edge) / P(win)`. Ties resolve to the player's chosen side, so there's always a valid (and a safe) pick.
- Service: `start_hilo_round` (validate, debit stake, deal first card, single active round per user), `hilo_guess` (draw next card, grow multiplier or bust), `hilo_cashout`; abandoned rounds expire as a loss and are ledgered.
- Config block `hilo` (`ranks`, `house_edge`); routes `POST /api/casino/play/hilo`, `/hilo/guess`, `/hilo/cashout`.
- Frontend: card face with higher/lower buttons showing live per-step multipliers, running cash-out value.

**Tournaments module (events slice)** — time-boxed, real-money-capable, fully ledgered & reconcilable.
- Engine `backend/services/casino_tournaments.py` — per-currency competitions with a house-seeded prize pool grown by real-money buy-ins. Score = cumulative **net** of the player's bets in that currency during the window (hooked into the `_append_ledger()` chokepoint via `record_bet`, so every game counts). On window close the pool is split among the top finishers (`prize_split`, default 50/30/20) and credited through the normal balance path. Buy-ins for MN2/USD pass the same security gate as bets. Daily templates auto-recreate so there's always a live cup. State in `logs/casino_tournaments.json`; every seed/buyin/payout is in `logs/casino_tournament_ledger.jsonl` and `reconcile()` checks `seed + buyins − paid_out ≥ 0`.
- Service wrappers `list_tournaments` / `get_tournament` / `join_tournament` / `reconcile_tournaments`; routes `GET /api/casino/tournaments`, `GET /api/casino/tournaments/<id>`, `POST /api/casino/tournaments/join`, `GET /api/casino/tournaments/reconcile`.
- Frontend: tournaments panel with live prize pool, countdown, entrants, top-5 leaderboard, your rank, and a currency-aware Join button.

**The show (C5 slice)** — in `casino/index.html`, `static/js/casino.js`, `static/css/casino.css`:
- Live rising **crash curve** on `<canvas>` with rocket/💥, live multiplier, auto cash-out, manual cash-out.
- **Live winners ticker** (from the DB feed), opt-in **sound** (muted by default, `localStorage`), **BIG WIN / MEGA WIN** celebration overlay (≥3× / ≥10×) routed through all games, and a per-game **Provably-Fair panel** (seed hash + rotate/reveal). All animations honor `prefers-reduced-motion`.

**Tests:** `tests/unit/test_casino_crash.py` — crash (engine bounds/RTP convergence, curve growth, settle, HMAC determinism, `verify()` reproduction, rotate-reveal hash match, route flows + fairness endpoints), Plinko (deterministic path, binomial bins, RTP band, route payout + bad-risk), Wheel (deterministic weighted spin, RTP band, route payout), Mines (deterministic layout, growing multiplier, reveal-safe→cashout win, mine-hit loss, single-active-round guard), Jackpot (contribution + reconcile invariant, forced slot-symbol award + re-seed + player credit, pools route), Keno (deterministic distinct draw, RTP band, route payout + spot-limit guard), Roulette (pocket mapping, evaluate matrix, 36/37 RTP, straight route payout), Hi-Lo (fair multipliers, start→guess→cashout win, wrong-guess bust, single-active-round guard), and Tournaments (join + score + forced finalize + prize split + reconcile invariant). Run: `python -m pytest tests/unit/test_casino_crash.py tests/unit/test_casino_routes.py -q` (48 passing).

**Deploy:**
```
python scripts/deploy.py --files \
  backend/services/casino_service.py backend/services/casino_rng.py \
  backend/services/casino_ledger.py backend/services/casino_jackpot.py \
  backend/services/casino_tournaments.py \
  backend/services/engines/__init__.py \
  backend/services/engines/crash.py backend/services/engines/plinko.py \
  backend/services/engines/mines.py backend/services/engines/wheel.py \
  backend/services/engines/keno.py backend/services/engines/hilo.py \
  backend/services/engines/roulette.py \
  backend/routes/casino_routes.py \
  data/casino_config.json casino/index.html static/js/casino.js static/css/casino.css
```

**Still to build (next waves):** rest of the roster (blackjack, video poker, baccarat, more slots), XP/VIP/achievements, PvP/social duels, and moving leaderboard/quest reads onto the new DB ledger.

---

## ✅ Shipped — competition, shop, trophies & achievements (C6 slice)

Decisions locked: cosmetic-only shop items (no RTP perks), coin rewards for trophies/achievements, three currency rails unchanged, `virtual_casino` blueprint only.

**User competition**
- **PvP duels** extended: coin flip, RPS, and **dice** (high/low 4–6 vs 1–3) with escrow + rake; ledgered; hooks into progression/trophies on settle.
- **Rival boards** — `GET /api/casino/rivals` weekly/monthly net-vs-peers; "Rival of the week" callout; duel streak battles.
- **Achievement races** — first-to-unlock races (`first_jackpot`, `first_duel_10`, `first_shop_15`) with coin prizes; `GET /api/casino/achievement-races`.
- **Crew casino leaderboard** — `GET /api/casino/crew-leaderboard` aggregates crew member casino net from ledger (hooks `data/social_structure.json` crews).
- **Tournament enhancements** — weekly/monthly templates with `rivalry_callout`; tournament close hooks award progression/trophies.

**Casino shop (24 items)** — `data/casino_shop_catalog.json`
- Avatar frames, table skins, card backs, slot themes, free-bet vouchers, VIP badges, emotes, win celebrations, tournament/duel tokens, trophy pedestals, profile banners.
- Service: `backend/services/casino_shop_service.py`
- Routes: `GET /api/casino/shop/catalog`, `GET /api/casino/shop/owned`, `POST /api/casino/shop/purchase`

**Trophies (25)** — `data/casino_trophies.json`
- Win streaks, jackpots, tournament placements, duel wins/streaks, game exploration, high roller, daily grinder, crash/plinko/mines, social, shop/achievement collection, rival of the week.
- Service: `backend/services/casino_trophies_service.py`; awards coin rewards + syncs global trophy DB when available.
- Route: `GET /api/casino/trophies`

**Achievements (35, bronze/silver/gold tiers)** — `data/casino_achievements.json`
- Per-game milestones, competitive (rival beats, tournament, duels), collection (shop/trophies), streaks, volume, achievement races.
- Extended `backend/services/casino_progression.py` with metric-based `on_event()` + progress bars; hooked from `_append_ledger`, duel settle, tournament close, shop purchase.
- Route: `GET /api/casino/achievements` (progress % included)

**Competition orchestration** — `backend/services/casino_competition_service.py`

**UI** — Compete tab in `casino/index.html` + `static/js/casino.js`: rival board, achievement races, crew board, shop grid with buy, trophies grid, achievements grid with progress bars. Dice added to duel game selector.

**Tests:** `tests/unit/test_casino_competition_expansion.py` (6 passing) — shop purchase, trophies/achievements lists, rivals/races/crew, dice duel, progression unlock.

**Still to build (next waves):** rest of the roster polish, moving leaderboard/quest reads onto the DB ledger, spectating/shareable duel cards.

---

## ✅ Shipped — mobile, Discord, and Facebook integration (Play / social slice)

Cross-platform casino distribution and social fan-out:

**Google Play / TWA (`mobile/casino-twa/`)**
- `casino/manifest.webmanifest` — standalone PWA, icons, Play `related_applications`
- `static/.well-known/assetlinks.json` — Digital Asset Links template (replace Play signing SHA-256)
- `static/js/casino-twa-shell.js` + `casino-twa-shell.css` — bottom nav for `?app=casino-twa`
- Deep links: `?game=crash`, `?tab=social`, `?app=casino-twa`
- Social tab: Google Play badge + PWA install prompt on Android
- `mobile/casino-twa/PLAY_STORE_LISTING.md` — store copy + screenshot checklist

**Discord casino fan-out**
- `backend/services/casino_discord_fanout.py` — activity_events → `#casino` embeds (big win, jackpot, tournament start/end)
- Hooks: `_finalize_bet` → `on_big_win` / `on_jackpot_win`; tournaments → start/end events
- Opt-in + geo gate via `casino_social_service` (existing); cron `cron/discord_casino_fanout.sh`
- Routes: `POST /api/casino/discord/notify`, `POST /api/discord/casino/fanout`

**Facebook / share**
- Open Graph + Twitter Card meta on `casino/index.html`
- `POST /api/casino/share/big-win` — share card + network URLs
- Facebook page link in Social tab; no new OAuth (existing `social_auth_service` unchanged)

**APIs**
- `GET /api/casino/mobile/config`, `GET /api/casino/social/links`
- Agent parity on `/api/agent/casino/*`
- Config blocks: `mobile`, `discord_integration`, `facebook`, `social` in `data/casino_config.json`

**Ops (not in repo):** set `DISCORD_CHANNEL_ID_CASINO` webhook URL, replace assetlinks SHA-256, upload AAB to Play Console.

---

## 0. Core constraints (read first)

These are **locked** and the expansion must respect them:

1. **Three currency rails stay as‑is:** virtual `coins` (cosmetic), in‑app `mn2_balance` (MN2), and `casino_fiat_balance` (PayPal‑funded USD). All new games must support the same `currency` param and route debits/credits through `_apply_balance_delta()`.
2. **Staked MN2 is off‑limits.** Per `MN2_STAKING_PLAN.md` §14 #10, the casino must **never** read `mn2_staked` or offer "stake‑to‑unlock" casino perks. Staking lives in the profile wallet; the casino only touches the liquid `mn2_balance`.
3. **Real‑money bets require the security gate.** Any `mn2`/`usd` bet keeps going through `account_security_service.check_real_money_action()` (password + `verification_token`). New games inherit this in `_validate_bet()` — no new game may bypass it.
4. **Config‑driven, not code‑forked.** New games/slots are added as blocks in `data/casino_config.json` and auto‑render in the UI. Avoid hard‑coding per‑game UI where a generic renderer works (the slot catalog already does this).
5. **Agent/API parity (project‑rethink rule).** Every new action a user can take in the UI must be reachable via the API with a `user_id`, exposed through the existing `virtual_casino` blueprint — **no fragmented new blueprints**.
6. **Honesty in RTP/odds.** Every game keeps a published `rtp_estimate`; "provably fair" claims (Phase 1) must be backed by a real verifiable seed scheme, not marketing copy.

---

## 1. Goals & non‑goals

**Goals**
- **Breadth:** add a roster of new, genuinely different game types (cards, wheel, crash, plinko, mines, keno, hi‑lo, etc.) beyond flip/dice/slots.
- **Depth (the "show"):** animated reels/cards/wheels, sound, near‑miss + big‑win celebrations, themed lobbies, a casino "host" presence, and a live activity ticker.
- **Progression:** player XP/levels, VIP tiers, achievements/badges, and a daily "lucky wheel" / loot reward loop that keeps people coming back.
- **Events:** live **progressive jackpots** and time‑boxed **tournaments** with prize pools and leaderboards.
- **Social:** PvP duels and crew‑vs‑crew challenges, spectating, a live winners feed, and shareable big‑win cards.
- **Trust:** provably‑fair RNG (server seed + client seed + nonce) with an in‑UI verifier.
- **Scale:** move the bet ledger off flat JSONL onto a queryable store so leaderboards/quests/jackpots don't re‑scan a growing file.
- **Agent parity:** an agent can browse games, place bets, join tournaments, and claim rewards via API.

**Non‑goals (this expansion)**
- No on‑chain/smart‑contract betting; outcomes stay server‑authoritative.
- No coupling to MN2 **staking** (locked, §0 #2).
- No new payment rails beyond the existing PayPal USD + MN2.
- No live human dealers / real‑time video.

---

## 2. Architecture overview (target)

```
Browser (casino/index.html + casino.js, modular game widgets + shared animation/sound layer)
  └── fetch /api/casino/*  (currency-aware, verification_token for real money)
        │
Flask backend (single virtual_casino blueprint)
  ├── casino_routes.py        (thin HTTP layer; play/<game>, tournaments, jackpot, profile, verify)
  ├── casino_service.py       (orchestration: validate → engine → finalize → ledger → events)
  ├── engines/                (NEW: one module per game family — pure outcome functions)
  │     ├── slots.py  cards.py  wheel.py  crash.py  plinko.py  mines.py  instant.py
  ├── casino_rng.py           (NEW: provably-fair seed/nonce, verify())
  ├── casino_jackpot.py       (NEW: progressive pool contribution + award)
  ├── casino_tournament.py    (NEW: event lifecycle, scoring, prize payout)
  ├── casino_progression.py   (NEW: XP, levels, VIP tiers, achievements)
  └── casino_ledger.py        (NEW: DB-backed bet ledger; replaces raw JSONL scans)
        │
Storage
  ├── unified_points_database (coins / mn2_balance / casino_fiat_balance — unchanged)
  ├── SQLite/SQLAlchemy table  casino_bets (indexed: user, currency, ts, game)
  └── data/casino_config.json  (games, jackpots, tournaments schedule, VIP tiers, RNG policy)
```

**Key refactor:** today every game lives in `casino_service.py`. The expansion extracts **pure outcome engines** (input: bet, choice, rng → output: result + multiplier) so each game is independently testable and the service just orchestrates validate → engine → finalize. This is the precondition for adding many games without growing one 5k‑line file.

---

## 3. New games (Phase 2 roster)

All payout math lives in `data/casino_config.json`; execution in `backend/services/engines/*`. Each is `currency`‑aware and respects the real‑money gate.

| Game | Engine | Mechanic | Why it adds entertainment |
|------|--------|----------|---------------------------|
| **Blackjack** | `cards.py` | Player vs dealer, hit/stand/double, 3:2 BJ | Skill + decisions; long session game |
| **European Roulette** | `wheel.py` | Inside/outside bets, single‑zero | Iconic; many bet types per spin |
| **Crash** | `crash.py` | Rising multiplier, cash out before bust | High‑adrenaline, great for live ticker |
| **Plinko** | `plinko.py` | Ball drops through pegs into multiplier bins | Hugely visual; risk rows = volatility |
| **Mines** | `mines.py` | Reveal tiles, avoid bombs, cash out | Tension + player agency |
| **Hi‑Lo** | `cards.py` | Guess next card higher/lower, chain multiplier | Simple, chainable like double‑or‑nothing |
| **Keno** | `instant.py` | Pick numbers, draw 20, paytable by hits | Lottery feel, configurable RTP |
| **Wheel of Fortune** | `wheel.py` | Weighted multiplier wheel, risk modes | Pairs with daily free spin |
| **Video Poker (Jacks or Better)** | `cards.py` | Draw poker, hold cards, paytable | Skill ceiling; classic |
| **Baccarat** | `cards.py` | Player/Banker/Tie | Low‑decision, fast |
| **New themed slots** | `slots.py` | 3 more `slot_*` config blocks + a 5‑reel variant | Reuses existing slot engine |

**Config example (drop‑in, no new code path for slots):**

```json
"slot_pharaoh": {
  "label": "Pharaoh's Gold", "icon": "🏺", "volatility": "high", "rtp_estimate": 95.5,
  "reels": 5, "symbols": ["ankh","scarab","eye","pyramid","sand","wild"],
  "scatter_symbol": "eye", "scatter_min": 3, "scatter_multiplier": 4.0,
  "paytable": { "default_three": 6.0, "three": {"ankh": 18.0} }
}
```

For **5‑reel** support, `slots.py` generalizes `reels` (3 → N) and adds simple paylines; 3‑reel configs keep working unchanged.

---

## 4. The "show" — entertainment & presentation layer (Phase 5)

A shared front‑end layer in `static/js/casino.js` (+ `casino.css`) so every game feels alive:

- **Animation kit:** reel spin easing, card deal/flip, wheel spin with deceleration, plinko ball physics (canvas), crash curve render. CSS transforms + `requestAnimationFrame`; no heavy 3D.
- **Sound (opt‑in, muted default):** spin, win, big‑win, jackpot siren; respects a persisted mute toggle in `localStorage`.
- **Celebrations:** confetti + "BIG WIN / MEGA WIN" overlays scaled by payout multiple; near‑miss highlighting on slots.
- **Live activity ticker:** a "recent winners" feed (anonymized handles) streamed from the ledger; drives FOMO and social proof.
- **Themed lobbies:** group games into rooms (Slots Hall, Tables, Arcade, Live) with distinct theming.
- **Casino host:** a lightweight mascot/host that reacts to wins/losses and surfaces quests, daily wheel, and jackpot size.
- **Big‑win share card:** generate a shareable image (handle, game, multiplier) — ties into existing social structure.

Accessibility: all animations honor `prefers-reduced-motion`; sound is off by default.

---

## 5. Engagement systems (Phase 3)

| System | Service | Storage | Notes |
|--------|---------|---------|-------|
| **XP & Levels** | `casino_progression.py` | unified points meta | XP per wager (coins‑equivalent), level‑up rewards in coins |
| **VIP tiers** | `casino_progression.py` | config `vip_tiers` | Bronze→Diamond; perks = higher daily caps, exclusive daily‑wheel slices, badge. **No RTP edge** (fairness) |
| **Achievements/Badges** | `casino_progression.py` | `logs/casino_achievements.json` | "First jackpot", "10‑win streak", "tried all games" |
| **Daily Lucky Wheel** | `wheel.py` + quests | `logs/casino_quest_claims.json` pattern | One free spin/day, coin/booster prizes; extends existing `free_daily_bet` |
| **Loot / mystery box** | `instant.py` | config | Earned via quests/levels; coins + shop boosters (ties to `monetization_config.json`) |
| **Missions (existing+more)** | reuse quest system | unchanged | Add per‑game daily/rotating quests for the new roster |

All rewards pay in **coins** (consistent with existing quest payouts) unless explicitly a USD/MN2 promo — keeps real‑money accounting clean.

---

## 6. Live events (Phase 4)

### 6.1 Progressive jackpots (`casino_jackpot.py`)
- A small % of each eligible bet contributes to a shared pool (per currency rail; coins pool is separate from MN2/USD pools).
- Award triggers: jackpot symbol on slots, or a rare random "must‑drop‑by" timer.
- Fully ledgered: contributions and awards are explicit ledger entries; pool size is reconcilable (mirrors the conservation discipline in `MN2_STAKING_PLAN.md` §8).
- UI: live‑ticking jackpot meter in the lobby and on eligible games.

### 6.2 Tournaments (`casino_tournament.py`)
- Time‑boxed events (e.g. "Friday Slots Sprint"): buy‑in (coins or real money) → prize pool → ranked by score (net win, biggest multiplier, or most wins).
- Scoring reads the DB ledger (Phase 1) filtered by event window.
- Prize payout is automatic at close, ledgered, and shown on a dedicated tournament leaderboard.
- Config‑driven schedule in `data/casino_config.json` → `tournaments[]`.

---

## 7. Provably‑fair RNG (Phase 1, trust foundation)

`backend/services/casino_rng.py`:
- Per bet: `result = HMAC_SHA256(server_seed, f"{client_seed}:{nonce}")` → mapped to game outcome.
- `server_seed` is committed as a **hash** before play; revealed after the user rotates their seed, so past rounds are verifiable.
- `client_seed` is user‑settable (default random); `nonce` increments per bet.
- New endpoints: `GET /api/casino/fairness/seed` (current hashed server seed + client seed + nonce), `POST /api/casino/fairness/rotate` (reveal old, commit new), `POST /api/casino/fairness/verify` (recompute a past outcome).
- UI: a "Provably Fair" panel per game showing seeds + a verify button.

This replaces bare `random` calls in the engines with a seeded, auditable stream while keeping configured RTPs intact.

---

## 8. Data & scaling (Phase 1)

`backend/services/casino_ledger.py` introduces a **SQLAlchemy `casino_bets` table** (indexed on `user_id`, `currency`, `ts`, `game`, `bet_id`) replacing growing‑file scans for:
- leaderboards, house‑stats, personal‑bests, hall‑of‑fame
- quest progress, tournament scoring, jackpot contributions

`logs/casino_bets.jsonl` is kept as an **append‑only audit mirror** (or a one‑time migration imports it). Reads move to the DB; this removes the O(file) scan the explore noted as a risk. Balances stay in `unified_points_database` — unchanged.

---

## 9. API surface (additions, all on `virtual_casino`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/casino/play/blackjack` (+ `/hit`,`/stand`,`/double` session actions) | Card game with state |
| POST | `/api/casino/play/roulette` | Spin + multi‑bet payload |
| POST | `/api/casino/play/crash` (+ `/cashout`) | Live multiplier round |
| POST | `/api/casino/play/plinko` | Drop |
| POST | `/api/casino/play/mines` (+ `/reveal`,`/cashout`) | Stateful reveal |
| POST | `/api/casino/play/hi-lo` | Chainable guess |
| POST | `/api/casino/play/keno` | Pick + draw |
| POST | `/api/casino/play/wheel` | Wheel spin |
| POST | `/api/casino/play/video-poker` (+ `/draw`) | Hold/draw |
| POST | `/api/casino/play/baccarat` | Bet player/banker/tie |
| GET/POST | `/api/casino/jackpots`, `/api/casino/jackpots/state` | Pool sizes |
| GET/POST | `/api/casino/tournaments`, `/join`, `/leaderboard` | Events |
| GET | `/api/casino/progression` · `/achievements` · `/vip` | Player profile |
| POST | `/api/casino/daily-wheel/spin` · `/lootbox/open` | Reward loop |
| GET/POST | `/api/casino/fairness/seed` · `/rotate` · `/verify` | Provably fair |
| GET | `/api/casino/activity-feed` (or SSE) | Live winners ticker |

Stateful games (blackjack, mines, crash, video poker) need a short‑lived server‑side round state keyed by `user_id` + `round_id`; store in the DB with a TTL so a refresh can't double‑settle.

---

## 10. Agent parity (project‑rethink rule)

Per `.cursor/rules/project-rethink.mdc` and `PROJECT_RETHINK.md`:
- Every new endpoint resolves a `user_id` from query/body exactly like existing casino routes — agents can already drive them.
- Add the new verbs to the casino capability/metadata surface (`/api/casino/config` already exposes games metadata) so an agent can discover the roster, limits, jackpots, and active tournaments.
- Keep it on the **single** `virtual_casino` blueprint; do not spin up per‑game blueprints.
- Real‑money agent bets still require the security gate (`verification_token`) — parity does **not** mean bypassing the password gate.

---

## 11. Touchpoints summary

**New files**
- `backend/services/casino_rng.py`, `casino_ledger.py`, `casino_jackpot.py`, `casino_tournament.py`, `casino_progression.py`
- `backend/services/engines/__init__.py`, `slots.py`, `cards.py`, `wheel.py`, `crash.py`, `plinko.py`, `mines.py`, `instant.py`
- `tests/unit/test_casino_engines.py`, `test_casino_jackpot.py`, `test_casino_tournament.py`, `test_casino_fairness.py`

**Extend**
- `data/casino_config.json` (new games, `jackpots`, `tournaments`, `vip_tiers`, `rng`, `progression`)
- `backend/services/casino_service.py` (orchestrate → delegate to engines; thin it down)
- `backend/routes/casino_routes.py` (new endpoints)
- `static/js/casino.js`, `static/css/casino.css`, `casino/index.html` (game widgets + show layer + lobbies)
- `tests/unit/test_casino_routes.py` (new endpoint coverage)
- `register_blueprints.py` (fix stale "cosmetic only" comment)

---

## 12. Testing strategy

- **Engine unit tests:** each engine is a pure function → assert payout distribution converges to configured RTP over N seeded runs (e.g. 100k) within tolerance.
- **Fairness tests:** `verify()` reproduces outcomes for known seed/nonce; rotation reveals match commitments.
- **Money tests:** stake/payout deltas hit the correct balance field per currency; real‑money gate blocks unverified `mn2`/`usd` bets; daily cap + per‑bet limits enforced.
- **State tests:** stateful games can't double‑settle on replay; TTL expiry voids stale rounds.
- **Jackpot/tournament:** contribution + award conserve the pool; payouts ledgered; reconcile passes.
- Reuse the `tests/unit/test_casino_routes.py` harness and pytest tmp config fixtures.

---

## 13. Rollout phases

| Phase | Scope | Ships |
|-------|-------|-------|
| **C1 — Foundation** | Engine refactor (extract `engines/`), provably‑fair RNG, DB ledger migration. No user‑facing change yet. | Trust + scale base |
| **C2 — Game roster** | Blackjack, roulette, crash, plinko, mines, hi‑lo, keno, wheel, video poker, baccarat, 3–4 new slots (incl. 5‑reel). | Breadth |
| **C3 — Progression** | XP/levels, VIP tiers, achievements, daily lucky wheel, loot boxes, expanded quests. | Retention loop |
| **C4 — Live events** | Progressive jackpots + tournaments with prize pools and leaderboards. | Stickiness |
| **C5 — The show** | Animation kit, sound, celebrations, themed lobbies, host, live winners ticker, share cards. | Polish/wow |
| **C6 — Social** | PvP duels, crew‑vs‑crew, spectating, shareable wins. | Virality |

C1 is a prerequisite for the rest (engines + ledger). C2–C5 can interleave; C6 depends on C1 ledger + C3 progression.

---

## 14. Open decisions for you

1. **Real money on new games:** enable `mn2`/`usd` on the full new roster, or keep some (crash, mines, blackjack) coins‑only at launch for compliance comfort?
2. **Jackpot funding:** house‑funded seed pool vs purely bet‑funded — affects whether a real‑money pool needs a reserve (like the staking stabilization reserve).
3. **Tournament prizes:** coins‑only, or real‑money buy‑ins/payouts (adds compliance + reconcile load)?
4. **Scope first cut:** do you want C1+C2 as the first shippable milestone, or a thin vertical slice (1 new game end‑to‑end with the show layer) to validate the pattern before the full roster?

> Default recommendation if you don't pick: ship **C1 + a vertical slice (Crash, coins + MN2)** first — it exercises the engine refactor, provably‑fair RNG, DB ledger, stateful rounds, and the animation/ticker layer in one go, then fan out the rest of the roster.

---

## Shipped this session (2026-06-25)

Consolidated deploy pass from parallel casino workers:

| Area | Shipped |
|------|---------|
| **UI** | Tabbed casino hub (`casino/index.html`, `casino.js`, `casino.css`); slot polish and show-layer hooks |
| **Games / backend** | Expanded `casino_service` + routes (crash, engines: `slots`, `cards`); ledger and config in `data/casino_config.json` |
| **Progression** | `casino_progression`, achievements data, shop + trophies services and catalogs |
| **Competition** | `casino_competition_service`, tournaments wiring |
| **Agents** | `agent_casino_routes`, Kelly-style casino agents, LLM planner, skillset sync |
| **Social** | `casino_social_service`, Discord fanout (`casino_discord_fanout`), platform news hooks |
| **Mobile** | `mobile/casino-twa`, `mobile/casino-app`, `casino/manifest.webmanifest`, `casino-twa-shell.js` |
| **Tests** | `test_casino_crash`, routes, agents, discord fanout, competition expansion, agent LLM (77 tests green) |

**Ops / follow-up:** set Discord webhook env vars for win fanout; Play Store / App Store builds are scaffold-only until signing and store listings are configured; enable `AGENT_CASINO_SECRET` and optional `CASINO_AGENT_LLM` in production.
