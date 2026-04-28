# Profile Page API Contract

Date: 2026-04-29

This document lists the APIs the `/profile` and `/user/` account surfaces expect, the fields used by the UI, and the fallback behavior when a card cannot load.

## Core Identity

### `POST /api/user/bind-session`

Purpose: bind a browser-selected `user_id` to the server session.

Required request:

```json
{ "user_id": "default_user" }
```

Required response fields:

- `success`: boolean.
- `user_id`: string.
- `db_created`: optional boolean.

Fallback: the browser stores `game_user_id` and `user_id` locally even if the server call fails.

### `GET /api/user/identity?user_id=<id>`

Purpose: explain the server/browser account model.

Required response fields:

- `success`: boolean.
- `user_id`: resolved server user ID.
- `user_index`: stable numeric index.
- `session_bound`: whether server session is currently bound.
- `resolution_source`: `session`, `query`, `body`, `identification`, or `fallback`.
- `identity_model`: object with `anonymous_device_id`, `authenticated_user_id`, `display_name`, and `linked_providers`.
- `identifiers`: sanitized device/browser metadata.
- `progress_stores`: array of progress stores keyed by user ID.

Fallback: show an inline identity unavailable message while continuing to use local browser ID.

## Profile Data

### `GET /api/user/profile/<user_id>/aggregated`

Purpose: one-call payload for the main profile dashboard.

Required top-level fields:

- `success`: boolean.
- `profile`: object with `display_name`, `username`, `avatar_url`, `bio`, `preferences`, `onboarding_complete`, and date fields when available.
- `stats`: object with `level`, `total_points`, `generation_points`, `game_points`, `skills_count`, `achievements_count`, and optional `star_map_25`.
- `skills.skills`: array.
- `activity_feed.activities`: array.
- `my_agents.agents`: array.
- `achievements.achievements`: array.
- `trophies_list.trophies`: array.
- `geo_ref`: optional object.
- `lab_logbook`: optional object.
- `password_status`: object with `has_password`, `has_unlocked`, `can_unlock`, `unlock_rule`, `reward_on_set`, and `recovery` when the password service is available.

Fallback: keep page visible, show empty states per card, and allow account/session controls to continue working.

### `POST /api/user/profile/update`

Purpose: save profile display fields and preferences.

Required request:

```json
{
  "user_id": "default_user",
  "update_data": {
    "preferences": {
      "display_name": "Name",
      "avatar_url": "https://example.com/avatar.png",
      "bio": "Short bio"
    }
  }
}
```

Fallback: show inline modal error and keep entered values in the form.

## Account Privacy

### `GET /api/user/account-privacy?user_id=<id>`

Purpose: load account privacy and profile customization settings.

Required response fields:

- `success`: boolean.
- `privacy.profile_visibility`: `public`, `friends`, or `private`.
- `privacy.preferred_language`: short language code.
- `privacy.notifications_enabled`: boolean.
- `privacy.email_notifications`: boolean.
- `privacy.featured_achievement`: string.
- `privacy.pinned_activity`: string.
- `privacy.featured_agents`: array.
- `privacy.profile_theme`: `dark`, `neon`, `minimal`, or `system`.
- `privacy.linked_providers`: array.
- `privacy.account_deleted`: boolean.

### `POST /api/user/account-privacy`

Purpose: save privacy/customization settings. Same fields as the GET payload, plus `user_id`.

Fallback: show an inline error in `account-privacy-status` or `privacy-status`.

## Data Export And Delete

### `GET /api/user/export?user_id=<id>`

Purpose: download JSON account data.

Required response fields:

- `success`: boolean.
- `user_id`: string.
- `exported_at`: ISO timestamp.
- `profile`: object or `profile_error`.
- `settings`: object or `settings_error`.
- `account_summary`: object or `account_summary_error`.

Fallback: show inline export failure.

### `POST /api/user/delete`

Purpose: soft-delete account by hiding profile and disabling notifications.

Required request:

```json
{ "user_id": "default_user", "confirm": "DELETE" }
```

Required response fields:

- `success`: boolean.
- `deleted`: boolean.
- `mode`: `soft_delete`.

Fallback: require exact `DELETE` confirmation and show inline error.

## Providers And Sessions

### `GET /api/user/linked-providers?user_id=<id>`

Purpose: list configured social providers and providers marked as linked on the profile.

Required fields:

- `configured_providers`: array.
- `linked_providers`: array.
- `providers`: array with `id`, `configured`, `linked`, and `revocation_supported`.
- `revocation_supported`: boolean. True when `SOCIAL_AUTH_STORE_TOKENS` enables provider token storage.
- `revocation_note`: human-readable explanation for provider-token or local-only disconnect behavior.

### `POST /api/user/linked-providers`

Purpose: mark a provider linked or unlinked in profile preferences.

Required request:

```json
{ "user_id": "default_user", "provider": "github", "action": "unlink" }
```

Unlink response includes `revocation_status`, `revocation_supported`, and `revocation`. When a stored token exists, supported providers are revoked through their provider API before the local link is removed.

### `GET /api/user/sessions?user_id=<id>`

Purpose: show central active session/device history. Calling this endpoint records the current request as the latest current device in `data/account_sessions.json`.

Required fields:

- `sessions`: array with `id`, `current`, `resolution_source`, `device`, `ip_hash`, and `last_seen_at`.
- `persistent`: boolean.

Fallback: show “No session data reported.”

### `POST /api/user/sessions/revoke`

Purpose: mark a non-current persisted device/session as revoked.

Required request:

```json
{ "user_id": "default_user", "session_id": "device-abc123" }
```

Current-session revocation is rejected; users must revoke other devices from the current one. Revoked current devices are ignored by account resolution on later requests.

## Password Protection

### `GET /api/auth/password/status?user_id=<id>`

Purpose: load password setup/change status and unlock policy.

Required fields:

- `has_password`: boolean.
- `has_unlocked`: boolean.
- `can_unlock`: boolean.
- `unlock_rule`: object with `min_game_points` and `min_investigations`.
- `reward_on_set`: object with `game_points`.
- `recovery`: object with `has_email`, `email_masked`, `email_delivery_configured`, `provider`, `provider_recovery_supported`, and `token_reset_supported`.

### `POST /api/auth/password/set`

Purpose: set or change the account password after unlock requirements are met.

Required request:

```json
{ "user_id": "default_user", "password": "minimum-six-chars" }
```

### `GET /api/auth/password/recovery/status?user_id=<id>`

Purpose: report whether email/provider-backed recovery can be used.

Required fields:

- `has_email`: boolean.
- `email_masked`: masked email or null.
- `email_delivery_configured`: boolean.
- `provider`: linked provider ID or null.
- `provider_recovery_supported`: boolean.
- `token_reset_supported`: boolean.

### `POST /api/auth/password/recovery/request`

Purpose: create a short-lived password reset request when the account has a verified email or linked provider.

Required request:

```json
{ "user_id": "default_user", "email": "optional@example.com" }
```

Required response fields:

- `success`: boolean.
- `expires_at`: ISO timestamp when successful.
- `email_delivery_configured`: boolean.
- `reset_token`: present when email delivery is not configured or `PASSWORD_RECOVERY_RETURN_TOKEN` is enabled.

### `POST /api/auth/password/recovery/reset`

Purpose: reset the password with a valid recovery token.

Required request:

```json
{ "user_id": "default_user", "token": "recovery-token", "password": "minimum-six-chars" }
```

Fallback: show inline recovery errors and keep password setup/change controls available.
