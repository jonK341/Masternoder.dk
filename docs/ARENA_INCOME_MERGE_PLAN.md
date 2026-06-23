# Arena — merge `/game` + `/battle` into one income-friendly hub

This plan **merges the `/game` Champion Pulse hub and the `/battle` competitive page into a single revenue-generating destination ("Arena")** and adds real income streams (real‑money tournament buy‑ins, PvP wagering, ranked entry fees, and a paid shop) by **reusing the casino's money rails** instead of building a second payment system.

## Why merge, and why this shape

Today's split is the problem:
- **`/game`** (`game/index.html`) is a *dashboard/aggregator* (Champion Pulse: timestamps, season, level, next‑action buttons, MN2 earning relays). It has **no payment rail** and takes no money — it's a launcher.
- **`/battle`** (`battle/index.html`, `backend/routes/battle_routes.py`) is *almost entirely internal economy*. Its only crypto hook (`_battle_crypto_*`) **pays MN2 out** — a cost center. Tournaments have `entry_fee`/`prize_pool` fields but they are internal points, not real money.
- **The casino** already owns every money primitive we need: `casino_service._validate_bet()` (with the `account_security_service.check_real_money_action()` gate for `mn2`/`usd`), `_apply_balance_delta()`, `_finalize_bet()`, and `_append_ledger()` → `casino_ledger`.

So the cheapest path to the most income is: **fold the game hub into battle, present them as one "Arena", and route every paid action through the casino rails** (no new payment system, no fragmented blueprints — consistent with `.cursor/rules/project-rethink.mdc`).

## Locked constraints (inherited)

1. **Three currency rails stay as‑is:** `coins` (cosmetic), `mn2_balance` (liquid MN2), `casino_fiat_balance` (PayPal USD). Every paid Arena action takes a `currency` param and moves money through `_apply_balance_delta()`.
2. **Staked MN2 is off‑limits** (`MN2_STAKING_PLAN.md` §14 #10). Arena only ever touches the liquid `mn2_balance`, never `mn2_staked`.
3. **Real‑money requires the security gate.** Any `mn2`/`usd` debit goes through `check_real_money_action()` (password + `verification_token`). No Arena path may bypass it.
4. **Agent/API parity** (`PROJECT_RETHINK.md`): every paid action is reachable via API with a `user_id` on the **existing** `battle` blueprint — no new fragmented blueprints.
5. **Honesty in odds / no rigged real‑money wagers.** See compliance note below.

## Compliance note — what may take real money

Battle PvE outcomes are **RPS + weighted‑random AI the house controls**. We will **not** wager real money on a house‑controlled outcome. Real money is allowed only where the house does not control who wins:
- ✅ **Tournament buy‑ins** — pay to enter, ranked by score, fixed prize split, house takes a **rake**. House revenue = rake, not "beating the player".
- ✅ **PvP duel wagering** — two real players escrow into a pot, winner takes pot minus rake.
- ✅ **Shop** — boosters / cosmetics / season pass are flat purchases.
- ⚠️ **Ranked entry fees** — allowed as a pure entry fee that funds a transparent prize pool (rake on top), *not* as a bet against the AI for a multiplier.

## The income engine: escrow + rake

A single shared helper makes all four levers safe and reconcilable.

**`backend/services/arena_economy.py` (NEW)** — thin wrapper over casino primitives:
- `collect_buy_in(user_id, amount, currency, context)` → validates (incl. real‑money gate via casino `_validate_bet`), debits the stake into an **escrow** record, ledgers it (`game="arena_<context>"`, `phase="buy_in"`). Returns an `entry_id`.
- `payout(user_id, amount, currency, context, parent_entry_id)` → credits a winner/prize and ledgers it (`phase="payout"`).
- `rake(amount, rake_pct)` → splits a pot into `prize_pool` and `house_take`; the house take is ledgered to a house account so pools are **reconcilable** (mirrors the conservation discipline in `MN2_STAKING_PLAN.md` §8 and the casino jackpot ledgering).
- Escrow + event state lives in the existing `battle_v2_state.json` store (`_load_battle_v2_state`) under an `arena` namespace, or a small SQLite table if volume warrants (reuse `casino_ledger` pattern). TTL so refunds/voids are deterministic.

**Invariant to test:** `sum(buy_ins) == sum(prize_payouts) + house_take` per event, per currency. No money is created or destroyed outside the ledger.

## Config

**`data/arena_config.json` (NEW)** (or an `arena` block in `battle_minimal_content.json`):
- `rake`: default house rake % per lever (e.g. tournaments 10%, pvp 5%).
- `buy_in_tiers`: allowed buy‑in amounts per currency.
- `ranked`: entry fee + prize‑pool split per ranked mode.
- `shop`: catalog of boosters/cosmetics/season pass with USD + MN2 prices.
- Exposed via a public `GET /api/battle/arena/config` (no secrets) for the UI and agents.

## API surface (additions, all on the existing `battle` blueprint)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/battle/arena/config` | Rake, tiers, shop catalog (agent‑discoverable) |
| GET | `/api/battle/arena/summary` | **Merged** game+battle progress + income surfaces in one payload |
| POST | `/api/battle/tournaments/<id>/buy-in` | Real‑money buy‑in → escrow + prize pool |
| POST | `/api/battle/tournaments/<id>/settle` | Close event → rake + ranked prize payout (ledgered) |
| POST | `/api/battle/pvp/duel` (+ `/accept`, `/resolve`) | Two‑player escrow pot, winner take minus rake |
| POST | `/api/battle/ranked/enter` | Ranked entry fee → prize pool |
| GET/POST | `/api/battle/shop`, `/api/battle/shop/purchase` | Boosters / cosmetics / season pass (USD+MN2) |

Stateful events (tournaments, duels) store server‑side state keyed by `user_id` + `entry_id` with a TTL so a refresh can't double‑settle (same rule as the casino's stateful games).

