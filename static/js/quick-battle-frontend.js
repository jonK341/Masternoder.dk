/**
 * Quick Battle Frontend - A+ User Graphic Experience
 * Real-time point updates on every click
 */
class QuickBattleFrontend {
    constructor() {
        this.userId = this.getUserId();
        this.currentBattle = null;
        this.pointsCache = {};
        this.updateInterval = null;
        this.init();
    }
    
    getUserId() {
        // Share the same profile identity as Battle, Game, Lab, and Profile.
        let userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id');
        if (!userId) {
            userId = 'anonymous_' + Date.now();
            localStorage.setItem('game_user_id', userId);
        }
        localStorage.setItem('user_id', userId);
        return userId;
    }
    
    init() {
        // Initialize quick battle UI
        this.createQuickBattleUI();
        
        // Start real-time point updates
        this.startPointUpdates();
        
        // Track clicks for points
        this.trackClicks();
        
        console.log('[QuickBattle] Initialized for user:', this.userId);
    }
    
    createQuickBattleUI() {
        // Find or create quick battle container
        let container = document.getElementById('quick-battle-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'quick-battle-container';
            container.className = 'quick-battle-container';
            container.innerHTML = this.getQuickBattleHTML();
            
            // Insert after hero section or at top of page
            const hero = document.querySelector('.hero');
            if (hero && hero.parentNode) {
                hero.parentNode.insertBefore(container, hero.nextSibling);
            } else {
                document.body.insertBefore(container, document.body.firstChild);
            }
        }
        
        // Add event listeners
        this.attachEventListeners();
    }
    
    getQuickBattleHTML() {
        return `
            <div class="quick-battle-widget" style="
                background: linear-gradient(135deg, rgba(0, 255, 136, 0.1), rgba(0, 212, 255, 0.1));
                border-radius: 20px;
                padding: 30px;
                margin: 20px auto;
                max-width: 800px;
                box-shadow: 0 10px 40px rgba(0, 255, 136, 0.2);
                border: 2px solid rgba(0, 255, 136, 0.3);
            ">
                <h2 style="text-align: center; color: var(--primary); margin-bottom: 20px;">
                    ⚔️ Quick Battle
                </h2>
                
                <div class="battle-stats" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px;">
                    <div class="stat-card" style="background: rgba(0, 255, 136, 0.1); padding: 15px; border-radius: 10px; text-align: center;">
                        <div class="stat-label" style="font-size: 0.9em; color: var(--text-secondary);">Battles</div>
                        <div class="stat-value" id="battle-counter-total" style="font-size: 1.5em; font-weight: bold; color: var(--primary);">0</div>
                    </div>
                    <div class="stat-card" style="background: rgba(0, 255, 136, 0.1); padding: 15px; border-radius: 10px; text-align: center;">
                        <div class="stat-label" style="font-size: 0.9em; color: var(--text-secondary);">Wins</div>
                        <div class="stat-value" id="battle-counter-wins" style="font-size: 1.5em; font-weight: bold; color: #00ff88;">0</div>
                    </div>
                    <div class="stat-card" style="background: rgba(0, 255, 136, 0.1); padding: 15px; border-radius: 10px; text-align: center;">
                        <div class="stat-label" style="font-size: 0.9em; color: var(--text-secondary);">Streak</div>
                        <div class="stat-value" id="battle-streak" style="font-size: 1.5em; font-weight: bold; color: var(--secondary);">0</div>
                    </div>
                    <div class="stat-card" style="background: rgba(0, 255, 136, 0.1); padding: 15px; border-radius: 10px; text-align: center;">
                        <div class="stat-label" style="font-size: 0.9em; color: var(--text-secondary);">Points</div>
                        <div class="stat-value" id="battle-points" style="font-size: 1.5em; font-weight: bold; color: var(--primary);">0</div>
                    </div>
                </div>
                
                <div class="quick-battle-controls" style="text-align: center;">
                    <div class="difficulty-selector" style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 10px; color: var(--text-primary);">Difficulty:</label>
                        <select id="battle-difficulty" style="
                            padding: 10px 20px;
                            border-radius: 10px;
                            border: 2px solid rgba(0, 255, 136, 0.3);
                            background: rgba(0, 0, 0, 0.3);
                            color: var(--text-primary);
                            font-size: 1em;
                            cursor: pointer;
                        ">
                            <option value="easy">Easy</option>
                            <option value="balanced" selected>Balanced</option>
                            <option value="hard">Hard</option>
                        </select>
                    </div>
                    
                    <button id="create-quick-battle-btn" class="btn-create-battle" style="
                        padding: 15px 40px;
                        background: linear-gradient(135deg, var(--primary), var(--secondary));
                        color: #000;
                        border: none;
                        border-radius: 25px;
                        font-size: 1.2em;
                        font-weight: bold;
                        cursor: pointer;
                        transition: all 0.3s;
                        box-shadow: 0 5px 20px rgba(0, 255, 136, 0.3);
                    ">
                        ⚔️ Create Quick Battle
                    </button>
                    
                    <div id="battle-status" style="margin-top: 20px; min-height: 30px;"></div>
                </div>
                
                <div class="intelligence-display" id="intelligence-display" style="
                    margin-top: 20px;
                    padding: 15px;
                    background: rgba(0, 0, 0, 0.2);
                    border-radius: 10px;
                    display: none;
                ">
                    <h3 style="color: var(--primary); margin-bottom: 10px;">Battle Intelligence</h3>
                    <div id="intelligence-content"></div>
                </div>
            </div>
        `;
    }
    
