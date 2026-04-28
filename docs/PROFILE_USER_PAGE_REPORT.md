# Profile And User Page Report

Date: 2026-04-29

## Fixed This Pass

- Added automatic social network appearance sync: `/api/social/appearance/scan` writes detected social presence into profile preferences as `social_network_appearance`.
- Hardened dynamic profile rendering by escaping user/profile/API values before inserting them into `innerHTML` in the main profile header, identity card, activity feed, agents list, achievements, battle leaderboard, skills, lab logbook, communication psychology block, and profile hub summary.
- Added safe avatar URL handling so profile avatars only resolve to HTTP(S) or same-origin URLs, with a local fallback avatar.
- Improved account switching: `Use ID` and `Sync session` now reload the profile after updating the browser/session user ID, so the visible profile matches the selected account immediately.
- Added a Profile hub `Account` tab and support for `/profile?tab=account` plus `/profile?tab=user`.
- Added a profile setup checklist to the profile overview so missing name, avatar, bio, linked login, location, activity, progress, and agent setup are visible.
- Added `/user/` as a lightweight account-first page for identity/session sync, setup guidance, and links into the full profile.
- Added account privacy APIs and UI: profile visibility, language, notifications, featured achievement, pinned activity, featured agents, and profile theme.
- Added account data export, soft-delete, linked-provider list/unlink, and active session/device list endpoints with inline UI states on `/profile` and `/user/`.
- Added identity-model separation in `/api/user/identity`: anonymous device ID, authenticated user ID, display name, and linked providers.
- Added `docs/PROFILE_PAGE_API_CONTRACT.md` and `scripts/smoke_profile_user_flows.py` for profile/user API coverage.
- Added focused route-like profile views for `/profile?tab=account`, `points`, `shop`, `wallet`, `agents`, `activity`, and `lab`, while Overview still shows the full dashboard.
- Added password-protection status to the aggregated profile payload and setup checklist.
- Added small render helpers for account chips/statuses and optional Playwright browser smoke coverage in `scripts/browser_smoke_profile_user.py`.
- Added persistent session/device inventory in profile preferences with non-current session revoke controls.
- Added provider disconnect status metadata so the UI explains local-only disconnect until OAuth token storage exists.
- Added password set/change controls and recovery-policy messaging on both `/profile` and `/user/`.
- Added central file-backed account session registry in `data/account_sessions.json`; revoked devices are now checked before trusting server session user IDs.
- Added token-aware OAuth provider revocation path. When `SOCIAL_AUTH_STORE_TOKENS` is enabled, stored provider tokens can be revoked during unlink; otherwise the UI reports local-only disconnect.
- Added password recovery status/request/reset endpoints with email/provider recovery availability, expiring recovery tokens, and reset controls on `/profile` and `/user/`.
- Kept the existing neon/dark visual language and page structure intact while improving safety and consistency.

## Current Status

- `/profile` is the main combined profile/user page. It includes account creation/login, social login entry points, user identity/session status, unified point summary, profile header, activity, lab logbook, trophies, shop inventory, MN2 wallet, agents, battle, monetization, password protection, achievements, stats, communication psychology, game links, geo reference, and PayPal controls.
- Social appearance can now be scanned from the Social tab and is stored automatically on the profile for later display/use.
- The page relies on `/api/user/profile/<user_id>/aggregated` as its main data source, including password status, then loads secondary cards from points, shop, battle, MN2, lab, auth, and Star Map APIs.
- `/user/` now exists as the account-first entry point. It keeps identity/session sync separate from the larger progress-heavy profile page, then links users to `/profile?tab=account` for the full account controls.
- Account/privacy controls are now backed by `/api/user/account-privacy`, `/api/user/export`, `/api/user/delete`, `/api/user/linked-providers`, `/api/user/sessions`, `/api/user/sessions/revoke`, `/api/auth/password/*`, and `/api/auth/password/recovery/*`.

## Missing Parts

- Account deletion is currently a soft-delete. A true destructive delete still needs a retention policy and ledger/payment/history rules.
- Linked-provider management can revoke stored provider tokens when `SOCIAL_AUTH_STORE_TOKENS` is enabled. Existing accounts without stored tokens still fall back to local-only disconnect.
- Active session/device list is now centralized in `data/account_sessions.json` and supports non-current revocation. A database-backed session store would still be stronger for production scale.
- The page is less dense due to `/user/`, the Account tab, and focused route-like profile tabs; a full componentized route split would still be cleaner long-term.
- Many account controls now use inline statuses, but older cards still use alerts or silent fallbacks and need a broader consistency sweep.
- Loading states now show account-control sync timestamps, but the full page still lacks one consolidated last-synced state across every secondary card.
- Accessibility improved with account labels, focus-visible states, and Escape-to-close for the edit modal; a full keyboard/focus-trap pass remains.
- Security/privacy improved for the highest-risk profile render paths and account controls; remaining legacy `innerHTML` renderers still need a full audit.
- Smoke coverage now exists for account APIs and page markers, plus optional Playwright browser checks when browser tooling is installed.

## Recommended Next Steps

- Continue extracting `/profile` sections into smaller component/page files if this app later moves beyond static HTML.
- Move OAuth token/session storage from local JSON into the production database or secret store before relying on it for high-value accounts.
- Add real email delivery for recovery links by configuring SMTP or an email provider.
- Convert repeated inline HTML rendering to small reusable render helpers/components so escaping and empty/error states are consistent.
- Run browser smoke checks in deployment/CI after Playwright browser binaries are available.
