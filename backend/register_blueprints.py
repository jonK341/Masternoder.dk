"""
Automatic Blueprint Registration
Registers all blueprints in four groups (OK 1/4 through OK 4/4):

  [OK 1/4] Critical   — all_page, missing_endpoints, gallery, health
  [OK 2/4] Core       — game, battle, agents, points, paypal, user, compendium
  [OK 3/4] Monitoring — error, debug, dashboard, shop, auth
  [OK 4/4] Agents     — agent technologies, chat, quest, leaderboard

When LITE_APP=1 (env), only ~25 critical+core blueprints are registered (migration plan Phase 1.2).
Then auto-discovers any remaining blueprints and prints [SUMMARY].
"""
import os
from flask import Flask


def register_lite_blueprints(app):
    """Register only critical + core blueprints (LITE_APP=1). Same file capabilities, faster startup."""
    n = 0
    print("  [LITE_APP] Registering subset of blueprints (~25)...")
    # 1-4: Critical
    try:
        if 'all_pages' not in app.blueprints:
            from backend.routes.all_page_routes import all_page_bp
            app.register_blueprint(all_page_bp)
            n += 1
            print("  [OK] Registered all_page blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP all_page: {e}")
    try:
        if 'missing_endpoints' not in app.blueprints:
            from backend.routes.missing_endpoints_routes import missing_endpoints_bp
            app.register_blueprint(missing_endpoints_bp)
            n += 1
            print("  [OK] Registered missing_endpoints blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP missing_endpoints: {e}")
    try:
        if 'gallery' not in app.blueprints:
            from backend.routes.gallery_routes import gallery_bp
            app.register_blueprint(gallery_bp)
            n += 1
            print("  [OK] Registered gallery blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP gallery: {e}")
    try:
        if 'health' not in app.blueprints:
            from backend.routes.health_routes import health_bp
            app.register_blueprint(health_bp)
            n += 1
            print("  [OK] Registered health blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP health: {e}")
    try:
        if 'vidgenerator_disabled' not in app.blueprints:
            from backend.routes.vidgenerator_disabled_routes import vidgenerator_disabled_bp
            app.register_blueprint(vidgenerator_disabled_bp, url_prefix="/vidgenerator/api")
            n += 1
            print("  [OK] Registered vidgenerator_disabled")
    except Exception as e:
        print(f"  [WARN] LITE_APP vidgenerator_disabled: {e}")
    try:
        if 'api_monitor' not in app.blueprints:
            from backend.routes.api_monitor_routes import api_monitor_bp
            app.register_blueprint(api_monitor_bp)
            n += 1
            print("  [OK] Registered api_monitor")
    except Exception as e:
        print(f"  [WARN] LITE_APP api_monitor: {e}")
    try:
        if 'generator' not in app.blueprints:
            from backend.routes.generator_routes import generator_bp
            app.register_blueprint(generator_bp)
            n += 1
            print("  [OK] Registered generator blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP generator: {e}")
    # 5-10: Core
    try:
        from backend.routes.hunters_game import hunters_game_bp
        app.register_blueprint(hunters_game_bp)
        n += 1
        print("  [OK] Registered hunters_game blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP hunters_game: {e}")
    try:
        from backend.routes.star_map_routes import star_map_bp
        app.register_blueprint(star_map_bp)
        n += 1
        print("  [OK] Registered star_map blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP star_map: {e}")
    try:
        from backend.routes.intelligence_aggregator_routes import intelligence_aggregator_bp
        app.register_blueprint(intelligence_aggregator_bp)
        n += 1
        print("  [OK] Registered intelligence_aggregator blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP intelligence_aggregator: {e}")
    try:
        from backend.routes.battle_routes import battle_bp
        app.register_blueprint(battle_bp)
        n += 1
        print("  [OK] Registered battle blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP battle: {e}")
    try:
        from backend.routes.lab_routes import lab_bp
        app.register_blueprint(lab_bp)
        n += 1
        print("  [OK] Registered lab blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP lab: {e}")
    try:
        from backend.routes.trophies_routes import trophies_bp
        app.register_blueprint(trophies_bp)
        n += 1
        print("  [OK] Registered trophies blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP trophies: {e}")
    try:
        from backend.routes.game_hub_routes import game_hub_bp
        app.register_blueprint(game_hub_bp)
        n += 1
        print("  [OK] Registered game_hub blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP game_hub: {e}")
    try:
        from backend.routes.points_routes import points_bp
        app.register_blueprint(points_bp)
        n += 1
        print("  [OK] Registered points blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP points: {e}")
    try:
        from backend.routes.mn2_routes import mn2_bp
        app.register_blueprint(mn2_bp)
        n += 1
        print("  [OK] Registered mn2 blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP mn2: {e}")
    try:
        from backend.routes.ops_stream_routes import ops_stream_bp
        if "ops_stream" not in app.blueprints:
            app.register_blueprint(ops_stream_bp)
            n += 1
            print("  [OK] Registered ops_stream blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP ops_stream: {e}")
    try:
        from backend.routes.activity_stream_routes import activity_stream_bp
        if "activity_stream" not in app.blueprints:
            app.register_blueprint(activity_stream_bp)
            n += 1
            print("  [OK] Registered activity_stream blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP activity_stream: {e}")
    try:
        from backend.routes.mn2_staking_routes import mn2_staking_bp
        if 'mn2_staking' not in app.blueprints:
            app.register_blueprint(mn2_staking_bp)
            n += 1
            print("  [OK] Registered mn2_staking blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP mn2_staking: {e}")
    try:
        from backend.routes.mn2_masternode_routes import mn2_masternode_bp
        if 'mn2_masternode' not in app.blueprints:
            app.register_blueprint(mn2_masternode_bp)
            n += 1
            print("  [OK] Registered mn2_masternode blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP mn2_masternode: {e}")
    try:
        from backend.routes.agent_staking_routes import agent_staking_bp
        if 'agent_staking' not in app.blueprints:
            app.register_blueprint(agent_staking_bp)
            n += 1
            print("  [OK] Registered agent_staking blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP agent_staking: {e}")
    try:
        from backend.routes.agent_casino_routes import agent_casino_bp
        if 'agent_casino' not in app.blueprints:
            app.register_blueprint(agent_casino_bp)
            n += 1
            print("  [OK] Registered agent_casino blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP agent_casino: {e}")
    try:
        from backend.routes.mn2_onramp_routes import mn2_onramp_bp
        if 'mn2_onramp' not in app.blueprints:
            app.register_blueprint(mn2_onramp_bp)
            n += 1
            print("  [OK] Registered mn2_onramp blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP mn2_onramp: {e}")
    try:
        from backend.routes.mn2_p2p_routes import mn2_p2p_bp
        if 'mn2_p2p' not in app.blueprints:
            app.register_blueprint(mn2_p2p_bp)
            n += 1
            print("  [OK] Registered mn2_p2p blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP mn2_p2p: {e}")
    try:
        from backend.routes.ptc_ads_routes import ptc_ads_bp
        app.register_blueprint(ptc_ads_bp)
        n += 1
        print("  [OK] Registered ptc_ads blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP ptc_ads: {e}")
    try:
        from backend.routes.casino_routes import casino_bp
        app.register_blueprint(casino_bp)
        n += 1
        print("  [OK] Registered casino blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP casino: {e}")
    try:
        from backend.routes.paypal_routes import paypal_bp
        app.register_blueprint(paypal_bp)
        n += 1
        print("  [OK] Registered paypal blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP paypal: {e}")
    try:
        from backend.routes.cogs_routes import cogs_bp
        app.register_blueprint(cogs_bp)
        n += 1
        print("  [OK] Registered cogs blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP cogs: {e}")
    try:
        from backend.routes.monetization_expansion_routes import monetization_expansion_bp
        app.register_blueprint(monetization_expansion_bp)
        n += 1
        print("  [OK] Registered monetization_expansion blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP monetization_expansion: {e}")
    try:
        from backend.routes.compendium_routes import compendium_bp
        app.register_blueprint(compendium_bp)
        from backend.routes.rulebook_routes import rulebook_bp
        app.register_blueprint(rulebook_bp)
        n += 2
        print("  [OK] Registered compendium + rulebook blueprints")
    except Exception as e:
        print(f"  [WARN] LITE_APP compendium/rulebook: {e}")
    try:
        from backend.routes.user_account_routes import user_account_bp
        app.register_blueprint(user_account_bp)
        n += 1
        print("  [OK] Registered user_account blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP user_account: {e}")
    try:
        from backend.routes.user_profile_routes import user_profile_bp
        app.register_blueprint(user_profile_bp)
        n += 1
        print("  [OK] Registered user_profile blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP user_profile: {e}")
    try:
        from backend.routes.shop_routes import shop_bp
        app.register_blueprint(shop_bp)
        n += 1
        print("  [OK] Registered shop blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP shop: {e}")
    try:
        from backend.routes.social_auth_routes import social_auth_bp
        app.register_blueprint(social_auth_bp)
        n += 1
        print("  [OK] Registered social_auth blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP social_auth: {e}")
    try:
        from backend.routes.password_protection_routes import password_protection_bp
        app.register_blueprint(password_protection_bp)
        n += 1
        print("  [OK] Registered password_protection blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP password_protection: {e}")
    try:
        from backend.routes.platform_news_routes import platform_news_bp
        app.register_blueprint(platform_news_bp)
        n += 1
        print("  [OK] Registered platform_news blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP platform_news: {e}")
    try:
        from backend.routes.discord_routes import discord_bp
        if "discord" not in app.blueprints:
            app.register_blueprint(discord_bp)
            n += 1
            print("  [OK] Registered discord blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP discord: {e}")
    try:
        from backend.routes.customer_aggregator_routes import customer_aggregator_bp
        if "customer_aggregator" not in app.blueprints:
            app.register_blueprint(customer_aggregator_bp)
            n += 1
            print("  [OK] Registered customer_aggregator blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP customer_aggregator: {e}")
    try:
        from backend.routes.agent_treasury_routes import agent_treasury_bp
        if "agent_treasury" not in app.blueprints:
            app.register_blueprint(agent_treasury_bp)
            n += 1
            print("  [OK] Registered agent_treasury blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP agent_treasury: {e}")
    try:
        from backend.routes.agent_trader_staking_routes import agent_trader_staking_bp
        if "agent_trader_staking" not in app.blueprints:
            app.register_blueprint(agent_trader_staking_bp)
            n += 1
            print("  [OK] Registered agent_trader_staking blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP agent_trader_staking: {e}")
    try:
        from backend.routes.camgirls_routes import camgirls_bp
        if "camgirls" not in app.blueprints:
            app.register_blueprint(camgirls_bp)
            n += 1
            print("  [OK] Registered camgirls blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP camgirls: {e}")
    try:
        from backend.routes.security_cron_routes import security_cron_bp
        if "security_cron" not in app.blueprints:
            app.register_blueprint(security_cron_bp)
            n += 1
            print("  [OK] Registered security_cron blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP security_cron: {e}")
    try:
        from backend.routes.p2p_market_routes import p2p_market_bp
        if "p2p_market" not in app.blueprints:
            app.register_blueprint(p2p_market_bp)
            n += 1
            print("  [OK] Registered p2p_market blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP p2p_market: {e}")
    try:
        from backend.routes.debugger_quiz_routes import debugger_quiz_bp
        if "debugger_quiz" not in app.blueprints:
            app.register_blueprint(debugger_quiz_bp)
            n += 1
            print("  [OK] Registered debugger_quiz blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP debugger_quiz: {e}")
    try:
        from backend.routes.point_control_board_routes import point_control_board_bp
        if "point_control_board" not in app.blueprints:
            app.register_blueprint(point_control_board_bp)
            n += 1
            print("  [OK] Registered point_control_board blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP point_control_board: {e}")
    try:
        from backend.routes.agent_admin_routes import agent_admin_bp
        if "agent_admin" not in app.blueprints:
            app.register_blueprint(agent_admin_bp)
            n += 1
            print("  [OK] Registered agent_admin blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP agent_admin: {e}")
    try:
        from backend.routes.account_security_routes import account_security_bp
        app.register_blueprint(account_security_bp)
        n += 1
        print("  [OK] Registered account_security blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP account_security: {e}")
    try:
        if 'agent_profile' not in app.blueprints:
            from backend.routes.agent_profile_routes import agent_profile_bp
            app.register_blueprint(agent_profile_bp)
            n += 1
            print("  [OK] Registered agent_profile blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP agent_profile: {e}")
    try:
        from backend.routes.agent_cron_routes import agent_cron_bp
        app.register_blueprint(agent_cron_bp)
        n += 1
        print("  [OK] Registered agent_cron blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP agent_cron: {e}")
    try:
        from backend.routes.agent_intelligence_routes import agent_intelligence_bp
        app.register_blueprint(agent_intelligence_bp)
        n += 1
        print("  [OK] Registered agent_intelligence blueprint (LITE)")
    except Exception as e:
        print(f"  [WARN] LITE_APP agent_intelligence: {e}")
    try:
        from backend.routes.agent_shop_crypto_routes import agent_shop_crypto_bp
        app.register_blueprint(agent_shop_crypto_bp)
        n += 1
        print("  [OK] Registered agent_shop_crypto blueprint (LITE)")
    except Exception as e:
        print(f"  [WARN] LITE_APP agent_shop_crypto: {e}")
    try:
        from backend.routes.communication_psychology_routes import comm_psych_bp
        app.register_blueprint(comm_psych_bp)
        n += 1
        print("  [OK] Registered communication_psychology blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP communication_psychology: {e}")
    try:
        from backend.routes.dashboard_page_routes import (
            dashboard_page_bp, profile_page_bp, stats_page_bp, social_page_bp,
            trophies_page_bp, points_page_bp, analytics_page_bp,
        )
        for bp in (dashboard_page_bp, profile_page_bp, stats_page_bp, social_page_bp,
                   trophies_page_bp, points_page_bp, analytics_page_bp):
            app.register_blueprint(bp)
        n += 7
        print("  [OK] Registered dashboard_page, profile_page, stats_page, social_page, trophies_page, points_page, analytics_page blueprints")
    except Exception as e:
        print(f"  [WARN] LITE_APP dashboard_page: {e}")
    try:
        from backend.routes.chat_routes import chat_bp
        app.register_blueprint(chat_bp)
        n += 1
        print("  [OK] Registered chat blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP chat: {e}")
    try:
        from backend.routes.ai_providers_routes import ai_providers_bp
        app.register_blueprint(ai_providers_bp)
        n += 1
        print("  [OK] Registered ai_providers blueprint (LITE)")
    except Exception as e:
        print(f"  [WARN] LITE_APP ai_providers: {e}")
    try:
        from backend.routes.quest_routes import quest_bp
        app.register_blueprint(quest_bp)
        n += 1
        print("  [OK] Registered quest blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP quest: {e}")
    try:
        from backend.routes.leaderboard_routes import leaderboard_bp
        app.register_blueprint(leaderboard_bp)
        n += 1
        print("  [OK] Registered leaderboard blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP leaderboard: {e}")
    try:
        from backend.routes.social_routes import social_bp
        app.register_blueprint(social_bp)
        n += 1
        print("  [OK] Registered social blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP social: {e}")
    try:
        from backend.routes.monitoring_routes import monitoring_bp
        app.register_blueprint(monitoring_bp)
        n += 1
        print("  [OK] Registered monitoring blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP monitoring: {e}")
    try:
        from vidgenerator.src.routes.point_calculator_routes import point_calculator_bp
        app.register_blueprint(point_calculator_bp)
        n += 1
        print("  [OK] Registered point_calculator blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP point_calculator: {e}")
    try:
        from vidgenerator.src.routes.advanced_calculator_routes import advanced_calculator_bp
        app.register_blueprint(advanced_calculator_bp)
        n += 1
        print("  [OK] Registered advanced_calculator blueprint")
    except Exception as e:
        print(f"  [WARN] LITE_APP advanced_calculator: {e}")

    # ----- Debugger / diagnostics suite -----
    # The /vidgenerator/debugger admin page calls these APIs. Without them the
    # routes are unregistered under LITE_APP, fall through to the 404 handler,
    # and surface as 500s. Keep them in LITE so the debugger is fully functional.
    import importlib as _importlib
    _debugger_blueprints = [
        ("backend.routes.debug_routes", "debug_bp"),
        ("backend.routes.api_scanner_routes", "api_scanner_bp"),
        ("backend.routes.debugger_profile_routes", "debugger_profile_bp"),
        ("backend.routes.debugger_agent_tasks_routes", "debugger_agent_tasks_bp"),
        ("backend.routes.debugger_agent_routes", "debugger_agent_bp"),
        ("backend.routes.debugger_agent_analytics_routes", "debugger_agent_analytics_bp"),
        ("backend.routes.master_fix_agent_get_routes", "master_fix_get_bp"),
        ("backend.routes.master_fix_agent_routes", "master_fix_agent_bp"),
        ("backend.routes.error_logging_routes", "error_logging_bp"),
        ("backend.routes.error_handler_status_routes", "error_handler_status_bp"),
        ("backend.routes.error_agent_tasks_routes", "error_agent_tasks_bp"),
        ("backend.routes.debugging_master_routes", "debugging_master_bp"),
        ("backend.routes.debugger_download", "debugger_download_bp"),
    ]
    for _mod_path, _bp_attr in _debugger_blueprints:
        try:
            _mod = _importlib.import_module(_mod_path)
            _bp = getattr(_mod, _bp_attr)
            if _bp.name not in app.blueprints:
                app.register_blueprint(_bp)
                n += 1
                print(f"  [OK] Registered {_bp.name} blueprint (debugger suite)")
        except Exception as e:
            print(f"  [WARN] LITE_APP debugger {_bp_attr}: {e}")

    print(f"  [LITE_APP] Registered {n} blueprints")
    return n


