#!/usr/bin/env python3
"""
Comprehensive Database Test Suite
Tests all database tables, queries, and operations
"""
import os
import sys
from datetime import datetime, date
from typing import Dict, List, Any
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class ComprehensiveDatabaseTest:
    """Comprehensive database testing"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.test_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    def run_all_tests(self):
        """Run all database tests"""
        print("=" * 80)
        print("COMPREHENSIVE DATABASE TEST SUITE")
        print("=" * 80)
        print()
        
        # 1. Test table existence
        print("1. Testing table existence...")
        self.test_table_existence()
        print()
        
        # 2. Test table schemas
        print("2. Testing table schemas...")
        self.test_table_schemas()
        print()
        
        # 3. Test CRUD operations
        print("3. Testing CRUD operations...")
        self.test_crud_operations()
        print()
        
        # 4. Test indexes
        print("4. Testing indexes...")
        self.test_indexes()
        print()
        
        # 5. Test data integrity
        print("5. Testing data integrity...")
        self.test_data_integrity()
        print()
        
        # 6. Test performance
        print("6. Testing query performance...")
        self.test_performance()
        print()
        
        # Summary
        self.print_summary()
    
    def test_table_existence(self):
        """Test that all required tables exist"""
        required_tables = [
            'player_levels', 'xp_history', 'daily_activities', 'rewards', 'user_rewards',
            'user_profiles', 'user_scraped_info', 'user_agent_skills', 'onboarding_progress',
            'system_point_snapshots', 'point_transactions', 'point_history', 'point_aggregates',
            'point_analytics', 'system_usage_stats',
            'agent_technologies', 'agent_technology_improvements', 'agent_technology_metrics',
            'agent_technology_usage', 'agent_technology_relationships', 'agent_technology_events',
            'agent_missions', 'agent_quests', 'agent_personality', 'agent_skill_history',
            'agent_ai_intelligence', 'agent_errors', 'agent_use_cases',
            'video_generation_jobs', 'dna_manipulation',
            'calculation_history', 'point_loss_detection', 'repair_log', 'predictions',
            'pattern_analysis', 'anomaly_detection'
        ]
        
        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        
        for table in required_tables:
            if table in existing_tables:
                self.test_results['passed'].append(f"Table {table} exists")
            else:
                self.test_results['failed'].append(f"Table {table} missing")
                print(f"   [FAIL] Missing table: {table}")
        
        print(f"   [OK] Tested {len(required_tables)} tables")
    
    def test_table_schemas(self):
        """Test table schemas"""
        inspector = inspect(db.engine)
        
        # Test key tables have required columns
        schema_tests = [
            ('player_levels', ['user_id', 'level', 'total_xp']),
            ('system_point_snapshots', ['user_id', 'system_name', 'point_value']),
            ('agent_technologies', ['tech_id', 'tech_name', 'category']),
            ('agent_missions', ['mission_id', 'mission_name', 'status']),
            ('video_generation_jobs', ['job_id', 'status', 'progress']),
        ]
        
        for table, required_columns in schema_tests:
            try:
                columns = {col['name'] for col in inspector.get_columns(table)}
                missing = [col for col in required_columns if col not in columns]
                
                if missing:
                    self.test_results['failed'].append(f"{table} missing columns: {', '.join(missing)}")
                    print(f"   [FAIL] {table} missing columns: {', '.join(missing)}")
                else:
                    self.test_results['passed'].append(f"{table} schema valid")
            except Exception as e:
                self.test_results['failed'].append(f"{table} schema check failed: {str(e)}")
    
    def test_crud_operations(self):
        """Test CRUD operations on key tables"""
        test_user = "test_user_crud_" + datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Test INSERT
        try:
            db.session.execute(
                text("INSERT OR IGNORE INTO player_levels (user_id, level, total_xp) VALUES (:user_id, 1, 0)"),
                {"user_id": test_user}
            )
            db.session.commit()
            self.test_results['passed'].append("INSERT operation works")
        except Exception as e:
            self.test_results['failed'].append(f"INSERT failed: {str(e)}")
            db.session.rollback()
        
        # Test SELECT
        try:
            result = db.session.execute(
                text("SELECT level, total_xp FROM player_levels WHERE user_id = :user_id"),
                {"user_id": test_user}
            ).fetchone()
            if result:
                self.test_results['passed'].append("SELECT operation works")
            else:
                self.test_results['failed'].append("SELECT returned no results")
        except Exception as e:
            self.test_results['failed'].append(f"SELECT failed: {str(e)}")
        
        # Test UPDATE
        try:
            db.session.execute(
                text("UPDATE player_levels SET total_xp = 100 WHERE user_id = :user_id"),
                {"user_id": test_user}
            )
            db.session.commit()
            self.test_results['passed'].append("UPDATE operation works")
        except Exception as e:
            self.test_results['failed'].append(f"UPDATE failed: {str(e)}")
            db.session.rollback()
        
        # Cleanup
        try:
            db.session.execute(
                text("DELETE FROM player_levels WHERE user_id = :user_id"),
                {"user_id": test_user}
            )
            db.session.commit()
        except Exception:
            pass
        
        print(f"   [OK] Tested CRUD operations")
    
    def test_indexes(self):
        """Test that indexes exist"""
        inspector = inspect(db.engine)
        
        # Check key indexes
        index_checks = [
            ('player_levels', 'idx_player_levels_user_id'),
            ('system_point_snapshots', 'idx_snapshots_user_id'),
            ('point_transactions', 'idx_transactions_user_id'),
            ('agent_technologies', 'idx_tech_category'),
        ]
        
        for table, index_name in index_checks:
            try:
                indexes = inspector.get_indexes(table)
                index_names = [idx['name'] for idx in indexes]
                
                if index_name in index_names:
                    self.test_results['passed'].append(f"Index {index_name} exists")
                else:
                    self.test_results['warnings'].append(f"Index {index_name} missing")
            except Exception:
                pass
        
        print(f"   [OK] Tested indexes")
    
    def test_data_integrity(self):
        """Test data integrity"""
        # Test foreign key relationships (if applicable)
        # Test unique constraints
        # Test data types
        
        try:
            # Test that user_id is unique in player_levels
            result = db.session.execute(
                text("""
                    SELECT user_id, COUNT(*) as count
                    FROM player_levels
                    GROUP BY user_id
                    HAVING COUNT(*) > 1
                """)
            ).fetchall()
            
            if result:
                self.test_results['warnings'].append(f"Found {len(result)} duplicate user_ids in player_levels")
            else:
                self.test_results['passed'].append("player_levels user_id uniqueness valid")
        except Exception as e:
            self.test_results['warnings'].append(f"Data integrity check: {str(e)}")
        
        print(f"   [OK] Tested data integrity")
    
    def test_performance(self):
        """Test query performance"""
        import time
        
        performance_tests = [
            ("Simple SELECT", "SELECT COUNT(*) FROM player_levels"),
            ("JOIN query", """
                SELECT p.user_id, COUNT(s.id) as snapshots
                FROM player_levels p
                LEFT JOIN system_point_snapshots s ON p.user_id = s.user_id
                GROUP BY p.user_id
                LIMIT 10
            """),
            ("Aggregate query", """
                SELECT system_name, SUM(point_value) as total
                FROM system_point_snapshots
                GROUP BY system_name
                LIMIT 10
            """),
        ]
        
        for test_name, query in performance_tests:
            try:
                start = time.time()
                db.session.execute(text(query))
                duration = time.time() - start
                
                if duration < 1.0:
                    self.test_results['passed'].append(f"{test_name}: {duration*1000:.2f}ms")
                else:
                    self.test_results['warnings'].append(f"{test_name}: {duration*1000:.2f}ms (slow)")
            except Exception as e:
                self.test_results['failed'].append(f"{test_name} failed: {str(e)}")
        
        print(f"   [OK] Tested query performance")
    
    def print_summary(self):
        """Print test summary"""
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print()
        
        total = len(self.test_results['passed']) + len(self.test_results['failed']) + len(self.test_results['warnings'])
        passed = len(self.test_results['passed'])
        failed = len(self.test_results['failed'])
        warnings = len(self.test_results['warnings'])
        
        print(f"Total Tests: {total}")
        print(f"[OK] Passed: {passed}")
        print(f"[FAIL] Failed: {failed}")
        print(f"[WARN] Warnings: {warnings}")
        print()
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        if failed > 0:
            print("Failed Tests:")
            for test in self.test_results['failed'][:10]:
                print(f"   - {test}")
            if len(self.test_results['failed']) > 10:
                print(f"   ... and {len(self.test_results['failed']) - 10} more")
            print()
        
        if warnings > 0:
            print("Warnings:")
            for warning in self.test_results['warnings'][:5]:
                print(f"   - {warning}")
            print()


def main():
    """Main entry point"""
    tester = ComprehensiveDatabaseTest()
    tester.run_all_tests()


if __name__ == '__main__':
    main()