    attachEventListeners() {
        const createBtn = document.getElementById('create-quick-battle-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => this.createQuickBattle());
        }
    }
    
    async createQuickBattle() {
        const difficulty = document.getElementById('battle-difficulty')?.value || 'balanced';
        const statusDiv = document.getElementById('battle-status');
        
        if (statusDiv) {
            statusDiv.innerHTML = '<span style="color: var(--primary);">Creating battle...</span>';
        }
        
        // Track battle participation
        if (window.epicGaming) {
            window.epicGaming.trackActivity('battle_participate', {
                battle_type: 'quick_battle',
                difficulty: difficulty,
                action: 'create'
            });
        }
        
        try {
            const response = await fetch('/api/battle/quick', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    difficulty: difficulty,
                    opponent_type: 'ai'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentBattle = null;
                const result = data.result === 'win' ? 'Victory!' : (data.result === 'loss' ? 'Defeat.' : 'Draw.');
                const delta = (data.points_delta || 0) >= 0 ? `+${data.points_delta || 0}` : `${data.points_delta}`;
                const duel = data.player_move && (data.opponent_move || data.ai_move)
                    ? `<br><span>You: ${data.player_move} · Opponent: ${data.opponent_move || data.ai_move}</span>`
                    : '';
                
                if (statusDiv) {
                    statusDiv.innerHTML = `
                        <span style="color: #00ff88; font-weight: 700;">${result}</span>
                        <br><span>Battle points: ${delta}</span>
                        ${duel}
                        ${data.hunter_xp && data.hunter_xp.xp_awarded ? `<br><span>Hunter XP: +${data.hunter_xp.xp_awarded}</span>` : ''}
                        ${data.ai_commentary ? `<br><br><span>${data.ai_commentary}</span>` : ''}
                    `;
                }
                
                // Show intelligence
                this.displayIntelligence({
                    focus: data.battle_mode || 'quick_battle',
                    recommendations: [data.strategy_tip || data.instant_skirmish_note || 'Pick a stance to control the opening duel.']
                });
                
                // Update points immediately
                this.updateCounters();
                this.updateStreak();
                this.updatePoints();
            } else {
                if (statusDiv) {
                    statusDiv.innerHTML = `<span style="color: #ff4444;">Error: ${data.error || 'Unknown error'}</span>`;
                }
            }
        } catch (error) {
            console.error('[QuickBattle] Error creating battle:', error);
            if (statusDiv) {
                statusDiv.innerHTML = `<span style="color: #ff4444;">Error creating battle</span>`;
            }
        }
    }
    
