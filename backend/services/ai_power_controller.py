"""
AI Power Controller
Controls and enhances AI power across all systems
"""
import os
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy imports
def get_agent_ai_intelligence():
    from backend.services.agent_ai_intelligence import agent_ai_intelligence
    return agent_ai_intelligence

def get_unified_points_db():
    try:
        from backend.services.unified_points_database_enhanced import UnifiedPointsDatabaseEnhanced
        return UnifiedPointsDatabaseEnhanced()
    except:
        return None


class AIPowerController:
    """Controls AI power and capabilities"""
    
    def __init__(self):
        self.ai = get_agent_ai_intelligence()
        self.points_db = get_unified_points_db()
    
    def enhance_ai_power(self, agent_id: str, power_type: str, amount: float) -> Dict:
        """Enhance AI power for specific capability"""
        if agent_id not in self.ai.intelligence['agents']:
            self.ai.intelligence['agents'][agent_id] = {
                'power_level': 10,
                'enhanced_capabilities': {}
            }
        
        agent_data = self.ai.intelligence['agents'][agent_id]
        
        if 'enhanced_capabilities' not in agent_data:
            agent_data['enhanced_capabilities'] = {}
        
        current_power = agent_data['enhanced_capabilities'].get(power_type, 10)
        new_power = min(100, current_power + amount)
        
        agent_data['enhanced_capabilities'][power_type] = new_power
        
        # Update global enhanced capabilities
        if 'enhanced_capabilities' not in self.ai.intelligence:
            self.ai.intelligence['enhanced_capabilities'] = {}
        self.ai.intelligence['enhanced_capabilities'][power_type] = new_power
        
        self.ai.save_intelligence()
        
        return {
            'agent_id': agent_id,
            'power_type': power_type,
            'previous_power': current_power,
            'new_power': new_power,
            'enhancement': amount
        }
    
    def get_ai_power_level(self, agent_id: str) -> Dict:
        """Get current AI power level"""
        agent_data = self.ai.intelligence['agents'].get(agent_id, {})
        
        base_power = agent_data.get('power_level', 10)
        enhanced = agent_data.get('enhanced_capabilities', {})
        global_enhanced = self.ai.intelligence.get('enhanced_capabilities', {})
        
        total_power = {
            'base': base_power,
            'enhanced': enhanced,
            'global_enhanced': global_enhanced,
            'total': base_power + sum(enhanced.values()) + sum(global_enhanced.values())
        }
        
        return total_power
    
    def control_ai_power(self, agent_id: str, power_limit: int) -> Dict:
        """Set power limit for AI agent"""
        if agent_id not in self.ai.intelligence['agents']:
            self.ai.intelligence['agents'][agent_id] = {}
        
        self.ai.intelligence['agents'][agent_id]['power_limit'] = power_limit
        self.ai.intelligence['power_level'] = min(
            self.ai.intelligence.get('power_level', 100),
            power_limit
        )
        
        self.ai.save_intelligence()
        
        return {
            'agent_id': agent_id,
            'power_limit': power_limit,
            'current_power': self.ai.intelligence.get('power_level', 100)
        }


# Global instance
ai_power_controller = AIPowerController()
