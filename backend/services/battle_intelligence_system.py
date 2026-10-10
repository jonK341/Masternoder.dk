"""
Battle Intelligence System
AI-powered intelligence for different battle modes and strategies
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import random
import math


class BattleIntelligenceSystem:
    """Intelligent battle system with mode-specific logic"""
    
    def __init__(self):
        self.battle_history = {}  # {user_id: [battles]}
        self.strategy_profiles = {}  # {user_id: StrategyProfile}
        self.opponent_analysis = {}  # {opponent_id: Analysis}
        
    def analyze_opponent(self, opponent_id: str, user_id: str) -> Dict[str, Any]:
        """Analyze opponent and provide intelligence"""
        # Get opponent battle history
        opponent_history = self.battle_history.get(opponent_id, [])
        
        # Calculate statistics
        total_battles = len(opponent_history)
        wins = sum(1 for b in opponent_history if b.get('winner_id') == opponent_id)
        losses = total_battles - wins
        win_rate = (wins / total_battles * 100) if total_battles > 0 else 50
        
        # Analyze patterns
        preferred_difficulty = self._analyze_preferred_difficulty(opponent_history)
        preferred_strategy = self._analyze_preferred_strategy(opponent_history)
        weakness_patterns = self._identify_weaknesses(opponent_history)
        
        # Calculate win probability
        user_profile = self.strategy_profiles.get(user_id, {})
        win_probability = self._calculate_win_probability(user_profile, {
            'win_rate': win_rate,
            'total_battles': total_battles,
            'preferred_strategy': preferred_strategy
        })
        
        # Risk assessment
        risk_level = self._assess_risk(win_rate, total_battles, user_profile)
        
        return {
            'success': True,
            'opponent_id': opponent_id,
            'statistics': {
                'total_battles': total_battles,
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 2)
            },
            'analysis': {
                'preferred_difficulty': preferred_difficulty,
                'preferred_strategy': preferred_strategy,
                'weakness_patterns': weakness_patterns,
                'win_probability': round(win_probability, 2),
                'risk_level': risk_level,
                'recommendation': self._get_recommendation(win_probability, risk_level)
            }
        }
    
    def get_mode_intelligence(self, mode: str, user_id: str) -> Dict[str, Any]:
        """Get intelligence specific to battle mode"""
        try:
            user_profile = self.strategy_profiles.get(user_id, {})
            user_history = self.battle_history.get(user_id, [])
            
            mode_intelligence = {
                'quick': self._get_quick_battle_intelligence(user_profile, user_history),
                'tournament': self._get_tournament_intelligence(user_profile, user_history),
                'pvp': self._get_pvp_intelligence(user_profile, user_history),
                'ranked': self._get_ranked_intelligence(user_profile, user_history)
            }
            
            intelligence = mode_intelligence.get(mode, {})
            if not intelligence:
                # Return default intelligence if mode not found
                intelligence = {
                    'mode': mode,
                    'focus': 'general',
                    'recommendations': ['Focus on improving skills', 'Practice regularly', 'Analyze your battles'],
                    'stats': {}
                }
            
            return {
                'success': True,
                'mode': mode,
                'intelligence': intelligence,
                'recommendations': self._get_mode_recommendations(mode, user_profile)
            }
        except Exception as e:
            # Return safe default on error
            return {
                'success': True,
                'mode': mode,
                'intelligence': {
                    'mode': mode,
                    'focus': 'general',
                    'recommendations': ['Focus on improving skills', 'Practice regularly'],
                    'stats': {}
                },
                'recommendations': self._get_mode_recommendations(mode, {})
            }
    
    def recommend_strategy(self, user_id: str, battle_type: str, opponent_data: Dict = None) -> Dict[str, Any]:
        """Recommend optimal strategy based on context"""
        user_profile = self.strategy_profiles.get(user_id, {})
        user_history = self.battle_history.get(user_id, [])
        
        # Analyze user's past performance
        successful_strategies = self._analyze_successful_strategies(user_history)
        
        # Consider opponent if provided
        if opponent_data:
            counter_strategy = self._get_counter_strategy(opponent_data)
        else:
            counter_strategy = None
        
        # Recommend best strategy
        recommended = self._select_optimal_strategy(
            successful_strategies,
            counter_strategy,
            battle_type
        )
        
        return {
            'success': True,
            'recommended_strategy': recommended,
            'confidence': self._calculate_confidence(user_history, recommended),
            'alternatives': self._get_alternative_strategies(recommended, successful_strategies)
        }
    
    def _get_quick_battle_intelligence(self, profile: Dict, history: List) -> Dict[str, Any]:
        """Intelligence for quick battle mode"""
        recent_battles = [b for b in history if b.get('battle_type') == 'quick'][-10:]
        
        return {
            'mode': 'quick',
            'focus': 'speed',
            'recommendations': [
                'Fast decision-making',
                'Aggressive opening',
                'Quick resource allocation'
            ],
            'stats': {
                'quick_battles': len(recent_battles),
                'avg_duration': self._calculate_avg_duration(recent_battles),
                'success_rate': self._calculate_success_rate(recent_battles, profile.get('user_id', 'default_user'))
            }
        }
    
    def _get_tournament_intelligence(self, profile: Dict, history: List) -> Dict[str, Any]:
        """Intelligence for tournament mode"""
        tournament_battles = [b for b in history if b.get('battle_type') == 'tournament']
        
        return {
            'mode': 'tournament',
            'focus': 'endurance',
            'recommendations': [
                'Long-term strategy',
                'Resource conservation',
                'Progressive difficulty'
            ],
            'stats': {
                'tournaments': len(tournament_battles),
                'best_placement': self._get_best_placement(tournament_battles),
                'avg_rounds': self._calculate_avg_rounds(tournament_battles)
            }
        }
    
    def _get_pvp_intelligence(self, profile: Dict, history: List) -> Dict[str, Any]:
        """Intelligence for PVP mode"""
        pvp_battles = [b for b in history if b.get('battle_type') == 'pvp']
        
        return {
            'mode': 'pvp',
            'focus': 'adaptation',
            'recommendations': [
                'Real-time adaptation',
                'Opponent behavior analysis',
                'Dynamic counter-strategies'
            ],
            'stats': {
                'pvp_battles': len(pvp_battles),
                'win_rate': self._calculate_win_rate(pvp_battles, profile.get('user_id', 'default_user')),
                'avg_response_time': self._calculate_avg_response_time(pvp_battles)
            }
        }
    
    def _get_ranked_intelligence(self, profile: Dict, history: List) -> Dict[str, Any]:
        """Intelligence for ranked mode"""
        ranked_battles = [b for b in history if b.get('battle_type') == 'ranked']
        
        return {
            'mode': 'ranked',
            'focus': 'skill',
            'recommendations': [
                'Skill-based matching',
                'Consistent performance',
                'Ranking optimization'
            ],
            'stats': {
                'ranked_battles': len(ranked_battles),
                'current_rank': profile.get('rank', 'unranked'),
                'rank_progress': self._calculate_rank_progress(ranked_battles)
            }
        }
    
    def _calculate_win_probability(self, user_profile: Dict, opponent_data: Dict) -> float:
        """Calculate probability of winning against opponent"""
        user_win_rate = user_profile.get('win_rate', 50)
        opponent_win_rate = opponent_data.get('win_rate', 50)
        
        # Base probability
        base_prob = 50
        
        # Adjust based on win rates
        win_rate_diff = user_win_rate - opponent_win_rate
        adjusted_prob = base_prob + (win_rate_diff * 0.5)
        
        # Clamp between 10% and 90%
        return max(10, min(90, adjusted_prob))
    
    def _assess_risk(self, opponent_win_rate: float, opponent_battles: int, user_profile: Dict) -> str:
        """Assess risk level of facing opponent"""
        user_win_rate = user_profile.get('win_rate', 50)
        
        if opponent_win_rate > 70 and opponent_battles > 20:
            return 'high'
        elif opponent_win_rate > user_win_rate + 10:
            return 'medium-high'
        elif opponent_win_rate < user_win_rate - 10:
            return 'low'
        else:
            return 'medium'
    
    def _get_recommendation(self, win_probability: float, risk_level: str) -> str:
        """Get recommendation based on analysis"""
        if win_probability > 70 and risk_level in ['low', 'medium']:
            return 'highly_recommended'
        elif win_probability > 50:
            return 'recommended'
        elif win_probability > 30:
            return 'challenging'
        else:
            return 'not_recommended'
    
    def _analyze_preferred_difficulty(self, history: List) -> str:
        """Analyze opponent's preferred difficulty"""
        difficulties = [b.get('difficulty', 'balanced') for b in history]
        if not difficulties:
            return 'balanced'
        return max(set(difficulties), key=difficulties.count)
    
    def _analyze_preferred_strategy(self, history: List) -> str:
        """Analyze opponent's preferred strategy"""
        strategies = [b.get('strategy', 'balanced') for b in history]
        if not strategies:
            return 'balanced'
        return max(set(strategies), key=strategies.count)
    
    def _identify_weaknesses(self, history: List) -> List[str]:
        """Identify opponent weaknesses from battle history"""
        # Analyze losses to find patterns
        losses = [b for b in history if b.get('outcome') == 'defeat']
        weakness_patterns = []
        
        if len(losses) > 3:
            # Find common patterns in losses
            weakness_patterns.append('vulnerable_to_aggressive')
        
        return weakness_patterns
    
    def _analyze_successful_strategies(self, history: List) -> List[Dict]:
        """Analyze which strategies have been most successful"""
        wins = [b for b in history if b.get('outcome') == 'victory']
        strategy_success = {}
        
        for battle in wins:
            strategy = battle.get('strategy', 'balanced')
            strategy_success[strategy] = strategy_success.get(strategy, 0) + 1
        
        return sorted(strategy_success.items(), key=lambda x: x[1], reverse=True)
    
    def _get_counter_strategy(self, opponent_data: Dict) -> str:
        """Get counter strategy for opponent"""
        opponent_strategy = opponent_data.get('preferred_strategy', 'balanced')
        
        counter_map = {
            'aggressive': 'defensive',
            'defensive': 'tactical',
            'tactical': 'aggressive',
            'balanced': 'tactical'
        }
        
        return counter_map.get(opponent_strategy, 'balanced')
    
    def _select_optimal_strategy(self, successful: List, counter: Optional[str], battle_type: str) -> str:
        """Select optimal strategy"""
        if counter and successful:
            # Prefer counter strategy if user has experience with it
            for strategy, count in successful:
                if strategy == counter:
                    return strategy
        
        # Return most successful strategy
        if successful:
            return successful[0][0]
        
        return 'balanced'
    
    def _calculate_confidence(self, history: List, strategy: str) -> float:
        """Calculate confidence in strategy recommendation"""
        strategy_battles = [b for b in history if b.get('strategy') == strategy]
        if not strategy_battles:
            return 0.5
        
        wins = sum(1 for b in strategy_battles if b.get('outcome') == 'victory')
        return wins / len(strategy_battles)
    
    def _get_alternative_strategies(self, recommended: str, successful: List) -> List[str]:
        """Get alternative strategies"""
        alternatives = []
        for strategy, _ in successful[:3]:
            if strategy != recommended:
                alternatives.append(strategy)
        return alternatives
    
    def _calculate_avg_duration(self, battles: List) -> float:
        """Calculate average battle duration"""
        if not battles:
            return 0
        durations = [b.get('duration', 0) for b in battles]
        return sum(durations) / len(durations) if durations else 0
    
    def _calculate_success_rate(self, battles: List, user_id: str) -> float:
        """Calculate success rate"""
        if not battles:
            return 0
        wins = sum(1 for b in battles if b.get('winner_id') == user_id)
        return (wins / len(battles) * 100) if battles else 0
    
    def _calculate_win_rate(self, battles: List, user_id: str) -> float:
        """Calculate win rate"""
        return self._calculate_success_rate(battles, user_id)
    
    def _get_best_placement(self, battles: List) -> int:
        """Get best tournament placement"""
        placements = [b.get('placement', 999) for b in battles]
        return min(placements) if placements else 999
    
    def _calculate_avg_rounds(self, battles: List) -> float:
        """Calculate average rounds in tournament"""
        if not battles:
            return 0
        rounds = [b.get('rounds', 1) for b in battles]
        return sum(rounds) / len(rounds) if rounds else 0
    
    def _calculate_avg_response_time(self, battles: List) -> float:
        """Calculate average response time"""
        if not battles:
            return 0
        response_times = [b.get('response_time', 0) for b in battles]
        return sum(response_times) / len(response_times) if response_times else 0
    
    def get_agent_battle_strategy(self, user_id: str, agent_id: str, battle_type: str, 
                                 opponent_data: Dict = None) -> Dict[str, Any]:
        """
        Get battle strategy recommendations from agent
        """
        try:
            from backend.services.agent_system import agent_system
            
            # Get agent
            agent = agent_system.get_agent(agent_id)
            if not agent:
                return {'error': 'Agent not found'}
            
            # Get agent's battle-related memories
            agent_memories = agent.get('visual_memory', [])
            battle_memories = [m for m in agent_memories if m.get('category') == 'battle' or m.get('type') == 'battle']
            
            # Get agent's battle skills
            agent_skills = agent.get('top50_skills', [])
            battle_skills = [s for s in agent_skills if 'battle' in s.get('name', '').lower() or 'combat' in s.get('name', '').lower()]
            
            # Analyze agent's battle experience
            battle_experience = len(battle_memories)
            battle_skill_level = sum(s.get('level', 1) for s in battle_skills) / len(battle_skills) if battle_skills else 1
            
            # Get agent recommendations
            agent_recommendations = agent_system.get_smart_recommendations(agent_id, 'battle')
            
            # Generate strategy based on agent analysis
            strategy = {
                'agent_id': agent_id,
                'battle_type': battle_type,
                'agent_battle_experience': battle_experience,
                'agent_battle_skill_level': battle_skill_level,
                'recommended_approach': self._get_agent_approach(battle_experience, battle_skill_level),
                'agent_recommendations': agent_recommendations.get('recommendations', []),
                'suggested_tactics': self._get_agent_tactics(battle_type, battle_skill_level),
                'risk_assessment': self._get_agent_risk_assessment(battle_experience, battle_skill_level)
            }
            
            # If opponent data provided, get counter-strategy
            if opponent_data:
                strategy['counter_strategy'] = self._get_agent_counter_strategy(agent, opponent_data)
            
            return {
                'success': True,
                'user_id': user_id,
                'agent_id': agent_id,
                'strategy': strategy,
                'confidence': min(0.9, (battle_experience / 50.0) + (battle_skill_level / 20.0))
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_agent_approach(self, experience: int, skill_level: float) -> str:
        """Get recommended approach based on agent experience"""
        if experience > 50 and skill_level > 15:
            return 'aggressive'
        elif experience > 20 and skill_level > 10:
            return 'balanced'
        elif experience > 10:
            return 'defensive'
        else:
            return 'cautious'
    
    def _get_agent_tactics(self, battle_type: str, skill_level: float) -> List[str]:
        """Get suggested tactics from agent"""
        tactics = []
        
        if skill_level > 15:
            tactics.extend(['advanced_combos', 'predictive_play', 'resource_optimization'])
        elif skill_level > 10:
            tactics.extend(['combo_attacks', 'defensive_positioning', 'timing_optimization'])
        else:
            tactics.extend(['basic_attacks', 'defensive_play', 'resource_management'])
        
        if battle_type == 'quick':
            tactics.append('fast_execution')
        elif battle_type == 'tournament':
            tactics.append('endurance_strategy')
        elif battle_type == 'pvp':
            tactics.append('psychological_play')
        
        return tactics
    
    def _get_agent_risk_assessment(self, experience: int, skill_level: float) -> Dict[str, Any]:
        """Get risk assessment from agent"""
        risk_score = max(0, min(100, 50 - (experience * 0.5) - (skill_level * 2)))
        
        return {
            'risk_level': 'low' if risk_score < 30 else 'medium' if risk_score < 60 else 'high',
            'risk_score': risk_score,
            'confidence': min(100, experience * 2 + skill_level * 5),
            'recommendation': 'proceed' if risk_score < 50 else 'caution' if risk_score < 70 else 'avoid'
        }
    
    def _get_agent_counter_strategy(self, agent: Dict, opponent_data: Dict) -> Dict[str, Any]:
        """Get counter-strategy based on agent analysis and opponent data"""
        opponent_win_rate = opponent_data.get('win_rate', 50)
        opponent_strategy = opponent_data.get('preferred_strategy', 'balanced')
        
        # Agent's preferred strategy
        agent_skills = agent.get('top50_skills', [])
        battle_skills = [s for s in agent_skills if 'battle' in s.get('name', '').lower()]
        
        counter_strategies = {
            'aggressive': 'defensive',
            'defensive': 'aggressive',
            'balanced': 'adaptive',
            'adaptive': 'unpredictable'
        }
        
        recommended_counter = counter_strategies.get(opponent_strategy, 'balanced')
        
        return {
            'opponent_strategy': opponent_strategy,
            'recommended_counter': recommended_counter,
            'reasoning': f"Opponent uses {opponent_strategy} strategy. Counter with {recommended_counter} approach.",
            'effectiveness': 0.7 if opponent_win_rate < 60 else 0.5
        }
    
    def get_agent_battle_recommendations(self, user_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Get comprehensive battle recommendations from agent
        """
        try:
            from backend.services.agent_system import agent_system
            
            agent = agent_system.get_agent(agent_id)
            if not agent:
                return {'error': 'Agent not found'}
            
            # Get user's battle history
            user_history = self.battle_history.get(user_id, [])
            
            # Analyze with agent
            recommendations = []
            
            # Recommendation 1: Battle type
            battle_type_performance = {}
            for battle in user_history[-20:]:
                battle_type = battle.get('battle_type', 'quick')
                won = battle.get('winner_id') == user_id
                if battle_type not in battle_type_performance:
                    battle_type_performance[battle_type] = {'wins': 0, 'total': 0}
                battle_type_performance[battle_type]['total'] += 1
                if won:
                    battle_type_performance[battle_type]['wins'] += 1
            
            best_type = max(battle_type_performance.items(), 
                          key=lambda x: x[1]['wins'] / x[1]['total'] if x[1]['total'] > 0 else 0,
                          default=('quick', {'wins': 0, 'total': 0}))
            
            recommendations.append({
                'type': 'battle_type',
                'title': 'Optimal Battle Type',
                'description': f"Your best performance is in {best_type[0]} battles with {best_type[1]['wins']}/{best_type[1]['total']} wins.",
                'action': f"Focus on {best_type[0]} battles",
                'priority': 'high',
                'expected_benefit': 'Higher win rate'
            })
            
            # Recommendation 2: Strategy improvement
            recent_losses = [b for b in user_history[-10:] if b.get('winner_id') != user_id]
            if recent_losses:
                recommendations.append({
                    'type': 'strategy',
                    'title': 'Improve Battle Strategy',
                    'description': f"You've lost {len(recent_losses)} recent battles. Consider adjusting your strategy.",
                    'action': 'Review battle history and adapt strategy',
                    'priority': 'high',
                    'expected_benefit': 'Better win rate'
                })
            
            # Recommendation 3: Agent skill development
            agent_skills = agent.get('top50_skills', [])
            battle_skills = [s for s in agent_skills if 'battle' in s.get('name', '').lower()]
            if len(battle_skills) < 5:
                recommendations.append({
                    'type': 'skills',
                    'title': 'Develop Battle Skills',
                    'description': f"Your agent has {len(battle_skills)} battle skills. Develop more for better performance.",
                    'action': 'Train agent in battle-related activities',
                    'priority': 'medium',
                    'expected_benefit': 'Improved battle performance'
                })
            
            # Recommendation 4: Timing
            if user_history:
                avg_time = self._calculate_avg_duration(user_history[-10:])
                if avg_time > 300:  # 5 minutes
                    recommendations.append({
                        'type': 'timing',
                        'title': 'Optimize Battle Duration',
                        'description': f"Your battles average {avg_time:.0f} seconds. Faster battles can improve efficiency.",
                        'action': 'Focus on quicker decision-making',
                        'priority': 'medium',
                        'expected_benefit': 'More battles per session'
                    })
            
            return {
                'success': True,
                'user_id': user_id,
                'agent_id': agent_id,
                'recommendations': recommendations,
                'total_recommendations': len(recommendations),
                'agent_battle_experience': len([m for m in agent.get('visual_memory', []) if m.get('category') == 'battle']),
                'agent_battle_skills': len(battle_skills)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_battle_with_agent(self, user_id: str, agent_id: str, battle_id: str) -> Dict[str, Any]:
        """
        Analyze a battle using agent intelligence
        """
        try:
            from backend.services.agent_system import agent_system
            
            agent = agent_system.get_agent(agent_id)
            if not agent:
                return {'error': 'Agent not found'}
            
            # Find battle in history
            user_history = self.battle_history.get(user_id, [])
            battle = next((b for b in user_history if b.get('battle_id') == battle_id), None)
            
            if not battle:
                return {'error': 'Battle not found'}
            
            # Analyze with agent
            analysis = {
                'battle_id': battle_id,
                'battle_type': battle.get('battle_type'),
                'result': battle.get('result'),
                'agent_insights': [],
                'improvements': [],
                'lessons_learned': []
            }
            
            # Get insights from agent's battle memories
            agent_memories = agent.get('visual_memory', [])
            similar_battles = [m for m in agent_memories if m.get('data', {}).get('battle_type') == battle.get('battle_type')]
            
            if similar_battles:
                analysis['agent_insights'].append({
                    'type': 'pattern_recognition',
                    'insight': f"Agent has {len(similar_battles)} similar battle memories",
                    'relevance': 'high'
                })
            
            # Generate improvements
            if battle.get('result') != 'victory':
                analysis['improvements'].append({
                    'area': 'strategy',
                    'suggestion': 'Review battle strategy and adapt for next time',
                    'priority': 'high'
                })
            
            # Save battle as visual memory for agent
            try:
                agent_system.save_visual_memory(agent_id, 'battle', {
                    'battle_id': battle_id,
                    'battle_type': battle.get('battle_type'),
                    'result': battle.get('result'),
                    'timestamp': battle.get('completed_at'),
                    'analysis': analysis
                })
            except:
                pass
            
            return {
                'success': True,
                'user_id': user_id,
                'agent_id': agent_id,
                'analysis': analysis
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_rank_progress(self, battles: List) -> Dict[str, Any]:
        """Calculate rank progress"""
        if not battles:
            return {'current': 0, 'change': 0}
        
        recent = battles[-1] if battles else {}
        return {
            'current': recent.get('rank', 0),
            'change': recent.get('rank_change', 0)
        }
    
    def calculate_win_probability(self, user_id: str, opponent_id: str = None, 
                                battle_type: str = 'quick', user_stats: Dict = None,
                                opponent_stats: Dict = None) -> Dict[str, Any]:
        """
        Calculate win probability for a battle
        """
        try:
            # Get user's battle history
            user_history = self.battle_history.get(user_id, [])
            user_wins = sum(1 for b in user_history if b.get('winner_id') == user_id)
            user_total = len(user_history)
            user_win_rate = (user_wins / user_total * 100) if user_total > 0 else 50.0
            
            # Get opponent stats if provided
            if opponent_id:
                opponent_history = self.battle_history.get(opponent_id, [])
                opponent_wins = sum(1 for b in opponent_history if b.get('winner_id') == opponent_id)
                opponent_total = len(opponent_history)
                opponent_win_rate = (opponent_wins / opponent_total * 100) if opponent_total > 0 else 50.0
            elif opponent_stats:
                opponent_win_rate = opponent_stats.get('win_rate', 50.0)
            else:
                opponent_win_rate = 50.0  # Default
            
            # Base probability from win rates
            base_probability = (user_win_rate / (user_win_rate + opponent_win_rate)) * 100 if (user_win_rate + opponent_win_rate) > 0 else 50.0
            
            # Adjust for battle type performance
            battle_type_history = [b for b in user_history if b.get('battle_type') == battle_type]
            if battle_type_history:
                type_wins = sum(1 for b in battle_type_history if b.get('winner_id') == user_id)
                type_win_rate = (type_wins / len(battle_type_history) * 100) if battle_type_history else 50.0
                # Adjust probability based on type performance
                type_adjustment = (type_win_rate - user_win_rate) * 0.3  # 30% weight
                base_probability += type_adjustment
            
            # Adjust for user stats if provided
            if user_stats:
                level = user_stats.get('level', 1)
                level_bonus = (level - 1) * 0.5  # 0.5% per level above 1
                base_probability += level_bonus
                
                streak = user_stats.get('streak', 0)
                streak_bonus = streak * 0.3  # 0.3% per streak
                base_probability += streak_bonus
            
            # Adjust for opponent stats if provided
            if opponent_stats:
                opponent_level = opponent_stats.get('level', 1)
                level_penalty = (opponent_level - 1) * 0.3  # Penalty for higher level opponent
                base_probability -= level_penalty
            
            # Clamp probability between 5% and 95%
            final_probability = max(5.0, min(95.0, base_probability))
            
            # Calculate confidence based on data available
            confidence = min(100, (user_total * 2) + (len(battle_type_history) * 3))
            
            return {
                'success': True,
                'user_id': user_id,
                'opponent_id': opponent_id,
                'battle_type': battle_type,
                'win_probability': round(final_probability, 2),
                'confidence': round(confidence, 2),
                'factors': {
                    'user_win_rate': round(user_win_rate, 2),
                    'opponent_win_rate': round(opponent_win_rate, 2),
                    'battle_type_performance': len(battle_type_history),
                    'user_total_battles': user_total,
                    'user_wins': user_wins
                },
                'recommendation': 'favorable' if final_probability > 60 else 'unfavorable' if final_probability < 40 else 'balanced'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate_battle_rewards(self, battle_type: str, victory: bool = True,
                                user_level: int = 1, streak: int = 0,
                                difficulty: str = 'normal', multipliers: Dict = None) -> Dict[str, Any]:
        """
        Calculate point rewards for a battle
        """
        try:
            # Base rewards by battle type
            base_rewards = {
                'quick': {'victory': 50, 'defeat': 10},
                'tournament': {'victory': 150, 'defeat': 30},
                'pvp': {'victory': 100, 'defeat': 20},
                'ranked': {'victory': 200, 'defeat': 40},
                'insane_lock': {'victory': 100, 'defeat': 10},
                'ultimate_challenge': {'victory': 150, 'defeat': 15},
                'death_match': {'victory': 200, 'defeat': 20},
                'survival_mode': {'victory': 250, 'defeat': 25},
                'boss_raid': {'victory': 300, 'defeat': 30}
            }
            
            # Get base reward
            battle_rewards = base_rewards.get(battle_type, {'victory': 50, 'defeat': 10})
            base_points = battle_rewards['victory'] if victory else battle_rewards['defeat']
            
            # Difficulty multipliers
            difficulty_multipliers = {
                'easy': 0.8,
                'normal': 1.0,
                'hard': 1.5,
                'extreme': 2.0,
                'insane': 3.0
            }
            difficulty_mult = difficulty_multipliers.get(difficulty, 1.0)
            
            # Level multiplier (0.5% per level above 1)
            level_mult = 1.0 + ((user_level - 1) * 0.005)
            
            # Streak multiplier (1% per streak)
            streak_mult = 1.0 + (streak * 0.01)
            
            # Apply custom multipliers if provided
            custom_mult = 1.0
            if multipliers:
                for mult_value in multipliers.values():
                    custom_mult *= mult_value
            
            # Calculate total multiplier
            total_multiplier = difficulty_mult * level_mult * streak_mult * custom_mult
            
            # Calculate final rewards
            final_points = int(base_points * total_multiplier)
            
            # Breakdown by point type
            point_breakdown = {
                'base_points': base_points,
                'xp_points': int(final_points * 0.6),
                'battle_points': int(final_points * 0.4),
                'activity_points': int(final_points * 0.1)
            }
            
            return {
                'success': True,
                'battle_type': battle_type,
                'victory': victory,
                'base_points': base_points,
                'total_points': final_points,
                'point_breakdown': point_breakdown,
                'multipliers': {
                    'difficulty': difficulty_mult,
                    'level': level_mult,
                    'streak': streak_mult,
                    'custom': custom_mult,
                    'total': total_multiplier
                },
                'calculation': {
                    'formula': f'{base_points} * {total_multiplier:.2f} = {final_points}',
                    'breakdown': point_breakdown
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def optimize_battle_strategy(self, user_id: str, battle_type: str,
                               opponent_data: Dict = None, constraints: Dict = None) -> Dict[str, Any]:
        """
        Optimize battle strategy based on user history and opponent analysis
        """
        try:
            user_history = self.battle_history.get(user_id, [])
            battle_type_history = [b for b in user_history if b.get('battle_type') == battle_type]
            
            # Analyze successful strategies
            successful_battles = [b for b in battle_type_history if b.get('winner_id') == user_id]
            failed_battles = [b for b in battle_type_history if b.get('winner_id') != user_id]
            
            # Strategy patterns from successful battles
            successful_strategies = {}
            for battle in successful_battles[-10:]:
                strategy = battle.get('strategy', 'balanced')
                if strategy not in successful_strategies:
                    successful_strategies[strategy] = 0
                successful_strategies[strategy] += 1
            
            # Strategy patterns from failed battles (to avoid)
            failed_strategies = {}
            for battle in failed_battles[-10:]:
                strategy = battle.get('strategy', 'balanced')
                if strategy not in failed_strategies:
                    failed_strategies[strategy] = 0
                failed_strategies[strategy] += 1
            
            # Recommend optimal strategy
            best_strategy = max(successful_strategies.items(), key=lambda x: x[1], default=('balanced', 0))[0]
            
            # Counter-strategy if opponent data provided
            counter_strategy = None
            if opponent_data:
                opponent_strategy = opponent_data.get('preferred_strategy', 'balanced')
                counter_map = {
                    'aggressive': 'defensive',
                    'defensive': 'aggressive',
                    'balanced': 'adaptive',
                    'adaptive': 'unpredictable'
                }
                counter_strategy = counter_map.get(opponent_strategy, 'balanced')
            
            # Calculate expected win rate with recommended strategy
            strategy_win_rate = (successful_strategies.get(best_strategy, 0) / 
                                max(1, successful_strategies.get(best_strategy, 0) + failed_strategies.get(best_strategy, 0))) * 100
            
            # Resource allocation recommendations
            resource_recommendations = {
                'energy_allocation': 'high' if battle_type in ['boss_raid', 'survival_mode'] else 'medium',
                'time_investment': 'high' if battle_type in ['tournament', 'ranked'] else 'medium',
                'risk_tolerance': 'high' if strategy_win_rate > 60 else 'medium' if strategy_win_rate > 40 else 'low'
            }
            
            # Optimization score
            optimization_score = min(100, strategy_win_rate + (len(successful_battles) * 2))
            
            return {
                'success': True,
                'user_id': user_id,
                'battle_type': battle_type,
                'recommended_strategy': best_strategy,
                'counter_strategy': counter_strategy,
                'expected_win_rate': round(strategy_win_rate, 2),
                'strategy_analysis': {
                    'successful_strategies': successful_strategies,
                    'failed_strategies': failed_strategies,
                    'total_battles_analyzed': len(battle_type_history)
                },
                'resource_recommendations': resource_recommendations,
                'optimization_score': round(optimization_score, 2),
                'recommendations': [
                    f"Use {best_strategy} strategy for best results",
                    f"Expected win rate: {strategy_win_rate:.1f}%",
                    f"Resource allocation: {resource_recommendations['energy_allocation']}"
                ]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_battle_leaderboard(self, limit: int = 10, category: str = 'wins') -> Dict[str, Any]:
        """
        Get battle leaderboard with top players
        category: 'wins', 'win_rate', 'total_battles', 'streak'
        """
        try:
            # Collect all user battle statistics
            user_stats = {}
            
            for user_id, battles in self.battle_history.items():
                wins = sum(1 for b in battles if b.get('winner_id') == user_id)
                total = len(battles)
                win_rate = (wins / total * 100) if total > 0 else 0
                
                # Calculate current streak
                streak = 0
                for battle in reversed(battles[-10:]):  # Check last 10 battles
                    if battle.get('winner_id') == user_id:
                        streak += 1
                    else:
                        break
                
                user_stats[user_id] = {
                    'user_id': user_id,
                    'wins': wins,
                    'losses': total - wins,
                    'total_battles': total,
                    'win_rate': round(win_rate, 2),
                    'streak': streak
                }
            
            # Sort by category
            if category == 'wins':
                sorted_users = sorted(user_stats.values(), key=lambda x: x['wins'], reverse=True)
            elif category == 'win_rate':
                sorted_users = sorted(user_stats.values(), key=lambda x: x['win_rate'], reverse=True)
            elif category == 'total_battles':
                sorted_users = sorted(user_stats.values(), key=lambda x: x['total_battles'], reverse=True)
            elif category == 'streak':
                sorted_users = sorted(user_stats.values(), key=lambda x: x['streak'], reverse=True)
            else:
                sorted_users = sorted(user_stats.values(), key=lambda x: x['wins'], reverse=True)
            
            # Add ranks
            leaderboard = []
            for rank, user in enumerate(sorted_users[:limit], 1):
                user['rank'] = rank
                leaderboard.append(user)
            
            return {
                'success': True,
                'category': category,
                'leaderboard': leaderboard,
                'total_players': len(user_stats)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_recent_battles(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent battles across all users"""
        try:
            all_battles = []
            
            # Collect all battles
            for user_id, battles in self.battle_history.items():
                for battle in battles:
                    battle_copy = battle.copy()
                    battle_copy['user_id'] = user_id
                    all_battles.append(battle_copy)
            
            # Sort by timestamp (most recent first)
            all_battles.sort(
                key=lambda x: x.get('completed_at', x.get('timestamp', '')),
                reverse=True
            )
            
            # Get recent battles
            recent = all_battles[:limit]
            
            return {
                'success': True,
                'recent_battles': recent,
                'total_battles': len(all_battles)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_battle_statistics(self) -> Dict[str, Any]:
        """Get overall battle statistics"""
        try:
            total_battles = 0
            total_wins = 0
            battle_types = {}
            total_players = len(self.battle_history)
            
            # Collect statistics
            for user_id, battles in self.battle_history.items():
                total_battles += len(battles)
                wins = sum(1 for b in battles if b.get('winner_id') == user_id)
                total_wins += wins
                
                # Count by battle type
                for battle in battles:
                    battle_type = battle.get('battle_type', 'unknown')
                    if battle_type not in battle_types:
                        battle_types[battle_type] = {'count': 0, 'wins': 0}
                    battle_types[battle_type]['count'] += 1
                    if battle.get('winner_id') == user_id:
                        battle_types[battle_type]['wins'] += 1
            
            # Calculate overall win rate
            overall_win_rate = (total_wins / total_battles * 100) if total_battles > 0 else 0
            
            # Calculate battle type statistics
            type_stats = []
            for battle_type, stats in battle_types.items():
                win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
                type_stats.append({
                    'battle_type': battle_type,
                    'total_battles': stats['count'],
                    'wins': stats['wins'],
                    'win_rate': round(win_rate, 2)
                })
            
            type_stats.sort(key=lambda x: x['total_battles'], reverse=True)
            
            return {
                'success': True,
                'statistics': {
                    'total_battles': total_battles,
                    'total_wins': total_wins,
                    'total_losses': total_battles - total_wins,
                    'overall_win_rate': round(overall_win_rate, 2),
                    'total_players': total_players,
                    'average_battles_per_player': round(total_battles / total_players, 2) if total_players > 0 else 0
                },
                'battle_types': type_stats,
                'most_popular_type': type_stats[0]['battle_type'] if type_stats else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_mode_recommendations(self, mode: str, profile: Dict) -> List[str]:
        """Get recommendations for specific mode"""
        recommendations = {
            'quick': [
                'Focus on speed',
                'Use aggressive strategies',
                'Quick resource decisions'
            ],
            'tournament': [
                'Plan for multiple rounds',
                'Conserve resources',
                'Adapt to bracket'
            ],
            'pvp': [
                'Watch opponent patterns',
                'Adapt in real-time',
                'Counter their strategy'
            ],
            'ranked': [
                'Maintain consistency',
                'Focus on skill improvement',
                'Track ranking trends'
            ]
        }
        
        return recommendations.get(mode, [])


# Global instance
battle_intelligence_system = BattleIntelligenceSystem()

