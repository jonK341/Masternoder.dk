# Documentation index

This is the index for all current MasterNoder.dk documentation. It was rebuilt on 2026-07-06 after archiving ~180 stale, point-in-time status/completion reports (see [`archive/README.md`](archive/README.md)) — everything listed below is either an active backlog, a living reference doc, or a design/ops doc still relevant to how the platform works today.  <!-- pragma: allowlist secret -->

**For the single up-to-date summary of the whole platform, start with [`../PROJECT_OVERVIEW.md`](../PROJECT_OVERVIEW.md).**

## Start here

| Doc | What it is |
|---|---|
| [ROADMAP_Q3_2026.md](ROADMAP_Q3_2026.md) | Active 3-month roadmap (Jul–Sep 2026) |
| [MN2_TODO.md](MN2_TODO.md) | Live MN2/crypto/monetization ops backlog (most frequently updated doc in the repo) |
| [CASINO_TODO.md](CASINO_TODO.md) | Live casino feature + ops backlog |
| [PLATFORM_TODO.md](PLATFORM_TODO.md) | Live cross-platform backlog (gallery, shop, generator, leaderboard) |
| [IMPLEMENTATION_TODO.md](IMPLEMENTATION_TODO.md) | Older cross-cutting backlog (social login, battle hardening, generator) — still has open items |
| [PROBLEM_SOLVING_TODOS.md](PROBLEM_SOLVING_TODOS.md) | User-facing troubleshooting checklists (points/skills) |
| [PROJECT_RETHINK.md](PROJECT_RETHINK.md) | Open strategic question: one-sentence product definition + agent-native architecture direction |
| [plans/](plans/) | The 5 active build plans, sequenced by [`plans/master_build_orchestrator.plan.md`](plans/master_build_orchestrator.plan.md) |

## Ops, deployment & infra

DEPLOYMENT.md · DEPLOYMENT_GUIDE.md · DEPLOYMENT_PLAN.md · DEPLOY_PREP.md · SERVER_QUICK_REFERENCE.md · SERVER_CLEANUP.md · GATEWAY_504_502.md · UWSGI_EXIT1_TROUBLESHOOTING.md · UWSGI_SECOND_INSTANCE.md · UWSGI_SERVER_FIX.md · TESTING_INSTRUCTIONS.md · EASY_UPDATE_AFTER_UPGRADE.md · DATABASE_HEALTH_GREEN_CHECKLIST.md · MIGRATION_STRATEGY_REUSABLE.md · SITE_STABILITY_AND_OFFLINE_FIXES.md · PORT_5000_BOTTLENECK_AND_SOLUTIONS.md · PRODUCTION_READINESS_AND_LOOSE_ENDS.md · URL_TIMING_PRODUCTION.md · PAGES_AND_FUNCTIONS_AUDIT.md · RESEARCH_AI_SYSTEMS.md · ERROR_LOGGING_SYSTEM.md <!-- pragma: allowlist secret -->

Also see [`db/`](db/) (migration/schema reference) and [`patches/`](patches/) (MN2 daemon C++ patches).

## MN2 / masternode / crypto

AGENTS_MN2.md · MN2_CONFIG_AND_PASSWORD_STEPS.md · MN2_DAEMON_MULTI_PING_UPGRADE.md · MN2_DAEMON_SETUP.md · MN2_ECOSYSTEM_REPORT.md · MN2_ENDPOINT_TESTS.md · MN2_EXPLORER_PLAN.md · MN2_INTEGRATION_GAPS.md · MN2_OPS.md · MN2_PLAN_REVIEW.md · MN2_RELEASE_BUILD.md · MN2_SHOP_AND_ADDRESSES.md · MN2_STAKING_PLAN.md · MN2_V131_BUILD_CHECKPOINT.md · MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md · MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md

## Casino

CASINO_AGENT_AI_SETUP.md · CASINO_DEPLOY_OPS.md · CASINO_EXPANSION_PLAN.md · CASINO_GLOBAL_SYNC.md · CASINO_IDEAS.md · CASINO_INTEGRATIONS_CHECKLIST.md · CASINO_MARKETING.md · CASINO_OPS_PROGRESS.md · CASINO_PLAY_STORE_TUESDAY.md · CASINO_REVENUE_REPORTS.md

## Exchange, trading & monetization

