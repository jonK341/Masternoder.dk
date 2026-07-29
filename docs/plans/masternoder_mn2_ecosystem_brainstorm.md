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
| 2 Wallet | **Done** | refresh/connect/address-book/transfer + profile UX |
| 3 Market | **Done** | `p2p_market_*` + page + tests |
| 4 Agents | **Done (code)** | Trader level-gates + skills + control board; C3 live distribute blocked |
| 5 Explorer/news/Discord | **Done (code)** | channels/publish/RSS + auto-hooks; Discord/M8 live |
| 6 Debugger Q&A | **Done** | Quiz submit + MN2 + anti-farm |
| 7 Casino crypto | **Done** | Cashback + swap UI + `CASINO_CRYPTO_POLICY.md` |
| 8 Activity monitor | **Done** | SSE + UI + tests |
| 9 Security cron | **Done** | Full presets + `test_security_cron` |
| 10 Generator MN2 | **Done** | Pay/earn + tests |
| 11 Game monitor | **Done** | Monitor tab + quest fix + top-10 earn |
| 12 Customers | **Done** | Aggregator + page + tests |
| 13 AI intelligence | **Done (inventory)** | `GET /api/ai-intelligence/waves`; deferred waves tracked |
| 14 Tests/docs | **Done** | Critical/Upgrades board in `MN2_TODO.md` (Option D) |

**Doc roles:** ecosystem plan = architecture map · `MN2_TODO.md` = sprint board · report = money-path audit.

---

## Options

### A — Health contract close — **Done 2026-07-24**
### B — Gate S load + conservation proof — **Done 2026-07-24**
### C — Agent treasury readiness (config only) — **Done 2026-07-25** (`live_distribute=false`)
### D — Sync plan ↔ TODO — **Done 2026-07-25**
### E — Jump to exchange / multi-ping P1 (ops product)
**What:** Follow `MN2_TODO.md` P1 (daemon v1.3 multi-ping, exchange gateway).  
**Status (2026-07-25):** **Code slice done** — multi-ping safety gate (`multi_ping_enabled` requires daemon ≥1.3; config flag `false`). **Still ops:** build/deploy v1.3 binary, QA probes, then flip flag. Exchange PayPal webhook rail = next code slice after ops binary (see U8 / P1).  
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
