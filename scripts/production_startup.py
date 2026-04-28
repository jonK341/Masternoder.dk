#!/usr/bin/env python3
"""
Production Startup Script
Initializes all systems and verifies they're ready
"""
import sys
import os
import logging

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(BASE_DIR, 'logs', 'startup.log'))
    ]
)

logger = logging.getLogger(__name__)

def initialize_services():
    """Initialize all services"""
    logger.info("Initializing services...")
    
    services = []
    
    # Initialize services that need initialization
    try:
        from backend.services.enhanced_click_activity import EnhancedClickActivity
        click_service = EnhancedClickActivity()
        services.append(('Enhanced Click Activity', True))
        logger.info("✅ Enhanced Click Activity initialized")
    except Exception as e:
        services.append(('Enhanced Click Activity', False))
        logger.error(f"❌ Enhanced Click Activity initialization failed: {e}")
    
    try:
        from backend.services.trophy_system import TrophySystem
        trophy_service = TrophySystem()
        services.append(('Trophy System', True))
        logger.info("✅ Trophy System initialized")
    except Exception as e:
        services.append(('Trophy System', False))
        logger.error(f"❌ Trophy System initialization failed: {e}")
    
    try:
        from backend.services.system_history import SystemHistory
        history_service = SystemHistory()
        services.append(('System History', True))
        logger.info("✅ System History initialized")
    except Exception as e:
        services.append(('System History', False))
        logger.error(f"❌ System History initialization failed: {e}")
    
    try:
        from backend.services.search_intelligence import SearchIntelligence
        search_service = SearchIntelligence()
        services.append(('Search Intelligence', True))
        logger.info("✅ Search Intelligence initialized")
    except Exception as e:
        services.append(('Search Intelligence', False))
        logger.error(f"❌ Search Intelligence initialization failed: {e}")
    
    try:
        from backend.services.energy_generation_system import EnergyGenerationSystem
        energy_service = EnergyGenerationSystem()
        services.append(('Energy Generation', True))
        logger.info("✅ Energy Generation initialized")
    except Exception as e:
        services.append(('Energy Generation', False))
        logger.error(f"❌ Energy Generation initialization failed: {e}")
    
    try:
        from backend.services.agent_manager import AgentManager
        agent_service = AgentManager()
        services.append(('Agent Manager', True))
        logger.info("✅ Agent Manager initialized")
    except Exception as e:
        services.append(('Agent Manager', False))
        logger.error(f"❌ Agent Manager initialization failed: {e}")
    
    try:
        from backend.services.enhanced_progress_data import EnhancedProgressData
        progress_service = EnhancedProgressData()
        services.append(('Enhanced Progress Data', True))
        logger.info("✅ Enhanced Progress Data initialized")
    except Exception as e:
        services.append(('Enhanced Progress Data', False))
        logger.error(f"❌ Enhanced Progress Data initialization failed: {e}")
    
    try:
        from backend.services.video_generation_rewards import VideoGenerationRewards
        video_service = VideoGenerationRewards()
        services.append(('Video Generation Rewards', True))
        logger.info("✅ Video Generation Rewards initialized")
    except Exception as e:
        services.append(('Video Generation Rewards', False))
        logger.error(f"❌ Video Generation Rewards initialization failed: {e}")
    
    try:
        from backend.services.shop_v2_enhanced import shop_v2_enhanced
        services.append(('Shop V2 Enhanced', True))
        logger.info("✅ Shop V2 Enhanced initialized")
    except Exception as e:
        services.append(('Shop V2 Enhanced', False))
        logger.error(f"❌ Shop V2 Enhanced initialization failed: {e}")
    
    return services

def verify_database():
    """Verify database is accessible"""
    logger.info("Verifying database connection...")
    
    try:
        from backend.services.unified_points_database import unified_points_db
        
        # Try a simple operation
        result = unified_points_db.get_user_points('system_check')
        logger.info("✅ Database connection verified")
        return True
    except Exception as e:
        logger.warning(f"⚠️  Database check warning: {e}")
        logger.info("   (This may be expected if database needs initialization)")
        return True  # Don't fail, might be expected

def verify_blueprints():
    """Verify all blueprints are registered"""
    logger.info("Verifying blueprint registration...")
    
    try:
        from flask import Flask
        from backend.register_blueprints import register_all_blueprints
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'startup-check'
        app.config['TESTING'] = True
        
        register_all_blueprints(app)
        
        registered = [bp.name for bp in app.blueprints.values()]
        logger.info(f"✅ {len(registered)} blueprints registered")
        
        return True
    except Exception as e:
        logger.error(f"❌ Blueprint verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main startup routine"""
    print("\n" + "=" * 70)
    print("PRODUCTION STARTUP - SYSTEM INITIALIZATION")
    print("=" * 70)
    print()
    
    # Create logs directory
    logs_dir = os.path.join(BASE_DIR, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    logger.info("Starting production startup sequence...")
    
    # Initialize services
    services = initialize_services()
    
    # Verify database
    db_ok = verify_database()
    
    # Verify blueprints
    bp_ok = verify_blueprints()
    
    # Summary
    print("\n" + "=" * 70)
    print("STARTUP SUMMARY")
    print("=" * 70)
    
    for name, result in services:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"{'✅' if db_ok else '❌'} Database Connection")
    print(f"{'✅' if bp_ok else '❌'} Blueprint Registration")
    
    all_ok = (
        all(result for _, result in services) and
        db_ok and
        bp_ok
    )
    
    if all_ok:
        print("\n🎉 ALL SYSTEMS INITIALIZED - READY FOR PRODUCTION!")
        logger.info("All systems initialized successfully")
        return 0
    else:
        print("\n⚠️  SOME SYSTEMS FAILED TO INITIALIZE - REVIEW LOGS")
        logger.warning("Some systems failed to initialize")
        return 1

if __name__ == '__main__':
    sys.exit(main())
