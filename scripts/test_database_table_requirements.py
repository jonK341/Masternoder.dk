#!/usr/bin/env python3
"""
Test Database Table Requirements
Analyzes codebase to identify missing database tables
"""
import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class DatabaseTableRequirementsTester:
    """Test and identify missing database tables"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.existing_tables = set()
        self.services_with_json = []
        self.missing_tables = []
        self.recommended_tables = []
    
    def run_analysis(self):
        """Run complete analysis"""
        print("=" * 80)
        print("DATABASE TABLE REQUIREMENTS ANALYSIS")
        print("=" * 80)
        print()
        
        # 1. Get existing tables
        print("1. Analyzing existing database tables...")
        self.analyze_existing_tables()
        print()
        
        # 2. Find services using JSON files
        print("2. Finding services using JSON file storage...")
        self.find_json_file_services()
        print()
        
        # 3. Analyze data structures
        print("3. Analyzing data structures...")
        self.analyze_data_structures()
        print()
        
        # 4. Check for missing tables
        print("4. Identifying missing tables...")
        self.identify_missing_tables()
        print()
        
        # 5. Generate recommendations
        print("5. Generating recommendations...")
        self.generate_recommendations()
        print()
        
        # 6. Generate report
        print("6. Generating report...")
        self.generate_report()
        print()
    
    def analyze_existing_tables(self):
        """Get all existing tables"""
        try:
            inspector = inspect(db.engine)
            self.existing_tables = set(inspector.get_table_names())
            print(f"   Found {len(self.existing_tables)} existing tables:")
            for table in sorted(self.existing_tables):
                # Count records
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"      - {table}: {count} records")
                except Exception:
                    print(f"      - {table}: (error counting)")
        except Exception as e:
            print(f"   [ERROR] Failed to analyze tables: {str(e)}")
    
    def find_json_file_services(self):
        """Find services that use JSON file storage"""
        services_dir = Path("backend/services")
        if not services_dir.exists():
            print("   [WARN] backend/services directory not found")
            return
        
        json_patterns = [
            r'\.json',
            r'json\.load',
            r'json\.dump',
            r'open\(.*\.json',
            r'\.json\)',
        ]
        
        for service_file in services_dir.rglob("*.py"):
            if service_file.name.startswith("__"):
                continue
            
            try:
                content = service_file.read_text(encoding='utf-8', errors='ignore')
                
                # Check for JSON usage
                uses_json = any(re.search(pattern, content, re.IGNORECASE) for pattern in json_patterns)
                
                if uses_json:
                    # Try to identify what data is stored
                    data_types = []
                    if 'mission' in content.lower():
                        data_types.append('missions')
                    if 'quest' in content.lower():
                        data_types.append('quests')
                    if 'personality' in content.lower():
                        data_types.append('personality')
                    if 'intelligence' in content.lower():
                        data_types.append('intelligence')
                    if 'error' in content.lower() and 'use_case' in content.lower():
                        data_types.append('errors')
                        data_types.append('use_cases')
                    if 'profile' in content.lower():
                        data_types.append('profiles')
                    if 'history' in content.lower() or 'skill_history' in content.lower():
                        data_types.append('history')
                    if 'tracker' in service_file.name.lower():
                        data_types.append('tracking')
                    if 'agent' in service_file.name.lower() and 'tech' in service_file.name.lower():
                        data_types.append('agent_tech')
                    
                    self.services_with_json.append({
                        'file': str(service_file.relative_to(Path.cwd())),
                        'data_types': list(set(data_types)) if data_types else ['general']
                    })
            except Exception as e:
                pass
        
        print(f"   Found {len(self.services_with_json)} services using JSON files:")
        for service in self.services_with_json[:20]:  # Show first 20
            print(f"      - {service['file']}: {', '.join(service['data_types'])}")
        if len(self.services_with_json) > 20:
            print(f"      ... and {len(self.services_with_json) - 20} more")
    
    def analyze_data_structures(self):
        """Analyze what data structures need tables"""
        # Check for specific services that need tables
        required_tables = {
            # Agent systems
            'agent_missions': 'master_fix_agent_skills.py',
            'agent_quests': 'master_fix_agent_skills.py',
            'agent_personality': 'master_fix_agent_skills.py',
            'agent_skill_history': 'master_fix_agent_skills.py',
            'agent_ai_intelligence': 'agent_ai_intelligence.py',
            'agent_errors': 'agent_error_handler.py',
            'agent_use_cases': 'agent_error_handler.py',
            
            # User systems
            'user_profiles_file': 'user_onboarding.py',  # Already have user_profiles table
            'user_agent_skills': 'user_agent_skills.py',
            'user_scraped_info': 'user_info_scraper.py',  # May already exist
            
            # Tracking systems
            'point_tracking': 'enhanced_point_tracker.py',
            'agent_ability_tracking': 'agent_ability_tracker.py',
            'agent_research_tracking': 'agent_research_tracker.py',
            
            # Other systems
            'dna_manipulation': 'dna_manipulation_system.py',
            'video_generation_jobs': 'video generation endpoints',
            'rewards': 'rewards system',  # May already exist
            'user_rewards': 'rewards system',  # May already exist
        }
        
        print(f"   Analyzing {len(required_tables)} potential table requirements...")
        
        for table_name, source in required_tables.items():
            if table_name not in self.existing_tables:
                self.missing_tables.append({
                    'table': table_name,
                    'source': source,
                    'priority': self._determine_priority(table_name)
                })
    
    def _determine_priority(self, table_name: str) -> str:
        """Determine priority for table"""
        high_priority = ['agent_missions', 'agent_quests', 'agent_personality', 
                        'user_agent_skills', 'rewards', 'user_rewards']
        medium_priority = ['agent_ai_intelligence', 'agent_errors', 'agent_use_cases',
                          'point_tracking', 'video_generation_jobs']
        
        if table_name in high_priority:
            return 'HIGH'
        elif table_name in medium_priority:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def identify_missing_tables(self):
        """Identify tables that should exist but don't"""
        # Expected tables based on codebase analysis
        expected_tables = {
            # Core game tables
            'player_levels', 'xp_history', 'daily_activities',
            'rewards', 'user_rewards',
            
            # User tables
            'user_profiles', 'user_scraped_info', 'user_agent_skills',
            'onboarding_progress',
            
            # Points tables
            'system_point_snapshots', 'point_transactions', 'point_history',
            'point_aggregates', 'point_analytics', 'system_usage_stats',
            
            # Agent tables
            'agent_technologies', 'agent_technology_improvements',
            'agent_technology_metrics', 'agent_technology_usage',
            'agent_technology_relationships', 'agent_technology_events',
            
            # Calculator tables
            'calculation_history', 'point_loss_detection', 'repair_log',
            'predictions', 'pattern_analysis', 'anomaly_detection',
        }
        
        missing = expected_tables - self.existing_tables
        
        if missing:
            print(f"   Found {len(missing)} potentially missing tables:")
            for table in sorted(missing):
                print(f"      - {table}")
        else:
            print("   [OK] All expected tables exist")
    
    def generate_recommendations(self):
        """Generate table recommendations"""
        recommendations = []
        
        # Agent missions and quests
        if 'agent_missions' not in self.existing_tables:
            recommendations.append({
                'table': 'agent_missions',
                'description': 'Store agent missions with tasks, progress, and rewards',
                'priority': 'HIGH',
                'columns': ['id', 'mission_id', 'user_id', 'mission_name', 'description', 
                           'tasks', 'progress', 'status', 'rewards', 'created_at', 'updated_at']
            })
        
        if 'agent_quests' not in self.existing_tables:
            recommendations.append({
                'table': 'agent_quests',
                'description': 'Store agent quests with objectives and completion status',
                'priority': 'HIGH',
                'columns': ['id', 'quest_id', 'user_id', 'quest_name', 'objectives',
                           'status', 'progress', 'rewards', 'created_at', 'completed_at']
            })
        
        if 'agent_personality' not in self.existing_tables:
            recommendations.append({
                'table': 'agent_personality',
                'description': 'Store agent personality traits and behavior patterns',
                'priority': 'HIGH',
                'columns': ['id', 'user_id', 'personality_type', 'traits', 'behavior_patterns',
                           'experience_level', 'achievements', 'created_at', 'updated_at']
            })
        
        if 'agent_skill_history' not in self.existing_tables:
            recommendations.append({
                'table': 'agent_skill_history',
                'description': 'Store agent skill usage history',
                'priority': 'MEDIUM',
                'columns': ['id', 'user_id', 'skill_name', 'action', 'result', 
                           'points_earned', 'created_at']
            })
        
        if 'agent_ai_intelligence' not in self.existing_tables:
            recommendations.append({
                'table': 'agent_ai_intelligence',
                'description': 'Store AI intelligence data, knowledge base, and patterns',
                'priority': 'MEDIUM',
                'columns': ['id', 'user_id', 'intelligence_type', 'knowledge_data',
                           'patterns', 'predictions', 'decisions', 'created_at', 'updated_at']
            })
        
        if 'agent_errors' not in self.existing_tables:
            recommendations.append({
                'table': 'agent_errors',
                'description': 'Store error logs and patterns for analysis',
                'priority': 'MEDIUM',
                'columns': ['id', 'error_type', 'error_message', 'error_pattern',
                           'category', 'frequency', 'last_occurred', 'created_at']
            })
        
        if 'agent_use_cases' not in self.existing_tables:
            recommendations.append({
                'table': 'agent_use_cases',
                'description': 'Store use cases generated from errors',
                'priority': 'MEDIUM',
                'columns': ['id', 'use_case_id', 'error_id', 'description',
                           'steps', 'status', 'created_at']
            })
        
        if 'video_generation_jobs' not in self.existing_tables:
            recommendations.append({
                'table': 'video_generation_jobs',
                'description': 'Store video generation job status and progress',
                'priority': 'MEDIUM',
                'columns': ['id', 'job_id', 'user_id', 'status', 'progress',
                           'theme', 'clips', 'video_url', 'created_at', 'updated_at']
            })
        
        if 'dna_manipulation' not in self.existing_tables:
            recommendations.append({
                'table': 'dna_manipulation',
                'description': 'Store DNA manipulation and cloning data',
                'priority': 'LOW',
                'columns': ['id', 'user_id', 'manipulation_type', 'dna_data',
                           'cloning_data', 'created_at', 'updated_at']
            })
        
        self.recommended_tables = recommendations
        
        print(f"   Generated {len(recommendations)} table recommendations:")
        for rec in recommendations:
            print(f"      [{rec['priority']}] {rec['table']}: {rec['description']}")
    
    def generate_report(self):
        """Generate comprehensive report"""
        print("=" * 80)
        print("ANALYSIS REPORT")
        print("=" * 80)
        print()
        
        print(f"Existing Tables: {len(self.existing_tables)}")
        print(f"Services Using JSON: {len(self.services_with_json)}")
        print(f"Missing Tables Identified: {len(self.missing_tables)}")
        print(f"Recommended Tables: {len(self.recommended_tables)}")
        print()
        
        if self.recommended_tables:
            print("RECOMMENDED TABLES TO CREATE:")
            print()
            high_priority = [r for r in self.recommended_tables if r['priority'] == 'HIGH']
            medium_priority = [r for r in self.recommended_tables if r['priority'] == 'MEDIUM']
            low_priority = [r for r in self.recommended_tables if r['priority'] == 'LOW']
            
            if high_priority:
                print("HIGH PRIORITY:")
                for rec in high_priority:
                    print(f"   - {rec['table']}")
                    print(f"     {rec['description']}")
                    print(f"     Columns: {', '.join(rec['columns'][:5])}...")
                    print()
            
            if medium_priority:
                print("MEDIUM PRIORITY:")
                for rec in medium_priority:
                    print(f"   - {rec['table']}")
                    print(f"     {rec['description']}")
                    print()
            
            if low_priority:
                print("LOW PRIORITY:")
                for rec in low_priority:
                    print(f"   - {rec['table']}")
                    print(f"     {rec['description']}")
                    print()
        
        print("=" * 80)


def main():
    """Main entry point"""
    tester = DatabaseTableRequirementsTester()
    tester.run_analysis()


if __name__ == '__main__':
    main()
