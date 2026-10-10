"""
Frontpage Initializer Service
Initializes and starts all systems: Points, Game, Battles
"""
import sys
from datetime import datetime

class FrontpageInitializer:
    """Initialize all systems for frontpage"""
    
    def __init__(self):
        self.initialized = False
        self.init_time = None
    
    def initialize_all(self):
        """Initialize all systems"""
        try:
            print(f"[FrontpageInitializer] Starting initialization at {datetime.now()}", file=sys.stderr, flush=True)
            
            # Initialize Points Collection System
            self._init_points_system()
            
            # Initialize Game System
            self._init_game_system()
            
            # Initialize Battle System
            self._init_battle_system()
            
            self.initialized = True
            self.init_time = datetime.now()
            print(f"[FrontpageInitializer] All systems initialized successfully at {self.init_time}", file=sys.stderr, flush=True)
            return True
        except Exception as e:
            print(f"[FrontpageInitializer] Error during initialization: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            return False
    
    def _init_points_system(self):
        """Initialize points collection system"""
        try:
            # Try to initialize unified points system
            try:
                from backend.services.unified_point_system_json_storage import unified_point_system
                # Initialize with default user
                unified_point_system.get_points('default_user')
                print("[FrontpageInitializer] Points system initialized", file=sys.stderr, flush=True)
            except ImportError:
                print("[FrontpageInitializer] Unified points system not available", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[FrontpageInitializer] Points system init error: {e}", file=sys.stderr, flush=True)
            
            # Try to initialize point calculator
            try:
                from backend.services.point_calculator_integration import point_calculator_integration
                # Test calculation
                point_calculator_integration.calculate_with_hardcoded('default_user', sync_to_db=False)
                print("[FrontpageInitializer] Point calculator initialized", file=sys.stderr, flush=True)
            except ImportError:
                print("[FrontpageInitializer] Point calculator not available", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[FrontpageInitializer] Point calculator init error: {e}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[FrontpageInitializer] Points system initialization failed: {e}", file=sys.stderr, flush=True)
    
    def _init_game_system(self):
        """Initialize game system"""
        try:
            # Try to initialize game mechanics
            try:
                from backend.services.unified_game_mechanics_constructor import unified_game_mechanics
                # Initialize with default user
                unified_game_mechanics.get_user_progress('default_user')
                print("[FrontpageInitializer] Game mechanics initialized", file=sys.stderr, flush=True)
            except ImportError:
                print("[FrontpageInitializer] Game mechanics not available", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[FrontpageInitializer] Game mechanics init error: {e}", file=sys.stderr, flush=True)
            
            # Try to initialize leveling system
            try:
                from backend.services.hunters_leveling_system import hunters_leveling_system
                # Get default profile
                hunters_leveling_system.get_player_profile('default_user')
                print("[FrontpageInitializer] Leveling system initialized", file=sys.stderr, flush=True)
            except ImportError:
                print("[FrontpageInitializer] Leveling system not available", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[FrontpageInitializer] Leveling system init error: {e}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[FrontpageInitializer] Game system initialization failed: {e}", file=sys.stderr, flush=True)
    
    def _init_battle_system(self):
        """Initialize battle system"""
        try:
            # Try to initialize quick battle system
            try:
                from backend.services.quick_battle_system import quick_battle
                # Get default stats
                quick_battle.get_user_battle_stats('default_user')
                print("[FrontpageInitializer] Quick battle system initialized", file=sys.stderr, flush=True)
            except ImportError:
                print("[FrontpageInitializer] Quick battle system not available", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[FrontpageInitializer] Quick battle init error: {e}", file=sys.stderr, flush=True)
            
            # Try to initialize battle system
            try:
                from backend.services.battle_system import battle_system
                # Get status
                battle_system.get_battle_status('default_user')
                print("[FrontpageInitializer] Battle system initialized", file=sys.stderr, flush=True)
            except ImportError:
                print("[FrontpageInitializer] Battle system not available", file=sys.stderr, flush=True)
            except Exception as e:
                print(f"[FrontpageInitializer] Battle system init error: {e}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[FrontpageInitializer] Battle system initialization failed: {e}", file=sys.stderr, flush=True)
    
    def get_status(self):
        """Get initialization status"""
        return {
            'initialized': self.initialized,
            'init_time': self.init_time.isoformat() if self.init_time else None
        }

# Global instance
frontpage_initializer = FrontpageInitializer()
