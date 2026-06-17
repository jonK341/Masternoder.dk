# Master Build Orchestrator — PLAN

Single index for the Masternoder.dk MN2 ecosystem build program.

## Sub-plans

| Plan | Path | Scope | Status |
|------|------|-------|--------|
| MN2 Ecosystem | `docs/plans/masternoder_mn2_ecosystem.plan.md` | Wallet, market, agents, explorer, debugger, casino/generator/game crypto, monitoring | Phase 14 pending |
| EU Crypto Casino | `docs/plans/eu_crypto_casino_platform.plan.md` | Dual-currency casino + compliance | **Done** |
| Generator Roadmap | `docs/plans/generator_page_roadmap.plan.md` | Generator criticals + MN2 pay/earn foundation | **Done** |
| Game & Battle | `docs/plans/game_and_battle_review.plan.md` | Battle correctness + game crypto foundation | Active (optional items) |
| Orchestrator | `docs/plans/master_build_orchestrator.plan.md` | Stage sequencing + gates | Stage 4 pending |

## Build stages

1. **Stage 0** — Foundations (generator, battle, MN2 health, casino baseline) → **Gate A**
2. **Stage 1** — Economy core (ledger, activity events, pricing, game rewards, treasury address) → **Gate B**
3. **Stage 1.5** — Gate S hardening (atomic money path, off-request workers, treasury custody) → **Gate S**
4. **Stage 2** — Features (market, agents, generator/game/casino crypto, news, Discord, debugger, aggregator, AI M1–M8)
5. **Stage 3** — Cross-cutting (SSE monitor, security cron, control board)
6. **Stage 4** — pytest, `MN2_ECOSYSTEM_REPORT.md`, `MN2_TODO.md` → **Gate D**

## Readiness gates

- **Gate A:** `/api/health`, `/api/mn2/health`, `/api/themes/user`, battle tests, unified points R/W, casino MN2 rail
- **Gate B:** `mn2_ledger` + `activity_events.jsonl`, `generator_pricing_service`, `game_mn2_rewards`
- **Gate S:** Atomic+locked money writes, idempotency, earn auth, treasury ops-only, backups
- **Gate C:** Market, generator-crypto, game-rewards, news+Discord emit activity events
- **Gate D:** Full pytest green + reports committed

## M7 — Staking Yield Advisor (idé #29)

- **Service:** `backend/services/ai_staking_advisor_service.py`
- **Routes:** `GET /api/ai/staking-advisor`, `POST /api/ai/staking-advisor/refresh` (ops)
- **Cache:** `data/ai_staking_advisor_cache.json`
- **Decisions:** `data/ai_monetization_decisions.jsonl`
- **Rule:** Informational only — never auto stake/unstake

## M8 — Discord channel economy (idéer 51–60)

**Full map:** [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md)

| # | Stream | Service hook | Cross-road status |
|---|--------|--------------|-------------------|
| 51 | Role gating | `discord_service` + `/api/discord/link` | Partial — no Profile UI |
| 52 | Promo codes | `casino_social_service` (casino only) | Shop-wide not built |
| 53 | Alert funnel | `discord_m8_streams.run_alert_funnel` | Live — includes market, camgirls, agents |
| 54 | Partner spotlight | `platform_news` channel=market | Live |
| 55 | Daily digest | `platform_news_digest.run_daily_digest` | Live |
| 56 | Quest bot | `user_engagement` daily quests | Live |
| 57 | Affiliate rotator | Daily rotation → `#announcements` | Live — market, camgirls, compendium |
| 58 | Casino highlights | `casino_discord_fanout` | Live |
| 59 | Generator showcase | `video_generator_service` on complete | Live |
| 60 | Support FAQ | `GET /api/discord/support/faq` | Live — market, camgirls topics |
| — | **Market fan-out** | `market_discord_fanout` → `#market` | Code ready — deploy + cron |

**Infrastructure:** `discord_service.py`, `discord_m8_streams.py`, `market_discord_fanout.py`, `casino_discord_fanout.py`, `discord_routes.py`, `logs/discord_outbox.jsonl`, `logs/activity_events.jsonl`

**M8 build order (after Gate S + Phase 5):** 51 Role Gating → 52+56 Promo/Quest → 53+55 Funnel/Digest → 58+59 Casino/Generator → 57+54+60 Affiliate/Partner/Support → market fan-out

**Compliance:** No custody on Discord; rewards on-site with auth; gambling promos geo-blocked; affiliate disclosure in embed footer.

## Stage 0 Gate A (verified)

| Check | Status |
|-------|--------|
| `GET /api/health` | Pass |
| `GET /api/mn2/health` | Pass (degraded OK if daemon offline) |
| `GET /api/themes/user` | Pass |
| Battle URL tests | Pass (`test_02_battle.py`) |
| Unified points idempotency | Pass (`test_gate_a_orchestrator.py`) |
| Casino MN2 rail | Pass (`casino_service.py`) |

## Shared backbone files

- Economy: `backend/services/unified_points_database.py`
- MN2: `mn2_wallet_service.py`, `mn2_rpc_client.py`, `mn2_ledger.py`, `data/mn2_config.json`
- Activity: `backend/services/activity_events_service.py` → `logs/activity_events.jsonl`
- Wiring: `backend/register_blueprints.py`, `all_page_routes.py`, `navigation-toolbar.js`
