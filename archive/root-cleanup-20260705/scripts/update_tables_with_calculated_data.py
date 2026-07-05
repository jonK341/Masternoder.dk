#!/usr/bin/env python3
"""
Update Database Tables with Calculated Data
Add data until it breaks - stress testing
"""
import sys
import os
import json
from datetime import datetime, timedelta
import random
import uuid

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.app import create_app
    from src.db.models import db
    from src.db.models_178_knowledge_intelligence import PointSystemKnowledge, PointSystemIntelligence
    from backend.services.monetization_system import monetization_system
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.unified_point_counter import unified_point_counter
except ImportError as e:
    print(f"[ERROR] Import error: {e}", flush=True)
    sys.exit(1)

def calculate_monetization_data():
    """Calculate monetization revenue data"""
    print("\n[1] Calculating monetization data...", flush=True)
    
    revenue_data = []
    total_revenue = 0.0
    
    # Generate transactions for all 25 streams
    for stream_id, stream in monetization_system.INCOME_STREAMS.items():
        # Calculate number of transactions (random 0-100)
        num_transactions = random.randint(0, 100)
        
        for i in range(num_transactions):
            user_id = f"user_{random.randint(1, 1000)}"
            amount = stream['price']
            
            # Add some randomness to amounts
            if random.random() > 0.7:
                amount *= random.uniform(0.8, 1.2)
            
            transaction = {
                'transaction_id': str(uuid.uuid4()),
                'user_id': user_id,
                'stream_id': stream_id,
                'stream_name': stream['name'],
                'amount': round(amount, 2),
                'currency': stream.get('currency', 'USD'),
                'timestamp': (datetime.utcnow() - timedelta(days=random.randint(0, 365))).isoformat(),
                'month': (datetime.utcnow() - timedelta(days=random.randint(0, 365))).strftime('%Y-%m')
            }
            
            revenue_data.append(transaction)
            total_revenue += amount
    
    print(f"  [OK] Calculated {len(revenue_data)} transactions")
    print(f"  [OK] Total revenue: ${total_revenue:,.2f}")
    
    return revenue_data, total_revenue

def calculate_178_systems_data():
    """Calculate data for all 178 point systems"""
    print("\n[2] Calculating 178 systems data...", flush=True)
    
    # Load 178 systems config
    config_file = '178_systems_config.json'
    if not os.path.exists(config_file):
        print(f"  [WARN] Config file not found: {config_file}", flush=True)
        return []
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    systems_data = []
    all_systems = []
    
    # Collect all systems
    for category_name, category_data in config.get('categories', {}).items():
        systems = category_data.get('systems', [])
        all_systems.extend(systems)
    
    print(f"  [OK] Found {len(all_systems)} systems", flush=True)
    
    # Generate data for each system
    for system_id in all_systems:
        # Calculate points for random users
        num_users = random.randint(10, 100)
        
        for i in range(num_users):
            user_id = f"user_{random.randint(1, 1000)}"
            points = random.randint(0, 10000)
            
            system_data = {
                'user_id': user_id,
                'system_id': system_id,
                'points': points,
                'timestamp': (datetime.utcnow() - timedelta(days=random.randint(0, 90))).isoformat()
            }
            
            systems_data.append(system_data)
    
    print(f"  [OK] Calculated data for {len(systems_data)} user-system combinations", flush=True)
    
    return systems_data

