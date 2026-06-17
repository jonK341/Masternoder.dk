# Game Hub Unified — 25 Ideas (Option C)



Frontpage **Game Hub** section with tabs: **Trophies · Quests · Game · Battle · Story**.  

Backend: unified quest service + `/api/game-hub/overview`.



| # | Idea | Status |

|---|------|--------|

| 1 | Frontpage tab panel (5 tabs) | ✅ Done |

| 2 | `GET /api/game-hub/overview` aggregate | ✅ Done |

| 3 | Unified quests API (trophy + platform) | ✅ Done |

| 4 | Window-based trophy quest progress (baseline per day/week) | ✅ Done |

| 5 | `POST /api/game-hub/quests/claim` + trophy alias | ✅ Done |

| 6 | MN2 on trophy quest claim | ✅ Done |

| 7 | Trophy points on quest claim | ✅ Done |

| 8 | File-backed quest state (`data/trophy_quests/`) | ✅ Done |

| 9 | Fix `/quests` page to unified schema + claim | ✅ Done |

| 10 | Trophy Quests tab claim button | ✅ Done |

| 11 | Deploy manifest `game_hub` | ✅ Done |

| 12 | Deep links to full pages per tab | ✅ Done |

| 13 | Auto-refresh hub every 60s | ✅ Done |

| 14 | Quest claimable count in hub summary | ✅ Done |

| 15 | Collector level + pending income in Trophies tab | ✅ Done |

| 16 | Wire `weekly_trophies` platform quest to unlock events | ✅ Done |

| 17 | Quest streak bonus (7-day claim streak → MN2) | ✅ Done |

| 18 | Hub notification dot when claimable > 0 | ✅ Done |

| 19 | Embed mini leaderboard in Trophies tab | ✅ Done |

| 20 | Battle tab: last 3 match results | ✅ Done |

| 21 | Story tab: read progress + continue CTA | ✅ Done |

| 22 | Game tab: Hunter level + active mission | ✅ Done |

| 23 | Merge AI daily quests (`/api/quests/daily`) into unified list | ✅ Done |

| 24 | Casino quests as optional 6th sub-tab under Quests | ✅ Done |

| 25 | Agent-tools: `game_hub overview` + `quest claim` actions | ✅ Done |



## Deploy



```bash

python scripts/deploy.py game_hub --ask-pass

```



Also restarts `uwsgi-vidgenerator` only (same as `trophies`).



## API



- `GET /api/game-hub/overview?user_id=...`

- `GET /api/game-hub/quests?user_id=...`

- `POST /api/game-hub/quests/claim` — body `{ "quest_id": "..." }`

- `GET /api/game-hub/agent-tools` — capability map (#25)

- `POST /api/game-hub/agent-action` — body `{ "action": "overview|quests|quest_claim", "approved": true }`

- `GET /api/trophies/quests` — same payload as game-hub quests (backward compatible)

- `POST /api/trophies/quests/claim` — same as game-hub claim



## Architecture (Option C)



```

index.html Game Hub

    └── game-hub-panel.js

            └── GET /api/game-hub/overview

                    ├── trophy_level_service + trophy_social (leaderboard)

                    ├── trophy_quest_service (+ user_engagement, AI, casino)

                    ├── unified_points_database + hunters_game level

                    ├── battle_db_service (recent matches)

                    └── hunters_stories.json (read progress)



quests/index.html + trophies Quests tab

    └── same trophy_quest_service

```



## #17 — claim streak



- Any successful unified claim increments consecutive-day streak in `data/trophy_quests/{user}.json`

- Day 7 (and every 7 thereafter) awards **+0.007 MN2** via `trophy_level_service._credit_mn2`

- Streak shown in Quests tab + returned as `claim_streak` on overview/quests



## #16 — weekly_trophies wiring



- `count_trophy_unlocks_this_week()` reads `user_trophy_unlocks` since Monday UTC

- `sync_weekly_trophies_quest()` sets platform quest progress from that count

- `get_quests()` syncs on every load (self-healing)

- `award_trophy()` calls `on_trophy_unlocked()` on **new** unlocks only (no duplicate pts)

- Star Map trophy awards call `sync_weekly_trophies_quest()` instead of manual increment

## Phase 2 polish (post-25)

| Item | Status |
|------|--------|
| `POST /api/game-hub/stories/read` + trophies tab hook | ✅ Done |
| `GET /api/game-hub/stories/progress` | ✅ Done |
| Agent actions `story_read`, `story_progress` | ✅ Done |
| Quest sub-tabs on `/quests/` (match frontpage) | ✅ Done |
| Unit tests `tests/unit/test_game_hub.py` | ✅ Done |
| Camgirls Phase 2 chat `POST /api/camgirls/chat` | ✅ Done |
| Phase 1c ops script + template | ✅ See [CAMGIRLS_PHASE1C.md](CAMGIRLS_PHASE1C.md) |
| MN2 v1.2.3.0 release build | ⏳ Manual — [MN2_RELEASE_BUILD.md](MN2_RELEASE_BUILD.md) |

## Discord cross-road (M8)

Game Hub rewards emit `game_mn2_reward` to the activity bus → M8 alert funnel (#53). Compendium and Game Hub are in the daily affiliate rotator (#57). Future: compendium 25/25 milestone → `platform_news` + Discord. See [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md).
