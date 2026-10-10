"""
AI Defense System - Prioritized Security and Safety
Protects against malicious inputs, abuse, and ensures safe generation
"""
import re
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict


class AIDefenseSystem:
    """AI Defense System for Generation Security"""
    
    def __init__(self):
        self.threat_levels = {
            'low': 0,
            'medium': 1,
            'high': 2,
            'critical': 3
        }
        self.blocked_patterns = []
        self.rate_limits = {}  # {user_id: {count: int, reset_time: datetime}}
        self.suspicious_activities = {}  # {user_id: List[Activity]}
        self.whitelist = set()
        self.blacklist = set()
        
        # Initialize threat patterns
        self._initialize_threat_patterns()
    
    def _initialize_threat_patterns(self):
        """Initialize known threat patterns"""
        self.blocked_patterns = [
            # Injection attempts
            (r'<script[^>]*>.*?</script>', 'high'),
            (r'javascript:', 'high'),
            (r'on\w+\s*=', 'high'),
            
            # SQL injection patterns
            (r"('|(\\')|(;)|(--)|(\*)|(\/\*)|(\*\/))", 'medium'),
            
            # Command injection
            (r'[;&|`$(){}]', 'medium'),
            
            # Excessive length (potential DoS)
            (r'.{10000,}', 'medium'),
            
            # Suspicious content
            (r'(hack|exploit|vulnerability|bypass|inject)', 'low'),
            
            # Spam patterns
            (r'(http://|https://).{0,10}(bit\.ly|tinyurl|t\.co)', 'low'),
        ]
    
    def analyze_input(self, user_id: str, input_text: str, input_type: str = 'prompt') -> Dict[str, Any]:
        """
        Analyze input for threats and security issues
        
        Args:
            user_id: User identifier
            input_text: Input text to analyze
            input_type: Type of input (prompt, title, etc.)
        
        Returns:
            Analysis result with threat level and recommendations
        """
        threats = []
        max_threat_level = 0
        
        # Check against blocked patterns
        for pattern, level in self.blocked_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                threat_level = self.threat_levels.get(level, 0)
                threats.append({
                    'pattern': pattern,
                    'level': level,
                    'threat_level': threat_level
                })
                max_threat_level = max(max_threat_level, threat_level)
        
        # Check rate limiting
        rate_limit_result = self._check_rate_limit(user_id, input_type)
        if not rate_limit_result['allowed']:
            max_threat_level = max(max_threat_level, 1)
            threats.append({
                'type': 'rate_limit',
                'level': 'medium',
                'threat_level': 1,
                'message': rate_limit_result['message']
            })
        
        # Check blacklist
        if user_id in self.blacklist:
            max_threat_level = 3
            threats.append({
                'type': 'blacklist',
                'level': 'critical',
                'threat_level': 3,
                'message': 'User is blacklisted'
            })
        
        # Determine action
        action = 'allow'
        if max_threat_level >= 3:
            action = 'block'
        elif max_threat_level >= 2:
            action = 'review'
        elif max_threat_level >= 1:
            action = 'monitor'
        
        # Log suspicious activity
        if max_threat_level > 0:
            self._log_suspicious_activity(user_id, input_text, max_threat_level, threats)
        
        return {
            'safe': max_threat_level == 0,
            'threat_level': max_threat_level,
            'threat_level_name': self._get_threat_level_name(max_threat_level),
            'action': action,
            'threats': threats,
            'recommendations': self._get_recommendations(max_threat_level, threats)
        }
    
    def _check_rate_limit(self, user_id: str, action_type: str) -> Dict[str, Any]:
        """Check if user has exceeded rate limits"""
        now = datetime.utcnow()
        key = f"{user_id}:{action_type}"
        
        # Rate limits (per hour)
        limits = {
            'generate': 10,  # 10 generations per hour
            'prompt': 50,    # 50 prompts per hour
            'api': 100       # 100 API calls per hour
        }
        
        limit = limits.get(action_type, 50)
        window = timedelta(hours=1)
        
        if key not in self.rate_limits:
            self.rate_limits[key] = {
                'count': 0,
                'reset_time': now + window
            }
        
        rate_data = self.rate_limits[key]
        
        # Reset if window expired
        if now > rate_data['reset_time']:
            rate_data['count'] = 0
            rate_data['reset_time'] = now + window
        
        # Check limit
        if rate_data['count'] >= limit:
            return {
                'allowed': False,
                'message': f'Rate limit exceeded: {limit} {action_type} per hour',
                'reset_time': rate_data['reset_time'].isoformat()
            }
        
        # Increment count
        rate_data['count'] += 1
        
        return {
            'allowed': True,
            'count': rate_data['count'],
            'limit': limit
        }
    
    def _log_suspicious_activity(self, user_id: str, input_text: str, threat_level: int, threats: List):
        """Log suspicious activity for monitoring"""
        if user_id not in self.suspicious_activities:
            self.suspicious_activities[user_id] = []
        
        activity = {
            'timestamp': datetime.utcnow().isoformat(),
            'threat_level': threat_level,
            'threats': threats,
            'input_preview': input_text[:100] if input_text else '',
            'action_taken': self._get_action_for_threat_level(threat_level)
        }
        
        self.suspicious_activities[user_id].append(activity)
        
        # Keep only last 100 activities per user
        if len(self.suspicious_activities[user_id]) > 100:
            self.suspicious_activities[user_id] = self.suspicious_activities[user_id][-100:]
    
    def _get_threat_level_name(self, level: int) -> str:
        """Get threat level name from numeric level"""
        level_map = {0: 'low', 1: 'medium', 2: 'high', 3: 'critical'}
        return level_map.get(level, 'unknown')
    
    def _get_action_for_threat_level(self, level: int) -> str:
        """Get recommended action for threat level"""
        if level >= 3:
            return 'block'
        elif level >= 2:
            return 'review'
        elif level >= 1:
            return 'monitor'
        return 'allow'
    
    def _get_recommendations(self, threat_level: int, threats: List) -> List[str]:
        """Get security recommendations based on threats"""
        recommendations = []
        
        if threat_level >= 3:
            recommendations.append('BLOCK: Critical threat detected')
            recommendations.append('Log incident for security review')
        elif threat_level >= 2:
            recommendations.append('REVIEW: High threat level - manual review recommended')
            recommendations.append('Monitor user activity closely')
        elif threat_level >= 1:
            recommendations.append('MONITOR: Suspicious activity detected')
            recommendations.append('Track user behavior patterns')
        
        return recommendations
    
    def sanitize_input(self, input_text: str) -> str:
        """Sanitize input text for safe processing"""
        # Remove script tags
        input_text = re.sub(r'<script[^>]*>.*?</script>', '', input_text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove javascript: protocol
        input_text = re.sub(r'javascript:', '', input_text, flags=re.IGNORECASE)
        
        # Remove event handlers
        input_text = re.sub(r'on\w+\s*=', '', input_text, flags=re.IGNORECASE)
        
        # Limit length (prevent DoS)
        max_length = 10000
        if len(input_text) > max_length:
            input_text = input_text[:max_length]
        
        # Trim whitespace
        input_text = input_text.strip()
        
        return input_text
    
    def is_safe_to_process(self, user_id: str, input_text: str, input_type: str = 'prompt') -> Tuple[bool, Dict[str, Any]]:
        """
        Check if input is safe to process (main entry point)
        
        Returns:
            (is_safe, analysis_result)
        """
        # Sanitize input first
        sanitized = self.sanitize_input(input_text)
        
        # Analyze for threats
        analysis = self.analyze_input(user_id, sanitized, input_type)
        
        # Determine if safe
        is_safe = analysis['safe'] and analysis['action'] in ['allow', 'monitor']
        
        return is_safe, {
            'sanitized_input': sanitized,
            'analysis': analysis,
            'original_length': len(input_text),
            'sanitized_length': len(sanitized)
        }


# Global instance
ai_defense = AIDefenseSystem()

