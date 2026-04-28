#!/usr/bin/env python3
"""
Agent Technologies Database Migration
Creates database tables for all 50 agent technologies
"""
import os
import sys
from datetime import datetime
from sqlalchemy import text, inspect

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


# All 50 Agent Technologies
AGENT_TECHS = [
    # Core Infrastructure (10)
    {'id': 'agent_quantum_processor', 'name': 'Quantum Processor', 'category': 'core', 'icon': '⚛️', 'description': 'Advanced processing capabilities'},
    {'id': 'agent_neural_network', 'name': 'Neural Network', 'category': 'core', 'icon': '🧠', 'description': 'AI/ML processing'},
    {'id': 'agent_blockchain_ledger', 'name': 'Blockchain Ledger', 'category': 'core', 'icon': '⛓️', 'description': 'Distributed ledger technology'},
    {'id': 'agent_cloud_sync', 'name': 'Cloud Sync', 'category': 'core', 'icon': '☁️', 'description': 'Cloud synchronization'},
    {'id': 'agent_distributed_cache', 'name': 'Distributed Cache', 'category': 'core', 'icon': '💾', 'description': 'Distributed caching system'},
    {'id': 'agent_microservices', 'name': 'Microservices', 'category': 'core', 'icon': '🔧', 'description': 'Microservices architecture'},
    {'id': 'agent_api_gateway', 'name': 'API Gateway', 'category': 'core', 'icon': '🚪', 'description': 'API gateway management'},
    {'id': 'agent_load_balancer', 'name': 'Load Balancer', 'category': 'core', 'icon': '⚖️', 'description': 'Load balancing'},
    {'id': 'agent_service_mesh', 'name': 'Service Mesh', 'category': 'core', 'icon': '🕸️', 'description': 'Service mesh networking'},
    {'id': 'agent_container_orchestrator', 'name': 'Container Orchestrator', 'category': 'core', 'icon': '📦', 'description': 'Container orchestration'},
    
    # Tools & Debuggers (10)
    {'id': 'agent_code_analyzer', 'name': 'Code Analyzer', 'category': 'tools', 'icon': '🔍', 'description': 'Code analysis tools'},
    {'id': 'agent_performance_profiler', 'name': 'Performance Profiler', 'category': 'tools', 'icon': '📊', 'description': 'Performance profiling'},
    {'id': 'agent_memory_debugger', 'name': 'Memory Debugger', 'category': 'tools', 'icon': '🧪', 'description': 'Memory debugging'},
    {'id': 'agent_security_scanner', 'name': 'Security Scanner', 'category': 'tools', 'icon': '🔒', 'description': 'Security scanning'},
    {'id': 'agent_dependency_checker', 'name': 'Dependency Checker', 'category': 'tools', 'icon': '📋', 'description': 'Dependency management'},
    {'id': 'agent_test_generator', 'name': 'Test Generator', 'category': 'tools', 'icon': '🧪', 'description': 'Test generation'},
    {'id': 'agent_log_analyzer', 'name': 'Log Analyzer', 'category': 'tools', 'icon': '📝', 'description': 'Log analysis'},
    {'id': 'agent_error_tracker', 'name': 'Error Tracker', 'category': 'tools', 'icon': '⚠️', 'description': 'Error tracking'},
    {'id': 'agent_code_formatter', 'name': 'Code Formatter', 'category': 'tools', 'icon': '✨', 'description': 'Code formatting'},
    {'id': 'agent_documentation_generator', 'name': 'Documentation Generator', 'category': 'tools', 'icon': '📚', 'description': 'Documentation generation'},
    
    # Trackers & Scanners (10)
    {'id': 'agent_activity_tracker', 'name': 'Activity Tracker', 'category': 'tracker', 'icon': '📈', 'description': 'Activity tracking'},
    {'id': 'agent_behavior_tracker', 'name': 'Behavior Tracker', 'category': 'tracker', 'icon': '👁️', 'description': 'Behavior tracking'},
    {'id': 'agent_metric_tracker', 'name': 'Metric Tracker', 'category': 'tracker', 'icon': '📉', 'description': 'Metric tracking'},
    {'id': 'agent_event_tracker', 'name': 'Event Tracker', 'category': 'tracker', 'icon': '🎯', 'description': 'Event tracking'},
    {'id': 'agent_network_scanner', 'name': 'Network Scanner', 'category': 'scanner', 'icon': '🌐', 'description': 'Network scanning'},
    {'id': 'agent_vulnerability_scanner', 'name': 'Vulnerability Scanner', 'category': 'scanner', 'icon': '🛡️', 'description': 'Vulnerability scanning'},
    {'id': 'agent_file_scanner', 'name': 'File Scanner', 'category': 'scanner', 'icon': '📁', 'description': 'File scanning'},
    {'id': 'agent_database_scanner', 'name': 'Database Scanner', 'category': 'scanner', 'icon': '🗄️', 'description': 'Database scanning'},
    {'id': 'agent_endpoint_scanner', 'name': 'Endpoint Scanner', 'category': 'scanner', 'icon': '🔗', 'description': 'Endpoint scanning'},
    {'id': 'agent_config_scanner', 'name': 'Config Scanner', 'category': 'scanner', 'icon': '⚙️', 'description': 'Configuration scanning'},
    
    # Monitors & GPS (10)
    {'id': 'agent_health_monitor', 'name': 'Health Monitor', 'category': 'monitor', 'icon': '💚', 'description': 'Health monitoring'},
    {'id': 'agent_resource_monitor', 'name': 'Resource Monitor', 'category': 'monitor', 'icon': '📊', 'description': 'Resource monitoring'},
    {'id': 'agent_uptime_monitor', 'name': 'Uptime Monitor', 'category': 'monitor', 'icon': '⏱️', 'description': 'Uptime monitoring'},
    {'id': 'agent_alert_monitor', 'name': 'Alert Monitor', 'category': 'monitor', 'icon': '🚨', 'description': 'Alert monitoring'},
    {'id': 'agent_metric_monitor', 'name': 'Metric Monitor', 'category': 'monitor', 'icon': '📈', 'description': 'Metric monitoring'},
    {'id': 'agent_gps_coordinator', 'name': 'GPS Coordinator', 'category': 'gps', 'icon': '📍', 'description': 'GPS coordination'},
    {'id': 'agent_location_tracker', 'name': 'Location Tracker', 'category': 'gps', 'icon': '🗺️', 'description': 'Location tracking'},
    {'id': 'agent_geofence_manager', 'name': 'Geofence Manager', 'category': 'gps', 'icon': '🗺️', 'description': 'Geofence management'},
    {'id': 'agent_route_optimizer', 'name': 'Route Optimizer', 'category': 'gps', 'icon': '🛣️', 'description': 'Route optimization'},
    {'id': 'agent_navigation_system', 'name': 'Navigation System', 'category': 'gps', 'icon': '🧭', 'description': 'Navigation system'},
    
    # Advanced Features (10)
    {'id': 'agent_ml_predictor', 'name': 'ML Predictor', 'category': 'advanced', 'icon': '🤖', 'description': 'Machine learning prediction'},
    {'id': 'agent_auto_scaler', 'name': 'Auto Scaler', 'category': 'advanced', 'icon': '📏', 'description': 'Auto-scaling'},
    {'id': 'agent_self_healer', 'name': 'Self Healer', 'category': 'advanced', 'icon': '💊', 'description': 'Self-healing capabilities'},
    {'id': 'agent_adaptive_learner', 'name': 'Adaptive Learner', 'category': 'advanced', 'icon': '🎓', 'description': 'Adaptive learning'},
    {'id': 'agent_pattern_matcher', 'name': 'Pattern Matcher', 'category': 'advanced', 'icon': '🔀', 'description': 'Pattern matching'},
    {'id': 'agent_anomaly_detector', 'name': 'Anomaly Detector', 'category': 'advanced', 'icon': '🔍', 'description': 'Anomaly detection'},
    {'id': 'agent_optimization_engine', 'name': 'Optimization Engine', 'category': 'advanced', 'icon': '⚡', 'description': 'Optimization engine'},
    {'id': 'agent_decision_maker', 'name': 'Decision Maker', 'category': 'advanced', 'icon': '🎯', 'description': 'Decision making'},
    {'id': 'agent_workflow_orchestrator', 'name': 'Workflow Orchestrator', 'category': 'advanced', 'icon': '🔄', 'description': 'Workflow orchestration'},
    {'id': 'agent_event_driven_processor', 'name': 'Event-Driven Processor', 'category': 'advanced', 'icon': '⚡', 'description': 'Event-driven processing'},
    {'id': 'agent_electric_magnet', 'name': 'Electric Magnet', 'category': 'advanced', 'icon': '🧲', 'description': 'Electric Magnet tech with verification & DNA test specials'},
    {'id': 'agent_synchronization', 'name': 'Synchronization', 'category': 'core', 'icon': '🔄', 'description': 'Platform-wide sync device, domain sync, status API. Rulebook V16.'},
]

