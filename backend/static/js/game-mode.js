/**
 * Stats Page Game Mode
 * Transform stats page into an engaging game with achievements, levels, rewards
 */

class StatsGameMode {
    constructor() {
        this.userLevel = 1;
        this.userXP = 0;
        this.achievements = [];
        this.leaderboard = [];
        this.quests = [];
        this.rewards = [];
        this.gameStats = {
            videosCreated: 0,
            totalWatchTime: 0,
            trophiesEarned: 0,
            streaks: 0,
            perfectGenerations: 0
        };
        
        this.initializeGame();
    }
    
    initializeGame() {
        this.loadGameData();
        this.setupGameUI();
        this.startGameLoop();
        this.setupAchievements();
        this.setupQuests();
    }
    
    loadGameData() {
        // Load from API
        fetch('/vidgenerator/api/stats/user')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    this.userLevel = data.level || 1;
                    this.userXP = data.xp || 0;
                    this.gameStats = {
                        videosCreated: data.videos_created || 0,
                        totalWatchTime: data.total_watch_time || 0,
                        trophiesEarned: data.trophies_earned || 0,
                        streaks: data.streaks || 0,
                        perfectGenerations: data.perfect_generations || 0
                    };
                    this.updateGameUI();
                    this.setupAchievements(); // Update achievements based on new stats
                }
            })
            .catch(err => console.error('[GameMode] Load error:', err));
    }
    
    setupGameUI() {
        // Create game mode container
        const gameContainer = document.createElement('div');
        gameContainer.id = 'game-mode-container';
        gameContainer.className = 'game-mode-container';
        gameContainer.innerHTML = `
            <div class="game-header">
                <h2>🎮 Game Mode</h2>
                <div class="game-level-display">
                    <div class="level-badge">
                        <span class="level-number">${this.userLevel}</span>
                        <span class="level-label">Level</span>
                    </div>
                    <div class="xp-bar-container">
                        <div class="xp-bar" id="xp-bar">
                            <div class="xp-fill" id="xp-fill" style="width: 0%"></div>
                        </div>
                        <span class="xp-text" id="xp-text">0 / 1000 XP</span>
                    </div>
                </div>
            </div>
            
            <div class="game-tabs">
                <button class="game-tab active" data-tab="achievements">🏆 Achievements</button>
                <button class="game-tab" data-tab="quests">📜 Quests</button>
                <button class="game-tab" data-tab="leaderboard">👑 Leaderboard</button>
                <button class="game-tab" data-tab="rewards">🎁 Rewards</button>
                <button class="game-tab" data-tab="frames">🖼️ Frames</button>
            </div>
            
            <div class="game-content">
                <div class="game-tab-content active" id="tab-achievements">
                    <div class="achievements-grid" id="achievements-grid"></div>
                </div>
                <div class="game-tab-content" id="tab-quests">
                    <div class="quests-list" id="quests-list"></div>
                </div>
                <div class="game-tab-content" id="tab-leaderboard">
                    <div class="leaderboard-list" id="leaderboard-list"></div>
                </div>
                <div class="game-tab-content" id="tab-rewards">
                    <div class="rewards-list" id="rewards-list"></div>
                </div>
                <div class="game-tab-content" id="tab-frames">
                    <div class="frames-gallery" id="frames-gallery"></div>
                </div>
            </div>
        `;
        
        // Insert into stats page
        const statsContainer = document.querySelector('.stats-container');
        if (statsContainer) {
            statsContainer.insertBefore(gameContainer, statsContainer.firstChild);
        }
        
        // Setup tab switching
        document.querySelectorAll('.game-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.target.dataset.tab;
                this.switchTab(tabName);
            });
        });
    }
    
    switchTab(tabName) {
        // Update active tab
        document.querySelectorAll('.game-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.game-tab-content').forEach(c => c.classList.remove('active'));
        
        document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');
        document.getElementById(`tab-${tabName}`)?.classList.add('active');
        
        // Load tab content
        if (tabName === 'achievements') this.loadAchievements();
        if (tabName === 'quests') this.loadQuests();
        if (tabName === 'leaderboard') this.loadLeaderboard();
        if (tabName === 'rewards') this.loadRewards();
        if (tabName === 'frames') this.loadFrames();
    }
    
    setupAchievements() {
        this.achievements = [
            {
                id: 'first_video',
                name: 'First Steps',
                description: 'Create your first video',
                icon: '🎬',
                xp: 100,
                unlocked: this.gameStats.videosCreated >= 1
            },
            {
                id: 'video_master',
                name: 'Video Master',
                description: 'Create 10 videos',
                icon: '🎥',
                xp: 500,
                unlocked: this.gameStats.videosCreated >= 10
            },
            {
                id: 'trophy_hunter',
                name: 'Trophy Hunter',
                description: 'Earn 5 trophies',
                icon: '🏆',
                xp: 300,
                unlocked: this.gameStats.trophiesEarned >= 5
            },
            {
                id: 'streak_master',
                name: 'Streak Master',
                description: 'Maintain a 7-day streak',
                icon: '🔥',
                xp: 1000,
                unlocked: this.gameStats.streaks >= 7
            },
            {
                id: 'perfectionist',
                name: 'Perfectionist',
                description: 'Create 5 perfect generations',
                icon: '✨',
                xp: 750,
                unlocked: this.gameStats.perfectGenerations >= 5
            }
        ];
    }
    
    setupQuests() {
        this.quests = [
            {
                id: 'daily_video',
                name: 'Daily Creator',
                description: 'Create a video today',
                reward: 50,
                progress: 0,
                max: 1,
                type: 'daily'
            },
            {
                id: 'watch_time',
                name: 'Viewer',
                description: 'Watch 30 minutes of videos',
                reward: 100,
                progress: 0,
                max: 30,
                type: 'weekly'
            },
            {
                id: 'explore_themes',
                name: 'Theme Explorer',
                description: 'Try 3 different themes',
                reward: 150,
                progress: 0,
                max: 3,
                type: 'weekly'
            }
        ];
    }
    
    loadAchievements() {
        const grid = document.getElementById('achievements-grid');
        if (!grid) return;
        
        grid.innerHTML = this.achievements.map(ach => `
            <div class="achievement-card ${ach.unlocked ? 'unlocked' : 'locked'}">
                <div class="achievement-icon">${ach.icon}</div>
                <div class="achievement-info">
                    <h3>${ach.name}</h3>
                    <p>${ach.description}</p>
                    <div class="achievement-reward">+${ach.xp} XP</div>
                </div>
                ${ach.unlocked ? '<div class="achievement-badge">✓</div>' : ''}
            </div>
        `).join('');
    }
    
    loadQuests() {
        const list = document.getElementById('quests-list');
        if (!list) return;
        
        list.innerHTML = this.quests.map(quest => {
            const progressPercent = (quest.progress / quest.max) * 100;
            return `
                <div class="quest-card">
                    <div class="quest-header">
                        <h3>${quest.name}</h3>
                        <span class="quest-type">${quest.type}</span>
                    </div>
                    <p>${quest.description}</p>
                    <div class="quest-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progressPercent}%"></div>
                        </div>
                        <span class="progress-text">${quest.progress} / ${quest.max}</span>
                    </div>
                    <div class="quest-reward">Reward: +${quest.reward} XP</div>
                </div>
            `;
        }).join('');
    }
    
    loadLeaderboard() {
        const list = document.getElementById('leaderboard-list');
        if (!list) return;
        
        // Fetch leaderboard from API
        fetch('/vidgenerator/api/stats/leaderboard')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    this.leaderboard = data.leaderboard || [];
                    if (this.leaderboard.length === 0) {
                        list.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 2rem;">No leaderboard data available yet. Be the first!</p>';
                    } else {
                        list.innerHTML = this.leaderboard.map((user, index) => `
                            <div class="leaderboard-item ${index < 3 ? 'top-three' : ''}">
                                <div class="rank">#${index + 1}</div>
                                <div class="user-info">
                                    <div class="user-name">${user.name || 'Anonymous'}</div>
                                    <div class="user-stats">Level ${user.level} • ${user.xp} XP • ${user.videos || 0} videos</div>
                                </div>
                                <div class="user-score">${user.score || 0}</div>
                            </div>
                        `).join('');
                    }
                } else {
                    list.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 2rem;">Leaderboard unavailable</p>';
                }
            })
            .catch(err => {
                list.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 2rem;">Leaderboard unavailable</p>';
                console.error('[GameMode] Leaderboard error:', err);
            });
    }
    
    loadRewards() {
        const list = document.getElementById('rewards-list');
        if (!list) return;
        
        // Calculate available rewards based on level
        const availableRewards = this.calculateRewards();
        
        list.innerHTML = availableRewards.map(reward => `
            <div class="reward-card ${reward.claimed ? 'claimed' : ''}">
                <div class="reward-icon">${reward.icon}</div>
                <div class="reward-info">
                    <h3>${reward.name}</h3>
                    <p>${reward.description}</p>
                    <div class="reward-requirement">Level ${reward.requiredLevel} required</div>
                </div>
                ${reward.claimed ? 
                    '<div class="reward-badge">Claimed</div>' : 
                    `<button class="claim-btn" onclick="statsGameMode.claimReward('${reward.id}')">Claim</button>`
                }
            </div>
        `).join('');
    }
    
    loadFrames() {
        const gallery = document.getElementById('frames-gallery');
        if (!gallery) return;
        
        gallery.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 2rem;">Loading frames...</p>';
        
        // Fetch frames from API
        fetch('/vidgenerator/api/stats/frames')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const frames = data.frames || [];
                    if (frames.length === 0) {
                        gallery.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 2rem;">No frames extracted yet. Generate some videos to see frames here!</p>';
                    } else {
                        gallery.innerHTML = frames.map(frame => `
                            <div class="frame-card">
                                <img src="${frame.url}" alt="${frame.title}" onerror="this.parentElement.style.display='none';" />
                                <div class="frame-info">
                                    <h4>${frame.title}</h4>
                                    <p>${frame.source}</p>
                                    <span class="frame-date">${frame.date}</span>
                                </div>
                            </div>
                        `).join('');
                    }
                } else {
                    gallery.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 2rem;">Frames unavailable</p>';
                }
            })
            .catch(err => {
                gallery.innerHTML = '<p style="color: rgba(255,255,255,0.6); text-align: center; padding: 2rem;">Frames unavailable</p>';
                console.error('[GameMode] Frames error:', err);
            });
    }
    
    calculateRewards() {
        return [
            {
                id: 'level_5',
                name: 'Level 5 Badge',
                description: 'Unlock special badge',
                icon: '🎖️',
                requiredLevel: 5,
                claimed: this.userLevel >= 5
            },
            {
                id: 'level_10',
                name: 'Level 10 Title',
                description: 'Unlock "Creator" title',
                icon: '👑',
                requiredLevel: 10,
                claimed: this.userLevel >= 10
            },
            {
                id: 'level_20',
                name: 'Level 20 Theme',
                description: 'Unlock exclusive theme',
                icon: '🎨',
                requiredLevel: 20,
                claimed: this.userLevel >= 20
            }
        ];
    }
    
    async claimReward(rewardId) {
        // Claim reward logic
        console.log(`[GameMode] Claiming reward: ${rewardId}`);
        
        try {
            const userId = this.userId || 'default_user';
            const response = await fetch('/vidgenerator/api/game/rewards/claim', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    reward_id: rewardId
                })
            });
            
            const data = await response.json();
            
            if (data.success || data.status === 'success') {
                console.log(`[GameMode] Reward ${rewardId} claimed successfully`);
                // Show success message
                if (typeof showNotification === 'function') {
                    showNotification('Reward claimed successfully!', 'success');
                }
                // Refresh rewards and user data
                this.loadRewards();
                this.loadUserData();
            } else {
                console.error(`[GameMode] Failed to claim reward: ${data.error || data.message}`);
                if (typeof showNotification === 'function') {
                    showNotification(data.error || data.message || 'Failed to claim reward', 'error');
                }
            }
        } catch (error) {
            console.error(`[GameMode] Error claiming reward: ${error}`);
            // Fallback: mark as claimed locally
            const reward = this.rewards.find(r => r.id === rewardId);
            if (reward) {
                reward.claimed = true;
                this.loadRewards();
            }
        }
    }
    
    updateGameUI() {
        // Update XP bar
        const xpNeeded = this.getXPForLevel(this.userLevel + 1);
        const currentLevelXP = this.getXPForLevel(this.userLevel);
        const progress = ((this.userXP - currentLevelXP) / (xpNeeded - currentLevelXP)) * 100;
        
        const xpFill = document.getElementById('xp-fill');
        const xpText = document.getElementById('xp-text');
        if (xpFill) xpFill.style.width = `${Math.min(100, progress)}%`;
        if (xpText) xpText.textContent = `${this.userXP} / ${xpNeeded} XP`;
        
        // Update level
        const levelNumber = document.querySelector('.level-number');
        if (levelNumber) levelNumber.textContent = this.userLevel;
    }
    
    getXPForLevel(level) {
        // XP formula: 1000 * level^1.5
        return Math.floor(1000 * Math.pow(level, 1.5));
    }
    
    startGameLoop() {
        // Update game stats periodically
        setInterval(() => {
            this.loadGameData();
        }, 30000); // Every 30 seconds
    }
}

// Initialize game mode
let statsGameMode = null;
document.addEventListener('DOMContentLoaded', () => {
    statsGameMode = new StatsGameMode();
    window.statsGameMode = statsGameMode; // Make available globally
});

