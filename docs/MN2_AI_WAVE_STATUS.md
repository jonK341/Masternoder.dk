# MN2 AI / Monetization Wave Status

Source of truth for Phase 13 inventory: `GET /api/ai-intelligence/waves` (`backend/services/ai_wave_inventory_service.py`).

## Policy
- AI runs **off-request** (cron / workers / cached snapshots).
- Money moves require Gate S + deterministic validation; models flag/recommend only.

## Summary
Use the API `counts` block. Deferred waves are roadmap items, not ship blockers.

## Related
- Security sweeps: `POST /api/security/cron/sweep`
- Game earn: `GET /api/game-hub/earn/top10`, `POST /api/game-hub/earn/check-in`
- Sprint board: [MN2_TODO.md](MN2_TODO.md)
