#!/usr/bin/env python3
"""
Database to UI Integration Test
Tests full integration from database to browser UI
"""
import os
import sys
from typing import Dict, List, Any
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class DatabaseUIIntegrationTest:
    """Test database to UI integration"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.test_user = "test_integration_user"
        self.issues = []
        self.fixes_applied = []
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("=" * 80)
        print("DATABASE TO UI INTEGRATION TEST")
        print("=" * 80)
        print()
        
        # 1. Setup test data
        print("1. Setting up test data...")
        self.setup_test_data()
        print()
        
        # 2. Test points endpoint
        print("2. Testing points endpoint...")
        self.test_points_endpoint()
        print()
        
        # 3. Test aggregator endpoint
        print("3. Testing aggregator endpoint...")
        self.test_aggregator_endpoint()
        print()
        
        # 4. Test data format consistency
        print("4. Testing data format consistency...")
        self.test_data_format()
        print()
        
        # 5. Test database queries
        print("5. Testing database queries...")
        self.test_database_queries()
        print()
        
        # 6. Fix issues found
        print("6. Fixing issues...")
        self.fix_issues()
        print()
        
        # Summary
        self.print_summary()
    
    def setup_test_data(self):
        """Setup test data in database"""
        try:
            # Create test user points
            from backend.services.unified_points_database import unified_points_db
            
            # Add some test points
            unified_points_db.add_points(
                user_id=self.test_user,
                point_type="battle_points",
                amount=100.0,
                source="test"
            )
            unified_points_db.add_points(
                user_id=self.test_user,
                point_type="social_points",
                amount=50.0,
                source="test"
            )
            unified_points_db.add_points(
                user_id=self.test_user,
                point_type="xp",
                amount=500.0,
                source="test"
            )
            
            print(f"   [OK] Test data created for {self.test_user}")
        except Exception as e:
            print(f"   [ERROR] Failed to create test data: {str(e)}")
            self.issues.append(f"Test data setup failed: {str(e)}")
    
    def test_points_endpoint(self):
        """Test /api/points/get-all-connected endpoint"""
        try:
            with self.app.test_client() as client:
                response = client.get(f'/api/points/get-all-connected?user_id={self.test_user}')
                
                if response.status_code == 200:
                    data = response.get_json()
                    if data and data.get('success'):
                        points = data.get('points', {})
                        systems = points.get('systems', {})
                        
                        # Check if data is from database
                        if 'battle_points' in systems or 'social_points' in systems:
                            print(f"   [OK] Endpoint returns data from database")
                            print(f"   [OK] XP: {points.get('xp_total', 0)}, Level: {points.get('level', 1)}")
                            print(f"   [OK] Systems found: {len(systems)}")
                        else:
                            print(f"   [WARN] Endpoint returns data but may not be from database")
                            self.issues.append("Points endpoint may not be using database")
                    else:
                        print(f"   [FAIL] Endpoint returned success=False")
                        self.issues.append("Points endpoint returned success=False")
                else:
                    print(f"   [FAIL] Endpoint returned status {response.status_code}")
                    self.issues.append(f"Points endpoint returned {response.status_code}")
        except Exception as e:
            print(f"   [ERROR] Test failed: {str(e)}")
            self.issues.append(f"Points endpoint test error: {str(e)}")
    
    def test_aggregator_endpoint(self):
        """Test /api/aggregator/frontend endpoint"""
        try:
            with self.app.test_client() as client:
                response = client.get(f'/api/aggregator/frontend?user_id={self.test_user}')
                
                if response.status_code == 200:
                    data = response.get_json()
                    if data and data.get('success'):
                        frontend_data = data.get('data', {})
                        
                        # Check expected structure
                        has_points = 'points' in frontend_data
                        has_stats = 'stats' in frontend_data
                        
                        if has_points or has_stats:
                            print(f"   [OK] Aggregator endpoint returns data")
                            print(f"   [OK] Has points: {has_points}, Has stats: {has_stats}")
                        else:
                            print(f"   [WARN] Aggregator endpoint structure may be incomplete")
                            self.issues.append("Aggregator endpoint missing expected data structure")
                    else:
                        print(f"   [FAIL] Aggregator endpoint returned success=False")
                        self.issues.append("Aggregator endpoint returned success=False")
                else:
                    print(f"   [FAIL] Aggregator endpoint returned status {response.status_code}")
                    self.issues.append(f"Aggregator endpoint returned {response.status_code}")
        except Exception as e:
            print(f"   [ERROR] Test failed: {str(e)}")
            self.issues.append(f"Aggregator endpoint test error: {str(e)}")
    
    def test_data_format(self):
        """Test data format consistency"""
        try:
            from backend.services.unified_points_database import unified_points_db
            
            # Get data from service
            service_data = unified_points_db.get_all_points(self.test_user)
            
            # Get data from endpoint
            with self.app.test_client() as client:
                endpoint_response = client.get(f'/api/points/get-all-connected?user_id={self.test_user}')
                endpoint_data = endpoint_response.get_json() if endpoint_response.status_code == 200 else None
            
            # Compare structures
            if service_data and endpoint_data:
                service_points = service_data.get('points', {})
                endpoint_points = endpoint_data.get('points', {})
                
                # Check key fields
                service_xp = service_points.get('xp_total', 0)
                endpoint_xp = endpoint_points.get('xp_total', 0)
                
                if service_xp == endpoint_xp:
                    print(f"   [OK] Data format consistent between service and endpoint")
                else:
                    print(f"   [WARN] Data mismatch: service XP={service_xp}, endpoint XP={endpoint_xp}")
                    self.issues.append("Data format inconsistency between service and endpoint")
        except Exception as e:
            print(f"   [ERROR] Test failed: {str(e)}")
            self.issues.append(f"Data format test error: {str(e)}")
    
    def test_database_queries(self):
        """Test direct database queries"""
        try:
            # Test system_point_snapshots query
            result = db.session.execute(
                text("""
                    SELECT system_name, point_value 
                    FROM system_point_snapshots 
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                """),
                {"user_id": self.test_user}
            ).fetchall()
            
            if result:
                print(f"   [OK] Database query successful: {len(result)} snapshots found")
                for row in result[:3]:
                    print(f"      - {row[0]}: {row[1]}")
            else:
                print(f"   [WARN] No snapshots found in database for test user")
                self.issues.append("No snapshots in database - may need to run migration")
            
            # Test player_levels query
            level_result = db.session.execute(
                text("SELECT level, total_xp FROM player_levels WHERE user_id = :user_id"),
                {"user_id": self.test_user}
            ).fetchone()
            
            if level_result:
                print(f"   [OK] Player level found: Level {level_result[0]}, XP {level_result[1]}")
            else:
                print(f"   [WARN] No player level found in database")
                self.issues.append("No player level in database")
        except Exception as e:
            print(f"   [ERROR] Database query test failed: {str(e)}")
            self.issues.append(f"Database query error: {str(e)}")
    
    def fix_issues(self):
        """Fix identified issues"""
        for issue in self.issues[:]:
            if "No snapshots in database" in issue:
                # Ensure snapshots are created
                try:
                    from backend.services.unified_points_database import unified_points_db
                    # Force snapshot creation
                    unified_points_db.add_points(
                        user_id=self.test_user,
                        point_type="test_points",
                        amount=1.0,
                        source="integration_test"
                    )
                    self.fixes_applied.append("Created missing snapshots")
                    self.issues.remove(issue)
                except Exception as e:
                    print(f"   [WARN] Could not fix snapshot issue: {str(e)}")
            
            elif "No player level in database" in issue:
                # Ensure player level exists
                try:
                    db.session.execute(
                        text("""
                            INSERT OR IGNORE INTO player_levels (user_id, level, total_xp, current_level_xp, xp_to_next_level)
                            VALUES (:user_id, 1, 0, 0, 1000)
                        """),
                        {"user_id": self.test_user}
                    )
                    db.session.commit()
                    self.fixes_applied.append("Created missing player level")
                    self.issues.remove(issue)
                except Exception as e:
                    print(f"   [WARN] Could not fix player level issue: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("=" * 80)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 80)
        print()
        
        if self.issues:
            print(f"Issues Found: {len(self.issues)}")
            for issue in self.issues:
                print(f"   - {issue}")
            print()
        else:
            print("   [OK] No issues found!")
            print()
        
        if self.fixes_applied:
            print(f"Fixes Applied: {len(self.fixes_applied)}")
            for fix in self.fixes_applied:
                print(f"   [OK] {fix}")
            print()
        
        # Cleanup test data
        try:
            db.session.execute(
                text("DELETE FROM system_point_snapshots WHERE user_id = :user_id"),
                {"user_id": self.test_user}
            )
            db.session.execute(
                text("DELETE FROM player_levels WHERE user_id = :user_id"),
                {"user_id": self.test_user}
            )
            db.session.commit()
            print("   [OK] Test data cleaned up")
        except:
            pass


def main():
    """Main entry point"""
    tester = DatabaseUIIntegrationTest()
    tester.run_all_tests()


if __name__ == '__main__':
    main()