def calculate_knowledge_intelligence_data():
    """Calculate knowledge and intelligence data"""
    print("\n[3] Calculating knowledge & intelligence data...", flush=True)
    
    # Load knowledge data
    knowledge_file = '178_systems_knowledge_data.json'
    if not os.path.exists(knowledge_file):
        print(f"  [WARN] Knowledge file not found: {knowledge_file}", flush=True)
        return [], []
    
    with open(knowledge_file, 'r', encoding='utf-8') as f:
        knowledge_data = json.load(f)
    
    knowledge_entries = []
    intelligence_entries = []
    
    systems = knowledge_data.get('knowledge', {})
    print(f"  [OK] Found {len(systems)} systems with knowledge", flush=True)
    
    for system_id, system_knowledge in systems.items():
        # Create knowledge entry
        knowledge_entry = {
            'id': str(uuid.uuid4()),
            'system_id': system_id,
            'system_name': system_knowledge.get('system_name', system_id),
            'description': system_knowledge.get('description', ''),
            'detailed_description': system_knowledge.get('detailed_description', ''),
            'context': system_knowledge.get('context', ''),
            'examples': json.dumps(system_knowledge.get('examples', [])),
            'best_practices': json.dumps(system_knowledge.get('best_practices', [])),
            'strategies': json.dumps(system_knowledge.get('strategies', [])),
            'intelligence_score': system_knowledge.get('intelligence_score', 50.0),
            'complexity_level': system_knowledge.get('complexity_level', 1),
            'learning_curve': system_knowledge.get('learning_curve', 'easy'),
            'mastery_requirements': json.dumps(system_knowledge.get('mastery_requirements', {})),
            'related_systems': json.dumps(system_knowledge.get('related_systems', [])),
            'prerequisites': json.dumps(system_knowledge.get('prerequisites', [])),
            'unlocks': json.dumps(system_knowledge.get('unlocks', [])),
            'knowledge_points_value': system_knowledge.get('knowledge_points_value', 0),
            'intelligence_points_value': system_knowledge.get('intelligence_points_value', 0)
        }
        
        knowledge_entries.append(knowledge_entry)
        
        # Create intelligence entries for random users
        num_users = random.randint(5, 50)
        for i in range(num_users):
            user_id = f"user_{random.randint(1, 1000)}"
            
            intelligence_entry = {
                'id': str(uuid.uuid4()),
                'system_id': system_id,
                'user_id': user_id,
                'intelligence_score': random.uniform(0, 100),
                'calculation_accuracy': random.uniform(0, 1),
                'prediction_accuracy': random.uniform(0, 1),
                'pattern_recognition_score': random.uniform(0, 100),
                'ai_insights': json.dumps(['insight1', 'insight2']),
                'recommendations': json.dumps(['rec1', 'rec2']),
                'optimizations': json.dumps(['opt1', 'opt2']),
                'neural_analysis': json.dumps({'layer1': 0.5, 'layer2': 0.7}),
                'learning_data': json.dumps({'epochs': 100, 'loss': 0.1}),
                'quantum_state': json.dumps({'state': 'superposition'}),
                'multi_dimensional_data': json.dumps({'dim1': 1, 'dim2': 2}),
                'total_calculations': random.randint(0, 10000),
                'successful_calculations': random.randint(0, 9000),
                'failed_calculations': random.randint(0, 1000),
                'average_confidence': random.uniform(0, 1)
            }
            
            intelligence_entries.append(intelligence_entry)
    
    print(f"  [OK] Calculated {len(knowledge_entries)} knowledge entries", flush=True)
    print(f"  [OK] Calculated {len(intelligence_entries)} intelligence entries", flush=True)
    
    return knowledge_entries, intelligence_entries

