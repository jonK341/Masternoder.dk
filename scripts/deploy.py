#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generic deploy: upload files by manifest name, clear cache, restart services.
Usage:
  python scripts/deploy.py profile     # profile + auth
  python scripts/deploy.py sync        # sync + agent DB
  python scripts/deploy.py loading     # loading optimizations
  python scripts/deploy.py static_pages  # root index.html pages + entire static/ folder
  python scripts/deploy.py mn2_staking static_pages mn2_env --ask-pass  # multiple manifests (merged upload)
  python scripts/deploy.py trophies      # trophy levels, MN2 income, routes + data + UI
  python scripts/deploy.py compendium    # rulebook readers V1–V16, pages API, view tracker
  python scripts/deploy.py static_pages --upload-only   # upload only (no restart)
  python scripts/deploy.py battle_hunter_quick   # battle RPS/queue + Hunter XP + battle/profile UI + tournaments JS
  python scripts/deploy.py service_check_backend --upload-only   # leaderboard/agents/service_check files; no uwsgi restart
  python scripts/deploy.py --files path1 path2 ...
  python scripts/deploy.py --files debugger/index.html --upload-only   # upload only, no restart

SSH password: set DEPLOY_PASS, or use --ask-pass to prompt (ignores .env), or run from an
interactive terminal to be prompted twice when DEPLOY_PASS is unset.
"""
import os
import sys
import time
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass, connect_deploy_ssh

SERVER_HOST = deploy_host()
SERVER_USER = deploy_user()
REMOTE_BASE = "/var/www/html"

_MN2_SHELL_SCRIPTS = (
    "mn2_fix_config_permissions.sh",
    "mn2_fix_daemon_privkey.sh",
    "mn2_hotfix_alias_provision_server.sh",
    "mn2_fleet_autostart.sh",
    "mn2_unlock_collateral.sh",
    "camgirls_py.sh",
)


def _mn2_apply_config_permissions(ssh) -> None:
    """Ensure www-data can read masternoder2.conf (root:www-data 640). Requires root SSH."""
    print("[2h] MN2 config permissions (www-data read masternoder2.conf)...")
    config_dir = f"{REMOTE_BASE}/config"
    inline = (
        f"CONFIG={config_dir} && "
        f"chown root:www-data \"$CONFIG\" && chmod 775 \"$CONFIG\"; "
        f"if [ -f \"$CONFIG/masternoder2.conf\" ]; then "
        f"chown root:www-data \"$CONFIG/masternoder2.conf\" && chmod 640 \"$CONFIG/masternoder2.conf\"; "
        f"fi; "
        f"if [ -f \"$CONFIG/masternode.conf\" ]; then "
        f"chown www-data:www-data \"$CONFIG/masternode.conf\" && chmod 664 \"$CONFIG/masternode.conf\"; "
        f"fi"
    )
    ssh.exec_command(inline, timeout=15)
    time.sleep(0.3)
    fix_sh = f"{REMOTE_BASE}/scripts/mn2_fix_config_permissions.sh"
    stdin, stdout, stderr = ssh.exec_command(
        f"test -f {fix_sh} && bash {fix_sh} --verify 2>&1 || echo SKIP",
        timeout=30,
    )
    text = ((stdout.read() or b"") + (stderr.read() or b"")).decode(errors="replace").strip()
    if "FAIL" in text:
        print("  [WARN] www-data MN2 config permissions failed — fix on server as root:")
        print(f"         sudo bash {fix_sh}")
        for line in text.splitlines():
            if "FAIL" in line:
                print(f"         {line}")
    elif "OK www-data can read" in text:
        print("  [OK] masternoder2.conf + masternode.conf permissions verified")
    else:
        print("  [OK] inline config permissions applied")
    for sh in _MN2_SHELL_SCRIPTS:
        ssh.exec_command(f"chmod +x {REMOTE_BASE}/scripts/{sh} 2>/dev/null || true", timeout=5)
    print()


def _static_pages_manifest():
    """Root site HTML (index.html + */index.html) and all files under static/ (excludes backup trees)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = []
    skip_dirs = {
        "backend", "vidgenerator", "vidgenerator.backup", "server_backup",
        ".git", "__pycache__", "node_modules", "mcps", ".cursor", "src",
    }
    idx_root = os.path.join(root, "index.html")
    if os.path.isfile(idx_root):
        out.append("index.html")
    try:
        for name in os.listdir(root):
            if name in skip_dirs or name.startswith("."):
                continue
            p = os.path.join(root, name)
            if not os.path.isdir(p):
                continue
            idx = os.path.join(p, "index.html")
            if os.path.isfile(idx):
                out.append(f"{name}/index.html")
    except OSError:
        pass
    mc = os.path.join(root, "dashboard", "master_control", "index.html")
    if os.path.isfile(mc):
        out.append("dashboard/master_control/index.html")
    static_dir = os.path.join(root, "static")
    if os.path.isdir(static_dir):
        for dirpath, dirnames, filenames in os.walk(static_dir):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                if fn.startswith(".") or fn.endswith(".backup"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                out.append(rel)
    return sorted(set(out))


MANIFESTS = {
    "profile": [
        "vidgenerator/profile/index.html",
        "vidgenerator/static/js/backend-connector.js",
        "vidgenerator/static/js/image-support.js",
        "vidgenerator/static/css/sync-status-widget.css",
        "vidgenerator/static/js/sync-status-widget.js",
        "backend/routes/social_auth_routes.py",
        "backend/routes/user_profile_routes.py",
        "backend/routes/missing_endpoints_routes.py",
    ],
    "sync": [
        "backend/services/unified_points_sync.py",
        "scripts/sync_database_migration.py",
        "backend/services/communication_psychology_service.py",
        "backend/services/dna_manipulation_system.py",
        "backend/services/user_engagement.py",
        "backend/services/agent_db_service.py",
        "backend/routes/missing_endpoints_routes.py",
        "docs/SYNC_AND_AGENT_KNOWLEDGE.md",
        "docs/TSS_AI_IMPLEMENTATION_GUIDE.md",
        "docs/LOADING_AND_VIDGENERATOR_STATE.md",
        "data/rulebook_v16_sync.json",
    ],
    "loading": [
        "vidgenerator/static/js/load-time-measurement.js",
        "vidgenerator/static/css/sync-status-widget.css",
        "vidgenerator/static/js/sync-status-widget.js",
        "vidgenerator/unified_dashboard/index.html",
        "vidgenerator/profile/index.html",
        "vidgenerator/stats/index.html",
        "vidgenerator/generator/index.html",
        "vidgenerator/battle/index.html",
        "vidgenerator/shop/index.html",
        "backend/routes/missing_endpoints_routes.py",
        "docs/LOADING_AND_VIDGENERATOR_STATE.md",
    ],
    # TTS (Piper/ElevenLabs/gTTS) + Audio Enhancement (DeepFilterNet/loudnorm) — pipeline + system overview
    "tts": [
        "backend/services/tts_service.py",
        "backend/services/audio_enhancement_service.py",
        "backend/services/video_generator_service.py",
        "backend/routes/system_overview_routes.py",
        "backend/routes/ai_providers_routes.py",
        "backend/routes/missing_endpoints_routes.py",
        "vidgenerator/debugger/index.html",
        "backend/templates/debugger/index.html",
        "docs/ENCODER_FREE_TIER.md",
    ],
    "generator": [
        "vidgenerator/generator/index.html",
        "vidgenerator/static/js/theme-timeline.js",
        "vidgenerator/static/css/theme-timeline.css",
        "vidgenerator/static/js/unified-generator-battle.js",
        "vidgenerator/static/js/load-time-measurement.js",
        "vidgenerator/static/js/error-manager.js",
        "vidgenerator/static/js/service-worker-gatherer.js",
        "vidgenerator/static/css/navigation-toolbar.css",
        "vidgenerator/static/js/navigation-toolbar.js",
        "backend/routes/missing_endpoints_routes.py",
    ],
    # Minimal set for generator UI + routes + blueprint; only restarts uwsgi-vidgenerator
    "generator_recent": [
        "generator/index.html",
        "backend/routes/missing_endpoints_routes.py",
        "backend/routes/generator_routes.py",
        "backend/routes/generator_shared.py",
        "backend/routes/gallery_routes.py",
        "backend/register_blueprints.py",
        "backend/services/video_generator_service.py",
        "backend/services/generator_crypto_rewards_service.py",
        "backend/services/generator_mn2_service.py",
        "backend/services/video_ai_bridge.py",
        "backend/services/agent_support_service.py",
        "backend/services/user_identification.py",
        "backend/run_generator_job.py",
        "data/generator_config.json",
        "data/mn2_config.json",
        "backend/services/generator_agent_service.py",
        "backend/services/generator_encode_service.py",
        "backend/services/generator_thumbnail_service.py",
        "backend/services/tts_service.py",
        "scripts/generator_stale_cleanup.py",
        "static/js/unified-point-counters.js",
    ],
    # Gallery + compact nav (no restart override; use full restart)
    "gallery_nav": [
        "gallery/index.html",
        "static/css/navigation-toolbar.css",
        "static/css/page-layout-metrics.css",
        "static/css/page-layout-metrics-debugger.css",
    ],
    # Star Map 25 upgrade: monitor, 50 projects, agent assignment, generator UI
    "starmap25": [
        "starmap25/index.html",
        "game/index.html",
        "generator/index.html",
        "backend/routes/star_map_routes.py",
        "backend/routes/debugger_agent_tasks_routes.py",
        "data/star_map_25.json",
        "data/starmap25_agent_projects.json",
        "data/starmap25_ai_proof_docs.json",
        "data/starmap25_walkthrough.json",
        "docs/STARMAP_25_50_PROJECTS.md",
        "docs/STARMAP25_UPGRADE_FINISH.md",
        "uwsgi.ini",
        ".uwsgi_touch_reload",
    ],
    # Rewind cleanup + deploy all commonly missing files (profile, sync, loading, tts, endpoints, blueprints, agent services)
    "rewind_missing": [
        "backend/routes/missing_endpoints_routes.py",
        "backend/register_blueprints.py",
        "vidgenerator/profile/index.html",
        "vidgenerator/static/js/backend-connector.js",
        "vidgenerator/static/css/sync-status-widget.css",
        "vidgenerator/static/js/sync-status-widget.js",
        "vidgenerator/static/js/image-support.js",
        "backend/routes/social_auth_routes.py",
        "backend/routes/user_profile_routes.py",
        "backend/services/unified_points_sync.py",
        "scripts/sync_database_migration.py",
        "backend/services/communication_psychology_service.py",
        "backend/services/dna_manipulation_system.py",
        "backend/services/user_engagement.py",
        "backend/services/agent_db_service.py",
        "backend/services/agent_controller.py",
        "backend/services/agent_automation.py",
        "backend/services/agent_skillset.py",
        "backend/services/agent_groups.py",
        "backend/services/agent_ability_tracker.py",
        "vidgenerator/static/js/load-time-measurement.js",
        "vidgenerator/unified_dashboard/index.html",
        "vidgenerator/stats/index.html",
        "vidgenerator/generator/index.html",
        "vidgenerator/battle/index.html",
        "vidgenerator/shop/index.html",
        "backend/services/tts_service.py",
        "backend/services/audio_enhancement_service.py",
        "backend/services/video_generator_service.py",
        "backend/routes/system_overview_routes.py",
        "backend/routes/ai_providers_routes.py",
        "vidgenerator/debugger/index.html",
        "docs/SYNC_AND_AGENT_KNOWLEDGE.md",
        "docs/TSS_AI_IMPLEMENTATION_GUIDE.md",
        "docs/LOADING_AND_VIDGENERATOR_STATE.md",
        "docs/ENCODER_FREE_TIER.md",
        "data/rulebook_v16_sync.json",
    ],
    # Trophy system: collector levels, passive income (pts + MN2), social, agent tools
    "trophies": [
        "trophies/index.html",
        "profile/index.html",
        "backend/routes/trophies_routes.py",
        "backend/services/trophy_level_service.py",
        "backend/services/trophy_social_service.py",
        "backend/services/trophy_quest_service.py",
        "data/trophy_levels.json",
        "data/trophy_definitions.json",
    ],
    # Compendium + rulebook readers (V1–V16), view tracker, pages API
    "compendium": [
        "compendium/index.html",
        "compendium/rulebook-viewer.html",
        "compendium/hunters-rulebook.html",
        "compendium/page-1.html",
        "compendium/page-2.html",
        "compendium/page-3.html",
        "compendium/page-4.html",
        "compendium/page-5.html",
        "compendium/page-6.html",
        "compendium/page-7.html",
        "compendium/page-8.html",
        "compendium/page-9.html",
        "compendium/page-10.html",
        "static/js/compendium-view-tracker.js",
        "static/css/calm-reader.css",
        "static/js/calm-reader.js",
        "static/js/reader-launcher.js",
        "static/js/navigation-toolbar.js",
        "backend/routes/rulebook_routes.py",
        "backend/routes/compendium_routes.py",
        "backend/services/compendium_crypto_rewards_service.py",
        "backend/routes/all_page_routes.py",
        "backend/register_blueprints.py",
        "data/rulebook_index_v15.json",
        "data/rulebook_v1_core.json",
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
        "data/hunters_rulebook_v2.json",
        "data/communication_psychology_theories.json",
        "data/mn2_config.json",
        "static/img/rulebook-compendium-v15.png",
        "static/img/rulebook-v1-core.png",
        "static/img/rulebook-v2-hunters.png",
        "static/img/rulebook-v3-comm-psych.png",
        "static/img/rulebook-v3-2-systemic.png",
        "static/img/rulebook-v4-star-map.png",
        "static/img/rulebook-v5-effect-clusters.png",
        "static/img/rulebook-v6-electric-magnet.png",
        "static/img/rulebook-v7-unified-points.png",
        "static/img/rulebook-v8-agents.png",
        "static/img/rulebook-v9-shop.png",
        "static/img/rulebook-v10-battle.png",
        "static/img/rulebook-v11-dna.png",
        "static/img/rulebook-v12-generator.png",
        "static/img/rulebook-v13-geo-session.png",
        "static/img/rulebook-v14-analytics.png",
        "static/img/rulebook-v16-sync.png",
        "scripts/generate_rulebook_images.py",
        "docs/RULEBOOK_READERS.md",
    ],
    # Unified Game Hub: frontpage tabs + quest unification (Option C)
    "game_hub": [
        "index.html",
        "quests/index.html",
        "trophies/index.html",
        "static/css/frontpage-home.css",
        "static/js/game-hub-panel.js",
        "backend/routes/game_hub_routes.py",
        "backend/services/game_hub_service.py",
        "backend/services/trophy_quest_service.py",
        "backend/routes/quest_routes.py",
        "backend/services/trophies_db_service.py",
        "backend/services/user_engagement.py",
        "backend/routes/trophies_routes.py",
        "backend/register_blueprints.py",
    ],
    # Fix production 404s: routes + fallbacks + blueprint registration (see logs/production_404_deploy_checklist.txt)
    "fix_404": [
        "backend/routes/missing_endpoints_routes.py",
        "backend/register_blueprints.py",
        "backend/routes/user_profile_routes.py",
        "backend/routes/user_account_routes.py",
        "backend/routes/battle_routes.py",
        "backend/routes/agent_automation_routes.py",
        "backend/routes/gallery_routes.py",
        "backend/routes/trophies_routes.py",
    ],
    # Quick battle (RPS / queue / Hunter XP), Hunters award_xp metadata, battle + profile UI, fantasy tournaments JS
    "battle_hunter_quick": [
        "backend/routes/battle_routes.py",
        "backend/routes/hunters_game.py",
        "backend/services/game_level_crypto_service.py",
        "data/game_level_crypto.json",
        "game/index.html",
        "static/css/game-tabulator.css",
        "static/js/game-tabulator.js",
        "static/js/game-level-crypto.js",
        "battle/index.html",
        "profile/index.html",
        "static/js/enhanced-game-mechanics.js",
    ],
    # Important-only: 502/recursion fix (agent_ai_intelligence RecursionError, restart script log path, docs)
    "important": [
        "backend/services/agent_ai_intelligence.py",
        "backend/services/path_corrector.py",
        "backend/middleware/signal_processor_middleware.py",
        "scripts/restart_uwsgi_fix_502.py",
        "docs/SERVER_QUICK_REFERENCE.md",
        "src/app/__init__.py",
    ],
    # Full solution: generator safeJson, profile/game time & boosters, shop apply, fallbacks, docs
    "solution": [
        "vidgenerator/generator/index.html",
        "vidgenerator/profile/index.html",
        "vidgenerator/game/index.html",
        "backend/routes/missing_endpoints_routes.py",
        "backend/routes/shop_routes.py",
        "backend/services/unified_points_database.py",
        "backend/services/user_profile.py",
        "docs/PAGES_AND_FUNCTIONS_AUDIT.md",
        "docs/STARMAP_25_TOP10_IDEAS.md",
        "docs/AGENTS_SKILLS_SYNC.md",
    ],
    # API monitor dashboard (GET /api/) + disabled /vidgenerator/api
    "monitor": [
        "backend/routes/api_monitor_routes.py",
        "backend/routes/vidgenerator_disabled_routes.py",
        "backend/register_blueprints.py",
    ],
    # User location (GPS), themes, criticism skill, profile/generator/agents/gallery/aggregator UI
    "location_themes_recent": [
        "backend/services/user_location_service.py",
        "backend/routes/user_profile_routes.py",
        "backend/routes/hunters_game.py",
        "backend/services/agent_skillset.py",
        "backend/routes/missing_endpoints_routes.py",
        "profile/index.html",
        "generator/index.html",
        "theme_premium/index.html",
        "agents/index.html",
        "gallery/index.html",
        "aggregator/index.html",
        "static/js/theme-timeline.js",
        "docs/USER_LOCATION_GPS_SYSTEM.md",
        "docs/AGENT_SKILLS_AND_CONCLUSIONS.md",
        "docs/AGENTS_SKILLS_SYNC.md",
    ],
    # MN2 401 fix: upload only .env + systemd units, install units, restart uwsgi-vidgenerator
    "mn2_env": [
        ".env",
        "systemd/uwsgi-vidgenerator.service",
        "systemd/uwsgi-vidgenerator-5001.service",
        "systemd/masternoder2d.service.example",
        "scripts/run_masternoder2d.sh",
        "scripts/run_masternoder2d.ps1",
        "cron/mn2_scan_deposits.sh",
        "cron/masternoder-mn2-scan.cron.d",
        "cron/mn2_accrue_rewards.sh",
        "cron/masternoder-mn2-accrue.cron.d",
        "cron/mn2_masternode_provision.sh",
        "cron/masternoder-mn2-masternode-provision.cron.d",
        "scripts/mn2_patch_rpc_retries.sh",
    ],
    # MN2 staking system backend: services + routes + blueprint registration + config + ops script.
    # Frontend (profile/staking-monitor pages + static/js/mn2-*.js) ships via the "static_pages" manifest;
    # cron + .env ship via "mn2_env". Restarts both uwsgi-vidgenerator units to load new env/Python.
    # NOTE: data/*.json here are CONFIG (safe to overwrite). Runtime state files (mn2_stakes.json,
    # mn2_ledger.json, reserve/rewards, onramp/p2p orders, agent_staking_agents.json) are intentionally
    # NOT deployed so the server's live state is never clobbered.
    #
    # REMEMBER: backend/services/monetization_config_service.py — required whenever
    # monetization_config.json or get_* helpers change (generator API tiers, mobile_iap,
    # coin packs). Missing on server => /api/generator/api/tiers returns tiers:[].
    "mn2_staking": [
        "backend/services/mn2_rpc_client.py",
        "backend/services/mn2_ledger.py",
        "backend/services/mn2_deposit_scanner.py",
        "backend/services/mn2_chainz.py",
        "backend/services/mn2_wallet_service.py",
        "backend/services/mn2_network_stats.py",
        "backend/services/mn2_explorer_data.py",
        "backend/services/mn2_explorer_urls.py",
        "backend/services/mn2_staking_service.py",
        "backend/services/mn2_staking_reconcile_service.py",
        "backend/services/mn2_staking_agents_service.py",
        "backend/services/agent_trader_staking_service.py",
        "backend/services/agent_trader_service.py",
        "backend/services/agent_kill_switch.py",
        "backend/services/p2p_market_service.py",
        "backend/services/mn2_earn_auth.py",
        "backend/services/mn2_copy_trading.py",
        "backend/services/mn2_onramp_service.py",
        "backend/services/mn2_p2p_service.py",
        "backend/services/mn2_masternode_service.py",
        "backend/services/mn2_masternode_hosting_service.py",
        "backend/services/mn2_services_hub.py",
        "backend/services/discord_service.py",
        "backend/services/discord_m8_streams.py",
        "backend/services/casino_discord_fanout.py",
        "backend/services/market_discord_fanout.py",
        "backend/services/game_discord_fanout.py",
        "backend/services/compendium_milestone_service.py",
        "backend/services/compendium_access_service.py",
        "backend/services/generator_api_key_service.py",
        "backend/services/camgirls_livekit_service.py",
        "backend/services/mobile_iap_service.py",
        "backend/services/shop_auction_service.py",
        "backend/services/discord_hosting_vip_service.py",
        "backend/services/tier_b_monetization_service.py",
        "backend/services/referral_purchase_rewards_service.py",
        "backend/services/shop_upsell_service.py",
        "backend/services/monetization_revenue_pulse_service.py",
        "backend/services/monetization_margin_report_service.py",
        "backend/services/monetization_scr_blend_service.py",
        "backend/services/monetization_config_service.py",
        "backend/services/agent_cron_service.py",
        "backend/routes/paypal_routes.py",
        "backend/services/discord_link_service.py",
        "backend/services/shop_discord_promo_service.py",
        "backend/services/shop_checkout_promo_service.py",
        "backend/routes/battle_routes.py",
        "backend/routes/hunters_game.py",
        "backend/routes/shop_routes.py",
        "backend/routes/generator_routes.py",
        "backend/routes/camgirls_routes.py",
        "backend/routes/monetization_expansion_routes.py",
        "backend/routes/cogs_routes.py",
        "data/discord_promo_codes.json",
        "profile/index.html",
        "backend/services/unified_points_database.py",
        "backend/routes/health_routes.py",
        "backend/routes/discord_routes.py",
        "backend/routes/platform_news_routes.py",
        "backend/services/video_generator_service.py",
        "backend/routes/mn2_routes.py",
        "backend/routes/mn2_staking_routes.py",
        "backend/routes/mn2_onramp_routes.py",
        "backend/routes/mn2_p2p_routes.py",
        "backend/routes/mn2_masternode_routes.py",
        "backend/routes/agent_staking_routes.py",
        "backend/routes/agent_treasury_routes.py",
        "backend/routes/agent_trader_staking_routes.py",
        "backend/routes/p2p_market_routes.py",
        "backend/routes/agent_cron_routes.py",
        "backend/services/agent_cron_service.py",
        "backend/services/agent_wallet_service.py",
        "backend/services/treasury_signoff_service.py",
        "backend/routes/all_page_routes.py",
        "backend/register_blueprints.py",
        "data/mn2_config.json",
        "data/mn2_staking_config.json",
        "data/mn2_staking_terms.json",
        "data/mn2_masternode_config.json",
        "data/monetization_config.json",
        "shop/index.html",
        "hosting/index.html",
        "generator/index.html",
        "camgirls/index.html",
        "scripts/mn2_reconcile.py",
        "scripts/mn2_next_ops_remote.py",
        "scripts/mn2_ops_optionals_remote.py",
        "scripts/mn2_p1_monetization_remote.py",
        "scripts/mn2_start_masternode.py",
        "scripts/mn2_fix_daemon_privkey.sh",
        "scripts/mn2_ensure_rpc_conf.sh",
        "scripts/mn2_fix_config_permissions.sh",
        "scripts/mn2_unlock_collateral.sh",
        "scripts/mn2_repair_masternode_conf.sh",
        "scripts/mn2_fleet_autostart.sh",
        "scripts/mn2_masternode_fleet_ops_remote.py",
        "scripts/mn2_check_activetime_public.py",
        "scripts/mn2_test_ping_live.py",
        "scripts/mn2_hotfix_alias_provision_server.sh",
        "scripts/fix_explorer_subdomains_remote.py",
        "systemd/mn2-fleet-autostart.service.example",
        "scripts/treasury_signoff.py",
        "scripts/trader_staking_join_server.sh",
        "explorer/index.html",
        "static/js/mn2-explorer-overview.js",
        "static/js/mn2-internal-market.js",
        "static/js/mn2-crypto-hub.js",
        "static/css/mn2-crypto-hub.css",
        "scripts/_verify_trader_market_remote.py",
        "cron/discord_market_fanout.sh",
        "cron/discord_promo_rotator.sh",
        "cron/discord_game_fanout.sh",
        "cron/masternoder-discord-game.cron.d",
        "cron/masternoder-discord-market.cron.d",
        "cron/masternoder-discord-promo.cron.d",
        "cron/monetization_cron.sh",
        "cron/masternoder-monetization.cron.d",
        "cron/revenue_pulse_cron.sh",
        "cron/masternoder-revenue-pulse.cron.d",
        "cron/margin_report_cron.sh",
        "cron/masternoder-margin-report.cron.d",
        "cron/discord_activity_funnel.sh",
        "cron/mn2_read_ops_secret.sh",
    ],
    "camgirls": [
        "backend/services/camgirls_service.py",
        "backend/services/camgirls_payout_service.py",
        "backend/services/camgirls_agents_service.py",
        "backend/services/camgirls_studio_service.py",
        "backend/services/camgirls_social_service.py",
        "backend/services/mn2_wallet_service.py",
        "backend/services/mn2_rpc_client.py",
        "backend/services/platform_news_publish.py",
        "backend/services/discord_m8_streams.py",
        "backend/routes/camgirls_routes.py",
        "backend/services/mn2_earn_auth.py",
        "backend/services/mn2_ledger.py",
        "backend/services/unified_points_database.py",
        "backend/services/llm_service.py",
        "backend/services/agent_skillset.py",
        "backend/services/agent_cron_service.py",
        "backend/routes/agent_cron_routes.py",
        "backend/routes/all_page_routes.py",
        "backend/register_blueprints.py",
        "backend/middleware/error_logging_middleware.py",
        "backend/services/mn2_chainz.py",
        "backend/routes/mn2_routes.py",
        "backend/routes/mn2_staking_routes.py",
        "data/camgirls_performers.json",
        "data/camgirls_agent_models.json",
        "data/camgirls_studio_catalog.json",
        # Runtime: provision on server via camgirls_provision_payout_addresses.py — do not deploy empty file.
        "data/camgirls_performers_production.json",
        "data/camgirls_performers_production.template.json",
        "scripts/camgirls_onboard_performers.py",
        "scripts/camgirls_provision_payout_addresses.py",
        "scripts/camgirls_py.sh",
        "scripts/project_env.py",
        "scripts/camgirls_post_deploy_verify.py",
        "scripts/camgirls_discord_spotlight.py",
        "scripts/camgirls_remote_diag.py",
        "docs/CAMGIRLS_PHASE4_NGINX.md",
        "camgirls/index.html",
        "static/js/camgirls.js",
        "static/js/camgirls-studio.js",
        "scripts/camgirls_py.sh",
        "static/camgirls/avatar-demo.svg",
        "static/camgirls/avatar-sage.svg",
        "static/camgirls/avatar-ember.svg",
        "static/camgirls/avatar-iris.svg",
        "static/camgirls/preview-demo.svg",
    ],
    # Reporter agent: knowledge-sharing ingredients cron (daily); set KNOWLEDGE_REPORT_SECRET in .env
    "knowledge_cron_env": [
        "cron/knowledge_sharing_report.sh",
        "cron/masternoder-knowledge-report.cron.d",
    ],
    # Agent platform crons (daily/weekly/monthly); set AGENT_CRON_SECRET — see docs/RESEARCH_AI_SYSTEMS.md
    "agents_cron_env": [
        "cron/agents_cron_daily.sh",
        "cron/agents_cron_weekly.sh",
        "cron/agents_cron_monthly.sh",
        "cron/agents_blueprint_route_fixer.sh",
        "cron/agents_api_service_skill.sh",
        "cron/agents_trader.sh",
        "cron/masternoder-agents-daily.cron.d",
        "cron/masternoder-agents-weekly.cron.d",
        "cron/masternoder-agents-monthly.cron.d",
        "cron/masternoder-agents-blueprint-route.cron.d",
        "cron/masternoder-agents-api-service.cron.d",
        "cron/masternoder-agents-trader.cron.d",
    ],
    # MN2 daemon config (masternoder2.conf); deploy config folder to server
    "config": [
        "config/masternoder2.conf.example",
        "config/masternoder2.conf",
    ],
    # Optional: agent daemon (scripts/agent_daemon.py) + systemd unit example — install unit manually on server
    "agent_daemon_env": [
        "scripts/agent_daemon.py",
        "systemd/masternoder-agent-daemon.service.example",
    ],
    # Leaderboard + /agents routing fix + service check script (upload-only, then run service_check with --restart-uwsgi)
    "service_check_backend": [
        "backend/routes/missing_endpoints_routes.py",
        "backend/routes/leaderboard_routes.py",
        "backend/services/unified_points_database.py",
        "scripts/service_check_all_components.py",
        "docs/SERVICE_CHECK_LEADERBOARD_AGENTS_FIX.md",
    ],
    # Investigate + remove leftover/outdated files on server (no uwsgi restart)
    "server_prune": [
        "scripts/server_orphan_scan.py",
        "scripts/server_prune_remote.sh",
        "scripts/server_cleanup_scan.py",
    ],
}

# Built at import: every root */index.html + static/** (see _static_pages_manifest docstring)
MANIFESTS["static_pages"] = _static_pages_manifest()


# When using this manifest, restart both vidgenerator uwsgi units (nginx upstream uses :5000 + :5001).
RESTART_VIDGENERATOR_ONLY_FOR = frozenset({
    "generator_recent",
    "monitor",
    "mn2_env",
    "mn2_staking",
    "camgirls",
    "trophies",
    "compendium",
    "game_hub",
    "config",
    "agent_daemon_env",
    "service_check_backend",
})
# HTML/CSS/JS under /var/www/html — clear nginx cache + reload nginx only (no uwsgi/python-proxy)
RESTART_NGINX_ONLY_FOR = frozenset({"static_pages"})


def run_server_prune(server_pass=None, with_disk=False):
    """SSH: upload prune scripts, print investigation, run safe cleanup (no service restart)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
    import server_orphan_scan as orphan  # noqa: E402

    if not server_pass:
        server_pass = require_deploy_pass()
    ssh = None
    sftp = None
    try:
        print("=" * 60)
        print("SERVER PRUNE — investigate + safe cleanup")
        print("=" * 60)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(base)

        ssh, auth_method = connect_deploy_ssh(server_pass)
        sftp = ssh.open_sftp()
        print(f"  [OK] Connected ({auth_method})")
        print()

        for local in MANIFESTS["server_prune"]:
            if not os.path.isfile(local):
                continue
            remote = f"{REMOTE_BASE}/{local.replace(os.sep, '/')}"
            ssh.exec_command(f"mkdir -p '{os.path.dirname(remote)}'", timeout=5)
            with open(local, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            with sftp.file(remote, "w") as rf:
                rf.write(content)
            print(f"  [OK] uploaded {local}")
        sftp.close()
        print()

        report = orphan.investigate(ssh)
        print("\n".join(report))
        print("\n--- CLEANUP ---")
        for line in orphan.cleanup(ssh, yes=True, with_disk=with_disk):
            print(f"  [OK] {line}")

        print("\n" + "=" * 60)
        print("SERVER PRUNE COMPLETE (no uwsgi restart)")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if sftp:
            try:
                sftp.close()
            except Exception:
                pass
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass


def _merge_manifest_files(manifest_names):
    """Merge file lists from multiple manifests, preserving order and deduplicating."""
    files = []
    seen = set()
    for name in manifest_names:
        for path in MANIFESTS[name]:
            if path not in seen:
                seen.add(path)
                files.append(path)
    return files


def _resolve_restart_services(manifest_names, upload_only):
    names = set(manifest_names)
    if names & RESTART_VIDGENERATOR_ONLY_FOR:
        print("(Restart: uwsgi-vidgenerator + uwsgi-vidgenerator-5001)")
        return ["uwsgi-vidgenerator", "uwsgi-vidgenerator-5001"]
    if names & RESTART_NGINX_ONLY_FOR and not upload_only:
        print("(Restart: nginx reload only — static HTML/CSS/JS)")
        return ["__nginx_static__"]
    return None


def run(files, upload_only=False, restart_services=None, manifest_name=None, manifest_names=None, server_pass=None):
    if not server_pass:
        server_pass = require_deploy_pass()
    _manifests = set(manifest_names or ([] if manifest_name is None else [manifest_name]))
    ssh = None
    sftp = None
    try:
        print("=" * 60)
        print("DEPLOY:", " ".join(files[:3]) + (" ..." if len(files) > 3 else ""))
        if upload_only:
            print("(upload only — no cache clear, no restart)")
        print("=" * 60)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(base)

        step = "[1/2]" if upload_only else "[1/4]"
        print(f"{step} Connecting...")
        ssh, auth_method = connect_deploy_ssh(server_pass)
        sftp = ssh.open_sftp()
        print(f"  [OK] Connected ({auth_method})")
        print()

        step = "[2/2]" if upload_only else "[2/4]"
        print(f"{step} Uploading files...")
        deployed = 0
        for local in files:
            if not os.path.exists(local):
                print(f"  [SKIP] {local} (missing)")
                continue
            remote = f"{REMOTE_BASE}/{local.replace(os.sep, '/')}"
            remote_dir = os.path.dirname(remote)
            try:
                ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=5)
                time.sleep(0.2)
            except Exception:
                pass
            try:
                with open(local, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                with sftp.file(remote, "w") as rf:
                    rf.write(content)
                print(f"  [OK] {local}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local}: {e}")
        sftp.close()
        print(f"  [SUMMARY] {deployed} files uploaded")
        print()

        # If we uploaded systemd units, install them so EnvironmentFile=.env is used
        systemd_units = [f for f in files if f.replace("\\", "/").startswith("systemd/") and f.endswith(".service")]
        if systemd_units and not upload_only:
            print("[2b] Installing systemd units...")
            for unit in ("uwsgi-vidgenerator.service", "uwsgi-vidgenerator-5001.service"):
                ssh.exec_command(f"cp {REMOTE_BASE}/systemd/{unit} /etc/systemd/system/ 2>/dev/null && echo OK", timeout=5)
                time.sleep(0.5)
            ssh.exec_command("systemctl daemon-reload", timeout=10)
            print("  [OK] systemd units installed and daemon-reloaded")
            print()

        # MN2 deposit scanner: executable + /etc/cron.d/ (manifest mn2_env)
        if "mn2_env" in _manifests and not upload_only:
            print("[2c] MN2 scanner cron...")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/mn2_scan_deposits.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-mn2-scan.cron.d /etc/cron.d/masternoder-mn2-scan && chmod 644 /etc/cron.d/masternoder-mn2-scan",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command("test -f /etc/cron.d/masternoder-mn2-scan && echo OK", timeout=5)
            out = (stdout.read() or b"").decode().strip()
            if out == "OK":
                print("  [OK] /etc/cron.d/masternoder-mn2-scan (every 5 min)")
            else:
                print("  [WARN] cron.d install may have failed — check root and /etc/cron.d/")

            # MN2 staking reward accrual cron (hourly)
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/mn2_accrue_rewards.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-mn2-accrue.cron.d /etc/cron.d/masternoder-mn2-accrue && chmod 644 /etc/cron.d/masternoder-mn2-accrue",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command("test -f /etc/cron.d/masternoder-mn2-accrue && echo OK", timeout=5)
            out2 = (stdout.read() or b"").decode().strip()
            print("  [OK] /etc/cron.d/masternoder-mn2-accrue (hourly)" if out2 == "OK"
                  else "  [WARN] staking accrual cron.d install may have failed")
            print()

        if "mn2_staking" in _manifests and not upload_only:
            print("[2f] MN2 masternode hosting post-deploy...")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/mn2_masternode_provision.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-mn2-masternode-provision.cron.d "
                f"/etc/cron.d/masternoder-mn2-masternode-provision 2>/dev/null && "
                f"chmod 644 /etc/cron.d/masternoder-mn2-masternode-provision 2>/dev/null || true",
                timeout=10,
            )
            seed_cmd = (
                f"cd {REMOTE_BASE} && "
                "SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' .env | head -1 | cut -d= -f2- | tr -d '\\r\"') && "
                "for n in 2 3 4 5; do "
                "curl -s -X POST -H 'Content-Type: application/json' -H \"X-Ops-Secret: $SECRET\" "
                "-d \"{\\\"id\\\":\\\"platform-mn-$n\\\",\\\"label\\\":\\\"Masternoder.dk fleet #$n\\\","
                "\\\"status\\\":\\\"queued\\\",\\\"notes\\\":\\\"Platform expansion slot\\\"}\" "
                "http://127.0.0.1:5000/api/mn2/masternode/hosts; echo; done && "
                "curl -s http://127.0.0.1:5000/api/mn2/masternode/service | head -c 800"
            )
            stdin, stdout, stderr = ssh.exec_command(seed_cmd, timeout=60)
            out = (stdout.read() or b"").decode(errors="replace").strip()
            if out:
                print(f"  {out[:600]}")
            print("  [OK] masternode provision cron + fleet seed (platform-mn-2..5)")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/discord_game_fanout.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-discord-game.cron.d /etc/cron.d/masternoder-discord-game "
                f"&& chmod 644 /etc/cron.d/masternoder-discord-game",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command(
                "test -f /etc/cron.d/masternoder-discord-game && echo OK", timeout=5
            )
            out_dg = (stdout.read() or b"").decode().strip()
            print("  [OK] /etc/cron.d/masternoder-discord-game (every 15 min)" if out_dg == "OK"
                  else "  [WARN] discord game cron.d install may have failed")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/discord_market_fanout.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-discord-market.cron.d /etc/cron.d/masternoder-discord-market "
                f"&& chmod 644 /etc/cron.d/masternoder-discord-market",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command(
                "test -f /etc/cron.d/masternoder-discord-market && echo OK", timeout=5
            )
            out_dm = (stdout.read() or b"").decode().strip()
            print("  [OK] /etc/cron.d/masternoder-discord-market (every 15 min)" if out_dm == "OK"
                  else "  [WARN] discord market cron.d install may have failed")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/monetization_cron.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-monetization.cron.d /etc/cron.d/masternoder-monetization "
                f"&& chmod 644 /etc/cron.d/masternoder-monetization",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command(
                "test -f /etc/cron.d/masternoder-monetization && echo OK", timeout=5
            )
            out_mon = (stdout.read() or b"").decode().strip()
            print("  [OK] /etc/cron.d/masternoder-monetization (daily 09:00 UTC)" if out_mon == "OK"
                  else "  [WARN] monetization cron.d install may have failed")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/revenue_pulse_cron.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-revenue-pulse.cron.d /etc/cron.d/masternoder-revenue-pulse "
                f"&& chmod 644 /etc/cron.d/masternoder-revenue-pulse",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command(
                "test -f /etc/cron.d/masternoder-revenue-pulse && echo OK", timeout=5
            )
            out_rp = (stdout.read() or b"").decode().strip()
            print("  [OK] /etc/cron.d/masternoder-revenue-pulse (Mon 10:00 UTC)" if out_rp == "OK"
                  else "  [WARN] revenue pulse cron.d install may have failed")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/margin_report_cron.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-margin-report.cron.d /etc/cron.d/masternoder-margin-report "
                f"&& chmod 644 /etc/cron.d/masternoder-margin-report",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command(
                "test -f /etc/cron.d/masternoder-margin-report && echo OK", timeout=5
            )
            out_mr = (stdout.read() or b"").decode().strip()
            print("  [OK] /etc/cron.d/masternoder-margin-report (Tue 10:00 UTC)" if out_mr == "OK"
                  else "  [WARN] margin report cron.d install may have failed")
            _mn2_apply_config_permissions(ssh)

        if "config" in _manifests and not upload_only:
            _mn2_apply_config_permissions(ssh)

        if "knowledge_cron_env" in _manifests and not upload_only:
            print("[2d] Knowledge-sharing report cron (reporter_agent)...")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/knowledge_sharing_report.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-knowledge-report.cron.d /etc/cron.d/masternoder-knowledge-report && chmod 644 /etc/cron.d/masternoder-knowledge-report",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command(
                "test -f /etc/cron.d/masternoder-knowledge-report && echo OK", timeout=5
            )
            out = (stdout.read() or b"").decode().strip()
            if out == "OK":
                print("  [OK] /etc/cron.d/masternoder-knowledge-report (daily)")
            else:
                print("  [WARN] knowledge cron.d install may have failed")
            print()

        if "agents_cron_env" in _manifests and not upload_only:
            print("[2e] Agent platform crons (daily / weekly / monthly + blueprint/API)...")
            for sh in (
                "agents_cron_daily.sh",
                "agents_cron_weekly.sh",
                "agents_cron_monthly.sh",
                "agents_blueprint_route_fixer.sh",
                "agents_api_service_skill.sh",
                "agents_trader.sh",
            ):
                ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/{sh} 2>/dev/null || true", timeout=5)
            for cd, remote_name in (
                ("masternoder-agents-daily.cron.d", "masternoder-agents-daily"),
                ("masternoder-agents-weekly.cron.d", "masternoder-agents-weekly"),
                ("masternoder-agents-monthly.cron.d", "masternoder-agents-monthly"),
                ("masternoder-agents-blueprint-route.cron.d", "masternoder-agents-blueprint-route"),
                ("masternoder-agents-api-service.cron.d", "masternoder-agents-api-service"),
                ("masternoder-agents-trader.cron.d", "masternoder-agents-trader"),
            ):
                ssh.exec_command(
                    f"cp {REMOTE_BASE}/cron/{cd} /etc/cron.d/{remote_name} && chmod 644 /etc/cron.d/{remote_name}",
                    timeout=10,
                )
                time.sleep(0.15)
            print("  [OK] /etc/cron.d/masternoder-agents-* (daily, weekly, monthly, blueprint-route, api-service, trader)")
            print()

        if "camgirls" in _manifests and not upload_only:
            print("[2g] Camgirls post-deploy (venv deps + script perms)...")
            ssh.exec_command(
                f"chmod +x {REMOTE_BASE}/scripts/camgirls_py.sh 2>/dev/null || true",
                timeout=5,
            )
            dep_cmd = (
                f"cd {REMOTE_BASE} && "
                "if [ -x ./.venv/bin/python ]; then "
                "./.venv/bin/python -m ensurepip --upgrade 2>/dev/null || true; "
                "./.venv/bin/python -m pip install -q 'requests>=2.32.0,<2.34' 2>/dev/null || "
                "SITE=$(./.venv/bin/python -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null) && "
                "[ -n \"$SITE\" ] && python3 -m pip install -q -t \"$SITE\" 'requests>=2.32.0,<2.34' 2>/dev/null || true; "
                "fi"
            )
            stdin, stdout, stderr = ssh.exec_command(dep_cmd, timeout=120)
            stdout.channel.recv_exit_status()
            err = (stderr.read() or b"").decode(errors="replace").strip()
            if err and "error" in err.lower():
                print(f"  [WARN] pip install requests: {err[:200]}")
            else:
                print("  [OK] .venv requests (MN2 payout RPC)")
            onboard_cmd = (
                f"cd {REMOTE_BASE} && bash scripts/camgirls_py.sh "
                "scripts/camgirls_onboard_performers.py "
                "--file data/camgirls_performers_production.json 2>&1 | tail -8"
            )
            _, ob_out, _ = ssh.exec_command(onboard_cmd, timeout=120)
            ob_text = (ob_out.read() or b"").decode(errors="replace").strip()
            if ob_text:
                print(f"  [onboard] {ob_text.split(chr(10))[-1][:120]}")
            print()

        if upload_only:
            print("=" * 60)
            print("UPLOAD COMPLETE (no restart)")
            print("=" * 60)
            ssh.close()
            return True

        print("[3/4] Clearing cache...")
        ssh.exec_command(
            f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true",
            timeout=30,
        )
        ssh.exec_command(
            f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true",
            timeout=30,
        )
        ssh.exec_command("rm -rf /var/cache/nginx/* 2>/dev/null || true", timeout=10)
        print("  [OK] Cache cleared")
        print()

        print("[4/4] Restarting services...")
        wait_s = 8
        if restart_services is not None and restart_services == ["__nginx_static__"]:
            ssh.exec_command("nginx -t 2>&1 || true", timeout=10)
            ssh.exec_command("systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
            print("  [OK] Nginx reloaded (static_pages deploy; uwsgi not restarted)")
        elif restart_services is not None:
            for svc in restart_services:
                ssh.exec_command(f"systemctl restart {svc} 2>&1 || true", timeout=20)
                time.sleep(wait_s)
        else:
            ssh.exec_command("systemctl restart python-proxy 2>&1 || true", timeout=20)
            time.sleep(wait_s)
            for uwsgi_unit in (
                "uwsgi-vidgenerator",
                "uwsgi-vidgenerator-5001",
                "uwsgi",
            ):
                ssh.exec_command(f"systemctl restart {uwsgi_unit} 2>&1 || true", timeout=20)
                time.sleep(wait_s)
        for port in (5000, 5001):
            for _ in range(6):
                try:
                    stdin, stdout, stderr = ssh.exec_command(
                        f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{port}/casino/ 2>/dev/null || echo 000",
                        timeout=10,
                    )
                    out = (stdout.read() or b"").decode().strip()
                    if out and out != "000":
                        try:
                            c = int(out)
                            if 200 <= c < 600 or c in (301, 302):
                                print(f"  [OK] Upstream :{port}/casino/ -> {c}")
                                break
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(3)
            else:
                print(f"  [WARN] Upstream :{port} not ready (or /casino/ check timed out)")
        ssh.exec_command("nginx -t 2>&1 || true", timeout=10)
        ssh.exec_command("systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
        print("  [OK] Services restarted")
        print()
        print("=" * 60)
        print("DEPLOY COMPLETE")
        print("=" * 60)
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
        return False


def main():
    args = sys.argv[1:]
    ask_pass = "--ask-pass" in args
    if ask_pass:
        args = [a for a in args if a != "--ask-pass"]
    upload_only = "--upload-only" in args
    if upload_only:
        args = [a for a in args if a != "--upload-only"]
    with_disk = "--with-disk" in args
    if with_disk:
        args = [a for a in args if a != "--with-disk"]
    if not args:
        print("Usage: python scripts/deploy.py <manifest> [manifest ...] [--ask-pass] [--upload-only]")
        print("       python scripts/deploy.py --files path1 path2 [--ask-pass] [--upload-only]")
        print("  --ask-pass     Prompt for SSH password (ignores DEPLOY_PASS in .env)")
        print("  --upload-only  SFTP files to the server only (no cache clear, no systemd/cron hooks, no service restart).")
        print("Manifests:", ", ".join(MANIFESTS))
        sys.exit(1)
    server_pass = require_deploy_pass(force_prompt=ask_pass)
    if args and args[0].lower() == "server_prune":
        ok = run_server_prune(server_pass=server_pass, with_disk=with_disk)
        sys.exit(0 if ok else 1)
    manifest_names = None
    if args[0] == "--files":
        files = args[1:]
        if not files:
            print("--files requires at least one path")
            sys.exit(1)
        restart_services = None
    else:
        manifest_names = []
        for a in args:
            name = a.lower()
            if name not in MANIFESTS:
                print("Unknown manifest:", name, "| known:", ", ".join(MANIFESTS))
                sys.exit(1)
            manifest_names.append(name)
        if len(manifest_names) > 1:
            print(f"(Manifests: {', '.join(manifest_names)})")
        files = _merge_manifest_files(manifest_names)
        restart_services = _resolve_restart_services(manifest_names, upload_only)
    ok = run(
        files,
        upload_only=upload_only,
        restart_services=restart_services,
        manifest_names=manifest_names,
        server_pass=server_pass,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
