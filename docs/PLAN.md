# Master Build Orchestrator — PLAN

Single index for the Masternoder.dk MN2 ecosystem build program.

## Sub-plans

| Plan | Path | Scope |
|------|------|-------|
| MN2 Ecosystem | `docs/plans/masternoder_mn2_ecosystem.plan.md` | Wallet, market, agents, explorer, debugger, casino/generator/game crypto, monitoring |
| EU Crypto Casino | `docs/plans/eu_crypto_casino_platform.plan.md` | Dual-currency casino + compliance |
| Generator Roadmap | `docs/plans/generator_page_roadmap.plan.md` | Generator criticals + MN2 pay/earn foundation |
| Game & Battle | `docs/plans/game_and_battle_review.plan.md` | Battle correctness + game crypto foundation |
| Orchestrator | `docs/plans/master_build_orchestrator.plan.md` | Stage sequencing + gates |

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

| # | Stream | Service hook |
|---|--------|--------------|
| 51 | Role gating | `discord_service` + linked account |
| 52 | Promo codes | `shop_routes` / `data/discord_promo_codes.json` |
| 53 | Alert funnel | `activity_events` → Discord embeds |
| 54 | Partner spotlight | `platform_news` channel=market |
| 55 | Daily digest | `platform_news_digest.run_daily_digest` |
| 56 | Quest bot | `game_mn2_rewards` + daily quest links |
| 57 | Affiliate rotator | `discord_clicks.jsonl` |
| 58 | Casino highlights | `casino_service` opt-in wins |
| 59 | Generator showcase | `video_generator_service` on complete |
| 60 | Support bot | RAG + Customer Support Copilot |

**Infrastructure:** `backend/services/discord_service.py`, `backend/routes/discord_routes.py`, `logs/discord_outbox.jsonl`

## Shared backbone files

- Economy: `backend/services/unified_points_database.py`
- MN2: `mn2_wallet_service.py`, `mn2_rpc_client.py`, `mn2_ledger.py`, `data/mn2_config.json`
- Activity: `backend/services/activity_events_service.py` → `logs/activity_events.jsonl`
- Wiring: `backend/register_blueprints.py`, `all_page_routes.py`, `navigation-toolbar.js`