    async completeBattle(won) {
        // The current API resolves quick battles immediately; keep this method as a compatibility shim.
        await this.createQuickBattle();
    }
    
    async updateCounters() {
        try {
            const response = await fetch(`/api/battle/stats?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success && data.stats) {
                const counter = data.stats;
                const totalEl = document.getElementById('battle-counter-total');
                const winsEl = document.getElementById('battle-counter-wins');
                
                if (totalEl) totalEl.textContent = counter.total_battles || ((counter.wins || 0) + (counter.losses || 0));
                if (winsEl) winsEl.textContent = counter.wins || 0;
            }
        } catch (error) {
            console.error('[QuickBattle] Error updating counters:', error);
        }
    }
    
    async updateStreak() {
        try {
            const response = await fetch(`/api/battle/stats?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success && data.stats) {
                const streak = data.stats;
                const streakEl = document.getElementById('battle-streak');
                
                if (streakEl) {
                    streakEl.textContent = streak.win_streak || 0;
                    streakEl.style.color = (streak.win_streak || 0) > 0 ? '#00ff88' : '#ff4444';
                }
            }
        } catch (error) {
            console.error('[QuickBattle] Error updating streak:', error);
        }
    }
    
    async updatePoints() {
        try {
            // Get points from unified system
            const response = await fetch(`/api/points/all?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success && data.points) {
                const points = data.points || {};
                const battlePoints = points.battle_points || 0;
                const activityPoints = points.activity_points || 0;
                const xp = points.xp_total || points.xp || 0;
                const total = battlePoints + activityPoints + xp;
                
                const pointsEl = document.getElementById('battle-points');
                if (pointsEl) {
                    pointsEl.textContent = total;
                    // Animate update
                    pointsEl.style.transform = 'scale(1.2)';
                    setTimeout(() => {
                        pointsEl.style.transform = 'scale(1)';
                    }, 300);
                }
                
                this.pointsCache = points;
            }
        } catch (error) {
            console.error('[QuickBattle] Error updating points:', error);
        }
    }
    
    displayIntelligence(intelligence) {
        const display = document.getElementById('intelligence-display');
        const content = document.getElementById('intelligence-content');
        
        if (display && content && intelligence) {
            display.style.display = 'block';
            content.innerHTML = `
                <div style="color: var(--text-primary);">
                    <strong>Focus:</strong> ${intelligence.focus || 'Speed'}<br>
                    <strong>Recommendations:</strong>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        ${(intelligence.recommendations || []).map(r => `<li>${r}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
    }
    
    trackClicks() {
        // Track every click for activity points
        document.addEventListener('click', async (e) => {
            // Don't track clicks on battle buttons (they have their own tracking)
            if (e.target.closest('.quick-battle-widget')) {
                return;
            }
            
            // Award activity points for clicks
            try {
                await fetch('/api/activity-points/track', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        visitor_id: this.userId,
                        activity_type: 'click',
                        metadata: {
                            x: e.clientX,
                            y: e.clientY,
                            element: e.target.tagName
                        }
                    })
                });
                
                // Update points immediately
                this.updatePoints();
            } catch (error) {
                // Silent fail - don't interrupt user experience
            }
        });
    }
    
    startPointUpdates() {
        // Update points every 5 seconds
        this.updateInterval = setInterval(() => {
            this.updatePoints();
            this.updateCounters();
            this.updateStreak();
        }, 5000);
        
        // Initial update
        this.updatePoints();
        this.updateCounters();
        this.updateStreak();
    }
    
    stopPointUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
}

// Initialize on page load
let quickBattleFrontend;
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('tab-quick-battle')) {
        return;
    }
    quickBattleFrontend = new QuickBattleFrontend();
});

