# Social structure — players interact through the game

**Purpose:** Let players interact via **friends**, **crews**, **activity feed**, and **challenges**. Share links use **social networks** (X, LinkedIn, Facebook, Mastodon). Data: `data/social_structure.json` and `data/social_networks.json`; routes: `backend/routes/social_routes.py`.

---

## 1. Features

| Feature | Description |
|--------|-------------|
| **Friends** | Add/remove friends by `user_id`. Mutual: adding A→B also adds B→A. Max 100 per user. |
| **Activity feed** | Global feed of recent actions: Star Map 25 investigate/collect, quick battle. Optional filter: friends only. |
| **Crews** | Guild-like groups. Create a crew, join/leave. One crew per user. Max 50 members per crew. |
| **Challenges** | Send a challenge to a friend (e.g. race to 5 investigations). Only friends can be challenged. |

**Social networks (content sharing):** `data/social_networks.json` defines share targets (X, LinkedIn, Facebook, Mastodon). `GET /api/social/networks` returns them for consistent share UI. Used on Profile, Generator finish, Game Social tab, and Gallery (Share on cards and in video modal).

---

## 3. Data (`data/social_structure.json`)

- **friends** — `{ "user_id": [ "friend_id1", "friend_id2" ], ... }`
- **crews** — `[ { "id", "name", "member_ids", "created_by", "created_at" }, ... ]`
- **user_crews** — `{ "user_id": "crew_id", ... }`
- **activity_feed** — `[ { "id", "user_id", "action_type", "label", "ts", "extra" }, ... ]` (capped at 500)
- **challenges** — `[ { "id", "from_user_id", "to_user_id", "challenge_type", "target", "status", "created_at" }, ... ]`

---

## 4. API (prefix `/api/social`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/friends?user_id=` | List current user's friends (display_name, user_id). |
| POST | `/friends/add` | Body: `user_id`, `friend_id`. Add friend (mutual). |
| POST | `/friends/remove` | Body: `user_id`, `friend_id`. Remove friend (mutual). |
| GET | `/activity?user_id=&limit=30&friends_only=0` | Activity feed; `friends_only=1` restricts to friends + self. |
| POST | `/activity/push` | Body: `user_id`, `action_type`, `label`, `extra?`. Push entry (used by game actions). |
| GET | `/crews?user_id=` | List crews and current user's crew. |
| POST | `/crews/create` | Body: `user_id`, `name`. Create crew (user becomes only member). |
| POST | `/crews/join` | Body: `user_id`, `crew_id`. Join a crew. |
| POST | `/crews/leave` | Body: `user_id`. Leave current crew. |
| GET | `/challenges?user_id=` | List challenges involving user (sent or received). |
| POST | `/challenges/send` | Body: `user_id`, `to_user_id`, `challenge_type`, `target?`. Send challenge (friends only). |
| GET | `/summary?user_id=` | One-shot: friends_count, crew (id, name, member_count), pending_challenges_count. |

---

## 5. Activity hooks (where feed entries are pushed)

- **Star Map 25 investigate** — after successful investigate: `starmap25_investigate`, label e.g. "Investigated Mars".
- **Star Map 25 collect** — after collect with points > 0: `starmap25_collect`, label e.g. "Collected 42 game_points from buildup".
- **Quick battle** — after battle: `battle`, label e.g. "Quick battle: won (+10 pts)".

Other actions (build, deploy, crew create/join, challenge send) can call `push_activity()` from `social_routes` when needed.

---

## 6. Game UI

- **Game page → Social tab (👥 Social):**
  - Summary: friends count, crew name, pending challenges.
  - Add friend: input `user_id` + Add.
  - Friends list with Remove.
  - Crews list with Join / Create crew (name + Create).
  - Activity feed (last 25 items).

- **Profile:** Optional link to Game → Social tab (e.g. "Play with others") can be added in profile.

---

## 7. Display names

Display names are derived from `user_id` via a deterministic hash (same as leaderboard) so no extra profile data is required. Later you can plug in real display names from account/profile if available.

---

## 8. Optional next steps

- **Accept/decline challenges** — add `POST /challenges/accept`, `POST /challenges/decline` and track progress (e.g. race to 5 investigations).
- **Crew leaderboard** — aggregate XP or game_points by crew for a crew ranking.
- **Direct messages** — store simple DMs in `social_structure.json` or a separate store; endpoint `GET/POST /social/dms`.
- **Invite to crew** — allow crew members to invite friends by `user_id` (pending invite list).
