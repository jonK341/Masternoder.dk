/**
 * Historical Timeline Component for Game
 * Shows progression over time with interactive timeline
 */

class GameTimeline {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }
        
        this.options = {
            userId: options.userId || 'default_user',
            baseUrl: options.baseUrl || window.location.origin,
            ...options
        };
        
        this.timelineData = [];
        this.init();
    }
    
    async init() {
        await this.loadTimelineData();
        this.render();
    }
    
    async loadTimelineData() {
        try {
            // Load XP history
            const xpResponse = await fetch(`${this.options.baseUrl}/api/game/hunters/xp-history?user_id=${this.options.userId}&limit=100`);
            const xpData = await xpResponse.json();
            
            // Load achievements
            const achResponse = await fetch(`${this.options.baseUrl}/api/game/achievements?user_id=${this.options.userId}`);
            const achData = await achResponse.json();
            
            // Load milestones
            const milResponse = await fetch(`${this.options.baseUrl}/api/game/milestones?user_id=${this.options.userId}`);
            const milData = await milResponse.json();
            
            // Combine and process timeline data
            this.timelineData = [];
            
            // Add XP events
            if (xpData.success && xpData.history) {
                xpData.history.forEach(entry => {
                    this.timelineData.push({
                        type: 'xp',
                        date: new Date(entry.timestamp || entry.created_at),
                        title: entry.action_type || 'XP Gained',
                        description: `+${entry.xp_awarded || 0} XP`,
                        icon: '⭐',
                        color: '#00ff88'
                    });
                });
            }
            
            // Add achievement unlocks
            if (achData.success && achData.achievements) {
                achData.achievements.filter(a => a.earned).forEach(ach => {
                    this.timelineData.push({
                        type: 'achievement',
                        date: new Date(ach.earned_at || Date.now()),
                        title: ach.name,
                        description: ach.description,
                        icon: '🏆',
                        color: '#ffd700'
                    });
                });
            }
            
            // Add milestone reaches
            if (milData.success && milData.milestones) {
                milData.milestones.filter(m => m.reached).forEach(mil => {
                    this.timelineData.push({
                        type: 'milestone',
                        date: new Date(mil.reached_at || Date.now()),
                        title: mil.name,
                        description: mil.description,
                        icon: '🎯',
                        color: '#00d4ff'
                    });
                });
            }
            
            // Sort by date (newest first)
            this.timelineData.sort((a, b) => b.date - a.date);
            
        } catch (error) {
            console.error('Error loading timeline data:', error);
            this.timelineData = [];
        }
    }
    
    render() {
        if (!this.container) return;
        
        if (this.timelineData.length === 0) {
            this.container.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    <i class="fas fa-history" style="font-size: 3em; margin-bottom: 1rem; opacity: 0.5;"></i>
                    <p>No timeline data available yet. Start playing to build your history!</p>
                </div>
            `;
            return;
        }
        
        // Group by date
        const grouped = this.groupByDate(this.timelineData);
        const dates = Object.keys(grouped).sort((a, b) => new Date(b) - new Date(a));
        
        let html = '<div class="timeline-container">';
        
        dates.forEach((dateStr, dateIndex) => {
            const date = new Date(dateStr);
            const events = grouped[dateStr];
            
            html += `
                <div class="timeline-date-group">
                    <div class="timeline-date-marker">
                        <div class="timeline-date-label">${this.formatDate(date)}</div>
                        <div class="timeline-date-line"></div>
                    </div>
                    <div class="timeline-events">
            `;
            
            events.forEach((event, eventIndex) => {
                html += `
                    <div class="timeline-event" data-type="${event.type}">
                        <div class="timeline-event-icon" style="background: ${event.color}20; border-color: ${event.color};">
                            ${event.icon}
                        </div>
                        <div class="timeline-event-content">
                            <div class="timeline-event-title">${event.title}</div>
                            <div class="timeline-event-description">${event.description}</div>
                            <div class="timeline-event-time">${this.formatTime(event.date)}</div>
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        this.container.innerHTML = html;
    }
    
    groupByDate(events) {
        const grouped = {};
        events.forEach(event => {
            const dateStr = event.date.toISOString().split('T')[0];
            if (!grouped[dateStr]) {
                grouped[dateStr] = [];
            }
            grouped[dateStr].push(event);
        });
        return grouped;
    }
    
    formatDate(date) {
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        
        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric',
                year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined
            });
        }
    }
    
    formatTime(date) {
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
    refresh() {
        this.loadTimelineData().then(() => {
            this.render();
        });
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GameTimeline;
}

