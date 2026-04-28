# Instance DB Table Inventory (Phase 3)

Source of truth DB: `sqlite:///instance/database.db`  
Generated: 2026-02-24 (updated after Phase 6)

Format: `table_name | column_count | row_count`

- `agent_ai_intelligence | 15 | 0`
- `agent_errors | 12 | 0`
- `agent_geo_refs | 6 | 0`
- `agent_missions | 16 | 28`
- `agent_personality | 14 | 0`
- `agent_quests | 17 | 0`
- `agent_skill_history | 10 | 140`
- `agent_technologies | 17 | 51`
- `agent_technology_events | 11 | 0`
- `agent_technology_improvements | 14 | 602`
- `agent_technology_metrics | 14 | 50`
- `agent_technology_relationships | 8 | 0`
- `agent_technology_usage | 14 | 0`
- `agent_use_cases | 13 | 0`
- `anomaly_detection | 7 | 0`
- `calculation_history | 12 | 0`
- `comm_psych_activity_log | 8 | 0`
- `comm_psych_theory_unlocks | 5 | 0`
- `daily_activities | 14 | 669`
- `dna_manipulation | 12 | 0`
- `error_logs | 29 | 0`
- `error_summaries | 16 | 0`
- `hunters_game_sessions | 9 | 0`
- `hunters_profiles | 6 | 0`
- `hunters_spells | 6 | 0`
- `knowledge_base | 8 | 0`
- `onboarding_progress | 11 | 19`
- `pattern_analysis | 7 | 0`
- `player_levels | 22 | 76`
- `point_aggregates | 11 | 0`
- `point_analytics | 12 | 0`
- `point_history | 8 | 0`
- `point_loss_detection | 10 | 0`
- `point_transactions | 11 | 16`
- `predictions | 8 | 0`
- `repair_log | 9 | 0`
- `rewards | 10 | 12`
- `schema_migrations | 7 | 10`
- `shop_items | 15 | 124`
- `shop_purchases | 15 | 0`
- `sqlite_sequence | 2 | 15`
- `star_map_visits | 5 | 0`
- `system_point_snapshots | 10 | 22`
- `system_usage_stats | 11 | 8`
- `user_agent_skills | 7 | 97`
- `user_inventory | 12 | 0`
- `user_profiles | 12 | 58`
- `user_rewards | 4 | 0`
- `user_scraped_info | 5 | 52`
- `video_generation_jobs | 17 | 0`
- `xp_history | 10 | 45257`

## Phase 6 note

- Drift checker reports:
  - Missing canonical tables: `0`
  - Missing canonical script ledger entries: `0`
  - Extra tables outside canonical set: `14` (kept intentionally for broader platform features)
