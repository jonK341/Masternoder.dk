"""
Dashboard Upgrades Service
Provides enhanced dashboard features including real-time updates,
advanced visualizations, and future tech integration
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

try:
    from backend.services.future_tech_integration_service import future_tech_integration_service
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    FUTURE_TECH_AVAILABLE = True
    CALCULATOR_AVAILABLE = True
except ImportError:
    future_tech_integration_service = None
    advanced_intelligent_calculator = None
    FUTURE_TECH_AVAILABLE = False
    CALCULATOR_AVAILABLE = False


class DashboardUpgrades:
    """
    Enhanced dashboard features:
    - Real-time data updates
    - Advanced visualizations
    - Performance metrics
    - Future tech integration
    - Calculator-powered insights
    """
    
    def __init__(self):
        self.update_cache = {}
        self.cache_ttl = 30  # 30 seconds cache
        self.metrics_history = defaultdict(list)
    
    def enhance_dashboard_data(self, user_id: str, 
                              base_dashboard: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance dashboard data with upgrades
        
        Args:
            user_id: User identifier
            base_dashboard: Base dashboard data
        """
        enhanced = base_dashboard.copy()
        
        # Add real-time metrics
        enhanced['real_time_metrics'] = self._get_realtime_metrics(user_id)
        
        # Add performance insights
        enhanced['performance_insights'] = self._calculate_performance_insights(user_id)
        
        # Add trend analysis
        enhanced['trends'] = self._calculate_trends(user_id)
        
        # Add calculator-powered insights
        if CALCULATOR_AVAILABLE:
            try:
                from backend.services.unified_point_counter import unified_point_counter
                point_data = unified_point_counter.get_all_points(user_id) or {}
                calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                    point_data, user_id
                )
                enhanced['calculator_insights'] = {
                    'confidence_score': calc_result.get('confidence_score', 0),
                    'recommendations': self._generate_calculator_recommendations(calc_result),
                    'growth_projection': self._calculate_growth_projection(calc_result)
                }
            except Exception as e:
                print(f"[DashboardUpgrades] Error adding calculator insights: {e}")
        
        # Add future tech summary
        if FUTURE_TECH_AVAILABLE:
            try:
                enhanced['future_tech_summary'] = self._get_future_tech_summary(user_id)
            except Exception as e:
                print(f"[DashboardUpgrades] Error adding future tech summary: {e}")
        
        # Add update timestamp
        enhanced['last_updated'] = datetime.utcnow().isoformat()
        enhanced['update_interval'] = self.cache_ttl
        
        return enhanced
    
    def _get_realtime_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get real-time metrics for dashboard"""
        return {
            'active_generations': self._count_active_generations(user_id),
            'recent_activity': self._get_recent_activity(user_id),
            'system_status': 'operational',
            'last_check': datetime.utcnow().isoformat()
        }
    
    def _count_active_generations(self, user_id: str) -> int:
        """Count active video generations"""
        try:
            from src.db.models import db, Documentary
            count = Documentary.query.filter_by(
                user_id=user_id,
                status='processing'
            ).count()
            return count
        except Exception:
            return 0
    
    def _get_recent_activity(self, user_id: str) -> List[Dict[str, Any]]:
        """Get recent activity for user"""
        try:
            from src.db.models import db, Documentary
            recent = Documentary.query.filter_by(
                user_id=user_id
            ).order_by(Documentary.created_at.desc()).limit(5).all()
            
            return [
                {
                    'type': 'video_generation',
                    'title': doc.title or 'Untitled',
                    'status': doc.status,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None
                }
                for doc in recent
            ]
        except Exception:
            return []
    
    def _calculate_performance_insights(self, user_id: str) -> Dict[str, Any]:
        """Calculate performance insights"""
        try:
            from src.db.models import db, Documentary
            from sqlalchemy import func
            
            # Get completion rate
            total = Documentary.query.filter_by(user_id=user_id).count()
            completed = Documentary.query.filter_by(
                user_id=user_id,
                status='completed'
            ).count()
            completion_rate = (completed / total * 100) if total > 0 else 0
            
            # Get average quality
            avg_quality = db.session.query(
                func.avg(Documentary.quality_score)
            ).filter_by(user_id=user_id, status='completed').scalar() or 0
            
            # Get average generation time (if available)
            recent_completed = Documentary.query.filter_by(
                user_id=user_id,
                status='completed'
            ).order_by(Documentary.completed_at.desc()).limit(10).all()
            
            avg_generation_time = 0
            if recent_completed:
                times = []
                for doc in recent_completed:
                    if doc.created_at and doc.completed_at:
                        delta = doc.completed_at - doc.created_at
                        times.append(delta.total_seconds())
                if times:
                    avg_generation_time = sum(times) / len(times)
            
            return {
                'completion_rate': round(completion_rate, 2),
                'average_quality_score': round(avg_quality, 3),
                'average_generation_time_seconds': round(avg_generation_time, 0),
                'total_generations': total,
                'completed_generations': completed,
                'performance_grade': self._calculate_performance_grade(completion_rate, avg_quality)
            }
        except Exception as e:
            print(f"[DashboardUpgrades] Error calculating performance insights: {e}")
            return {}
    
    def _calculate_performance_grade(self, completion_rate: float, avg_quality: float) -> str:
        """Calculate performance grade"""
        score = (completion_rate * 0.5) + (avg_quality * 100 * 0.5)
        
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 60:
            return 'C'
        else:
            return 'D'
    
    def _calculate_trends(self, user_id: str) -> Dict[str, Any]:
        """Calculate trends over time"""
        try:
            from src.db.models import db, Documentary
            from datetime import datetime, timedelta
            
            now = datetime.utcnow()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            # Recent activity
            recent_count = Documentary.query.filter(
                Documentary.user_id == user_id,
                Documentary.created_at >= week_ago
            ).count()
            
            # Previous week
            two_weeks_ago = now - timedelta(days=14)
            previous_count = Documentary.query.filter(
                Documentary.user_id == user_id,
                Documentary.created_at >= two_weeks_ago,
                Documentary.created_at < week_ago
            ).count()
            
            # Calculate trend
            trend_direction = 'stable'
            trend_percentage = 0
            if previous_count > 0:
                trend_percentage = ((recent_count - previous_count) / previous_count) * 100
                if trend_percentage > 10:
                    trend_direction = 'increasing'
                elif trend_percentage < -10:
                    trend_direction = 'decreasing'
            
            return {
                'recent_activity_count': recent_count,
                'previous_period_count': previous_count,
                'trend_direction': trend_direction,
                'trend_percentage': round(trend_percentage, 1),
                'period': 'weekly'
            }
        except Exception as e:
            print(f"[DashboardUpgrades] Error calculating trends: {e}")
            return {}
    
    def _generate_calculator_recommendations(self, calc_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on calculator results"""
        recommendations = []
        
        confidence = calc_result.get('confidence_score', 0)
        if confidence < 0.7:
            recommendations.append("Consider validating point calculations for better accuracy")
        
        multipliers = calc_result.get('intelligent_multipliers', {})
        if not multipliers:
            recommendations.append("No intelligent multipliers detected - explore advanced features")
        
        final_calc = calc_result.get('final_calculation', {})
        total_points = final_calc.get('total_points', 0)
        if total_points > 0:
            recommendations.append(f"Current calculated points: {total_points:,.0f}")
        
        return recommendations
    
    def _calculate_growth_projection(self, calc_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate growth projection from calculator data"""
        final_calc = calc_result.get('final_calculation', {})
        current_points = final_calc.get('total_points', 0)
        
        # Simple projection (could be enhanced with ML)
        projected_growth = current_points * 1.1  # 10% growth assumption
        
        return {
            'current_points': current_points,
            'projected_points_30_days': projected_growth,
            'projected_growth_percent': 10.0,
            'confidence': 'medium'
        }
    
    def _get_future_tech_summary(self, user_id: str) -> Dict[str, Any]:
        """Get future tech summary for dashboard"""
        if not FUTURE_TECH_AVAILABLE:
            return {}
        
        try:
            status = future_tech_integration_service.get_integration_status()
            return {
                'future_tech_enabled': status.get('future_tech_available', False),
                'calculator_enabled': status.get('calculator_available', False),
                'integrations_active': status.get('integrations_active', {})
            }
        except Exception:
            return {}


# Global instance
dashboard_upgrades = DashboardUpgrades()

