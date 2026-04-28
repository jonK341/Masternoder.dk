"""
Populate Initial Rewards Data
Creates default rewards for the hunters game system
"""
import os
import sys
import json

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.app import create_app


def populate_rewards():
    """Populate initial rewards data"""
    print("=" * 70)
    print("Populating Initial Rewards")
    print("=" * 70)
    print()
    
    app = create_app()
    
    with app.app_context():
        from src.db.models import db
        
        try:
            # Check if rewards table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'rewards' not in tables:
                print("[ERROR] Rewards table does not exist!")
                print("Please run migrate_hunters_game_complete.py first")
                return False
            
            # Check if rewards already exist
            result = db.session.execute("SELECT COUNT(*) FROM rewards")
            existing_count = result.scalar()
            
            if existing_count > 0:
                print(f"[INFO] {existing_count} rewards already exist")
                response = input("Do you want to add more rewards? (y/n): ")
                if response.lower() != 'y':
                    print("Skipping reward population")
                    return True
            
            # Define initial rewards
            rewards = [
                # Level-based rewards
                {
                    'reward_type': 'level',
                    'reward_name': 'Level 5 Achievement',
                    'reward_description': 'Reach level 5 to unlock premium themes',
                    'level_required': 5,
                    'points_required': None,
                    'point_type': None,
                    'reward_data': json.dumps({
                        'themes': ['premium', 'nature'],
                        'stat_points': 5
                    }),
                    'icon': '🎨'
                },
                {
                    'reward_type': 'level',
                    'reward_name': 'Level 10 Milestone',
                    'reward_description': 'Reach level 10 for exclusive templates',
                    'level_required': 10,
                    'points_required': None,
                    'point_type': None,
                    'reward_data': json.dumps({
                        'templates': ['professional', 'cinematic'],
                        'stat_points': 10
                    }),
                    'icon': '🏆'
                },
                {
                    'reward_type': 'level',
                    'reward_name': 'Level 25 Expert',
                    'reward_description': 'Become an expert hunter',
                    'level_required': 25,
                    'points_required': None,
                    'point_type': None,
                    'reward_data': json.dumps({
                        'title': 'Expert Hunter',
                        'stat_points': 25,
                        'xp_bonus': 10
                    }),
                    'icon': '⭐'
                },
                
                # Points-based rewards (XP)
                {
                    'reward_type': 'points',
                    'reward_name': '1,000 XP Reward',
                    'reward_description': 'Earn 1,000 XP to unlock this reward',
                    'level_required': None,
                    'points_required': 1000,
                    'point_type': 'xp',
                    'reward_data': json.dumps({
                        'stat_points': 2,
                        'themes': ['starter']
                    }),
                    'icon': '💎'
                },
                {
                    'reward_type': 'points',
                    'reward_name': '5,000 XP Milestone',
                    'reward_description': 'Reach 5,000 XP for bonus stat points',
                    'level_required': None,
                    'points_required': 5000,
                    'point_type': 'xp',
                    'reward_data': json.dumps({
                        'stat_points': 10
                    }),
                    'icon': '🎯'
                },
                {
                    'reward_type': 'points',
                    'reward_name': '10,000 XP Achievement',
                    'reward_description': 'Major milestone reward',
                    'level_required': None,
                    'points_required': 10000,
                    'point_type': 'xp',
                    'reward_data': json.dumps({
                        'stat_points': 20,
                        'themes': ['premium']
                    }),
                    'icon': '🌟'
                },
                
                # Generation points rewards
                {
                    'reward_type': 'points',
                    'reward_name': '100 Generation Points',
                    'reward_description': 'Create 100 videos to unlock',
                    'level_required': None,
                    'points_required': 100,
                    'point_type': 'generation',
                    'reward_data': json.dumps({
                        'stat_points': 5,
                        'templates': ['video_master']
                    }),
                    'icon': '🎬'
                },
                {
                    'reward_type': 'points',
                    'reward_name': '500 Generation Points',
                    'reward_description': 'Video creation master',
                    'level_required': None,
                    'points_required': 500,
                    'point_type': 'generation',
                    'reward_data': json.dumps({
                        'stat_points': 15,
                        'themes': ['cinematic']
                    }),
                    'icon': '🎥'
                },
                
                # Battle points rewards
                {
                    'reward_type': 'points',
                    'reward_name': '50 Battle Points',
                    'reward_description': 'Win battles to earn rewards',
                    'level_required': None,
                    'points_required': 50,
                    'point_type': 'battle',
                    'reward_data': json.dumps({
                        'stat_points': 3
                    }),
                    'icon': '⚔️'
                },
                {
                    'reward_type': 'points',
                    'reward_name': '200 Battle Points',
                    'reward_description': 'Battle champion reward',
                    'level_required': None,
                    'points_required': 200,
                    'point_type': 'battle',
                    'reward_data': json.dumps({
                        'stat_points': 10,
                        'themes': ['warrior']
                    }),
                    'icon': '🛡️'
                },
                
                # Social points rewards
                {
                    'reward_type': 'points',
                    'reward_name': '100 Social Points',
                    'reward_description': 'Engage with the community',
                    'level_required': None,
                    'points_required': 100,
                    'point_type': 'social',
                    'reward_data': json.dumps({
                        'stat_points': 5
                    }),
                    'icon': '👥'
                },
                {
                    'reward_type': 'points',
                    'reward_name': '500 Social Points',
                    'reward_description': 'Social media master',
                    'level_required': None,
                    'points_required': 500,
                    'point_type': 'social',
                    'reward_data': json.dumps({
                        'stat_points': 15,
                        'themes': ['social']
                    }),
                    'icon': '🌟'
                },
            ]
            
            # Insert rewards
            print(f"Inserting {len(rewards)} rewards...")
            inserted = 0
            
            for reward in rewards:
                try:
                    # Check if reward already exists
                    check_sql = """
                        SELECT COUNT(*) FROM rewards 
                        WHERE reward_name = :name 
                        AND (level_required = :level OR (level_required IS NULL AND :level IS NULL))
                        AND (points_required = :points OR (points_required IS NULL AND :points IS NULL))
                    """
                    result = db.session.execute(check_sql, {
                        'name': reward['reward_name'],
                        'level': reward['level_required'],
                        'points': reward['points_required']
                    })
                    exists = result.scalar() > 0
                    
                    if not exists:
                        insert_sql = """
                            INSERT INTO rewards 
                            (reward_type, reward_name, reward_description, level_required, 
                             points_required, point_type, reward_data, icon)
                            VALUES 
                            (:type, :name, :description, :level, :points, :point_type, :data, :icon)
                        """
                        db.session.execute(insert_sql, {
                            'type': reward['reward_type'],
                            'name': reward['reward_name'],
                            'description': reward['reward_description'],
                            'level': reward['level_required'],
                            'points': reward['points_required'],
                            'point_type': reward['point_type'],
                            'data': reward['reward_data'],
                            'icon': reward['icon']
                        })
                        inserted += 1
                        print(f"  ✅ Inserted: {reward['reward_name']}")
                    else:
                        print(f"  ⏭️  Skipped (exists): {reward['reward_name']}")
                except Exception as e:
                    print(f"  ❌ Error inserting {reward['reward_name']}: {e}")
            
            db.session.commit()
            
            print()
            print(f"[OK] Inserted {inserted} new rewards")
            print()
            
            # Show summary
            result = db.session.execute("SELECT COUNT(*) FROM rewards")
            total = result.scalar()
            print(f"Total rewards in database: {total}")
            
            # Show by type
            result = db.session.execute("""
                SELECT reward_type, COUNT(*) 
                FROM rewards 
                GROUP BY reward_type
            """)
            print()
            print("Rewards by type:")
            for row in result:
                print(f"  {row[0]}: {row[1]}")
            
            print()
            print("=" * 70)
            print("[OK] Reward Population Complete!")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to populate rewards: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False


if __name__ == '__main__':
    success = populate_rewards()
    sys.exit(0 if success else 1)
