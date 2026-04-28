# User location (GPS) system

Single source of truth for user GPS: latitude, longitude, geo_ref, accuracy, and source.

---

## Overview

- **Service:** `backend/services/user_location_service.py` — file-backed store at `data/user_locations.json`.
- **API:** `GET /api/user/location` and `POST /api/user/location` (user_profile blueprint). User is resolved via session, body, or query `user_id`.
- **Profile UI:** "Update location" uses browser Geolocation when available, then POSTs to the new API; fallback is manual lat/lon/geo_ref prompts. Display shows coords, optional geo_ref, and accuracy when present.

---

## Data shape

Per user in `data/user_locations.json`:

- `latitude`, `longitude` — numbers or null
- `geo_ref` — optional label (e.g. "Home", "Office")
- `accuracy` — meters (from browser Geolocation), optional
- `updated_at` — ISO timestamp
- `source` — `browser` | `manual` | `api`

---

## Compatibility

- **hunters_game:** `_get_geo_ref(user_id)` now tries DB table `agent_geo_refs` first, then `user_location_service.get_location()`. So existing geo-ref consumers (profile aggregated, game profiling) see location from either source.
- **hunters_game POST** `/api/game/hunters/geo-ref`: still accepted; writes into the new user location service and, when DB is available, into `agent_geo_refs`.
- **Profile:** Loads location via `GET /api/user/location` (fallback `GET /api/game/hunters/geo-ref`). Saves via `POST /api/user/location` with optional `accuracy` and `source: 'browser'`.

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/user/location` | Get current user's location (query or session `user_id`). |
| POST | `/api/user/location` | Update location. Body: `latitude`, `longitude`, `geo_ref`, `accuracy`, `source`. |

Response: `{ "success": true, "user_id": "...", "location": { "latitude", "longitude", "geo_ref", "accuracy", "updated_at", "source" } }`.
