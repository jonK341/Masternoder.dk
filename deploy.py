#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Deploy — uploads to the server over SSH (SFTP).

By default this script also stops/starts uwsgi and python-proxy (full restart).

Upload without touching services:

  python deploy.py --upload-only
  python deploy.py --no-restart

After deploy, run verification locally (same machine as this script):

  python scripts/post_deploy_verify.py
  python scripts/post_deploy_verify.py --list   # manual checklist only

SSH password: set DEPLOY_PASS, or run from an interactive terminal to be prompted
twice (enter + confirm); see deploy_ssh_env.require_deploy_pass.

Automation: set environment variable DEPLOY_POST_VERIFY=1 before running deploy.py
to run post_deploy_verify.py automatically after a successful SSH deploy (full-line
smoke against POST_DEPLOY_BASE_URL + shop unit tests). Requires network access to
the deployed origin.
"""
import paramiko
import os
import subprocess
import sys
import time
from datetime import datetime

from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

SERVER_HOST = deploy_host()
SERVER_USER = deploy_user()
SERVER_PASS = require_deploy_pass()

# Files to deploy - Critical files from FINAL_COMPREHENSIVE_SUMMARY.md
# Env: .env (server runtime secrets) and .env.example (template). Keep local .env in sync with production when deploying.
FILES_TO_DEPLOY = [
    ".env",
    ".env.example",
    # uWSGI (must be Unix LF; CRLF in uwsgi_common.ini breaks Linux)
    "uwsgi.ini",
    "uwsgi_common.ini",
    "uwsgi_5001.ini",
    "scripts/verify_server_env_db.sh",
    "scripts/uwsgi_diagnose_server.sh",
    "scripts/smoke_db_health_flows.sh",
    "scripts/smoke_pages_game_battle.py",
    # Core Flask app package (CRITICAL - must be deployed)
    "wsgi.py",
    "src/app/__init__.py",  # Main Flask app factory with static/page route registration
    "src/db/__init__.py",
    "src/db/models.py",
    "src/db/models_error_logging.py",
    
    # Core routes from comprehensive summary
    "backend/routes/trophie_routes.py",  # Trophy routes
    "backend/routes/leaderboard_unified_routes.py",  # Unified leaderboard routes (FIXED: import issues, added stats route, removed problematic imports)
    "backend/routes/quick_battle_routes.py",  # Enhanced quick battle routes with action tracking
    "backend/services/quick_battle_system.py",  # Enhanced with action counting
    "backend/services/178_systems_leaderboard.py",  # 178 systems leaderboard service (FIXED: field name mapping for subsystems)
    "backend/register_blueprints.py",  # Blueprint registration with trophie, leaderboard, shop-v3 fixes
    # API route fixes for unified dashboard
    "backend/routes/unified_dashboard_routes.py",  # Fixed unified dashboard routes with error handling
    "backend/routes/monetization_top50_routes.py",  # Fixed monetization routes (top50, cash, knowledge)
    "backend/routes/agent_routes.py",  # Fixed agent get-all route
    "backend/routes/unified_points.py",  # Fixed points history analytics route
    "backend/routes/point_analytics_routes.py",  # Fixed points statistics route
    "backend/routes/point_calculator_routes.py",  # Points calculator routes (predict endpoint)
    "backend/routes/tech_tree_routes.py",  # Tech tree routes
    
    # Frontend fixes
    "vidgenerator/leaderboards/index.html",  # Fixed API endpoint URLs
    "vidgenerator/python_proxy_server.py",  # python-proxy.service entrypoint
    "vidgenerator/service-worker.js",  # Reduced verbose logging
    
    # Static files for leaderboards and unified dashboard
    "vidgenerator/static/css/dashboard.css",
    "vidgenerator/static/css/image-support.css",
    "vidgenerator/static/css/template-effects.css",
    "vidgenerator/static/css/agent-skill-sets.css",
    "vidgenerator/static/css/modern-design-system.css",
    "vidgenerator/static/css/navigation-toolbar.css",
    "vidgenerator/static/js/image-support.js",
    "vidgenerator/static/js/template-effects.js",
    "vidgenerator/static/js/template-engine-core.js",
    "vidgenerator/static/js/template-services.js",
    "vidgenerator/static/js/agent-skill-sets.js",
    "vidgenerator/static/js/stats-achievements-tracker.js",
    "vidgenerator/static/js/navigation-toolbar.js",
    "vidgenerator/static/js/comprehensive-auto-save.js",
    "vidgenerator/static/js/enhanced-frontpage-stats.js",
    "vidgenerator/static/js/top50-monetization-frame.js",
    "vidgenerator/static/js/energy-regeneration-timers.js",
    # Unified dashboard page
    "vidgenerator/unified_dashboard/index.html",
    
    # Existing critical files
    "backend/routes/battle.py",  # Fixed 500 errors + added 22 missing endpoints
    "backend/routes/game.py",  # Fixed stats endpoint
    "backend/services/unified_points_database.py",  # Syntax error fix
    "vidgenerator/battle/index.html",  # Updated quick battle frontend integration + 6 new tabs
    "vidgenerator/index.html",
    "backend/routes/stats_summary.py",
    "backend/routes/all_page_routes.py",
    "vidgenerator/static/js/comprehensive-api-integration.js",
    "vidgenerator/static/js/all-api-integration.js",
    # Critical missing services and routes
    # Added automatically - 164 files
    "backend/routes/activity_points_routes.py",
    "backend/routes/advanced_battle_tech_routes.py",
    "backend/routes/advanced_calculator_routes.py",
    "backend/routes/agent_battle_skills_routes.py",
    "backend/routes/agent_enhanced_skills_routes.py",
    "backend/routes/agent_listeners_handlers_routes.py",
    "backend/routes/agent_skills_payment_routes.py",
    "backend/routes/agent_task_force_routes.py",
    "backend/routes/agent_team_roles_routes.py",
    "backend/routes/all_api_routes_registry.py",
    "backend/routes/analytics.py",
    "backend/routes/analytics_routes.py",
    "backend/routes/api_debugger.py",
    "backend/routes/atomic_calculator_routes.py",
    "backend/routes/battle_arena_gear_routes.py",
    "backend/routes/battle_hunt_video.py",
    "backend/routes/battle_intelligence_routes.py",
    "backend/routes/battle_replay_routes.py",
    "backend/routes/battle_stats_endpoints.py",
    "backend/routes/battle_tech_tree_routes.py",
    "backend/routes/battle_v3_routes.py",
    "backend/routes/battlegrounds_page.py",
    "backend/routes/calculator_automation_routes.py",
    "backend/routes/click_game_routes.py",
    "backend/routes/competitive_battle_routes.py",
    "backend/routes/complete_point_equation_routes.py",
    "backend/routes/comprehensive_points_display_routes.py",
    "backend/routes/danish_divine_tech_tree.py",
    "backend/routes/dashboard_page_routes.py",
    "backend/routes/debugger_dashboard.py",
    "backend/routes/energy_agent_routes.py",
    "backend/routes/enhanced_agent_routes.py",
    "backend/routes/enhanced_game_mechanics_routes.py",
    "backend/routes/enhanced_metal_systems.py",
    "backend/routes/enhanced_systems_routes.py",
    "backend/routes/game_agent_routes.py",
    "backend/routes/game_stats_save_routes.py",
    "backend/routes/guild_vs_clan_battlegrounds.py",
    "backend/routes/hunters_game.py",
    "backend/routes/intelligent_points_routes.py",
    "backend/routes/mind_energy_routes.py",
    "backend/routes/mission_controller_routes.py",
    "backend/routes/monetization_routes.py",
    "backend/routes/new_systems_routes.py",
    "backend/routes/ofc_api_routes.py",
    "backend/routes/player_profiler.py",
    "backend/routes/point_connection_routes.py",
    "backend/routes/point_control_board_routes.py",
    "backend/routes/point_generation_routes.py",
    "backend/routes/point_system_repair_routes.py",
    "backend/routes/point_testing_routes.py",
    "backend/routes/profile.py",
    "backend/routes/profile_enhanced_routes.py",
    "backend/routes/progress_rewards_routes.py",
    "backend/routes/rewards_routes_v2.py",
    "backend/routes/shop_v2_enhanced_routes.py",
    "backend/routes/shop_v2_routes.py",
    "backend/routes/shop_v3_routes.py",
    "backend/routes/space_time_battlegrounds.py",
    "backend/routes/theme_points.py",
    "backend/routes/theme_points_page.py",
    "backend/routes/time_disorder_battle_routes.py",
    "backend/routes/trophy_hunter_enhanced.py",
    "backend/routes/ultra_resource_controller_routes.py",
    "backend/routes/unified_game_mechanics_routes.py",
    "backend/routes/unified_generator_battle_routes.py",
    "backend/routes/unified_point_connector_routes.py",
    "backend/routes/unified_points_reconstructed.py",
    "backend/routes/v3_monetization_routes.py",
    "backend/routes/victory_tech_tree.py",
    "backend/routes/video_generation_calculator_routes.py",
    "backend/services/activity_points_system.py",
    "backend/services/advanced_battle_tech.py",
    "backend/services/advanced_intelligent_calculator.py",
    "backend/services/agent_battle_skills.py",
    "backend/services/agent_enhanced_skills_system.py",
    "backend/services/agent_listeners_handlers_system.py",
    "backend/services/agent_manager.py",
    "backend/services/agent_skills_payment_system.py",
    "backend/services/agent_system.py",
    "backend/services/agent_task_force.py",
    "backend/services/agent_team_roles_system.py",
    "backend/services/ai_agent_dashboard_system.py",
    "backend/services/analytics_service.py",
    "backend/services/atomic_calculator_hell_money.py",
    "backend/services/battle_arena_agents.py",
    "backend/services/battle_arena_error_handlers.py",
    "backend/services/battle_arena_event_handlers.py",
    "backend/services/battle_arena_gear_system.py",
    "backend/services/battle_extensions.py",
    "backend/services/battle_hunt_video_integration.py",
    "backend/services/battle_intelligence.py",
    "backend/services/battle_intelligence_system.py",
    "backend/services/battle_replay_system.py",
    "backend/services/battle_stats_service.py",
    "backend/services/battle_system.py",
    "backend/services/battle_system_enhanced.py",
    "backend/services/battle_techno_tunnel_magi.py",
    "backend/services/battle_v3_ultimate.py",
    "backend/services/calculator_automation.py",
    "backend/services/chat_points.py",
    "backend/services/competitive_battle_system.py",
    "backend/services/complete_point_equation.py",
    "backend/services/database_redesign.py",
    "backend/services/encrypted_json_storage.py",
    "backend/services/energy_generation_system.py",
    "backend/services/enhanced_database_content.py",
    "backend/services/enhanced_game_agent.py",
    "backend/services/enhanced_game_mechanics.py",
    "backend/services/enhanced_leaderboard_system.py",
    "backend/services/enhanced_shop_system.py",
    "backend/services/enhanced_tech_tree_with_quests.py",
    "backend/services/enhanced_user_profile_json.py",
    "backend/services/fantasy_battle_intelligence.py",
    "backend/services/fantasy_leaderboard_rulebook.py",
    "backend/services/game_achievements.py",
    "backend/services/game_shop.py",
    "backend/services/insane_battle_system.py",
    "backend/services/leaderboard_cache.py",
    "backend/services/mind_energy_system.py",
    "backend/services/mission_controller_operator.py",
    "backend/services/monetization_cash_generator.py",
    "backend/services/monetization_system.py",
    "backend/services/player_profiler.py",
    "backend/services/point_analytics_dashboard.py",
    "backend/services/point_calculator_178_systems.py",
    "backend/services/point_calculator_hardcoded.py",
    "backend/services/point_calculator_integration.py",
    "backend/services/point_connection_system.py",
    "backend/services/point_generation_activities.py",
    "backend/services/point_history_tracking.py",
    "backend/services/point_repair_restoration_system.py",
    "backend/services/point_system_control_board.py",
    "backend/services/profile_service.py",
    "backend/services/rewards_system.py",
    "backend/services/rewards_system_v2.py",
    "backend/services/scaling_calculator_distributed.py",
    "backend/services/shop_point_counter.py",
    "backend/services/shop_v2_enhanced.py",
    "backend/services/shop_v2_system.py",
    "backend/services/shop_v3_ultimate.py",
    "backend/services/skill_reward_system.py",
    "backend/services/social_points_system.py",
    "backend/services/space_time_battlegrounds.py",
    "backend/services/tech_tree_galactic_upgrade.py",
    "backend/services/tech_tree_knowledge.py",
    "backend/services/tech_tree_system.py",
    "backend/services/technology_intelligence_battle.py",
    "backend/services/theme_points_system.py",
    "backend/services/trophy_system.py",
    "backend/services/trophy_trading_system.py",
    "backend/services/ultra_resource_controller.py",
    "backend/services/unified_game_mechanics_constructor.py",
    "backend/services/unified_generator_battle_integration.py",
    "backend/services/unified_point_connector.py",
    "backend/services/unified_point_counter.py",
    "backend/services/unified_point_matrix.py",
    "backend/services/unified_point_system_json_storage.py",
    "backend/services/unified_point_system_reconstructed.py",
    "backend/services/v3_monetization_integration.py",
    "backend/services/victory_trophy_generator.py",
    "backend/services/video_generation_rewards.py",
    "backend/services/visual_game_engine.py",
    "backend/services/visual_game_experience.py",
    # COGS / monetization investigation (A+): LLM usage aggregation + metering stats
    "backend/services/cogs_metering_service.py",
    "backend/services/video_ai_bridge.py",
    "backend/services/llm_service.py",
    "backend/services/video_generator_service.py",
    "backend/routes/cogs_routes.py",
    "backend/services/monetization_config_service.py",
    "backend/services/monetization_ledger_service.py",
    "backend/services/monetization_tier_service.py",
    "backend/services/paypal_service.py",
    "backend/services/paypal_webhook_service.py",
    "backend/services/monetization_subscription_service.py",
    "backend/services/monetization_org_pool_service.py",
    "backend/services/monetization_allowance_service.py",
    "backend/services/monetization_overage_service.py",
    "backend/services/monetization_email_service.py",
    "backend/services/shop_checkout_promo_service.py",
    "backend/services/monetization_priority_service.py",
    "backend/services/camgirls_paypal_service.py",
    "backend/services/scr_checkout_service.py",
    "backend/services/generator_premium_checkout_service.py",
    "backend/services/battle_pass_service.py",
    "backend/services/generator_api_key_service.py",
    "backend/routes/monetization_expansion_routes.py",
    "backend/routes/shop_routes.py",
    "backend/services/shop_api_line_checks.py",
    # MN2 + unified points (avoid partial deploy; balance/wallet-activity depend on these)
    "backend/services/shop_db_service.py",
    "backend/routes/mn2_routes.py",
    "backend/services/mn2_rpc_client.py",
    "backend/services/mn2_chainz.py",
    "backend/services/mn2_ledger.py",
    "backend/services/mn2_wallet_service.py",
    "backend/services/mn2_deposit_scanner.py",
    "backend/services/mn2_order_payment_service.py",
    "backend/services/mn2_verification.py",
    "backend/services/shop_mn2_purchase_core.py",
    "backend/routes/agent_shop_crypto_routes.py",
    "data/agent_crypto_wallet_agents.json",
    "scripts/agent_mn2_shop_demo.py",
    "scripts/mn2_daemon_health.sh",
    "scripts/run_masternoder2d.sh",
    # MN2 staking system (browser rig + custodial pool): services, routes, config, ops script,
    # frontend. register_blueprints.py (above) registers these; without the route/service files
    # the staking/on-ramp/P2P/agent endpoints 404. Cron (hourly accrual/reconcile/run-all) installs
    # via `python scripts/deploy.py mn2_env`. Runtime state files (stakes/ledger/reserve/rewards/
    # orders/personas) are intentionally NOT deployed so live server state is never clobbered.
    "backend/services/mn2_staking_service.py",
    "backend/services/mn2_staking_reconcile_service.py",
    "backend/services/mn2_staking_agents_service.py",
    "backend/services/mn2_onramp_service.py",
    "backend/services/mn2_p2p_service.py",
    "backend/routes/mn2_staking_routes.py",
    "backend/routes/mn2_onramp_routes.py",
    "backend/routes/mn2_p2p_routes.py",
    "backend/routes/agent_staking_routes.py",
    "data/mn2_staking_config.json",
    "data/mn2_staking_terms.json",
    "scripts/mn2_reconcile.py",
    "staking-monitor/index.html",
    "static/js/mn2-staking.js",
    "static/js/mn2-staking-worker.js",
    "static/js/mn2-staking-monitor.js",
    "static/js/mn2-onramp.js",
    "static/js/mn2-p2p.js",
    # MN2 ecosystem buildout (site UI, market, security, callbacks, casino/aggregator)
    "data/mn2_config.json",
    "backend/routes/chat_routes.py",
    "backend/routes/gallery_routes.py",
    "backend/routes/quest_routes.py",
    "backend/routes/activity_stream_routes.py",
    "backend/routes/casino_routes.py",
    "backend/services/aggregator_mn2_service.py",
    "backend/services/generator_mn2_service.py",
    "backend/services/activity_feed_service.py",
    "backend/services/mn2_callback_auth.py",
    "backend/services/mn2_withdrawal_security.py",
    "backend/services/casino_service.py",
    "backend/services/casino_ledger.py",
    "backend/services/casino_rng.py",
    "backend/services/casino_jackpot.py",
    "backend/services/casino_tournaments.py",
    "backend/services/casino_responsible_gaming.py",
    "backend/services/casino_trophy_rake_rebate.py",
    "backend/services/engines/__init__.py",
    "backend/services/engines/crash.py",
    "backend/services/engines/hilo.py",
    "backend/services/engines/keno.py",
    "backend/services/engines/mines.py",
    "backend/services/engines/plinko.py",
    "backend/services/engines/roulette.py",
    "backend/services/engines/wheel.py",
    "market/index.html",
    "casino/index.html",
    "static/css/mn2-page-strip.css",
    "static/css/casino.css",
    "static/js/mn2-site-bridge.js",
    "static/js/mn2-page-strip-init.js",
    "static/js/mn2-global-bar.js",
    "static/js/mn2-activity-stream.js",
    "static/js/mn2-withdrawal-security.js",
    "static/js/chat-mn2-tips.js",
    "static/js/gallery-mn2-paywall.js",
    "static/js/battlegrounds-mn2.js",
    "static/js/social-mn2-rewards.js",
    "static/js/aggregator-mn2-crypto.js",
    "static/js/casino.js",
    "aggregator/index.html",
    "battlegrounds/index.html",
    "chat/index.html",
    "gallery/index.html",
    "generator/index.html",
    "quests/index.html",
    "social/index.html",
    "monetization/index.html",
    "metal/index.html",
    "theme-points/index.html",
    "champions-league/index.html",
    "editor/index.html",
    "milkyway/index.html",
    "backend/routes/paypal_routes.py",
    "backend/routes/missing_endpoints_routes.py",
    "data/monetization_config.json",
    "data/shop_v4_api_line_checks.json",
    # Shop v5.0 marketplace / Auction House
    "backend/services/shop_auction_service.py",
    "shop/index.html",
    "scripts/cogs_metering_report.py",
    "scripts/scr_usage_export.py",
    "docs/MONETIZATION_PAYPAL.md",
    "docs/MONETIZATION_INVESTIGATION_CLOSEOUT.md",
    "docs/REFERENCE_JOB_COGS.md",
    # Unified profile / points / shop consolidation — root HTML + API (see docs/RULEBOOK_CANON.md)
    "battle/index.html",
    "game/index.html",
    "profile/index.html",
    "user/index.html",
    # Profile/user account hardening: central sessions, OAuth unlink revocation, password recovery.
    "backend/routes/user_account_routes.py",
    "backend/routes/user_profile_routes.py",
    "backend/routes/password_protection_routes.py",
    "backend/routes/social_auth_routes.py",
    "backend/services/account_resolution_service.py",
    "backend/services/account_session_service.py",
    "backend/services/password_protection_service.py",
    "scripts/smoke_profile_user_flows.py",
    "scripts/browser_smoke_profile_user.py",
    "scripts/service_check_all_components.py",
    "docs/PROFILE_PAGE_API_CONTRACT.md",
    "lab/index.html",
    "debugger/index.html",
    "backend/templates/debugger/index.html",
    # Root frontpage v2.0 upgrade: hero, upgrade panels, opt-in sound console.
    "index.html",
    "service-worker.js",
    "static/css/navigation-toolbar.css",
    "static/css/frontpage-home.css",
    "static/js/frontpage-home.js",
    "static/js/service-worker-gatherer.js",
    "static/js/hypnotic-point-counters.js",
    "static/js/unified-point-counters.js",
    "static/js/navigation-toolbar.js",
    "static/js/navigation.js",
    "static/js/enhanced-game-mechanics.js",
    "static/js/quick-battle-frontend.js",
    # Star Map 25 — gameplay/economy/crypto relay monitor + state/data files.
    "starmap25/index.html",
    "backend/routes/star_map_routes.py",
    "backend/services/user_engagement.py",
    "data/star_map_25.json",
    "data/star_map_25_investigations.json",
    "data/starmap25_buildings.json",
    "data/starmap25_units.json",
    "data/starmap25_buildup.json",
    "data/starmap25_invasions.json",
    "data/starmap25_events.json",
    "data/starmap25_trophies.json",
    "data/starmap25_crypto.json",
    "data/starmap25_system_levels.json",
    "data/starmap25_walkthrough.json",
    "data/starmap25_ai_proof_docs.json",
    "docs/STARMAP25_UPGRADES_TODO.md",
    "docs/STARMAP25_API_OPENAPI.md",
    "backend/routes/user_profile_routes.py",
    "backend/routes/health_routes.py",
    "backend/routes/battle_routes.py",
    "backend/services/battle_db_service.py",
    "backend/services/battle_social_store.py",
    "scripts/battle_migration.py",
    "data/battle_minimal_content.json",
    "data/battle_social_state.json",
    "data/battle_v2_state.json",
    "backend/routes/lab_routes.py",  # Lab workbench: research log/share-card/deep scan/co-tech lifecycle APIs
    "backend/routes/api_monitor_routes.py",  # /api/ dashboard; lab endpoint fallbacks when url_map empty
    "backend/routes/error_handler_status_routes.py",
    "backend/routes/debugger_agent_tasks_routes.py",
    "backend/routes/points_routes.py",
    "backend/services/unified_points_trigger_integration.py",
    "vidgenerator/src/services/point_calculator.py",
    # Social network system — rewards, referrals, chat, appearance scanner, moderation/privacy, monitor, agent-safe reads.
    "backend/routes/social_routes.py",
    "backend/services/social_auth_service.py",
    "data/social_networks.json",
    "social-monitor/index.html",
    "docs/SOCIAL_NETWORK_STATUS_REPORT.md",
    "docs/SOCIAL_NETWORK_API_OPENAPI.md",
    "tests/unit/test_social_network.py",
    "docs/PROFILE_USER_PAGE_REPORT.md",
    "docs/RULEBOOK_CANON.md",
    "docs/LAB.md",
    "docs/LAB_V2_REQUIREMENTS.md",
    "docs/RULEBOOK_AGENT_CONTEXT.md",
    "docs/RULEBOOK_TODO_25.md",
    "docs/GAMING_SITE_STATUS_REPORT.md",
    "docs/brainstorms/battle-v2-requirements.md",
    # Rulebook API: blueprint + full V1–V16 JSON (GET /api/rulebooks/*, agent-context; V9 includes lab_research)
    "backend/routes/rulebook_routes.py",
    "data/rulebook_index_v15.json",
    "data/rulebook_v1_core.json",
    "data/hunters_rulebook_v2.json",
    "data/communication_psychology_theories.json",
    "data/rulebook_v3_2_systemic_protocols.json",
    "data/rulebook_v4_star_map.json",
    "data/rulebook_v5_effect_clusters.json",
    "data/rulebook_v6_electric_magnet.json",
    "data/rulebook_v7_unified_points.json",
    "data/rulebook_v8_agents.json",
    "data/rulebook_v9_shop.json",
    "data/rulebook_v10_battle.json",
    "data/rulebook_v11_dna.json",
    "data/rulebook_v12_generator.json",
    "data/rulebook_v13_geo_session.json",
    "data/rulebook_v14_analytics.json",
    "data/rulebook_v16_sync.json",
    "data/rulebook_lab_v2.json",
    # Aggregator hub — HTML, layout metrics, monitor game, engagement API, ideas JSON, intelligence widget
    "aggregator/index.html",
    "static/css/page-layout-metrics.css",
    "static/css/page-layout-metrics-debugger.css",
    "static/css/aggregator-monitor.css",
    "static/css/intelligence-widget.css",
    "static/js/aggregator-monitor-game.js",
    "static/js/aggregator-engagement.js",
    "static/js/aggregator-ideas.js",
    "static/js/game-battle-bridge.js",
    "static/js/intelligence-widget.js",
    "static/data/aggregator_ideas_top15.json",
    "data/lab_progression_catalog.json",  # Chapters II–IV research catalog
    "backend/routes/intelligence_aggregator_routes.py",
    "static/css/story-monitor-5d.css",
    "static/js/story-monitor-5d.js",
    "static/css/cooldown-timer.css",
    "static/js/cooldown-timer.js",
]

# Files that used to exist on the server but now shadow the current package layout.
# If /var/www/html/src/app.py remains, `from src.app import create_app` can import
# that stale module instead of the real src/app/__init__.py package.
STALE_REMOTE_FILES = [
    "src/app.py",
    "src/app.pyc",
    "src/__pycache__/app*.pyc",
    "vidgenerator/src/app.py",
    "vidgenerator/src/app.pyc",
    "vidgenerator/src/__pycache__/app*.pyc",
]

def deploy(upload_only=False):
    """Deploy files over SFTP. When upload_only is True, skip cache clear and service restarts."""
    print("="*70)
    if upload_only:
        print("AUTO DEPLOY - UPLOAD ONLY (no restart)")
    else:
        print("AUTO DEPLOY - FLASK RESTART")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if upload_only:
        print()
        print("  Mode: files are written under /var/www/html; uwsgi / python-proxy are NOT restarted.")
        print("  Restart manually on the server when you want new Python code loaded.")
    print()
    
    # Run cache buster before deployment
    try:
        print("[0/5] Running cache buster...")
        import subprocess
        result = subprocess.run(['python', 'scripts/cache_buster.py'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("  [OK] Cache version updated")
            print(f"  {result.stdout.strip()}")
        else:
            print(f"  [WARN] Cache buster warning: {result.stderr}")
        print()
    except Exception as e:
        print(f"  [WARN] Cache buster failed: {e}")
    print()
    
    try:
        # Connect
        print("[1/5] Connecting...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()

        # Remove stale server files that would shadow current package paths
        print("[1b/5] Removing stale server files...")
        for stale_file in STALE_REMOTE_FILES:
            remote_stale = f"/var/www/html/{stale_file}"
            ssh.exec_command(f"rm -f {remote_stale} 2>&1 || true", timeout=5)
            print(f"  [OK] removed stale {stale_file} if present")
        print()
        
        # Deploy files
        print("[2/5] Deploying files...")
        sftp = ssh.open_sftp()
        deployed = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue
                
            try:
                remote_file = f"/var/www/html/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=5)
                
                with open(local_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                with sftp.file(remote_file, 'w') as rf:
                    rf.write(content)
                
                print(f"  [OK] {local_file}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local_file}: {e}")
        
        sftp.close()
        print(f"  [SUMMARY] {deployed} files deployed")
        print()

        print("[2b/5] Checking server app import target...")
        probe_cmd = (
            "cd /var/www/html && python3 - <<'PY'\n"
            "import src.app\n"
            "print('src.app file:', getattr(src.app, '__file__', 'unknown'))\n"
            "print('has create_app:', hasattr(src.app, 'create_app'))\n"
            "PY"
        )
        stdin, stdout, stderr = ssh.exec_command(probe_cmd, timeout=20)
        probe_out = stdout.read().decode(errors="replace").strip()
        probe_err = stderr.read().decode(errors="replace").strip()
        if probe_out:
            print(probe_out)
        if probe_err:
            print("[WARN] import probe stderr:")
            print(probe_err[-3000:])
        print()

        if "ModuleNotFoundError: No module named 'flask'" in probe_err:
            print("[2c/5] Installing missing server Python Flask dependencies...")
            install_cmd = (
                "export DEBIAN_FRONTEND=noninteractive; "
                "dpkg --configure -a >/tmp/masternoder-dpkg-configure.log 2>&1 || true; "
                "apt-get update >/tmp/masternoder-apt-update.log 2>&1 || true; "
                "apt-get install -y python3-flask python3-flask-sqlalchemy python3-dotenv python3-requests "
                "python3-werkzeug python3-jinja2 python3-itsdangerous python3-click "
                ">/tmp/masternoder-apt-flask.log 2>&1; "
                "RC=$?; tail -80 /tmp/masternoder-apt-flask.log; exit $RC"
            )
            stdin, stdout, stderr = ssh.exec_command(install_cmd, timeout=180)
            install_out = stdout.read().decode(errors="replace").strip()
            install_err = stderr.read().decode(errors="replace").strip()
            if install_out:
                print(install_out[-5000:])
            if install_err:
                print("[WARN] dependency install stderr:")
                print(install_err[-3000:])
            stdin, stdout, stderr = ssh.exec_command(probe_cmd, timeout=20)
            probe_out = stdout.read().decode(errors="replace").strip()
            probe_err = stderr.read().decode(errors="replace").strip()
            if probe_out:
                print(probe_out)
            if probe_err:
                print("[WARN] import probe stderr after install:")
                print(probe_err[-3000:])
            print()

        if upload_only:
            print("="*70)
            print("UPLOAD COMPLETE (no restart)")
            print("="*70)
            print()
            print("When ready to load new backend code, on the server run e.g.:")
            print("  systemctl restart uwsgi-vidgenerator python-proxy uwsgi-vidgenerator-5001")
            print("Or use: python deploy.py   (without --upload-only) for full deploy + restart.")
            print()
            ssh.close()
            return True

        # Clear cache
        print("[3/5] Clearing cache...")
        ssh.exec_command("find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Stop services
        print("[4/5] Stopping services...")
        for service in ['uwsgi', 'uwsgi-vidgenerator', 'uwsgi-vidgenerator-5001', 'python-proxy']:
            ssh.exec_command(f"systemctl stop {service} 2>&1", timeout=10)
        time.sleep(3)
        print("  [OK] Services stopped")
        print()

        print("[4b/5] Cleaning stale uWSGI workers and sockets...")
        cleanup_cmd = (
            "systemctl reset-failed uwsgi uwsgi-vidgenerator uwsgi-vidgenerator-5001 python-proxy 2>/dev/null || true; "
            "fuser -k 5000/tcp 2>/dev/null || true; "
            "fuser -k 5001/tcp 2>/dev/null || true; "
            "pkill -TERM -f 'uwsgi.*(uwsgi.ini|uwsgi_5001.ini|apps-enabled/vidgenerator.ini)' 2>/dev/null || true; "
            "sleep 2; "
            "pkill -KILL -f 'uwsgi.*(uwsgi.ini|uwsgi_5001.ini|apps-enabled/vidgenerator.ini)' 2>/dev/null || true; "
            "rm -f /var/www/html/uwsgi.pid /var/www/html/uwsgi_5001.pid 2>/dev/null || true; "
            "sleep 2; "
            "if command -v ss >/dev/null 2>&1; then ss -ltnp '( sport = :5000 or sport = :5001 )' || true; fi"
        )
        stdin, stdout, stderr = ssh.exec_command(cleanup_cmd, timeout=20)
        cleanup_out = stdout.read().decode(errors="replace").strip()
        if cleanup_out:
            print(cleanup_out[-2000:])
        print("  [OK] stale uWSGI cleanup attempted")
        print()
        
        # Start services
        print("[5/5] Starting services...")
        # Do not start the legacy `uwsgi` wrapper here. It also loads a
        # vidgenerator app from /etc/uwsgi/apps-enabled and can race the
        # dedicated service for 127.0.0.1:5000.
        for service in ['uwsgi-vidgenerator', 'python-proxy']:
            ssh.exec_command(f"systemctl start {service} 2>&1", timeout=10)
        time.sleep(8)
        
        # Verify
        failed_services = []
        for service in ['uwsgi-vidgenerator', 'python-proxy']:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1", timeout=5)
            status = stdout.read().decode().strip()
            if status == "active":
                print(f"  [OK] {service} is ACTIVE")
            else:
                print(f"  [WARN] {service} status: {status}")
                failed_services.append(service)

        if failed_services:
            print()
            print("[DIAG] Service startup diagnostics:")
            for service in failed_services:
                print(f"--- systemctl status {service} ---")
                stdin, stdout, stderr = ssh.exec_command(f"systemctl status {service} --no-pager -l 2>&1 || true", timeout=10)
                print(stdout.read().decode(errors="replace")[-4000:])
                print(f"--- journalctl -u {service} ---")
                stdin, stdout, stderr = ssh.exec_command(f"journalctl -u {service} -n 80 --no-pager 2>&1 || true", timeout=10)
                print(stdout.read().decode(errors="replace")[-6000:])
            print("--- app startup logs ---")
            for log_path in [
                "/var/www/html/logs/wsgi_error.log",
                "/var/www/html/uwsgi.log",
                "/var/www/html/uwsgi_5001.log",
                "/var/www/html/vidgenerator/uwsgi.log",
            ]:
                stdin, stdout, stderr = ssh.exec_command(f"printf '\\n## {log_path}\\n'; tail -120 {log_path} 2>/dev/null || true", timeout=10)
                print(stdout.read().decode(errors="replace")[-6000:])
        
        # Last: vidgenerator on port 5001 (reload .env + app after main uwsgi stack)
        print()
        print("[6/6] Restarting uwsgi-vidgenerator-5001 (last)...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator-5001 2>&1", timeout=30)
        time.sleep(4)
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator-5001 2>&1", timeout=5)
        status_5001 = stdout.read().decode().strip()
        if status_5001 == "active":
            print("  [OK] uwsgi-vidgenerator-5001 is ACTIVE")
        else:
            print(f"  [WARN] uwsgi-vidgenerator-5001 status: {status_5001}")
        
        print()
        print("="*70)
        print("DEPLOYMENT COMPLETE!")
        print("="*70)
        print()
        print("Services restarted. Wait 10 seconds, then:")
        print("1. Visit: https://masternoder.dk/ and hard refresh: Ctrl+F5")
        print("2. Confirm the v2.0 hero, upgrade panels, and MasterNoder Sound System load")
        print("3. Start sound, switch Focus/Star/Battle modes, and confirm no console errors")
        print("4. Visit: https://masternoder.dk/vidgenerator/")
        print("5. Shop DB: GET /api/shop/payment-health — if shop_storage.mode is \"file\", run")
        print("   python scripts/shop_purchase_migration.py --standalone on the server (durable catalog/inventory).")
        print("6. Regression: python scripts/post_deploy_verify.py (or set DEPLOY_POST_VERIFY=1 next deploy).")
        print("   Use post_deploy_verify.py --list for a manual checklist.")
        print()

        _root = os.path.dirname(os.path.abspath(__file__))
        _verify = os.path.join(_root, "scripts", "post_deploy_verify.py")
        if os.environ.get("DEPLOY_POST_VERIFY", "").strip().lower() in ("1", "true", "yes") and os.path.isfile(_verify):
            print("[VERIFY] DEPLOY_POST_VERIFY=1 — running post_deploy_verify.py ...", flush=True)
            rc = subprocess.run([sys.executable, _verify], cwd=_root)
            if rc.returncode != 0:
                print(f"[WARN] post_deploy_verify exited with code {rc.returncode}", flush=True)

        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a.strip()]
    upload_only = "--upload-only" in argv or "--no-restart" in argv
    success = deploy(upload_only=upload_only)
    sys.exit(0 if success else 1)
