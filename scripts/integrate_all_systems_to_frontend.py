#!/usr/bin/env python3
"""
Integrate All Systems to Frontend
Updates frontend pages to use the aggregator and debugger
"""
import os
import re
from typing import List, Dict

FRONTEND_PAGES = [
    "vidgenerator/unified_dashboard/index.html",
    "vidgenerator/leaderboards/index.html",
    "vidgenerator/index.html",
    "vidgenerator/dashboard/index.html",
    "vidgenerator/battle/index.html",
    "vidgenerator/shop/index.html",
    "vidgenerator/profile/index.html",
    "vidgenerator/quests/index.html",
    "vidgenerator/champions-league/index.html",
    "vidgenerator/aggregator/index.html",
]


def add_aggregator_integration(html_content: str, page_type: str) -> str:
    """Add aggregator integration to HTML content"""
    
    # Add aggregator script before closing body tag
    aggregator_script = """
    <!-- System Aggregator Integration -->
    <script>
        const AGGREGATOR_API = '/vidgenerator/api/aggregator';
        
        // Unified data loader using aggregator
        async function loadAllSystemData(userId) {
            try {
                const response = await fetch(`${AGGREGATOR_API}/frontend?user_id=${userId}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        return data.data;
                    }
                }
            } catch (error) {
                console.warn('Aggregator API failed, falling back to individual endpoints:', error);
            }
            return null;
        }
        
        // Update page-specific data
        async function updatePageData(userId) {
            const allData = await loadAllSystemData(userId);
            if (!allData) return;
            
            // Update based on page type
            if (allData.dashboard) {
                updateDashboardData(allData.dashboard);
            }
            if (allData.battle) {
                updateBattleData(allData.battle);
            }
            if (allData.shop) {
                updateShopData(allData.shop);
            }
            if (allData.quest) {
                updateQuestData(allData.quest);
            }
            if (allData.points) {
                updatePointsData(allData.points);
            }
        }
        
        // Helper functions for each page type
        function updateDashboardData(data) {
            if (data.points && data.points.total !== undefined) {
                const pointsEl = document.getElementById('total-points');
                if (pointsEl) pointsEl.textContent = data.points.total;
            }
        }
        
        function updateBattleData(data) {
            if (data.battles && Array.isArray(data.battles)) {
                const battlesEl = document.getElementById('battle-list');
                if (battlesEl) {
                    battlesEl.innerHTML = data.battles.map(b => 
                        `<div class="battle-item">${b.name || 'Battle'}</div>`
                    ).join('');
                }
            }
        }
        
        function updateShopData(data) {
            if (data.items && Array.isArray(data.items)) {
                const itemsEl = document.getElementById('shop-items');
                if (itemsEl) {
                    itemsEl.innerHTML = data.items.map(item => 
                        `<div class="shop-item">${item.name || 'Item'}</div>`
                    ).join('');
                }
            }
        }
        
        function updateQuestData(data) {
            if (data.active_quests && Array.isArray(data.active_quests)) {
                const questsEl = document.getElementById('active-quests');
                if (questsEl) {
                    questsEl.innerHTML = data.active_quests.map(q => 
                        `<div class="quest-item">${q.name || 'Quest'}</div>`
                    ).join('');
                }
            }
        }
        
        function updatePointsData(data) {
            // Update points displays across the page
            const pointsElements = document.querySelectorAll('[data-points]');
            pointsElements.forEach(el => {
                const pointType = el.getAttribute('data-points');
                if (data[pointType] !== undefined) {
                    el.textContent = data[pointType];
                }
            });
        }
        
        // Auto-update on page load
        document.addEventListener('DOMContentLoaded', () => {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            updatePageData(userId);
            
            // Auto-refresh every 30 seconds
            setInterval(() => updatePageData(userId), 30000);
        });
    </script>
    """
    
    # Insert before closing body tag
    if '</body>' in html_content:
        html_content = html_content.replace('</body>', aggregator_script + '\n</body>')
    else:
        html_content += aggregator_script
    
    return html_content


def add_debugger_integration(html_content: str) -> str:
    """Add debugger integration to HTML content"""
    
    debugger_script = """
    <!-- Production Debugger Integration -->
    <script>
        const DEBUGGER_API = '/vidgenerator/api/debug';
        
        // Debug function (only in development)
        function debugSystem(systemName) {
            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
                fetch(`${DEBUGGER_API}/system/${systemName}`)
                    .then(r => r.json())
                    .then(data => {
                        console.log(`[Debug] ${systemName}:`, data);
                    })
                    .catch(e => console.error(`[Debug] Error debugging ${systemName}:`, e));
            }
        }
        
        // Auto-debug on errors (development only)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            window.addEventListener('error', (event) => {
                console.error('[Debug] Page error detected:', event.error);
                // Optionally send to debugger API
            });
        }
    </script>
    """
    
    # Insert before closing body tag
    if '</body>' in html_content:
        html_content = html_content.replace('</body>', debugger_script + '\n</body>')
    else:
        html_content += debugger_script
    
    return html_content


def integrate_frontend_page(file_path: str) -> bool:
    """Integrate aggregator and debugger into a frontend page"""
    try:
        if not os.path.exists(file_path):
            print(f"  [SKIP] {file_path} (not found)")
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already integrated
        if 'System Aggregator Integration' in content:
            print(f"  [SKIP] {file_path} (already integrated)")
            return True
        
        # Determine page type
        page_type = 'dashboard'
        if 'battle' in file_path.lower():
            page_type = 'battle'
        elif 'shop' in file_path.lower():
            page_type = 'shop'
        elif 'quest' in file_path.lower():
            page_type = 'quest'
        elif 'leaderboard' in file_path.lower():
            page_type = 'leaderboard'
        
        # Add integrations
        content = add_aggregator_integration(content, page_type)
        content = add_debugger_integration(content)
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  [OK] {file_path}")
        return True
    
    except Exception as e:
        print(f"  [ERROR] {file_path}: {e}")
        return False


def main():
    """Main integration function"""
    print("="*80)
    print("INTEGRATING ALL SYSTEMS TO FRONTEND")
    print("="*80)
    print()
    
    integrated = 0
    skipped = 0
    errors = 0
    
    for page_path in FRONTEND_PAGES:
        if integrate_frontend_page(page_path):
            integrated += 1
        else:
            if os.path.exists(page_path):
                errors += 1
            else:
                skipped += 1
    
    print()
    print("="*80)
    print("INTEGRATION COMPLETE")
    print("="*80)
    print(f"Integrated: {integrated} pages")
    print(f"Skipped: {skipped} pages")
    print(f"Errors: {errors} pages")
    print()


if __name__ == "__main__":
    main()
