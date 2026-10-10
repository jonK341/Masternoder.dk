"""
Technology Tree System
Research branches, dependencies, and progression
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import uuid

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.point_connection_system import PointConnectionSystem
    unified_points_db = UnifiedPointsDatabase()
    point_connection = PointConnectionSystem()
except ImportError:
    unified_points_db = None
    point_connection = None


class TechTreeSystem:
    """Technology Tree System with research branches and dependencies"""
    
    def __init__(self):
        self.tech_tree = self._initialize_tech_tree()
        self.user_research = defaultdict(dict)  # {user_id: {tech_id: research_data}}
        self.research_progress = defaultdict(dict)  # {user_id: {tech_id: progress}}
        self.tech_skills = defaultdict(dict)  # {user_id: {tech_id: [skills]}}
        self.visual_memories = defaultdict(list)  # {user_id: [visual_memories]}
        self.learning_progress = defaultdict(dict)  # {user_id: {tech_id: learning_data}}
        
    def _initialize_tech_tree(self) -> Dict[str, Dict[str, Any]]:
        """Initialize technology tree with branches and dependencies"""
        return {
            # Foundation Technologies
            'basic_computing': {
                'id': 'basic_computing',
                'name': 'Basic Computing',
                'category': 'foundation',
                'tier': 1,
                'description': 'Fundamental computing principles and basic algorithmic thinking. This technology forms the foundation of all advanced computing systems.',
                'detailed_info': {
                    'overview': 'Learn the core principles of computing including binary logic, data structures, and basic algorithms.',
                    'applications': ['Data processing', 'Basic calculations', 'Simple automation'],
                    'skills_unlocked': ['algorithmic_thinking', 'data_structures', 'basic_programming'],
                    'visual_memory_points': 50,
                    'learning_points': 100,
                    'prerequisites_description': 'No prerequisites - this is the starting technology.',
                    'research_tips': 'Focus on understanding core concepts before moving to advanced topics.'
                },
                'cost': 100,
                'research_time': 60,  # minutes
                'prerequisites': [],
                'unlocks': ['advanced_computing', 'quantum_basics'],
                'bonuses': {
                    'calculation_speed': 0.1,
                    'efficiency': 0.05
                },
                'skill_bonuses': {
                    'algorithmic_thinking': 0.1,
                    'problem_solving': 0.05
                }
            },
            'advanced_computing': {
                'id': 'advanced_computing',
                'name': 'Advanced Computing',
                'category': 'foundation',
                'tier': 2,
                'description': 'Advanced computational methods',
                'cost': 500,
                'research_time': 180,
                'prerequisites': ['basic_computing'],
                'unlocks': ['quantum_computing', 'neural_networks'],
                'bonuses': {
                    'calculation_speed': 0.25,
                    'efficiency': 0.15
                }
            },
            
            # Quantum Technologies
            'quantum_basics': {
                'id': 'quantum_basics',
                'name': 'Quantum Basics',
                'category': 'quantum',
                'tier': 1,
                'description': 'Introduction to quantum mechanics',
                'cost': 200,
                'research_time': 120,
                'prerequisites': ['basic_computing'],
                'unlocks': ['quantum_computing', 'quantum_entanglement'],
                'bonuses': {
                    'quantum_power': 0.1,
                    'processing_speed': 0.2
                }
            },
            'quantum_computing': {
                'id': 'quantum_computing',
                'name': 'Quantum Computing',
                'category': 'quantum',
                'tier': 2,
                'description': 'Full quantum computing capabilities',
                'cost': 1000,
                'research_time': 360,
                'prerequisites': ['advanced_computing', 'quantum_basics'],
                'unlocks': ['quantum_supremacy', 'quantum_ai'],
                'bonuses': {
                    'quantum_power': 0.5,
                    'processing_speed': 1.0,
                    'calculation_accuracy': 0.3
                }
            },
            'quantum_entanglement': {
                'id': 'quantum_entanglement',
                'name': 'Quantum Entanglement',
                'category': 'quantum',
                'tier': 2,
                'description': 'Quantum entanglement manipulation',
                'cost': 800,
                'research_time': 300,
                'prerequisites': ['quantum_basics'],
                'unlocks': ['quantum_teleportation'],
                'bonuses': {
                    'quantum_power': 0.3,
                    'network_speed': 0.5
                }
            },
            'quantum_supremacy': {
                'id': 'quantum_supremacy',
                'name': 'Quantum Supremacy',
                'category': 'quantum',
                'tier': 3,
                'description': 'Achieve quantum computational supremacy',
                'cost': 5000,
                'research_time': 1440,
                'prerequisites': ['quantum_computing'],
                'unlocks': ['quantum_reality'],
                'bonuses': {
                    'quantum_power': 2.0,
                    'processing_speed': 5.0,
                    'all_stats': 0.5
                }
            },
            
            # Neural Network Technologies
            'neural_networks': {
                'id': 'neural_networks',
                'name': 'Neural Networks',
                'category': 'ai',
                'tier': 2,
                'description': 'Artificial neural network systems',
                'cost': 600,
                'research_time': 240,
                'prerequisites': ['advanced_computing'],
                'unlocks': ['deep_learning', 'ai_intelligence'],
                'bonuses': {
                    'ai_power': 0.3,
                    'prediction_accuracy': 0.2
                }
            },
            'deep_learning': {
                'id': 'deep_learning',
                'name': 'Deep Learning',
                'category': 'ai',
                'tier': 3,
                'description': 'Advanced deep learning algorithms',
                'cost': 2000,
                'research_time': 720,
                'prerequisites': ['neural_networks'],
                'unlocks': ['ai_mastery'],
                'bonuses': {
                    'ai_power': 1.0,
                    'prediction_accuracy': 0.5,
                    'learning_speed': 0.4
                }
            },
            'ai_intelligence': {
                'id': 'ai_intelligence',
                'name': 'AI Intelligence',
                'category': 'ai',
                'tier': 3,
                'description': 'General AI intelligence systems',
                'cost': 1500,
                'research_time': 600,
                'prerequisites': ['neural_networks'],
                'unlocks': ['ai_mastery'],
                'bonuses': {
                    'ai_power': 0.8,
                    'intelligence': 0.6,
                    'automation': 0.5
                }
            },
            'ai_mastery': {
                'id': 'ai_mastery',
                'name': 'AI Mastery',
                'category': 'ai',
                'tier': 4,
                'description': 'Complete mastery of AI systems',
                'cost': 10000,
                'research_time': 2880,
                'prerequisites': ['deep_learning', 'ai_intelligence'],
                'unlocks': ['quantum_ai'],
                'bonuses': {
                    'ai_power': 3.0,
                    'intelligence': 2.0,
                    'automation': 1.5,
                    'all_stats': 0.3
                }
            },
            'quantum_ai': {
                'id': 'quantum_ai',
                'name': 'Quantum AI',
                'category': 'quantum_ai',
                'tier': 4,
                'description': 'Quantum-powered AI systems',
                'cost': 15000,
                'research_time': 4320,
                'prerequisites': ['quantum_computing', 'ai_mastery'],
                'unlocks': ['quantum_reality'],
                'bonuses': {
                    'quantum_power': 3.0,
                    'ai_power': 3.0,
                    'processing_speed': 10.0,
                    'all_stats': 1.0
                }
            },
            
            # Advanced Technologies
            'quantum_teleportation': {
                'id': 'quantum_teleportation',
                'name': 'Quantum Teleportation',
                'category': 'quantum',
                'tier': 3,
                'description': 'Instant quantum teleportation',
                'cost': 3000,
                'research_time': 1080,
                'prerequisites': ['quantum_entanglement'],
                'unlocks': ['quantum_reality'],
                'bonuses': {
                    'quantum_power': 1.5,
                    'mobility': 2.0,
                    'speed': 1.0
                }
            },
            'quantum_reality': {
                'id': 'quantum_reality',
                'name': 'Quantum Reality Manipulation',
                'category': 'quantum',
                'tier': 5,
                'description': 'Ultimate quantum reality control',
                'cost': 50000,
                'research_time': 10080,
                'prerequisites': ['quantum_supremacy', 'quantum_ai', 'quantum_teleportation'],
                'unlocks': [],
                'bonuses': {
                    'quantum_power': 10.0,
                    'reality_control': 5.0,
                    'all_stats': 2.0
                }
            },
            
            # Battle Technologies
            'battle_ai': {
                'id': 'battle_ai',
                'name': 'Battle AI',
                'category': 'battle',
                'tier': 2,
                'description': 'AI-powered battle predictions',
                'cost': 400,
                'research_time': 180,
                'prerequisites': ['basic_computing'],
                'unlocks': ['advanced_battle_ai', 'predictive_battle'],
                'bonuses': {
                    'battle_accuracy': 0.2,
                    'win_rate': 0.1
                }
            },
            'advanced_battle_ai': {
                'id': 'advanced_battle_ai',
                'name': 'Advanced Battle AI',
                'category': 'battle',
                'tier': 3,
                'description': 'Advanced AI battle strategies',
                'cost': 1200,
                'research_time': 480,
                'prerequisites': ['battle_ai', 'neural_networks'],
                'unlocks': ['quantum_battle'],
                'bonuses': {
                    'battle_accuracy': 0.5,
                    'win_rate': 0.3,
                    'strategy_power': 0.4
                }
            },
            'predictive_battle': {
                'id': 'predictive_battle',
                'name': 'Predictive Battle',
                'category': 'battle',
                'tier': 3,
                'description': 'Predict battle outcomes',
                'cost': 1000,
                'research_time': 420,
                'prerequisites': ['battle_ai'],
                'unlocks': ['quantum_battle'],
                'bonuses': {
                    'prediction_accuracy': 0.6,
                    'battle_advantage': 0.3
                }
            },
            'quantum_battle': {
                'id': 'quantum_battle',
                'name': 'Quantum Battle',
                'category': 'battle',
                'tier': 4,
                'description': 'Quantum-enhanced battle systems',
                'cost': 8000,
                'research_time': 2160,
                'prerequisites': ['advanced_battle_ai', 'predictive_battle', 'quantum_computing'],
                'unlocks': [],
                'bonuses': {
                    'battle_accuracy': 1.0,
                    'win_rate': 0.8,
                    'quantum_power': 1.5,
                    'all_battle_stats': 0.5
                }
            }
        }
    
    def get_tech_tree(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get technology tree with user progress"""
        user_research = self.user_research.get(user_id, {}) if user_id else {}
        
        tech_list = []
        for tech_id, tech_data in self.tech_tree.items():
            research_data = user_research.get(tech_id, {})
            progress = self.research_progress.get(user_id, {}).get(tech_id, 0) if user_id else 0
            
            # Check if prerequisites are met
            prerequisites_met = True
            if user_id and tech_data.get('prerequisites'):
                for prereq in tech_data['prerequisites']:
                    if prereq not in user_research or user_research[prereq].get('status') != 'completed':
                        prerequisites_met = False
                        break
            
            tech_list.append({
                **tech_data,
                'researched': research_data.get('status') == 'completed',
                'in_progress': research_data.get('status') == 'researching',
                'progress': progress,
                'prerequisites_met': prerequisites_met,
                'unlocked': prerequisites_met or len(tech_data.get('prerequisites', [])) == 0,
                'started_at': research_data.get('started_at'),
                'completed_at': research_data.get('completed_at')
            })
        
        return {
            'success': True,
            'tech_tree': tech_list,
            'total_technologies': len(self.tech_tree),
            'researched_count': len([t for t in tech_list if t['researched']]),
            'available_count': len([t for t in tech_list if t['unlocked'] and not t['researched']])
        }
    
    def start_research(self, user_id: str, tech_id: str) -> Dict[str, Any]:
        """Start researching a technology"""
        if tech_id not in self.tech_tree:
            return {'success': False, 'error': 'Technology not found'}
        
        tech = self.tech_tree[tech_id]
        user_research = self.user_research[user_id]
        
        # Check if already researched
        if tech_id in user_research and user_research[tech_id].get('status') == 'completed':
            return {'success': False, 'error': 'Technology already researched'}
        
        # Check if already researching
        if tech_id in user_research and user_research[tech_id].get('status') == 'researching':
            return {'success': False, 'error': 'Research already in progress'}
        
        # Check prerequisites
        if tech.get('prerequisites'):
            for prereq in tech['prerequisites']:
                if prereq not in user_research or user_research[prereq].get('status') != 'completed':
                    return {
                        'success': False,
                        'error': f'Prerequisites not met: {prereq}',
                        'missing_prerequisites': [p for p in tech['prerequisites'] 
                                                  if p not in user_research or user_research[p].get('status') != 'completed']
                    }
        
        # Check cost (points)
        if point_connection:
            try:
                all_points = point_connection.get_all_connected_points(user_id)
                total_points = sum(all_points.values())
                if total_points < tech['cost']:
                    return {
                        'success': False,
                        'error': f'Insufficient points. Need {tech["cost"]}, have {total_points}',
                        'required': tech['cost'],
                        'available': total_points
                    }
            except Exception as e:
                print(f"[TechTree] Error checking points: {e}")
        
        # Start research
        research_id = str(uuid.uuid4())
        user_research[tech_id] = {
            'research_id': research_id,
            'tech_id': tech_id,
            'status': 'researching',
            'started_at': datetime.utcnow().isoformat(),
            'research_time': tech['research_time'],
            'progress': 0
        }
        
        self.research_progress[user_id][tech_id] = 0
        
        return {
            'success': True,
            'research_id': research_id,
            'tech_id': tech_id,
            'research_time': tech['research_time'],
            'message': f'Research started: {tech["name"]}'
        }
    
    def complete_research(self, user_id: str, tech_id: str) -> Dict[str, Any]:
        """Complete a research (called after research time)"""
        if tech_id not in self.tech_tree:
            return {'success': False, 'error': 'Technology not found'}
        
        user_research = self.user_research.get(user_id, {})
        
        if tech_id not in user_research:
            return {'success': False, 'error': 'Research not started'}
        
        if user_research[tech_id].get('status') == 'completed':
            return {'success': False, 'error': 'Research already completed'}
        
        # Mark as completed
        user_research[tech_id]['status'] = 'completed'
        user_research[tech_id]['completed_at'] = datetime.utcnow().isoformat()
        user_research[tech_id]['progress'] = 100
        
        self.research_progress[user_id][tech_id] = 100
        
        tech = self.tech_tree[tech_id]
        
        # Award points for research completion
        if point_connection:
            try:
                point_connection.ensure_point_counting(
                    user_id,
                    'tech_points',
                    tech['cost'] // 10,  # 10% of cost as reward
                    'tech_tree_system'
                )
            except Exception as e:
                print(f"[TechTree] Error awarding points: {e}")
        
        # Save visual memory for progressive learning
        detailed_info = tech.get('detailed_info', {})
        if detailed_info:
            memory_data = {
                'tech_name': tech['name'],
                'category': tech.get('category', 'general'),
                'tier': tech.get('tier', 1),
                'bonuses': tech.get('bonuses', {}),
                'skills_unlocked': detailed_info.get('skills_unlocked', [])
            }
            self.save_visual_memory_from_tech(user_id, tech_id, memory_data)
        
        return {
            'success': True,
            'tech_id': tech_id,
            'tech_name': tech['name'],
            'bonuses': tech.get('bonuses', {}),
            'unlocks': tech.get('unlocks', []),
            'skills_unlocked': detailed_info.get('skills_unlocked', []) if detailed_info else [],
            'message': f'Research completed: {tech["name"]}'
        }
    
    def get_user_research(self, user_id: str) -> Dict[str, Any]:
        """Get user's research progress"""
        user_research = self.user_research.get(user_id, {})
        research_progress = self.research_progress.get(user_id, {})
        
        completed = [tech_id for tech_id, data in user_research.items() 
                     if data.get('status') == 'completed']
        in_progress = [tech_id for tech_id, data in user_research.items() 
                      if data.get('status') == 'researching']
        
        return {
            'success': True,
            'user_id': user_id,
            'completed_research': completed,
            'in_progress_research': in_progress,
            'research_data': user_research,
            'progress': research_progress,
            'total_completed': len(completed),
            'total_in_progress': len(in_progress)
        }
    
    def update_research_progress(self, user_id: str, tech_id: str, progress: float) -> Dict[str, Any]:
        """Update research progress (called periodically)"""
        if tech_id not in self.tech_tree:
            return {'success': False, 'error': 'Technology not found'}
        
        user_research = self.user_research.get(user_id, {})
        if tech_id not in user_research:
            return {'success': False, 'error': 'Research not started'}
        
        if user_research[tech_id].get('status') == 'completed':
            return {'success': False, 'error': 'Research already completed'}
        
        # Update progress
        self.research_progress[user_id][tech_id] = min(100.0, max(0.0, progress))
        user_research[tech_id]['progress'] = self.research_progress[user_id][tech_id]
        
        # Auto-complete if progress reaches 100%
        if progress >= 100.0:
            return self.complete_research(user_id, tech_id)
        
        return {
            'success': True,
            'tech_id': tech_id,
            'progress': self.research_progress[user_id][tech_id]
        }
    
    def get_research_bonuses(self, user_id: str) -> Dict[str, Any]:
        """Get all active research bonuses for user"""
        user_research = self.user_research.get(user_id, {})
        completed_tech = [tech_id for tech_id, data in user_research.items() 
                          if data.get('status') == 'completed']
        
        total_bonuses = {}
        for tech_id in completed_tech:
            tech = self.tech_tree.get(tech_id, {})
            bonuses = tech.get('bonuses', {})
            for bonus_type, value in bonuses.items():
                if bonus_type not in total_bonuses:
                    total_bonuses[bonus_type] = 0
                total_bonuses[bonus_type] += value
        
        return {
            'success': True,
            'user_id': user_id,
            'bonuses': total_bonuses,
            'researched_technologies': completed_tech,
            'total_bonuses': len(total_bonuses)
        }
    
    def save_visual_memory_from_tech(self, user_id: str, tech_id: str, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save visual memory when researching tech (progressive learning)"""
        if tech_id not in self.tech_tree:
            return {'success': False, 'error': 'Technology not found'}
        
        tech = self.tech_tree[tech_id]
        detailed_info = tech.get('detailed_info', {})
        
        # Create visual memory
        visual_memory = {
            'id': str(uuid.uuid4()),
            'tech_id': tech_id,
            'tech_name': tech['name'],
            'type': 'tech_research',
            'data': memory_data,
            'timestamp': datetime.utcnow().isoformat(),
            'points_value': detailed_info.get('visual_memory_points', 50),
            'learning_points': detailed_info.get('learning_points', 100)
        }
        
        # Add to user's visual memories
        if user_id not in self.visual_memories:
            self.visual_memories[user_id] = []
        
        self.visual_memories[user_id].append(visual_memory)
        
        # Update learning progress
        if user_id not in self.learning_progress:
            self.learning_progress[user_id] = {}
        
        if tech_id not in self.learning_progress[user_id]:
            self.learning_progress[user_id][tech_id] = {
                'memories_saved': 0,
                'total_learning_points': 0,
                'learning_efficiency': 0.5
            }
        
        learning_data = self.learning_progress[user_id][tech_id]
        learning_data['memories_saved'] += 1
        learning_data['total_learning_points'] += visual_memory['learning_points']
        learning_data['learning_efficiency'] = min(learning_data['learning_efficiency'] + 0.01, 1.0)
        
        # Save to agent system if user has agents
        try:
            from backend.services.agent_system import agent_system
            user_agents = agent_system.get_user_agents(user_id)
            for agent in user_agents:
                agent_id = agent.get('agent_id')
                if agent_id:
                    # Save visual memory to agent
                    agent_system.save_visual_memory(
                        agent_id,
                        'tech_research',
                        {
                            'tech_id': tech_id,
                            'tech_name': tech['name'],
                            'category': tech.get('category', 'general'),
                            'tier': tech.get('tier', 1),
                            'skills_unlocked': memory_data.get('skills_unlocked', []),
                            'bonuses': memory_data.get('bonuses', {}),
                            'learning_points': visual_memory['learning_points']
                        }
                    )
        except Exception as e:
            print(f"[TechTree] Error saving to agent system: {e}")
        
        # Award points through unified system
        try:
            from backend.services.unified_point_counter import unified_point_counter
            unified_point_counter.add_points(
                user_id,
                'tech_visual_memory',
                visual_memory['points_value'],
                source=f'tech_tree_{tech_id}',
                metadata={'tech_id': tech_id, 'memory_id': visual_memory['id']}
            )
            
            # Also award learning points
            unified_point_counter.add_points(
                user_id,
                'tech_learning',
                visual_memory['learning_points'],
                source=f'tech_tree_{tech_id}_learning',
                metadata={'tech_id': tech_id, 'learning_efficiency': learning_data['learning_efficiency']}
            )
        except Exception as e:
            print(f"[TechTree] Error awarding points: {e}")
        
        return {
            'success': True,
            'memory_id': visual_memory['id'],
            'points_awarded': visual_memory['points_value'],
            'learning_points_awarded': visual_memory['learning_points'],
            'learning_progress': learning_data
        }
    
    def get_tech_skills(self, user_id: str, tech_id: str = None) -> Dict[str, Any]:
        """Get skills unlocked from tech research"""
        if tech_id:
            # Get skills for specific tech
            tech = self.tech_tree.get(tech_id, {})
            detailed_info = tech.get('detailed_info', {})
            skills = detailed_info.get('skills_unlocked', [])
            
            return {
                'success': True,
                'tech_id': tech_id,
                'skills': skills,
                'skill_bonuses': tech.get('skill_bonuses', {})
            }
        else:
            # Get all skills from all researched tech
            user_research = self.user_research.get(user_id, {})
            completed_tech = [tech_id for tech_id, data in user_research.items() 
                             if data.get('status') == 'completed']
            
            all_skills = []
            all_skill_bonuses = {}
            
            for tech_id in completed_tech:
                tech = self.tech_tree.get(tech_id, {})
                detailed_info = tech.get('detailed_info', {})
                skills = detailed_info.get('skills_unlocked', [])
                all_skills.extend(skills)
                
                skill_bonuses = tech.get('skill_bonuses', {})
                for skill, bonus in skill_bonuses.items():
                    if skill not in all_skill_bonuses:
                        all_skill_bonuses[skill] = 0
                    all_skill_bonuses[skill] += bonus
            
            return {
                'success': True,
                'user_id': user_id,
                'all_skills': list(set(all_skills)),  # Remove duplicates
                'skill_bonuses': all_skill_bonuses,
                'total_skills': len(set(all_skills))
            }
    
    def get_progressive_learning_data(self, user_id: str) -> Dict[str, Any]:
        """Get progressive learning data for user"""
        learning_data = self.learning_progress.get(user_id, {})
        visual_memories = self.visual_memories.get(user_id, [])
        
        total_memories = len(visual_memories)
        total_learning_points = sum(m.get('learning_points', 0) for m in visual_memories)
        total_points = sum(m.get('points_value', 0) for m in visual_memories)
        
        avg_learning_efficiency = 0.5
        if learning_data:
            efficiencies = [data.get('learning_efficiency', 0.5) for data in learning_data.values()]
            if efficiencies:
                avg_learning_efficiency = sum(efficiencies) / len(efficiencies)
        
        return {
            'success': True,
            'user_id': user_id,
            'total_visual_memories': total_memories,
            'total_learning_points': total_learning_points,
            'total_points_from_memories': total_points,
            'average_learning_efficiency': avg_learning_efficiency,
            'tech_learning_progress': learning_data,
            'recent_memories': visual_memories[-10:] if visual_memories else []
        }
    
    def learn_from_tech_research(self, user_id: str, agent_id: str = None) -> Dict[str, Any]:
        """Learn from tech research - process visual memories and award learning points"""
        visual_memories = self.visual_memories.get(user_id, [])
        if not visual_memories:
            return {'error': 'No visual memories available'}
        
        # Filter tech research memories
        tech_memories = [m for m in visual_memories if m.get('type') == 'tech_research']
        if not tech_memories:
            return {'error': 'No tech research memories available'}
        
        # Process memories for learning
        total_learning_points = 0
        skills_learned = []
        
        for memory in tech_memories[-20:]:  # Last 20 tech memories
            learning_points = memory.get('learning_points', 0)
            total_learning_points += learning_points
            
            # Extract skills from memory
            memory_data = memory.get('data', {})
            skills = memory_data.get('skills_unlocked', [])
            skills_learned.extend(skills)
        
        # If agent_id provided, learn through agent system
        if agent_id:
            try:
                from backend.services.agent_system import agent_system
                # Find memories by category
                tech_memory_ids = [m.get('id') for m in tech_memories[-10:]]
                
                # Learn from each memory
                for memory_id in tech_memory_ids:
                    try:
                        agent_system.learn_from_memory(agent_id, memory_id)
                    except:
                        pass
                
                # Award XP to agent
                xp_awarded = total_learning_points // 10  # Convert learning points to XP
                if xp_awarded > 0:
                    agent_system.award_xp(agent_id, 'system_1', xp_awarded)
            except Exception as e:
                print(f"[TechTree] Error learning through agent: {e}")
        
        # Award unified points
        try:
            from backend.services.unified_point_counter import unified_point_counter
            unified_point_counter.add_points(
                user_id,
                'tech_learning',
                total_learning_points,
                source='tech_tree_learning',
                metadata={
                    'memories_processed': len(tech_memories),
                    'skills_learned': list(set(skills_learned)),
                    'agent_id': agent_id
                }
            )
        except Exception as e:
            print(f"[TechTree] Error awarding learning points: {e}")
        
        return {
            'success': True,
            'user_id': user_id,
            'agent_id': agent_id,
            'memories_processed': len(tech_memories),
            'total_learning_points': total_learning_points,
            'skills_learned': list(set(skills_learned)),
            'unique_skills': len(set(skills_learned))
        }
    
    def get_agent_tech_learning(self, user_id: str, agent_id: str) -> Dict[str, Any]:
        """Get agent's tech learning progress"""
        try:
            from backend.services.agent_system import agent_system
            agent = agent_system.get_agent(agent_id)
            if not agent:
                return {'error': 'Agent not found'}
            
            # Get agent's visual memories related to tech
            agent_memories = agent.get('visual_memory', [])
            tech_memories = [m for m in agent_memories if m.get('category') == 'tech_research' or m.get('type') == 'tech_research']
            
            # Get tech learning progress
            learning_progress = self.learning_progress.get(user_id, {})
            
            # Get skills unlocked from tech
            tech_skills = self.get_tech_skills(user_id)
            
            return {
                'success': True,
                'agent_id': agent_id,
                'user_id': user_id,
                'tech_memories_count': len(tech_memories),
                'tech_learning_progress': learning_progress,
                'skills_unlocked': tech_skills.get('all_skills', []),
                'skill_bonuses': tech_skills.get('skill_bonuses', {}),
                'total_tech_memories': len(tech_memories),
                'recent_tech_memories': tech_memories[-5:] if tech_memories else []
            }
        except Exception as e:
            return {'error': f'Error getting agent tech learning: {str(e)}'}
    
    def calculate_research_cost(self, user_id: str, tech_id: str, include_prerequisites: bool = True) -> Dict[str, Any]:
        """Calculate total research cost for a technology"""
        if tech_id not in self.tech_tree:
            return {'error': 'Technology not found'}
        
        tech = self.tech_tree[tech_id]
        user_research = self.user_research.get(user_id, {})
        
        total_cost = 0
        techs_to_research = []
        
        if include_prerequisites:
            # Calculate cost including prerequisites
            prerequisites = tech.get('prerequisites', [])
            for prereq_id in prerequisites:
                prereq = self.tech_tree.get(prereq_id)
                if prereq and user_research.get(prereq_id, {}).get('status') != 'completed':
                    prereq_cost = prereq.get('cost', 0)
                    total_cost += prereq_cost
                    techs_to_research.append({
                        'tech_id': prereq_id,
                        'name': prereq.get('name'),
                        'cost': prereq_cost
                    })
        
        # Add main tech cost
        if user_research.get(tech_id, {}).get('status') != 'completed':
            tech_cost = tech.get('cost', 0)
            total_cost += tech_cost
            techs_to_research.append({
                'tech_id': tech_id,
                'name': tech.get('name'),
                'cost': tech_cost
            })
        
        return {
            'success': True,
            'tech_id': tech_id,
            'tech_name': tech.get('name'),
            'base_cost': tech.get('cost', 0),
            'total_cost': total_cost,
            'techs_to_research': techs_to_research,
            'include_prerequisites': include_prerequisites,
            'already_researched': user_research.get(tech_id, {}).get('status') == 'completed'
        }
    
    def calculate_research_time(self, user_id: str, tech_id: str, include_prerequisites: bool = True) -> Dict[str, Any]:
        """Calculate total research time for a technology"""
        if tech_id not in self.tech_tree:
            return {'error': 'Technology not found'}
        
        tech = self.tech_tree[tech_id]
        user_research = self.user_research.get(user_id, {})
        
        total_time = 0  # in minutes
        techs_to_research = []
        
        # Get research bonuses (speed bonuses)
        bonuses = self.get_research_bonuses(user_id)
        speed_bonus = bonuses.get('bonuses', {}).get('calculation_speed', 0)
        efficiency_bonus = bonuses.get('bonuses', {}).get('efficiency', 0)
        total_speed_bonus = speed_bonus + efficiency_bonus
        
        if include_prerequisites:
            # Calculate time including prerequisites
            prerequisites = tech.get('prerequisites', [])
            for prereq_id in prerequisites:
                prereq = self.tech_tree.get(prereq_id)
                if prereq and user_research.get(prereq_id, {}).get('status') != 'completed':
                    prereq_time = prereq.get('research_time', 0)
                    # Apply speed bonus
                    adjusted_time = prereq_time * (1 - total_speed_bonus)
                    total_time += adjusted_time
                    techs_to_research.append({
                        'tech_id': prereq_id,
                        'name': prereq.get('name'),
                        'base_time': prereq_time,
                        'adjusted_time': adjusted_time
                    })
        
        # Add main tech time
        if user_research.get(tech_id, {}).get('status') != 'completed':
            tech_time = tech.get('research_time', 0)
            # Apply speed bonus
            adjusted_time = tech_time * (1 - total_speed_bonus)
            total_time += adjusted_time
            techs_to_research.append({
                'tech_id': tech_id,
                'name': tech.get('name'),
                'base_time': tech_time,
                'adjusted_time': adjusted_time
            })
        
        # Convert to hours and days
        hours = total_time / 60
        days = hours / 24
        
        return {
            'success': True,
            'tech_id': tech_id,
            'tech_name': tech.get('name'),
            'base_time_minutes': tech.get('research_time', 0),
            'total_time_minutes': total_time,
            'total_time_hours': round(hours, 2),
            'total_time_days': round(days, 2),
            'speed_bonus': total_speed_bonus,
            'techs_to_research': techs_to_research,
            'include_prerequisites': include_prerequisites,
            'estimated_completion': self._estimate_completion_time(total_time)
        }
    
    def _estimate_completion_time(self, minutes: float) -> Dict[str, Any]:
        """Estimate completion time in human-readable format"""
        hours = minutes / 60
        days = hours / 24
        
        if days >= 1:
            return {
                'days': int(days),
                'hours': int(hours % 24),
                'minutes': int(minutes % 60),
                'formatted': f"{int(days)}d {int(hours % 24)}h {int(minutes % 60)}m"
            }
        elif hours >= 1:
            return {
                'hours': int(hours),
                'minutes': int(minutes % 60),
                'formatted': f"{int(hours)}h {int(minutes % 60)}m"
            }
        else:
            return {
                'minutes': int(minutes),
                'formatted': f"{int(minutes)}m"
            }
    
    def predict_bonuses(self, user_id: str, tech_id: str, include_prerequisites: bool = True) -> Dict[str, Any]:
        """Predict bonuses from researching a technology"""
        if tech_id not in self.tech_tree:
            return {'error': 'Technology not found'}
        
        tech = self.tech_tree[tech_id]
        user_research = self.user_research.get(user_id, {})
        
        predicted_bonuses = {}
        techs_to_research = []
        
        if include_prerequisites:
            # Get bonuses from prerequisites
            prerequisites = tech.get('prerequisites', [])
            for prereq_id in prerequisites:
                prereq = self.tech_tree.get(prereq_id)
                if prereq and user_research.get(prereq_id, {}).get('status') != 'completed':
                    prereq_bonuses = prereq.get('bonuses', {})
                    for bonus_type, value in prereq_bonuses.items():
                        if bonus_type not in predicted_bonuses:
                            predicted_bonuses[bonus_type] = 0
                        predicted_bonuses[bonus_type] += value
                    
                    techs_to_research.append({
                        'tech_id': prereq_id,
                        'name': prereq.get('name'),
                        'bonuses': prereq_bonuses
                    })
        
        # Add main tech bonuses
        if user_research.get(tech_id, {}).get('status') != 'completed':
            tech_bonuses = tech.get('bonuses', {})
            for bonus_type, value in tech_bonuses.items():
                if bonus_type not in predicted_bonuses:
                    predicted_bonuses[bonus_type] = 0
                predicted_bonuses[bonus_type] += value
            
            techs_to_research.append({
                'tech_id': tech_id,
                'name': tech.get('name'),
                'bonuses': tech_bonuses
            })
        
        # Get current bonuses
        current_bonuses = self.get_research_bonuses(user_id)
        current_total = current_bonuses.get('bonuses', {})
        
        # Calculate new totals
        new_totals = {}
        for bonus_type, value in current_total.items():
            new_totals[bonus_type] = value
        for bonus_type, value in predicted_bonuses.items():
            if bonus_type not in new_totals:
                new_totals[bonus_type] = 0
            new_totals[bonus_type] += value
        
        return {
            'success': True,
            'tech_id': tech_id,
            'tech_name': tech.get('name'),
            'predicted_bonuses': predicted_bonuses,
            'current_bonuses': current_total,
            'new_total_bonuses': new_totals,
            'bonus_increases': {k: predicted_bonuses.get(k, 0) for k in new_totals.keys()},
            'techs_to_research': techs_to_research,
            'include_prerequisites': include_prerequisites
        }
    
    def calculate_research_path(self, user_id: str, target_tech_id: str) -> Dict[str, Any]:
        """Calculate optimal research path to a target technology"""
        if target_tech_id not in self.tech_tree:
            return {'error': 'Technology not found'}
        
        user_research = self.user_research.get(user_id, {})
        completed_tech = [tech_id for tech_id, data in user_research.items() 
                         if data.get('status') == 'completed']
        
        # Find all prerequisites recursively
        def get_all_prerequisites(tech_id: str, visited: set = None) -> List[str]:
            if visited is None:
                visited = set()
            
            if tech_id in visited or tech_id in completed_tech:
                return []
            
            visited.add(tech_id)
            tech = self.tech_tree.get(tech_id, {})
            prerequisites = tech.get('prerequisites', [])
            
            all_prereqs = []
            for prereq_id in prerequisites:
                if prereq_id not in completed_tech:
                    all_prereqs.append(prereq_id)
                    all_prereqs.extend(get_all_prerequisites(prereq_id, visited))
            
            return all_prereqs
        
        prerequisites = get_all_prerequisites(target_tech_id)
        prerequisites.append(target_tech_id)
        
        # Calculate costs and times
        total_cost = 0
        total_time = 0
        path_techs = []
        
        for tech_id in prerequisites:
            tech = self.tech_tree.get(tech_id, {})
            if tech:
                cost = tech.get('cost', 0)
                time = tech.get('research_time', 0)
                total_cost += cost
                total_time += time
                
                path_techs.append({
                    'tech_id': tech_id,
                    'name': tech.get('name'),
                    'tier': tech.get('tier', 1),
                    'category': tech.get('category', 'general'),
                    'cost': cost,
                    'research_time': time,
                    'prerequisites': tech.get('prerequisites', [])
                })
        
        # Sort by tier
        path_techs.sort(key=lambda x: (x['tier'], x['tech_id']))
        
        return {
            'success': True,
            'target_tech_id': target_tech_id,
            'target_tech_name': self.tech_tree[target_tech_id].get('name'),
            'research_path': path_techs,
            'total_cost': total_cost,
            'total_time_minutes': total_time,
            'total_time_hours': round(total_time / 60, 2),
            'total_time_days': round(total_time / 60 / 24, 2),
            'path_length': len(path_techs),
            'estimated_completion': self._estimate_completion_time(total_time)
        }


tech_tree_system = TechTreeSystem()