def register_all_blueprints(app):
    """Register all blueprints automatically. Critical blueprints first. Runs once per app."""
    # Avoid duplicate registration if this app was already fully registered (e.g. same app passed twice)
    if getattr(app, "_blueprints_full_registration_done", False):
        n = len(app.blueprints)
        print(f"  [SKIP] Blueprints already registered for this app ({n} blueprints).")
        return n

    # LITE_APP=1: register only critical + core subset (~25 blueprints); same file capabilities, faster startup (migration plan Phase 1.2)
    if os.environ.get("LITE_APP") == "1":
        register_lite_blueprints(app)
        app._blueprints_full_registration_done = True
        print(f"  [SUMMARY] LITE_APP: registered {len(app.blueprints)} blueprints")
        return len(app.blueprints)

    registered_count = 0

    # ----- CRITICAL: all_pages FIRST so /vidgenerator/generator, /profile, etc. always work -----
    try:
        if 'all_pages' not in app.blueprints:
            from backend.routes.all_page_routes import all_page_bp
            app.register_blueprint(all_page_bp)
            registered_count += 1
            print("  [OK] Registered all_page blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import all_page: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering all_page: {e}")

    try:
        if 'missing_endpoints' not in app.blueprints:
            from backend.routes.missing_endpoints_routes import missing_endpoints_bp
            app.register_blueprint(missing_endpoints_bp)
            registered_count += 1
            print("  [OK] Registered missing_endpoints blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import missing_endpoints: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering missing_endpoints: {e}")

    try:
        if 'gallery' not in app.blueprints:
            from backend.routes.gallery_routes import gallery_bp
            app.register_blueprint(gallery_bp)
            registered_count += 1
            print("  [OK] Registered gallery blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import gallery: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering gallery: {e}")

    try:
        if 'health' not in app.blueprints:
            from backend.routes.health_routes import health_bp
            app.register_blueprint(health_bp)
            registered_count += 1
            print("  [OK] Registered health blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import health: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering health: {e}")

    try:
        if 'vidgenerator_disabled' not in app.blueprints:
            from backend.routes.vidgenerator_disabled_routes import vidgenerator_disabled_bp
            app.register_blueprint(vidgenerator_disabled_bp, url_prefix="/vidgenerator/api")
            registered_count += 1
            print("  [OK] Registered vidgenerator_disabled (410 for /vidgenerator/api)")
    except ImportError as e:
        print(f"  [WARN] Could not import vidgenerator_disabled: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering vidgenerator_disabled: {e}")

    try:
        if 'api_monitor' not in app.blueprints:
            from backend.routes.api_monitor_routes import api_monitor_bp
            app.register_blueprint(api_monitor_bp)
            registered_count += 1
            print("  [OK] Registered api_monitor (GET /api/ dashboard)")
    except ImportError as e:
        print(f"  [WARN] Could not import api_monitor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering api_monitor: {e}")

    try:
        if 'generator' not in app.blueprints:
            from backend.routes.generator_routes import generator_bp
            app.register_blueprint(generator_bp)
            registered_count += 1
            print("  [OK] Registered generator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import generator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering generator: {e}")

    print("  [OK 1/4] Critical blueprints (pages, gallery, health, generator)")

    # ----- OK 2/4: Core features (game, battle, agents, points, user, compendium) -----
    # Hunters Game Routes
    try:
        from backend.routes.hunters_game import hunters_game_bp
        app.register_blueprint(hunters_game_bp)
        registered_count += 1
        print("  [OK] Registered hunters_game blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import hunters_game: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering hunters_game: {e}")

    try:
        from backend.routes.star_map_routes import star_map_bp
        app.register_blueprint(star_map_bp)
        registered_count += 1
        print("  [OK] Registered star_map blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import star_map: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering star_map: {e}")
    
    # Intelligence Aggregator Routes
    try:
        from backend.routes.intelligence_aggregator_routes import intelligence_aggregator_bp
        app.register_blueprint(intelligence_aggregator_bp)
        registered_count += 1
        print("  [OK] Registered intelligence_aggregator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import intelligence_aggregator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering intelligence_aggregator: {e}")
    
    # Battle Routes (stub implementations for Battle/Trophies pages)
    try:
        from backend.routes.battle_routes import battle_bp
        app.register_blueprint(battle_bp)
        registered_count += 1
        print("  [OK] Registered battle blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import battle: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering battle: {e}")

    try:
        from backend.routes.lab_routes import lab_bp
        app.register_blueprint(lab_bp)
        registered_count += 1
        print("  [OK] Registered lab blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import lab: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering lab: {e}")

    # Social structure (friends, crews, activity feed, challenges)
    try:
        from backend.routes.social_routes import social_bp
        app.register_blueprint(social_bp)
        registered_count += 1
        print("  [OK] Registered social blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import social: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering social: {e}")

    # Trophies Routes
    try:
        from backend.routes.trophies_routes import trophies_bp
        app.register_blueprint(trophies_bp)
        registered_count += 1
        print("  [OK] Registered trophies blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import trophies: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering trophies: {e}")

    # Game Hub (unified frontpage tabs)
    try:
        from backend.routes.game_hub_routes import game_hub_bp
        app.register_blueprint(game_hub_bp)
        registered_count += 1
        print("  [OK] Registered game_hub blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import game_hub: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering game_hub: {e}")
    
    # Debugger Builder Routes
    try:
        from backend.routes.debugger_builder import debugger_builder_bp
        app.register_blueprint(debugger_builder_bp)
        registered_count += 1
        print("  [OK] Registered debugger_builder blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import debugger_builder: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering debugger_builder: {e}")
    
    # Debugger Download Routes
    try:
        from backend.routes.debugger_download import debugger_download_bp
        app.register_blueprint(debugger_download_bp)
        registered_count += 1
        print("  [OK] Registered debugger_download blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import debugger_download: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering debugger_download: {e}")
    
    # Point Calculator Routes
    try:
        from vidgenerator.src.routes.point_calculator_routes import point_calculator_bp
        app.register_blueprint(point_calculator_bp)
        registered_count += 1
        print("  [OK] Registered point_calculator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import point_calculator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering point_calculator: {e}")
    
    # Advanced Calculator Routes
    try:
        from vidgenerator.src.routes.advanced_calculator_routes import advanced_calculator_bp
        app.register_blueprint(advanced_calculator_bp)
        registered_count += 1
        print("  [OK] Registered advanced_calculator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import advanced_calculator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering advanced_calculator: {e}")
    
    # API Scanner Routes (Debugger Tool)
    try:
        from backend.routes.api_scanner_routes import api_scanner_bp
        app.register_blueprint(api_scanner_bp)
        registered_count += 1
        print("  [OK] Registered api_scanner blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import api_scanner: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering api_scanner: {e}")
    
    # API Monitoring Agent Routes
    try:
        from backend.routes.api_monitoring_agent_routes import api_monitoring_agent_bp
        app.register_blueprint(api_monitoring_agent_bp)
        registered_count += 1
        print("  [OK] Registered api_monitoring_agent blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import api_monitoring_agent: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering api_monitoring_agent: {e}")
    
    # Agent Profile Routes (my-agents, activity-feed, tech-unlock)
    try:
        if 'agent_profile' not in app.blueprints:
            from backend.routes.agent_profile_routes import agent_profile_bp
            app.register_blueprint(agent_profile_bp)
            registered_count += 1
            print("  [OK] Registered agent_profile blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_profile: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_profile: {e}")

    # Agent cron (secured skillsets / maintenance / research — see RESEARCH_AI_SYSTEMS.md)
    try:
        if 'agent_cron' not in app.blueprints:
            from backend.routes.agent_cron_routes import agent_cron_bp
            app.register_blueprint(agent_cron_bp)
            registered_count += 1
            print("  [OK] Registered agent_cron blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_cron: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_cron: {e}")

    # Master Fix Agent Routes
    try:
        from backend.routes.master_fix_agent_routes import master_fix_agent_bp
        app.register_blueprint(master_fix_agent_bp)
        registered_count += 1
        print("  [OK] Registered master_fix_agent blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import master_fix_agent: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering master_fix_agent: {e}")
    
    # Agent Tracker Routes
    try:
        from backend.routes.agent_tracker_routes import agent_tracker_bp
        app.register_blueprint(agent_tracker_bp)
        registered_count += 1
        print("  [OK] Registered agent_tracker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_tracker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_tracker: {e}")
    
    # Agent Automation Routes
    try:
        from backend.routes.agent_automation_routes import agent_automation_bp
        app.register_blueprint(agent_automation_bp)
        registered_count += 1
        print("  [OK] Registered agent_automation blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_automation: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_automation: {e}")

    # Agent shop + MN2 (headless purchasers; AGENT_MN2_SHOP_SECRET)
    try:
        from backend.routes.agent_shop_crypto_routes import agent_shop_crypto_bp
        app.register_blueprint(agent_shop_crypto_bp)
        registered_count += 1
        print("  [OK] Registered agent_shop_crypto blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_shop_crypto: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_shop_crypto: {e}")
    
    # Agent AI Intelligence Routes
    try:
        from backend.routes.agent_ai_intelligence_routes import agent_ai_intelligence_bp
        app.register_blueprint(agent_ai_intelligence_bp)
        registered_count += 1
        print("  [OK] Registered agent_ai_intelligence blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_ai_intelligence: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_ai_intelligence: {e}")

    # Agent intelligence: router, feedback, capability map, routed chat (agent ↔ LLM)
    try:
        from backend.routes.agent_intelligence_routes import agent_intelligence_bp
        app.register_blueprint(agent_intelligence_bp)
        registered_count += 1
        print("  [OK] Registered agent_intelligence blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_intelligence: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_intelligence: {e}")
    
    # Agent Error Handler Routes
    try:
        from backend.routes.agent_error_handler_routes import agent_error_handler_bp
        app.register_blueprint(agent_error_handler_bp)
        registered_count += 1
        print("  [OK] Registered agent_error_handler blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_error_handler: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_error_handler: {e}")
    
    # Agent Python Executor Routes
    try:
        from backend.routes.agent_python_executor_routes import agent_python_executor_bp
        app.register_blueprint(agent_python_executor_bp)
        registered_count += 1
        print("  [OK] Registered agent_python_executor blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_python_executor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_python_executor: {e}")
    
    # Agent Support Routes
    try:
        from backend.routes.agent_support_routes import agent_support_bp
        app.register_blueprint(agent_support_bp)
        registered_count += 1
        print("  [OK] Registered agent_support blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_support: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_support: {e}")
    
    # Agent Research Routes
    try:
        from backend.routes.agent_research_routes import agent_research_bp
        app.register_blueprint(agent_research_bp)
        registered_count += 1
        print("  [OK] Registered agent_research blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_research: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_research: {e}")
    
    # Unified Points Trigger Routes
    try:
        from backend.routes.unified_points_trigger_routes import unified_points_trigger_bp
        app.register_blueprint(unified_points_trigger_bp)
        registered_count += 1
        print("  [OK] Registered unified_points_trigger blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import unified_points_trigger: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering unified_points_trigger: {e}")

    # Points Routes (Unified /api/points/all)
    try:
        from backend.routes.points_routes import points_bp
        app.register_blueprint(points_bp)
        registered_count += 1
        print("  [OK] Registered points blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import points: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering points: {e}")

    # MN2 (MasterNoder2) wallet: balance + deposit address (Phase 2)
    try:
        from backend.routes.mn2_routes import mn2_bp
        app.register_blueprint(mn2_bp)
        registered_count += 1
        print("  [OK] Registered mn2 blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import mn2: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering mn2: {e}")
    try:
        from backend.routes.ops_stream_routes import ops_stream_bp
        if "ops_stream" not in app.blueprints:
            app.register_blueprint(ops_stream_bp)
            registered_count += 1
            print("  [OK] Registered ops_stream blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import ops_stream: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering ops_stream: {e}")
    try:
        from backend.routes.mn2_staking_routes import mn2_staking_bp
        if 'mn2_staking' not in app.blueprints:
            app.register_blueprint(mn2_staking_bp)
            registered_count += 1
            print("  [OK] Registered mn2_staking blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import mn2_staking: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering mn2_staking: {e}")
    try:
        from backend.routes.agent_staking_routes import agent_staking_bp
        if 'agent_staking' not in app.blueprints:
            app.register_blueprint(agent_staking_bp)
            registered_count += 1
            print("  [OK] Registered agent_staking blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_staking: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_staking: {e}")
    try:
        from backend.routes.agent_casino_routes import agent_casino_bp
        if 'agent_casino' not in app.blueprints:
            app.register_blueprint(agent_casino_bp)
            registered_count += 1
            print("  [OK] Registered agent_casino blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_casino: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_casino: {e}")
    try:
        from backend.routes.mn2_onramp_routes import mn2_onramp_bp
        if 'mn2_onramp' not in app.blueprints:
            app.register_blueprint(mn2_onramp_bp)
            registered_count += 1
            print("  [OK] Registered mn2_onramp blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import mn2_onramp: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering mn2_onramp: {e}")
    try:
        from backend.routes.mn2_p2p_routes import mn2_p2p_bp
        if 'mn2_p2p' not in app.blueprints:
            app.register_blueprint(mn2_p2p_bp)
            registered_count += 1
            print("  [OK] Registered mn2_p2p blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import mn2_p2p: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering mn2_p2p: {e}")
    try:
        from backend.routes.mn2_masternode_routes import mn2_masternode_bp
        if 'mn2_masternode' not in app.blueprints:
            app.register_blueprint(mn2_masternode_bp)
            registered_count += 1
            print("  [OK] Registered mn2_masternode blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import mn2_masternode: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering mn2_masternode: {e}")

    # PTC ads + traffic rotator (internal rewards first; advertiser packages later)
    try:
        from backend.routes.ptc_ads_routes import ptc_ads_bp
        app.register_blueprint(ptc_ads_bp)
        registered_count += 1
        print("  [OK] Registered ptc_ads blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import ptc_ads: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering ptc_ads: {e}")

    # Virtual-coins casino (cosmetic betting only)
    try:
        from backend.routes.casino_routes import casino_bp
        app.register_blueprint(casino_bp)
        registered_count += 1
        print("  [OK] Registered casino blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import casino: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering casino: {e}")

    # PayPal (real-money payments — add PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET to .env)
    try:
        from backend.routes.paypal_routes import paypal_bp
        app.register_blueprint(paypal_bp)
        registered_count += 1
        print("  [OK] Registered paypal blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import paypal: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering paypal: {e}")

    # DNA Monster Calendar Routes (DNA manipulation / cloning)
    try:
        from backend.routes.dna_monster_calendar_routes import dna_monster_calendar_bp
        app.register_blueprint(dna_monster_calendar_bp)
        registered_count += 1
        print("  [OK] Registered dna_monster_calendar blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import dna_monster_calendar: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering dna_monster_calendar: {e}")

    # Communication Psychology (25 theories, starmap, profile, trophies, shop)
    try:
        from backend.routes.communication_psychology_routes import comm_psych_bp
        app.register_blueprint(comm_psych_bp)
        registered_count += 1
        print("  [OK] Registered communication_psychology blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import communication_psychology: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering communication_psychology: {e}")

    # Compendium (Rulebook V2.1 — 10 wiki pages, compendium_points)
    try:
        from backend.routes.compendium_routes import compendium_bp
        app.register_blueprint(compendium_bp)
        from backend.routes.rulebook_routes import rulebook_bp
        app.register_blueprint(rulebook_bp)
        registered_count += 1
        print("  [OK] Registered compendium blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import compendium: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering compendium: {e}")

    # User account (user index and ID for generation and account control)
    try:
        from backend.routes.user_account_routes import user_account_bp
        app.register_blueprint(user_account_bp)
        registered_count += 1
        print("  [OK] Registered user_account blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import user_account: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering user_account: {e}")
    
    # New Agents Routes
    try:
        from backend.routes.new_agents_routes import new_agents_bp
        app.register_blueprint(new_agents_bp)
        registered_count += 1
        print("  [OK] Registered new_agents blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import new_agents: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering new_agents: {e}")
    
    # Agent Controller Routes
    try:
        from backend.routes.agent_controller_routes import agent_controller_bp
        app.register_blueprint(agent_controller_bp)
        registered_count += 1
        print("  [OK] Registered agent_controller blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_controller: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_controller: {e}")
    
    # Manager and Secretary Routes
    try:
        from backend.routes.manager_secretary_routes import manager_secretary_bp
        app.register_blueprint(manager_secretary_bp)
        registered_count += 1
        print("  [OK] Registered manager_secretary blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import manager_secretary: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering manager_secretary: {e}")
    
    # Enhanced Tracker Routes
    try:
        from backend.routes.enhanced_tracker_routes import enhanced_tracker_bp
        app.register_blueprint(enhanced_tracker_bp)
        registered_count += 1
        print("  [OK] Registered enhanced_tracker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import enhanced_tracker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering enhanced_tracker: {e}")
    
    # Agent Judge Routes
    try:
        from backend.routes.agent_judge_routes import agent_judge_bp
        app.register_blueprint(agent_judge_bp)
        registered_count += 1
        print("  [OK] Registered agent_judge blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_judge: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_judge: {e}")
    
    # Agent Point Creator Routes
    try:
        from backend.routes.agent_point_creator_routes import agent_point_creator_bp
        app.register_blueprint(agent_point_creator_bp)
        registered_count += 1
        print("  [OK] Registered agent_point_creator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_point_creator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_point_creator: {e}")
    
    # User Profile Routes
    try:
        from backend.routes.user_profile_routes import user_profile_bp
        app.register_blueprint(user_profile_bp)
        registered_count += 1
        print("  [OK] Registered user_profile blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import user_profile: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering user_profile: {e}")

    print("  [OK 2/4] Core features (game, battle, agents, points, paypal, user, compendium)")
    
    # ----- OK 3/4: Monitoring, error, debug, dashboard, shop, auth -----
    # Monitoring Routes
    try:
        from backend.routes.monitoring_routes import monitoring_bp
        app.register_blueprint(monitoring_bp)
        registered_count += 1
        print("  [OK] Registered monitoring blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import monitoring: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering monitoring: {e}")
    
    # Auto-Fix Routes
    try:
        from backend.routes.auto_fix_routes import auto_fix_bp
        app.register_blueprint(auto_fix_bp)
        registered_count += 1
        print("  [OK] Registered auto_fix blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import auto_fix: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering auto_fix: {e}")
    
    # Error Logging Routes
    try:
        from backend.routes.error_logging_routes import error_logging_bp
        if 'error_logging' not in app.blueprints:
            app.register_blueprint(error_logging_bp)
            registered_count += 1
            print("  [OK] Registered error_logging blueprint")
        else:
            print("  [SKIP] error_logging blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import error_logging: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering error_logging: {e}")
    
    # Error Handler Status Routes
    try:
        from backend.routes.error_handler_status_routes import error_handler_status_bp
        if 'error_handler_status' not in app.blueprints:
            app.register_blueprint(error_handler_status_bp)
            registered_count += 1
            print("  [OK] Registered error_handler_status blueprint")
        else:
            print("  [SKIP] error_handler_status blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import error_handler_status: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering error_handler_status: {e}")
    
    # Error Agent Tasks Routes
    try:
        from backend.routes.error_agent_tasks_routes import error_agent_tasks_bp
        if 'error_agent_tasks' not in app.blueprints:
            app.register_blueprint(error_agent_tasks_bp)
            registered_count += 1
            print("  [OK] Registered error_agent_tasks blueprint")
        else:
            print("  [SKIP] error_agent_tasks blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import error_agent_tasks: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering error_agent_tasks: {e}")
    
    # Debugger Agent Tasks Routes
    try:
        from backend.routes.debugger_agent_tasks_routes import debugger_agent_tasks_bp
        if 'debugger_agent_tasks' not in app.blueprints:
            app.register_blueprint(debugger_agent_tasks_bp)
            registered_count += 1
            print("  [OK] Registered debugger_agent_tasks blueprint")
        else:
            print("  [SKIP] debugger_agent_tasks blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import debugger_agent_tasks: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering debugger_agent_tasks: {e}")
    
    # Agent Reengineering Routes
    try:
        from backend.routes.agent_reengineering_routes import agent_reengineering_bp
        if 'agent_reengineering' not in app.blueprints:
            app.register_blueprint(agent_reengineering_bp)
            registered_count += 1
            print("  [OK] Registered agent_reengineering blueprint")
        else:
            print("  [SKIP] agent_reengineering blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_reengineering: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_reengineering: {e}")
    
    # Signal Collector Routes
    try:
        from backend.routes.signal_collector_routes import signal_collector_bp
        if 'signal_collector' not in app.blueprints:
            app.register_blueprint(signal_collector_bp)
            registered_count += 1
            print("  [OK] Registered signal_collector blueprint")
        else:
            print("  [SKIP] signal_collector blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import signal_collector: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering signal_collector: {e}")
    
    # Path Corrector Routes
    try:
        from backend.routes.path_corrector_routes import path_corrector_bp
        if 'path_corrector' not in app.blueprints:
            app.register_blueprint(path_corrector_bp)
            registered_count += 1
            print("  [OK] Registered path_corrector blueprint")
        else:
            print("  [SKIP] path_corrector blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import path_corrector: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering path_corrector: {e}")
    
    # Debugging Master Routes - THE AUTHORITY
    try:
        from backend.routes.debugging_master_routes import debugging_master_bp
        if 'debugging_master' not in app.blueprints:
            app.register_blueprint(debugging_master_bp)
            registered_count += 1
            print("  [OK] Registered debugging_master blueprint - THE AUTHORITY")
        else:
            print("  [SKIP] debugging_master blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import debugging_master: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering debugging_master: {e}")
    
    # AI-Enhanced Routes
    try:
        from backend.routes.ai_enhanced_routes import ai_enhanced_bp
        if 'ai_enhanced' not in app.blueprints:
            app.register_blueprint(ai_enhanced_bp)
            registered_count += 1
            print("  [OK] Registered ai_enhanced blueprint - AI POWERED")
        else:
            print("  [SKIP] ai_enhanced blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import ai_enhanced: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering ai_enhanced: {e}")
    
    # AI Agent Routes
    try:
        from backend.routes.ai_agent_routes import ai_agent_bp
        if 'ai_agent' not in app.blueprints:
            app.register_blueprint(ai_agent_bp)
            registered_count += 1
            print("  [OK] Registered ai_agent blueprint - NEW AI AGENT CLASS")
        else:
            print("  [SKIP] ai_agent blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import ai_agent: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering ai_agent: {e}")
    
    # AI Skill Routes
    try:
        from backend.routes.ai_skill_routes import ai_skill_bp
        if 'ai_skill' not in app.blueprints:
            app.register_blueprint(ai_skill_bp)
            registered_count += 1
            print("  [OK] Registered ai_skill blueprint - ALL SKILLS IMPLEMENTED")
        else:
            print("  [SKIP] ai_skill blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import ai_skill: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering ai_skill: {e}")
    
    # CEO Agent Routes
    try:
        from backend.routes.ceo_agent_routes import ceo_agent_bp
        if 'ceo_agent' not in app.blueprints:
            app.register_blueprint(ceo_agent_bp)
            registered_count += 1
            print("  [OK] Registered ceo_agent blueprint - EXECUTIVE CAPABILITIES")
        else:
            print("  [SKIP] ceo_agent blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import ceo_agent: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering ceo_agent: {e}")
    
    # Debug Routes
    try:
        from backend.routes.debug_routes import debug_bp
        if 'debug' not in app.blueprints:
            app.register_blueprint(debug_bp)
            registered_count += 1
            print("  [OK] Registered debug blueprint")
        else:
            print("  [SKIP] debug blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import debug: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering debug: {e}")
    
    # Debugger Profile Routes
    try:
        from backend.routes.debugger_profile_routes import debugger_profile_bp
        if 'debugger_profile' not in app.blueprints:
            app.register_blueprint(debugger_profile_bp)
            registered_count += 1
            print("  [OK] Registered debugger_profile blueprint")
        else:
            print("  [SKIP] debugger_profile blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import debugger_profile: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering debugger_profile: {e}")
    
    # Debugger Agent Routes
    try:
        from backend.routes.debugger_agent_routes import debugger_agent_bp
        if 'debugger_agent' not in app.blueprints:
            app.register_blueprint(debugger_agent_bp)
            registered_count += 1
            print("  [OK] Registered debugger_agent blueprint")
        else:
            print("  [SKIP] debugger_agent blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import debugger_agent: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering debugger_agent: {e}")
    
    # Master Fix Agent Get Routes
    try:
        from backend.routes.master_fix_agent_get_routes import master_fix_get_bp
        if 'master_fix_get' not in app.blueprints:
            app.register_blueprint(master_fix_get_bp)
            registered_count += 1
            print("  [OK] Registered master_fix_get blueprint")
        else:
            print("  [SKIP] master_fix_get blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import master_fix_get: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering master_fix_get: {e}")
    
    # Debugger Agent Analytics Routes
    try:
        from backend.routes.debugger_agent_analytics_routes import debugger_agent_analytics_bp
        if 'debugger_agent_analytics' not in app.blueprints:
            app.register_blueprint(debugger_agent_analytics_bp)
            registered_count += 1
            print("  [OK] Registered debugger_agent_analytics blueprint")
        else:
            print("  [SKIP] debugger_agent_analytics blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import debugger_agent_analytics: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering debugger_agent_analytics: {e}")
    
    # Master Dashboard Routes
    try:
        from backend.routes.master_dashboard_routes import master_dashboard_bp
        if 'master_dashboard' not in app.blueprints:
            app.register_blueprint(master_dashboard_bp)
            registered_count += 1
            print("  [OK] Registered master_dashboard blueprint")
        else:
            print("  [SKIP] master_dashboard blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import master_dashboard: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering master_dashboard: {e}")
    
    # AI Intelligence Dashboard Routes
    try:
        from backend.routes.ai_intelligence_dashboard_routes import ai_intelligence_dashboard_bp
        if 'ai_intelligence_dashboard' not in app.blueprints:
            app.register_blueprint(ai_intelligence_dashboard_bp)
            registered_count += 1
            print("  [OK] Registered ai_intelligence_dashboard blueprint")
        else:
            print("  [SKIP] ai_intelligence_dashboard blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import ai_intelligence_dashboard: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering ai_intelligence_dashboard: {e}")
    
    # The End War Movie Routes
    try:
        from backend.routes.the_end_war_movie_routes import the_end_war_bp
        if 'the_end_war' not in app.blueprints:
            app.register_blueprint(the_end_war_bp)
            registered_count += 1
            print("  [OK] Registered the_end_war blueprint")
        else:
            print("  [SKIP] the_end_war blueprint already registered")
    except ImportError as e:
        print(f"  [WARN] Could not import the_end_war: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering the_end_war: {e}")
    
    # User Identification Routes
    try:
        from backend.routes.user_identification_routes import user_identification_bp
        app.register_blueprint(user_identification_bp)
        registered_count += 1
        print("  [OK] Registered user_identification blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import user_identification: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering user_identification: {e}")
    
    # Dashboard Page Routes
    try:
        from backend.routes.dashboard_page_routes import dashboard_page_bp, profile_page_bp, stats_page_bp, social_page_bp, trophies_page_bp, points_page_bp, analytics_page_bp
        app.register_blueprint(dashboard_page_bp)
        app.register_blueprint(profile_page_bp)
        app.register_blueprint(stats_page_bp)
        app.register_blueprint(social_page_bp)
        app.register_blueprint(trophies_page_bp)
        app.register_blueprint(points_page_bp)
        app.register_blueprint(analytics_page_bp)
        registered_count += 7
        print("  [OK] Registered dashboard_page, profile_page, stats_page, social_page, trophies_page, points_page, and analytics_page blueprints")
    except ImportError as e:
        print(f"  [WARN] Could not import dashboard_page: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering dashboard_page: {e}")
    
    # Shop Routes
    try:
        from backend.routes.shop_routes import shop_bp
        app.register_blueprint(shop_bp)
        registered_count += 1
        print("  [OK] Registered shop blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import shop: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering shop: {e}")

    # Shop V9.2 Monetization Routes (VIP, mystery boxes, spin, flash sales, gifting, loyalty)
    try:
        from backend.routes.shop_monetization_routes import shop_monetization_bp
        app.register_blueprint(shop_monetization_bp)
        registered_count += 1
        print("  [OK] Registered shop_monetization blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import shop_monetization: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering shop_monetization: {e}")

    # Social Auth Routes
    try:
        from backend.routes.social_auth_routes import social_auth_bp
        app.register_blueprint(social_auth_bp)
        registered_count += 1
        print("  [OK] Registered social_auth blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import social_auth: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering social_auth: {e}")

    try:
        from backend.routes.password_protection_routes import password_protection_bp
        app.register_blueprint(password_protection_bp)
        registered_count += 1
        print("  [OK] Registered password_protection blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import password_protection: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering password_protection: {e}")

    try:
        from backend.routes.platform_news_routes import platform_news_bp
        app.register_blueprint(platform_news_bp)
        registered_count += 1
        print("  [OK] Registered platform_news blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import platform_news: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering platform_news: {e}")

    try:
        from backend.routes.discord_routes import discord_bp
        if "discord" not in app.blueprints:
            app.register_blueprint(discord_bp)
            registered_count += 1
            print("  [OK] Registered discord blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import discord: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering discord: {e}")

    try:
        from backend.routes.customer_aggregator_routes import customer_aggregator_bp
        if "customer_aggregator" not in app.blueprints:
            app.register_blueprint(customer_aggregator_bp)
            registered_count += 1
            print("  [OK] Registered customer_aggregator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import customer_aggregator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering customer_aggregator: {e}")

    try:
        from backend.routes.agent_treasury_routes import agent_treasury_bp
        if "agent_treasury" not in app.blueprints:
            app.register_blueprint(agent_treasury_bp)
            registered_count += 1
            print("  [OK] Registered agent_treasury blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_treasury: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_treasury: {e}")

    try:
        from backend.routes.agent_trader_staking_routes import agent_trader_staking_bp
        if "agent_trader_staking" not in app.blueprints:
            app.register_blueprint(agent_trader_staking_bp)
            registered_count += 1
            print("  [OK] Registered agent_trader_staking blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_trader_staking: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_trader_staking: {e}")

    try:
        from backend.routes.camgirls_routes import camgirls_bp
        if "camgirls" not in app.blueprints:
            app.register_blueprint(camgirls_bp)
            registered_count += 1
            print("  [OK] Registered camgirls blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import camgirls: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering camgirls: {e}")

    try:
        from backend.routes.security_cron_routes import security_cron_bp
        if "security_cron" not in app.blueprints:
            app.register_blueprint(security_cron_bp)
            registered_count += 1
            print("  [OK] Registered security_cron blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import security_cron: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering security_cron: {e}")

    try:
        from backend.routes.p2p_market_routes import p2p_market_bp
        if "p2p_market" not in app.blueprints:
            app.register_blueprint(p2p_market_bp)
            registered_count += 1
            print("  [OK] Registered p2p_market blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import p2p_market: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering p2p_market: {e}")

    try:
        from backend.routes.debugger_quiz_routes import debugger_quiz_bp
        if "debugger_quiz" not in app.blueprints:
            app.register_blueprint(debugger_quiz_bp)
            registered_count += 1
            print("  [OK] Registered debugger_quiz blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import debugger_quiz: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering debugger_quiz: {e}")

    try:
        from backend.routes.point_control_board_routes import point_control_board_bp
        if "point_control_board" not in app.blueprints:
            app.register_blueprint(point_control_board_bp)
            registered_count += 1
            print("  [OK] Registered point_control_board blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import point_control_board: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering point_control_board: {e}")

    try:
        from backend.routes.agent_admin_routes import agent_admin_bp
        if "agent_admin" not in app.blueprints:
            app.register_blueprint(agent_admin_bp)
            registered_count += 1
            print("  [OK] Registered agent_admin blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_admin: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_admin: {e}")

    try:
        from backend.routes.account_security_routes import account_security_bp
        app.register_blueprint(account_security_bp)
        registered_count += 1
        print("  [OK] Registered account_security blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import account_security: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering account_security: {e}")

    print("  [OK 3/4] Monitoring, debug, dashboard, shop, auth")

    # ----- OK 4/4: Agent technologies, chat, quest, leaderboard -----
    # ========== 50 AGENT TECHNOLOGIES ==========
    try:
        from backend.routes.agent_activity_tracker_routes import agent_activity_tracker_bp
        app.register_blueprint(agent_activity_tracker_bp)
        registered_count += 1
        print("  [OK] Registered agent_activity_tracker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_activity_tracker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_activity_tracker: {e}")
    
    try:
        from backend.routes.agent_adaptive_learner_routes import agent_adaptive_learner_bp
        app.register_blueprint(agent_adaptive_learner_bp)
        registered_count += 1
        print("  [OK] Registered agent_adaptive_learner blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_adaptive_learner: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_adaptive_learner: {e}")
    
    try:
        from backend.routes.agent_alert_monitor_routes import agent_alert_monitor_bp
        app.register_blueprint(agent_alert_monitor_bp)
        registered_count += 1
        print("  [OK] Registered agent_alert_monitor blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_alert_monitor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_alert_monitor: {e}")
    
    try:
        from backend.routes.agent_anomaly_detector_routes import agent_anomaly_detector_bp
        app.register_blueprint(agent_anomaly_detector_bp)
        registered_count += 1
        print("  [OK] Registered agent_anomaly_detector blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_anomaly_detector: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_anomaly_detector: {e}")
    
    try:
        from backend.routes.agent_api_gateway_routes import agent_api_gateway_bp
        app.register_blueprint(agent_api_gateway_bp)
        registered_count += 1
        print("  [OK] Registered agent_api_gateway blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_api_gateway: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_api_gateway: {e}")
    
    try:
        from backend.routes.agent_auto_scaler_routes import agent_auto_scaler_bp
        app.register_blueprint(agent_auto_scaler_bp)
        registered_count += 1
        print("  [OK] Registered agent_auto_scaler blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_auto_scaler: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_auto_scaler: {e}")
    
    try:
        from backend.routes.agent_behavior_tracker_routes import agent_behavior_tracker_bp
        app.register_blueprint(agent_behavior_tracker_bp)
        registered_count += 1
        print("  [OK] Registered agent_behavior_tracker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_behavior_tracker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_behavior_tracker: {e}")
    
    try:
        from backend.routes.agent_blockchain_ledger_routes import agent_blockchain_ledger_bp
        app.register_blueprint(agent_blockchain_ledger_bp)
        registered_count += 1
        print("  [OK] Registered agent_blockchain_ledger blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_blockchain_ledger: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_blockchain_ledger: {e}")
    
    try:
        from backend.routes.agent_cloud_sync_routes import agent_cloud_sync_bp
        app.register_blueprint(agent_cloud_sync_bp)
        registered_count += 1
        print("  [OK] Registered agent_cloud_sync blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_cloud_sync: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_cloud_sync: {e}")
    
    try:
        from backend.routes.agent_code_analyzer_routes import agent_code_analyzer_bp
        app.register_blueprint(agent_code_analyzer_bp)
        registered_count += 1
        print("  [OK] Registered agent_code_analyzer blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_code_analyzer: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_code_analyzer: {e}")
    
    try:
        from backend.routes.agent_code_formatter_routes import agent_code_formatter_bp
        app.register_blueprint(agent_code_formatter_bp)
        registered_count += 1
        print("  [OK] Registered agent_code_formatter blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_code_formatter: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_code_formatter: {e}")
    
    try:
        from backend.routes.agent_config_scanner_routes import agent_config_scanner_bp
        app.register_blueprint(agent_config_scanner_bp)
        registered_count += 1
        print("  [OK] Registered agent_config_scanner blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_config_scanner: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_config_scanner: {e}")
    
    try:
        from backend.routes.agent_container_orchestrator_routes import agent_container_orchestrator_bp
        app.register_blueprint(agent_container_orchestrator_bp)
        registered_count += 1
        print("  [OK] Registered agent_container_orchestrator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_container_orchestrator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_container_orchestrator: {e}")
    
    try:
        from backend.routes.agent_database_scanner_routes import agent_database_scanner_bp
        app.register_blueprint(agent_database_scanner_bp)
        registered_count += 1
        print("  [OK] Registered agent_database_scanner blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_database_scanner: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_database_scanner: {e}")
    
    try:
        from backend.routes.agent_decision_maker_routes import agent_decision_maker_bp
        app.register_blueprint(agent_decision_maker_bp)
        registered_count += 1
        print("  [OK] Registered agent_decision_maker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_decision_maker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_decision_maker: {e}")
    
    try:
        from backend.routes.agent_dependency_checker_routes import agent_dependency_checker_bp
        app.register_blueprint(agent_dependency_checker_bp)
        registered_count += 1
        print("  [OK] Registered agent_dependency_checker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_dependency_checker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_dependency_checker: {e}")
    
    try:
        from backend.routes.agent_distributed_cache_routes import agent_distributed_cache_bp
        app.register_blueprint(agent_distributed_cache_bp)
        registered_count += 1
        print("  [OK] Registered agent_distributed_cache blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_distributed_cache: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_distributed_cache: {e}")
    
    try:
        from backend.routes.agent_documentation_generator_routes import agent_documentation_generator_bp
        app.register_blueprint(agent_documentation_generator_bp)
        registered_count += 1
        print("  [OK] Registered agent_documentation_generator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_documentation_generator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_documentation_generator: {e}")
    
    try:
        from backend.routes.agent_endpoint_scanner_routes import agent_endpoint_scanner_bp
        app.register_blueprint(agent_endpoint_scanner_bp)
        registered_count += 1
        print("  [OK] Registered agent_endpoint_scanner blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_endpoint_scanner: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_endpoint_scanner: {e}")
    
    try:
        from backend.routes.agent_error_tracker_routes import agent_error_tracker_bp
        app.register_blueprint(agent_error_tracker_bp)
        registered_count += 1
        print("  [OK] Registered agent_error_tracker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_error_tracker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_error_tracker: {e}")
    
    try:
        from backend.routes.agent_event_driven_processor_routes import agent_event_driven_processor_bp
        app.register_blueprint(agent_event_driven_processor_bp)
        registered_count += 1
        print("  [OK] Registered agent_event_driven_processor blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_event_driven_processor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_event_driven_processor: {e}")

    try:
        from backend.routes.agent_electric_magnet_routes import agent_electric_magnet_bp
        app.register_blueprint(agent_electric_magnet_bp)
        registered_count += 1
        print("  [OK] Registered agent_electric_magnet blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_electric_magnet: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_electric_magnet: {e}")
    
    try:
        from backend.routes.agent_event_tracker_routes import agent_event_tracker_bp
        app.register_blueprint(agent_event_tracker_bp)
        registered_count += 1
        print("  [OK] Registered agent_event_tracker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_event_tracker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_event_tracker: {e}")
    
    try:
        from backend.routes.agent_file_scanner_routes import agent_file_scanner_bp
        app.register_blueprint(agent_file_scanner_bp)
        registered_count += 1
        print("  [OK] Registered agent_file_scanner blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_file_scanner: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_file_scanner: {e}")
    
    try:
        from backend.routes.agent_geofence_manager_routes import agent_geofence_manager_bp
        app.register_blueprint(agent_geofence_manager_bp)
        registered_count += 1
        print("  [OK] Registered agent_geofence_manager blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_geofence_manager: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_geofence_manager: {e}")
    
    try:
        from backend.routes.agent_gps_coordinator_routes import agent_gps_coordinator_bp
        app.register_blueprint(agent_gps_coordinator_bp)
        registered_count += 1
        print("  [OK] Registered agent_gps_coordinator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_gps_coordinator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_gps_coordinator: {e}")
    
    try:
        from backend.routes.agent_health_monitor_routes import agent_health_monitor_bp
        app.register_blueprint(agent_health_monitor_bp)
        registered_count += 1
        print("  [OK] Registered agent_health_monitor blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_health_monitor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_health_monitor: {e}")
    
    try:
        from backend.routes.agent_load_balancer_routes import agent_load_balancer_bp
        app.register_blueprint(agent_load_balancer_bp)
        registered_count += 1
        print("  [OK] Registered agent_load_balancer blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_load_balancer: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_load_balancer: {e}")
    
    try:
        from backend.routes.agent_location_tracker_routes import agent_location_tracker_bp
        app.register_blueprint(agent_location_tracker_bp)
        registered_count += 1
        print("  [OK] Registered agent_location_tracker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_location_tracker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_location_tracker: {e}")
    
    try:
        from backend.routes.agent_log_analyzer_routes import agent_log_analyzer_bp
        app.register_blueprint(agent_log_analyzer_bp)
        registered_count += 1
        print("  [OK] Registered agent_log_analyzer blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_log_analyzer: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_log_analyzer: {e}")
    
    try:
        from backend.routes.agent_memory_debugger_routes import agent_memory_debugger_bp
        app.register_blueprint(agent_memory_debugger_bp)
        registered_count += 1
        print("  [OK] Registered agent_memory_debugger blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_memory_debugger: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_memory_debugger: {e}")
    
    try:
        from backend.routes.agent_metric_monitor_routes import agent_metric_monitor_bp
        app.register_blueprint(agent_metric_monitor_bp)
        registered_count += 1
        print("  [OK] Registered agent_metric_monitor blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_metric_monitor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_metric_monitor: {e}")
    
    try:
        from backend.routes.agent_metric_tracker_routes import agent_metric_tracker_bp
        app.register_blueprint(agent_metric_tracker_bp)
        registered_count += 1
        print("  [OK] Registered agent_metric_tracker blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_metric_tracker: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_metric_tracker: {e}")
    
    try:
        from backend.routes.agent_microservices_routes import agent_microservices_bp
        app.register_blueprint(agent_microservices_bp)
        registered_count += 1
        print("  [OK] Registered agent_microservices blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_microservices: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_microservices: {e}")
    
    try:
        from backend.routes.agent_ml_predictor_routes import agent_ml_predictor_bp
        app.register_blueprint(agent_ml_predictor_bp)
        registered_count += 1
        print("  [OK] Registered agent_ml_predictor blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_ml_predictor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_ml_predictor: {e}")
    
    try:
        from backend.routes.agent_navigation_system_routes import agent_navigation_system_bp
        app.register_blueprint(agent_navigation_system_bp)
        registered_count += 1
        print("  [OK] Registered agent_navigation_system blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_navigation_system: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_navigation_system: {e}")
    
    try:
        from backend.routes.agent_network_scanner_routes import agent_network_scanner_bp
        app.register_blueprint(agent_network_scanner_bp)
        registered_count += 1
        print("  [OK] Registered agent_network_scanner blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_network_scanner: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_network_scanner: {e}")
    
    try:
        from backend.routes.agent_neural_network_routes import agent_neural_network_bp
        app.register_blueprint(agent_neural_network_bp)
        registered_count += 1
        print("  [OK] Registered agent_neural_network blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_neural_network: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_neural_network: {e}")
    
    try:
        from backend.routes.agent_optimization_engine_routes import agent_optimization_engine_bp
        app.register_blueprint(agent_optimization_engine_bp)
        registered_count += 1
        print("  [OK] Registered agent_optimization_engine blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_optimization_engine: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_optimization_engine: {e}")
    
    try:
        from backend.routes.agent_pattern_matcher_routes import agent_pattern_matcher_bp
        app.register_blueprint(agent_pattern_matcher_bp)
        registered_count += 1
        print("  [OK] Registered agent_pattern_matcher blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_pattern_matcher: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_pattern_matcher: {e}")
    
    try:
        from backend.routes.agent_performance_profiler_routes import agent_performance_profiler_bp
        app.register_blueprint(agent_performance_profiler_bp)
        registered_count += 1
        print("  [OK] Registered agent_performance_profiler blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_performance_profiler: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_performance_profiler: {e}")
    
    try:
        from backend.routes.agent_quantum_processor_routes import agent_quantum_processor_bp
        app.register_blueprint(agent_quantum_processor_bp)
        registered_count += 1
        print("  [OK] Registered agent_quantum_processor blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_quantum_processor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_quantum_processor: {e}")
    
    try:
        from backend.routes.agent_resource_monitor_routes import agent_resource_monitor_bp
        app.register_blueprint(agent_resource_monitor_bp)
        registered_count += 1
        print("  [OK] Registered agent_resource_monitor blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_resource_monitor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_resource_monitor: {e}")
    
    try:
        from backend.routes.agent_route_optimizer_routes import agent_route_optimizer_bp
        app.register_blueprint(agent_route_optimizer_bp)
        registered_count += 1
        print("  [OK] Registered agent_route_optimizer blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_route_optimizer: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_route_optimizer: {e}")
    
    try:
        from backend.routes.agent_security_scanner_routes import agent_security_scanner_bp
        app.register_blueprint(agent_security_scanner_bp)
        registered_count += 1
        print("  [OK] Registered agent_security_scanner blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_security_scanner: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_security_scanner: {e}")
    
    try:
        from backend.routes.agent_self_healer_routes import agent_self_healer_bp
        app.register_blueprint(agent_self_healer_bp)
        registered_count += 1
        print("  [OK] Registered agent_self_healer blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_self_healer: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_self_healer: {e}")
    
    try:
        from backend.routes.agent_service_mesh_routes import agent_service_mesh_bp
        app.register_blueprint(agent_service_mesh_bp)
        registered_count += 1
        print("  [OK] Registered agent_service_mesh blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_service_mesh: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_service_mesh: {e}")
    
    try:
        from backend.routes.agent_test_generator_routes import agent_test_generator_bp
        app.register_blueprint(agent_test_generator_bp)
        registered_count += 1
        print("  [OK] Registered agent_test_generator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_test_generator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_test_generator: {e}")
    
    try:
        from backend.routes.agent_uptime_monitor_routes import agent_uptime_monitor_bp
        app.register_blueprint(agent_uptime_monitor_bp)
        registered_count += 1
        print("  [OK] Registered agent_uptime_monitor blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_uptime_monitor: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_uptime_monitor: {e}")
    
    try:
        from backend.routes.agent_vulnerability_scanner_routes import agent_vulnerability_scanner_bp
        app.register_blueprint(agent_vulnerability_scanner_bp)
        registered_count += 1
        print("  [OK] Registered agent_vulnerability_scanner blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_vulnerability_scanner: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_vulnerability_scanner: {e}")
    
    try:
        from backend.routes.agent_workflow_orchestrator_routes import agent_workflow_orchestrator_bp
        app.register_blueprint(agent_workflow_orchestrator_bp)
        registered_count += 1
        print("  [OK] Registered agent_workflow_orchestrator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_workflow_orchestrator: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_workflow_orchestrator: {e}")
    
