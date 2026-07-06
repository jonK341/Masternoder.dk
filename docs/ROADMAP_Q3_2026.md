# MasterNoder.dk — 3-Month Roadmap (July – September 2026) <!-- pragma: allowlist secret -->

**Written:** 2026-07-06 · **Covers:** 2026-07-06 → 2026-10-06
**Status of inputs:** grounded in live repo state (`git`, `gh pr/issue list`), not just the `docs/*_TODO.md` files, several of which are already stale relative to `main`.

---

## 0. Where things actually stand today (reality check)

Before planning new work, here's the verified current state — several existing status docs disagree with each other and with `main`, so treat this section as the source of truth for this roadmap.

| Signal | Finding |
|---|---|
| **Open PRs** | **18 open**, oldest from **2026-06-20** (PR #12) — over 2 weeks of unmerged feature work (lab, trophies, nav, gallery, starmap, casino v10–v14, social fan-out, MN2 wallet hub, fleet ops). |
| **PR rot** | 3 already show `CONFLICTING` merge status (#32 camgirls/Ubuntu ops, #35 fleet cap raise, #44 MN2 wallet hub) — every day these sit unmerged, conflicts compound. |
| **Live CPU incident** | The "140% CPU / old processes" issue investigated this week has a **root cause and fix already written**: PR #46 found an infinite-recursion bug in the path-correction middleware (`PathCorrector.correct_path` ↔ `AIEnhancedPaths.intelligent_path_correction`) firing on every API request, plus an incompatible `SystemPointSnapshot` DB schema. Verified idle CPU **90–100% → ~0.1%** after the fix. **It is not yet merged or deployed.** |
| **Casino** | Waves 1–5 (25 feature ideas) are **code-complete** per `docs/CASINO_TODO.md` (2026-07-01) and PR #43 (casino mega expansion) **merged 2026-07-04**. Remaining work is ops: deploy the slice, Play Store $25 signup, agent secrets + Discord live fan-out. |
| **MN2 / masternodes** | 30 hosted, 28 active, fleet ops stable; **daemon multi-ping v1.3 still not built/deployed** — this caps meaningful masternode scaling (only the synced privkey can go `ENABLED`). |
| **Tests** | Latest full run (PR #45, 2026-07-05): **913 passed / 67 failed / 2 skipped** on `pytest tests/unit` — much healthier than the historical "35% pass" figure still floating around in Jan-2025 docs. |
| **Money-path safety** | `docs/plans/master_build_orchestrator.plan.md` flags, by direct code inspection, that `unified_points_database.py` writes balances **without file locking or atomic replace** — concurrent bets/trades/claims can race and double-spend. This is still open and is the single biggest risk given real PayPal/MN2 money already flows through casino, shop, and hosting. |
| **Doc drift** | Root-level `*_STATUS.md` / `*_REPORT.md` / `LAUNCH_READY.md` files (Jan 2026) claim the site has 0% errors and is fully live/launch-ready, while `ISSUES_PRIORITY_LIST.md` from the same week lists 131/200 requests 404ing. Neither has been reconciled with current reality. |

**Implication for this roadmap:** the most valuable thing to do in week 1 is not a new feature — it's clearing the merge backlog and deploying the fix that's already sitting in PR #46.

---

## 1. Guiding principle

Follow the sequencing already designed in [`docs/plans/master_build_orchestrator.plan.md`](plans/master_build_orchestrator.plan.md) (Gates A → B → S → C → D: stabilize foundations → shared economy core → **hardening (Gate S)** → feature layers → cross-cutting/finish). This roadmap adds one missing stage in front of it — **Stage -1: clear the PR backlog** — because `main` is now materially behind what's actually been built, and inserts explicit human-only action items the agents cannot complete themselves (payments, legal accounts, credential rotation approval).

**Non-negotiables for the quarter** (to stop this backlog from recurring):
- No PR sits open more than **1 week** without merge or explicit close/superseded decision.
- Every change that touches balances/wallets/payments must include an idempotency key and a concurrency test.
- One status doc per subsystem, dated, superseding all older "final report" files — no new `*_FINAL_STATUS.md` snapshots.

---

## Month 1 (Jul 6 – Aug 3): Stop the bleeding, clear the backlog

### Week 1 — Live incident + easiest wins first
- [ ] **Merge + deploy PR #46** (CPU/points-schema/restart-script fix) — this is an active live-site incident with a verified fix sitting idle. Highest priority item on the entire roadmap.
- [ ] **Merge PR #45** (`AGENTS.md` dev environment docs) — zero risk (`MERGEABLE`, no app code changed), immediately makes every future agent/dev session faster and more correct (venv layout, run/lint/test commands, known gotchas documented).
- [ ] Re-verify `GET /api/health` and `GET /api/mn2/health` are green post-deploy (Gate A check #1 from the orchestrator plan).

### Week 2 — Triage and merge the remaining 16 open PRs
Work through in dependency-safe order, resolving conflicts while they're still small:
1. **Resolve the 3 `CONFLICTING` PRs first** (#32 camgirls/Ubuntu ops, #35 fleet cap raise, #44 MN2 wallet hub) — rebase or close/re-cut before they rot further.
2. **June 20–21 batch** (#12–#18: lab hub, trophies/control board, nav/customers page, backend cogs/security cron, gallery/profile/health, starmap hub, engagement/quest sync) — oldest, most likely to be safe/independent; merge in small batches with smoke tests between each.
3. **June 23–24 casino/social batch** (#28 camgirls PayPal, #38–#42: social fan-out, Discord casino app, casino hub super, casino v10–v14, deploy-ops manifests) — these build on the already-merged casino mega expansion (#43), so sequence them relative to it and re-run `tests/unit/test_casino_ideas_wave*.py` after each merge.
4. **Fleet ops** (#36, #37) — masternode activetime/sync-ping watchers; low risk, ops-only.
- [ ] After each batch: run `python scripts/service_check_all_components.py` against a staging/prod smoke and update **one** consolidated status doc (see Week 3).

### Week 3 — Reconcile documentation with reality
- [ ] Retire or clearly mark superseded: `LAUNCH_READY.md`, `PRODUCTION_LIVE.md` <!-- pragma: allowlist secret -->, `FINAL_STATUS.md`, `README_FINAL.md`, the multiple `*_CLEANUP_AND_*.md` reports — replace with a single dated `docs/STATUS.md` reflecting the post-merge state.
- [ ] Re-run the 404 probe behind `ISSUES_PRIORITY_LIST.md` and close out or re-open with current numbers (it's from January; the 131/200 figure predates 6+ months of route work and is almost certainly stale, but hasn't been re-measured).
- [ ] Root-cause and fix remaining `default_user` fallbacks flagged since January — this now matters far more than it did in January, because Month 2's money-path hardening (below) depends on real user identity for every earning action.

### Week 4 — Casino + MN2 ops backlog (from the docs' own "next actions")
- [ ] `python scripts/deploy.py casino --ask-pass` — deploy the merged casino slice; verify `/api/agent/casino/models`.
- [ ] **Human action:** pay Play Store $25 signup, create `dk.masternoder.casino`, upload first AAB, copy the App Signing SHA-256 into `scripts/casino_play_assetlinks_update.py`.
- [ ] Dry-run casino agent daemon (`CASINO_AGENT_DRY_RUN=1`) on server, verify Discord fan-out dry-run, then flip `CASINO_FANOUT_LIVE=1` only after verification.
- [ ] Continue MN2 daemon v1.3 (multi-ping) build/deploy tracking — this is the top infra blocker for masternode fleet scaling past the current conservative 250-slot cap.

**Gate A exit criteria (per orchestrator plan):** health endpoints green, `unified_points_db` read/write verified, `GET /api/themes/user` returns 200, battle tournament URLs resolve + tests pass, casino MN2 rail confirmed. Do not start Month 2 hardening on top of an unstable base.

---

## Month 2 (Aug 3 – Aug 31): Harden the money path (Gate S) — the critical quarter priority

Real money already moves through this platform (PayPal shop/hosting/casino deposits, MN2 wallet balances, masternode collateral). The orchestrator plan's "A+ critical-to-service requirements" are all still open per direct code inspection — this month exists to close them before any more money-touching surface area ships.

### Money-write integrity (CRITICAL)
- [ ] Add a serialized, atomic money path to `backend/services/unified_points_database.py`: per-user lock + atomic write (`tempfile` + `os.replace`), or migrate money-critical mutations into single SQL transactions.
- [ ] Enforce a unique idempotency `reference` on every credit/debit (reuse the existing casino ledger pattern as the template).
- [ ] Add concurrency tests: simulate parallel bets/claims/trades against the same balance and assert no double-spend.

### Runtime stability (defense in depth beyond PR #46's specific fix)
- [ ] Confirm video encoding always runs in a real subprocess, never the in-worker thread fallback.
- [ ] Move the agent trader/runner to cron, not in-request execution.
- [ ] Serve `GET /api/activity/stream` SSE off a path that can't starve the uWSGI worker pool (or add a short-poll fallback).
- [ ] Set uWSGI `max-requests` / `harakiri` / concurrency caps; verify behavior under `LITE_APP=1`.

### Treasury / hot-wallet custody (CRITICAL)
- [ ] Cap the operating hot wallet; cold/multisig the remainder of the 600k+ MN2 agent treasury.
- [ ] Ensure the treasury address is ops-only, never rendered on public pages; cap per-run distribution.
- [ ] Add a reconciliation job (pool vs. `agent_wallets` vs. `mn2_ledger`) every cycle, surfaced in `proof-of-reserves`.
- [ ] Add explicit caps/audit for internal funding flows (they currently bypass `data/mn2_config.json`'s real-withdrawal caps).

### Reward-farming / sybil abuse (CRITICAL)
- [ ] Require real authenticated identity (reject `default_user`/anonymous) for every MN2-earning action (Q&A, generator, game).
- [ ] Add per-account/day earning caps; apply `backend/middleware/rate_limit_middleware.py` to earn endpoints; add an anomaly-detection cron.

### Admin authorization + backups
- [ ] Real admin auth (not a shared secret) on the agents control board and any treasury/distribute endpoints; append-only admin action audit log.
- [ ] Scheduled backup job for JSON balance stores + `mn2_ledger`; pre-migration snapshot + documented restore procedure.
- [ ] Idempotent migration scripts for any new tables (`agent_wallets`, market orders/trades, activity events), consistent with the existing `db.create_all()` pattern.

### Compliance
- [ ] Casino real-money paths reuse deposit/loss limits, KYC gates, and geo rules from the EU crypto casino plan — verify these are actually wired to the live PayPal/deposit flows, not just implemented in isolation.

### Repo hygiene (lower risk, do in parallel)
- [ ] Root-level script cleanup phase 1: consolidate the 100+ duplicate `deploy_*.py`/`restart_*.py`/`fix_*.py` scripts at repo root into `scripts/` with clear, non-duplicated names (continues the Jan-2026 cleanup that flagged 790 unused files but didn't finish). This directly reduces the risk of someone running a stale ad-hoc script against prod.
- [ ] Fix the 67 pre-existing `pytest tests/unit` failures (currently 913/982 passing) — prioritize any that touch money/points/wallet code given the hardening work above.

**Gate S exit criteria:** atomic+locked money path live and unit-tested under concurrency; encoding/agent/SSE confirmed off request workers with uWSGI caps; treasury custody + reconciliation + ops-only address enforced; earn endpoints auth-gated + rate-limited; admin auth on control board/treasury; backup job running. **Nothing in Month 3's feature list ships ahead of this gate.**

---

## Month 3 (Aug 31 – Sep 28): Coherent product layer + gated feature expansion

### Strategic clarity first (blocks nothing technical, but should happen early in the month)
- [ ] Resolve the open question in [`docs/PROJECT_RETHINK.md`](PROJECT_RETHINK.md): pick the one-sentence product definition (video-creation-first / gamified-economy-first / agent-first) and use it to decide what expands vs. what moves to "lab"/advanced status. This determines whether the next quarter emphasizes generator, casino/exchange, or the agent surface.
- [ ] Start the "one capability map" (`docs/PROJECT_RETHINK.md` §4.2): every user-facing action mapped to how an agent achieves the same outcome, as a first step toward consolidating the 50+ fragmented `agent_*` blueprints into one agent surface.

### Feature layers (Gate S–gated — only after Month 2 is done)
- [ ] P2P market + agent trader wallets — including the one-time 600k MN2 treasury distribution to trader agent wallets, but **only** after treasury custody controls from Month 2 are live.
- [ ] Generator MN2 pay/earn path (depends on generator criticals already tracked in `docs/plans/generator_page_roadmap.plan.md`).
- [ ] Unified game monitor + game crypto rewards (depends on battle/Hunters correctness fixes).
- [ ] Casino crypto expansion, explorer + multi-channel news, Discord outbound — all routed through the single shared `mn2_ledger` / `logs/activity_events.jsonl` schema (no parallel ad-hoc balance writes — this is the #1 integration rule from the orchestrator plan).

### Cross-cutting
- [ ] Activity monitoring SSE + Discord feed status widgets.
- [ ] Security cron: anomaly/auto-freeze, reconciliation, cleanup, avatar backfill.
- [ ] Agents control board governing market/game agents, behind the real admin auth added in Month 2.

### Process / CI maturity (so the 18-PR backlog doesn't recur)
- [ ] Wire `scripts/service_check_all_components.py` into CI as a post-deploy smoke step, not a manually-run script.
- [ ] Split the existing generic `pytest` CI job into a fast unit subset per-PR + a nightly full-suite run.
- [ ] Adopt smaller, faster-merging PRs as the default working pattern (ties back to the Month 1 non-negotiable of no PR older than 1 week).

**Gate D / quarter-close criteria:** full `pytest` green; `docs/MN2_ECOSYSTEM_REPORT.md` and `docs/MN2_TODO.md` refreshed against actual deployed state; the single `docs/STATUS.md` from Month 1 is the only "current state" doc anyone needs to read.

---

## 2. Human-only actions this quarter (agents cannot do these)

| Action | Blocks |
|---|---|
| Pay Play Store $25 signup + upload first AAB | Casino Android app listing (Month 1) |
| Apple Developer account (or explicit decision to stay PWA-only) | iOS app / AASA (currently paused) |
| Approve/rotate `DEPLOY_PASS` and any credentials currently hardcoded in deploy scripts | Ops security (flagged since Jan, still open) |
| Decide treasury custody approach (which wallet stays hot vs. cold/multisig) | Month 2 treasury hardening |
| Confirm KYC/compliance posture for the casino's target jurisdictions | Month 2 compliance item |
| Add `DEPLOY_HOST`/`DEPLOY_USER`/`DEPLOY_PASS` as Cursor Cloud Agent secrets, if agents should keep doing live-server ops | Any agent-run deploy/diagnostic script (e.g. `scripts/cpu_process_map.py`) |

---

## 3. Top risks if this roadmap isn't followed

1. **PR backlog keeps growing** — at the current rate (18 open in ~2 weeks), conflicts compound and features silently regress each other (already true for #32, #35, #44).
2. **Money-path race conditions** — real PayPal/MN2 money with no atomic writes or idempotency is a double-spend/loss incident waiting to happen, not a theoretical risk.
3. **CPU incident recurs** — PR #46 fixes the specific recursion bug, but Month 2's "off request workers + uWSGI caps" work is what prevents the *next* unbounded-CPU bug from taking the site down the same way.
4. **Doc drift compounds** — every quarter without a single source of truth makes the next roadmap harder to ground in reality (this document required cross-referencing `git`/`gh` state against docs specifically because the docs alone were contradictory).

---

## 4. Success metrics for the quarter

- Zero open PRs older than 1 week by end of Month 1, sustained through Month 3.
- Zero unplanned CPU/uptime incidents after PR #46 deploys.
- 100% of money-crediting/debiting code paths have an idempotency key and a passing concurrency test by end of Month 2.
- `pytest tests/unit` pass rate ≥ 98% (from current 913/982 ≈ 93%) by end of Month 2.
- One `docs/STATUS.md` is the only doc anyone links to when asked "is it live and working" by end of Month 1.
