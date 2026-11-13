---
title: Grid resume, quarantine, and learning
date: 2026-11-13
type: feature
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-brainstorm
execution: code
status: requirements
---

## Goal Capsule

**Objective:** Operators can tell why the grid is quiet, see it unpause and reseed when quote returns, and have losing pairs quarantine themselves while the tick universe shrinks to what is actually fundable — with every guard event logged and fed into exchange agent learning.

**Means:** Keep thin-quote as a full venue quiet period; add auto-resume + reseed; add per-asset quarantine + inventory/quote universe shrink; extend ledger + learning hooks.

**Product authority:** Session brainstorm on top of `docs/ideation/2026-11-13-grid-upgrade-ideas.md`. Surrounding work (sell-only under thin quote, 5–10% TP ladders, denser grids) is out of scope.

**Open blockers:** None for requirements. Planning must confirm PPP `apply_quote_and_loss_guards` vs in-repo grid service drift.

## Product Contract

### Problem

The profit daemon reports `grid live=True ticks=57 open_orders=0` while all venues sit in `thin_quote` pause. Operators cannot see the real reason. Quote recovery does not clear the pause or reseed ladders. A single underwater pair (BINANCE:XRP ≈ −$6.61) and venue-wide guards interact poorly with a 57-pair spray that has no free quote.

### Actors

- **Operator / owner** — funds venues, reads daemon heartbeat and ledgers, expects the grid to recover without a manual state wipe when quote returns.
- **Profit daemon (grid loop)** — applies quiet/quarantine/universe rules every tick and emits summaries.
- **Exchange learning agent** — consumes logged guard outcomes so proficiency / edge bonus can reflect successful resumes and avoid repeating quarantined losers.

### Key Decisions

- Thin quote stays **fully quiet** (no buys and no sells) until free quote recovers. `(session-settled: user-directed — chosen over sell-only and sell-only-on-NK/XE: keep capital for ladder/arb while quote-starved)`
- On recovery, **auto-resume + reseed** on the next tick. `(session-settled: user-directed — chosen over auto-resume-only and manual-only: unstick without operator babysitting)`
- Hard-loss handling is **per-asset quarantine plus shrink the tick universe** to symbols with real free inventory and/or quote. `(session-settled: user-directed — chosen over pair-only and whole-venue: isolate losers and stop empty sprays)`
- Quarantine, resume, universe-shrink, and thin-quote quiet events are **written to log/ledger files and hooked into auto learning**. `(session-settled: user-directed — user added learning + log filing to option 3)`

### Requirements

- **R1 — Honest quiet signal.** When any venue is thin-quote quiet or any asset is quarantined, the daemon grid summary must name the reason(s), count of paused venues/assets, and free-quote hint — not only `open_orders=0`.
- **R2 — Thin-quote full quiet.** While free quote on a venue is below the existing thin-quote threshold, that venue places neither buys nor sells (preserve current full-quiet intent).
- **R3 — Auto-resume + reseed.** When free quote rises above the threshold, clear that venue’s non-manual `thin_quote` pause and reseed a fresh ladder on the next successful tick (inventory/PnL preserved; open orders rebuilt).
- **R4 — Per-asset quarantine.** When a (venue, asset) breaches the hard-loss / underwater rule, quarantine that pair only; other pairs on the venue may continue if the venue is not thin-quote quiet.
- **R5 — Universe shrink.** While quote is constrained or after quarantines, only tick symbols that have fundable quote for buys and/or free base above min notional for sells; skip empty spray targets.
- **R6 — Log filing.** Append structured events for `thin_quote_pause`, `thin_quote_resume`, `asset_quarantine`, `universe_shrink` (and clear/resume counterparts) to the grid ledger/event log with ts, venue, asset, free_quote, realized, reason.
- **R7 — Auto learning.** On those events (and on reseed-after-resume fills that realize PnL), call into the existing exchange agent learning path so quarantine/resume history affects skill proficiency / learning bonus — losses and repeated quarantines must not look like silent no-ops.
- **R8 — Manual pauses stay manual.** Operator/manual venue pauses are never auto-cleared by quote recovery.

### Acceptance Examples

- **A1.** All venues thin-quote quiet → heartbeat shows `thin_quote` (or equivalent) with venue list; `open_orders` may be 0 but is not the only signal.
- **A2.** Free quote on NonKYC rises above threshold → within one grid interval the `thin_quote` pause is gone and that venue has reseeding open orders (subject to spread/API health).
- **A3.** BINANCE:XRP quarantined for hard loss → other Binance symbols still eligible; XRP is skipped until quarantine lifts per planning’s lift rule.
- **A4.** After quarantine + shrink, tick count targets only fundable symbols; ledger contains matching `asset_quarantine` / `universe_shrink` lines.
- **A5.** A resume or quarantine event updates learning state (proficiency/bonus or explicit learn call recorded), visible in learning/monitor tests or agent fields.

### Non-goals

- Sell-only mode during thin quote.
- Default 5–10% take-profit resting ladders.
- Redesigning maker-quote service yield logic (may stay complementary).
- Fixing venue API key/401 issues beyond surfacing them in the honest quiet signal if already detected.

### Success Criteria

- Operators can diagnose “why quiet” from one heartbeat line.
- Quote top-up alone returns the grid to placing orders without manual state edits.
- One losing pair cannot silence an entire healthy venue.
- Guard lifecycle is auditable in logs and reflected in auto learning.

### How This Work Fits Together

Builds on the live PPP quote/loss guards and the ideation mix (heartbeat, resume, quarantine, universe). Defers sell-only thin-quote and wide TP ladders. Complements dual-farm / hunter / pbook which still need funded legs separately.

### Outstanding Questions for Planning

- Exact quarantine lift rule (cooldown hours vs manual vs realized recovery).
- Whether universe shrink is hard-skip only or also rewrites stuck-inventory → grid apply lists.
- Which learning agent id / skill ids receive grid guard events.