# 12 Improvement Functions per tech
IMPROVEMENT_FUNCTIONS = [
    'optimize_performance',
    'enhance_security',
    'improve_reliability',
    'scale_capacity',
    'reduce_latency',
    'increase_throughput',
    'add_monitoring',
    'enable_auto_recovery',
    'improve_caching',
    'enhance_logging',
    'add_analytics',
    'upgrade_algorithm',
]

# Extra special improvement functions for Electric Magnet (and other techs that support them)
SPECIAL_IMPROVEMENT_FUNCTIONS = ['run_verification', 'run_dna_test']


class AgentTechnologiesMigration:
    """Database migration for all 50 agent technologies"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.migrations_applied = []
    
    def run_migration(self):
        """Run all migrations for agent technologies"""
        print("=" * 80)
        print("AGENT TECHNOLOGIES DATABASE MIGRATION")
        print("=" * 80)
        print()
        
        # 1. Create main technologies table
        print("1. Creating agent_technologies table...")
        self.create_technologies_table()
        print()
        
        # 2. Create improvements table
        print("2. Creating agent_technology_improvements table...")
        self.create_improvements_table()
        print()
        
        # 3. Create metrics table
        print("3. Creating agent_technology_metrics table...")
        self.create_metrics_table()
        print()
        
        # 4. Create usage stats table
        print("4. Creating agent_technology_usage table...")
        self.create_usage_table()
        print()
        
        # 5. Create relationships table
        print("5. Creating agent_technology_relationships table...")
        self.create_relationships_table()
        print()
        
        # 6. Create events table
        print("6. Creating agent_technology_events table...")
        self.create_events_table()
        print()
        
        # 7. Insert default technologies
        print("7. Inserting default technologies...")
        self.insert_default_technologies()
        print()
        
        # 8. Create indexes
        print("8. Creating indexes...")
        self.create_indexes()
        print()
        
        # Summary
        print("=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print()
        print(f"Applied {len(self.migrations_applied)} migrations:")
        for migration in self.migrations_applied:
            print(f"   [OK] {migration}")
        print()
        print("Migration complete!")
        print()
    
    def create_technologies_table(self):
        """Create main technologies table"""
        try:
            inspector = inspect(db.engine)
            if 'agent_technologies' not in inspector.get_table_names():
                print("   Creating agent_technologies table...")
                db.session.execute(text("""
                    CREATE TABLE agent_technologies (
                        tech_id VARCHAR(100) PRIMARY KEY,
                        tech_name VARCHAR(200) NOT NULL,
                        category VARCHAR(50) NOT NULL,
                        icon VARCHAR(10),
                        description TEXT,
                        version VARCHAR(20) DEFAULT '1.0.0',
                        status VARCHAR(20) DEFAULT 'active',
                        enabled BOOLEAN DEFAULT 1,
                        priority INTEGER DEFAULT 0,
                        performance_score DECIMAL(5,2) DEFAULT 0,
                        security_score DECIMAL(5,2) DEFAULT 0,
                        reliability_score DECIMAL(5,2) DEFAULT 0,
                        total_operations INTEGER DEFAULT 0,
                        success_rate DECIMAL(5,2) DEFAULT 0,
                        last_used_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_technologies table")
                print("   [OK] Created agent_technologies table")
            else:
                print("   [OK] agent_technologies table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_improvements_table(self):
        """Create improvements table (12 per tech = 600 total)"""
        try:
            inspector = inspect(db.engine)
            if 'agent_technology_improvements' not in inspector.get_table_names():
                print("   Creating agent_technology_improvements table...")
                db.session.execute(text("""
                    CREATE TABLE agent_technology_improvements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tech_id VARCHAR(100) NOT NULL,
                        improvement_function VARCHAR(100) NOT NULL,
                        improvement_name VARCHAR(200),
                        status VARCHAR(20) DEFAULT 'available',
                        level INTEGER DEFAULT 0,
                        max_level INTEGER DEFAULT 10,
                        current_effectiveness DECIMAL(5,2) DEFAULT 0,
                        cost_points INTEGER DEFAULT 0,
                        execution_count INTEGER DEFAULT 0,
                        last_executed_at TIMESTAMP,
                        improvement_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(tech_id, improvement_function)
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_technology_improvements table")
                print("   [OK] Created agent_technology_improvements table")
            else:
                print("   [OK] agent_technology_improvements table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_metrics_table(self):
        """Create metrics table for tracking technology metrics"""
        try:
            inspector = inspect(db.engine)
            if 'agent_technology_metrics' not in inspector.get_table_names():
                print("   Creating agent_technology_metrics table...")
                db.session.execute(text("""
                    CREATE TABLE agent_technology_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tech_id VARCHAR(100) NOT NULL,
                        metric_date DATE NOT NULL,
                        performance_score DECIMAL(5,2) DEFAULT 0,
                        security_score DECIMAL(5,2) DEFAULT 0,
                        reliability_score DECIMAL(5,2) DEFAULT 0,
                        total_operations INTEGER DEFAULT 0,
                        successful_operations INTEGER DEFAULT 0,
                        failed_operations INTEGER DEFAULT 0,
                        average_response_time DECIMAL(10,2) DEFAULT 0,
                        total_throughput DECIMAL(15,2) DEFAULT 0,
                        error_rate DECIMAL(5,2) DEFAULT 0,
                        metrics_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(tech_id, metric_date)
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_technology_metrics table")
                print("   [OK] Created agent_technology_metrics table")
            else:
                print("   [OK] agent_technology_metrics table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_usage_table(self):
        """Create usage statistics table"""
        try:
            inspector = inspect(db.engine)
            if 'agent_technology_usage' not in inspector.get_table_names():
                print("   Creating agent_technology_usage table...")
                db.session.execute(text("""
                    CREATE TABLE agent_technology_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tech_id VARCHAR(100) NOT NULL,
                        user_id VARCHAR(100),
                        usage_count INTEGER DEFAULT 0,
                        total_executions INTEGER DEFAULT 0,
                        successful_executions INTEGER DEFAULT 0,
                        failed_executions INTEGER DEFAULT 0,
                        total_points_earned DECIMAL(15,2) DEFAULT 0,
                        average_execution_time DECIMAL(10,2) DEFAULT 0,
                        first_used_at TIMESTAMP,
                        last_used_at TIMESTAMP,
                        usage_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(tech_id, user_id)
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_technology_usage table")
                print("   [OK] Created agent_technology_usage table")
            else:
                print("   [OK] agent_technology_usage table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_relationships_table(self):
        """Create relationships table for technology dependencies"""
        try:
            inspector = inspect(db.engine)
            if 'agent_technology_relationships' not in inspector.get_table_names():
                print("   Creating agent_technology_relationships table...")
                db.session.execute(text("""
                    CREATE TABLE agent_technology_relationships (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tech_id VARCHAR(100) NOT NULL,
                        related_tech_id VARCHAR(100) NOT NULL,
                        relationship_type VARCHAR(50) NOT NULL,
                        strength DECIMAL(5,2) DEFAULT 1.0,
                        description TEXT,
                        relationship_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(tech_id, related_tech_id, relationship_type)
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_technology_relationships table")
                print("   [OK] Created agent_technology_relationships table")
            else:
                print("   [OK] agent_technology_relationships table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_events_table(self):
        """Create events table for technology operations"""
        try:
            inspector = inspect(db.engine)
            if 'agent_technology_events' not in inspector.get_table_names():
                print("   Creating agent_technology_events table...")
                db.session.execute(text("""
                    CREATE TABLE agent_technology_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tech_id VARCHAR(100) NOT NULL,
                        user_id VARCHAR(100),
                        event_type VARCHAR(50) NOT NULL,
                        event_action VARCHAR(100),
                        event_status VARCHAR(20) DEFAULT 'success',
                        execution_time DECIMAL(10,2) DEFAULT 0,
                        points_earned DECIMAL(15,2) DEFAULT 0,
                        error_message TEXT,
                        event_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                self.migrations_applied.append("Created agent_technology_events table")
                print("   [OK] Created agent_technology_events table")
            else:
                print("   [OK] agent_technology_events table exists")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def insert_default_technologies(self):
        """Insert all 50 default technologies"""
        try:
            inspector = inspect(db.engine)
            if 'agent_technologies' not in inspector.get_table_names():
                print("   [WARN] Technologies table doesn't exist, skipping insert")
                return
            
            existing = db.session.execute(
                text("SELECT COUNT(*) FROM agent_technologies")
            ).scalar()

            inserted = 0
            if existing == 0:
                for tech in AGENT_TECHS:
                    try:
                        db.session.execute(
                            text("""
                                INSERT INTO agent_technologies 
                                (tech_id, tech_name, category, icon, description, version, status, enabled, created_at, updated_at)
                                VALUES (:tech_id, :tech_name, :category, :icon, :description, '1.0.0', 'active', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """),
                            {
                                "tech_id": tech['id'],
                                "tech_name": tech['name'],
                                "category": tech['category'],
                                "icon": tech.get('icon', ''),
                                "description": tech.get('description', '')
                            }
                        )
                        inserted += 1
                    except Exception:
                        pass
            else:
                print(f"   [OK] {existing} technologies already exist")

            improvements_inserted = 0
            if existing == 0:
                for tech in AGENT_TECHS:
                    for improvement in IMPROVEMENT_FUNCTIONS:
                        try:
                            db.session.execute(
                                text("""
                                    INSERT INTO agent_technology_improvements
                                    (tech_id, improvement_function, improvement_name, status, level, max_level, created_at, updated_at)
                                    VALUES (:tech_id, :improvement_function, :improvement_name, 'available', 0, 10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                """),
                                {
                                    "tech_id": tech['id'],
                                    "improvement_function": improvement,
                                    "improvement_name": improvement.replace('_', ' ').title()
                                }
                            )
                            improvements_inserted += 1
                        except Exception:
                            pass

            # Ensure Synchronization tech exists (Rulebook V16)
            sync_tech = next((t for t in AGENT_TECHS if t['id'] == 'agent_synchronization'), None)
            if sync_tech:
                try:
                    db.session.execute(
                        text("""
                            INSERT OR IGNORE INTO agent_technologies
                            (tech_id, tech_name, category, icon, description, version, status, enabled, created_at, updated_at)
                            VALUES (:tech_id, :tech_name, :category, :icon, :description, '1.0.0', 'active', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """),
                        {"tech_id": sync_tech['id'], "tech_name": sync_tech['name'], "category": sync_tech['category'],
                         "icon": sync_tech.get('icon', ''), "description": sync_tech.get('description', '')}
                    )
                    for imp in IMPROVEMENT_FUNCTIONS:
                        try:
                            db.session.execute(
                                text("""
                                    INSERT OR IGNORE INTO agent_technology_improvements
                                    (tech_id, improvement_function, improvement_name, status, level, max_level, created_at, updated_at)
                                    VALUES (:tech_id, :improvement_function, :improvement_name, 'available', 0, 10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                """),
                                {"tech_id": 'agent_synchronization', "improvement_function": imp, "improvement_name": imp.replace('_', ' ').title()}
                            )
                            improvements_inserted += 1
                        except Exception:
                            pass
                except Exception as e:
                    print(f"   [WARN] Synchronization upsert: {e}")

            # Ensure Electric Magnet tech exists and has special improvements (run_verification, run_dna_test)
            em_tech = next((t for t in AGENT_TECHS if t['id'] == 'agent_electric_magnet'), None)
            if em_tech:
                try:
                    db.session.execute(
                        text("""
                            INSERT OR IGNORE INTO agent_technologies
                            (tech_id, tech_name, category, icon, description, version, status, enabled, created_at, updated_at)
                            VALUES (:tech_id, :tech_name, :category, :icon, :description, '1.0.0', 'active', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """),
                        {"tech_id": em_tech['id'], "tech_name": em_tech['name'], "category": em_tech['category'],
                         "icon": em_tech.get('icon', ''), "description": em_tech.get('description', '')}
                    )
                    for imp in SPECIAL_IMPROVEMENT_FUNCTIONS:
                        try:
                            db.session.execute(
                                text("""
                                    INSERT OR IGNORE INTO agent_technology_improvements
                                    (tech_id, improvement_function, improvement_name, status, level, max_level, created_at, updated_at)
                                    VALUES (:tech_id, :improvement_function, :improvement_name, 'available', 0, 10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                """),
                                {"tech_id": 'agent_electric_magnet', "improvement_function": imp, "improvement_name": imp.replace('_', ' ').title()}
                            )
                            improvements_inserted += 1
                        except Exception:
                            pass
                except Exception as e:
                    print(f"   [WARN] Electric Magnet upsert: {e}")

            db.session.commit()
            self.migrations_applied.append(f"Inserted {inserted} technologies and {improvements_inserted} improvements")
            print(f"   [OK] Inserted {inserted} technologies")
            print(f"   [OK] Inserted {improvements_inserted} improvement functions")
        except Exception as e:
            print(f"   [ERROR] Failed: {str(e)}")
            db.session.rollback()
    
    def create_indexes(self):
        """Create indexes for performance"""
        indexes = [
            # Technologies indexes
            ("agent_technologies", "idx_tech_category", "category"),
            ("agent_technologies", "idx_tech_status", "status"),
            ("agent_technologies", "idx_tech_enabled", "enabled"),
            
            # Improvements indexes
            ("agent_technology_improvements", "idx_improvements_tech_id", "tech_id"),
            ("agent_technology_improvements", "idx_improvements_status", "status"),
            ("agent_technology_improvements", "idx_improvements_tech_status", "tech_id, status"),
            
            # Metrics indexes
            ("agent_technology_metrics", "idx_metrics_tech_id", "tech_id"),
            ("agent_technology_metrics", "idx_metrics_date", "metric_date"),
            ("agent_technology_metrics", "idx_metrics_tech_date", "tech_id, metric_date"),
            
            # Usage indexes
            ("agent_technology_usage", "idx_usage_tech_id", "tech_id"),
            ("agent_technology_usage", "idx_usage_user_id", "user_id"),
            ("agent_technology_usage", "idx_usage_tech_user", "tech_id, user_id"),
            
            # Relationships indexes
            ("agent_technology_relationships", "idx_relationships_tech_id", "tech_id"),
            ("agent_technology_relationships", "idx_relationships_related", "related_tech_id"),
            ("agent_technology_relationships", "idx_relationships_type", "relationship_type"),
            
            # Events indexes
            ("agent_technology_events", "idx_events_tech_id", "tech_id"),
            ("agent_technology_events", "idx_events_user_id", "user_id"),
            ("agent_technology_events", "idx_events_type", "event_type"),
            ("agent_technology_events", "idx_events_created", "created_at"),
            ("agent_technology_events", "idx_events_tech_created", "tech_id, created_at"),
        ]
        
        created = 0
        for table, index_name, columns in indexes:
            try:
                db.session.execute(text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} ON {table}({columns})
                """))
                created += 1
            except Exception:
                # Table might not exist or index already exists
                pass
        
        if created > 0:
            db.session.commit()
            self.migrations_applied.append(f"Created {created} indexes")
            print(f"   [OK] Created {created} indexes")
        else:
            print("   [OK] Indexes are up to date")


def main():
    """Main entry point"""
    migration = AgentTechnologiesMigration()
    migration.run_migration()


if __name__ == '__main__':
    main()
