"""
Advanced Calculator Automation
Automatically calculates all stats in the system
Monitors behavior patterns
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import threading
import time

try:
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    from backend.services.behavior_pattern_monitor import behavior_pattern_monitor
    from backend.services.unified_point_counter import unified_point_counter
    from src.db.models import db, UserProfile
except ImportError:
    advanced_intelligent_calculator = None
    behavior_pattern_monitor = None
    unified_point_counter = None
    db = None
    UserProfile = None


class CalculatorAutomation:
    """
    Automated calculator system
    Calculates all stats and monitors behavior patterns
    """
    
    def __init__(self):
        """Initialize calculator automation"""
        self.is_running = False
        self.calculation_interval = 300  # 5 minutes
        self.last_calculation = {}
        self.calculation_thread = None
    
    def start(self):
        """Start automated calculations"""
        if self.is_running:
            return {'success': False, 'error': 'Already running'}
        
        self.is_running = True
        self.calculation_thread = threading.Thread(target=self._calculation_loop, daemon=True)
        self.calculation_thread.start()
        
        return {
            'success': True,
            'message': 'Calculator automation started',
            'interval_seconds': self.calculation_interval
        }
    
    def stop(self):
        """Stop automated calculations"""
        self.is_running = False
        return {
            'success': True,
            'message': 'Calculator automation stopped'
        }
    
    def _calculation_loop(self):
        """Main calculation loop"""
        while self.is_running:
            try:
                # Calculate for all users
                self._calculate_all_users()
                
                # Sleep for interval
                time.sleep(self.calculation_interval)
            except Exception as e:
                print(f"[CalculatorAutomation] Error in calculation loop: {e}", flush=True)
                time.sleep(60)  # Wait 1 minute on error
    
    def _calculate_all_users(self):
        """Calculate stats for all users"""
        if not db or not UserProfile:
            return
        
        try:
            # Use Flask app context if available
            from flask import has_app_context, current_app
            if has_app_context():
                users = UserProfile.query.filter(
                    UserProfile.preferences.isnot(None)
                ).limit(100).all()  # Limit to 100 users per cycle
            else:
                # Try to get app from global
                try:
                    from src.app import create_app
                    app = create_app()
                    with app.app_context():
                        users = UserProfile.query.filter(
                            UserProfile.preferences.isnot(None)
                        ).limit(100).all()
                except:
                    print("[CalculatorAutomation] No app context available, skipping calculation", flush=True)
                    return
            
            for user in users:
                try:
                    self._calculate_user_stats(user.user_id)
                except Exception as e:
                    print(f"[CalculatorAutomation] Error calculating for {user.user_id}: {e}", flush=True)
        except Exception as e:
            print(f"[CalculatorAutomation] Error getting users: {e}", flush=True)
    
    def _calculate_user_stats(self, user_id: str):
        """Calculate stats for a single user"""
        if not advanced_intelligent_calculator or not unified_point_counter:
            return
        
        try:
            # Get current points
            current_points = unified_point_counter.get_all_points(user_id)
            
            # Calculate with intelligence
            calculation_result = advanced_intelligent_calculator.calculate_with_intelligence(
                current_points, user_id
            )
            
            # Record behavior pattern
            behavior_data = {
                'total_points': calculation_result.get('final_calculation', {}).get('final_total', 0),
                'points_restored': calculation_result.get('restored_points', {}).get('total_restored', 0),
                'anomalies_detected': len(calculation_result.get('anomalies_detected', {}).get('detected', [])),
                'confidence_score': calculation_result.get('confidence_score', 0),
                'calculation_id': calculation_result.get('calculation_id')
            }
            
            # Monitor behavior
            if behavior_pattern_monitor:
                behavior_pattern_monitor.record_behavior(user_id, behavior_data)
            
            # Update last calculation
            self.last_calculation[user_id] = {
                'timestamp': datetime.utcnow().isoformat(),
                'calculation_id': calculation_result.get('calculation_id'),
                'final_total': behavior_data['total_points']
            }
            
        except Exception as e:
            print(f"[CalculatorAutomation] Error calculating stats for {user_id}: {e}", flush=True)
    
    def get_status(self) -> Dict[str, Any]:
        """Get automation status"""
        return {
            'is_running': self.is_running,
            'interval_seconds': self.calculation_interval,
            'users_calculated': len(self.last_calculation),
            'last_calculations': dict(list(self.last_calculation.items())[-10:])  # Last 10
        }
    
    def calculate_now(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Trigger immediate calculation"""
        if user_id:
            self._calculate_user_stats(user_id)
            return {
                'success': True,
                'user_id': user_id,
                'message': 'Calculation triggered'
            }
        else:
            self._calculate_all_users()
            return {
                'success': True,
                'message': 'Calculation triggered for all users'
            }


# Global instance
calculator_automation = CalculatorAutomation()

