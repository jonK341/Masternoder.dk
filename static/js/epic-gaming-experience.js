/**
 * Epic Gaming Experience - Frontend Integration
 * Makes ALL activities count towards unified progression
 * Includes story, timeline, and continuous point rolling
 */
class EpicGamingExperience {
    constructor(baseUrl = '', userId = 'default_user') {
        this.BASE_URL = baseUrl;
        this.userId = userId;
        this.progress = null;
        this.updateInterval = null;
        this.lastUpdate = null;
        
        // Initialize
        this.init();
    }
    
    async init() {
        console.log('[Epic Gaming] Initializing Epic Gaming Experience...');
        
        // Load initial progress
        await this.loadProgress();
        
        // Start auto-update (every 5 seconds)
        this.startAutoUpdate();
        
        // Track page view
        await this.trackActivity('page_view', { page: window.location.pathname });
        
        // Listen for various activities
        this.setupActivityListeners();
    }
    
    async loadProgress() {
        try {
            const response = await fetch(`${this.BASE_URL}/api/game/epic/progress?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success) {
                this.progress = data;
                this.updateDisplay();
                this.lastUpdate = new Date();
                return data;
            }
        } catch (error) {
            console.error('[Epic Gaming] Error loading progress:', error);
        }
        return null;
    }
    
    async trackActivity(activityType, metadata = {}) {
        try {
            const response = await fetch(`${this.BASE_URL}/api/game/epic/track`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    activity_type: activityType,
                    metadata: metadata
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Update local progress
                if (this.progress) {
                    this.progress.total_xp = data.total_xp;
                    this.progress.current_level = data.new_level;
                    this.progress.level_info = data.level_info;
                    this.progress.level_name = data.level_name;
                }
                
                // Show level up notification
                if (data.level_up) {
                    this.showLevelUp(data);
                }
                
                // Update display
                this.updateDisplay();
                
                return data;
            }
        } catch (error) {
            console.error('[Epic Gaming] Error tracking activity:', error);
        }
        return null;
    }
    
    setupActivityListeners() {
        // Track video generation
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-track="generate"]') || 
                e.target.closest('[data-track="generate"]')) {
                this.trackActivity('generate_video', { source: 'click' });
            }
        });
        
        // Track video watching
        document.addEventListener('play', (e) => {
            if (e.target.tagName === 'VIDEO') {
                this.trackActivity('watch_video', { video_id: e.target.id || 'unknown' });
            }
        }, true);
        
        // Track social actions
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-track="like"]')) {
                this.trackActivity('like_video');
            }
            if (e.target.matches('[data-track="share"]')) {
                this.trackActivity('share_video');
            }
            if (e.target.matches('[data-track="comment"]')) {
                this.trackActivity('comment');
            }
        });
        
        // Track battle participation
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-track="battle"]')) {
                this.trackActivity('battle_participate');
            }
        });
        
        // Track quest completion
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-track="quest"]')) {
                this.trackActivity('quest_complete');
            }
        });
        
        // Track daily login (once per day)
        const lastLogin = localStorage.getItem('epic_gaming_last_login');
        const today = new Date().toDateString();
        if (lastLogin !== today) {
            this.trackActivity('daily_login');
            localStorage.setItem('epic_gaming_last_login', today);
        }
    }
    
    updateDisplay() {
        if (!this.progress) return;
        
        // Update level display
        const levelDisplay = document.getElementById('epic-level-display');
        if (levelDisplay) {
            levelDisplay.innerHTML = `
                <div class="epic-level-info">
                    <div class="epic-level-name">${this.progress.level_name}</div>
                    <div class="epic-level-number">Level ${this.progress.current_level}</div>
                    <div class="epic-xp-total">${this.progress.total_xp.toLocaleString()} XP</div>
                </div>
            `;
        }
        
        // Update progress bar
        const progressBar = document.getElementById('epic-progress-bar');
        if (progressBar && this.progress.level_info) {
            const percent = this.progress.level_info.progress_percent;
            progressBar.style.width = `${percent}%`;
            
            const progressText = document.getElementById('epic-progress-text');
            if (progressText) {
                progressText.textContent = `${this.progress.level_info.xp_progress.toLocaleString()} / ${this.progress.level_info.xp_needed.toLocaleString()} XP`;
            }
        }
        
        // Update timeline
        this.updateTimeline();
        
        // Update story
        this.updateStory();
    }
    
    async updateTimeline() {
        try {
            const response = await fetch(`${this.BASE_URL}/api/game/epic/timeline?user_id=${this.userId}&limit=20`);
            const data = await response.json();
            
            if (data.success && data.timeline) {
                const timelineContainer = document.getElementById('epic-timeline');
                if (timelineContainer) {
                    timelineContainer.innerHTML = data.timeline.map(event => `
                        <div class="timeline-event">
                            <div class="timeline-time">${new Date(event.timestamp).toLocaleTimeString()}</div>
                            <div class="timeline-activity">${this.formatActivity(event.activity)}</div>
                            <div class="timeline-xp">+${event.xp_awarded} XP</div>
                            ${event.level ? `<div class="timeline-level">Level ${event.level}</div>` : ''}
                        </div>
                    `).join('');
                }
            }
        } catch (error) {
            console.error('[Epic Gaming] Error updating timeline:', error);
        }
    }
    
    async updateStory() {
        try {
            const response = await fetch(`${this.BASE_URL}/api/game/epic/story?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success) {
                const storyContainer = document.getElementById('epic-story');
                if (storyContainer) {
                    const currentChapter = data.current_chapter;
                    const chapters = data.chapters;
                    
                    storyContainer.innerHTML = `
                        <div class="story-progress">
                            <div class="story-current">
                                ${currentChapter ? `
                                    <h3>Current Chapter: ${currentChapter.title}</h3>
                                    <p>${currentChapter.description}</p>
                                    <div class="story-reward">Reward: ${currentChapter.xp_reward} XP</div>
                                ` : '<p>All chapters completed! You are a legend!</p>'}
                            </div>
                            <div class="story-chapters">
                                ${chapters.map(chapter => `
                                    <div class="story-chapter ${chapter.unlocked ? 'unlocked' : 'locked'} ${chapter.completed ? 'completed' : ''}">
                                        <div class="chapter-icon">${chapter.unlocked ? '✓' : '🔒'}</div>
                                        <div class="chapter-title">${chapter.title}</div>
                                        <div class="chapter-level">Level ${chapter.level_required}</div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }
            }
        } catch (error) {
            console.error('[Epic Gaming] Error updating story:', error);
        }
    }
    
