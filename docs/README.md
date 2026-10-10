# Documentation map (MasterNoder.dk)

Short index of **living** docs. Prefer these over old `*_COMPLETE` / session-report dumps (most were removed 2026-09-30).

**Last refreshed:** 2026-09-30

---

## Start here

| Doc | Role |
| --- | ---- |
| [MN2_TODO.md](MN2_TODO.md) | Primary MN2 / monetization / fleet backlog + recent snapshot |
| [PLATFORM_TODO.md](PLATFORM_TODO.md) | Cross-site platform backlog (gallery, shop, themes, Play Store deferral) |
| [IMPLEMENTATION_TODO.md](IMPLEMENTATION_TODO.md) | Historical full-plan checklist (Jan 2026) — use for archaeology, not day-to-day |
| [MN2_OPS.md](MN2_OPS.md) | Production ops, deploy waterfall, fleet notes |
| [MONETIZATION_PAYPAL.md](MONETIZATION_PAYPAL.md) | PayPal / packs / subs / COGS north star |

---

## By topic

### MN2 / daemon / explorer

- [MN2_RELEASE_BUILD.md](MN2_RELEASE_BUILD.md) — release binary build
- [MN2_DAEMON_MULTI_PING_UPGRADE.md](MN2_DAEMON_MULTI_PING_UPGRADE.md) — multi-ping upgrade
- [MN2_V131_BUILD_CHECKPOINT.md](MN2_V131_BUILD_CHECKPOINT.md) — v1.3.1 build checkpoint
- [MN2_STAKING_PLAN.md](MN2_STAKING_PLAN.md) · [MN2_EXPLORER_PLAN.md](MN2_EXPLORER_PLAN.md) · [MN2_SHOP_AND_ADDRESSES.md](MN2_SHOP_AND_ADDRESSES.md)
- [SERVER_CLEANUP.md](SERVER_CLEANUP.md) · [DATABASE_HEALTH_GREEN_CHECKLIST.md](DATABASE_HEALTH_GREEN_CHECKLIST.md)
- [UWSGI_EXIT1_TROUBLESHOOTING.md](UWSGI_EXIT1_TROUBLESHOOTING.md) · [UWSGI_SECOND_INSTANCE.md](UWSGI_SECOND_INSTANCE.md)

### Monetization / shop / exchange

- [REFERENCE_JOB_COGS.md](REFERENCE_JOB_COGS.md) · [PAYPAL_INTEGRATION_GUIDE.md](PAYPAL_INTEGRATION_GUIDE.md)
- [SHOP_MONETIZATION_V92.md](SHOP_MONETIZATION_V92.md) · [SHOP_MONETIZATION_AUTOMATION_CLOSEOUT.md](SHOP_MONETIZATION_AUTOMATION_CLOSEOUT.md)
- [EXCHANGE_RENTAL_AND_SHOP.md](EXCHANGE_RENTAL_AND_SHOP.md) · [EXCHANGE_CROSS_VENUE_ARBITRAGE.md](EXCHANGE_CROSS_VENUE_ARBITRAGE.md)
- [EXCHANGE_TRUST_AND_LIVE_WATCH.md](EXCHANGE_TRUST_AND_LIVE_WATCH.md) · [LIVE_PROFIT_TRADING.md](LIVE_PROFIT_TRADING.md)
- [PROFIT_PATH_PROTOCOL.md](PROFIT_PATH_PROTOCOL.md) · [PROFIT_DAEMON_SERVER.md](PROFIT_DAEMON_SERVER.md) · [PROFIT_CRITICAL_TOP25.md](PROFIT_CRITICAL_TOP25.md)
- Machine inventory: `data/monetization_revenue_tracks.json`

### Casino / Play Store / Discord

- [CASINO_TODO.md](CASINO_TODO.md) · [CASINO_DEPLOY_OPS.md](CASINO_DEPLOY_OPS.md) · [CASINO_OPS_PROGRESS.md](CASINO_OPS_PROGRESS.md)
- [CASINO_PLAY_STORE_TUESDAY.md](CASINO_PLAY_STORE_TUESDAY.md) — Google Play account + assetlinks
- [CASINO_INTEGRATIONS_CHECKLIST.md](CASINO_INTEGRATIONS_CHECKLIST.md) · [CASINO_AGENT_AI_SETUP.md](CASINO_AGENT_AI_SETUP.md)
- [DISCORD_WEBHOOK_SETUP.md](DISCORD_WEBHOOK_SETUP.md) · [DISCORD_INTERACTIONS.md](DISCORD_INTERACTIONS.md) · [DISCORD_LINKED_ROLES.md](DISCORD_LINKED_ROLES.md)

### Product surfaces

- [PODCAST.md](PODCAST.md) · [LAB.md](LAB.md) · [LAB_V2_REQUIREMENTS.md](LAB_V2_REQUIREMENTS.md)
- [DEPLOY_CREATE_APP_RELEASE.md](DEPLOY_CREATE_APP_RELEASE.md) — Create App / Super Encoder deploy handoff
- [DAEMONS_AND_AGENTS.md](DAEMONS_AND_AGENTS.md) · [AGENTS_SKILLS_SYNC.md](AGENTS_SKILLS_SYNC.md) · [AGENTS_MN2.md](AGENTS_MN2.md)
- [PASSWORD_PROTECTION.md](PASSWORD_PROTECTION.md) · [PROFILE_PAGE_API_CONTRACT.md](PROFILE_PAGE_API_CONTRACT.md)
- [RULEBOOK_CANON.md](RULEBOOK_CANON.md) · [BUSINESS_CONTROL_PHASES.md](BUSINESS_CONTROL_PHASES.md)

### Deploy / health

- [DEPLOYMENT.md](DEPLOYMENT.md) · [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) · [DEPLOY_PREP.md](DEPLOY_PREP.md)
- [GATEWAY_504_502.md](GATEWAY_504_502.md) · [SERVER_QUICK_REFERENCE.md](SERVER_QUICK_REFERENCE.md)
- [db/migration_registry.md](db/migration_registry.md)

### Plans (longer-form; not day-to-day TODOs)

- [plans/](plans/) — ecosystem, casino platform, generator roadmap, battle review, orchestrator
- [archive/plans/](archive/plans/) — closed-out plans
- [brainstorms/](brainstorms/) — design notes

### Patches

- [patches/](patches/) — MN2 daemon / GCC compatibility patches (keep; used by build/ops)

---

## User / points guides (older, still useful)

- [GUIDE_INTELLIGENT_POINT_SYSTEM.md](GUIDE_INTELLIGENT_POINT_SYSTEM.md)
- [WALKTHROUGH_178_SYSTEMS.md](WALKTHROUGH_178_SYSTEMS.md)
- [SKILLS_ABILITIES_GUIDE.md](SKILLS_ABILITIES_GUIDE.md)
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- [PROBLEM_SOLVING_TODOS.md](PROBLEM_SOLVING_TODOS.md)
- Legacy index: [README_GUIDES.md](README_GUIDES.md) (dated; prefer this file)

---

## Doc hygiene

- **Do not** add new `*_COMPLETE_SUMMARY.md` session dumps — update [MN2_TODO.md](MN2_TODO.md) or the topic doc instead.
- Before deleting a doc, grep for references from `scripts/`, `.github/`, and `deploy.py`.
- Root README still points at some historical paths (`FINAL_STATUS.md`, etc.); treat [this map](README.md) as the current entry for `docs/`.
