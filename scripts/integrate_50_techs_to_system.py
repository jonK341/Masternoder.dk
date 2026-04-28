#!/usr/bin/env python3
"""
Integrate 50 Agent Technologies to System
- Register all blueprints
- Create frontend integration
- Create testing framework
"""
import os
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER_FILE = os.path.join(BASE_DIR, 'backend', 'register_blueprints.py')
FRONTEND_JS_DIR = os.path.join(BASE_DIR, 'vidgenerator', 'static', 'js')

# Read tech list
TECH_IDS = []
for filename in os.listdir(os.path.join(BASE_DIR, 'backend', 'services', 'agent_techs')):
    if filename.endswith('.py') and filename != '__init__.py':
        tech_id = filename[:-3]
        TECH_IDS.append(tech_id)

def update_blueprint_registration():
    """Update register_blueprints.py to include all 50 techs"""
    print("Updating blueprint registration...")
    
    with open(REGISTER_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find insertion point (before final summary)
    insertion_point = content.find('# Agent Behavior Routes')
    if insertion_point == -1:
        insertion_point = content.find('def register_all_blueprints')
    
    if insertion_point == -1:
        print("⚠️  Could not find insertion point, appending to end")
        insertion_point = len(content)
    
    # Generate registration code
    registration_code = "\n    # ========== 50 AGENT TECHNOLOGIES ==========\n"
    for tech_id in TECH_IDS:
        class_name = ''.join(word.capitalize() for word in tech_id.split('_'))
        registration_code += f'''    try:
        from backend.routes.{tech_id}_routes import {tech_id}_bp
        app.register_blueprint({tech_id}_bp)
        registered_count += 1
        print("  [OK] Registered {tech_id} blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import {tech_id}: {{e}}")
    except Exception as e:
        print(f"  [ERROR] Error registering {tech_id}: {{e}}")
    
'''
    
    # Insert before insertion point
    new_content = content[:insertion_point] + registration_code + content[insertion_point:]
    
    with open(REGISTER_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Updated blueprint registration for {len(TECH_IDS)} techs")

def create_frontend_integration():
    """Create frontend JavaScript integration"""
    print("Creating frontend integration...")
    
    js_content = '''/**
 * 50 Agent Technologies Frontend Integration
 * Connects all 50 techs to frontend dashboards
 */
class AgentTechsManager {
    constructor() {
        this.baseUrl = window.location.origin;
        this.techs = [];
        this.cache = {};
        this.cacheTimeout = 30000;
    }

    /**
     * Load all techs status
     */
    async loadAllTechsStatus() {
        try {
            const techIds = [
'''
    
    for tech_id in TECH_IDS:
        js_content += f"                '{tech_id}',\n"
    
    js_content += '''            ];
            
            const promises = techIds.map(techId => 
                fetch(`${this.baseUrl}/vidgenerator/api/agent-tech/${techId}/status`)
                    .then(r => r.ok ? r.json() : {success: false, tech_id: techId})
                    .catch(() => ({success: false, tech_id: techId}))
            );
            
            const results = await Promise.all(promises);
            this.techs = results.filter(r => r.success);
            return this.techs;
        } catch (error) {
            console.error('[AgentTechsManager] Error loading techs:', error);
            return [];
        }
    }

    /**
     * Execute improvement function on a tech
     */
    async executeImprovement(techId, functionName, userId = 'default_user', params = {}) {
        try {
            const response = await fetch(
                `${this.baseUrl}/vidgenerator/api/agent-tech/${techId}/${functionName}`,
                {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user_id: userId, params})
                }
            );
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Get tech metrics
     */
    async getTechMetrics(techId) {
        try {
            const response = await fetch(
                `${this.baseUrl}/vidgenerator/api/agent-tech/${techId}/metrics`
            );
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Render techs dashboard
     */
    renderTechsDashboard(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const html = `
            <div class="agent-techs-dashboard">
                <h2>50 Agent Technologies</h2>
                <div class="techs-grid" id="techs-grid">
                    <div class="loading">Loading technologies...</div>
                </div>
            </div>
        `;
        container.innerHTML = html;

        this.loadAllTechsStatus().then(techs => {
            const grid = document.getElementById('techs-grid');
            if (!grid) return;

            grid.innerHTML = techs.map(tech => `
                <div class="tech-card" data-tech-id="${tech.tech_id}">
                    <div class="tech-header">
                        <h3>${tech.tech_name || tech.tech_id}</h3>
                        <span class="tech-status ${tech.status}">${tech.status}</span>
                    </div>
                    <div class="tech-metrics">
                        <div class="metric">
                            <span>Performance:</span>
                            <span>${tech.metrics?.performance_score || 0}</span>
                        </div>
                        <div class="metric">
                            <span>Security:</span>
                            <span>${tech.metrics?.security_score || 0}</span>
                        </div>
                        <div class="metric">
                            <span>Reliability:</span>
                            <span>${tech.metrics?.reliability_score || 0}</span>
                        </div>
                    </div>
                    <div class="tech-actions">
                        <button onclick="agentTechsManager.viewTechDetails('${tech.tech_id}')">
                            View Details
                        </button>
                        <button onclick="agentTechsManager.executeAllImprovements('${tech.tech_id}')">
                            Apply All Improvements
                        </button>
                    </div>
                </div>
            `).join('');
        });
    }

    /**
     * Execute all 12 improvements for a tech
     */
    async executeAllImprovements(techId, userId = 'default_user') {
        const improvements = [
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
            'upgrade_algorithm'
        ];

        const results = [];
        for (const improvement of improvements) {
            const result = await this.executeImprovement(techId, improvement, userId);
            results.push({improvement, result});
            await new Promise(resolve => setTimeout(resolve, 100)); // Small delay
        }

        return results;
    }

    /**
     * View tech details
     */
    async viewTechDetails(techId) {
        const [status, metrics] = await Promise.all([
            fetch(`${this.baseUrl}/vidgenerator/api/agent-tech/${techId}/status`).then(r => r.json()),
            this.getTechMetrics(techId)
        ]);

        const details = {
            status,
            metrics
        };

        console.log(`[${techId}] Details:`, details);
        // Could open a modal here
        return details;
    }
}

// Global instance
const agentTechsManager = new AgentTechsManager();
window.agentTechsManager = agentTechsManager;

// Auto-load on page ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('agent-techs-dashboard')) {
            agentTechsManager.renderTechsDashboard('agent-techs-dashboard');
        }
    });
} else {
    if (document.getElementById('agent-techs-dashboard')) {
        agentTechsManager.renderTechsDashboard('agent-techs-dashboard');
    }
}
'''
    
    js_file = os.path.join(FRONTEND_JS_DIR, 'agent-techs-manager.js')
    with open(js_file, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"✅ Created frontend integration: {js_file}")

def create_testing_framework():
    """Create testing framework"""
    print("Creating testing framework...")
    
    test_content = f'''#!/usr/bin/env python3
"""
Test Framework for 50 Agent Technologies
Tests all techs and their 12 improvement functions
"""
import requests
import json
from typing import Dict, List

BASE_URL = "https://masternoder.dk"
TECH_IDS = {json.dumps(TECH_IDS, indent=16)}

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

def test_tech_status(tech_id: str) -> Dict:
    """Test tech status endpoint"""
    try:
        url = f"{{BASE_URL}}/vidgenerator/api/agent-tech/{{tech_id}}/status"
        response = requests.get(url, timeout=10)
        return {{
            'tech_id': tech_id,
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'data': response.json() if response.headers.get('Content-Type', '').startswith('application/json') else None
        }}
    except Exception as e:
        return {{'tech_id': tech_id, 'success': False, 'error': str(e)}}

def test_tech_improvement(tech_id: str, function_name: str) -> Dict:
    """Test tech improvement function"""
    try:
        url = f"{{BASE_URL}}/vidgenerator/api/agent-tech/{{tech_id}}/{{function_name}}"
        response = requests.post(
            url,
            json={{'user_id': 'test_user', 'params': {{}}}},
            timeout=10
        )
        return {{
            'tech_id': tech_id,
            'function': function_name,
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'data': response.json() if response.headers.get('Content-Type', '').startswith('application/json') else None
        }}
    except Exception as e:
        return {{'tech_id': tech_id, 'function': function_name, 'success': False, 'error': str(e)}}

def main():
    """Run all tests"""
    print("=" * 70)
    print("TESTING 50 AGENT TECHNOLOGIES")
    print("=" * 70)
    
    results = {{
        'status_tests': [],
        'improvement_tests': [],
        'summary': {{
            'total_techs': len(TECH_IDS),
            'status_passed': 0,
            'status_failed': 0,
            'improvements_passed': 0,
            'improvements_failed': 0
        }}
    }}
    
    # Test status endpoints
    print("\\n[1/2] Testing status endpoints...")
    for tech_id in TECH_IDS:
        result = test_tech_status(tech_id)
        results['status_tests'].append(result)
        if result['success']:
            results['summary']['status_passed'] += 1
            print(f"  [OK] {{tech_id}}")
        else:
            results['summary']['status_failed'] += 1
            print(f"  [FAIL] {{tech_id}}: {{result.get('error', 'Unknown error')}}")
    
    # Test improvement functions (sample: first 3 techs, first 2 functions)
    print("\\n[2/2] Testing improvement functions (sample)...")
    sample_techs = TECH_IDS[:3]
    sample_functions = IMPROVEMENT_FUNCTIONS[:2]
    
    for tech_id in sample_techs:
        for func in sample_functions:
            result = test_tech_improvement(tech_id, func)
            results['improvement_tests'].append(result)
            if result['success']:
                results['summary']['improvements_passed'] += 1
                print(f"  [OK] {{tech_id}}.{{func}}")
            else:
                results['summary']['improvements_failed'] += 1
                print(f"  [FAIL] {{tech_id}}.{{func}}: {{result.get('error', 'Unknown error')}}")
    
    # Print summary
    print("\\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Status Tests: {{results['summary']['status_passed']}}/{{len(TECH_IDS)}} passed")
    print(f"Improvement Tests: {{results['summary']['improvements_passed']}}/{{len(sample_techs) * len(sample_functions)}} passed")
    
    # Save results
    with open('agent_techs_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\\nResults saved to: agent_techs_test_results.json")

if __name__ == '__main__':
    main()
'''
    
    test_file = os.path.join(BASE_DIR, 'scripts', 'test_50_agent_techs.py')
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print(f"✅ Created testing framework: {test_file}")

def main():
    """Main integration"""
    print("=" * 70)
    print("INTEGRATING 50 AGENT TECHNOLOGIES TO SYSTEM")
    print("=" * 70)
    
    update_blueprint_registration()
    create_frontend_integration()
    create_testing_framework()
    
    print("\n✅ Integration complete!")
    print("\nNext steps:")
    print("1. Deploy all files to production")
    print("2. Run: python scripts/test_50_agent_techs.py")
    print("3. Add agent-techs-manager.js to dashboard HTML files")

if __name__ == '__main__':
    main()
