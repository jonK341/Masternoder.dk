"""
Psychological Defense Mechanisms Engine
Mathematical calculation system for defense mechanisms, points, and psychological warfare
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import math
import json

class DefenseMechanism(Enum):
    """Psychological defense mechanisms"""
    DENIAL = "denial"
    PROJECTION = "projection"
    DISPLACEMENT = "displacement"
    RATIONALIZATION = "rationalization"
    REACTION_FORMATION = "reaction_formation"
    REGRESSION = "regression"
    SUBLIMATION = "sublimation"
    REPRESSION = "repression"
    INTELLECTUALIZATION = "intellectualization"
    COMPENSATION = "compensation"
    IDENTIFICATION = "identification"
    UNDOING = "undoing"
    SPLITTING = "splitting"
    DISSOCIATION = "dissociation"
    ISOLATION = "isolation"

class SkillType(Enum):
    """Skill categories"""
    LOGIC = "logic"
    ORGANIZATION = "organization"
    SOCIAL = "social"
    TECHNICAL = "technical"
    STRATEGIC = "strategic"
    PSYCHOLOGICAL = "psychological"

class EnemyType(Enum):
    """Enemy website company types"""
    COMPETITOR = "competitor"
    HACKER = "hacker"
    SCAMMER = "scammer"
    CORPORATE = "corporate"
    GOVERNMENT = "government"
    RIVAL_PLATFORM = "rival_platform"

class HackType(Enum):
    """Hack and scam types"""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    PHISHING = "phishing"
    SOCIAL_ENGINEERING = "social_engineering"
    DDOS = "ddos"
    BRUTE_FORCE = "brute_force"
    MAN_IN_THE_MIDDLE = "man_in_the_middle"
    PASSWORD_CRACKING = "password_cracking"
    EXPLOIT = "exploit"

class DefenseMechanismsEngine:
    """Main engine for psychological defense mechanisms"""
    
    def __init__(self):
        self.base_multipliers = {
            DefenseMechanism.DENIAL: 1.2,
            DefenseMechanism.PROJECTION: 1.5,
            DefenseMechanism.DISPLACEMENT: 1.3,
            DefenseMechanism.RATIONALIZATION: 1.4,
            DefenseMechanism.REACTION_FORMATION: 1.6,
            DefenseMechanism.REGRESSION: 0.8,
            DefenseMechanism.SUBLIMATION: 2.0,
            DefenseMechanism.REPRESSION: 1.1,
            DefenseMechanism.INTELLECTUALIZATION: 1.7,
            DefenseMechanism.COMPENSATION: 1.5,
            DefenseMechanism.IDENTIFICATION: 1.8,
            DefenseMechanism.UNDOING: 1.3,
            DefenseMechanism.SPLITTING: 1.2,
            DefenseMechanism.DISSOCIATION: 1.0,
            DefenseMechanism.ISOLATION: 1.4,
        }
        
        self.skill_multipliers = {
            SkillType.LOGIC: 1.5,
            SkillType.ORGANIZATION: 1.3,
            SkillType.SOCIAL: 1.4,
            SkillType.TECHNICAL: 1.6,
            SkillType.STRATEGIC: 1.7,
            SkillType.PSYCHOLOGICAL: 2.0,
        }
        
        self.enemy_threat_levels = {
            EnemyType.COMPETITOR: 1.2,
            EnemyType.HACKER: 2.0,
            EnemyType.SCAMMER: 1.5,
            EnemyType.CORPORATE: 1.8,
            EnemyType.GOVERNMENT: 2.5,
            EnemyType.RIVAL_PLATFORM: 1.6,
        }
        
        self.hack_difficulty = {
            HackType.SQL_INJECTION: 1.5,
            HackType.XSS: 1.2,
            HackType.CSRF: 1.0,
            HackType.PHISHING: 0.8,
            HackType.SOCIAL_ENGINEERING: 1.3,
            HackType.DDOS: 1.4,
            HackType.BRUTE_FORCE: 1.1,
            HackType.MAN_IN_THE_MIDDLE: 1.6,
            HackType.PASSWORD_CRACKING: 1.3,
            HackType.EXPLOIT: 1.8,
        }
    
    def calculate_defense_points(
        self,
        mechanism: DefenseMechanism,
        base_points: float,
        skill_levels: Dict[SkillType, float],
        enemy_threat: EnemyType,
        time_factor: float = 1.0
    ) -> Dict[str, float]:
        """
        Calculate defense mechanism points mathematically
        
        Formula:
        points = base_points * mechanism_multiplier * skill_multiplier * enemy_threat * time_factor
        """
        mechanism_mult = self.base_multipliers.get(mechanism, 1.0)
        
        # Calculate skill multiplier (weighted average)
        total_skill_mult = 0.0
        total_weight = 0.0
        for skill_type, level in skill_levels.items():
            skill_mult = self.skill_multipliers.get(skill_type, 1.0)
            weighted_mult = skill_mult * (level / 100.0)  # Normalize to 0-1
            total_skill_mult += weighted_mult
            total_weight += 1.0
        
        avg_skill_mult = total_skill_mult / total_weight if total_weight > 0 else 1.0
        
        # Enemy threat multiplier
        threat_mult = self.enemy_threat_levels.get(enemy_threat, 1.0)
        
        # Final calculation
        final_points = base_points * mechanism_mult * avg_skill_mult * threat_mult * time_factor
        
        # Calculate breakdown
        breakdown = {
            'base_points': base_points,
            'mechanism_multiplier': mechanism_mult,
            'skill_multiplier': avg_skill_mult,
            'enemy_threat_multiplier': threat_mult,
            'time_factor': time_factor,
            'final_points': round(final_points, 2),
            'mechanism': mechanism.value,
            'enemy_type': enemy_threat.value,
        }
        
        return breakdown
    
    def calculate_hack_points(
        self,
        hack_type: HackType,
        success_rate: float,
        skill_levels: Dict[SkillType, float],
        target_enemy: EnemyType
    ) -> Dict[str, float]:
        """
        Calculate hack/scam points
        
        Formula:
        points = base_hack_points * difficulty * success_rate * skill_multiplier * enemy_resistance
        """
        base_points = 100.0
        difficulty = self.hack_difficulty.get(hack_type, 1.0)
        enemy_resistance = 1.0 / self.enemy_threat_levels.get(target_enemy, 1.0)  # Inverse
        
        # Calculate skill multiplier (technical and strategic weighted more)
        tech_skill = skill_levels.get(SkillType.TECHNICAL, 0.0) / 100.0
        strat_skill = skill_levels.get(SkillType.STRATEGIC, 0.0) / 100.0
        social_skill = skill_levels.get(SkillType.SOCIAL, 0.0) / 100.0
        
        skill_mult = (tech_skill * 0.4 + strat_skill * 0.3 + social_skill * 0.3)
        
        # Final calculation
        final_points = base_points * difficulty * success_rate * skill_mult * enemy_resistance
        
        breakdown = {
            'base_points': base_points,
            'hack_type': hack_type.value,
            'difficulty': difficulty,
            'success_rate': success_rate,
            'skill_multiplier': skill_mult,
            'enemy_resistance': enemy_resistance,
            'final_points': round(final_points, 2),
            'target_enemy': target_enemy.value,
        }
        
        return breakdown
    
    def calculate_total_user_points(
        self,
        defense_actions: List[Dict],
        hack_actions: List[Dict],
        base_xp: float = 0.0
    ) -> Dict[str, float]:
        """
        Recalculate all user points from scratch
        
        This ensures mathematical accuracy
        """
        total_defense_points = sum(
            action.get('final_points', 0.0) for action in defense_actions
        )
        
        total_hack_points = sum(
            action.get('final_points', 0.0) for action in hack_actions
        )
        
        # Calculate bonuses
        defense_count = len(defense_actions)
        hack_count = len(hack_actions)
        
        # Activity bonus (more actions = more bonus, but diminishing returns)
        activity_bonus = math.log(defense_count + hack_count + 1) * 10
        
        # Diversity bonus (using different mechanisms/hacks)
        unique_defenses = len(set(a.get('mechanism', '') for a in defense_actions))
        unique_hacks = len(set(a.get('hack_type', '') for a in hack_actions))
        diversity_bonus = (unique_defenses + unique_hacks) * 5
        
        total_points = (
            base_xp +
            total_defense_points +
            total_hack_points +
            activity_bonus +
            diversity_bonus
        )
        
        # Calculate level from total points
        level = self._calculate_level(total_points)
        
        return {
            'base_xp': base_xp,
            'defense_points': round(total_defense_points, 2),
            'hack_points': round(total_hack_points, 2),
            'activity_bonus': round(activity_bonus, 2),
            'diversity_bonus': round(diversity_bonus, 2),
            'total_points': round(total_points, 2),
            'level': level,
            'defense_actions_count': defense_count,
            'hack_actions_count': hack_count,
            'unique_defenses': unique_defenses,
            'unique_hacks': unique_hacks,
        }
    
    def _calculate_level(self, total_points: float) -> int:
        """Calculate level from total points (exponential curve)"""
        if total_points <= 0:
            return 1
        
        # Level = floor(log2(points / 100) + 1)
        level = int(math.log2(total_points / 100.0) + 1)
        return max(1, min(level, 100))  # Cap at level 100
    
    def get_enemy_websites(self) -> List[Dict]:
        """Get list of enemy websites with their properties"""
        return [
            {
                'id': 'competitor_1',
                'name': 'RivalVideoGen',
                'type': EnemyType.COMPETITOR.value,
                'threat_level': 1.2,
                'skills': {
                    'logic': 60,
                    'organization': 70,
                    'social': 50,
                },
                'weaknesses': ['social', 'technical'],
            },
            {
                'id': 'hacker_group_1',
                'name': 'DarkNet Hackers',
                'type': EnemyType.HACKER.value,
                'threat_level': 2.0,
                'skills': {
                    'logic': 90,
                    'organization': 80,
                    'social': 40,
                    'technical': 95,
                },
                'weaknesses': ['social', 'psychological'],
            },
            {
                'id': 'scammer_network',
                'name': 'Phishing Network',
                'type': EnemyType.SCAMMER.value,
                'threat_level': 1.5,
                'skills': {
                    'logic': 50,
                    'organization': 60,
                    'social': 85,
                    'psychological': 80,
                },
                'weaknesses': ['logic', 'technical'],
            },
            {
                'id': 'corporate_spy',
                'name': 'Corporate Intelligence',
                'type': EnemyType.CORPORATE.value,
                'threat_level': 1.8,
                'skills': {
                    'logic': 75,
                    'organization': 90,
                    'social': 70,
                    'strategic': 85,
                },
                'weaknesses': ['technical', 'psychological'],
            },
            {
                'id': 'gov_agency',
                'name': 'Government Agency',
                'type': EnemyType.GOVERNMENT.value,
                'threat_level': 2.5,
                'skills': {
                    'logic': 85,
                    'organization': 95,
                    'social': 60,
                    'strategic': 90,
                    'technical': 80,
                },
                'weaknesses': ['social', 'psychological'],
            },
            {
                'id': 'rival_platform',
                'name': 'Competitor Platform',
                'type': EnemyType.RIVAL_PLATFORM.value,
                'threat_level': 1.6,
                'skills': {
                    'logic': 70,
                    'organization': 75,
                    'social': 65,
                    'technical': 70,
                },
                'weaknesses': ['strategic', 'psychological'],
            },
        ]
    
    def get_available_hacks(self) -> List[Dict]:
        """Get list of available hacks and scams"""
        return [
            {
                'type': HackType.SQL_INJECTION.value,
                'name': 'SQL Injection',
                'description': 'Exploit database vulnerabilities',
                'difficulty': 1.5,
                'required_skills': ['technical', 'logic'],
            },
            {
                'type': HackType.XSS.value,
                'name': 'Cross-Site Scripting',
                'description': 'Inject malicious scripts',
                'difficulty': 1.2,
                'required_skills': ['technical'],
            },
            {
                'type': HackType.PHISHING.value,
                'name': 'Phishing Attack',
                'description': 'Social engineering via fake emails',
                'difficulty': 0.8,
                'required_skills': ['social', 'psychological'],
            },
            {
                'type': HackType.SOCIAL_ENGINEERING.value,
                'name': 'Social Engineering',
                'description': 'Manipulate people to gain access',
                'difficulty': 1.3,
                'required_skills': ['social', 'psychological'],
            },
            {
                'type': HackType.DDOS.value,
                'name': 'DDoS Attack',
                'description': 'Overwhelm target with traffic',
                'difficulty': 1.4,
                'required_skills': ['technical', 'organization'],
            },
            {
                'type': HackType.EXPLOIT.value,
                'name': 'Zero-Day Exploit',
                'description': 'Use unknown vulnerability',
                'difficulty': 1.8,
                'required_skills': ['technical', 'strategic', 'logic'],
            },
        ]

