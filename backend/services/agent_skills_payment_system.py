"""
Agent Skills Payment System
Agent skill sets with working hours and payment calculation
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

class AgentSkillsPaymentSystem:
    """
    Agent Skills Payment System
    - Skill sets for agents
    - Working hours tracking
    - Payment calculation based on hours and skills
    """
    
    # Skill Categories with Base Hourly Rates
    SKILL_CATEGORIES = {
        'leadership': {
            'base_rate': 50.0,  # Base hourly rate in points
            'multiplier_per_level': 2.0,  # Additional rate per skill level
            'name': 'Leadership Skills'
        },
        'management': {
            'base_rate': 45.0,
            'multiplier_per_level': 1.8,
            'name': 'Management Skills'
        },
        'strategy': {
            'base_rate': 55.0,
            'multiplier_per_level': 2.2,
            'name': 'Strategy Skills'
        },
        'communication': {
            'base_rate': 40.0,
            'multiplier_per_level': 1.5,
            'name': 'Communication Skills'
        },
        'administration': {
            'base_rate': 35.0,
            'multiplier_per_level': 1.3,
            'name': 'Administration Skills'
        },
        'organization': {
            'base_rate': 38.0,
            'multiplier_per_level': 1.4,
            'name': 'Organization Skills'
        },
        'support': {
            'base_rate': 32.0,
            'multiplier_per_level': 1.2,
            'name': 'Support Skills'
        },
        'technical': {
            'base_rate': 60.0,
            'multiplier_per_level': 2.5,
            'name': 'Technical Skills'
        },
        'creative': {
            'base_rate': 48.0,
            'multiplier_per_level': 1.9,
            'name': 'Creative Skills'
        },
        'analytical': {
            'base_rate': 52.0,
            'multiplier_per_level': 2.1,
            'name': 'Analytical Skills'
        }
    }
    
    # Working Hours Presets
    WORKING_HOURS_PRESETS = {
        'full_time': {
            'name': 'Full Time',
            'hours_per_day': 8,
            'days_per_week': 5,
            'overtime_rate': 1.5,  # 1.5x for overtime
            'description': 'Standard 40-hour work week'
        },
        'part_time': {
            'name': 'Part Time',
            'hours_per_day': 4,
            'days_per_week': 5,
            'overtime_rate': 1.3,
            'description': '20-hour work week'
        },
        'flexible': {
            'name': 'Flexible',
            'hours_per_day': 6,
            'days_per_week': 4,
            'overtime_rate': 1.4,
            'description': 'Flexible 24-hour work week'
        },
        'contract': {
            'name': 'Contract',
            'hours_per_day': 10,
            'days_per_week': 3,
            'overtime_rate': 2.0,
            'description': 'Contract 30-hour work week'
        },
        'on_demand': {
            'name': 'On Demand',
            'hours_per_day': 0,  # Variable
            'days_per_week': 0,  # Variable
            'overtime_rate': 1.2,
            'description': 'Work as needed'
        }
    }
    
    def __init__(self):
        self.agent_skill_sets = {}  # {agent_id: {skill_id: skill_data}}
        self.agent_working_hours = {}  # {agent_id: working_hours_data}
        self.agent_payment_history = {}  # {agent_id: [payment_records]}
        self.agent_time_tracking = {}  # {agent_id: {date: hours_worked}}
    
    def assign_skill_set(self, agent_id: str, skill_set: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assign a skill set to an agent"""
        if agent_id not in self.agent_skill_sets:
            self.agent_skill_sets[agent_id] = {}
        
        total_skill_value = 0
        for skill in skill_set:
            skill_id = skill.get('id', skill.get('skill_id', ''))
            skill_level = skill.get('level', skill.get('skill_level', 1))
            skill_category = skill.get('category', 'support')
            
            self.agent_skill_sets[agent_id][skill_id] = {
                'id': skill_id,
                'name': skill.get('name', ''),
                'level': skill_level,
                'category': skill_category,
                'assigned_at': datetime.utcnow().isoformat(),
                'experience': skill.get('experience', 0)
            }
            
            # Calculate skill value
            category_data = self.SKILL_CATEGORIES.get(skill_category, self.SKILL_CATEGORIES['support'])
            skill_value = category_data['base_rate'] + (category_data['multiplier_per_level'] * skill_level)
            total_skill_value += skill_value
        
        return {
            'success': True,
            'agent_id': agent_id,
            'skills_assigned': len(skill_set),
            'total_skill_value': total_skill_value,
            'average_hourly_rate': total_skill_value / len(skill_set) if skill_set else 0
        }
    
    def set_working_hours(self, agent_id: str, preset: str = 'full_time', 
                         custom_hours: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Set working hours for an agent"""
        if custom_hours:
            working_hours = custom_hours
        else:
            preset_data = self.WORKING_HOURS_PRESETS.get(preset, self.WORKING_HOURS_PRESETS['full_time'])
            working_hours = {
                'preset': preset,
                'hours_per_day': preset_data['hours_per_day'],
                'days_per_week': preset_data['days_per_week'],
                'overtime_rate': preset_data['overtime_rate'],
                'work_days': preset_data.get('work_days', [0, 1, 2, 3, 4]),  # Mon-Fri
                'start_time': preset_data.get('start_time', '09:00'),
                'end_time': preset_data.get('end_time', '17:00')
            }
        
        self.agent_working_hours[agent_id] = {
            **working_hours,
            'set_at': datetime.utcnow().isoformat(),
            'total_weekly_hours': working_hours.get('hours_per_day', 0) * working_hours.get('days_per_week', 0)
        }
        
        return {
            'success': True,
            'agent_id': agent_id,
            'working_hours': self.agent_working_hours[agent_id]
        }
    
    def track_work_hours(self, agent_id: str, date: str, hours: float, 
                        is_overtime: bool = False) -> Dict[str, Any]:
        """Track hours worked by an agent"""
        if agent_id not in self.agent_time_tracking:
            self.agent_time_tracking[agent_id] = {}
        
        if date not in self.agent_time_tracking[agent_id]:
            self.agent_time_tracking[agent_id][date] = {
                'regular_hours': 0.0,
                'overtime_hours': 0.0,
                'total_hours': 0.0
            }
        
        if is_overtime:
            self.agent_time_tracking[agent_id][date]['overtime_hours'] += hours
        else:
            self.agent_time_tracking[agent_id][date]['regular_hours'] += hours
        
        self.agent_time_tracking[agent_id][date]['total_hours'] += hours
        self.agent_time_tracking[agent_id][date]['last_updated'] = datetime.utcnow().isoformat()
        
        return {
            'success': True,
            'agent_id': agent_id,
            'date': date,
            'hours_tracked': hours,
            'is_overtime': is_overtime,
            'total_hours_today': self.agent_time_tracking[agent_id][date]['total_hours']
        }
    
    def calculate_payment(self, agent_id: str, date: Optional[str] = None, 
                         period: str = 'daily') -> Dict[str, Any]:
        """Calculate payment for an agent based on hours worked and skills"""
        if agent_id not in self.agent_skill_sets:
            return {
                'success': False,
                'error': 'Agent has no skill set assigned'
            }
        
        if agent_id not in self.agent_time_tracking:
            return {
                'success': False,
                'error': 'No time tracking data for agent'
            }
        
        # Get agent skills
        skills = self.agent_skill_sets.get(agent_id, {})
        working_hours = self.agent_working_hours.get(agent_id, {})
        overtime_rate = working_hours.get('overtime_rate', 1.5)
        
        # Calculate base hourly rate from skills
        total_base_rate = 0.0
        skill_count = 0
        
        for skill_id, skill_data in skills.items():
            category = skill_data.get('category', 'support')
            level = skill_data.get('level', 1)
            category_data = self.SKILL_CATEGORIES.get(category, self.SKILL_CATEGORIES['support'])
            
            skill_rate = category_data['base_rate'] + (category_data['multiplier_per_level'] * level)
            total_base_rate += skill_rate
            skill_count += 1
        
        average_hourly_rate = total_base_rate / skill_count if skill_count > 0 else 0
        
        # Calculate payment based on period
        if period == 'daily':
            if not date:
                date = datetime.utcnow().strftime('%Y-%m-%d')
            
            time_data = self.agent_time_tracking[agent_id].get(date, {})
            regular_hours = time_data.get('regular_hours', 0.0)
            overtime_hours = time_data.get('overtime_hours', 0.0)
            
            regular_pay = regular_hours * average_hourly_rate
            overtime_pay = overtime_hours * average_hourly_rate * overtime_rate
            total_pay = regular_pay + overtime_pay
            
            return {
                'success': True,
                'agent_id': agent_id,
                'date': date,
                'period': 'daily',
                'regular_hours': regular_hours,
                'overtime_hours': overtime_hours,
                'total_hours': regular_hours + overtime_hours,
                'average_hourly_rate': average_hourly_rate,
                'regular_pay': regular_pay,
                'overtime_pay': overtime_pay,
                'total_pay': total_pay,
                'skills_used': skill_count
            }
        
        elif period == 'weekly':
            # Calculate for current week
            today = datetime.utcnow()
            week_start = today - timedelta(days=today.weekday())
            
            total_regular_hours = 0.0
            total_overtime_hours = 0.0
            
            for i in range(7):
                date_str = (week_start + timedelta(days=i)).strftime('%Y-%m-%d')
                time_data = self.agent_time_tracking[agent_id].get(date_str, {})
                total_regular_hours += time_data.get('regular_hours', 0.0)
                total_overtime_hours += time_data.get('overtime_hours', 0.0)
            
            regular_pay = total_regular_hours * average_hourly_rate
            overtime_pay = total_overtime_hours * average_hourly_rate * overtime_rate
            total_pay = regular_pay + overtime_pay
            
            return {
                'success': True,
                'agent_id': agent_id,
                'period': 'weekly',
                'week_start': week_start.strftime('%Y-%m-%d'),
                'regular_hours': total_regular_hours,
                'overtime_hours': total_overtime_hours,
                'total_hours': total_regular_hours + total_overtime_hours,
                'average_hourly_rate': average_hourly_rate,
                'regular_pay': regular_pay,
                'overtime_pay': overtime_pay,
                'total_pay': total_pay,
                'skills_used': skill_count
            }
        
        elif period == 'monthly':
            # Calculate for current month
            today = datetime.utcnow()
            month_start = today.replace(day=1)
            
            total_regular_hours = 0.0
            total_overtime_hours = 0.0
            
            current_date = month_start
            while current_date.month == today.month:
                date_str = current_date.strftime('%Y-%m-%d')
                time_data = self.agent_time_tracking[agent_id].get(date_str, {})
                total_regular_hours += time_data.get('regular_hours', 0.0)
                total_overtime_hours += time_data.get('overtime_hours', 0.0)
                current_date += timedelta(days=1)
            
            regular_pay = total_regular_hours * average_hourly_rate
            overtime_pay = total_overtime_hours * average_hourly_rate * overtime_rate
            total_pay = regular_pay + overtime_pay
            
            return {
                'success': True,
                'agent_id': agent_id,
                'period': 'monthly',
                'month': today.strftime('%Y-%m'),
                'regular_hours': total_regular_hours,
                'overtime_hours': total_overtime_hours,
                'total_hours': total_regular_hours + total_overtime_hours,
                'average_hourly_rate': average_hourly_rate,
                'regular_pay': regular_pay,
                'overtime_pay': overtime_pay,
                'total_pay': total_pay,
                'skills_used': skill_count
            }
        
        return {
            'success': False,
            'error': f'Invalid period: {period}'
        }
    
    def process_payment(self, agent_id: str, period: str = 'daily', 
                       date: Optional[str] = None) -> Dict[str, Any]:
        """Process payment and award points to agent"""
        payment_calc = self.calculate_payment(agent_id, date, period)
        
        if not payment_calc.get('success'):
            return payment_calc
        
        total_pay = payment_calc.get('total_pay', 0)
        
        # Award points via unified point system
        try:
            from backend.services.point_connection_system import PointConnectionSystem
            point_connection = PointConnectionSystem()
            
            if point_connection:
                # Award payment as points
                point_connection.ensure_point_counting(
                    agent_id,
                    'agent_payment_points',
                    int(total_pay),
                    f'agent_payment_{period}'
                )
                
                # Also award to activity points
                point_connection.ensure_point_counting(
                    agent_id,
                    'activity_points',
                    int(total_pay * 0.1),  # 10% bonus
                    f'agent_payment_bonus_{period}'
                )
        except Exception as e:
            print(f"[AgentPayment] Error awarding points: {e}")
        
        # Record payment
        if agent_id not in self.agent_payment_history:
            self.agent_payment_history[agent_id] = []
        
        payment_record = {
            'payment_id': f"payment_{agent_id}_{datetime.utcnow().timestamp()}",
            'agent_id': agent_id,
            'period': period,
            'date': date or datetime.utcnow().strftime('%Y-%m-%d'),
            'amount': total_pay,
            'regular_hours': payment_calc.get('regular_hours', 0),
            'overtime_hours': payment_calc.get('overtime_hours', 0),
            'hourly_rate': payment_calc.get('average_hourly_rate', 0),
            'processed_at': datetime.utcnow().isoformat()
        }
        
        self.agent_payment_history[agent_id].append(payment_record)
        
        return {
            'success': True,
            'payment_processed': payment_record,
            'points_awarded': int(total_pay),
            'bonus_points': int(total_pay * 0.1)
        }
    
    def get_agent_payment_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get payment summary for an agent"""
        skills = self.agent_skill_sets.get(agent_id, {})
        working_hours = self.agent_working_hours.get(agent_id, {})
        payment_history = self.agent_payment_history.get(agent_id, [])
        time_tracking = self.agent_time_tracking.get(agent_id, {})
        
        # Calculate total earnings
        total_earnings = sum(p.get('amount', 0) for p in payment_history)
        
        # Calculate total hours worked
        total_hours = sum(
            day_data.get('total_hours', 0) 
            for day_data in time_tracking.values()
        )
        
        # Calculate average hourly rate
        if skills:
            total_base_rate = 0.0
            for skill_data in skills.values():
                category = skill_data.get('category', 'support')
                level = skill_data.get('level', 1)
                category_data = self.SKILL_CATEGORIES.get(category, self.SKILL_CATEGORIES['support'])
                skill_rate = category_data['base_rate'] + (category_data['multiplier_per_level'] * level)
                total_base_rate += skill_rate
            avg_hourly_rate = total_base_rate / len(skills)
        else:
            avg_hourly_rate = 0
        
        return {
            'success': True,
            'agent_id': agent_id,
            'skills': {
                'total_skills': len(skills),
                'skill_categories': list(set(s.get('category', '') for s in skills.values())),
                'average_hourly_rate': avg_hourly_rate
            },
            'working_hours': working_hours,
            'time_tracking': {
                'total_hours_worked': total_hours,
                'days_tracked': len(time_tracking),
                'average_hours_per_day': total_hours / len(time_tracking) if time_tracking else 0
            },
            'payment': {
                'total_earnings': total_earnings,
                'total_payments': len(payment_history),
                'average_payment': total_earnings / len(payment_history) if payment_history else 0,
                'last_payment': payment_history[-1] if payment_history else None
            }
        }
    
    def get_all_skill_categories(self) -> Dict[str, Any]:
        """Get all available skill categories"""
        return {
            'success': True,
            'categories': self.SKILL_CATEGORIES,
            'total_categories': len(self.SKILL_CATEGORIES)
        }
    
    def get_all_working_hours_presets(self) -> Dict[str, Any]:
        """Get all working hours presets"""
        return {
            'success': True,
            'presets': self.WORKING_HOURS_PRESETS,
            'total_presets': len(self.WORKING_HOURS_PRESETS)
        }

# Global instance
agent_skills_payment_system = AgentSkillsPaymentSystem()
