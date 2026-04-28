/**
 * Hardcore AI Metal Magi - Frontend integration
 */
class HardcoreAIMetalMagi {
    constructor() {
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.stats = null;
        this.init();
    }

    async init() {
        await this.loadStats();
        this.displayStats();
        this.startAutoUpdate();
    }

    async loadStats() {
        try {
            const response = await fetch(`/api/hardcore-ai-metal/stats?user_id=${this.userId}`);
            const data = await response.json();
            if (data.success) {
                this.stats = data.stats;
            }
        } catch (error) {
            console.error('Error loading Hardcore AI Metal Magi stats:', error);
        }
    }

    displayStats() {
        if (!this.stats) return;

        // Create or update stats display
        let statsContainer = document.getElementById('hardcore-ai-metal-stats');
        if (!statsContainer) {
            statsContainer = document.createElement('div');
            statsContainer.id = 'hardcore-ai-metal-stats';
            statsContainer.className = 'hardcore-stats-container';
            document.body.appendChild(statsContainer);
        }

        statsContainer.innerHTML = `
            <div class="hardcore-stats-card">
                <h3>🧠⚡ Hardcore AI Metal Magi</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Metal Level</span>
                        <span class="stat-value">${this.stats.metal_level}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">AI Power</span>
                        <span class="stat-value">${this.stats.ai_power}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Magi Points</span>
                        <span class="stat-value">${this.stats.magi_points}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Hardcore Score</span>
                        <span class="stat-value">${this.stats.hardcore_score}</span>
                    </div>
                </div>
                <div class="level-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${this.stats.level_progress}%"></div>
                    </div>
                    <span class="progress-text">${this.stats.magi_points} / ${this.stats.next_level_points} points to next level</span>
                </div>
            </div>
        `;
    }

    startAutoUpdate() {
        // Update stats every 30 seconds
        setInterval(() => {
            this.loadStats().then(() => this.displayStats());
        }, 30000);
    }

    async addPoints(points, source = 'general') {
        try {
            const response = await fetch('/api/hardcore-ai-metal/add-points', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    points: points,
                    source: source
                })
            });
            const data = await response.json();
            if (data.success) {
                await this.loadStats();
                this.displayStats();
                if (data.level_up) {
                    this.showLevelUpNotification(data);
                }
            }
            return data;
        } catch (error) {
            console.error('Error adding Magi points:', error);
            return null;
        }
    }

    showLevelUpNotification(data) {
        if (typeof toast !== 'undefined') {
            toast.success(`🎉 Metal Level ${data.new_level} Unlocked! ${data.unlocked_abilities.join(', ')}`);
        }
    }
}

// Initialize
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.hardcoreAIMetalMagi = new HardcoreAIMetalMagi();
    });
} else {
    window.hardcoreAIMetalMagi = new HardcoreAIMetalMagi();
}

