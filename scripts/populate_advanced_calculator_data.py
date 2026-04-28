#!/usr/bin/env python3
"""
Comprehensive Data Population Script for Advanced Calculator API
Generates massive amounts of constructive, realistic data for all calculator tables
"""
import os
import sys
import random
import json
from datetime import datetime, timedelta

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Ensure we're in the project root directory
try:
    os.chdir(BASE_DIR)
except:
    pass

# Also add to PYTHONPATH
os.environ['PYTHONPATH'] = BASE_DIR + os.pathsep + os.environ.get('PYTHONPATH', '')

# Sample system names from 178 systems
SAMPLE_SYSTEMS = [
    'xp', 'activity', 'theme', 'chat', 'trophy', 'battle', 'achievement', 'stats',
    'metal', 'graduation', 'generation', 'krimetime', 'guild', 'rewards', 'shop',
    'social', 'champions_league', 'watch_time', 'scroll_depth', 'interaction_quality',
    'return_visitor', 'session_duration', 'page_depth', 'content_consumption',
    'search', 'filter', 'share', 'bookmark', 'comment', 'rating', 'pvp_battle',
    'pve_battle', 'team_battle', 'guild_battle', 'arena_battle', 'tournament',
    'ranked_battle', 'casual_battle', 'victory', 'defeat', 'perfect_victory',
    'comeback', 'streak_battle', 'first_blood', 'multi_kill', 'assist', 'defense',
    'offense', 'tactical', 'strategy', 'combo', 'ultimate', 'video_generation',
    'clip_generation', 'image_generation', 'audio_generation', 'text_generation',
    'template_usage', 'custom_creation', 'quality', 'innovation', 'trending',
    'viral', 'collaboration', 'remix'
]

CALCULATION_TYPES = ['intelligent', 'atomic', 'financial', 'point_calculator', 'comprehensive']
PREDICTION_TYPES = ['future_points', 'trend', 'correction', 'growth', 'decline']
ANALYSIS_TYPES = ['trend', 'anomaly', 'correlation', 'neural', 'pattern', 'seasonal']
DETECTION_METHODS = ['statistical', 'pattern', 'neural', 'threshold', 'comparative']
REPAIR_TYPES = ['point_restoration', 'anomaly_fix', 'system_repair', 'comprehensive_repair', 'auto_fix']
ANOMALY_SEVERITIES = ['low', 'medium', 'high', 'critical']
ANOMALY_TYPES = ['statistical', 'pattern', 'neural', 'outlier', 'deviation']


def generate_user_ids(count=100):
    """Generate user IDs"""
    users = []
    for i in range(1, count + 1):
        users.append(f"user_{i:03d}")
    # Add some variation
    variations = ['player', 'gamer', 'hunter', 'master', 'pro']
    for variation in variations:
        for i in range(1, 21):
            users.append(f"{variation}_{i:02d}")
    return users


def generate_realistic_calculation_data(user_id, calc_type, base_total):
    """Generate realistic calculation data structure"""
    num_systems = random.randint(10, 50)
    systems = random.sample(SAMPLE_SYSTEMS, min(num_systems, len(SAMPLE_SYSTEMS)))
    
    system_breakdown = {}
    multipliers_applied = {}
    calculation_data = {
        'base_total': base_total * 0.8,
        'multiplier_total': base_total,
        'systems_included': systems[:10],
        'calculation_steps': random.randint(5, 15)
    }
    
    remaining_points = base_total
    for system in systems:
        if remaining_points <= 0:
            break
        points = random.uniform(remaining_points * 0.02, remaining_points * 0.15)
        system_breakdown[system] = round(points, 2)
        multipliers_applied[system] = round(random.uniform(1.0, 2.5), 2)
        remaining_points -= points
    
    insights = [
        f"User shows strong engagement in {random.choice(systems[:3])}",
        f"Potential for growth in {random.choice(systems[-3:])}",
        f"Overall activity trending {'upward' if random.random() > 0.5 else 'downward'}"
    ]
    
    return {
        'calculation_data': calculation_data,
        'system_breakdown': system_breakdown,
        'multipliers_applied': multipliers_applied,
        'insights': insights
    }


