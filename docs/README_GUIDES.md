# Documentation index

**Last updated:** 2026-06-17

## Start here

| Doc | Purpose |
|-----|---------|
| [PLAN.md](./PLAN.md) | Master build orchestrator — stages, gates, sub-plans |
| [MN2_TODO.md](./MN2_TODO.md) | MN2 critical work + upgrades |
| [PLATFORM_TODO.md](./PLATFORM_TODO.md) | Cross-site platform backlog |
| [PROJECT_RETHINK.md](./PROJECT_RETHINK.md) | Architecture intent, agent parity, consolidation |

## Operations & deploy

| Doc | Purpose |
|-----|---------|
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Deploy workflow |
| [DEPLOYMENT_PLAN.md](./DEPLOYMENT_PLAN.md) | uWSGI / server layout |
| [MN2_OPS.md](./MN2_OPS.md) | MN2 daemon, RPC, reconcile |
| [SERVER_QUICK_REFERENCE.md](./SERVER_QUICK_REFERENCE.md) | SSH / paths cheat sheet |
| [SERVER_CLEANUP.md](./SERVER_CLEANUP.md) | Disk cleanup on production |
| [UWSGI_EXIT1_TROUBLESHOOTING.md](./UWSGI_EXIT1_TROUBLESHOOTING.md) | uWSGI crash loop |
| [GATEWAY_504_502.md](./GATEWAY_504_502.md) | Gateway timeouts |
| [DATABASE_HEALTH_GREEN_CHECKLIST.md](./DATABASE_HEALTH_GREEN_CHECKLIST.md) | Health checks |

## MN2 & crypto

| Doc | Purpose |
|-----|---------|
| [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](./MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md) | Canonical MN2 integration spec |
| [MN2_STAKING_PLAN.md](./MN2_STAKING_PLAN.md) | Staking, P2P, on-ramp |
| [MN2_EXPLORER_PLAN.md](./MN2_EXPLORER_PLAN.md) | Block explorer |
| [MN2_TRADER_MARKET.md](./MN2_TRADER_MARKET.md) | Internal order book + trader agents |
| [DISCORD_CROSSROADS.md](./DISCORD_CROSSROADS.md) | Discord ↔ platform integration map (M8 #51–60) |
| [CAMGIRLS_PHASE1C.md](./CAMGIRLS_PHASE1C.md) | Camgirls production onboarding |
| [EXPLORER_REINSTALL_CHECKLIST.md](./EXPLORER_REINSTALL_CHECKLIST.md) | Explorer reinstall |
| [AGENTS_MN2.md](./AGENTS_MN2.md) | Agent-facing MN2 notes |

## Rulebooks & product

| Doc | Purpose |
|-----|---------|
| [RULEBOOK_CANON.md](./RULEBOOK_CANON.md) | Canonical cross-cutting rules |
| [COMPENDIUM_RULEBOOK_V1_V15.md](./COMPENDIUM_RULEBOOK_V1_V15.md) | Full rulebook compendium (V1–V16) |
| [RULEBOOK_READERS.md](./RULEBOOK_READERS.md) | Compendium viewers, progress tracking, story reader |
| [RULEBOOK_AGENT_CONTEXT.md](./RULEBOOK_AGENT_CONTEXT.md) | Agent-context API schema |
| [RULEBOOK_TODO_25.md](./RULEBOOK_TODO_25.md) | Rulebook maintenance checklist |
| [LAB.md](./LAB.md) | Lab handbook (APIs, catalog, deploy) |
| [MONETIZATION_PAYPAL.md](./MONETIZATION_PAYPAL.md) | PayPal / SCR monetization |

## Generator

| Doc | Purpose |
|-----|---------|
| [GENERATOR_UPGRADES_25.md](./GENERATOR_UPGRADES_25.md) | **25 prioritized upgrades** (plan + phases) |
| [GENERATOR_ENCODER_IDEAS.md](./GENERATOR_ENCODER_IDEAS.md) | Encoder pipeline backlog (E1–E15) + crypto tie-ins |
| [GENERATOR_AND_AI_OVERVIEW.md](./GENERATOR_AND_AI_OVERVIEW.md) | Pipeline, AI integration, 20 shipped fixes |
| [GENERATOR_PAGE_AND_POINTS_OVERVIEW.md](./GENERATOR_PAGE_AND_POINTS_OVERVIEW.md) | UI components, points scale |
| [plans/generator_page_roadmap.plan.md](./plans/generator_page_roadmap.plan.md) | Critical fixes + one-week roadmap |

## API references

| Doc | Purpose |
|-----|---------|
| [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) | General API index |
| [STARMAP25_API_OPENAPI.md](./STARMAP25_API_OPENAPI.md) | Star Map API |
| [TROPHIES_API_OPENAPI.md](./TROPHIES_API_OPENAPI.md) | Trophies API |
| [SOCIAL_NETWORK_API_OPENAPI.md](./SOCIAL_NETWORK_API_OPENAPI.md) | Social API |
| [PROFILE_PAGE_API_CONTRACT.md](./PROFILE_PAGE_API_CONTRACT.md) | Profile contract |

## Sub-plans (`docs/plans/`)

| Plan | Status |
|------|--------|
| [eu_crypto_casino_platform.plan.md](./plans/eu_crypto_casino_platform.plan.md) | **Done** (MVP + Discord casino fan-out) |
| [generator_page_roadmap.plan.md](./plans/generator_page_roadmap.plan.md) | **Done** (P0/P1 criticals + M8 showcase hook) |
| [masternoder_mn2_ecosystem.plan.md](./plans/masternoder_mn2_ecosystem.plan.md) | Active — Phase 14 (full pytest + finalize) |
| [master_build_orchestrator.plan.md](./plans/master_build_orchestrator.plan.md) | Active — Stage 4 finalize |
| [game_and_battle_review.plan.md](./plans/game_and_battle_review.plan.md) | Active — optional battle/Hunter follow-ups |

**Archived finished plans:** `docs/archive/plans/` (removed from production deploy). Re-audit anytime:

```bash
python scripts/plan_run_check.py
python scripts/plan_run_check.py --apply --production-prune
```

## User guides (legacy)

- [GUIDE_INTELLIGENT_POINT_SYSTEM.md](./GUIDE_INTELLIGENT_POINT_SYSTEM.md)
- [WALKTHROUGH_178_SYSTEMS.md](./WALKTHROUGH_178_SYSTEMS.md)
- [SKILLS_ABILITIES_GUIDE.md](./SKILLS_ABILITIES_GUIDE.md)
- [PROBLEM_SOLVING_TODOS.md](./PROBLEM_SOLVING_TODOS.md)

## Maintenance

Re-run obsolete-doc cleanup when session reports pile up:

```bash
python scripts/cleanup_obsolete_docs.py --dry-run
python scripts/cleanup_obsolete_docs.py
```
