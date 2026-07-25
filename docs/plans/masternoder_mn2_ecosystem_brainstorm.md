# MN2 Ecosystem — Brainstorm: what to do first

**Source plan:** [masternoder_mn2_ecosystem.plan.md](masternoder_mn2_ecosystem.plan.md)  
**Grounded against:** `docs/MN2_ECOSYSTEM_REPORT.md`, `docs/MN2_TODO.md`, live services (2026-07-25)

---

## One-sentence product

[REDACTED] is a custodial MN2 platform where users earn and spend MN2 across wallets, market, games, generator, casino, and agents — with ops health and Gate S money integrity as the floor.

---

## Reality check (Option D synced)

| Plan phase | Status | Evidence |
|------------|--------|----------|
| 0 Audit + report | **Done** | `MN2_ECOSYSTEM_REPORT.md` |
| 1 Daemon health | **Done** | Hub contract + `test_mn2_health` (Option A) |
| 2 Wallet | **Partial** | Service helpers; routes refresh/connect next |
| 3 Market | **Done** | `p2p_market_*` + page + tests |
| 4 Agents | **Partial** | Option C treasury dry-run; trader/cron/admin next |
| 5 Explorer/news/Discord | **Partial** | Infra live; `/api/news/channels` next |
| 6 Debugger Q&A | **Next** | Quiz submit + MN2 rewards |
| 7 Casino crypto | **Partial** | Jackpots/tournaments; cashback/policy next |
| 8 Activity monitor | **Done** | SSE + UI + tests |
| 9 Security cron | **Partial** | Sweep exists; full presets/tests next |
| 10 Generator MN2 | **Done** | Pay/earn + tests |
| 11 Game monitor | **Partial** | Rewards done; Monitor tab + quest fix next |
| 12 Customers | **Done** | Aggregator + page + tests |
| 13 AI intelligence | **Partial** | Waves incomplete |
| 14 Tests/docs | **Partial** | Critical/Upgrades board in `MN2_TODO.md` (Option D) |

**Doc roles:** ecosystem plan = architecture map · `MN2_TODO.md` = sprint board · report = money-path audit.

---

## Options

### A — Health contract close — **Done 2026-07-24**
### B — Gate S load + conservation proof — **Done 2026-07-24**
### C — Agent treasury readiness (config only) — **Done 2026-07-25** (`live_distribute=false`)
### D — Sync plan ↔ TODO — **Done 2026-07-25**
### E — Jump to exchange / multi-ping P1 (ops product)
**What:** Follow `MN2_TODO.md` P1 (daemon v1.3 multi-ping, exchange gateway).  
**Only if:** User priority is fleet ENABLED / exchange.

---

## Recommendation (updated)

Integrity slice **A → B → C → D** is complete. Next product forks:

1. **Ecosystem residuals (Critical C6/C7 / Upgrades U1–U7)** — wallet routes, debugger quiz, trader agents, etc.
2. **Option E** — exchange / multi-ping ops P1 in `MN2_TODO.md`.

Default if no reply: pick from Critical board (C6 wallet routes or C7 debugger quiz) unless pivoting to E.

### Success criteria
- [x] `pytest tests/unit/test_mn2_health.py` green  
- [x] `/api/mn2/health` Hub components  
- [x] Gate S concurrency suite green  
- [x] Treasury `live_distribute=false` + status dry-run  
- [x] Plan todos + `MN2_TODO` Critical/Upgrades synced (Option D)
