#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan Battle Page Tabs - Check for missing components
"""
import re
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# All tabs from navigation
ALL_TABS = [
    ("overview", "Overview"),
    ("battle", "Battle"),
    ("tournaments", "Tournaments"),
    ("history", "History"),
    ("leaderboard", "Leaderboard"),
    ("intelligence", "🧠 Intelligence"),
    ("resources", "💎 Resources"),
    ("rulebooks", "📚 Rule Books"),
    ("series", "🎯 Series"),
    ("gps", "📍 GPS"),
    ("news", "📰 News"),
    ("peers", "🌐 Peers & Network"),
    ("timepocket", "⏰ Timepocket Real-Time"),
    ("trading", "💎 Trophy Trading & Collectibles"),
    ("missions", "🎯 Missions & Quests"),
    ("ai-research", "🤖 AI Research"),
    ("rewards", "🎁 Rewards"),
    ("technology", "🔬 Technology & Science"),
    ("autoplay", "🎬 Autoplay & Recording"),
    ("social", "👥 Social"),
    ("teams", "👨‍👩‍👧‍👦 Teams & Groups"),
    ("alliances", "🤝 Alliances"),
    ("groups-destroy", "💥 Group Destruction"),
    ("bonus-level", "⭐ Bonus Level (Toons & Pegasus)"),
    ("death-teleport-install", "💀 Death Teleport Install"),
    ("militia-forces", "⚔️ Militia Forces"),
    ("legal-content", "📜 Legal Content"),
    ("tech-hardware", "🔧 Tech & Hardware"),
    ("death-portal", "🚪 Death Portal"),
    ("experience-recount", "🔄 Experience Recount"),
    ("enhanced-system", "⭐ Enhanced Battle System"),
]

def scan_file(filename):
    """Scan the battle page file for components"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    
    results = {
        'tabs_with_content': [],
        'tabs_without_content': [],
        'tabs_with_functions': [],
        'tabs_without_functions': [],
        'missing_functions': [],
        'missing_content': []
    }
    
    # Check for tab content divs
    for tab_id, tab_name in ALL_TABS:
        pattern = f'id="tab-{tab_id}"'
        if pattern in content:
            results['tabs_with_content'].append(tab_id)
        else:
            results['tabs_without_content'].append(tab_id)
            results['missing_content'].append((tab_id, tab_name))
    
    # Check for load functions
    function_mapping = {
        'overview': ['loadBattleStats', 'loadBattlePerformanceOverview'],
        'battle': ['executeFantasyBattle'],
        'tournaments': ['loadTournaments'],
        'history': ['loadBattleHistory'],
        'leaderboard': ['loadBattleLeaderboard'],
        'intelligence': ['loadBattleIntelligence', 'loadIntelligenceHeader', 'loadIntelligenceRecommendations'],
        'resources': ['loadBattleResources', 'loadFantasyPower', 'loadFantasyResources'],
        'rulebooks': ['loadRuleBooks'],
        'series': ['loadBattleSeries'],
        'gps': ['loadBattleGPS'],
        'news': ['loadBattleNews'],
        'peers': ['loadPeerNetwork'],
        'timepocket': ['loadTimepocketRealtime'],
        'trading': ['loadTrophyTrading', 'loadCollectibles'],
        'missions': ['loadDailyQuests', 'loadTimelineMissions', 'loadMTGID'],
        'ai-research': ['loadAIResearch'],
        'rewards': ['loadRewards'],
        'technology': ['loadTechTree', 'loadTechnologyScience'],
        'autoplay': ['loadAutoplayRecording'],
        'social': ['loadSocialData', 'loadFriends'],
        'teams': ['loadMyTeams'],
        'alliances': ['loadMyAlliances'],
        'groups-destroy': ['loadDestructionHistory'],
        'bonus-level': ['loadBonusLevels', 'loadToons', 'loadPegasus'],
        'death-teleport-install': ['loadDeathTeleportInstallations'],
        'militia-forces': ['loadMilitiaForces'],
        'legal-content': ['loadLegalContent'],
        'tech-hardware': ['loadTechHardwareProgress'],
        'death-portal': ['loadDeathPortal'],
        'experience-recount': ['loadExperienceRecount'],
        'enhanced-system': ['loadEnhancedBattleSystem'],
    }
    
    for tab_id, tab_name in ALL_TABS:
        functions = function_mapping.get(tab_id, [])
        has_function = False
        
        for func_name in functions:
            if f'function {func_name}' in content or f'async function {func_name}' in content:
                has_function = True
                break
        
        if has_function:
            results['tabs_with_functions'].append(tab_id)
        else:
            results['tabs_without_functions'].append(tab_id)
            if functions:
                results['missing_functions'].append((tab_id, tab_name, functions))
            else:
                results['missing_functions'].append((tab_id, tab_name, ['[No function defined]']))
    
    return results

