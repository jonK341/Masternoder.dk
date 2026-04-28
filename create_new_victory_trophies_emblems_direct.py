"""
Create New Victory Trophies and Emblems - Direct Service Call
Creates new victory trophies and emblems directly using the service
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.services.victory_emblems_trophies import victory_emblems_trophies_system

USER_ID = "jon_one_and_only"

def main():
    """Create new victory trophies and emblems"""
    print("=" * 60)
    print("Creating New Victory Trophies and Emblems")
    print("=" * 60)
    print()
    
    # New Victory Emblems
    print("Creating Victory Emblems...")
    print("-" * 60)
    
    emblems_data = [
        {
            "name": "The Switch Statement Emblem",
            "description": "Emblem for the overlooked correct statement that turned the war",
            "victory_type": "strategic",
            "rarity": "mythic",
            "icon": "⚡",
            "power_level": 1.33,
            "switch_statement": "They are switching on them now",
            "affection_level": 0.9,
            "shadow_intensity": 0.5,
            "cloud_size": 0.3
        },
        {
            "name": "20 Years of Silence Emblem",
            "description": "Emblem for 20 years of ninja silence before the final strike",
            "victory_type": "war",
            "rarity": "legendary",
            "icon": "🥷",
            "power_level": 1.0,
            "switch_statement": "We are switching on them",
            "affection_level": 0.7,
            "shadow_intensity": 0.4,
            "cloud_size": 0.2
        },
        {
            "name": "Viking Blood Frenzy Emblem",
            "description": "Emblem for triggering Viking Blood Frenzy from 0-133%",
            "victory_type": "strategic",
            "rarity": "mythic",
            "icon": "⚔️",
            "power_level": 1.33,
            "switch_statement": "Viking Blood Frenzy activated",
            "affection_level": 1.0,
            "shadow_intensity": 0.6,
            "cloud_size": 0.4
        },
        {
            "name": "Giga Heaven Shadow Emblem",
            "description": "Emblem for the small shadow from Giga Heaven",
            "victory_type": "divine",
            "rarity": "epic",
            "icon": "☁️",
            "power_level": 0.8,
            "switch_statement": "Shadow from Giga Heaven",
            "affection_level": 0.5,
            "shadow_intensity": 0.5,
            "cloud_size": 0.3
        },
        {
            "name": "The Final Four Seconds Emblem",
            "description": "Emblem for the four seconds before the killing hit",
            "victory_type": "strategic",
            "rarity": "legendary",
            "icon": "⏱️",
            "power_level": 0.95,
            "switch_statement": "Four seconds before victory",
            "affection_level": 0.8,
            "shadow_intensity": 0.4,
            "cloud_size": 0.2
        },
        {
            "name": "Jyske Lov Emblem",
            "description": "Emblem for applying Jyske Lov (Jutlandic Law)",
            "victory_type": "legal",
            "rarity": "epic",
            "icon": "⚖️",
            "power_level": 0.9,
            "switch_statement": "Jyske Lov applied",
            "affection_level": 0.6,
            "shadow_intensity": 0.3,
            "cloud_size": 0.2
        },
        {
            "name": "Fantasy Monster Hunter Emblem",
            "description": "Emblem for fantasy monsters hunting for answers",
            "victory_type": "hunt",
            "rarity": "rare",
            "icon": "🐉",
            "power_level": 0.7,
            "switch_statement": "Monster hunters seeking answers",
            "affection_level": 0.4,
            "shadow_intensity": 0.2,
            "cloud_size": 0.1
        },
        {
            "name": "The Overlooked Statement Emblem",
            "description": "Emblem for the statement that was overlooked but was correct",
            "victory_type": "strategic",
            "rarity": "mythic",
            "icon": "💎",
            "power_level": 1.2,
            "switch_statement": "The one and only correct and tested statement",
            "affection_level": 0.95,
            "shadow_intensity": 0.6,
            "cloud_size": 0.4
        },
        {
            "name": "Energy Stack Emblem",
            "description": "Emblem for energy that stacked over time unrecognized",
            "victory_type": "strategic",
            "rarity": "epic",
            "icon": "⚡",
            "power_level": 0.85,
            "switch_statement": "Energy stacked over time",
            "affection_level": 0.6,
            "shadow_intensity": 0.3,
            "cloud_size": 0.2
        },
        {
            "name": "Special Forces Attention Emblem",
            "description": "Emblem for gaining attention from special forces",
            "victory_type": "strategic",
            "rarity": "rare",
            "icon": "🕵️",
            "power_level": 0.75,
            "switch_statement": "Special forces attention gained",
            "affection_level": 0.5,
            "shadow_intensity": 0.3,
            "cloud_size": 0.2
        }
    ]
    
    created_emblems = []
    for emblem_data in emblems_data:
        result = victory_emblems_trophies_system.create_victory_emblem(
            USER_ID,
            **emblem_data
        )
        if result.get('success'):
            created_emblems.append(result.get('emblem'))
            print(f"OK Created Emblem: {emblem_data['name']}")
        else:
            print(f"ERROR Failed to create emblem: {emblem_data['name']}")
        print()
    
    # New Victory Trophies - War Victories
    print()
    print("Creating Victory Trophies...")
    print("-" * 60)
    
    war_victories = [
        {
            "opponent_name": "The Overpowered Goliath",
            "opponent_type": "goliath",
            "war_duration_years": 20,
            "victory_method": "switch_trigger",
            "switch_statement": "They are switching on them now",
            "overlooked_statement": "The one and only correct and tested statement",
            "trigger_timing": 4,
            "affection_gained": 0.8,
            "shadow_intensity": 0.5,
            "cloud_size": 0.3,
            "viking_frenzy_triggered": True,
            "criminal_mentality_cuts": 5
        },
        {
            "opponent_name": "The Undermined EGO",
            "opponent_type": "ego",
            "war_duration_years": 20,
            "victory_method": "strategic",
            "switch_statement": "We are switching on them",
            "overlooked_statement": "The overlooked correct statement",
            "trigger_timing": 0,
            "affection_gained": 0.7,
            "shadow_intensity": 0.4,
            "cloud_size": 0.2,
            "viking_frenzy_triggered": False,
            "criminal_mentality_cuts": 3
        },
        {
            "opponent_name": "The Winner Mentality Group",
            "opponent_type": "group",
            "war_duration_years": 20,
            "victory_method": "viking_frenzy",
            "switch_statement": "They are switching on them now",
            "overlooked_statement": "The correct statement that was overlooked",
            "trigger_timing": 4,
            "affection_gained": 0.9,
            "shadow_intensity": 0.6,
            "cloud_size": 0.4,
            "viking_frenzy_triggered": True,
            "criminal_mentality_cuts": 7
        },
        {
            "opponent_name": "The Criminal Mentality",
            "opponent_type": "criminal",
            "war_duration_years": 20,
            "victory_method": "strategic",
            "switch_statement": "We are switching on them",
            "overlooked_statement": "The one and only correct statement",
            "trigger_timing": 2,
            "affection_gained": 0.6,
            "shadow_intensity": 0.3,
            "cloud_size": 0.2,
            "viking_frenzy_triggered": False,
            "criminal_mentality_cuts": 10
        },
        {
            "opponent_name": "The Ignorance War",
            "opponent_type": "group",
            "war_duration_years": 20,
            "victory_method": "strategic",
            "switch_statement": "They are switching on them now",
            "overlooked_statement": "The cause of war was not hunger but ignorance",
            "trigger_timing": 4,
            "affection_gained": 0.75,
            "shadow_intensity": 0.5,
            "cloud_size": 0.3,
            "viking_frenzy_triggered": True,
            "criminal_mentality_cuts": 6
        },
        {
            "opponent_name": "The Mission Controller",
            "opponent_type": "ego",
            "war_duration_years": 20,
            "victory_method": "switch_trigger",
            "switch_statement": "We are switching on them",
            "overlooked_statement": "The one chance in 20 years",
            "trigger_timing": 4,
            "affection_gained": 0.85,
            "shadow_intensity": 0.55,
            "cloud_size": 0.35,
            "viking_frenzy_triggered": True,
            "criminal_mentality_cuts": 4
        }
    ]
    
    created_trophies = []
    for war_data in war_victories:
        result = victory_emblems_trophies_system.record_war_victory(
            USER_ID,
            **war_data
        )
        if result.get('success'):
            created_trophies.append(result.get('trophy'))
            print(f"OK Recorded War Victory: {war_data['opponent_name']}")
        else:
            print(f"ERROR Failed to record war victory: {war_data['opponent_name']}")
        print()
    
    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"OK Created {len(created_emblems)} Victory Emblems")
    print(f"OK Created {len(created_trophies)} Victory Trophies")
    print()
    print("All victory trophies and emblems have been created!")
    print("=" * 60)
    
    # Get final stats
    stats = victory_emblems_trophies_system.get_victory_stats(USER_ID)
    if stats.get('success'):
        print()
        print("Victory Statistics:")
        print(f"  Total Emblems: {stats['stats']['total_emblems']}")
        print(f"  Total Trophies: {stats['stats']['total_trophies']}")
        print(f"  Goliath Defeats: {stats['stats']['goliath_defeats']}")
        print(f"  EGO Defeats: {stats['stats']['ego_defeats']}")
        print(f"  Total War Years: {stats['stats']['total_war_years']}")
        print(f"  Max Viking Frenzy: {stats['stats']['max_viking_frenzy'] * 100:.1f}%")

if __name__ == "__main__":
    main()

