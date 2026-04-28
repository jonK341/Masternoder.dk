"""
AI Intelligence Dashboard Routes
Top 10 AI intelligence enhancements
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List
from datetime import datetime, timedelta

ai_intelligence_dashboard_bp = Blueprint('ai_intelligence_dashboard', __name__)


@ai_intelligence_dashboard_bp.route('/api/ai-intelligence/top10', methods=['GET'])
def get_ai_intelligence_top10():
    """Get Top 10 AI Intelligence enhancements"""
    try:
        top10 = []
        
        # Get AI Intelligence data
        try:
            from backend.services.agent_ai_intelligence import agent_ai_intelligence
            all_intelligence = agent_ai_intelligence.get_all_intelligence()
            
            # Top 10 Tech Sectors
            tech_sectors = all_intelligence.get('tech_sectors', {})
            sector_count = len(tech_sectors)
            top10.append({
                'rank': 1,
                'title': 'Tech Sectors Tracked',
                'value': sector_count,
                'type': 'tech_sectors',
                'description': f'{sector_count} technology sectors being monitored',
                'priority': 'high',
                'data': list(tech_sectors.keys())[:10] if isinstance(tech_sectors, dict) else []
            })
            
            # Top 10 Predictions
            predictions = all_intelligence.get('predictions', {})
            prediction_count = len(predictions) if isinstance(predictions, dict) else 0
            top10.append({
                'rank': 2,
                'title': 'AI Predictions',
                'value': prediction_count,
                'type': 'predictions',
                'description': f'{prediction_count} active predictions',
                'priority': 'high'
            })
            
            # Top 10 Insights
            insights = all_intelligence.get('insights', {})
            insight_count = len(insights) if isinstance(insights, dict) else 0
            top10.append({
                'rank': 3,
                'title': 'AI Insights',
                'value': insight_count,
                'type': 'insights',
                'description': f'{insight_count} insights generated',
                'priority': 'high'
            })
            
            # Top 10 Patterns
            patterns = all_intelligence.get('patterns', {})
            pattern_count = len(patterns) if isinstance(patterns, dict) else 0
            top10.append({
                'rank': 4,
                'title': 'Patterns Recognized',
                'value': pattern_count,
                'type': 'patterns',
                'description': f'{pattern_count} patterns identified',
                'priority': 'medium'
            })
            
            # Top 10 Optimizations
            optimizations = all_intelligence.get('optimizations', {})
            opt_count = len(optimizations) if isinstance(optimizations, dict) else 0
            top10.append({
                'rank': 5,
                'title': 'Optimizations Applied',
                'value': opt_count,
                'type': 'optimizations',
                'description': f'{opt_count} optimizations implemented',
                'priority': 'medium'
            })
            
        except Exception as e:
            print(f"[WARN] Could not get AI intelligence: {e}")
        
        # Top 10 Agent Skills
        try:
            from backend.services.agent_skillset import AgentSkillset
            skillset = AgentSkillset()
            agents = skillset.skillsets.get('agents', {})
            total_skills = sum(len(agent.get('skills', [])) for agent in agents.values())
            top10.append({
                'rank': 6,
                'title': 'Total Agent Skills',
                'value': total_skills,
                'type': 'skills',
                'description': f'{total_skills} skills across all agents',
                'priority': 'medium'
            })
        except:
            pass
        
        # Top 10 AI Tasks
        try:
            from backend.utils.agent_task_database import get_agent_tasks
            ai_tasks = [t for t in get_agent_tasks() if 'ai' in t.get('task_type', '').lower()]
            top10.append({
                'rank': 7,
                'title': 'AI Tasks',
                'value': len(ai_tasks),
                'type': 'tasks',
                'description': f'{len(ai_tasks)} AI-related tasks',
                'priority': 'medium'
            })
        except:
            pass
        
        # Top 10 Learning Events
        try:
            from backend.services.agent_ai_intelligence import agent_ai_intelligence
            if hasattr(agent_ai_intelligence, 'get_learning_data'):
                learning_data = agent_ai_intelligence.get_learning_data()
                learning_count = len(learning_data.get('events', [])) if isinstance(learning_data, dict) else 0
                top10.append({
                    'rank': 8,
                    'title': 'Learning Events',
                    'value': learning_count,
                    'type': 'learning',
                    'description': f'{learning_count} learning events recorded',
                    'priority': 'low'
                })
        except:
            pass
        
        # Top 10 Recommendations
        try:
            from backend.services.agent_ai_intelligence import agent_ai_intelligence
            if hasattr(agent_ai_intelligence, 'get_recommendations'):
                recommendations = agent_ai_intelligence.get_recommendations()
                rec_count = len(recommendations.get('recommendations', [])) if isinstance(recommendations, dict) else 0
                top10.append({
                    'rank': 9,
                    'title': 'AI Recommendations',
                    'value': rec_count,
                    'type': 'recommendations',
                    'description': f'{rec_count} recommendations available',
                    'priority': 'low'
                })
        except:
            pass
        
        # Top 10 Intelligence Updates
        try:
            from backend.services.agent_ai_intelligence import agent_ai_intelligence
            if hasattr(agent_ai_intelligence, 'get_intelligence_updates'):
                updates = agent_ai_intelligence.get_intelligence_updates()
                update_count = len(updates.get('updates', [])) if isinstance(updates, dict) else 0
                top10.append({
                    'rank': 10,
                    'title': 'Intelligence Updates',
                    'value': update_count,
                    'type': 'updates',
                    'description': f'{update_count} intelligence updates',
                    'priority': 'low'
                })
        except:
            pass
        
        # Sort by rank
        top10.sort(key=lambda x: x.get('rank', 999))
        
        return jsonify({
            'success': True,
            'top10': top10,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'top10': []
        }), 500


@ai_intelligence_dashboard_bp.route('/api/ai-intelligence/stats', methods=['GET'])
def get_ai_intelligence_stats():
    """Get comprehensive AI intelligence statistics"""
    try:
        stats = {
            'intelligence': {},
            'predictions': {},
            'insights': {},
            'optimizations': {},
            'learning': {}
        }
        
        try:
            from backend.services.agent_ai_intelligence import agent_ai_intelligence
            all_intelligence = agent_ai_intelligence.get_all_intelligence()
            
            stats['intelligence'] = {
                'tech_sectors': len(all_intelligence.get('tech_sectors', {})) if isinstance(all_intelligence.get('tech_sectors'), dict) else 0,
                'total_intelligence': len(all_intelligence) if isinstance(all_intelligence, dict) else 0,
                'last_update': all_intelligence.get('last_update', datetime.now().isoformat()) if isinstance(all_intelligence, dict) else datetime.now().isoformat()
            }
            
            stats['predictions'] = {
                'count': len(all_intelligence.get('predictions', {})) if isinstance(all_intelligence.get('predictions'), dict) else 0,
                'accuracy': all_intelligence.get('prediction_accuracy', 0) if isinstance(all_intelligence, dict) else 0
            }
            
            insights = all_intelligence.get('insights', {}) if isinstance(all_intelligence, dict) else {}
            stats['insights'] = {
                'count': len(insights) if isinstance(insights, dict) else 0,
                'categories': len(set(i.get('category', '') for i in insights.values() if isinstance(i, dict))) if isinstance(insights, dict) else 0
            }
            
        except Exception as e:
            print(f"[WARN] Could not get AI intelligence stats: {e}")
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {}
        }), 500