def generate_report(results):
    """Generate a comprehensive report"""
    print("=" * 80)
    print("BATTLE PAGE TABS - COMPREHENSIVE SCAN REPORT")
    print("=" * 80)
    print()
    
    # Summary
    total_tabs = len(ALL_TABS)
    tabs_with_content = len(results['tabs_with_content'])
    tabs_with_functions = len(results['tabs_with_functions'])
    
    print("SUMMARY")
    print("-" * 80)
    print(f"Total Tabs: {total_tabs}")
    print(f"Tabs with Content: {tabs_with_content}/{total_tabs} ({tabs_with_content*100//total_tabs}%)")
    print(f"Tabs with Functions: {tabs_with_functions}/{total_tabs} ({tabs_with_functions*100//total_tabs}%)")
    print()
    
    # Missing Content
    print("=" * 80)
    print("MISSING CONTENT DIVS")
    print("=" * 80)
    if results['missing_content']:
        for tab_id, tab_name in results['missing_content']:
            print(f"  [MISSING] {tab_name} (tab-{tab_id})")
    else:
        print("  [OK] All tabs have content divs")
    print()
    
    # Missing Functions
    print("=" * 80)
    print("MISSING/INCOMPLETE FUNCTIONS")
    print("=" * 80)
    if results['missing_functions']:
        for tab_id, tab_name, functions in results['missing_functions']:
            print(f"  [MISSING] {tab_name} (tab-{tab_id})")
            print(f"     Missing functions: {', '.join(functions)}")
    else:
        print("  [OK] All tabs have functions")
    print()
    
    # Status by Tab
    print("=" * 80)
    print("TAB STATUS BREAKDOWN")
    print("=" * 80)
    
    status_categories = {
        'complete': [],
        'missing_content': [],
        'missing_functions': [],
        'missing_both': []
    }
    
    for tab_id, tab_name in ALL_TABS:
        has_content = tab_id in results['tabs_with_content']
        has_function = tab_id in results['tabs_with_functions']
        
        if has_content and has_function:
            status_categories['complete'].append((tab_id, tab_name))
        elif not has_content and not has_function:
            status_categories['missing_both'].append((tab_id, tab_name))
        elif not has_content:
            status_categories['missing_content'].append((tab_id, tab_name))
        elif not has_function:
            status_categories['missing_functions'].append((tab_id, tab_name))
    
    print(f"\n[OK] COMPLETE ({len(status_categories['complete'])} tabs):")
    for tab_id, tab_name in status_categories['complete']:
        print(f"   [OK] {tab_name}")
    
    print(f"\n[WARN] MISSING CONTENT ({len(status_categories['missing_content'])} tabs):")
    for tab_id, tab_name in status_categories['missing_content']:
        print(f"   [WARN] {tab_name}")
    
    print(f"\n[WARN] MISSING FUNCTIONS ({len(status_categories['missing_functions'])} tabs):")
    for tab_id, tab_name in status_categories['missing_functions']:
        print(f"   [WARN] {tab_name}")
    
    print(f"\n[FAIL] MISSING BOTH ({len(status_categories['missing_both'])} tabs):")
    for tab_id, tab_name in status_categories['missing_both']:
        print(f"   [FAIL] {tab_name}")
    
    return status_categories