def add_data_until_break(app, data_type, data_list, batch_size=100):
    """Add data in batches until it breaks"""
    print(f"\n[4] Adding {data_type} data until break...", flush=True)
    
    added_count = 0
    error_count = 0
    last_error = None
    
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            print(f"  [OK] Tables created/verified", flush=True)
        except Exception as e:
            print(f"  [WARN] Table creation: {e}", flush=True)
        
        # Process in batches
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]
            
            try:
                if data_type == 'monetization':
                    # Add to monetization system
                    for transaction in batch:
                        monetization_system.record_purchase(
                            transaction['user_id'],
                            transaction['stream_id'],
                            transaction['amount'],
                            transaction['currency']
                        )
                    added_count += len(batch)
                
                elif data_type == 'knowledge':
                    # Add knowledge entries
                    for entry in batch:
                        try:
                            knowledge = PointSystemKnowledge(**entry)
                            db.session.add(knowledge)
                        except Exception as e:
                            error_count += 1
                            last_error = str(e)
                            continue
                    
                    db.session.commit()
                    added_count += len(batch) - error_count
                
                elif data_type == 'intelligence':
                    # Add intelligence entries
                    for entry in batch:
                        try:
                            intelligence = PointSystemIntelligence(**entry)
                            db.session.add(intelligence)
                        except Exception as e:
                            error_count += 1
                            last_error = str(e)
                            continue
                    
                    db.session.commit()
                    added_count += len(batch) - error_count
                
                elif data_type == 'points':
                    # Add points via unified system
                    for entry in batch:
                        try:
                            unified_point_counter.add_points(
                                entry['user_id'],
                                entry['system_id'],
                                entry['points']
                            )
                        except Exception as e:
                            error_count += 1
                            last_error = str(e)
                            continue
                    
                    added_count += len(batch) - error_count
                
                if (i + batch_size) % 1000 == 0:
                    print(f"  [PROGRESS] Added {added_count} entries, {error_count} errors", flush=True)
                
                # Check if we're hitting limits
                if error_count > added_count * 0.1:  # More than 10% errors
                    print(f"  [WARN] High error rate: {error_count}/{added_count}", flush=True)
                    break
                
            except Exception as e:
                print(f"  [ERROR] Batch failed: {e}", flush=True)
                last_error = str(e)
                error_count += len(batch)
                
                # Try smaller batch
                if batch_size > 10:
                    batch_size = max(10, batch_size // 2)
                    print(f"  [INFO] Reducing batch size to {batch_size}", flush=True)
                else:
                    print(f"  [BREAK] Too many errors, stopping", flush=True)
                    break
    
    print(f"  [RESULT] Added: {added_count}, Errors: {error_count}", flush=True)
    if last_error:
        print(f"  [LAST ERROR] {last_error}", flush=True)
    
    return added_count, error_count

def main():
    """Main function"""
    print("=" * 80)
    print("UPDATE DATABASE TABLES WITH CALCULATED DATA")
    print("Adding data until it breaks - stress testing")
    print("=" * 80)
    
    # Create Flask app
    app = create_app()
    
    # Calculate all data
    monetization_data, total_revenue = calculate_monetization_data()
    systems_data = calculate_178_systems_data()
    knowledge_data, intelligence_data = calculate_knowledge_intelligence_data()
    
    print("\n" + "=" * 80)
    print("DATA CALCULATION SUMMARY")
    print("=" * 80)
    print(f"Monetization transactions: {len(monetization_data)}")
    print(f"Total revenue: ${total_revenue:,.2f}")
    print(f"178 Systems data entries: {len(systems_data)}")
    print(f"Knowledge entries: {len(knowledge_data)}")
    print(f"Intelligence entries: {len(intelligence_data)}")
    print()
    
    # Add data until break
    results = {}
    
    # 1. Monetization data
    if monetization_data:
        added, errors = add_data_until_break(app, 'monetization', monetization_data)
        results['monetization'] = {'added': added, 'errors': errors}
    
    # 2. Knowledge data
    if knowledge_data:
        added, errors = add_data_until_break(app, 'knowledge', knowledge_data)
        results['knowledge'] = {'added': added, 'errors': errors}
    
    # 3. Intelligence data
    if intelligence_data:
        added, errors = add_data_until_break(app, 'intelligence', intelligence_data)
        results['intelligence'] = {'added': added, 'errors': errors}
    
    # 4. Points data
    if systems_data:
        added, errors = add_data_until_break(app, 'points', systems_data)
        results['points'] = {'added': added, 'errors': errors}
    
    # Final summary
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    for data_type, result in results.items():
        print(f"{data_type.upper()}:")
        print(f"  Added: {result['added']}")
        print(f"  Errors: {result['errors']}")
        print(f"  Success Rate: {(result['added'] / (result['added'] + result['errors']) * 100) if (result['added'] + result['errors']) > 0 else 0:.2f}%")
        print()
    
    print("=" * 80)
    print("DATA UPDATE COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()

