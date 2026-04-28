# TSS AI Implementation Guide

**For:** TSS AIs, external agents, and developers integrating with MasterNoder.dk  
**Last updated:** 2026-02-25

---

## 1. Overview

This guide explains how to implement sync, points, and domain integration with the MasterNoder.dk platform. Use it when building new features, agents, or external integrations.

---

## 2. Sync Device — Core Integration

### 2.1 Unified Points Sync Device

- **Location:** `backend/services/unified_points_sync.py`
- **Singleton:** `unified_points_sync_device`

**When to use:**
- After any write that affects points, users, profiles, or domain-specific data
- When you need canonical point state for a user
- When you want to trigger a sync pass

**Key methods:**

| Method | Purpose |
|--------|---------|
| `get_canonical(user_id)` | Get canonical point state for a user |
| `register_award(user_id, point_type, amount, source, metadata)` | Award points through the sync device |
| `sync_now(user_id=None)` | Run a sync pass (optional per-user) |
| `record_domain_sync(domain, count?, extra?)` | **Call after successful write** — audits domain sync |
| `record_points_activity()` | Called automatically from `add_points` |
| `get_sync_status()` | Full sync status for dashboards |

### 2.2 Sync Domains (SYNC_DOMAINS)

Add your domain to `SYNC_DOMAINS` in `unified_points_sync.py` if it is new. Existing domains:

- `unified_points`, `users`, `profiles`
- `aggregator`, `trophies`, `achievements`, `battle`, `shop`, `quests`
- `leaderboards`, `analytics`, `compendium`, `generator`, `gallery`
- `stats`, `social`, `points`, `agent_skillsets`, `agent_knowledge`
- `game`, `paypal`, `login`, `onboarding`
- `communication_psychology`, `dna`, `game_save`, `agent_activity`
- `referral`, `notifications`, `auto_save`, `templates`

### 2.3 Implementation Pattern

```python
# After a successful write in your service/route:
try:
    from backend.services.unified_points_sync import unified_points_sync_device
    unified_points_sync_device.record_domain_sync('your_domain', count=optional_count, extra=optional_dict)
except Exception:
    pass
```

---

## 3. State Storage (Database vs JSON)

- **Primary:** State is stored in the database (`sync_state`, `sync_domain_state` tables)
- **Fallback:** JSON file at `logs/unified_points_sync/sync_state.json` when DB is unavailable
- **Audit:** All sync events are logged to `sync_audit` table
- **Health:** Success/failure counts per domain in `sync_health` table

**Migration:** Run `scripts/sync_database_migration.py` to create sync tables.

---

## 4. APIs for External Integrations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/sync/status` | GET | Full sync status (points, users, profiles, domains) |
| `/vidgenerator/api/sync/status` | GET | Same, vidgenerator path |
| `/api/sync/now` | POST | Trigger sync pass. Body: `{"user_id": "optional"}` |
| `/vidgenerator/api/sync/now` | POST | Same |

---

## 5. Points System

- **Service:** `backend/services/unified_points_database.py`
- **Method:** `add_points(user_id, point_type, amount, source, metadata)`
- **Point types:** `xp_total`, `level`, `generation_points`, `battle_points`, `game_points`, `trophy_points`, `social_points`, `quest_points`, `achievement_points`, `communication_psychology_points`, `compendium_points`, `dna_manipulation_points`, `dna_cloning_points`, `knowledge_points`, `coins`, `credits`, etc.

---

## 6. Rulebook V16 — Sync Reference

See `data/rulebook_v16_sync.json` for:
- Full list of sync domains and their sources
- Agent prompts and tech specs
- Finish lines and documentation

---

## 7. Agent Knowledge

- **GET** `/api/rulebooks/agent-knowledge` — Agent-learned technology entries
- **POST** `/api/rulebooks/agent-knowledge` — Append entry (body: `id`, `source`, `title`, `text`, `rulebook_ref`)

---

## 8. Checklist for New Features

1. [ ] Add domain to `SYNC_DOMAINS` if new
2. [ ] Call `record_domain_sync(domain)` after successful write
3. [ ] Use `add_points` for point awards (triggers `record_points_activity` automatically)
4. [ ] Update rulebook/agent knowledge if relevant
5. [ ] Test sync status widget on dashboard

---

## 9. Error Handling and Auditing

- **Sync failures** are logged to `backend/services/error_logging.py` (error_type: `sync_failure`)
- **Audit:** Every `record_domain_sync` and `record_points_activity` is logged to `sync_audit`
- **Health:** Success/failure counts in `sync_health` per domain per day
