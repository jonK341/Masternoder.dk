# Star Map 25 API Surface

Date: 2026-04-29

The live OpenAPI JSON is exposed at `GET /api/star-map/25/openapi`.

## Core Data

- `GET /api/star-map/25` — full 25-point map data.
- `GET /api/star-map/25/point/{point_id}?user_id=...` — single point plus investigated, secured, level, placement, and invasion state.
- `GET /api/star-map/25/segmentums?user_id=...` — all Segmentum progress summaries.
- `GET /api/star-map/25/segmentum/{segmentum}?user_id=...` — one Segmentum with per-point state.
- `GET /api/star-map/25/status?user_id=...` — user progress, trophies, crypto, invasion, and point totals.
- `GET /api/star-map/25/levels?user_id=...` — system levels and daily reset state.

## Gameplay Actions

- `POST /api/star-map/25/investigate` — investigate a point.
- `POST /api/star-map/25/build` — place a building.
- `POST /api/star-map/25/deploy` — deploy a unit.
- `POST /api/star-map/25/collect` — collect buildup yield.
- `POST /api/star-map/25/invade` — secure a system.
- `GET /api/star-map/25/buildings` — building catalog.
- `GET /api/star-map/25/units` — unit catalog.

## Events, Crypto, Analytics

- `GET /api/star-map/25/events` — active/upcoming events.
- `GET /api/star-map/25/crypto?user_id=...` — in-game MN2 claim options.
- `POST /api/star-map/25/crypto/claim` — claim eligible in-game MN2 reward.
- `GET /api/star-map/25/analytics?user_id=...` — action/event analytics summary.
- `GET /api/star-map/25/leaderboard?limit=25` — Star Map 25 leaderboard.
- `GET /api/star-map/25/health` — data and writable-state health check.

## Agent Surface

- `GET /api/star-map/25/agent-tools` — capability map for agents.
- `POST /api/star-map/25/agent-action` — execute read actions or mutating actions with explicit `approved: true`.

Mutating agent actions use the same validation as UI endpoints and require approval in the request.
