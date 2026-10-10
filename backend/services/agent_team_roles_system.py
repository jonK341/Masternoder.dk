"""
Agent Team Roles System
Team Manager and Secretary agent types with comprehensive skills, abilities, and activities
Integrated with unified point system and 178 systems
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

class AgentTeamRolesSystem:
    """
    Team Manager and Secretary agent roles
    Each with 10 skills, 7-8 top abilities, activity patterns, and battle actions
    """
    
    # Team Manager Agent Type
    TEAM_MANAGER_AGENT = {
        'id': 'team_manager',
        'name': 'Team Manager',
        'role': 'Leadership & Coordination',
        'description': 'Expert in team coordination, resource allocation, and strategic planning',
        'icon': '👔',
        'color': '#4a90e2',
        
        # 10 Core Skills
        'skills': [
            {
                'id': 'team_coordination',
                'name': 'Team Coordination',
                'description': 'Coordinate multiple team members efficiently',
                'level': 1,
                'max_level': 100,
                'point_value': 150,
                'category': 'leadership',
                'effects': {
                    'team_efficiency_bonus': 0.15,
                    'task_completion_speed': 0.20
                }
            },
            {
                'id': 'resource_allocation',
                'name': 'Resource Allocation',
                'description': 'Optimally distribute resources across projects',
                'level': 1,
                'max_level': 100,
                'point_value': 140,
                'category': 'management',
                'effects': {
                    'resource_efficiency': 0.25,
                    'waste_reduction': 0.30
                }
            },
            {
                'id': 'strategic_planning',
                'name': 'Strategic Planning',
                'description': 'Develop long-term strategies and roadmaps',
                'level': 1,
                'max_level': 100,
                'point_value': 180,
                'category': 'strategy',
                'effects': {
                    'planning_accuracy': 0.20,
                    'goal_achievement_rate': 0.25
                }
            },
            {
                'id': 'conflict_resolution',
                'name': 'Conflict Resolution',
                'description': 'Resolve team conflicts and maintain harmony',
                'level': 1,
                'max_level': 100,
                'point_value': 130,
                'category': 'leadership',
                'effects': {
                    'team_morale': 0.30,
                    'conflict_reduction': 0.40
                }
            },
            {
                'id': 'performance_optimization',
                'name': 'Performance Optimization',
                'description': 'Optimize team performance and productivity',
                'level': 1,
                'max_level': 100,
                'point_value': 160,
                'category': 'management',
                'effects': {
                    'productivity_bonus': 0.25,
                    'quality_improvement': 0.20
                }
            },
            {
                'id': 'delegation_mastery',
                'name': 'Delegation Mastery',
                'description': 'Effectively delegate tasks to team members',
                'level': 1,
                'max_level': 100,
                'point_value': 145,
                'category': 'leadership',
                'effects': {
                    'delegation_efficiency': 0.30,
                    'workload_balance': 0.25
                }
            },
            {
                'id': 'team_motivation',
                'name': 'Team Motivation',
                'description': 'Inspire and motivate team members',
                'level': 1,
                'max_level': 100,
                'point_value': 135,
                'category': 'leadership',
                'effects': {
                    'motivation_boost': 0.35,
                    'engagement_level': 0.30
                }
            },
            {
                'id': 'risk_management',
                'name': 'Risk Management',
                'description': 'Identify and mitigate project risks',
                'level': 1,
                'max_level': 100,
                'point_value': 170,
                'category': 'strategy',
                'effects': {
                    'risk_reduction': 0.40,
                    'crisis_prevention': 0.35
                }
            },
            {
                'id': 'stakeholder_communication',
                'name': 'Stakeholder Communication',
                'description': 'Communicate effectively with stakeholders',
                'level': 1,
                'max_level': 100,
                'point_value': 155,
                'category': 'communication',
                'effects': {
                    'communication_clarity': 0.30,
                    'stakeholder_satisfaction': 0.25
                }
            },
            {
                'id': 'agile_leadership',
                'name': 'Agile Leadership',
                'description': 'Lead teams using agile methodologies',
                'level': 1,
                'max_level': 100,
                'point_value': 165,
                'category': 'management',
                'effects': {
                    'adaptability': 0.35,
                    'iteration_speed': 0.30
                }
            }
        ],
        
        # 8 Top Abilities
        'top_abilities': [
            {
                'id': 'team_synergy_boost',
                'name': 'Team Synergy Boost',
                'description': 'Temporarily boost all team member stats by 25%',
                'cooldown': 300,  # 5 minutes
                'duration': 60,  # 1 minute
                'trigger': 'battle_start',
                'effect': {
                    'team_stat_boost': 0.25,
                    'synergy_multiplier': 1.5
                },
                'point_value': 500
            },
            {
                'id': 'strategic_command',
                'name': 'Strategic Command',
                'description': 'Issue strategic commands that optimize team actions',
                'cooldown': 180,  # 3 minutes
                'duration': 30,
                'trigger': 'on_demand',
                'effect': {
                    'action_optimization': 0.40,
                    'decision_quality': 0.35
                },
                'point_value': 450
            },
            {
                'id': 'resource_redistribution',
                'name': 'Resource Redistribution',
                'description': 'Instantly redistribute resources for maximum efficiency',
                'cooldown': 240,  # 4 minutes
                'duration': 45,
                'trigger': 'resource_shortage',
                'effect': {
                    'resource_efficiency': 0.50,
                    'bottleneck_removal': 0.60
                },
                'point_value': 480
            },
            {
                'id': 'morale_boost',
                'name': 'Morale Boost',
                'description': 'Massively boost team morale and performance',
                'cooldown': 360,  # 6 minutes
                'duration': 90,
                'trigger': 'team_low_morale',
                'effect': {
                    'morale_boost': 0.50,
                    'performance_bonus': 0.30
                },
                'point_value': 520
            },
            {
                'id': 'crisis_management',
                'name': 'Crisis Management',
                'description': 'Activate emergency protocols to handle crises',
                'cooldown': 600,  # 10 minutes
                'duration': 120,
                'trigger': 'crisis_detected',
                'effect': {
                    'crisis_resolution': 0.70,
                    'damage_mitigation': 0.60
                },
                'point_value': 600
            },
            {
                'id': 'team_formation',
                'name': 'Team Formation',
                'description': 'Create optimal team formations for specific tasks',
                'cooldown': 180,
                'duration': 60,
                'trigger': 'task_assignment',
                'effect': {
                    'formation_bonus': 0.35,
                    'task_success_rate': 0.40
                },
                'point_value': 470
            },
            {
                'id': 'leadership_aura',
                'name': 'Leadership Aura',
                'description': 'Passive aura that boosts nearby team members',
                'cooldown': 0,  # Passive
                'duration': -1,  # Permanent while active
                'trigger': 'always_active',
                'effect': {
                    'aura_radius': 50,
                    'stat_boost': 0.10
                },
                'point_value': 550
            },
            {
                'id': 'executive_decision',
                'name': 'Executive Decision',
                'description': 'Make critical decisions that change battle outcome',
                'cooldown': 480,  # 8 minutes
                'duration': 20,
                'trigger': 'critical_moment',
                'effect': {
                    'decision_impact': 0.80,
                    'outcome_optimization': 0.70
                },
                'point_value': 650
            }
        ],
        
        # Activity Patterns (When they do what)
        'activity_patterns': [
            {
                'time_window': '06:00-09:00',
                'name': 'Morning Briefing',
                'actions': [
                    'Review overnight reports',
                    'Plan daily team objectives',
                    'Allocate morning resources',
                    'Check team status'
                ],
                'cadence': 'daily',
                'rewards': {
                    'points': 50,
                    'xp': 25,
                    'team_efficiency_bonus': 0.10
                }
            },
            {
                'time_window': '09:00-12:00',
                'name': 'Active Management',
                'actions': [
                    'Coordinate team activities',
                    'Monitor project progress',
                    'Resolve conflicts',
                    'Optimize resource allocation'
                ],
                'cadence': 'continuous',
                'rewards': {
                    'points': 30,
                    'xp': 15,
                    'productivity_bonus': 0.15
                }
            },
            {
                'time_window': '12:00-13:00',
                'name': 'Strategic Planning',
                'actions': [
                    'Develop long-term strategies',
                    'Analyze performance metrics',
                    'Plan resource needs',
                    'Risk assessment'
                ],
                'cadence': 'daily',
                'rewards': {
                    'points': 75,
                    'xp': 40,
                    'strategy_bonus': 0.20
                }
            },
            {
                'time_window': '13:00-17:00',
                'name': 'Team Coordination',
                'actions': [
                    'Facilitate team meetings',
                    'Delegate tasks',
                    'Monitor progress',
                    'Provide feedback'
                ],
                'cadence': 'continuous',
                'rewards': {
                    'points': 25,
                    'xp': 12,
                    'coordination_bonus': 0.12
                }
            },
            {
                'time_window': '17:00-19:00',
                'name': 'Performance Review',
                'actions': [
                    'Review daily performance',
                    'Identify improvements',
                    'Plan next day',
                    'Update stakeholders'
                ],
                'cadence': 'daily',
                'rewards': {
                    'points': 60,
                    'xp': 30,
                    'optimization_bonus': 0.18
                }
            },
            {
                'time_window': '19:00-22:00',
                'name': 'Strategic Analysis',
                'actions': [
                    'Analyze team data',
                    'Optimize strategies',
                    'Plan future initiatives',
                    'Research best practices'
                ],
                'cadence': 'daily',
                'rewards': {
                    'points': 80,
                    'xp': 45,
                    'analysis_bonus': 0.25
                }
            }
        ],
        
        # Battle Actions (Extra combat abilities)
        'battle_actions': [
            {
                'id': 'command_formation',
                'name': 'Command Formation',
                'description': 'Organize team into optimal battle formation',
                'effect': {
                    'defense_bonus': 0.30,
                    'attack_coordination': 0.25
                },
                'cooldown': 90,
                'synergy': ['team_synergy_boost', 'strategic_command']
            },
            {
                'id': 'tactical_retreat',
                'name': 'Tactical Retreat',
                'description': 'Order strategic retreat to minimize losses',
                'effect': {
                    'damage_reduction': 0.50,
                    'escape_success': 0.80
                },
                'cooldown': 180,
                'condition': 'team_health < 30%'
            },
            {
                'id': 'rally_cry',
                'name': 'Rally Cry',
                'description': 'Inspire team to fight harder',
                'effect': {
                    'attack_bonus': 0.35,
                    'morale_boost': 0.40
                },
                'cooldown': 120,
                'synergy': ['morale_boost', 'leadership_aura']
            },
            {
                'id': 'resource_boost',
                'name': 'Resource Boost',
                'description': 'Temporarily increase team resources',
                'effect': {
                    'resource_generation': 0.50,
                    'ability_cooldown_reduction': 0.25
                },
                'cooldown': 150,
                'synergy': ['resource_redistribution']
            },
            {
                'id': 'team_shield',
                'name': 'Team Shield',
                'description': 'Protect entire team with defensive barrier',
                'effect': {
                    'damage_absorption': 0.40,
                    'status_effect_resistance': 0.50
                },
                'cooldown': 200,
                'condition': 'enemy_attack_incoming'
            },
            {
                'id': 'coordinated_strike',
                'name': 'Coordinated Strike',
                'description': 'Team executes perfectly timed attack',
                'effect': {
                    'damage_multiplier': 2.0,
                    'critical_chance': 0.50
                },
                'cooldown': 240,
                'synergy': ['team_synergy_boost', 'strategic_command']
            },
            {
                'id': 'leadership_inspiration',
                'name': 'Leadership Inspiration',
                'description': 'Passive inspiration that boosts team stats',
                'effect': {
                    'passive_stat_boost': 0.15,
                    'ability_power': 0.20
                },
                'cooldown': 0,  # Passive
                'synergy': ['leadership_aura']
            },
            {
                'id': 'executive_order',
                'name': 'Executive Order',
                'description': 'Issue critical order that changes battle flow',
                'effect': {
                    'battle_control': 0.60,
                    'enemy_confusion': 0.40
                },
                'cooldown': 300,
                'synergy': ['executive_decision', 'strategic_command']
            }
        ],
        
        # Point System Integration
        'point_systems': [
            'leadership_points',
            'management_points',
            'strategy_points',
            'team_coordination_points',
            'social_points',
            'activity_points'
        ],
        
        # Unified Points Contribution
        'unified_points_contribution': {
            'base_points_per_action': 25,
            'skill_points_multiplier': 1.5,
            'ability_points_multiplier': 2.0,
            'battle_action_multiplier': 1.8
        }
    }
    
    # Secretary Agent Type
    SECRETARY_AGENT = {
        'id': 'secretary',
        'name': 'Secretary',
        'role': 'Administration & Organization',
        'description': 'Expert in organization, scheduling, documentation, and administrative support',
        'icon': '📋',
        'color': '#9b59b6',
        
        # 10 Core Skills
        'skills': [
            {
                'id': 'document_management',
                'name': 'Document Management',
                'description': 'Organize and manage documents efficiently',
                'level': 1,
                'max_level': 100,
                'point_value': 120,
                'category': 'administration',
                'effects': {
                    'document_organization': 0.30,
                    'retrieval_speed': 0.35
                }
            },
            {
                'id': 'schedule_optimization',
                'name': 'Schedule Optimization',
                'description': 'Create and optimize schedules for maximum efficiency',
                'level': 1,
                'max_level': 100,
                'point_value': 140,
                'category': 'organization',
                'effects': {
                    'schedule_efficiency': 0.40,
                    'time_utilization': 0.35
                }
            },
            {
                'id': 'communication_coordination',
                'name': 'Communication Coordination',
                'description': 'Coordinate communications between parties',
                'level': 1,
                'max_level': 100,
                'point_value': 130,
                'category': 'communication',
                'effects': {
                    'communication_speed': 0.30,
                    'message_clarity': 0.35
                }
            },
            {
                'id': 'data_organization',
                'name': 'Data Organization',
                'description': 'Organize and structure data effectively',
                'level': 1,
                'max_level': 100,
                'point_value': 125,
                'category': 'administration',
                'effects': {
                    'data_accessibility': 0.35,
                    'search_efficiency': 0.40
                }
            },
            {
                'id': 'meeting_coordination',
                'name': 'Meeting Coordination',
                'description': 'Coordinate meetings and manage logistics',
                'level': 1,
                'max_level': 100,
                'point_value': 135,
                'category': 'organization',
                'effects': {
                    'meeting_efficiency': 0.30,
                    'logistics_optimization': 0.35
                }
            },
            {
                'id': 'information_filtering',
                'name': 'Information Filtering',
                'description': 'Filter and prioritize important information',
                'level': 1,
                'max_level': 100,
                'point_value': 145,
                'category': 'administration',
                'effects': {
                    'information_relevance': 0.40,
                    'noise_reduction': 0.45
                }
            },
            {
                'id': 'record_keeping',
                'name': 'Record Keeping',
                'description': 'Maintain accurate and organized records',
                'level': 1,
                'max_level': 100,
                'point_value': 115,
                'category': 'administration',
                'effects': {
                    'record_accuracy': 0.50,
                    'compliance_rate': 0.40
                }
            },
            {
                'id': 'task_prioritization',
                'name': 'Task Prioritization',
                'description': 'Prioritize tasks based on importance and urgency',
                'level': 1,
                'max_level': 100,
                'point_value': 150,
                'category': 'organization',
                'effects': {
                    'priority_accuracy': 0.35,
                    'deadline_management': 0.40
                }
            },
            {
                'id': 'multitasking_mastery',
                'name': 'Multitasking Mastery',
                'description': 'Handle multiple tasks simultaneously',
                'level': 1,
                'max_level': 100,
                'point_value': 155,
                'category': 'administration',
                'effects': {
                    'concurrent_task_limit': 5,
                    'efficiency_maintenance': 0.85
                }
            },
            {
                'id': 'administrative_support',
                'name': 'Administrative Support',
                'description': 'Provide comprehensive administrative support',
                'level': 1,
                'max_level': 100,
                'point_value': 160,
                'category': 'support',
                'effects': {
                    'support_efficiency': 0.40,
                    'workflow_optimization': 0.35
                }
            }
        ],
        
        # 8 Top Abilities
        'top_abilities': [
            {
                'id': 'administrative_overdrive',
                'name': 'Administrative Overdrive',
                'description': 'Temporarily boost all administrative efficiency by 40%',
                'cooldown': 300,  # 5 minutes
                'duration': 90,  # 1.5 minutes
                'trigger': 'high_workload',
                'effect': {
                    'admin_efficiency': 0.40,
                    'task_processing_speed': 0.50
                },
                'point_value': 480
            },
            {
                'id': 'perfect_organization',
                'name': 'Perfect Organization',
                'description': 'Instantly organize all pending tasks and documents',
                'cooldown': 240,  # 4 minutes
                'duration': 60,
                'trigger': 'on_demand',
                'effect': {
                    'organization_level': 1.0,
                    'chaos_reduction': 0.80
                },
                'point_value': 450
            },
            {
                'id': 'information_synthesis',
                'name': 'Information Synthesis',
                'description': 'Synthesize information from multiple sources',
                'cooldown': 180,  # 3 minutes
                'duration': 45,
                'trigger': 'information_overload',
                'effect': {
                    'synthesis_quality': 0.60,
                    'insight_generation': 0.50
                },
                'point_value': 420
            },
            {
                'id': 'schedule_mastery',
                'name': 'Schedule Mastery',
                'description': 'Create perfect schedules that maximize productivity',
                'cooldown': 360,  # 6 minutes
                'duration': 120,
                'trigger': 'schedule_creation',
                'effect': {
                    'schedule_optimization': 0.70,
                    'time_efficiency': 0.60
                },
                'point_value': 500
            },
            {
                'id': 'rapid_documentation',
                'name': 'Rapid Documentation',
                'description': 'Document events and decisions instantly',
                'cooldown': 120,  # 2 minutes
                'duration': 30,
                'trigger': 'documentation_needed',
                'effect': {
                    'documentation_speed': 0.80,
                    'accuracy_maintenance': 0.95
                },
                'point_value': 400
            },
            {
                'id': 'communication_network',
                'name': 'Communication Network',
                'description': 'Establish efficient communication network',
                'cooldown': 240,
                'duration': 90,
                'trigger': 'communication_required',
                'effect': {
                    'network_efficiency': 0.50,
                    'message_delivery': 0.70
                },
                'point_value': 440
            },
            {
                'id': 'administrative_aura',
                'name': 'Administrative Aura',
                'description': 'Passive aura that improves organization around agent',
                'cooldown': 0,  # Passive
                'duration': -1,  # Permanent while active
                'trigger': 'always_active',
                'effect': {
                    'aura_radius': 30,
                    'organization_bonus': 0.15
                },
                'point_value': 460
            },
            {
                'id': 'crisis_documentation',
                'name': 'Crisis Documentation',
                'description': 'Document and organize crisis information instantly',
                'cooldown': 300,  # 5 minutes
                'duration': 60,
                'trigger': 'crisis_detected',
                'effect': {
                    'crisis_clarity': 0.70,
                    'response_coordination': 0.60
                },
                'point_value': 520
            }
        ],
        
        # Activity Patterns (When they do what)
        'activity_patterns': [
            {
                'time_window': '07:00-09:00',
                'name': 'Morning Organization',
                'actions': [
                    'Review overnight messages',
                    'Organize daily schedule',
                    'Prioritize tasks',
                    'Prepare documents'
                ],
                'cadence': 'daily',
                'rewards': {
                    'points': 40,
                    'xp': 20,
                    'organization_bonus': 0.15
                }
            },
            {
                'time_window': '09:00-12:00',
                'name': 'Active Administration',
                'actions': [
                    'Handle communications',
                    'Manage documents',
                    'Coordinate meetings',
                    'Process requests'
                ],
                'cadence': 'continuous',
                'rewards': {
                    'points': 20,
                    'xp': 10,
                    'efficiency_bonus': 0.12
                }
            },
            {
                'time_window': '12:00-13:00',
                'name': 'Data Organization',
                'actions': [
                    'Organize data files',
                    'Update records',
                    'Archive documents',
                    'Clean up systems'
                ],
                'cadence': 'daily',
                'rewards': {
                    'points': 50,
                    'xp': 25,
                    'data_organization_bonus': 0.20
                }
            },
            {
                'time_window': '13:00-17:00',
                'name': 'Administrative Support',
                'actions': [
                    'Support team activities',
                    'Manage communications',
                    'Handle documentation',
                    'Coordinate logistics'
                ],
                'cadence': 'continuous',
                'rewards': {
                    'points': 18,
                    'xp': 9,
                    'support_bonus': 0.10
                }
            },
            {
                'time_window': '17:00-19:00',
                'name': 'Evening Documentation',
                'actions': [
                    'Document daily activities',
                    'Update records',
                    'Prepare reports',
                    'Organize for next day'
                ],
                'cadence': 'daily',
                'rewards': {
                    'points': 55,
                    'xp': 28,
                    'documentation_bonus': 0.18
                }
            },
            {
                'time_window': '19:00-22:00',
                'name': 'System Optimization',
                'actions': [
                    'Optimize systems',
                    'Improve workflows',
                    'Research best practices',
                    'Plan improvements'
                ],
                'cadence': 'daily',
                'rewards': {
                    'points': 70,
                    'xp': 35,
                    'optimization_bonus': 0.22
                }
            }
        ],
        
        # Battle Actions (Extra combat abilities)
        'battle_actions': [
            {
                'id': 'tactical_documentation',
                'name': 'Tactical Documentation',
                'description': 'Document enemy patterns and weaknesses',
                'effect': {
                    'intelligence_gain': 0.40,
                    'weakness_identification': 0.35
                },
                'cooldown': 90,
                'synergy': ['information_synthesis', 'rapid_documentation']
            },
            {
                'id': 'organized_retreat',
                'name': 'Organized Retreat',
                'description': 'Coordinate organized retreat with minimal losses',
                'effect': {
                    'retreat_efficiency': 0.60,
                    'asset_preservation': 0.70
                },
                'cooldown': 180,
                'condition': 'team_health < 40%'
            },
            {
                'id': 'communication_jam',
                'name': 'Communication Jam',
                'description': 'Disrupt enemy communications',
                'effect': {
                    'enemy_coordination_reduction': 0.50,
                    'confusion_duration': 30
                },
                'cooldown': 150,
                'synergy': ['communication_network']
            },
            {
                'id': 'resource_tracking',
                'name': 'Resource Tracking',
                'description': 'Track and optimize resource usage',
                'effect': {
                    'resource_efficiency': 0.45,
                    'waste_reduction': 0.50
                },
                'cooldown': 120,
                'synergy': ['data_organization']
            },
            {
                'id': 'priority_shield',
                'name': 'Priority Shield',
                'description': 'Protect high-priority targets',
                'effect': {
                    'protection_bonus': 0.50,
                    'priority_target_safety': 0.80
                },
                'cooldown': 200,
                'condition': 'priority_target_threatened'
            },
            {
                'id': 'coordinated_response',
                'name': 'Coordinated Response',
                'description': 'Coordinate team response to threats',
                'effect': {
                    'response_speed': 0.60,
                    'coordination_bonus': 0.40
                },
                'cooldown': 180,
                'synergy': ['communication_network', 'perfect_organization']
            },
            {
                'id': 'administrative_efficiency',
                'name': 'Administrative Efficiency',
                'description': 'Passive boost to all administrative actions',
                'effect': {
                    'passive_efficiency': 0.20,
                    'action_speed': 0.25
                },
                'cooldown': 0,  # Passive
                'synergy': ['administrative_aura']
            },
            {
                'id': 'crisis_coordination',
                'name': 'Crisis Coordination',
                'description': 'Coordinate response to crisis situations',
                'effect': {
                    'crisis_response': 0.70,
                    'coordination_quality': 0.65
                },
                'cooldown': 300,
                'synergy': ['crisis_documentation', 'communication_network']
            }
        ],
        
        # Point System Integration
        'point_systems': [
            'administration_points',
            'organization_points',
            'communication_points',
            'documentation_points',
            'support_points',
            'activity_points'
        ],
        
        # Unified Points Contribution
        'unified_points_contribution': {
            'base_points_per_action': 20,
            'skill_points_multiplier': 1.4,
            'ability_points_multiplier': 1.9,
            'battle_action_multiplier': 1.7
        }
    }
    
    def __init__(self):
        self.agent_types = {
            'team_manager': self.TEAM_MANAGER_AGENT,
            'secretary': self.SECRETARY_AGENT
        }
        self.user_agents = {}  # {user_id: {agent_id: agent_data}}
        self.agent_activities = {}  # {agent_id: [activity_log]}
        self.agent_skills = {}  # {agent_id: {skill_id: skill_data}}
        self.agent_abilities = {}  # {agent_id: {ability_id: ability_data}}
    
    def get_agent_type(self, agent_type_id: str) -> Dict[str, Any]:
        """Get agent type definition"""
        return self.agent_types.get(agent_type_id, {})
    
    def get_all_agent_types(self) -> Dict[str, Any]:
        """Get all available agent types"""
        return {
            'success': True,
            'agent_types': {
                'team_manager': {
                    'id': self.TEAM_MANAGER_AGENT['id'],
                    'name': self.TEAM_MANAGER_AGENT['name'],
                    'role': self.TEAM_MANAGER_AGENT['role'],
                    'description': self.TEAM_MANAGER_AGENT['description'],
                    'icon': self.TEAM_MANAGER_AGENT['icon'],
                    'skills_count': len(self.TEAM_MANAGER_AGENT['skills']),
                    'abilities_count': len(self.TEAM_MANAGER_AGENT['top_abilities']),
                    'battle_actions_count': len(self.TEAM_MANAGER_AGENT['battle_actions'])
                },
                'secretary': {
                    'id': self.SECRETARY_AGENT['id'],
                    'name': self.SECRETARY_AGENT['name'],
                    'role': self.SECRETARY_AGENT['role'],
                    'description': self.SECRETARY_AGENT['description'],
                    'icon': self.SECRETARY_AGENT['icon'],
                    'skills_count': len(self.SECRETARY_AGENT['skills']),
                    'abilities_count': len(self.SECRETARY_AGENT['top_abilities']),
                    'battle_actions_count': len(self.SECRETARY_AGENT['battle_actions'])
                }
            }
        }
    
    def create_agent(self, user_id: str, agent_name: str, agent_type_id: str) -> Dict[str, Any]:
        """Create a new agent of specified type"""
        agent_type = self.agent_types.get(agent_type_id)
        if not agent_type:
            return {
                'success': False,
                'error': f'Agent type {agent_type_id} not found'
            }
        
        import uuid
        agent_id = str(uuid.uuid4())
        
        agent_data = {
            'id': agent_id,
            'user_id': user_id,
            'agent_name': agent_name,
            'agent_type': agent_type_id,
            'agent_type_data': agent_type,
            'created_at': datetime.utcnow().isoformat(),
            'last_active': datetime.utcnow().isoformat(),
            'level': 1,
            'xp': 0,
            'skills': {},
            'abilities': {},
            'battle_actions': {},
            'activity_log': [],
            'unified_points': {},
            'stats': {
                'tasks_completed': 0,
                'skills_used': 0,
                'abilities_activated': 0,
                'battle_actions_used': 0,
                'points_earned': 0
            }
        }
        
        # Initialize skills
        for skill in agent_type['skills']:
            agent_data['skills'][skill['id']] = {
                **skill,
                'unlocked': True,
                'current_level': 1,
                'experience': 0,
                'unlocked_at': datetime.utcnow().isoformat()
            }
        
        # Initialize abilities (start locked, unlock as agent levels)
        for ability in agent_type['top_abilities']:
            agent_data['abilities'][ability['id']] = {
                **ability,
                'unlocked': ability.get('cooldown', 0) == 0,  # Passive abilities start unlocked
                'current_cooldown': 0,
                'unlocked_at': datetime.utcnow().isoformat() if ability.get('cooldown', 0) == 0 else None
            }
        
        # Initialize battle actions
        for action in agent_type['battle_actions']:
            agent_data['battle_actions'][action['id']] = {
                **action,
                'unlocked': True,
                'uses': 0,
                'last_used': None
            }
        
        # Store agent
        if user_id not in self.user_agents:
            self.user_agents[user_id] = {}
        self.user_agents[user_id][agent_id] = agent_data
        
        # Initialize activity log
        self.agent_activities[agent_id] = []
        
        return {
            'success': True,
            'agent': agent_data
        }
    
    def perform_activity(self, agent_id: str, activity_name: str) -> Dict[str, Any]:
        """Agent performs an activity and earns rewards"""
        agent = self._find_agent(agent_id)
        if not agent:
            return {'success': False, 'error': 'Agent not found'}
        
        agent_type = agent['agent_type_data']
        activity = next((a for a in agent_type['activity_patterns'] if a['name'] == activity_name), None)
        
        if not activity:
            return {'success': False, 'error': 'Activity not found'}
        
        # Check if activity is in current time window
        current_hour = datetime.utcnow().hour
        time_window = activity['time_window'].split('-')
        start_hour = int(time_window[0].split(':')[0])
        end_hour = int(time_window[1].split(':')[0])
        
        if not (start_hour <= current_hour < end_hour):
            return {
                'success': False,
                'error': f'Activity {activity_name} is only available between {activity["time_window"]}'
            }
        
        # Calculate rewards
        base_points = activity['rewards']['points']
        base_xp = activity['rewards']['xp']
        
        # Apply skill bonuses
        skill_bonus = self._calculate_skill_bonuses(agent)
        total_points = int(base_points * (1 + skill_bonus))
        total_xp = int(base_xp * (1 + skill_bonus))
        
        # Award to unified point system
        self._award_unified_points(agent['user_id'], agent_type, total_points, 'activity')
        
        # Update agent stats
        agent['xp'] += total_xp
        agent['stats']['tasks_completed'] += 1
        agent['stats']['points_earned'] += total_points
        
        # Check for level up
        level_up_result = self._check_level_up(agent)
        
        # Log activity
        activity_log = {
            'activity_name': activity_name,
            'timestamp': datetime.utcnow().isoformat(),
            'points_earned': total_points,
            'xp_earned': total_xp,
            'rewards': activity['rewards']
        }
        self.agent_activities[agent_id].append(activity_log)
        agent['activity_log'].append(activity_log)
        
        return {
            'success': True,
            'activity': activity_name,
            'points_earned': total_points,
            'xp_earned': total_xp,
            'level_up': level_up_result.get('leveled_up', False),
            'new_level': level_up_result.get('new_level', agent['level']),
            'bonuses': activity['rewards']
        }
    
    def use_ability(self, agent_id: str, ability_id: str) -> Dict[str, Any]:
        """Agent uses an ability"""
        agent = self._find_agent(agent_id)
        if not agent:
            return {'success': False, 'error': 'Agent not found'}
        
        ability = agent['abilities'].get(ability_id)
        if not ability:
            return {'success': False, 'error': 'Ability not found'}
        
        if not ability.get('unlocked', False):
            return {'success': False, 'error': 'Ability not unlocked'}
        
        if ability.get('current_cooldown', 0) > 0:
            return {
                'success': False,
                'error': f'Ability on cooldown for {ability["current_cooldown"]} seconds'
            }
        
        # Activate ability
        ability['current_cooldown'] = ability.get('cooldown', 0)
        ability['last_used'] = datetime.utcnow().isoformat()
        
        # Award points
        points = ability.get('point_value', 0)
        self._award_unified_points(agent['user_id'], agent['agent_type_data'], points, 'ability')
        
        agent['stats']['abilities_activated'] += 1
        agent['stats']['points_earned'] += points
        
        return {
            'success': True,
            'ability': ability_id,
            'effect': ability['effect'],
            'cooldown': ability['cooldown'],
            'points_earned': points
        }
    
    def use_battle_action(self, agent_id: str, action_id: str, battle_context: Dict = None) -> Dict[str, Any]:
        """Agent uses a battle action"""
        agent = self._find_agent(agent_id)
        if not agent:
            return {'success': False, 'error': 'Agent not found'}
        
        action = agent['battle_actions'].get(action_id)
        if not action:
            return {'success': False, 'error': 'Battle action not found'}
        
        # Check conditions
        if 'condition' in action:
            condition = action['condition']
            if not self._check_condition(condition, battle_context):
                return {'success': False, 'error': f'Condition not met: {condition}'}
        
        # Use action
        action['uses'] = action.get('uses', 0) + 1
        action['last_used'] = datetime.utcnow().isoformat()
        
        # Award points
        points = int(agent['agent_type_data']['unified_points_contribution']['base_points_per_action'] * 
                    agent['agent_type_data']['unified_points_contribution']['battle_action_multiplier'])
        self._award_unified_points(agent['user_id'], agent['agent_type_data'], points, 'battle_action')
        
        agent['stats']['battle_actions_used'] += 1
        agent['stats']['points_earned'] += points
        
        return {
            'success': True,
            'action': action_id,
            'effect': action['effect'],
            'points_earned': points
        }
    
    def _find_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Find agent by ID"""
        for user_agents in self.user_agents.values():
            if agent_id in user_agents:
                return user_agents[agent_id]
        return None
    
    def _calculate_skill_bonuses(self, agent: Dict[str, Any]) -> float:
        """Calculate total skill bonus"""
        total_bonus = 0.0
        for skill_id, skill_data in agent['skills'].items():
            if skill_data.get('unlocked', False):
                level = skill_data.get('current_level', 1)
                # Each level adds 1% bonus
                total_bonus += 0.01 * level
        return min(total_bonus, 1.0)  # Cap at 100% bonus
    
    def _check_level_up(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """Check if agent should level up"""
        xp_needed = agent['level'] * 1000
        if agent['xp'] >= xp_needed:
            agent['level'] += 1
            agent['xp'] -= xp_needed
            
            # Unlock abilities at certain levels
            abilities_unlocked = []
            for ability_id, ability in agent['abilities'].items():
                unlock_level = ability.get('unlock_level', 1)
                if agent['level'] >= unlock_level and not ability.get('unlocked', False):
                    ability['unlocked'] = True
                    ability['unlocked_at'] = datetime.utcnow().isoformat()
                    abilities_unlocked.append(ability_id)
            
            return {
                'leveled_up': True,
                'new_level': agent['level'],
                'abilities_unlocked': abilities_unlocked
            }
        
        return {'leveled_up': False}
    
    def _check_condition(self, condition: str, context: Dict = None) -> bool:
        """Check if battle condition is met"""
        if not context:
            return False
        
        # Simple condition checking (can be expanded)
        if 'team_health' in condition:
            threshold = float(condition.split('<')[1].strip().replace('%', ''))
            team_health = context.get('team_health', 100)
            return team_health < threshold
        
        return True
    
    def _award_unified_points(self, user_id: str, agent_type: Dict, points: int, source: str):
        """Award points to unified point system"""
        try:
            from backend.services.point_connection_system import PointConnectionSystem
            point_connection = PointConnectionSystem()
            
            if point_connection:
                # Award to all relevant point systems
                for point_system in agent_type.get('point_systems', []):
                    point_connection.ensure_point_counting(
                        user_id,
                        point_system.replace('_points', ''),
                        int(points / len(agent_type.get('point_systems', [1]))),
                        f'agent_{agent_type["id"]}_{source}'
                    )
        except Exception as e:
            print(f"[AgentTeamRoles] Error awarding points: {e}")
    
    def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """Get full agent information"""
        agent = self._find_agent(agent_id)
        if not agent:
            return {'success': False, 'error': 'Agent not found'}
        
        return {
            'success': True,
            'agent': agent,
            'activity_log': self.agent_activities.get(agent_id, [])
        }
    
    def get_user_agents(self, user_id: str) -> Dict[str, Any]:
        """Get all agents for a user"""
        user_agents = self.user_agents.get(user_id, {})
        return {
            'success': True,
            'user_id': user_id,
            'agents': list(user_agents.values()),
            'total_agents': len(user_agents)
        }

# Global instance
agent_team_roles_system = AgentTeamRolesSystem()
