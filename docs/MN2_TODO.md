# MN2 TODO

## Critical

- [ ] Load-test Gate S idempotency under concurrent `add_points` for `mn2_balance`
- [ ] Treasury cold-wallet policy before 600k MN2 agent distribution goes live
- [ ] Require authenticated (non-anon) identity for all MN2 earn endpoints in production

## Upgrades

- [ ] Complete M8 Discord income streams 51–60 (role gating, promo codes, quest bot)
- [ ] Customer avatar backfill cron for existing `logs/unified_points/` users
- [ ] Health Ops Hub: surface `GET /api/mn2/health` + Discord outbox status tile
- [ ] Resync static `news/index.html` with `GET /api/news/platform?channel=*`
