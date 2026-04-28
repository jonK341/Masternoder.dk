/**
 * Agent Dashboard Data Utility
 * Fetches and formats agent data for dashboard display
 */
class AgentDashboardData {
    constructor(apiBase = '/api') {
        this.apiBase = apiBase;
        this.cache = {};
        this.cacheTimeout = 30000; // 30 seconds
    }

    /**
     * Get all agent data for dashboard
     */
    async getAllAgentData(userId = null) {
        const cacheKey = `all_agents_${userId || 'global'}`;
        
        // Check cache
        if (this.cache[cacheKey] && Date.now() - this.cache[cacheKey].timestamp < this.cacheTimeout) {
            return this.cache[cacheKey].data;
        }

        try {
            // Try to fetch data, but don't fail if endpoints are unavailable
            const data = await Promise.allSettled([
                this.getAgentControllerStatus().catch(() => null),
                this.getAgentSkillsets().catch(() => null),
                this.getUserAgentSkills(userId).catch(() => null),
                this.getAgentStatistics().catch(() => null)
            ]);

            const result = {
                controller: data[0].status === 'fulfilled' ? data[0].value : null,
                skillsets: data[1].status === 'fulfilled' ? data[1].value : null,
                userSkills: data[2].status === 'fulfilled' ? data[2].value : null,
                statistics: data[3].status === 'fulfilled' ? data[3].value : null,
                timestamp: Date.now()
            };

            // If we have at least some data, cache it
            if (result.controller || result.skillsets || result.userSkills || result.statistics) {
                this.cache[cacheKey] = {
                    data: result,
                    timestamp: Date.now()
                };
            }

            return result;
        } catch (error) {
            console.warn('Error fetching agent data (non-critical):', error);
            // Return empty result instead of error - don't break the page
            return {
                controller: null,
                skillsets: null,
                userSkills: null,
                statistics: null,
                timestamp: Date.now()
            };
        }
    }

