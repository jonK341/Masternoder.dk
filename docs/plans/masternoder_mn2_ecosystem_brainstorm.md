# MN2 Ecosystem — Brainstorm: what to do first

**Source plan:** [masternoder_mn2_ecosystem.plan.md](masternoder_mn2_ecosystem.plan.md)  
**Grounded against:** `docs/MN2_ECOSYSTEM_REPORT.md`, `docs/MN2_TODO.md`, live services (2026-07-24)

---

## One-sentence product

[REDACTED] is a custodial MN2 platform where users earn and spend MN2 across wallets, market, games, generator, casino, and agents — with ops health and Gate S money integrity as the floor.

---

## Reality check (do not restart Phase 0)

The ecosystem plan’s YAML todos still say Phase 0–14 `pending`. The repo disagrees:

| Plan phase | Actual status | Evidence |
|------------|---------------|----------|
| 0 Audit + report | **Done** | `docs/MN2_ECOSYSTEM_REPORT.md` (money path + Gate A) |
| 1 Daemon health | **Done (code)** | Hub keys wired: `daemon_staking`, `discord_outbox`, `network_alerts`; `test_mn2_health` green |
| 2–8 Wallet / market / agents / explorer / monitor / Discord | **Mostly built** | Services + routes + tests present; ops/TODO is the backlog |
| 9–13 Security / generator / game / customers / AI | **Largely shipped** | Report + MN2_TODO Done section |
| Live ops focus | **Exchange + multi-ping + health warn** | `MN2_TODO.md` P1 sprint |

**Verdict:** Treat the ecosystem plan as an architecture map, not a fresh build queue. First work = close integrity gaps that still block trust in money/ops, then align the plan todos with reality.

---

## What “done” looks like for the next slice

1. Ops can trust `GET /api/mn2/health` (matches Health Ops Hub + unit tests).
2. Gate S money paths stay green under concurrency (no silent double-credit).
3. Plan frontmatter todos reflect Done / Partial / Next (no false “pending”).
4. Only then: agent treasury funding / larger market capital moves.

---

## Options (pick one first)

### A — Health contract close (recommended first)
**What:** Finish Phase 1: wire `daemon_staking`, `discord_outbox`, `network_alerts` into `/api/mn2/health`; green `tests/unit/test_mn2_health.py`; ensure network snapshot path can populate history.
**Why first:** Smallest coding surface; unblocks ops truth; called out as watch/warn in MN2_TODO.
**Risk:** Low. No fund moves.
**Out of scope:** Agent 100k funding, new market features, Discord M8 product streams.

### B — Gate S load + conservation proof
**What:** Critical from the report — concurrency/idempotency tests on `unified_points` + ledger conservation under parallel deposit/withdraw/escrow.
**Status (2026-07-24):** **Done** — `admin_audit_service` restored; `mn2_ledger.append_entry` atomic + deposit txid unique; `test_gate_s_orchestrator.py` covers same-ref storm, credit/debit net, escrow roundtrip, concurrent ledger appends, deposit+points conservation (11 passed).
**Why:** Money integrity is the real floor before any treasury distribution.
**Risk:** Medium (test harness / flaky RPC mocks). Still no live fund moves.
**Depends on:** A preferred first so failures are attributed correctly (daemon vs app).

### C — Agent treasury readiness (config only)
**What:** Add `agent_funding` block to `mn2_config.json`, document cold-wallet policy, dry-run distribution status endpoints — **no** auto-send 600k MN2.
**Status (2026-07-25):** **Done** — `agent_funding.live_distribute=false` in config; `treasury_status` + ops-gated routes; `distribute_agent_funding` dry-run by default; sign-off/reconcile endpoints; CLI `scripts/treasury_signoff.py`; tests green.
**Why:** Unblocks Phase 4 funding design without spending treasury.
**Risk:** Medium if someone enables distribute too early.
**Depends on:** A + B before any distribute job runs live.

### D — Sync plan ↔ TODO (docs only)
**What:** Rewrite ecosystem plan todos to Done/Partial/Next; fold Critical/Upgrades into `MN2_TODO.md` shape.
**Why:** Stops the next agent from re-auditing from scratch.
**Risk:** None. High leverage for collaboration.
**Can parallel with A.**

### E — Jump to exchange / multi-ping P1 (ops product)
**What:** Follow `MN2_TODO.md` P1 (daemon v1.3 multi-ping, exchange gateway).
**Why:** That’s where live product attention already is.
**Risk:** High scope creep vs ecosystem plan; needs C++/SSH/daemon work.
**Only if:** User priority is fleet ENABLED / exchange, not ecosystem plan hygiene.

---

## Recommendation

**Do A + D this session, then B before any C live.**

1. **First coding:** Option A — close `/api/mn2/health` contract + green tests.  
2. **Same pass docs:** Option D — mark ecosystem plan phases Done/Partial so the map matches the ground.  
3. **Next coding:** Option B — Gate S concurrency / conservation.  
4. **Hold:** Option C live distribute and Option E unless you explicitly pivot to exchange/daemon P1.

### Why not “start at Phase 0”
Audit already exists. Re-auditing burns cycles without new product value. The plan’s own Phase 0 deliverable (`MN2_ECOSYSTEM_REPORT.md`) is already there; the valuable “first” is the unfinished Phase 1 health contract that ops still watches as degraded/warn.

### Success criteria for “first done”
- [x] `pytest tests/unit/test_mn2_health.py` green  
- [x] `/api/mn2/health` returns Hub-expected components  
- [x] Ecosystem plan Phase 1 marked done (code); remaining todos still need full sync (Option D)  
- [x] Short note in report: Phase 1 Hub contract closed

---

## Open decisions (answer before large builds)

1. **Primary next product:** ops integrity (A/B) vs exchange P1 (E)?  
2. **Agent treasury:** paper/config only for now, or schedule real funding after Gate S proof?  
3. **Plan ownership:** keep one ecosystem plan as source of truth, or treat `MN2_TODO.md` as the sprint board and the plan as archive?

**Default answers if no reply:** (1) A/B, (2) config-only, (3) TODO = sprint board, plan = architecture map updated by D.