# Agent Behavior Routes
    try:
        from backend.routes.agent_behavior_routes import agent_behavior_bp
        app.register_blueprint(agent_behavior_bp)
        registered_count += 1
        print("  [OK] Registered agent_behavior blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import agent_behavior: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering agent_behavior: {e}")
    
    # Chat Routes (AI-powered)
    try:
        from backend.routes.chat_routes import chat_bp
        app.register_blueprint(chat_bp)
        registered_count += 1
        print("  [OK] Registered chat blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import chat: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering chat: {e}")

    # AI Providers Routes (multi-provider status, test, reset, chat)
    try:
        from backend.routes.ai_providers_routes import ai_providers_bp
        app.register_blueprint(ai_providers_bp)
        registered_count += 1
        print("  [OK] Registered ai_providers blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import ai_providers: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering ai_providers: {e}")

    # COGS / reference job (Runway, encode, storage, LLM blend — GET only)
    try:
        from backend.routes.cogs_routes import cogs_bp
        if "cogs" not in app.blueprints:
            app.register_blueprint(cogs_bp)
            registered_count += 1
            print("  [OK] Registered cogs blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import cogs: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering cogs: {e}")

    try:
        from backend.routes.monetization_expansion_routes import monetization_expansion_bp
        if "monetization_expansion" not in app.blueprints:
            app.register_blueprint(monetization_expansion_bp)
            registered_count += 1
            print("  [OK] Registered monetization_expansion blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import monetization_expansion: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering monetization_expansion: {e}")

    # Quest Routes (AI-generated daily + personal quests)
    try:
        from backend.routes.quest_routes import quest_bp
        app.register_blueprint(quest_bp)
        registered_count += 1
        print("  [OK] Registered quest blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import quest: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering quest: {e}")

    # Leaderboard Routes (AI insights, rivalries, rankings)
    try:
        from backend.routes.leaderboard_routes import leaderboard_bp
        app.register_blueprint(leaderboard_bp)
        registered_count += 1
        print("  [OK] Registered leaderboard blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import leaderboard: {e}")
    except Exception as e:
        print(f"  [ERROR] Error registering leaderboard: {e}")

    print("  [OK 4/4] Agent technologies, chat, quest, leaderboard")

    # Register Intelligence: discover and register any blueprints not yet registered
    try:
        from backend.services.register_intelligence.route_discovery import discover_blueprints
        for b in discover_blueprints(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
            if b["bp_name"] not in app.blueprints:
                try:
                    parts = b["module_path"].split(".")
                    mod = __import__(b["module_path"], fromlist=[b["bp_var"]])
                    bp = getattr(mod, b["bp_var"])
                    app.register_blueprint(bp)
                    registered_count += 1
                    print("  [OK] Auto-registered %s (discovered)" % b["bp_name"])
                except Exception as e:
                    pass  # Silent - many may fail (vidgenerator paths etc)
    except Exception:
        pass

    print(f"\n  [SUMMARY] Registered {registered_count} blueprints")
    app._blueprints_full_registration_done = True
    return registered_count