    formatActivity(activity) {
        const activityNames = {
            'generate_video': 'Created Video',
            'watch_video': 'Watched Video',
            'like_video': 'Liked Video',
            'share_video': 'Shared Video',
            'comment': 'Commented',
            'battle_win': 'Won Battle',
            'battle_participate': 'Joined Battle',
            'quest_complete': 'Completed Quest',
            'achievement_unlock': 'Unlocked Achievement',
            'level_up': 'Leveled Up!',
            'daily_login': 'Daily Login',
            'page_view': 'Viewed Page'
        };
        return activityNames[activity] || activity.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    showLevelUp(data) {
        // Create level up notification
        const notification = document.createElement('div');
        notification.className = 'epic-level-up-notification';
        notification.innerHTML = `
            <div class="level-up-content">
                <div class="level-up-icon">🎉</div>
                <div class="level-up-title">LEVEL UP!</div>
                <div class="level-up-level">Level ${data.new_level}</div>
                <div class="level-up-name">${data.level_name}</div>
                <div class="level-up-bonus">+${data.level_up_bonus} XP Bonus!</div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Remove after animation
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 500);
        }, 3000);
        
        // Play sound if available
        if (window.playSound) {
            window.playSound('level_up');
        }
    }
    
    startAutoUpdate() {
        // Update every 5 seconds
        this.updateInterval = setInterval(() => {
            this.loadProgress();
        }, 5000);
    }
    
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
}

// Auto-initialize if on game or battle page
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (window.location.pathname.includes('/game') || window.location.pathname.includes('/battle')) {
            const userId = localStorage.getItem('game_user_id') || 'default_user';
            window.epicGaming = new EpicGamingExperience('', userId);
        }
    });
} else {
    if (window.location.pathname.includes('/game') || window.location.pathname.includes('/battle')) {
        const userId = localStorage.getItem('game_user_id') || 'default_user';
        window.epicGaming = new EpicGamingExperience('', userId);
    }
}
