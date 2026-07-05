/**
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
                'agent_activity_tracker',
                'agent_adaptive_learner',
                'agent_alert_monitor',
                'agent_anomaly_detector',
                'agent_api_gateway',
                'agent_auto_scaler',
                'agent_behavior_tracker',
                'agent_blockchain_ledger',
                'agent_cloud_sync',
                'agent_code_analyzer',
                'agent_code_formatter',
                'agent_config_scanner',
                'agent_container_orchestrator',
                'agent_database_scanner',
                'agent_decision_maker',
                'agent_dependency_checker',
                'agent_distributed_cache',
                'agent_documentation_generator',
                'agent_endpoint_scanner',
                'agent_error_tracker',
                'agent_event_driven_processor',
                'agent_event_tracker',
                'agent_file_scanner',
                'agent_geofence_manager',
                'agent_gps_coordinator',
                'agent_health_monitor',
                'agent_load_balancer',
                'agent_location_tracker',
                'agent_log_analyzer',
                'agent_memory_debugger',
                'agent_metric_monitor',
                'agent_metric_tracker',
                'agent_microservices',
                'agent_ml_predictor',
                'agent_navigation_system',
                'agent_network_scanner',
                'agent_neural_network',
                'agent_optimization_engine',
                'agent_pattern_matcher',
                'agent_performance_profiler',
                'agent_quantum_processor',
                'agent_resource_monitor',
                'agent_route_optimizer',
                'agent_security_scanner',
                'agent_self_healer',
                'agent_service_mesh',
                'agent_test_generator',
                'agent_uptime_monitor',
                'agent_vulnerability_scanner',
                'agent_workflow_orchestrator',
            ];
            
            const promises = techIds.map(techId => 
                fetch(`${this.baseUrl}/api/agent-tech/${techId}/status`)
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
                `${this.baseUrl}/api/agent-tech/${techId}/${functionName}`,
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
                `${this.baseUrl}/api/agent-tech/${techId}/metrics`
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
            fetch(`${this.baseUrl}/api/agent-tech/${techId}/status`).then(r => r.json()),
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
