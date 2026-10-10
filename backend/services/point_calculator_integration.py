"""
Point Calculator Integration
Connects point calculations to atomic calculator for precise math
"""
from typing import Dict, Any, Optional
from decimal import Decimal, getcontext

# Set precision for calculations
getcontext().prec = 50

class PointCalculatorIntegration:
    """Integrates point calculations with atomic calculator"""
    
    def __init__(self):
        try:
            from backend.services.atomic_calculator_hell_money import atomic_calculator_hell_money
            self.atomic_calculator = atomic_calculator_hell_money
        except ImportError:
            self.atomic_calculator = None
    
    def calculate_points_with_precision(self, base_points: float, 
                                       multipliers: Dict[str, float] = None) -> Dict[str, Any]:
        """Calculate points with atomic precision"""
        multipliers = multipliers or {}
        
        # Use atomic calculator if available
        if self.atomic_calculator:
            try:
                base_decimal = Decimal(str(base_points))
                
                # Apply multipliers using atomic calculator
                total_multiplier = Decimal('1.0')
                for mult_name, mult_value in multipliers.items():
                    total_multiplier *= Decimal(str(mult_value))
                
                final_points = base_decimal * total_multiplier
                
                # Use atomic calculator for final calculation
                result = self.atomic_calculator.atomic_calculate(
                    float(final_points),
                    'hell_money',
                    {'precision': 50}
                )
                
                if result.get('success'):
                    return {
                        'success': True,
                        'base_points': float(base_decimal),
                        'multipliers': multipliers,
                        'total_multiplier': float(total_multiplier),
                        'final_points': float(final_points),
                        'atomic_calculation': result.get('calculation', {}),
                        'precision': 50
                    }
            except Exception as e:
                print(f"Error in atomic calculation: {e}")
        
        # Fallback to standard calculation
        total_multiplier = 1.0
        for mult_value in multipliers.values():
            total_multiplier *= mult_value
        
        final_points = base_points * total_multiplier
        
        return {
            'success': True,
            'base_points': base_points,
            'multipliers': multipliers,
            'total_multiplier': total_multiplier,
            'final_points': final_points,
            'precision': 'standard'
        }
    
    def calculate_point_bonuses(self, base_points: float,
                               quality: float = 1.0,
                               difficulty: float = 1.0,
                               streak: int = 0,
                               level: int = 1) -> Dict[str, Any]:
        """Calculate point bonuses with atomic precision"""
        multipliers = {
            'quality': quality,
            'difficulty': difficulty,
            'streak': 1.0 + (streak * 0.01),  # 1% per streak
            'level': 1.0 + (level * 0.005)    # 0.5% per level
        }
        
        return self.calculate_points_with_precision(base_points, multipliers)
    
    def calculate_compound_points(self, initial_points: float,
                                rate: float = 0.1,
                                periods: int = 1) -> Dict[str, Any]:
        """Calculate compound points using atomic calculator"""
        if self.atomic_calculator:
            try:
                result = self.atomic_calculator.atomic_calculate(
                    initial_points,
                    'satan_compound',
                    {'rate': rate, 'periods': periods}
                )
                
                if result.get('success'):
                    return {
                        'success': True,
                        'initial_points': initial_points,
                        'rate': rate,
                        'periods': periods,
                        'final_points': result.get('calculation', {}).get('final_calculation', {}).get('final_total', initial_points),
                        'compound_calculation': result
                    }
            except Exception as e:
                print(f"Error in compound calculation: {e}")
        
        # Fallback
        final_points = initial_points * ((1 + rate) ** periods)
        return {
            'success': True,
            'initial_points': initial_points,
            'rate': rate,
            'periods': periods,
            'final_points': final_points
        }
    
    def predict_points(self, user_id: str, activity_type: str, 
                      base_points: float, days: int = 7) -> Dict[str, Any]:
        """
        Predict future points based on activity patterns
        """
        try:
            from backend.services.unified_points_database import unified_points_db
            from backend.services.point_history_tracking import point_history_tracking
            
            # Get historical data
            history_data = point_history_tracking.get_point_history(
                user_id, None, None, None, limit=1000
            )
            history = history_data.get('history', [])
            
            # Filter by activity type
            activity_history = [h for h in history if h.get('source', '').startswith(activity_type)]
            
            # Calculate average points per day
            if activity_history:
                daily_averages = {}
                for entry in activity_history[-30:]:  # Last 30 entries
                    date = entry.get('date', entry.get('timestamp', '')[:10])
                    if date not in daily_averages:
                        daily_averages[date] = []
                    daily_averages[date].append(entry.get('amount', 0))
                
                avg_per_day = sum(sum(amounts) for amounts in daily_averages.values()) / len(daily_averages) if daily_averages else base_points
            else:
                avg_per_day = base_points
            
            # Predict future points
            predicted_total = avg_per_day * days
            predicted_breakdown = []
            for day in range(1, days + 1):
                predicted_breakdown.append({
                    'day': day,
                    'predicted_points': avg_per_day,
                    'cumulative': avg_per_day * day
                })
            
            return {
                'success': True,
                'user_id': user_id,
                'activity_type': activity_type,
                'base_points': base_points,
                'prediction_period_days': days,
                'average_per_day': avg_per_day,
                'predicted_total': predicted_total,
                'predicted_breakdown': predicted_breakdown,
                'confidence': min(0.9, len(activity_history) / 100.0),  # Higher confidence with more history
                'based_on_history': len(activity_history)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def optimize_multipliers(self, base_points: float, 
                            available_multipliers: Dict[str, float],
                            target_points: Optional[float] = None) -> Dict[str, Any]:
        """
        Optimize multiplier combinations to achieve target points or maximize points
        """
        if target_points:
            # Find combination that gets closest to target
            best_combination = {}
            best_diff = float('inf')
            
            # Try different combinations
            for mult_name, mult_value in available_multipliers.items():
                test_points = base_points * mult_value
                diff = abs(test_points - target_points)
                if diff < best_diff:
                    best_diff = diff
                    best_combination = {mult_name: mult_value}
            
            # Try combinations
            mult_items = list(available_multipliers.items())
            for i, (name1, val1) in enumerate(mult_items):
                for name2, val2 in mult_items[i+1:]:
                    test_points = base_points * val1 * val2
                    diff = abs(test_points - target_points)
                    if diff < best_diff:
                        best_diff = diff
                        best_combination = {name1: val1, name2: val2}
            
            result_points = base_points
            for name, val in best_combination.items():
                result_points *= val
            
            return {
                'success': True,
                'base_points': base_points,
                'target_points': target_points,
                'optimized_combination': best_combination,
                'result_points': result_points,
                'difference': abs(result_points - target_points),
                'efficiency': 1.0 - (abs(result_points - target_points) / target_points) if target_points > 0 else 0
            }
        else:
            # Maximize points
            best_multiplier = max(available_multipliers.items(), key=lambda x: x[1])
            max_points = base_points * best_multiplier[1]
            
            # Try all multipliers combined
            all_mult = 1.0
            for val in available_multipliers.values():
                all_mult *= val
            max_all_points = base_points * all_mult
            
            return {
                'success': True,
                'base_points': base_points,
                'optimization_type': 'maximize',
                'best_single_multiplier': {best_multiplier[0]: best_multiplier[1]},
                'max_single_points': max_points,
                'all_multipliers_combined': dict(available_multipliers),
                'max_all_points': max_all_points,
                'recommendation': 'use_all' if max_all_points > max_points * 1.5 else 'use_single',
                'efficiency_gain': (max_all_points / max_points) if max_points > 0 else 1.0
            }
    
    def calculate_multiplier_combinations(self, base_points: float,
                                         multipliers: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate all possible multiplier combinations and their effects
        """
        combinations = []
        mult_items = list(multipliers.items())
        
        # Single multipliers
        for name, value in mult_items:
            combinations.append({
                'combination': {name: value},
                'total_multiplier': value,
                'result_points': base_points * value,
                'efficiency': value
            })
        
        # Pair combinations
        for i, (name1, val1) in enumerate(mult_items):
            for name2, val2 in mult_items[i+1:]:
                total_mult = val1 * val2
                combinations.append({
                    'combination': {name1: val1, name2: val2},
                    'total_multiplier': total_mult,
                    'result_points': base_points * total_mult,
                    'efficiency': total_mult
                })
        
        # All multipliers
        all_mult = 1.0
        for val in multipliers.values():
            all_mult *= val
        combinations.append({
            'combination': dict(multipliers),
            'total_multiplier': all_mult,
            'result_points': base_points * all_mult,
            'efficiency': all_mult
        })
        
        # Sort by efficiency
        combinations.sort(key=lambda x: x['efficiency'], reverse=True)
        
        return {
            'success': True,
            'base_points': base_points,
            'available_multipliers': multipliers,
            'total_combinations': len(combinations),
            'combinations': combinations,
            'best_combination': combinations[0] if combinations else None,
            'worst_combination': combinations[-1] if combinations else None
        }
    
    def suggest_optimization(self, user_id: str, current_points: float,
                           target_points: Optional[float] = None) -> Dict[str, Any]:
        """
        Suggest optimization strategies to increase points
        """
        try:
            from backend.services.unified_point_counter import unified_point_counter
            from backend.services.point_history_tracking import point_history_tracking
            
            # Get user's current state
            all_points = unified_point_counter.get_all_points(user_id)
            
            # Get activity history
            history_data = point_history_tracking.get_point_statistics(user_id, None, 30)
            
            suggestions = []
            
            # Analyze point sources
            by_source = history_data.get('by_source', {})
            top_sources = sorted(by_source.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            
            # Suggestion 1: Focus on top sources
            if top_sources:
                suggestions.append({
                    'type': 'focus_top_sources',
                    'priority': 'high',
                    'title': 'Focus on Top Point Sources',
                    'description': f"Your top source is '{top_sources[0][0]}' generating {top_sources[0][1]:.0f} points. Focus here for maximum gains.",
                    'expected_increase': top_sources[0][1] * 0.2,  # 20% increase
                    'action': f"Increase activity in {top_sources[0][0]}"
                })
            
            # Suggestion 2: Improve multipliers
            level = all_points.get('level', 1)
            if level < 10:
                suggestions.append({
                    'type': 'level_up',
                    'priority': 'high',
                    'title': 'Level Up for Multipliers',
                    'description': f'You are level {level}. Leveling up will unlock better multipliers.',
                    'expected_increase': current_points * 0.1,  # 10% increase per level
                    'action': 'Complete more activities to level up'
                })
            
            # Suggestion 3: Maintain streaks
            battle_streak = all_points.get('battle_streak', 0)
            if battle_streak < 5:
                suggestions.append({
                    'type': 'maintain_streak',
                    'priority': 'medium',
                    'title': 'Build Win Streaks',
                    'description': f'Your current streak is {battle_streak}. Building longer streaks provides bonus multipliers.',
                    'expected_increase': current_points * 0.05 * (5 - battle_streak),  # 5% per missing streak
                    'action': 'Win consecutive battles to build streaks'
                })
            
            # Suggestion 4: Complete achievements
            achievements_earned = all_points.get('achievements_earned', 0)
            if achievements_earned < 10:
                suggestions.append({
                    'type': 'complete_achievements',
                    'priority': 'medium',
                    'title': 'Complete More Achievements',
                    'description': f'You have {achievements_earned} achievements. More achievements unlock permanent bonuses.',
                    'expected_increase': 50 * (10 - achievements_earned),  # 50 points per achievement
                    'action': 'Focus on completing achievement requirements'
                })
            
            # Calculate total potential increase
            total_potential = sum(s.get('expected_increase', 0) for s in suggestions)
            
            return {
                'success': True,
                'user_id': user_id,
                'current_points': current_points,
                'target_points': target_points,
                'suggestions': suggestions,
                'total_suggestions': len(suggestions),
                'total_potential_increase': total_potential,
                'projected_total': current_points + total_potential,
                'optimization_score': min(100, (total_potential / current_points * 100) if current_points > 0 else 0)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
point_calculator_integration = PointCalculatorIntegration()
