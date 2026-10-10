"""
Battle Intelligence System - Fight and Aggression Intelligence
Downloads opponent data from battle network and analyzes fight patterns
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import random
import math

class BattleIntelligence:
    """Analyzes fight patterns, aggression levels, and opponent intelligence"""
    
    def __init__(self):
        self.opponent_cache = {}  # opponent_id -> cached_data
        self.fight_patterns = {}  # user_id -> fight_pattern_data
        self.aggression_profiles = {}  # user_id -> aggression_data
        self.battle_network_data = {}  # Network of available opponents
    
    def download_opponent_data(self, opponent_id: str) -> Dict[str, Any]:
        """
        Download opponent data from battle network
        Simulates downloading from battlenet/external source
        """
        if opponent_id in self.opponent_cache:
            return self.opponent_cache[opponent_id]
        
        # Simulate downloading from battle network
        # In production, this would fetch from external API/database
        opponent_data = {
            'id': opponent_id,
            'name': f'Opponent_{opponent_id[:8]}',
            'level': random.randint(1, 50),
            'rating': random.randint(800, 2500),
            'wins': random.randint(0, 100),
            'losses': random.randint(0, 50),
            'win_rate': random.uniform(0.3, 0.9),
            'total_battles': random.randint(10, 150),
            'aggression_score': random.uniform(0.1, 1.0),
            'fight_style': random.choice(['aggressive', 'defensive', 'balanced', 'tactical']),
            'preferred_battle_type': random.choice(['ranked', 'casual', 'tournament']),
            'strengths': random.sample(['creativity', 'quality', 'speed', 'consistency'], k=2),
            'weaknesses': random.sample(['creativity', 'quality', 'speed', 'consistency'], k=1),
            'artifacts_count': random.randint(0, 10),
            'items_equipped': random.randint(0, 5),
            'last_active': datetime.utcnow().isoformat(),
            'battle_history': self._generate_battle_history(opponent_id),
            'downloaded_at': datetime.utcnow().isoformat()
        }
        
        self.opponent_cache[opponent_id] = opponent_data
        return opponent_data
    
    def _generate_battle_history(self, opponent_id: str) -> List[Dict[str, Any]]:
        """Generate sample battle history for opponent"""
        history = []
        for i in range(random.randint(5, 20)):
            history.append({
                'battle_id': f'battle_{opponent_id}_{i}',
                'result': random.choice(['win', 'loss', 'draw']),
                'opponent_rating': random.randint(800, 2500),
                'score': random.randint(50, 500),
                'duration_seconds': random.randint(60, 600),
                'date': datetime.utcnow().isoformat()
            })
        return history
    
    def analyze_fight_intelligence(self, user_id: str, opponent_id: str) -> Dict[str, Any]:
        """
        Analyze fight intelligence between user and opponent
        Returns fight patterns, aggression levels, and strategic insights
        """
        opponent_data = self.download_opponent_data(opponent_id)
        user_profile = self._get_user_profile(user_id)
        
        # Calculate fight intelligence metrics
        fight_intelligence = {
            'user_id': user_id,
            'opponent_id': opponent_id,
            'opponent_data': opponent_data,
            'match_analysis': self._analyze_match(user_profile, opponent_data),
            'aggression_analysis': self._analyze_aggression(user_profile, opponent_data),
            'fight_patterns': self._analyze_fight_patterns(opponent_data),
            'strategic_recommendations': self._generate_strategic_recommendations(user_profile, opponent_data),
            'win_probability': self._calculate_win_probability(user_profile, opponent_data),
            'risk_assessment': self._assess_risk(user_profile, opponent_data),
            'analyzed_at': datetime.utcnow().isoformat()
        }
        
        return fight_intelligence
    
    def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile data from various systems"""
        profile = {
            'user_id': user_id,
            'level': 1,
            'rating': 1000,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'total_battles': 0,
            'aggression_score': 0.5,
            'fight_style': 'balanced',
            'artifacts_count': 0,
            'items_equipped': 0,
            'stats': {}
        }
        
        try:
            # Get player profiler data
            from backend.services.player_profiler import player_profiler
            profiler_data = player_profiler.get_profile(user_id)
            if profiler_data:
                profile['stats'] = profiler_data.get('stats', {})
                profile['total_actions'] = profiler_data.get('total_actions', 0)
        except:
            pass
        
        try:
            # Get battle stats
            from backend.services.battle_system import battle_system
            # Try to get battle history for user
            battle_history = battle_system.get_battle_history(100)
            user_battles = [b for b in battle_history if user_id in str(b)]
            if user_battles:
                wins = sum(1 for b in user_battles if b.get('winner') == user_id)
                profile['wins'] = wins
                profile['losses'] = len(user_battles) - wins
                profile['total_battles'] = len(user_battles)
                profile['win_rate'] = wins / len(user_battles) if user_battles else 0.0
        except:
            pass
        
        try:
            # Get artifacts count
            from backend.services.artifacts_system import artifacts_system
            artifacts = artifacts_system.get_user_artifacts(user_id)
            profile['artifacts_count'] = len(artifacts) if artifacts else 0
        except:
            pass
        
        try:
            # Get items count
            from backend.services.items_system import items_system
            inventory = items_system.get_inventory(user_id)
            if inventory:
                equipped = inventory.get('equipped', {})
                profile['items_equipped'] = len(equipped)
        except:
            pass
        
        return profile
    
    def _analyze_match(self, user_profile: Dict[str, Any], opponent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze match compatibility"""
        user_rating = user_profile.get('rating', 1000)
        opponent_rating = opponent_data.get('rating', 1000)
        rating_diff = abs(user_rating - opponent_rating)
        
        # Calculate match quality (0-1, higher is better)
        match_quality = 1.0 - min(rating_diff / 1000, 1.0)
        
        return {
            'rating_difference': rating_diff,
            'match_quality': match_quality,
            'fair_match': rating_diff < 200,
            'challenge_level': 'easy' if opponent_rating < user_rating - 200 else 'hard' if opponent_rating > user_rating + 200 else 'balanced',
            'recommended': match_quality > 0.6
        }
    
    def _analyze_aggression(self, user_profile: Dict[str, Any], opponent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze aggression levels and patterns"""
        opponent_aggression = opponent_data.get('aggression_score', 0.5)
        opponent_style = opponent_data.get('fight_style', 'balanced')
        
        # Calculate aggression metrics
        aggression_metrics = {
            'opponent_aggression_score': opponent_aggression,
            'opponent_fight_style': opponent_style,
            'aggression_level': 'low' if opponent_aggression < 0.4 else 'high' if opponent_aggression > 0.7 else 'medium',
            'tendency': self._analyze_aggression_tendency(opponent_data),
            'predicted_behavior': self._predict_behavior(opponent_data),
            'vulnerability_points': self._find_vulnerability_points(opponent_data)
        }
        
        return aggression_metrics
    
    def _analyze_aggression_tendency(self, opponent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze opponent's aggression tendency"""
        history = opponent_data.get('battle_history', [])
        if not history:
            return {'pattern': 'unknown', 'confidence': 0.0}
        
        # Analyze win/loss patterns
        wins = sum(1 for h in history if h.get('result') == 'win')
        losses = sum(1 for h in history if h.get('result') == 'loss')
        total = len(history)
        
        # Calculate aggression indicators
        avg_score = sum(h.get('score', 0) for h in history) / total if total > 0 else 0
        avg_duration = sum(h.get('duration_seconds', 0) for h in history) / total if total > 0 else 0
        
        # High aggression: high scores, short battles
        # Low aggression: lower scores, longer battles
        aggression_indicator = (avg_score / 500) * (1 - min(avg_duration / 600, 1))
        
        return {
            'pattern': 'aggressive' if aggression_indicator > 0.6 else 'defensive' if aggression_indicator < 0.3 else 'balanced',
            'confidence': min(aggression_indicator * 1.5, 1.0),
            'avg_score': avg_score,
            'avg_duration': avg_duration
        }
    
    def _predict_behavior(self, opponent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict opponent's battle behavior"""
        style = opponent_data.get('fight_style', 'balanced')
        aggression = opponent_data.get('aggression_score', 0.5)
        
        predictions = {
            'opening_strategy': 'rush' if aggression > 0.7 else 'defensive' if aggression < 0.3 else 'balanced',
            'mid_battle_style': style,
            'end_game_approach': 'aggressive' if aggression > 0.6 else 'cautious',
            'likely_actions': self._predict_likely_actions(style, aggression),
            'timing_pattern': 'fast' if aggression > 0.7 else 'slow' if aggression < 0.3 else 'moderate'
        }
        
        return predictions
    
    def _predict_likely_actions(self, style: str, aggression: float) -> List[str]:
        """Predict likely actions based on style and aggression"""
        actions = []
        
        if style == 'aggressive' or aggression > 0.7:
            actions.extend(['quick_video_generation', 'high_quality_push', 'rapid_fire_actions'])
        elif style == 'defensive' or aggression < 0.3:
            actions.extend(['careful_quality_focus', 'strategic_timing', 'resource_management'])
        else:
            actions.extend(['balanced_approach', 'adaptive_strategy'])
        
        return actions
    
    def _find_vulnerability_points(self, opponent_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find opponent's vulnerability points"""
        vulnerabilities = []
        
        weaknesses = opponent_data.get('weaknesses', [])
        for weakness in weaknesses:
            vulnerabilities.append({
                'type': weakness,
                'severity': 'high' if weakness in ['speed', 'consistency'] else 'medium',
                'exploitation_strategy': f'Focus on {weakness} advantage'
            })
        
        # Check win rate patterns
        win_rate = opponent_data.get('win_rate', 0.5)
        if win_rate < 0.4:
            vulnerabilities.append({
                'type': 'low_confidence',
                'severity': 'medium',
                'exploitation_strategy': 'Apply early pressure'
            })
        
        return vulnerabilities
    
    def _analyze_fight_patterns(self, opponent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze opponent's fight patterns"""
        history = opponent_data.get('battle_history', [])
        
        if not history:
            return {
                'pattern_type': 'unknown',
                'consistency': 0.0,
                'streak_analysis': {},
                'performance_trend': 'stable'
            }
        
        # Analyze streaks
        recent_results = [h.get('result') for h in history[:10]]
        win_streak = 0
        loss_streak = 0
        current_streak_type = None
        current_streak = 0
        
        for result in recent_results:
            if result == current_streak_type:
                current_streak += 1
            else:
                if current_streak_type == 'win':
                    win_streak = max(win_streak, current_streak)
                elif current_streak_type == 'loss':
                    loss_streak = max(loss_streak, current_streak)
                current_streak_type = result
                current_streak = 1
        
        # Calculate consistency
        scores = [h.get('score', 0) for h in history]
        if scores:
            avg_score = sum(scores) / len(scores)
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            consistency = 1.0 - min(variance / (avg_score ** 2) if avg_score > 0 else 1.0, 1.0)
        else:
            consistency = 0.0
        
        return {
            'pattern_type': 'streak_player' if max(win_streak, loss_streak) > 3 else 'consistent' if consistency > 0.7 else 'volatile',
            'consistency': consistency,
            'win_streak': win_streak,
            'loss_streak': loss_streak,
            'current_streak': current_streak,
            'current_streak_type': current_streak_type,
            'performance_trend': 'improving' if recent_results.count('win') > len(recent_results) * 0.6 else 'declining' if recent_results.count('loss') > len(recent_results) * 0.6 else 'stable',
            'avg_score': avg_score if scores else 0
        }
    
    def _generate_strategic_recommendations(self, user_profile: Dict[str, Any], opponent_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate strategic recommendations for battle"""
        recommendations = []
        
        # Analyze opponent weaknesses
        weaknesses = opponent_data.get('weaknesses', [])
        for weakness in weaknesses:
            recommendations.append({
                'type': 'exploit_weakness',
                'priority': 'high',
                'action': f'Focus on {weakness} to gain advantage',
                'expected_impact': 'significant'
            })
        
        # Analyze fight style
        opponent_style = opponent_data.get('fight_style', 'balanced')
        if opponent_style == 'aggressive':
            recommendations.append({
                'type': 'counter_strategy',
                'priority': 'high',
                'action': 'Use defensive strategy, let opponent exhaust resources',
                'expected_impact': 'high'
            })
        elif opponent_style == 'defensive':
            recommendations.append({
                'type': 'counter_strategy',
                'priority': 'high',
                'action': 'Apply early pressure, force quick decisions',
                'expected_impact': 'high'
            })
        
        # Rating difference strategy
        user_rating = user_profile.get('rating', 1000)
        opponent_rating = opponent_data.get('rating', 1000)
        if opponent_rating > user_rating + 200:
            recommendations.append({
                'type': 'underdog_strategy',
                'priority': 'medium',
                'action': 'Play conservatively, capitalize on mistakes',
                'expected_impact': 'medium'
            })
        elif opponent_rating < user_rating - 200:
            recommendations.append({
                'type': 'favorite_strategy',
                'priority': 'medium',
                'action': 'Maintain consistent quality, avoid complacency',
                'expected_impact': 'medium'
            })
        
        return recommendations
    
    def _calculate_win_probability(self, user_profile: Dict[str, Any], opponent_data: Dict[str, Any]) -> float:
        """Calculate probability of winning against opponent"""
        user_rating = user_profile.get('rating', 1000)
        opponent_rating = opponent_data.get('rating', 1000)
        
        # Base probability from rating difference (ELO formula)
        rating_diff = opponent_rating - user_rating
        base_probability = 1 / (1 + 10 ** (rating_diff / 400))
        
        # Adjust based on artifacts and items
        user_artifacts = user_profile.get('artifacts_count', 0)
        opponent_artifacts = opponent_data.get('artifacts_count', 0)
        artifact_advantage = (user_artifacts - opponent_artifacts) * 0.02
        
        user_items = user_profile.get('items_equipped', 0)
        opponent_items = opponent_data.get('items_equipped', 0)
        item_advantage = (user_items - opponent_items) * 0.01
        
        # Adjust based on win rate
        user_win_rate = user_profile.get('win_rate', 0.5)
        opponent_win_rate = opponent_data.get('win_rate', 0.5)
        win_rate_advantage = (user_win_rate - opponent_win_rate) * 0.1
        
        # Final probability
        final_probability = base_probability + artifact_advantage + item_advantage + win_rate_advantage
        return max(0.0, min(1.0, final_probability))
    
    def _assess_risk(self, user_profile: Dict[str, Any], opponent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk level of battle"""
        win_probability = self._calculate_win_probability(user_profile, opponent_data)
        opponent_rating = opponent_data.get('rating', 1000)
        user_rating = user_profile.get('rating', 1000)
        
        risk_level = 'low'
        if win_probability < 0.3:
            risk_level = 'very_high'
        elif win_probability < 0.4:
            risk_level = 'high'
        elif win_probability < 0.6:
            risk_level = 'medium'
        
        return {
            'risk_level': risk_level,
            'risk_score': 1.0 - win_probability,
            'rating_risk': 'high' if abs(opponent_rating - user_rating) > 300 else 'low',
            'recommendation': 'proceed' if win_probability > 0.35 else 'caution' if win_probability > 0.25 else 'avoid'
        }
    
    def find_intelligent_opponents(self, user_id: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Find intelligent opponents using battle network data
        Downloads opponent data and analyzes for best matches
        """
        user_profile = self._get_user_profile(user_id)
        
        # Generate potential opponents from battle network
        potential_opponents = []
        for i in range(count * 3):  # Generate more candidates for better selection
            opponent_id = f'opponent_{random.randint(1000, 9999)}'
            opponent_data = self.download_opponent_data(opponent_id)
            
            # Analyze match
            match_analysis = self._analyze_match(user_profile, opponent_data)
            fight_intelligence = self.analyze_fight_intelligence(user_id, opponent_id)
            
            potential_opponents.append({
                'opponent': opponent_data,
                'match_quality': match_analysis.get('match_quality', 0),
                'fight_intelligence': fight_intelligence,
                'win_probability': fight_intelligence.get('win_probability', 0.5),
                'risk_assessment': fight_intelligence.get('risk_assessment', {}),
                'recommended': match_analysis.get('recommended', False)
            })
        
        # Sort by match quality and win probability balance
        potential_opponents.sort(key=lambda x: (
            x['match_quality'] * 0.6 + x['win_probability'] * 0.4,
            -abs(x['win_probability'] - 0.5)  # Prefer close to 50% for fair matches
        ), reverse=True)
        
        # Return top matches
        return potential_opponents[:count]
    
    def get_aggression_intelligence(self, user_id: str, opponent_id: str) -> Dict[str, Any]:
        """Get detailed aggression intelligence for opponent"""
        opponent_data = self.download_opponent_data(opponent_id)
        user_profile = self._get_user_profile(user_id)
        
        aggression_intel = {
            'opponent_aggression_score': opponent_data.get('aggression_score', 0.5),
            'opponent_fight_style': opponent_data.get('fight_style', 'balanced'),
            'aggression_analysis': self._analyze_aggression(user_profile, opponent_data),
            'predicted_aggression_level': self._predict_aggression_level(opponent_data),
            'counter_aggression_strategy': self._generate_counter_aggression_strategy(opponent_data),
            'aggression_timeline': self._predict_aggression_timeline(opponent_data)
        }
        
        return aggression_intel
    
    def _predict_aggression_level(self, opponent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict opponent's aggression level throughout battle"""
        base_aggression = opponent_data.get('aggression_score', 0.5)
        style = opponent_data.get('fight_style', 'balanced')
        
        return {
            'opening_aggression': base_aggression * 1.2 if style == 'aggressive' else base_aggression * 0.8,
            'mid_battle_aggression': base_aggression,
            'end_game_aggression': base_aggression * 1.3 if base_aggression > 0.6 else base_aggression * 0.9,
            'peak_aggression_time': 'early' if style == 'aggressive' else 'late' if style == 'defensive' else 'mid'
        }
    
    def _generate_counter_aggression_strategy(self, opponent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate strategy to counter opponent's aggression"""
        aggression = opponent_data.get('aggression_score', 0.5)
        style = opponent_data.get('fight_style', 'balanced')
        
        if aggression > 0.7 or style == 'aggressive':
            return {
                'strategy': 'defensive_counter',
                'tactics': ['absorb_early_pressure', 'wait_for_mistakes', 'resource_conservation'],
                'timing': 'mid_to_late_battle',
                'key_actions': ['defensive_quality_focus', 'strategic_timing', 'endurance_play']
            }
        elif aggression < 0.3 or style == 'defensive':
            return {
                'strategy': 'aggressive_counter',
                'tactics': ['early_pressure', 'force_decisions', 'maintain_momentum'],
                'timing': 'opening_to_mid_battle',
                'key_actions': ['quick_actions', 'quality_push', 'resource_advantage']
            }
        else:
            return {
                'strategy': 'adaptive_counter',
                'tactics': ['read_opponent', 'match_intensity', 'flexible_approach'],
                'timing': 'throughout_battle',
                'key_actions': ['balanced_play', 'opportunistic_strikes', 'tactical_switches']
            }
    
    def _predict_aggression_timeline(self, opponent_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Predict aggression timeline throughout battle"""
        aggression = opponent_data.get('aggression_score', 0.5)
        style = opponent_data.get('fight_style', 'balanced')
        
        timeline = []
        
        # Opening phase (0-30% of battle)
        if style == 'aggressive':
            timeline.append({'phase': 'opening', 'aggression': min(aggression * 1.3, 1.0), 'duration': '0-30%'})
        else:
            timeline.append({'phase': 'opening', 'aggression': aggression * 0.8, 'duration': '0-30%'})
        
        # Mid phase (30-70% of battle)
        timeline.append({'phase': 'mid', 'aggression': aggression, 'duration': '30-70%'})
        
        # End phase (70-100% of battle)
        if aggression > 0.6:
            timeline.append({'phase': 'end', 'aggression': min(aggression * 1.2, 1.0), 'duration': '70-100%'})
        else:
            timeline.append({'phase': 'end', 'aggression': aggression * 0.9, 'duration': '70-100%'})
        
        return timeline


# Global instance
battle_intelligence = BattleIntelligence()