def generate_todo_list(status_categories):
    """Generate ordered TODO list"""
    print()
    print("=" * 80)
    print("ORDERED TODO LIST - BY PRIORITY")
    print("=" * 80)
    print()
    
    todo_items = []
    
    # Priority 1: Missing both content and functions (critical)
    priority = 1
    for tab_id, tab_name in status_categories['missing_both']:
        todo_items.append({
            'priority': priority,
            'tab_id': tab_id,
            'tab_name': tab_name,
            'task': f'Create complete tab: {tab_name}',
            'actions': [
                f'Create <div id="tab-{tab_id}" class="battle-tab-content">',
                f'Create load function: load{tab_name.replace(" ", "").replace("🧠", "").replace("💎", "").replace("📚", "").replace("🎯", "").replace("📍", "").replace("📰", "").replace("🌐", "").replace("⏰", "").replace("🤖", "").replace("🎁", "").replace("🔬", "").replace("🎬", "").replace("👥", "").replace("👨‍👩‍👧‍👦", "").replace("🤝", "").replace("💥", "").replace("⭐", "").replace("💀", "").replace("⚔️", "").replace("📜", "").replace("🔧", "").replace("🚪", "").replace("🔄", "")}()',
                f'Add tab click handler in tab switching code',
                f'Add API endpoint integration if needed'
            ]
        })
    
    # Priority 2: Missing content only
    priority = 2
    for tab_id, tab_name in status_categories['missing_content']:
        todo_items.append({
            'priority': priority,
            'tab_id': tab_id,
            'tab_name': tab_name,
            'task': f'Create content div for: {tab_name}',
            'actions': [
                f'Create <div id="tab-{tab_id}" class="battle-tab-content">',
                f'Add appropriate UI structure',
                f'Add loading states/skeleton loaders'
            ]
        })
    
    # Priority 3: Missing functions only
    priority = 3
    for tab_id, tab_name in status_categories['missing_functions']:
        todo_items.append({
            'priority': priority,
            'tab_id': tab_id,
            'tab_name': tab_name,
            'task': f'Create load function for: {tab_name}',
            'actions': [
                f'Create async function load{tab_name.replace(" ", "").replace("🧠", "").replace("💎", "").replace("📚", "").replace("🎯", "").replace("📍", "").replace("📰", "").replace("🌐", "").replace("⏰", "").replace("🤖", "").replace("🎁", "").replace("🔬", "").replace("🎬", "").replace("👥", "").replace("👨‍👩‍👧‍👦", "").replace("🤝", "").replace("💥", "").replace("⭐", "").replace("💀", "").replace("⚔️", "").replace("📜", "").replace("🔧", "").replace("🚪", "").replace("🔄", "")}()',
                f'Add API endpoint calls',
                f'Add error handling',
                f'Add data rendering logic'
            ]
        })
    
    # Print TODO list
    for item in todo_items:
        print(f"PRIORITY {item['priority']}: {item['task']}")
        print(f"  Tab ID: {item['tab_id']}")
        print(f"  Actions:")
        for action in item['actions']:
            print(f"    - {action}")
        print()
    
    return todo_items

def safe_print(text):
    """Print text safely handling Unicode"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Remove emojis and special characters for Windows console
        safe_text = text.encode('ascii', 'ignore').decode('ascii')
        print(safe_text)

def main():
    filename = 'vidgenerator/battle/index.html'
    
    # Fix encoding for Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    
    print("Scanning battle page tabs...")
    results = scan_file(filename)
    
    if not results:
        print("Failed to scan file")
        return
    
    status_categories = generate_report(results)
    todo_items = generate_todo_list(status_categories)
    
    # Save to file
    with open('BATTLE_TABS_TODO.md', 'w', encoding='utf-8') as f:
        f.write("# Battle Page Tabs - TODO List\n\n")
        f.write("**Generated:** 2026-01-05\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total Tabs: {len(ALL_TABS)}\n")
        f.write(f"- Complete: {len(status_categories['complete'])}\n")
        f.write(f"- Missing Content: {len(status_categories['missing_content'])}\n")
        f.write(f"- Missing Functions: {len(status_categories['missing_functions'])}\n")
        f.write(f"- Missing Both: {len(status_categories['missing_both'])}\n\n")
        
        f.write("## TODO List (Ordered by Priority)\n\n")
        for item in todo_items:
            f.write(f"### Priority {item['priority']}: {item['task']}\n\n")
            f.write(f"**Tab:** {item['tab_name']} (`{item['tab_id']}`)\n\n")
            f.write("**Actions:**\n")
            for action in item['actions']:
                f.write(f"- {action}\n")
            f.write("\n")
    
    print(f"\n[OK] Report saved to: BATTLE_TABS_TODO.md")

if __name__ == '__main__':
    main()
