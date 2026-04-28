#!/usr/bin/env python3
"""
Database Diagnostic and Fix Script
Comprehensive database health check, schema standardization, and connection testing
"""
import os
import sys
from datetime import datetime
from sqlalchemy import text, inspect
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class DatabaseDiagnostic:
    """Comprehensive database diagnostic and fix tool"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.issues = []
        self.fixes_applied = []
        
    def run_full_diagnostic(self):
        """Run complete diagnostic"""
        print("=" * 80)
        print("DATABASE DIAGNOSTIC AND FIX TOOL")
        print("=" * 80)
        print()
        
        # 1. Test basic connection
        print("1. Testing Database Connection...")
        connection_ok = self.test_connection()
        print(f"   {'[OK] Connection OK' if connection_ok else '[FAIL] Connection Failed'}")
        print()
        
        if not connection_ok:
            print("[FAIL] Cannot proceed - database connection failed")
            return False
        
        # 2. List all tables
        print("2. Listing All Tables...")
        tables = self.list_all_tables()
        print(f"   Found {len(tables)} tables")
        for table in tables:
            print(f"   - {table}")
        print()
        
        # 3. Check required tables
        print("3. Checking Required Tables...")
        required_tables = [
            'player_levels', 'system_point_snapshots', 'user_profiles',
            'xp_history', 'daily_activities', 'rewards', 'user_rewards',
            'onboarding_progress', 'user_agent_skills', 'calculation_history',
            'point_loss_detection', 'repair_log', 'predictions'
        ]
        missing_tables = self.check_required_tables(required_tables)
        print()
        
        # 4. Check player_levels schema
        print("4. Checking player_levels Schema...")
        schema_issues = self.check_player_levels_schema()
        print()
        
        # 5. Standardize player_levels schema
        if schema_issues:
            print("5. Fixing player_levels Schema...")
            self.fix_player_levels_schema()
            print()
        
        # 6. Test unified_points_database connection
        print("6. Testing Unified Points Database...")
        unified_points_ok = self.test_unified_points()
        print(f"   {'[OK] Unified Points OK' if unified_points_ok else '[FAIL] Unified Points Failed'}")
        print()
        
        # 7. Test blueprint registration
        print("7. Testing Blueprint Registration...")
        blueprint_status = self.test_blueprint_registration()
        print()
        
        # 8. Test key endpoints
        print("8. Testing Key Endpoints...")
        endpoint_status = self.test_key_endpoints()
        print()
        
        # 9. Generate report
        print("9. Generating Report...")
        self.generate_report()
        print()
        
        return True
    
    def test_connection(self) -> bool:
        """Test basic database connection"""
        try:
            result = db.session.execute(text("SELECT 1"))
            result.fetchone()
            return True
        except Exception as e:
            self.issues.append(f"Connection failed: {str(e)}")
            return False
    
    def list_all_tables(self) -> List[str]:
        """List all tables in database"""
        try:
            inspector = inspect(db.engine)
            return inspector.get_table_names()
        except Exception as e:
            self.issues.append(f"Failed to list tables: {str(e)}")
            return []
    
    def check_required_tables(self, required: List[str]) -> List[str]:
        """Check which required tables are missing"""
        existing = self.list_all_tables()
        missing = [t for t in required if t not in existing]
        
        for table in required:
            status = "[OK]" if table in existing else "[MISS]"
            print(f"   {status} {table}")
        
        if missing:
            self.issues.append(f"Missing tables: {', '.join(missing)}")
        
        return missing
    
    def check_player_levels_schema(self) -> Dict[str, Any]:
        """Check player_levels table schema for inconsistencies"""
        issues = {}
        
        try:
            # Get table info
            inspector = inspect(db.engine)
            columns = {col['name']: col for col in inspector.get_columns('player_levels')}
            
            # Check for expected columns
            expected_columns = {
                'user_id': True,  # Required
                'level': False,  # Optional (some schemas use current_level)
                'current_level': False,
                'total_xp': True,  # Required
                'current_xp': False,
                'current_level_xp': False,
                'xp_to_next_level': False
            }
            
            print(f"   Found {len(columns)} columns in player_levels")
            
            # Check for schema variations
            has_level = 'level' in columns
            has_current_level = 'current_level' in columns
            has_total_xp = 'total_xp' in columns
            
            if not has_total_xp:
                issues['missing_total_xp'] = True
                print("   [MISS] Missing 'total_xp' column")
            
            if not has_level and not has_current_level:
                issues['missing_level_column'] = True
                print("   [WARN] Missing both 'level' and 'current_level' columns")
            elif has_level and has_current_level:
                issues['both_level_columns'] = True
                print("   [WARN] Has both 'level' and 'current_level' (inconsistent)")
            else:
                print(f"   [OK] Has {'level' if has_level else 'current_level'} column")
            
            # List all columns
            print("   Columns found:")
            for col_name, col_info in columns.items():
                col_type = str(col_info['type'])
                nullable = "NULL" if col_info['nullable'] else "NOT NULL"
                print(f"     - {col_name}: {col_type} ({nullable})")
            
            return issues
            
        except Exception as e:
            if "no such table" in str(e).lower():
                issues['table_missing'] = True
                print(f"   [MISS] Table 'player_levels' does not exist")
                self.issues.append("player_levels table missing")
            else:
                issues['check_failed'] = str(e)
                print(f"   [ERROR] Failed to check schema: {str(e)}")
                self.issues.append(f"Schema check failed: {str(e)}")
            
            return issues
    
    def fix_player_levels_schema(self):
        """Standardize player_levels table schema"""
        try:
            inspector = inspect(db.engine)
            
            # Check if table exists
            if 'player_levels' not in inspector.get_table_names():
                print("   Creating player_levels table...")
                self.create_standard_player_levels_table()
                self.fixes_applied.append("Created player_levels table")
                return
            
            columns = {col['name'] for col in inspector.get_columns('player_levels')}
            
            # Add missing columns
            if 'total_xp' not in columns:
                print("   Adding 'total_xp' column...")
                db.session.execute(text("""
                    ALTER TABLE player_levels 
                    ADD COLUMN total_xp INTEGER DEFAULT 0
                """))
                db.session.commit()
                self.fixes_applied.append("Added total_xp column")
            
            # Standardize level column
            has_level = 'level' in columns
            has_current_level = 'current_level' in columns
            
            if not has_level and not has_current_level:
                print("   Adding 'level' column...")
                db.session.execute(text("""
                    ALTER TABLE player_levels 
                    ADD COLUMN level INTEGER DEFAULT 1
                """))
                db.session.commit()
                self.fixes_applied.append("Added level column")
            elif has_current_level and not has_level:
                # Rename current_level to level for consistency
                print("   Standardizing: using 'level' instead of 'current_level'...")
                # SQLite doesn't support RENAME COLUMN, so we'll add level and copy data
                db.session.execute(text("""
                    ALTER TABLE player_levels 
                    ADD COLUMN level INTEGER DEFAULT 1
                """))
                db.session.execute(text("""
                    UPDATE player_levels 
                    SET level = COALESCE(current_level, 1)
                """))
                db.session.commit()
                self.fixes_applied.append("Standardized level column")
            
            # Ensure user_id is primary key
            try:
                # Check if user_id is primary key
                pk_constraint = inspector.get_pk_constraint('player_levels')
                if 'user_id' not in pk_constraint.get('constrained_columns', []):
                    print("   ⚠️  user_id is not primary key (cannot fix automatically)")
            except Exception:
                pass
            
            print("   [OK] Schema standardized")
            
        except Exception as e:
            print(f"   [ERROR] Failed to fix schema: {str(e)}")
            self.issues.append(f"Schema fix failed: {str(e)}")
            db.session.rollback()
    
    def create_standard_player_levels_table(self):
        """Create player_levels table with standard schema"""
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS player_levels (
                user_id VARCHAR(100) PRIMARY KEY,
                level INTEGER DEFAULT 1,
                total_xp INTEGER DEFAULT 0,
                current_level_xp INTEGER DEFAULT 0,
                xp_to_next_level INTEGER DEFAULT 1000,
                level_progress DECIMAL(5,2) DEFAULT 0.0,
                title VARCHAR(50) DEFAULT 'Novice Hunter',
                prestige_level INTEGER DEFAULT 0,
                stat_creativity INTEGER DEFAULT 0,
                stat_efficiency INTEGER DEFAULT 0,
                stat_quality INTEGER DEFAULT 0,
                stat_social INTEGER DEFAULT 0,
                stat_knowledge INTEGER DEFAULT 0,
                available_stat_points INTEGER DEFAULT 0,
                unlocked_themes TEXT,
                unlocked_templates TEXT,
                xp_bonus_percent INTEGER DEFAULT 0,
                xp_bonus_remaining INTEGER DEFAULT 0,
                prestige_xp_bonus INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.commit()
    
    def test_unified_points(self) -> bool:
        """Test unified_points_database connection"""
        try:
            from backend.services.unified_points_database import unified_points_db
            
            # Test get_all_points
            result = unified_points_db.get_all_points("test_user")
            if result.get('success'):
                print("   [OK] Unified points database working")
                return True
            else:
                print("   [WARN] Unified points returned error")
                return False
        except Exception as e:
            print(f"   [ERROR] Unified points failed: {str(e)}")
            self.issues.append(f"Unified points test failed: {str(e)}")
            return False
    
    def test_blueprint_registration(self) -> Dict[str, Any]:
        """Test that all blueprints are registered"""
        try:
            from backend.register_blueprints import register_all_blueprints
            
            # Count registered routes
            registered_routes = []
            for rule in self.app.url_map.iter_rules():
                if rule.endpoint and not rule.endpoint.startswith('static'):
                    registered_routes.append(rule.rule)
            
            print(f"   Found {len(registered_routes)} registered routes")
            
            # Check for key blueprints
            key_endpoints = [
                '/api/health',
                '/api/points/comprehensive',
                '/api/stats/summary',
                '/api/game/stats'
            ]
            
            endpoint_map = {rule.rule: rule.endpoint for rule in self.app.url_map.iter_rules()}
            
            for endpoint in key_endpoints:
                found = any(endpoint in rule for rule in endpoint_map.keys())
                status = "[OK]" if found else "[MISS]"
                print(f"   {status} {endpoint}")
                if not found:
                    self.issues.append(f"Missing endpoint: {endpoint}")
            
            return {
                'total_routes': len(registered_routes),
                'key_endpoints_found': sum(1 for ep in key_endpoints if any(ep in r for r in endpoint_map.keys()))
            }
            
        except Exception as e:
            print(f"   [ERROR] Blueprint test failed: {str(e)}")
            self.issues.append(f"Blueprint test failed: {str(e)}")
            return {}
    
    def test_key_endpoints(self) -> Dict[str, bool]:
        """Test key endpoints using test client"""
        results = {}
        
        with self.app.test_client() as client:
            endpoints_to_test = [
                ('/api/health', 'GET'),
                ('/api/health/database', 'GET'),
                ('/api/points/comprehensive?user_id=test_user', 'GET'),
            ]
            
            for endpoint, method in endpoints_to_test:
                try:
                    if method == 'GET':
                        response = client.get(endpoint)
                    else:
                        response = client.post(endpoint)
                    
                    status_ok = response.status_code in [200, 201]
                    status = "[OK]" if status_ok else "[FAIL]"
                    print(f"   {status} {method} {endpoint} ({response.status_code})")
                    results[endpoint] = status_ok
                    
                    if not status_ok:
                        self.issues.append(f"Endpoint {endpoint} returned {response.status_code}")
                except Exception as e:
                    print(f"   [ERROR] {method} {endpoint} - Error: {str(e)}")
                    results[endpoint] = False
                    self.issues.append(f"Endpoint {endpoint} failed: {str(e)}")
        
        return results
    
    def generate_report(self):
        """Generate diagnostic report"""
        print("=" * 80)
        print("DIAGNOSTIC REPORT")
        print("=" * 80)
        print()
        
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()
        
        if self.fixes_applied:
            print("[OK] Fixes Applied:")
            for fix in self.fixes_applied:
                print(f"   - {fix}")
            print()
        
        if self.issues:
            print("[WARN] Issues Found:")
            for issue in self.issues:
                print(f"   - {issue}")
            print()
        else:
            print("[OK] No issues found!")
            print()
        
        # Database info
        try:
            tables = self.list_all_tables()
            print(f"Database Statistics:")
            print(f"   - Total tables: {len(tables)}")
            
            # Count records in key tables
            key_tables = ['player_levels', 'user_profiles', 'system_point_snapshots']
            for table in key_tables:
                if table in tables:
                    try:
                        result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        print(f"   - {table}: {count} records")
                    except Exception:
                        pass
        except Exception as e:
            print(f"   [WARN] Could not get statistics: {str(e)}")
        
        print()
        print("=" * 80)


def main():
    """Main entry point"""
    diagnostic = DatabaseDiagnostic()
    success = diagnostic.run_full_diagnostic()
    
    if success:
        print("[OK] Diagnostic complete!")
        if diagnostic.issues:
            print(f"[WARN] Found {len(diagnostic.issues)} issues")
        if diagnostic.fixes_applied:
            print(f"[OK] Applied {len(diagnostic.fixes_applied)} fixes")
    else:
        print("[FAIL] Diagnostic failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