    /**
     * Get agent controller status
     */
    async getAgentControllerStatus() {
        // Try multiple URL patterns
        const urls = [
            `${this.apiBase}/agent-controller/status`,
            `${this.apiBase}/agents/controller/status`,
            `${this.apiBase}/agent-controller/all-agents`  // Fallback to all-agents if status doesn't work
        ];
        
        for (const url of urls) {
            try {
                console.log(`[Agent Data] Trying: ${url}`);
                const response = await fetch(url);
                console.log(`[Agent Data] Response: ${response.status} ${response.statusText} for ${url}`);
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success || data.controller || data.data) {
                        console.log(`[Agent Data] ✅ Success from ${url}`);
                        return data;
                    }
                } else {
                    console.warn(`[Agent Data] ⚠️  ${response.status} from ${url}`);
                }
            } catch (error) {
                console.warn(`[Agent Data] ❌ Error from ${url}:`, error);
                continue; // Try next URL
            }
        }
        
        console.warn('[Agent Data] ❌ All URL patterns failed for agent controller status');
        return null;
    }

    /**
     * Get agent skillsets
     */
    async getAgentSkillsets() {
        // Try multiple URL patterns
        const urls = [
            `${this.apiBase}/agent/skillset/stats`,
            `${this.apiBase}/agents/skillsets/stats`,
            `${this.apiBase}/agent/skillset/all`  // Fallback
        ];
        
        for (const url of urls) {
            try {
                console.log(`[Agent Data] Trying: ${url}`);
                const response = await fetch(url);
                console.log(`[Agent Data] Response: ${response.status} ${response.statusText} for ${url}`);
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success || data.stats || data.skillsets) {
                        console.log(`[Agent Data] ✅ Success from ${url}`);
                        return data;
                    }
                } else {
                    console.warn(`[Agent Data] ⚠️  ${response.status} from ${url}`);
                }
            } catch (error) {
                console.warn(`[Agent Data] ❌ Error from ${url}:`, error);
                continue; // Try next URL
            }
        }
        
        console.warn('[Agent Data] ❌ All URL patterns failed for agent skillsets');
        return null;
    }

    /**
     * Get user agent skills
     */
    async getUserAgentSkills(userId) {
        if (!userId) return null;
        
        try {
            const response = await fetch(`${this.apiBase}/user/agent-skills/${userId}`);
            if (response.ok) {
                const data = await response.json();
                return data.success ? data : null;
            }
        } catch (error) {
            console.warn('Error fetching user agent skills:', error);
        }
        return null;
    }

    /**
     * Get agent statistics
     */
    async getAgentStatistics() {
        try {
            // Try multiple endpoints with fallbacks
            const endpoints = [
                `${this.apiBase}/agent-controller/status`,
                `${this.apiBase}/agents/controller/status`,
                `${this.apiBase}/agent-controller/all-agents`,
                `${this.apiBase}/agent/skillset/stats`,
                `${this.apiBase}/agents/skillsets/stats`
            ];

            const results = await Promise.allSettled(
                endpoints.map(url => fetch(url).then(r => r.ok ? r.json() : null))
            );

            const stats = {
                totalAgents: 0,
                activeAgents: 0,
                totalSkills: 0,
                agentsByLevel: {},
                topSkills: []
            };

            // Extract stats from results
            results.forEach((result, index) => {
                if (result.status === 'fulfilled' && result.value) {
                    const data = result.value;
                    // First result is agent-controller/status
                    if (index === 0 && data.controller) {
                        stats.totalAgents = data.controller.total_agents || 0;
                        stats.activeAgents = data.controller.active_agents || 0;
                    }
                    // Second result is agent/skillset/stats
                    if (index === 1 && data.stats) {
                        stats.totalSkills = data.stats.total_skills || 0;
                        stats.agentsByLevel = data.stats.agents_by_level || {};  
                        stats.topSkills = data.stats.top_skills || [];
                    }
                }
            });

            return stats;
        } catch (error) {
            console.warn('Error fetching agent statistics:', error);
            return null;
        }
    }

    /**
     * Format agent data for dashboard display
     */
    formatAgentDataForDashboard(agentData) {
        if (!agentData) return null;

        const formatted = {
            summary: {
                totalAgents: agentData.statistics?.totalAgents || agentData.controller?.controller?.total_agents || agentData.controller?.data?.total_agents || 0,
                activeAgents: agentData.statistics?.activeAgents || agentData.controller?.controller?.active_agents || agentData.controller?.data?.active_agents || 0,
                totalSkills: agentData.statistics?.totalSkills || agentData.skillsets?.stats?.total_skills || 0,
                userSkills: agentData.userSkills?.stats?.total_skills || 0
            },
            agents: [],
            userAgentSkills: agentData.userSkills?.skills || agentData.userSkills?.data?.skills || [],
            topSkills: agentData.statistics?.topSkills || agentData.skillsets?.stats?.top_skills || [],
            agentsByLevel: agentData.statistics?.agentsByLevel || agentData.skillsets?.stats?.agents_by_level || {}
        };

        // Extract agent list from controller
        if (agentData.controller?.data?.agents) {
            Object.entries(agentData.controller.data.agents).forEach(([agentId, agentInfo]) => {
                formatted.agents.push({
                    id: agentId,
                    name: agentInfo.data?.name || agentInfo.name || agentId,
                    status: agentInfo.status || 'unknown',
                    level: agentInfo.data?.level || agentInfo.level || 1,
                    experience: agentInfo.data?.experience || agentInfo.experience || 0
                });
            });
        }

        return formatted;
    }

    /**
     * Render agent data card HTML
     */
    renderAgentDataCard(formattedData) {
        if (!formattedData || (!formattedData.summary || formattedData.summary.totalAgents === 0)) {
            return '<div style="padding: 20px; text-align: center; color: rgba(255,255,255,0.7);">' +
                   '<div style="margin-bottom: 10px;">🤖 Agent System</div>' +
                   '<div style="font-size: 0.9em;">Agent data will appear here once endpoints are available</div>' +
                   '<div style="font-size: 0.8em; margin-top: 10px; color: rgba(255,255,255,0.5);">Some endpoints may still be initializing...</div>' +
                   '</div>';
        }

        let html = '<div class="agent-dashboard-section">';
        
        // Summary Stats
        html += '<div class="agent-summary-stats">';
        html += `<div class="agent-stat-item"><span class="stat-label">Total Agents:</span> <span class="stat-value">${formattedData.summary.totalAgents}</span></div>`;
        html += `<div class="agent-stat-item"><span class="stat-label">Active Agents:</span> <span class="stat-value">${formattedData.summary.activeAgents}</span></div>`;
        html += `<div class="agent-stat-item"><span class="stat-label">Total Skills:</span> <span class="stat-value">${formattedData.summary.totalSkills}</span></div>`;
        if (formattedData.summary.userSkills > 0) {
            html += `<div class="agent-stat-item"><span class="stat-label">Your Skills:</span> <span class="stat-value">${formattedData.summary.userSkills}</span></div>`;
        }
        html += '</div>';

        // User Skills
        if (formattedData.userAgentSkills.length > 0) {
            html += '<div class="agent-user-skills">';
            html += '<h4>Your Agent Skills</h4>';
            html += '<div class="skills-list">';
            formattedData.userAgentSkills.forEach(skill => {
                html += `<div class="skill-item">
                    <span class="skill-name">${skill.skill || skill.skill_name || 'Unknown'}</span>
                    <span class="skill-level">Level ${skill.level || 1}</span>
                    ${skill.agent_id ? `<span class="skill-agent">${skill.agent_id}</span>` : ''}
                </div>`;
            });
            html += '</div>';
            html += '</div>';
        }

        // Top Skills
        if (formattedData.topSkills.length > 0) {
            html += '<div class="agent-top-skills">';
            html += '<h4>Top Skills</h4>';
            html += '<div class="top-skills-list">';
            formattedData.topSkills.slice(0, 5).forEach(skill => {
                html += `<div class="top-skill-item">
                    <span class="skill-name">${skill.skill || skill.name || 'Unknown'}</span>
                    <span class="skill-count">${skill.count || 0} agents</span>
                </div>`;
            });
            html += '</div>';
            html += '</div>';
        }

        // Agents List
        if (formattedData.agents.length > 0) {
            html += '<div class="agent-list">';
            html += '<h4>Available Agents</h4>';
            html += '<div class="agents-grid">';
            formattedData.agents.slice(0, 6).forEach(agent => {
                html += `<div class="agent-card">
                    <div class="agent-name">${agent.name}</div>
                    <div class="agent-status ${agent.status}">${agent.status}</div>
                    ${agent.level ? `<div class="agent-level">Level ${agent.level}</div>` : ''}
                </div>`;
            });
            html += '</div>';
            html += '</div>';
        }

        html += '</div>';
        return html;
    }

    /**
     * Load and render agent data in a container
     */
    async loadAndRender(containerId, userId = null) {
        console.log(`[Agent Data] loadAndRender called for container: ${containerId}, userId: ${userId}`);
        
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`[Agent Data] ❌ Container ${containerId} not found`);
            return;
        }

        console.log(`[Agent Data] Container found, loading data...`);
        container.innerHTML = '<div class="loading">Loading agent data...</div>';

        try {
            console.log(`[Agent Data] Fetching all agent data...`);
            const agentData = await this.getAllAgentData(userId);
            console.log(`[Agent Data] Data received:`, agentData);
            
            const formatted = this.formatAgentDataForDashboard(agentData);
            console.log(`[Agent Data] Formatted data:`, formatted);
            
            container.innerHTML = this.renderAgentDataCard(formatted);
            console.log(`[Agent Data] ✅ Rendered successfully`);
        } catch (error) {
            console.error('[Agent Data] ❌ Error loading agent data:', error);
            container.innerHTML = `<div class="error">Error loading agent data: ${error.message}</div>`;
        }
    }
}

// Global instance
window.agentDashboardData = new AgentDashboardData();
