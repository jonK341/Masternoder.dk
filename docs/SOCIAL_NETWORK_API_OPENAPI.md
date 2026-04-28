# Social Network API OpenAPI Summary

Date: 2026-04-29

Base path: `/api/social`

## Core

- `GET /summary?user_id=` — social counts, crew, notifications, referral code, and reward status.
- `GET /friends?user_id=` — friends with display name and avatar when profile data exists.
- `POST /friends/add` — mutual friend add. Respects block status.
- `POST /friends/remove` — mutual friend remove.
- `GET /activity?user_id=&limit=&friends_only=` — feed with hidden/blocked/privacy filtering.
- `POST /activity/push` — append an activity entry.

## Crews

- `GET /crews?user_id=` — crew list and membership.
- `POST /crews/create` — create a crew.
- `POST /crews/join` — join a crew.
- `POST /crews/leave` — leave a crew.
- `GET /crews/leaderboard` — ranked crews with social score, XP, game points, battle wins, and Star Map secured totals.
- `GET /crews/invites?user_id=` — sent/received crew invites.
- `POST /crews/invite` — invite a friend to current crew.
- `POST /crews/invites/respond` — accept or decline a crew invite.

## Challenges

- `GET /challenges?user_id=` — sent/received challenges.
- `POST /challenges/send` — send challenge, respecting block and challenge privacy settings.
- `POST /challenges/{challenge_id}/accept`
- `POST /challenges/{challenge_id}/decline`
- `POST /challenges/{challenge_id}/cancel`
- `POST /challenges/{challenge_id}/complete`
- `POST /challenges/progress` — update participant progress and auto-complete at target.

## Rewards And Referrals

- `GET /rewards/status?user_id=` — MN2 social reward options with cooldown state.
- `POST /rewards/claim` — claim unlocked reward. Repeatable rewards enforce cooldown.
- `GET /referrals?user_id=` — referral code/link and signup list.
- `POST /referrals/register` — register a referred signup.

## Login, Chat, Appearance

- `GET /login-options` — GitHub, Google, and profile-session login entries.
- `GET /chat/messages?limit=` — social chat room messages.
- `POST /chat/send` — send social chat message and mirror to existing chat history.
- `GET|POST /appearance/scan` — detect social appearance and optionally sync into profile preferences.

## Privacy And Moderation

- `GET|POST /privacy` — profile visibility, activity visibility, challenge permissions.
- `POST /moderation/block` — block user and remove mutual friendship.
- `POST /moderation/unblock` — unblock user.
- `POST /moderation/report` — report user or activity.
- `POST /activity/hide` — hide an activity entry for the current user.

## Agent-Safe And Ops

- `GET /agent/status?user_id=` — read-only social status and appearance summary.
- `GET /agent/recommendations?user_id=` — read-only next-action recommendations.
- `GET /monitor` — operator snapshot for social data.
- `GET /schema` — migration-readiness table/index map for moving JSON state to DB.
- `GET /networks` — external share network configuration.
