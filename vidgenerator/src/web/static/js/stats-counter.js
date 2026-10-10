/**
 * Stats Counter
 * Tracks all attributes and stats through leveling and generation
 */

class StatsCounter {
    constructor() {
        this.stats = {
            generation: {},
            leveling: {},
            monetization: {},
            engagement: {},
            game: {},
            attributes: {},
            // Keyword foundation stats
            keyword_foundation: {
                power_stat: 0,
                conflict_stat: 0,
                knowledge_stat: 0,
                negative_stat: 0,
                social_stat: 0,
                financial_stat: 0,
                health_stat: 0,
                legal_stat: 0,
                game_mechanics_stat: 0,
                temporal_stat: 0,
                spatial_stat: 0,
                total_power: 0,
                active_keywords: [],
                keyword_categories: {}
            },
            // Points systems
            graduation_points: {
                graduation_points: 0,
                total_earned: 0,
                completed_milestones: 0,
                total_milestones: 0
            },
            chat_points: {
                total_chat_points: 0,
                total_messages: 0,
                current_streak: 0
            }
        };
        this.initializeStatsCounter();
    }
    
    async initializeStatsCounter() {
        await this.loadAllStats();
        this.setupStatsTracking();
        this.updateStatsDisplay();
    }
    
    async loadAllStats() {
        try {
            const response = await fetch('/vidgenerator/api/stats/all');
            if (response.ok) {
                const data = await response.json();
                this.stats = data.stats || this.stats;
                this.updateStatsDisplay();
            }
        } catch (error) {
            console.error('[StatsCounter] Load stats error:', error);
        }
    }
    
    setupStatsTracking() {
        // Track generation stats
        document.addEventListener('generationComplete', (event) => {
            this.updateGenerationStats(event.detail);
        });
        
        // Track leveling stats
        document.addEventListener('xpGained', (event) => {
            this.updateLevelingStats(event.detail);
        });
        
        // Track monetization stats
        document.addEventListener('purchaseComplete', (event) => {
            this.updateMonetizationStats(event.detail);
        });
        
        // Track engagement stats
        this.trackEngagement();
        
        // Track game stats
        document.addEventListener('questComplete', (event) => {
            this.updateGameStats({ quest_completed: true });
        });
        
        document.addEventListener('achievementUnlocked', (event) => {
            this.updateGameStats({ achievement_unlocked: true });
        });
    }
    
    trackEngagement() {
        // Track session start
        const sessionStart = Date.now();
        
        // Track time spent
        setInterval(() => {
            const timeSpent = Math.floor((Date.now() - sessionStart) / 1000);
            this.updateEngagementStats({
                duration: timeSpent,
                is_new_day: this.isNewDay(),
                maintains_streak: true
            });
        }, 60000); // Update every minute
    }
    
    isNewDay() {
        const lastActive = localStorage.getItem('last_active_date');
        const today = new Date().toDateString();
        
        if (lastActive !== today) {
            localStorage.setItem('last_active_date', today);
            return true;
        }
        return false;
    }
    
    async updateGenerationStats(data) {
        await fetch('/vidgenerator/api/stats/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'generation',
                data: data
            })
        });
        
        await this.loadAllStats();
    }
    
    async updateLevelingStats(data) {
        await fetch('/vidgenerator/api/stats/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'leveling',
                data: data
            })
        });
        
        await this.loadAllStats();
    }
    
    async updateMonetizationStats(data) {
        await fetch('/vidgenerator/api/stats/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'monetization',
                data: data
            })
        });
        
        await this.loadAllStats();
    }
    
    async updateEngagementStats(data) {
        await fetch('/vidgenerator/api/stats/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'engagement',
                data: data
            })
        });
        
        await this.loadAllStats();
    }
    
    async updateGameStats(data) {
        await fetch('/vidgenerator/api/stats/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'game',
                data: data
            })
        });
        
        await this.loadAllStats();
    }
    
    updateStatsDisplay() {
        // Update stats display in UI
        const statsContainer = document.getElementById('stats-display');
        if (!statsContainer) return;
        
        const summary = this.getStatsSummary();
        
        statsContainer.innerHTML = `
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Generations</h3>
                    <div class="stat-value">${summary.total_generations}</div>
                </div>
                <div class="stat-card">
                    <h3>Level</h3>
                    <div class="stat-value">${summary.current_level}</div>
                </div>
                <div class="stat-card">
                    <h3>Days Active</h3>
                    <div class="stat-value">${summary.days_active}</div>
                </div>
                <div class="stat-card">
                    <h3>Streak</h3>
                    <div class="stat-value">${summary.streak_days} days</div>
                </div>
                <div class="stat-card">
                    <h3>Quests</h3>
                    <div class="stat-value">${summary.quests_completed}</div>
                </div>
                <div class="stat-card">
                    <h3>Achievements</h3>
                    <div class="stat-value">${summary.achievements_unlocked}</div>
                </div>
            </div>
            <div class="attributes-grid">
                <h3>Attributes</h3>
                ${Object.entries(summary.attributes || {}).map(([attr, value]) => `
                    <div class="attribute-item">
                        <span class="attribute-name">${attr.replace('_', ' ').toUpperCase()}</span>
                        <div class="attribute-bar">
                            <div class="attribute-fill" style="width: ${value}%"></div>
                        </div>
                        <span class="attribute-value">${Math.round(value)}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    getStatsSummary() {
        return {
            total_generations: this.stats.generation?.total_generations || 0,
            current_level: this.stats.leveling?.current_level || 1,
            days_active: this.stats.engagement?.days_active || 0,
            streak_days: this.stats.engagement?.streak_days || 0,
            quests_completed: this.stats.game?.quests_completed || 0,
            achievements_unlocked: this.stats.game?.achievements_unlocked || 0,
            attributes: this.stats.attributes || {}
        };
    }
}

// Initialize
let statsCounter = null;
document.addEventListener('DOMContentLoaded', () => {
    statsCounter = new StatsCounter();
    window.statsCounter = statsCounter;
});

