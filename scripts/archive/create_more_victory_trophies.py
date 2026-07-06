"""
Create More Victory Trophies in All Places
Generates diverse victory trophies across different categories and locations
"""
import sys
import os

# Configure stdout for Unicode
sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.victory_emblems_trophies import VictoryEmblemsTrophiesSystem
from datetime import datetime
import uuid

def create_trophies_for_all_places():
    """Create victory trophies for all different places and categories"""
    
    # Initialize the victory system
    victory_system = VictoryEmblemsTrophiesSystem(data_dir='data')
    user_id = 'default_user'
    
    print("=" * 70)
    print("CREATING VICTORY TROPHIES FOR ALL PLACES")
    print("=" * 70)
    print()
    
    trophies_created = []
    
    # 1. Battle System Trophies
    print("Creating Battle System Trophies...")
    battle_trophies = [
        {
            'name': 'Champion of the Arena',
            'description': 'Victory in the main battle arena against overwhelming odds',
            'war_id': f'war_battle_arena_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'goliath',
            'victory_method': 'strategic',
            'museum_category': 'battle_arena',
            'war_duration_years': 5,
            'final_statement': 'Strategy over strength',
            'overlooked_statement': 'The arena rules were always in our favor',
            'trigger_timing_seconds': 10,
            'criminal_mentality_cuts': 3
        },
        {
            'name': 'Battlegrounds Master',
            'description': 'Conquered all battlegrounds through tactical superiority',
            'war_id': f'war_battlegrounds_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'group',
            'victory_method': 'switch_trigger',
            'museum_category': 'battlegrounds',
            'war_duration_years': 8,
            'final_statement': 'We are switching on them now',
            'overlooked_statement': 'Terrain advantage was key',
            'trigger_timing_seconds': 6,
            'criminal_mentality_cuts': 5
        },
        {
            'name': 'Champions League Victor',
            'description': 'Won the Champions League through superior tactics',
            'war_id': f'war_champions_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'ego',
            'victory_method': 'viking_frenzy',
            'museum_category': 'champions_league',
            'war_duration_years': 12,
            'final_statement': 'Viking blood frenzy activated',
            'overlooked_statement': 'The league structure favored us',
            'trigger_timing_seconds': 4,
            'criminal_mentality_cuts': 7
        }
    ]
    
    for trophy_data in battle_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            # Set museum category manually
            trophy = result['trophy']
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == trophy['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # 2. Social System Trophies
    print("Creating Social System Trophies...")
    social_trophies = [
        {
            'name': 'Social Network Dominator',
            'description': 'Conquered the social network through influence and strategy',
            'war_id': f'war_social_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'group',
            'victory_method': 'strategic',
            'museum_category': 'social_victories',
            'war_duration_years': 3,
            'final_statement': 'Influence over numbers',
            'overlooked_statement': 'Network effects were on our side',
            'trigger_timing_seconds': 8,
            'criminal_mentality_cuts': 2
        },
        {
            'name': 'Friendship Forge',
            'description': 'Built unbreakable alliances that defeated all enemies',
            'war_id': f'war_friendship_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'ego',
            'victory_method': 'switch_trigger',
            'museum_category': 'social_alliances',
            'war_duration_years': 6,
            'final_statement': 'Unity is strength',
            'overlooked_statement': 'Alliances were the real power',
            'trigger_timing_seconds': 5,
            'criminal_mentality_cuts': 4
        }
    ]
    
    for trophy_data in social_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == result['trophy']['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # 3. Game System Trophies
    print("Creating Game System Trophies...")
    game_trophies = [
        {
            'name': 'Game Master Supreme',
            'description': 'Mastered all game mechanics and defeated all challenges',
            'war_id': f'war_game_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'goliath',
            'victory_method': 'strategic',
            'museum_category': 'game_achievements',
            'war_duration_years': 15,
            'final_statement': 'Game knowledge is power',
            'overlooked_statement': 'The game rules were always clear',
            'trigger_timing_seconds': 12,
            'criminal_mentality_cuts': 8
        },
        {
            'name': 'Quest Completionist',
            'description': 'Completed all quests and defeated all quest bosses',
            'war_id': f'war_quests_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'group',
            'victory_method': 'viking_frenzy',
            'museum_category': 'quest_victories',
            'war_duration_years': 10,
            'final_statement': 'Quest mastery achieved',
            'overlooked_statement': 'Quest chains were the key',
            'trigger_timing_seconds': 7,
            'criminal_mentality_cuts': 6
        }
    ]
    
    for trophy_data in game_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == result['trophy']['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # 4. Metal System Trophies
    print("Creating Metal System Trophies...")
    metal_trophies = [
        {
            'name': 'Metal Territory Conqueror',
            'description': 'Conquered all metal territories through strategic planning',
            'war_id': f'war_metal_territory_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'goliath',
            'victory_method': 'strategic',
            'museum_category': 'metal_territories',
            'war_duration_years': 7,
            'final_statement': 'Territory control is everything',
            'overlooked_statement': 'Metal resources were abundant',
            'trigger_timing_seconds': 9,
            'criminal_mentality_cuts': 5
        },
        {
            'name': 'Trophy Hunter Legend',
            'description': 'Hunted and collected all legendary trophies',
            'war_id': f'war_trophy_hunt_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'ego',
            'victory_method': 'switch_trigger',
            'museum_category': 'trophy_hunting',
            'war_duration_years': 18,
            'final_statement': 'Hunting mastery complete',
            'overlooked_statement': 'Trophy locations were known',
            'trigger_timing_seconds': 3,
            'criminal_mentality_cuts': 9
        }
    ]
    
    for trophy_data in metal_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == result['trophy']['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # 5. Stats System Trophies
    print("Creating Stats System Trophies...")
    stats_trophies = [
        {
            'name': 'Stats Perfectionist',
            'description': 'Achieved perfect stats across all categories',
            'war_id': f'war_stats_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'ego',
            'victory_method': 'strategic',
            'museum_category': 'stats_achievements',
            'war_duration_years': 4,
            'final_statement': 'Perfect stats achieved',
            'overlooked_statement': 'Stat optimization was the goal',
            'trigger_timing_seconds': 11,
            'criminal_mentality_cuts': 3
        },
        {
            'name': 'Analytics Master',
            'description': 'Mastered all analytics and data systems',
            'war_id': f'war_analytics_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'group',
            'victory_method': 'switch_trigger',
            'museum_category': 'analytics_victories',
            'war_duration_years': 6,
            'final_statement': 'Data is power',
            'overlooked_statement': 'Analytics revealed the truth',
            'trigger_timing_seconds': 8,
            'criminal_mentality_cuts': 4
        }
    ]
    
    for trophy_data in stats_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == result['trophy']['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # 6. Shop System Trophies
    print("Creating Shop System Trophies...")
    shop_trophies = [
        {
            'name': 'Shop Master',
            'description': 'Mastered the shop system and acquired all items',
            'war_id': f'war_shop_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'goliath',
            'victory_method': 'strategic',
            'museum_category': 'shop_achievements',
            'war_duration_years': 5,
            'final_statement': 'Economic mastery',
            'overlooked_statement': 'Shop prices were always fair',
            'trigger_timing_seconds': 10,
            'criminal_mentality_cuts': 3
        }
    ]
    
    for trophy_data in shop_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == result['trophy']['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # 7. Generator System Trophies
    print("Creating Generator System Trophies...")
    generator_trophies = [
        {
            'name': 'Generator Master',
            'description': 'Mastered all video generation techniques',
            'war_id': f'war_generator_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'ego',
            'victory_method': 'viking_frenzy',
            'museum_category': 'generator_achievements',
            'war_duration_years': 9,
            'final_statement': 'Generation mastery',
            'overlooked_statement': 'Generator capabilities were unlimited',
            'trigger_timing_seconds': 6,
            'criminal_mentality_cuts': 5
        }
    ]
    
    for trophy_data in generator_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == result['trophy']['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # 8. Gallery System Trophies
    print("Creating Gallery System Trophies...")
    gallery_trophies = [
        {
            'name': 'Gallery Curator',
            'description': 'Curated the ultimate gallery collection',
            'war_id': f'war_gallery_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'group',
            'victory_method': 'strategic',
            'museum_category': 'gallery_achievements',
            'war_duration_years': 3,
            'final_statement': 'Curatorial excellence',
            'overlooked_statement': 'Gallery organization was key',
            'trigger_timing_seconds': 9,
            'criminal_mentality_cuts': 2
        }
    ]
    
    for trophy_data in gallery_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == result['trophy']['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # 9. Profile System Trophies
    print("Creating Profile System Trophies...")
    profile_trophies = [
        {
            'name': 'Profile Perfection',
            'description': 'Achieved perfect profile across all metrics',
            'war_id': f'war_profile_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'ego',
            'victory_method': 'switch_trigger',
            'museum_category': 'profile_achievements',
            'war_duration_years': 2,
            'final_statement': 'Profile mastery',
            'overlooked_statement': 'Profile optimization was simple',
            'trigger_timing_seconds': 7,
            'criminal_mentality_cuts': 1
        }
    ]
    
    for trophy_data in profile_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == result['trophy']['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # 10. Theme Points Trophies
    print("Creating Theme Points Trophies...")
    theme_trophies = [
        {
            'name': 'Theme Master',
            'description': 'Mastered all theme points and systems',
            'war_id': f'war_theme_{uuid.uuid4().hex[:8]}',
            'opponent_type': 'goliath',
            'victory_method': 'strategic',
            'museum_category': 'theme_achievements',
            'war_duration_years': 6,
            'final_statement': 'Theme mastery complete',
            'overlooked_statement': 'Theme systems were interconnected',
            'trigger_timing_seconds': 8,
            'criminal_mentality_cuts': 4
        }
    ]
    
    for trophy_data in theme_trophies:
        museum_category = trophy_data.pop('museum_category', 'war_victories')
        result = victory_system.create_victory_trophy(
            user_id=user_id,
            **trophy_data
        )
        if result['success']:
            trophy_obj = next((t for t in victory_system.victory_trophies.get(user_id, []) if t.id == result['trophy']['id']), None)
            if trophy_obj:
                trophy_obj.museum_category = museum_category
            result['trophy']['museum_category'] = museum_category
        if result['success']:
            trophies_created.append(result['trophy'])
            print(f"  ✅ Created: {trophy_data['name']}")
        else:
            print(f"  ❌ Failed: {trophy_data['name']}")
    
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Trophies Created: {len(trophies_created)}")
    print()
    print("Categories:")
    categories = {}
    for trophy in trophies_created:
        cat = trophy.get('museum_category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count} trophies")
    
    print()
    # Save data after setting all museum categories
    victory_system._save_data()
    
    print("[OK] All victory trophies created and saved!")
    print(f"Data saved to: {victory_system.data_file}")
    
    return trophies_created

if __name__ == "__main__":
    try:
        trophies = create_trophies_for_all_places()
        print(f"\n✅ Successfully created {len(trophies)} victory trophies!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

