# Trophies API Surface

Date: 2026-06-06

All endpoints are served under both `/api/trophies/*` and the singular alias `/api/trophie/*`.
User identity is resolved server-side (session > query > identification); callers do not need
to pass `user_id` in normal use.

## Core Data

- `GET /api/trophies/list?user_id=...` — all trophies merged from the JSON source, DB, and
  legacy definitions, with the caller's unlock state.
- `GET /api/trophies/definitions` — canonical definitions from `data/trophy_definitions.json`
  plus the `sets` array. This is the single source of truth; the client map is fallback only.
- `GET /api/trophies/quests?user_id=...` — date-seeded daily and weekly quests.

## Gameplay Actions

- `POST /api/trophies/sync` — award every trophy the user has legitimately earned and is
  currently eligible for (server authoritative). Returns newly unlocked ids.
- `POST /api/trophies/claim` — `{ trophy_id }` — idempotently record an unlock and credit its
  reward. Verifies the requirement before crediting.
- `POST /api/trophies/award` — award a specific trophy (reward pulled from definitions).

## Social & Competitive

- `GET /api/trophies/leaderboard?limit=25` — users ranked by rarity-weighted trophy score.
- `GET /api/trophies/activity?user_id=...&limit=...` — recent unlocks for a user.
- `GET /api/trophies/compare?with=<other_user>` — side-by-side unlocked trophies for two users.
- `GET /api/trophies/showcase?user_id=...` — the user's pinned trophies (max 6).
- `POST /api/trophies/showcase` — `{ trophy_ids: [...] }` — set the pinned showcase.

## Agent Surface (Feature 22)

- `GET /api/trophies/agent-tools` — capability map: every UI action with method, path,
  params, and a `mutating` flag.
- `POST /api/trophies/agent-action` — `{ action, ...params }` — dispatch an action. Read
  actions (`list`, `definitions`, `quests`, `leaderboard`, `activity`, `compare`,
  `showcase_get`, `level`, `health`) run directly. Mutating actions (`sync`, `claim`, `showcase_set`,
  `level_collect`) require explicit `approved: true`, mirroring the UI's confirm step.

## Collector Levels & Income

- `GET /api/trophies/level?user_id=...` — collector level, daily/hourly income (trophy points + MN2),
  pending accrual, progress to next level, unlock MN2-by-rarity table, and the full level ladder.
- `POST /api/trophies/level/collect` — credit accrued passive trophy_points and MN2 (capped at 72h accrual).
- Trophy unlock/claim/sync also credit MN2: explicit `mn2_reward` on a definition, else rarity table
  in `data/trophy_levels.json`, scaled by collector `unlock_bonus_pct`.

## Ops & Authoring (Feature 25)

- `GET /api/trophies/health` — validates definitions (duplicate ids, missing reward/rarity,
  metric/target mismatch, invalid seasonal dates, dangling set members), checks the showcase
  directory is writable, and reports trophy DB table state. Returns `healthy: bool`.
- `POST /api/trophies/admin/upsert` — `{ trophy: { id, ... } }` — create or update one trophy
  definition in the JSON source with no redeploy, then re-validates. **Disabled by default.**
  Set `TROPHY_ADMIN_SECRET` and send it via the `X-Trophy-Admin-Token` header (or
  `?admin_token=`) to enable. Returns `403` when the secret is unset or the token mismatches.

## Notes

- Mutating agent actions reuse the same validation as the UI endpoints and require approval.
- Definitions are cached in-process and invalidated on file mtime change and on admin upsert.
- Leaderboard results are cached briefly server-side to avoid rescanning per-user point files.
