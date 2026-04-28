# Star Map 25 — Upgrade Todo

Use this as the active upgrade checklist for progressing Star Map 25 beyond the investigation MVP.

## Now

- [x] Make buildup playable on `/starmap25/`: show pending points, placements, system levels, daily reset, build controls, deploy controls, and collect.
- [x] Add clear build/deploy validation feedback in the monitor UI: uninvestigated systems disabled, level requirements visible, not-enough-points errors surfaced.
- [x] Add placement summaries per system and planet so users can see what is generating buildup.

## Next Gameplay Upgrades

- [x] Add invasion state and `POST /api/star-map/25/invade`: investigated system + deployed unit secures a system once per user.
- [x] Store invasion blurbs per user and point, with an optional AI-generated one-liner.
- [x] Show secured/invaded systems on monitor cards and the 25-cell grid.
- [x] Show secured/invaded systems in the Game tab.
- [x] Add temporary Star Map events, such as system revolts or bonus deployment windows.
  - Fixed: events now have separate state, timing rules, reward modifiers, monitor display, and Game tab display.

## Fixed Checklist — Temporary Events

- [x] Add `data/starmap25_events.json` with active events, event type, target point/segmentum, reward modifier, start/end timestamps, and description.
- [x] Add `GET /api/star-map/25/events` to expose active and upcoming Star Map events.
- [x] Apply event modifiers to relevant actions, starting with deploy/invade bonus windows and system revolt secure bonuses.
- [x] Show active event banners on `/starmap25/` and mark affected cards/grid cells.
- [x] Show active Star Map events in the Game tab.
- [x] Log event participation for analytics when users build, deploy, collect, or invade during an event.

## Map And Monitor UX

- [x] Group cards by Segmentum: Solar, Obscurus, Tempestus, Pacificus, Ultima.
- [x] Add filters for segmentum, investigated state, level, and tags.
- [x] Add sort controls for index, name, point value, segmentum, and level.
- [x] Add expanded `lore_long` reading when content exists.
- [x] Add share progress and print-friendly views.
- [x] Add keyboard navigation for card focus and investigate/build actions.

## Data And Content

- [x] Add `tags` to `data/star_map_25.json` for fortress, forge, throne, legion homeworld, naval, xenos, and traitor modifiers.
- [x] Add coordinates to each point for deterministic 3D/4D placement.
- [x] Add extended lore and canon links per point.
- [x] Add segmentum metadata: colors, descriptions, fortress point, and completion requirements.
- [x] Add version/changelog metadata to the Star Map API.

## Economy, Trophies, And Quests

- [x] Show current `game_points` balance on `/starmap25/`.
- [x] Apply active Star Map boosters to investigation/build/deploy where intended.
- [x] Finish Star Map trophies: Terra, Segmentum Clear, Full Clear, Lore Master.
- [x] Ensure daily and weekly Star Map quests complete from investigation and buildup actions.
- [x] Deep-link monitor actions to `/shop?category=starmap25` when users need boosters or points.

## Crypto Relay

- [x] Add per-user Star Map crypto state keyed by `user_id`.
- [x] Add MN2 earning options for investigation telemetry, buildup yield, secured relays, and Segmentum routes.
- [x] Add cooldowns and claim history per earning option.
- [x] Award claimed crypto to unified `mn2_balance` with metadata.
- [x] Show crypto earning options, cooldowns, progress, and claim controls on `/starmap25/`.

## API, Analytics, And Agent Support

- [x] Add single-point and segmentum endpoints.
- [x] Add health check for Star Map data and writable state files.
- [x] Add leaderboard and analytics events for investigate, build, deploy, collect, and invade.
- [x] Add agent-safe tools for reading Star Map status and performing approved actions.
- [x] Add OpenAPI documentation for all `/api/star-map/25*` endpoints.