def populate_calculation_history(db, users, num_records=1000):
    """Populate calculation_history table"""
    print(f"\n[1/7] Populating calculation_history ({num_records} records)...")
    
    from src.db.models_advanced_calculator import CalculationHistory
    
    records_created = 0
    start_date = datetime.utcnow() - timedelta(days=180)  # 6 months of history
    
    try:
        for i in range(num_records):
            user_id = random.choice(users)
            calc_type = random.choice(CALCULATION_TYPES)
            
            # Generate realistic totals
            base_total = random.uniform(100, 50000)
            final_total = base_total * random.uniform(1.0, 1.5)
            
            calc_data = generate_realistic_calculation_data(user_id, calc_type, final_total)
            
            # Create timestamp (spread over 180 days)
            days_ago = random.randint(0, 180)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            created_at = start_date + timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            record = CalculationHistory(
                user_id=user_id,
                calculation_type=calc_type,
                final_total=round(final_total, 2),
                confidence_score=round(random.uniform(0.6, 0.99), 3),
                points_restored=round(random.uniform(0, final_total * 0.1), 2),
                anomalies_detected_count=random.randint(0, 5),
                calculation_data=calc_data['calculation_data'],
                system_breakdown=calc_data['system_breakdown'],
                multipliers_applied=calc_data['multipliers_applied'],
                insights=calc_data['insights'],
                calculation_duration_ms=random.randint(50, 500),
                created_at=created_at
            )
            
            db.session.add(record)
            records_created += 1
            
            if (i + 1) % 100 == 0:
                db.session.commit()
                print(f"  Created {i + 1}/{num_records} calculation records...")
        
        db.session.commit()
        print(f"  ✅ Created {records_created} calculation_history records")
        return records_created
        
    except Exception as e:
        db.session.rollback()
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def populate_point_loss_detection(db, users, calculations, num_records=300):
    """Populate point_loss_detection table"""
    print(f"\n[2/7] Populating point_loss_detection ({num_records} records)...")
    
    from src.db.models_advanced_calculator import PointLossDetection
    
    records_created = 0
    start_date = datetime.utcnow() - timedelta(days=180)
    
    try:
        for i in range(num_records):
            user_id = random.choice(users)
            points_lost = random.uniform(50, 5000)
            num_systems_affected = random.randint(1, 15)
            systems = random.sample(SAMPLE_SYSTEMS, min(num_systems_affected, len(SAMPLE_SYSTEMS)))
            
            loss_breakdown = {}
            remaining_loss = points_lost
            for system in systems:
                if remaining_loss <= 0:
                    break
                loss = random.uniform(remaining_loss * 0.1, remaining_loss * 0.3)
                loss_breakdown[system] = round(loss, 2)
                remaining_loss -= loss
            
            days_ago = random.randint(0, 180)
            created_at = start_date + timedelta(days=days_ago)
            
            # Some losses are resolved
            is_resolved = random.random() > 0.3
            resolved_at = None
            if is_resolved:
                resolved_at = created_at + timedelta(days=random.randint(1, 30))
            
            record = PointLossDetection(
                user_id=user_id,
                points_lost=round(points_lost, 2),
                systems_affected=num_systems_affected,
                detection_confidence=round(random.uniform(0.7, 0.98), 3),
                affected_systems=systems,
                loss_breakdown=loss_breakdown,
                detection_method=random.choice(DETECTION_METHODS),
                is_resolved=is_resolved,
                resolved_at=resolved_at,
                created_at=created_at
            )
            
            db.session.add(record)
            records_created += 1
            
            if (i + 1) % 50 == 0:
                db.session.commit()
                print(f"  Created {i + 1}/{num_records} loss detection records...")
        
        db.session.commit()
        print(f"  ✅ Created {records_created} point_loss_detection records")
        return records_created
        
    except Exception as e:
        db.session.rollback()
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def populate_repair_log(db, users, calculations, loss_detections, num_records=400):
    """Populate repair_log table"""
    print(f"\n[3/7] Populating repair_log ({num_records} records)...")
    
    from src.db.models_advanced_calculator import RepairLog
    
    records_created = 0
    start_date = datetime.utcnow() - timedelta(days=180)
    
    try:
        calculation_ids = [c.id for c in calculations] if calculations else []
        loss_ids = [l.id for l in loss_detections] if loss_detections else []
        
        for i in range(num_records):
            user_id = random.choice(users)
            repair_type = random.choice(REPAIR_TYPES)
            
            calculation_id = random.choice(calculation_ids) if calculation_ids else None
            loss_detection_id = random.choice(loss_ids) if loss_ids and random.random() > 0.5 else None
            
            systems_checked = random.randint(5, 50)
            issues_detected = random.randint(0, systems_checked // 2)
            points_restored = random.uniform(100, 3000)
            
            systems_repaired = random.sample(SAMPLE_SYSTEMS, min(issues_detected, len(SAMPLE_SYSTEMS)))
            repairs_performed = [
                {
                    'system': sys_name,
                    'points_restored': round(points_restored / len(systems_repaired), 2),
                    'method': random.choice(['auto_repair', 'manual_repair', 'system_reset'])
                }
                for sys_name in systems_repaired
            ]
            
            days_ago = random.randint(0, 180)
            created_at = start_date + timedelta(days=days_ago)
            
            success = random.random() > 0.15  # 85% success rate
            
            record = RepairLog(
                user_id=user_id,
                calculation_id=calculation_id,
                loss_detection_id=loss_detection_id,
                repair_type=repair_type,
                systems_checked=systems_checked,
                issues_detected=issues_detected,
                points_restored=round(points_restored, 2),
                repairs_performed=repairs_performed,
                issues_found=[f"Issue in {sys}" for sys in systems_repaired[:5]],
                systems_repaired=systems_repaired,
                success=success,
                error_message=None if success else "Partial repair completed",
                repair_duration_ms=random.randint(100, 2000),
                created_at=created_at
            )
            
            db.session.add(record)
            records_created += 1
            
            if (i + 1) % 50 == 0:
                db.session.commit()
                print(f"  Created {i + 1}/{num_records} repair log records...")
        
        db.session.commit()
        print(f"  ✅ Created {records_created} repair_log records")
        return records_created
        
    except Exception as e:
        db.session.rollback()
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def populate_predictions(db, users, num_records=500):
    """Populate predictions table"""
    print(f"\n[4/7] Populating predictions ({num_records} records)...")
    
    from src.db.models_advanced_calculator import Prediction
    
    records_created = 0
    start_date = datetime.utcnow() - timedelta(days=180)
    
    try:
        for i in range(num_records):
            user_id = random.choice(users)
            prediction_type = random.choice(PREDICTION_TYPES)
            days_ahead = random.choice([7, 14, 30, 60, 90])
            
            base_prediction = random.uniform(1000, 40000)
            predicted_points = base_prediction * random.uniform(0.8, 1.3)
            confidence = random.uniform(0.65, 0.95)
            
            prediction_range_min = predicted_points * (1 - (1 - confidence) * 0.5)
            prediction_range_max = predicted_points * (1 + (1 - confidence) * 0.5)
            
            num_systems = random.randint(10, 30)
            systems = random.sample(SAMPLE_SYSTEMS, min(num_systems, len(SAMPLE_SYSTEMS)))
            
            prediction_breakdown = {}
            remaining = predicted_points
            for system in systems:
                if remaining <= 0:
                    break
                points = random.uniform(remaining * 0.02, remaining * 0.15)
                prediction_breakdown[system] = round(points, 2)
                remaining -= points
            
            factors_considered = [
                'historical_trends', 'user_activity', 'system_performance',
                'seasonal_patterns', 'recent_changes'
            ]
            
            days_ago = random.randint(0, 180)
            created_at = start_date + timedelta(days=days_ago)
            
            record = Prediction(
                user_id=user_id,
                prediction_type=prediction_type,
                days_ahead=days_ahead,
                predicted_points=round(predicted_points, 2),
                confidence_level=round(confidence, 3),
                prediction_range_min=round(prediction_range_min, 2),
                prediction_range_max=round(prediction_range_max, 2),
                prediction_breakdown=prediction_breakdown,
                factors_considered=factors_considered,
                historical_data_points=random.randint(50, 500),
                created_at=created_at
            )
            
            db.session.add(record)
            records_created += 1
            
            if (i + 1) % 50 == 0:
                db.session.commit()
                print(f"  Created {i + 1}/{num_records} prediction records...")
        
        db.session.commit()
        print(f"  ✅ Created {records_created} predictions records")
        return records_created
        
    except Exception as e:
        db.session.rollback()
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def populate_pattern_analysis(db, users, num_records=400):
    """Populate pattern_analysis table"""
    print(f"\n[5/7] Populating pattern_analysis ({num_records} records)...")
    
    from src.db.models_advanced_calculator import PatternAnalysis
    
    records_created = 0
    start_date = datetime.utcnow() - timedelta(days=180)
    
    try:
        for i in range(num_records):
            user_id = random.choice(users)
            analysis_type = random.choice(ANALYSIS_TYPES)
            
            num_patterns = random.randint(1, 8)
            patterns = []
            for j in range(num_patterns):
                patterns.append({
                    'pattern_id': f"pattern_{j+1}",
                    'description': f"Pattern {j+1} detected in {random.choice(SAMPLE_SYSTEMS)}",
                    'strength': round(random.uniform(0.5, 0.95), 2),
                    'significance': random.choice(['low', 'medium', 'high'])
                })
            
            insights = [
                f"User shows consistent activity in {random.choice(SAMPLE_SYSTEMS[:10])}",
                f"Potential optimization opportunity in {random.choice(SAMPLE_SYSTEMS[10:20])}",
                f"Trend analysis indicates {'growth' if random.random() > 0.5 else 'stability'}"
            ]
            
            recommendations = [
                f"Consider focusing on {random.choice(SAMPLE_SYSTEMS[:15])}",
                f"Monitor {random.choice(SAMPLE_SYSTEMS[15:])} for improvements"
            ]
            
            num_systems = random.randint(10, 40)
            systems_analyzed = random.sample(SAMPLE_SYSTEMS, min(num_systems, len(SAMPLE_SYSTEMS)))
            
            days_ago = random.randint(0, 180)
            created_at = start_date + timedelta(days=days_ago)
            
            record = PatternAnalysis(
                user_id=user_id,
                analysis_type=analysis_type,
                patterns_found=num_patterns,
                confidence_score=round(random.uniform(0.7, 0.98), 3),
                patterns=patterns,
                insights=insights,
                recommendations=recommendations,
                data_range_days=random.randint(30, 180),
                systems_analyzed=systems_analyzed,
                analysis_duration_ms=random.randint(200, 3000),
                created_at=created_at
            )
            
            db.session.add(record)
            records_created += 1
            
            if (i + 1) % 50 == 0:
                db.session.commit()
                print(f"  Created {i + 1}/{num_records} pattern analysis records...")
        
        db.session.commit()
        print(f"  ✅ Created {records_created} pattern_analysis records")
        return records_created
        
    except Exception as e:
        db.session.rollback()
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def populate_anomaly_detection(db, users, calculations, num_records=600):
    """Populate anomaly_detection table"""
    print(f"\n[6/7] Populating anomaly_detection ({num_records} records)...")
    
    from src.db.models_advanced_calculator import AnomalyDetection
    
    records_created = 0
    start_date = datetime.utcnow() - timedelta(days=180)
    
    try:
        calculation_ids = [c.id for c in calculations] if calculations else []
        
        for i in range(num_records):
            user_id = random.choice(users)
            anomaly_type = random.choice(ANOMALY_TYPES)
            severity = random.choice(ANOMALY_SEVERITIES)
            
            calculation_id = random.choice(calculation_ids) if calculation_ids and random.random() > 0.3 else None
            
            affected_system = random.choice(SAMPLE_SYSTEMS)
            expected_value = random.uniform(100, 5000)
            deviation_percent = random.uniform(0.1, 0.5) if severity == 'low' else random.uniform(0.5, 2.0) if severity == 'medium' else random.uniform(2.0, 5.0)
            actual_value = expected_value * (1 + deviation_percent)
            deviation = actual_value - expected_value
            
            anomaly_details = {
                'description': f"Anomaly detected in {affected_system}",
                'magnitude': round(deviation_percent * 100, 2),
                'context': 'normal_operation'
            }
            
            suggested_fix = {
                'action': random.choice(['investigate', 'reset', 'repair', 'monitor']),
                'priority': severity,
                'estimated_impact': round(deviation * 0.8, 2)
            }
            
            is_fixed = random.random() > 0.4  # 60% fixed
            fixed_at = None
            if is_fixed:
                days_ago = random.randint(0, 180)
                created_at = start_date + timedelta(days=days_ago)
                fixed_at = created_at + timedelta(hours=random.randint(1, 72))
            
            days_ago = random.randint(0, 180)
            created_at = start_date + timedelta(days=days_ago)
            
            record = AnomalyDetection(
                user_id=user_id,
                calculation_id=calculation_id,
                anomaly_type=anomaly_type,
                severity=severity,
                confidence=round(random.uniform(0.75, 0.98), 3),
                affected_system=affected_system,
                expected_value=round(expected_value, 2),
                actual_value=round(actual_value, 2),
                deviation=round(deviation, 2),
                anomaly_details=anomaly_details,
                suggested_fix=suggested_fix,
                is_fixed=is_fixed,
                fixed_at=fixed_at,
                created_at=created_at
            )
            
            db.session.add(record)
            records_created += 1
            
            if (i + 1) % 50 == 0:
                db.session.commit()
                print(f"  Created {i + 1}/{num_records} anomaly detection records...")
        
        db.session.commit()
        print(f"  ✅ Created {records_created} anomaly_detection records")
        return records_created
        
    except Exception as e:
        db.session.rollback()
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def populate_system_point_snapshots(db, users, calculations, num_records=2000):
    """Populate system_point_snapshots table"""
    print(f"\n[7/7] Populating system_point_snapshots ({num_records} records)...")
    
    from src.db.models_advanced_calculator import SystemPointSnapshot
    
    records_created = 0
    start_date = datetime.utcnow() - timedelta(days=180)
    
    try:
        calculation_ids = [c.id for c in calculations] if calculations else []
        
        # Group snapshots by calculation_id for realism
        snapshots_per_calc = {}
        remaining = num_records
        
        while remaining > 0:
            calc_id = random.choice(calculation_ids) if calculation_ids else None
            user_id = random.choice(users)
            
            # Create 3-10 snapshots per calculation
            num_snapshots = min(random.randint(3, 10), remaining)
            
            for j in range(num_snapshots):
                system_name = random.choice(SAMPLE_SYSTEMS)
                point_value = random.uniform(10, 5000)
                multiplier = random.uniform(1.0, 2.5)
                calculated_total = point_value * multiplier
                
                days_ago = random.randint(0, 180)
                created_at = start_date + timedelta(days=days_ago, minutes=random.randint(0, 1439))
                
                record = SystemPointSnapshot(
                    user_id=user_id,
                    calculation_id=calc_id,
                    system_name=system_name,
                    point_value=round(point_value, 2),
                    multiplier_applied=round(multiplier, 2),
                    calculated_total=round(calculated_total, 2),
                    created_at=created_at
                )
                
                db.session.add(record)
                records_created += 1
                remaining -= 1
                
                if records_created % 100 == 0:
                    db.session.commit()
                    print(f"  Created {records_created}/{num_records} snapshot records...")
        
        db.session.commit()
        print(f"  ✅ Created {records_created} system_point_snapshots records")
        return records_created
        
    except Exception as e:
        db.session.rollback()
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Main function to populate all tables"""
    print("=" * 80)
    print("ADVANCED CALCULATOR DATA POPULATION")
    print("Generating Massive Amounts of Constructive Data for API")
    print("=" * 80)
    print()
    
    # Verify src directory exists
    src_path = os.path.join(BASE_DIR, 'src')
    if not os.path.exists(src_path):
        print(f"[ERROR] src directory not found at {src_path}")
        print(f"BASE_DIR: {BASE_DIR}")
        return False
    
    try:
        from src.app import create_app
        # Try importing from vidgenerator first (where models actually are)
        try:
            from vidgenerator.src.db.models_advanced_calculator import (
                CalculationHistory, PointLossDetection, RepairLog,
                Prediction, PatternAnalysis, AnomalyDetection, SystemPointSnapshot
            )
        except ImportError:
            # Fallback to src.db
            from src.db.models_advanced_calculator import (
                CalculationHistory, PointLossDetection, RepairLog,
                Prediction, PatternAnalysis, AnomalyDetection, SystemPointSnapshot
            )
        from src.db.models import db
        
        app = create_app()
        
        with app.app_context():
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = [
                'calculation_history', 'point_loss_detection', 'repair_log',
                'predictions', 'pattern_analysis', 'anomaly_detection', 'system_point_snapshots'
            ]
            
            missing = [t for t in required_tables if t not in tables]
            if missing:
                print(f"[ERROR] Missing tables: {', '.join(missing)}")
                print("Please run migrate_advanced_calculator.py first")
                return False
            
            # Generate user IDs
            users = generate_user_ids(100)
            print(f"[INFO] Using {len(users)} user IDs")
            
            # Ask user for record counts
            print("\n" + "=" * 80)
            print("DATA GENERATION CONFIGURATION")
            print("=" * 80)
            print()
            print("Recommended record counts:")
            print("  - calculation_history: 1000-5000")
            print("  - point_loss_detection: 300-1000")
            print("  - repair_log: 400-1500")
            print("  - predictions: 500-2000")
            print("  - pattern_analysis: 400-1500")
            print("  - anomaly_detection: 600-2000")
            print("  - system_point_snapshots: 2000-10000")
            print()
            
            try:
                calc_count = int(input("Number of calculation_history records [1000]: ") or "1000")
                loss_count = int(input("Number of point_loss_detection records [300]: ") or "300")
                repair_count = int(input("Number of repair_log records [400]: ") or "400")
                pred_count = int(input("Number of predictions records [500]: ") or "500")
                pattern_count = int(input("Number of pattern_analysis records [400]: ") or "400")
                anomaly_count = int(input("Number of anomaly_detection records [600]: ") or "600")
                snapshot_count = int(input("Number of system_point_snapshots records [2000]: ") or "2000")
            except (ValueError, KeyboardInterrupt):
                print("\n[INFO] Using default values")
                calc_count = 1000
                loss_count = 300
                repair_count = 400
                pred_count = 500
                pattern_count = 400
                anomaly_count = 600
                snapshot_count = 2000
            
            print()
            print("=" * 80)
            print("STARTING DATA POPULATION")
            print("=" * 80)
            print()
            
            # Populate tables in order (respecting foreign keys)
            total_records = 0
            
            # 1. Calculation History (no dependencies)
            calc_records = populate_calculation_history(db, users, calc_count)
            total_records += calc_records
            calculations = db.session.query(CalculationHistory).all()
            
            # 2. Point Loss Detection (no dependencies)
            loss_records = populate_point_loss_detection(db, users, calculations, loss_count)
            total_records += loss_records
            loss_detections = db.session.query(PointLossDetection).all()
            
            # 3. Repair Log (depends on calculations and loss detections)
            repair_records = populate_repair_log(db, users, calculations, loss_detections, repair_count)
            total_records += repair_records
            
            # 4. Predictions (no dependencies)
            pred_records = populate_predictions(db, users, pred_count)
            total_records += pred_records
            
            # 5. Pattern Analysis (no dependencies)
            pattern_records = populate_pattern_analysis(db, users, pattern_count)
            total_records += pattern_records
            
            # 6. Anomaly Detection (depends on calculations)
            anomaly_records = populate_anomaly_detection(db, users, calculations, anomaly_count)
            total_records += anomaly_records
            
            # 7. System Point Snapshots (depends on calculations)
            snapshot_records = populate_system_point_snapshots(db, users, calculations, snapshot_count)
            total_records += snapshot_records
            
            # Final summary
            print()
            print("=" * 80)
            print("DATA POPULATION COMPLETE!")
            print("=" * 80)
            print()
            print("Summary:")
            print(f"  calculation_history:     {calc_records:,} records")
            print(f"  point_loss_detection:    {loss_records:,} records")
            print(f"  repair_log:              {repair_records:,} records")
            print(f"  predictions:             {pred_records:,} records")
            print(f"  pattern_analysis:        {pattern_records:,} records")
            print(f"  anomaly_detection:       {anomaly_records:,} records")
            print(f"  system_point_snapshots:  {snapshot_records:,} records")
            print()
            print(f"  TOTAL RECORDS CREATED:   {total_records:,}")
            print()
            print("Next steps:")
            print("  1. Test API endpoints to verify data is accessible")
            print("  2. Check statistics endpoints for data aggregation")
            print("  3. Test prediction and analysis endpoints")
            print("  4. Verify data relationships and foreign keys")
            print()
            
            return True
            
    except Exception as e:
        print(f"\n[ERROR] Failed to populate data: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
