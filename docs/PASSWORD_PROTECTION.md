# Password protection (reward for completing and earning points)

Users can protect their account with an **encrypted (hashed) password** that is unlocked as a **reward** for completing activities and earning points.

## Unlock rule

- **Unlock condition:** Earn **50 game_points** OR complete **1 Star Map 25 investigation**.
- Configurable in `data/user_password_protection.json` under `unlock_rule`:
  - `min_game_points`: minimum game_points to unlock (default 50).
  - `min_investigations`: minimum number of Star Map points investigated (default 1).

## Reward for setting a password

When a user sets a password for the first time, they receive a one-time **game_points** reward (default **+10**), defined in `reward_on_set` in `data/user_password_protection.json`.

## Storage and security

- Passwords are **hashed** with PBKDF2-SHA256 (Werkzeug) and stored in `data/user_password_protection.json`.
- Only hashes are stored; plaintext passwords are never persisted.
- File contains: `users[user_id]` with `password_hash`, `unlocked_at`, `set_at`, and optional `reward_given`.

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/password/status` | GET | `?user_id=` — Returns `has_unlocked`, `has_password`, `can_unlock`, `unlock_rule`, `reward_on_set`. |
| `/api/auth/password/unlock` | POST | `{ "user_id" }` — Marks protection as unlocked if the user meets the rule. |
| `/api/auth/password/set` | POST | `{ "user_id", "password" }` — Sets or changes password; auto-unlocks if rule met; awards reward on first set. |
| `/api/auth/password/verify` | POST | `{ "user_id", "password" }` — Verifies password for sensitive actions. |

API routes are under `/api/auth/password/...`.

## UI

- **Profile** (`/profile`): Sidebar card **Password protection** shows status, unlock requirement, and Set password / Check unlock actions.
- Use **Verify** (via `/api/auth/password/verify`) before sensitive operations (e.g. delete account, change email) if you add those flows.

## Files

- `data/user_password_protection.json` — Config and user hashes.
- `backend/services/password_protection_service.py` — Unlock check, hash, set, verify.
- `backend/routes/password_protection_routes.py` — Flask blueprint for the API.
