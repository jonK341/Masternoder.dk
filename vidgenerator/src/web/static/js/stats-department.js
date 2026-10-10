/**
 * Stats Department - Comprehensive Stats Management
 * All stats update when points are added
 */

class StatsDepartment {
    constructor() {
        this.stats = {
            generation: {},
            leveling: {},
            monetization: {},
            engagement: {},
            game: {},
            attributes: {}
        };
        this.initialize();
    }
    
    async initialize() {
        await this.loadAllStats();
        this.setupEventListeners();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Add points form
        const addPointsForm = document.getElementById('add-points-form');
        if (addPointsForm) {
            addPointsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.addPoints();
            });
        }
        
        // Listen for stat updates from other components
        document.addEventListener('statUpdated', (event) => {
            this.loadAllStats();
        });
    }
    
    async loadAllStats() {
        try {
            // Try /vidgenerator prefix first, fallback to root
            let response = await fetch('/vidgenerator/api/stats/all');
            
            // If 404, try without prefix
            if (response.status === 404) {
                response = await fetch('/api/stats/all');
            }
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.stats = data.stats || this.stats;
                    this.updateAllDisplays();
                }
            } else {
                console.warn('[StatsDepartment] Failed to load stats:', response.status);
            }
        } catch (error) {
            console.error('[StatsDepartment] Load stats error:', error);
        }
    }
    
    async addPoints() {
        const category = document.getElementById('stat-category').value;
        const statName = document.getElementById('stat-name').value;
        const points = parseInt(document.getElementById('points-amount').value) || 1;
        const updateRelated = document.getElementById('update-related').checked;
        
        if (!category || !statName) {
            alert('Please select a category and enter a stat name');
            return;
        }
        
        try {
            // Try /vidgenerator prefix first, fallback to root
            let response = await fetch('/vidgenerator/api/stats/add-points', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: category,
                    stat_name: statName,
                    points: points,
                    update_related: updateRelated
                })
            });
            
            // If 404, try without prefix
            if (response.status === 404) {
                response = await fetch('/api/stats/add-points', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        category: category,
                        stat_name: statName,
                        points: points,
                        update_related: updateRelated
                    })
                });
            }
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Update local stats
                    this.stats = data.stats || this.stats;
                    this.updateAllDisplays();
                    
                    // Show success message
                    this.showNotification(`Added ${points} points to ${category}.${statName}`, 'success');
                    
                    // Dispatch event for other components
                    document.dispatchEvent(new CustomEvent('statUpdated', {
                        detail: { category, statName, points }
                    }));
                } else {
                    this.showNotification(data.error || 'Failed to add points', 'error');
                }
            } else {
                const error = await response.json();
                this.showNotification(error.error || 'Failed to add points', 'error');
            }
        } catch (error) {
            console.error('[StatsDepartment] Add points error:', error);
            this.showNotification('Error adding points: ' + error.message, 'error');
        }
    }
    
    updateAllDisplays() {
        this.updateCategoryDisplay('generation', this.stats.generation || {});
        this.updateCategoryDisplay('leveling', this.stats.leveling || {});
        this.updateCategoryDisplay('monetization', this.stats.monetization || {});
        this.updateCategoryDisplay('engagement', this.stats.engagement || {});
        this.updateCategoryDisplay('game', this.stats.game || {});
        this.updateCategoryDisplay('attributes', this.stats.attributes || {});
        this.updateSummary();
    }
    
    updateCategoryDisplay(category, stats) {
        const container = document.getElementById(`${category}-stats`);
        if (!container) return;
        
        if (Object.keys(stats).length === 0) {
            container.innerHTML = '<p style="color: rgba(0,255,0,0.5);">No stats available</p>';
            return;
        }
        
        container.innerHTML = Object.entries(stats).map(([key, value]) => {
            let displayValue = value;
            
            // Format different value types
            if (typeof value === 'object' && value !== null) {
                if (Array.isArray(value)) {
                    displayValue = value.length;
                } else {
                    displayValue = JSON.stringify(value);
                }
            } else if (typeof value === 'number') {
                if (value % 1 !== 0) {
                    displayValue = value.toFixed(2);
                }
            }
            
            return `
                <div class="stat-item">
                    <span class="stat-name">${this.formatStatName(key)}</span>
                    <span class="stat-value">${displayValue}</span>
                </div>
            `;
        }).join('');
    }
    
    formatStatName(name) {
        return name
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }
    
    updateSummary() {
        const summaryContainer = document.getElementById('stats-summary');
        if (!summaryContainer) return;
        
        const summary = {
            'Total Generations': this.stats.generation?.total_generations || 0,
            'Current Level': this.stats.leveling?.current_level || 1,
            'Total XP': this.stats.leveling?.total_xp || 0,
            'Days Active': this.stats.engagement?.days_active || 0,
            'Streak Days': this.stats.engagement?.streak_days || 0,
            'Quests Completed': this.stats.game?.quests_completed || 0,
            'Achievements': this.stats.game?.achievements_unlocked || 0,
            'Trophies': this.stats.game?.trophies_earned || 0,
            'Coins Earned': this.stats.monetization?.coins_earned || 0
        };
        
        summaryContainer.innerHTML = Object.entries(summary).map(([label, value]) => `
            <div class="summary-item">
                <div class="summary-label">${label}</div>
                <div class="summary-value">${value}</div>
            </div>
        `).join('');
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? 'rgba(0, 255, 0, 0.2)' : 'rgba(255, 0, 0, 0.2)'};
            border: 2px solid ${type === 'success' ? '#00ff00' : '#ff0000'};
            border-radius: 4px;
            color: ${type === 'success' ? '#00ff00' : '#ff0000'};
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    startAutoRefresh() {
        // Refresh stats every 5 seconds
        setInterval(() => {
            this.loadAllStats();
        }, 5000);
    }
}

// Initialize when DOM is ready
let statsDepartment = null;
document.addEventListener('DOMContentLoaded', () => {
    statsDepartment = new StatsDepartment();
    window.statsDepartment = statsDepartment;
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