## Frontend merge

Fold `game/index.html` content into the battle page (or make `/game` redirect to the unified Arena, like the existing profile‑tab redirects in `all_page_routes.py`):
- **One hub, tabbed:** Champion Pulse (level/season/next‑action) + Battle (quick battle, history, leaderboard) + **Income** (tournaments, PvP, ranked, shop) + Social (clans).
- Income surfaces show live prize pools, buy‑in tiers, the rake (honest), and a wallet strip (coins / MN2 / USD with the verification prompt for real‑money).
- Reuse the casino's real‑money verification UX (password + `verification_token`) so the gate is consistent.

## Rollout phases

| Phase | Scope | Ships |
|-------|-------|-------|
| **A1 — Economy core** | `arena_economy.py` (escrow + rake + payout, reconcilable), `arena_config.json`, `/arena/config`. No user‑facing change. | Income foundation |
| **A2 — Tournaments** | Real‑money buy‑in + settle (rake + ranked prize payout), ledgered. | First revenue |
| **A3 — PvP + Ranked** | Duel wagering pot + ranked entry fees. | More revenue |
| **A4 — Shop** | Boosters / cosmetics / season pass (USD+MN2). | Recurring revenue |
| **A5 — Merge UI** | One Arena hub: fold `/game` in, add income tabs + wallet strip; `/game` → Arena redirect. | Single destination |

A1 is the prerequisite (every paid lever uses it). A2–A4 are independent and can interleave; A5 ties them together visually.

## Testing strategy

- **Economy:** escrow conservation — `sum(buy_ins) == prizes + house_take` per currency; refunds void cleanly; TTL expiry.
- **Real‑money gate:** unverified `mn2`/`usd` buy‑in is blocked; `coins` is not gated.
- **No double‑settle:** replaying a settle/resolve is idempotent.
- **Routes:** buy‑in → settle prize split; bad currency/tier rejected.
- Reuse `tests/unit/test_02_battle.py` harness + casino test fixtures.

## Touchpoints summary

**New:** `backend/services/arena_economy.py`, `data/arena_config.json`, `tests/unit/test_arena_economy.py`.
**Extend:** `backend/routes/battle_routes.py` (new paid endpoints + merged summary), `battle/index.html` + `static/js/*battle*` / `static/css/battle-graphics.css` (income tabs + wallet), `backend/routes/all_page_routes.py` (`/game` → Arena redirect).
**Reuse (unchanged):** `casino_service` money primitives, `account_security_service`, `unified_points_database`, `casino_ledger`.