EXCHANGE_CASINO_BRIDGE.md · EXCHANGE_CROSS_VENUE_ARBITRAGE.md · EXCHANGE_RENTAL_AND_SHOP.md · EXCHANGE_TRUST_AND_LIVE_WATCH.md · LIVE_PROFIT_TRADING.md · PROFIT_CRITICAL_TOP25.md · PROFIT_DAEMON_SERVER.md · PROFIT_PATH_PROTOCOL.md · MONETIZATION_25_AI_AGENTS.md · MONETIZATION_CONTENT_CRYPTO_PLAN.md · MONETIZATION_PAYPAL.md · PAYPAL_INTEGRATION_GUIDE.md · SHOP_MONETIZATION_V92.md · REFERENCE_JOB_COGS.md · ENCODER_FREE_TIER.md · VIDEO_STORAGE_STRATEGY.md

## Generator / video / calculator

GENERATOR_AND_AI_OVERVIEW.md · GENERATOR_CACHE_FIX.md · GENERATOR_FIX_OVERVIEW.md · GENERATOR_PAGE_AND_POINTS_OVERVIEW.md · GENERATOR_REDESIGN_PLAN.md · ADVANCED_CALCULATOR_DATA_POPULATION.md · CALCULATOR_AGENT_ABILITIES.md · CALCULATOR_AGENT_INTEGRATION.md · CALCULATOR_CLICK_QUESTS.md

Also see [`plans/generator_page_roadmap.plan.md`](plans/generator_page_roadmap.plan.md).

## Game, battle, Star Map, trophies & compendium

HUNTERS_GAME_DESIGN.md · GAME_WALKTHROUGH_GUIDES.md · ARENA_INCOME_MERGE_PLAN.md · STARMAP25_AI_IMPROVEMENTS.md · STARMAP25_API_OPENAPI.md · STARMAP25_TODO_25.md · STARMAP25_UNITS_AND_INVASION_DESIGN.md · STARMAP25_UPGRADES_TODO.md · STARMAP25_UPGRADE_FINISH.md · STARMAP_25_50_PROJECTS.md · STARMAP_25_TOP10_IDEAS.md · STARMAP_25_WARHAMMER40K_RESEARCH.md · TROPHIES_API_OPENAPI.md · TROPHY_SITE_UPGRADES_25.md · COMPENDIUM_RULEBOOK_V1_V15.md · RULEBOOK_AGENT_CONTEXT.md · RULEBOOK_CANON.md · RULEBOOK_TODO_25.md · WALKTHROUGH_178_SYSTEMS.md · GUIDE_INTELLIGENT_POINT_SYSTEM.md

Also see [`plans/game_and_battle_review.plan.md`](plans/game_and_battle_review.plan.md).

## Social, Discord & community

DISCORD_INTERACTIONS.md · DISCORD_LINKED_ROLES.md · DISCORD_WEBHOOK_SETUP.md · SOCIAL_NETWORK_API_OPENAPI.md · SOCIAL_STRUCTURE.md · COMMUNICATION_PSYCHOLOGY_INTEGRATION.md · PODCAST.md

## Agents & AI

AGENTS_SKILLS_SYNC.md · AGENT_SKILLS_AND_CONCLUSIONS.md · API_MONITORING_AGENT_DOCUMENTATION.md · API_SCANNER_DOCUMENTATION.md · AUTO_FIX_SYSTEM_DOCUMENTATION.md · DAEMONS_AND_AGENTS.md · INTELLIGENCE_SOURCES.md · SKILLS_ABILITIES_GUIDE.md · TSS_AI_IMPLEMENTATION_GUIDE.md · THERE_S_AN_AI_FOR_THAT_TAAFT.md · NEW_IDEAS_NO_MARKETING.md

## Profile & user

PROFILE_PAGE_API_CONTRACT.md · PROFILE_POINTS_SYNC_PLAN.md · PROFILE_SYSTEM_IMPLEMENTATION_PLAN.md · USER_LOCATION_GPS_SYSTEM.md · PASSWORD_PROTECTION.md

## API reference

API_DOCUMENTATION.md

## Ideas, brainstorms & misc

CONSPIRACY_AND_CONTENT_CATEGORIES_POINTS.md · LINKS_BUTTONS_FUNCTIONS_BRAINSTORM.md · PERFORMANCE_IDEAS.md · PERFORMANCE_IMPROVEMENTS.md · REFLECTION_PY_AND_FILES.md · README_GUIDES.md · PLAN.md · LAB.md · LAB_V2_REQUIREMENTS.md · EXPLORER_REINSTALL_CHECKLIST.md

Also see [`brainstorms/`](brainstorms/).

## Archive

[`archive/`](archive/) holds ~180 superseded status reports, completion logs, and old plans — kept for history, not for current state. See [`archive/README.md`](archive/README.md) for the full explanation and index.
