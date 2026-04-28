# Social Network Status Report

Date: 2026-04-29

## Fixed This Pass

- Completed the remaining “Best Improvements To Add Next” implementation wave: richer crew leaderboard signals, cooldown-aware rewards, moderation controls, privacy controls, profile display names/avatars, agent-safe read tools, schema migration map, and API docs.
- Crew leaderboard now includes broader game signals: XP, game points, battle wins, Star Map secured totals, and a derived game score.
- Social MN2 rewards now support repeatable options with cooldown state while keeping signup as a one-time reward.
- Added moderation APIs for block, unblock, report, and per-user activity hiding.
- Added social privacy settings for profile visibility, activity visibility, and challenge permissions.
- Friend, feed, and chat payloads now use profile display names/avatar URLs when available, with deterministic names as fallback.
- Added agent-safe read-only endpoints: `/api/social/agent/status` and `/api/social/agent/recommendations`.
- Added `/api/social/schema` as the database migration-readiness map for future indexed tables.
- Added `docs/SOCIAL_NETWORK_API_OPENAPI.md`.
- Added a social appearance scanner at `/api/social/appearance/scan` that detects each user's social presence from friends, crew, challenges, referrals, chat, activity, and MN2 reward claims.
- The scanner now automatically syncs the detected appearance into profile preferences as `social_network_appearance`.
- Added a Social tab scanner panel that shows the detected tier, score, badges, key counts, and a manual rescan button.
- Started the “Best Improvements To Add Next” list with challenge lifecycle endpoints: accept, decline, cancel, complete, and progress updates.
- Added crew invite APIs so crew members can invite friends and invitees can accept or decline.
- Added a crew leaderboard ranked by social score across members, activity, chat, referrals, and completed challenges.
- Added notification counters for pending challenges, crew invites, friend count, and current crew rank.
- Expanded `/api/social/monitor` and `/social-monitor` with completed challenge totals, crew invite totals, and crew leaderboard data.
- Expanded the Game Social tab with challenge controls, crew invite controls, notification summary, and crew leaderboard.
- Added internal MN2 social rewards for signup, first friend, crew membership, chat activity, and successful referrals.
- Added social referral APIs for referral code discovery, referral link display, and signup registration.
- Added social chat APIs and connected Social tab messages into the existing chat history under the `social_room` context.
- Added login options API for surfacing GitHub, Google, and profile-session login entry points in the Social tab.
- Added `/api/social/monitor` plus `/social-monitor` to display network totals, top connectors, recent activity, chat, referrals, crews, reward claims, and MN2 claimed.
- Expanded the Game Social tab with MN2 reward cards, referral registration, login buttons, and social chat.
- Fixed Google OAuth provider configuration in `backend/services/social_auth_service.py` so it reads `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from environment variables.
- Restored the Google OAuth scope to `openid email profile`.
- Aligned the default social auth base URL with `.env.example`: `https://masternoder.dk`.
- Added Google OAuth keys to `.env.example` so future setup does not require code changes.
- Updated the Game Social tab to load share networks from `/api/social/networks` instead of hardcoding share URLs in the page script.
- Added consistent HTML escaping for Social tab names, labels, crew IDs, and generated share links.
- Added unit coverage for mutual friend creation, configured share networks, and Google OAuth provider settings.

## Current Status

- The social layer supports friends, crews, activity feed, challenges, social share targets, social auth provider discovery, referrals, internal MN2 social rewards, social chat, social appearance scanning, privacy, moderation, agent-safe reads, and migration schema guidance.
- Game page Social tab can show friend count, crew name, pending challenges, friend list, crews, activity feed, scanner results, rewards, referrals, login options, chat, and share links.
- `/social-monitor` is now the operator view for all JSON-backed social network data.
- Social data currently lives in JSON files under `data/`, which is simple and works for small usage but will need a database or locked write strategy as activity grows.
- Challenges now support accept, decline, cancel, complete, and progress workflows.
- Crews now support create, join, leave, invite, accept/decline invite, and leaderboard ranking.

## Best Improvements To Add Next

- Move social state from JSON files to the tables described by `/api/social/schema`.
- Add admin review actions for moderation reports: assign, resolve, dismiss, and audit trail.
- Add seasonal crew objectives and shared crew quests.
- Add browser-level smoke tests for the Social tab and `/social-monitor`.

## Verification Notes

- Added `tests/unit/test_social_network.py` for the fixed social behavior.
- Coverage now includes social rewards, cooldowns, referral registration, social chat, challenge lifecycle, crew invites, crew leaderboard, notification counters, privacy, moderation, agent-safe reads, schema map, social appearance profile sync, and monitor totals.
- Recommended test command: `python -m pytest tests/unit/test_social_network.py -v`.
