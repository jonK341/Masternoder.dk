/**
 * Agent Tracker JavaScript
 * Displays agent activity with record (live) and playback (history) simultaneously
 */
class AgentTracker {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.updateInterval = null;
        this.isRecording = true;
        this.historyLimit = 50;
    }
    
    init() {
        if (!this.container) {
            console.error('Agent tracker container not found:', this.containerId);
            return;
        }
        
        this.render();
        this.startAutoUpdate();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="agent-tracker-container">
                <!-- Live Panel (Recording) -->
                <div class="agent-tracker-panel live">
                    <div class="agent-tracker-header">
                        <h3>🔴 Live Activity</h3>
                        <button class="agent-tracker-refresh" onclick="agentTracker.refresh()">🔄 Refresh</button>
                    </div>
                    <div id="agent-live-content">
                        <div class="loading">Loading live activity...</div>
                    </div>
                </div>
                
                <!-- History Panel (Playback) -->
                <div class="agent-tracker-panel history">
                    <div class="agent-tracker-header">
                        <h3>▶️ Activity History</h3>
                        <button class="agent-tracker-refresh" onclick="agentTracker.refresh()">🔄 Refresh</button>
                    </div>
                    <div id="agent-history-content">
                        <div class="loading">Loading history...</div>
                    </div>
                </div>
            </div>
        `;
        
        this.loadData();
    }
    
    async loadData() {
        try {
            const response = await fetch('/api/agent/tracker/combined');
            const data = await response.json();
            
            if (data.success) {
                this.renderLive(data.live);
                this.renderHistory(data.history);
            } else {
                this.showError('Failed to load agent data');
            }
        } catch (error) {
            console.error('Error loading agent data:', error);
            this.showError('Error loading agent data: ' + error.message);
        }
    }
    
    renderLive(liveData) {
        const liveContent = document.getElementById('agent-live-content');
        if (!liveContent) return;
        
        let html = '';
        
        // Monitoring Status
        if (liveData.monitoring) {
            const monitoring = liveData.monitoring;
            html += `
                <div class="agent-status-section">
                    <div class="agent-status-badge ${monitoring.enabled ? 'active' : 'inactive'}">
                        ${monitoring.enabled ? '🟢 Active' : '🔴 Inactive'}
                    </div>
                    ${monitoring.alerts_count > 0 ? `
                        <div class="agent-status-badge active">
                            ⚠️ ${monitoring.alerts_count} Alerts
                        </div>
                    ` : ''}
                    ${monitoring.should_scan ? `
                        <div class="agent-status-badge active">
                            🔄 Scan Due
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        // Current Activity
        if (liveData.current_activity) {
            const activity = liveData.current_activity;
            html += `
                <div class="agent-activity-item">
                    <div>
                        <div class="activity-name">${activity.name}</div>
                        <div class="activity-time">${this.formatTime(activity.created_at)}</div>
                    </div>
                    <div class="agent-status-badge active">${activity.type}</div>
                </div>
            `;
        }
        
        // Active Missions
        if (liveData.active_missions && liveData.active_missions.length > 0) {
            html += `<h4 style="margin: 15px 0 10px 0; color: #00ff88;">Active Missions</h4>`;
            liveData.active_missions.forEach(mission => {
                const progress = mission.progress || 0;
                html += `
                    <div class="agent-mission-card">
                        <h4>${mission.name}</h4>
                        <div class="mission-progress">
                            <div class="mission-progress-bar" style="width: ${progress}%"></div>
                        </div>
                        <div style="font-size: 0.85em; color: rgba(255,255,255,0.7);">
                            ${mission.tasks ? mission.tasks.length : 0} tasks
                        </div>
                    </div>
                `;
            });
        }
        
        // In-Progress Quests
        if (liveData.in_progress_quests && liveData.in_progress_quests.length > 0) {
            html += `<h4 style="margin: 15px 0 10px 0; color: #00ff88;">Active Quests</h4>`;
            liveData.in_progress_quests.forEach(quest => {
                const progress = this.calculateQuestProgress(quest);
                html += `
                    <div class="agent-quest-card">
                        <h4>${quest.name}</h4>
                        <div class="quest-progress">
                            <div class="quest-progress-bar" style="width: ${progress}%"></div>
                        </div>
                        <div style="font-size: 0.85em; color: rgba(255,255,255,0.7);">
                            ${Object.keys(quest.progress || {}).length} objectives
                        </div>
                    </div>
                `;
            });
        }
        
        // Personality
        if (liveData.personality) {
            const personality = liveData.personality;
            html += `
                <div style="margin-top: 15px;">
                    <h4 style="margin: 0 0 10px 0; color: #00ff88;">Personality</h4>
                    <div class="agent-personality-display">
                        <span class="agent-personality-trait">${personality.personality_type || 'analytical'}</span>
                        ${(personality.traits || []).map(trait => 
                            `<span class="agent-personality-trait">${trait}</span>`
                        ).join('')}
                    </div>
                    <div class="agent-stats-grid">
                        <div class="agent-stat-card">
                            <div class="agent-stat-value">${personality.experience_level || 0}</div>
                            <div class="agent-stat-label">Experience</div>
                        </div>
                        <div class="agent-stat-card">
                            <div class="agent-stat-value">${(personality.achievements || []).length}</div>
                            <div class="agent-stat-label">Achievements</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Recent Activity
        if (liveData.recent_activity && liveData.recent_activity.length > 0) {
            html += `<h4 style="margin: 15px 0 10px 0; color: #00ff88;">Recent Activity</h4>`;
            html += `<div class="agent-activity-stream">`;
            liveData.recent_activity.forEach(activity => {
                html += `
                    <div class="agent-activity-item">
                        <div>
                            <div class="activity-name">${activity.skill || 'Unknown'}</div>
                            <div class="activity-time">${this.formatTime(activity.timestamp)}</div>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }
        
        liveContent.innerHTML = html || '<div style="color: rgba(255,255,255,0.6);">No live activity</div>';
    }
    
    renderHistory(historyData) {
        const historyContent = document.getElementById('agent-history-content');
        if (!historyContent) return;
        
        let html = '';
        
        // Statistics
        if (historyData.statistics) {
            const stats = historyData.statistics;
            html += `
                <div class="agent-stats-grid">
                    <div class="agent-stat-card">
                        <div class="agent-stat-value">${stats.experience_level || 0}</div>
                        <div class="agent-stat-label">Experience</div>
                    </div>
                    <div class="agent-stat-card">
                        <div class="agent-stat-value">${stats.mission_stats?.completed || 0}</div>
                        <div class="agent-stat-label">Missions</div>
                    </div>
                    <div class="agent-stat-card">
                        <div class="agent-stat-value">${stats.quest_stats?.completed || 0}</div>
                        <div class="agent-stat-label">Quests</div>
                    </div>
                    <div class="agent-stat-card">
                        <div class="agent-stat-value">${stats.achievements || 0}</div>
                        <div class="agent-stat-label">Achievements</div>
                    </div>
                </div>
            `;
            
            // Skill Usage
            if (stats.skill_usage) {
                html += `<h4 style="margin: 15px 0 10px 0; color: #00ff88;">Skill Usage</h4>`;
                const topSkills = Object.entries(stats.skill_usage)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 5);
                
                topSkills.forEach(([skill, count]) => {
                    html += `
                        <div class="agent-activity-item">
                            <div>
                                <div class="activity-name">${skill}</div>
                            </div>
                            <div class="agent-status-badge active">${count}x</div>
                        </div>
                    `;
                });
            }
        }
        
        // Completed Missions
        if (historyData.completed_missions && historyData.completed_missions.length > 0) {
            html += `<h4 style="margin: 15px 0 10px 0; color: #00ff88;">Completed Missions</h4>`;
            historyData.completed_missions.slice(0, 5).forEach(mission => {
                html += `
                    <div class="agent-mission-card">
                        <h4>✅ ${mission.name}</h4>
                        <div style="font-size: 0.85em; color: rgba(255,255,255,0.7);">
                            Completed: ${this.formatTime(mission.completed_at)}
                        </div>
                    </div>
                `;
            });
        }
        
        // Completed Quests
        if (historyData.completed_quests && historyData.completed_quests.length > 0) {
            html += `<h4 style="margin: 15px 0 10px 0; color: #00ff88;">Completed Quests</h4>`;
            historyData.completed_quests.slice(0, 5).forEach(quest => {
                html += `
                    <div class="agent-quest-card">
                        <h4>✅ ${quest.name}</h4>
                        <div style="font-size: 0.85em; color: rgba(255,255,255,0.7);">
                            Completed: ${this.formatTime(quest.completed_at)}
                        </div>
                    </div>
                `;
            });
        }
        
        // Skill History
        if (historyData.skill_history && historyData.skill_history.length > 0) {
            html += `<h4 style="margin: 15px 0 10px 0; color: #00ff88;">Recent Skills</h4>`;
            html += `<div class="agent-activity-stream">`;
            historyData.skill_history.slice(0, 10).forEach(entry => {
                html += `
                    <div class="agent-activity-item">
                        <div>
                            <div class="activity-name">${entry.skill || 'Unknown'}</div>
                            <div class="activity-time">${this.formatTime(entry.timestamp)}</div>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }
        
        historyContent.innerHTML = html || '<div style="color: rgba(255,255,255,0.6);">No history available</div>';
    }
    
    calculateQuestProgress(quest) {
        if (!quest.progress || !quest.objectives) return 0;
        const total = quest.objectives.length;
        const completed = Object.values(quest.progress).filter(p => p >= 100).length;
        return total > 0 ? Math.round((completed / total) * 100) : 0;
    }
    
    formatTime(timestamp) {
        if (!timestamp) return 'Never';
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(minutes / 60);
            const days = Math.floor(hours / 24);
            
            if (days > 0) return `${days}d ago`;
            if (hours > 0) return `${hours}h ago`;
            if (minutes > 0) return `${minutes}m ago`;
            return 'Just now';
        } catch {
            return timestamp;
        }
    }
    
    showError(message) {
        const liveContent = document.getElementById('agent-live-content');
        const historyContent = document.getElementById('agent-history-content');
        if (liveContent) liveContent.innerHTML = `<div class="status error">${message}</div>`;
        if (historyContent) historyContent.innerHTML = `<div class="status error">${message}</div>`;
    }
    
    refresh() {
        this.loadData();
    }
    
    startAutoUpdate() {
        // Update every 30 seconds
        this.updateInterval = setInterval(() => {
            this.loadData();
        }, 30000);
    }
    
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
}

// Global instance
let agentTracker = null;

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('agent-tracker')) {
            agentTracker = new AgentTracker('agent-tracker');
            agentTracker.init();
        }
    });
} else {
    if (document.getElementById('agent-tracker')) {
        agentTracker = new AgentTracker('agent-tracker');
        agentTracker.init();
    }
}
