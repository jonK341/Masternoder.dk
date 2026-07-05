/**
 * Enhanced Frontpage Stats Display
 * Shows every detail from unified system
 */

class EnhancedFrontpageStats {
    constructor() {
        this.baseURL = '/api';
        this.userId = this.getUserId();
        this.updateInterval = 5000; // 5 seconds
        this.statsCache = {};
    }

    getUserId() {
        const stored = localStorage.getItem('user_id');
        if (stored) return stored;
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('user_id')) return urlParams.get('user_id');
        return 'default_user';
    }

    /**
     * Load and display all unified stats
     */
    async loadAllUnifiedStats() {
        try {
            // Get unified points + energy
            const unifiedData = await this.getUnifiedData();
            
            // Get game mechanics progress
            const progress = await this.getProgress();
            
            // Get energy status
            const energy = await this.getEnergy();
            
            // Get all points
            const points = await this.getAllPoints();
            
            // Update all displays
            this.updateStatsDisplay(unifiedData, progress, energy, points);
            
            // Cache for quick access
            this.statsCache = {
                unified: unifiedData,
                progress: progress,
                energy: energy,
                points: points,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.error('Error loading unified stats:', error);
        }
    }

    /**
     * Get unified data (points + energy)
     */
    async getUnifiedData() {
        try {
            const response = await fetch(`${this.baseURL}/points/unified/get?user_id=${this.userId}`);
            return await response.json();
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Get progress
     */
    async getProgress() {
        try {
            if (window.GameMechanicsAPI) {
                return await window.GameMechanicsAPI.getProgress(this.userId);
            }
            return {success: false};
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Get energy
     */
    async getEnergy() {
        try {
            if (window.comprehensiveAPI) {
                return await window.comprehensiveAPI.getEnergyStatus();
            }
            return {success: false};
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Get all points
     */
    async getAllPoints() {
        try {
            if (window.comprehensiveAPI) {
                return await window.comprehensiveAPI.getPointsJSON(true);
            }
            return {success: false};
        } catch (error) {
            return {success: false, error: error.message};
        }
    }

    /**
     * Update stats display with all details
     */
    updateStatsDisplay(unifiedData, progress, energy, points) {
        // Update basic stats
        this.updateBasicStats(unifiedData, progress, energy, points);
        
        // Update enhanced stats
        this.updateEnhancedStats(unifiedData, progress, energy, points);
        
        // Update detailed stats section
        this.updateDetailedStats(unifiedData, progress, energy, points);
        
        // Update energy display
        this.updateEnergyDisplay(energy);
        
        // Update points breakdown
        this.updatePointsBreakdown(points);
    }

    /**
     * Update basic stats bar
     */
    updateBasicStats(unifiedData, progress, energy, points) {
        // Videos count
        const videosEl = document.getElementById('stat-videos');
        if (videosEl && points.success) {
            videosEl.textContent = points.points?.videos_created || 0;
        }

        // Achievements
        const achievementsEl = document.getElementById('stat-achievements');
        if (achievementsEl && progress.success) {
            achievementsEl.textContent = progress.data?.achievements_count || 0;
        }

        // Battles
        const battlesEl = document.getElementById('stat-battles');
        if (battlesEl && points.success) {
            battlesEl.textContent = points.points?.battles_won || 0;
        }
    }

    /**
     * Update enhanced stats
     */
    updateEnhancedStats(unifiedData, progress, energy, points) {
        // Total XP
        const xpEl = document.getElementById('stat-total-xp');
        if (xpEl && points.success) {
            xpEl.textContent = points.points?.total_xp || 0;
        }

        // Level
        const levelEl = document.getElementById('stat-level');
        if (levelEl && points.success) {
            levelEl.textContent = points.points?.level || 1;
        }

        // Stats Points
        const pointsEl = document.getElementById('stat-points');
        if (pointsEl && points.success) {
            pointsEl.textContent = points.points?.total || 0;
        }

        // Trophies
        const trophiesEl = document.getElementById('stat-trophies');
        if (trophiesEl && points.success) {
            trophiesEl.textContent = points.points?.trophies || 0;
        }
    }

    /**
     * Update detailed stats section
     */
    updateDetailedStats(unifiedData, progress, energy, points) {
        let detailedSection = document.getElementById('unified-detailed-stats');
        
        if (!detailedSection) {
            // Create detailed stats section
            detailedSection = document.createElement('div');
            detailedSection.id = 'unified-detailed-stats';
            detailedSection.className = 'unified-detailed-stats';
            detailedSection.style.cssText = `
                margin-top: 40px;
                padding: 30px;
                background: rgba(0, 255, 136, 0.05);
                border-radius: var(--radius-xl);
                border: 1px solid rgba(0, 255, 136, 0.2);
            `;
            
            // Insert after enhanced stats
            const enhancedStats = document.querySelector('.stats-enhanced');
            if (enhancedStats) {
                enhancedStats.parentNode.insertBefore(detailedSection, enhancedStats.nextSibling);
            }
        }

        // Build detailed HTML
        let html = '<h3 style="color: var(--primary); margin-bottom: 20px;"><i class="fas fa-chart-line"></i> Unified System Details</h3>';
        
        html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">';
        
        // Points Breakdown
        if (points.success && points.points) {
            html += '<div class="stats-detail-card" style="background: var(--bg-card); padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-primary);">';
            html += '<h4 style="color: var(--primary); margin-bottom: 15px;"><i class="fas fa-coins"></i> Points Breakdown</h4>';
            html += '<div style="display: flex; flex-direction: column; gap: 10px;">';
            
            const pointTypes = ['total', 'xp', 'coins', 'energy_mind', 'energy_power', 'energy_time', 'energy_place'];
            pointTypes.forEach(type => {
                const value = points.points[type] || 0;
                if (value > 0 || type === 'total') {
                    html += `<div style="display: flex; justify-content: space-between;"><span>${type.replace('_', ' ').toUpperCase()}:</span><strong>${value}</strong></div>`;
                }
            });
            
            html += '</div></div>';
        }
        
        // Energy Breakdown
        if (energy.success && energy.energy) {
            html += '<div class="stats-detail-card" style="background: var(--bg-card); padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-primary);">';
            html += '<h4 style="color: var(--primary); margin-bottom: 15px;"><i class="fas fa-bolt"></i> Energy Breakdown</h4>';
            html += '<div style="display: flex; flex-direction: column; gap: 10px;">';
            
            Object.entries(energy.energy).forEach(([type, value]) => {
                if (type !== 'last_update' && typeof value === 'number') {
                    const percentage = (value / 100) * 100;
                    html += `<div style="margin-bottom: 10px;">`;
                    html += `<div style="display: flex; justify-content: space-between; margin-bottom: 5px;">`;
                    html += `<span>${type.toUpperCase()}:</span><strong>${value}/100</strong>`;
                    html += `</div>`;
                    html += `<div style="background: rgba(0, 0, 0, 0.3); height: 8px; border-radius: 4px; overflow: hidden;">`;
                    html += `<div style="background: linear-gradient(90deg, var(--primary), var(--secondary)); height: 100%; width: ${percentage}%; transition: width 0.3s;"></div>`;
                    html += `</div></div>`;
                }
            });
            
            html += '</div></div>';
        }
        
        // Progress Breakdown
        if (progress.success && progress.data) {
            html += '<div class="stats-detail-card" style="background: var(--bg-card); padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-primary);">';
            html += '<h4 style="color: var(--primary); margin-bottom: 15px;"><i class="fas fa-tasks"></i> Progress Breakdown</h4>';
            html += '<div style="display: flex; flex-direction: column; gap: 10px;">';
            
            const progressData = progress.data;
            html += `<div><span>Subjects Completed:</span><strong>${progressData.completed_subjects || 0}</strong></div>`;
            html += `<div><span>Total Progress:</span><strong>${progressData.total_progress || 0}%</strong></div>`;
            html += `<div><span>Functions Used:</span><strong>${progressData.functions_used || 0}</strong></div>`;
            
            html += '</div></div>';
        }
        
        // Unified Summary
        html += '<div class="stats-detail-card" style="background: var(--bg-card); padding: 20px; border-radius: var(--radius-lg); border: 1px solid var(--border-primary);">';
        html += '<h4 style="color: var(--primary); margin-bottom: 15px;"><i class="fas fa-chart-pie"></i> Unified Summary</h4>';
        html += '<div style="display: flex; flex-direction: column; gap: 10px;">';
        
        if (unifiedData.success) {
            html += `<div><span>Total Points:</span><strong>${unifiedData.points?.total || 0}</strong></div>`;
            html += `<div><span>Total Energy:</span><strong>${unifiedData.total_energy || 0}/400</strong></div>`;
            html += `<div><span>Energy %:</span><strong>${((unifiedData.total_energy || 0) / 400 * 100).toFixed(1)}%</strong></div>`;
        }
        
        html += '</div></div>';
        
        html += '</div>';
        
        detailedSection.innerHTML = html;
    }

    /**
     * Update energy display
     */
    updateEnergyDisplay(energy) {
        if (!energy.success) return;
        
        const energyData = energy.energy || {};
        ['mind', 'power', 'time', 'place'].forEach(type => {
            const elements = document.querySelectorAll(`[data-energy="${type}"]`);
            elements.forEach(el => {
                el.textContent = energyData[type] || 0;
            });
        });
    }

    /**
     * Update points breakdown
     */
    updatePointsBreakdown(points) {
        if (!points.success) return;
        
        const pointsData = points.points || {};
        Object.entries(pointsData).forEach(([type, value]) => {
            const elements = document.querySelectorAll(`[data-points="${type}"]`);
            elements.forEach(el => {
                el.textContent = value || 0;
            });
        });
    }

    /**
     * Start auto-update
     */
    startAutoUpdate() {
        // Initial load
        this.loadAllUnifiedStats();
        
        // Auto-update interval
        setInterval(() => {
            this.loadAllUnifiedStats();
        }, this.updateInterval);
    }
}

// Global instance
window.enhancedFrontpageStats = new EnhancedFrontpageStats();

// Start on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.enhancedFrontpageStats.startAutoUpdate();
    });
} else {
    window.enhancedFrontpageStats.startAutoUpdate();
}

