#!/usr/bin/env python3
"""
Performance Monitoring and Optimization
Monitors database query performance and suggests optimizations
"""
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class PerformanceMonitor:
    """Monitor and optimize database performance"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.slow_queries = []
        self.optimization_suggestions = []
    
    def run_analysis(self):
        """Run performance analysis"""
        print("=" * 80)
        print("DATABASE PERFORMANCE MONITORING")
        print("=" * 80)
        print()
        
        # 1. Check table sizes
        print("1. Analyzing table sizes...")
        self.analyze_table_sizes()
        print()
        
        # 2. Check indexes
        print("2. Analyzing indexes...")
        self.analyze_indexes()
        print()
        
        # 3. Test query performance
        print("3. Testing query performance...")
        self.test_query_performance()
        print()
        
        # 4. Generate recommendations
        print("4. Generating optimization recommendations...")
        self.generate_recommendations()
        print()
        
        # Summary
        print("=" * 80)
        print("PERFORMANCE ANALYSIS SUMMARY")
        print("=" * 80)
        print()
        if self.slow_queries:
            print(f"Slow Queries Found: {len(self.slow_queries)}")
            for query in self.slow_queries[:5]:
                print(f"   - {query}")
        else:
            print("   [OK] No slow queries detected")
        print()
        
        if self.optimization_suggestions:
            print("Optimization Suggestions:")
            for suggestion in self.optimization_suggestions:
                print(f"   - {suggestion}")
        print()
    
    def analyze_table_sizes(self):
        """Analyze table sizes"""
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            table_sizes = []
            for table in tables:
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    table_sizes.append((table, count))
                except Exception:
                    pass
            
            table_sizes.sort(key=lambda x: x[1], reverse=True)
            
            print(f"   Found {len(table_sizes)} tables:")
            for table, count in table_sizes[:10]:
                size_category = "LARGE" if count > 10000 else "MEDIUM" if count > 1000 else "SMALL"
                print(f"      - {table}: {count:,} records ({size_category})")
                
                if count > 100000:
                    self.optimization_suggestions.append(f"Consider partitioning {table} (has {count:,} records)")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
    
    def analyze_indexes(self):
        """Analyze indexes"""
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            total_indexes = 0
            for table in tables:
                try:
                    indexes = inspector.get_indexes(table)
                    total_indexes += len(indexes)
                except Exception:
                    pass
            
            print(f"   Total indexes: {total_indexes}")
            print("   [OK] Indexes analyzed")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
    
    def test_query_performance(self):
        """Test query performance"""
        test_queries = [
            ("Get user points", "SELECT * FROM system_point_snapshots WHERE user_id = 'test_user' ORDER BY id DESC LIMIT 10"),
            ("Get XP history", "SELECT * FROM xp_history WHERE user_id = 'test_user' ORDER BY created_at DESC LIMIT 10"),
            ("Get technology metrics", "SELECT * FROM agent_technology_metrics WHERE tech_id = 'agent_quantum_processor' ORDER BY metric_date DESC LIMIT 10"),
            ("Get point transactions", "SELECT * FROM point_transactions WHERE user_id = 'test_user' ORDER BY created_at DESC LIMIT 10"),
        ]
        
        slow_threshold = 0.1  # 100ms
        
        for query_name, query_sql in test_queries:
            try:
                start_time = time.time()
                result = db.session.execute(text(query_sql))
                result.fetchall()
                duration = time.time() - start_time
                
                status = "[OK]" if duration < slow_threshold else "[SLOW]"
                print(f"   {status} {query_name}: {duration*1000:.2f}ms")
                
                if duration > slow_threshold:
                    self.slow_queries.append(f"{query_name}: {duration*1000:.2f}ms")
            except Exception as e:
                print(f"   [ERROR] {query_name}: {str(e)}")
    
    def generate_recommendations(self):
        """Generate optimization recommendations"""
        # Check for missing indexes on frequently queried columns
        recommendations = []
        
        # Check if common query patterns have indexes
        common_patterns = [
            ("point_transactions", "user_id", "created_at"),
            ("system_point_snapshots", "user_id", "system_name"),
            ("agent_technology_events", "tech_id", "created_at"),
        ]
        
        for table, col1, col2 in common_patterns:
            try:
                inspector = inspect(db.engine)
                indexes = inspector.get_indexes(table)
                index_columns = {idx['name']: idx['column_names'] for idx in indexes}
                
                # Check if composite index exists
                has_composite = any(col1 in cols and col2 in cols for cols in index_columns.values())
                if not has_composite:
                    recommendations.append(f"Consider adding composite index on {table}({col1}, {col2})")
            except Exception:
                pass
        
        self.optimization_suggestions.extend(recommendations)
        
        if recommendations:
            print(f"   Generated {len(recommendations)} recommendations")
        else:
            print("   [OK] No optimization recommendations")


def main():
    """Main entry point"""
    monitor = PerformanceMonitor()
    monitor.run_analysis()


if __name__ == '__main__':
    main()
