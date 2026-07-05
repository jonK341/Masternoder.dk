/**
 * Stats Achievements Tracker
 * Tracks all stats and awards one-time rewards/achievements
 * Ensures each stat achievement is only counted once per user
 */

class StatsAchievementsTracker {
    constructor() {
        this.baseURL = '/api';
        this.userId = this.getUserId();
        this.achievedStats = new Set(); // Track which stats have been achieved
        this.statsCache = {};
        this.updateInterval = 30000; // 30 seconds (reduced load on server)
        this.isInitialized = false;
    }

    getUserId() {
        const stored = localStorage.getItem('game_user_id') || localStorage.getItem('user_id');
        if (stored) return stored;
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('user_id')) return urlParams.get('user_id');
        return 'default_user';
    }

    /**
     * Initialize the tracker
     */
    async initialize() {
        if (this.isInitialized) return;
        
        try {
            // Load previously achieved stats from localStorage
            this.loadAchievedStats();
            
            // Start tracking
            await this.trackAllStats();
            
            // Set up periodic updates
            setInterval(() => this.trackAllStats(), this.updateInterval);
            
            this.isInitialized = true;
            console.log('[StatsTracker] Initialized');
        } catch (error) {
            console.error('[StatsTracker] Initialization error:', error);
        }
    }

    /**
     * Load achieved stats from localStorage
     */
    loadAchievedStats() {
        try {
            const stored = localStorage.getItem(`stats_achievements_${this.userId}`);
            if (stored) {
                const achieved = JSON.parse(stored);
                this.achievedStats = new Set(achieved);
            }
        } catch (error) {
            console.error('[StatsTracker] Error loading achieved stats:', error);
        }
    }

    /**
     * Save achieved stats to localStorage
     */
    saveAchievedStats() {
        try {
            localStorage.setItem(
                `stats_achievements_${this.userId}`,
                JSON.stringify(Array.from(this.achievedStats))
            );
        } catch (error) {
            console.error('[StatsTracker] Error saving achieved stats:', error);
        }
    }

    /**
     * Track all stats and check for achievements
     */
    async trackAllStats() {
        try {
            // Fetch all stats from various endpoints
            const stats = await this.fetchAllStats();
            
            // Check each stat category for achievements
            await this.checkStatAchievements(stats);
            
            // Cache stats
            this.statsCache = stats;
        } catch (error) {
            console.error('[StatsTracker] Error tracking stats:', error);
        }
    }

    /**
     * Fetch all stats from API endpoints in parallel (faster page load).
     */
    async fetchAllStats() {
        const stats = {
            videos: {},
            achievements: {},
            battles: {},
            points: {},
            xp: {},
            trophies: {},
            milestones: {},
            activity: {},
            social: {},
            generation: {},
            shop: {},
            game: {}
        };

        const uid = encodeURIComponent(this.userId);
        const base = this.baseURL;

        const [videosRes, gameRes, achRes, battleRes, pointsRes, trophiesRes, milestonesRes] = await Promise.allSettled([
            fetch(`${base}/stats/summary?user_id=${uid}`),
            fetch(`${base}/game/stats?user_id=${uid}`),
            fetch(`${base}/game/achievements?user_id=${uid}`),
            fetch(`${base}/battle/stats?user_id=${uid}`),
            fetch(`${base}/points/all?user_id=${uid}`),
            fetch(`${base}/stats/trophies?user_id=${uid}`),
            fetch(`${base}/game/milestones?user_id=${uid}`)
        ]);

        if (videosRes.status === 'fulfilled' && videosRes.value.ok) {
            try {
                const data = await videosRes.value.json();
                stats.videos = { total: data.total_videos || 0, completed: data.completed_videos || 0, success_rate: data.success_rate || 0 };
            } catch (_) {}
        }
        if (gameRes.status === 'fulfilled' && gameRes.value.ok) {
            try {
                const data = await gameRes.value.json();
                stats.game = data.stats || {};
                stats.xp = data.stats?.xp || {};
            } catch (_) {}
        }
        if (achRes.status === 'fulfilled' && achRes.value.ok) {
            try {
                const data = await achRes.value.json();
                stats.achievements = { total: data.total_count || 0, earned: data.earned_count || 0, list: data.achievements || [] };
            } catch (_) {}
        }
        if (battleRes.status === 'fulfilled' && battleRes.value.ok) {
            try {
                const data = await battleRes.value.json();
                stats.battles = data.stats || {};
            } catch (_) {}
        }
        if (pointsRes.status === 'fulfilled' && pointsRes.value.ok) {
            try {
                const data = await pointsRes.value.json();
                stats.points = data.points || {};
            } catch (_) {}
        }
        if (trophiesRes.status === 'fulfilled' && trophiesRes.value.ok) {
            try {
                const data = await trophiesRes.value.json();
                stats.trophies = { total: data.allTime?.length || 0, weekly: data.weekly?.length || 0 };
            } catch (_) {}
        }
        if (milestonesRes.status === 'fulfilled' && milestonesRes.value.ok) {
            try {
                const data = await milestonesRes.value.json();
                stats.milestones = { total: data.milestones?.length || 0, reached: data.milestones?.filter(m => m.reached)?.length || 0 };
            } catch (_) {}
        }

        return stats;
    }

    /**
     * Check stats for achievements and award rewards
     */
    async checkStatAchievements(stats) {
        const achievements = [];

        // Video achievements
        achievements.push(...this.checkVideoAchievements(stats.videos));
        
        // Achievement achievements
        achievements.push(...this.checkAchievementAchievements(stats.achievements));
        
        // Battle achievements
        achievements.push(...this.checkBattleAchievements(stats.battles));
        
        // Points achievements
        achievements.push(...this.checkPointsAchievements(stats.points));
        
        // XP achievements
        achievements.push(...this.checkXPAchievements(stats.xp));
        
        // Trophy achievements
        achievements.push(...this.checkTrophyAchievements(stats.trophies));
        
        // Milestone achievements
        achievements.push(...this.checkMilestoneAchievements(stats.milestones));

        // Award rewards for new achievements
        for (const achievement of achievements) {
            if (!this.achievedStats.has(achievement.id)) {
                await this.awardAchievementReward(achievement);
                this.achievedStats.add(achievement.id);
                this.saveAchievedStats();
            }
        }
    }

    /**
     * Check video stats for achievements
     */
    checkVideoAchievements(videos) {
        const achievements = [];
        const total = videos.total || 0;
        const completed = videos.completed || 0;

        // First video
        if (total >= 1 && !this.achievedStats.has('stat_video_first')) {
            achievements.push({
                id: 'stat_video_first',
                name: 'First Video',
                description: 'Created your first video',
                points: 100,
                category: 'videos'
            });
        }

        // 10 videos
        if (total >= 10 && !this.achievedStats.has('stat_video_10')) {
            achievements.push({
                id: 'stat_video_10',
                name: 'Video Creator',
                description: 'Created 10 videos',
                points: 500,
                category: 'videos'
            });
        }

        // 50 videos
        if (total >= 50 && !this.achievedStats.has('stat_video_50')) {
            achievements.push({
                id: 'stat_video_50',
                name: 'Video Master',
                description: 'Created 50 videos',
                points: 2000,
                category: 'videos'
            });
        }

        // 100 videos
        if (total >= 100 && !this.achievedStats.has('stat_video_100')) {
            achievements.push({
                id: 'stat_video_100',
                name: 'Video Legend',
                description: 'Created 100 videos',
                points: 5000,
                category: 'videos'
            });
        }

        // First completed video
        if (completed >= 1 && !this.achievedStats.has('stat_video_completed_first')) {
            achievements.push({
                id: 'stat_video_completed_first',
                name: 'First Completion',
                description: 'Completed your first video',
                points: 150,
                category: 'videos'
            });
        }

        return achievements;
    }

    /**
     * Check achievement stats for achievements
     */
    checkAchievementAchievements(achievements) {
        const achieved = [];
        const total = achievements.total || 0;
        const earned = achievements.earned || 0;

        // First achievement
        if (earned >= 1 && !this.achievedStats.has('stat_achievement_first')) {
            achieved.push({
                id: 'stat_achievement_first',
                name: 'First Achievement',
                description: 'Earned your first achievement',
                points: 50,
                category: 'achievements'
            });
        }

        // 10 achievements
        if (earned >= 10 && !this.achievedStats.has('stat_achievement_10')) {
            achieved.push({
                id: 'stat_achievement_10',
                name: 'Achievement Collector',
                description: 'Earned 10 achievements',
                points: 500,
                category: 'achievements'
            });
        }

        // 25 achievements
        if (earned >= 25 && !this.achievedStats.has('stat_achievement_25')) {
            achieved.push({
                id: 'stat_achievement_25',
                name: 'Achievement Master',
                description: 'Earned 25 achievements',
                points: 1500,
                category: 'achievements'
            });
        }

        return achieved;
    }

    /**
     * Check battle stats for achievements
     */
    checkBattleAchievements(battles) {
        const achieved = [];
        const wins = battles.wins || 0;
        const total = battles.total_battles || 0;
        const winRate = battles.win_rate || 0;

        // First battle
        if (total >= 1 && !this.achievedStats.has('stat_battle_first')) {
            achieved.push({
                id: 'stat_battle_first',
                name: 'First Battle',
                description: 'Participated in your first battle',
                points: 50,
                category: 'battles'
            });
        }

        // First win
        if (wins >= 1 && !this.achievedStats.has('stat_battle_win_first')) {
            achieved.push({
                id: 'stat_battle_win_first',
                name: 'First Victory',
                description: 'Won your first battle',
                points: 100,
                category: 'battles'
            });
        }

        // 10 wins
        if (wins >= 10 && !this.achievedStats.has('stat_battle_win_10')) {
            achieved.push({
                id: 'stat_battle_win_10',
                name: 'Battle Warrior',
                description: 'Won 10 battles',
                points: 500,
                category: 'battles'
            });
        }

        // 50 wins
        if (wins >= 50 && !this.achievedStats.has('stat_battle_win_50')) {
            achieved.push({
                id: 'stat_battle_win_50',
                name: 'Battle Champion',
                description: 'Won 50 battles',
                points: 2000,
                category: 'battles'
            });
        }

        // High win rate
        if (winRate >= 0.8 && total >= 10 && !this.achievedStats.has('stat_battle_winrate_80')) {
            achieved.push({
                id: 'stat_battle_winrate_80',
                name: 'Elite Warrior',
                description: 'Achieved 80% win rate with 10+ battles',
                points: 1000,
                category: 'battles'
            });
        }

        return achieved;
    }

    /**
     * Check points stats for achievements
     */
    checkPointsAchievements(points) {
        const achieved = [];
        const total = this.calculateTotalPoints(points);

        // 1000 points
        if (total >= 1000 && !this.achievedStats.has('stat_points_1k')) {
            achieved.push({
                id: 'stat_points_1k',
                name: 'Point Collector',
                description: 'Earned 1,000 total points',
                points: 100,
                category: 'points'
            });
        }

        // 10,000 points
        if (total >= 10000 && !this.achievedStats.has('stat_points_10k')) {
            achieved.push({
                id: 'stat_points_10k',
                name: 'Point Master',
                description: 'Earned 10,000 total points',
                points: 500,
                category: 'points'
            });
        }

        // 100,000 points
        if (total >= 100000 && !this.achievedStats.has('stat_points_100k')) {
            achieved.push({
                id: 'stat_points_100k',
                name: 'Point Legend',
                description: 'Earned 100,000 total points',
                points: 2000,
                category: 'points'
            });
        }

        return achieved;
    }

    /**
     * Check XP stats for achievements
     */
    checkXPAchievements(xp) {
        const achieved = [];
        const total = xp.total || 0;
        const level = xp.level || 1;

        // Level 5
        if (level >= 5 && !this.achievedStats.has('stat_xp_level_5')) {
            achieved.push({
                id: 'stat_xp_level_5',
                name: 'Level 5',
                description: 'Reached level 5',
                points: 100,
                category: 'xp'
            });
        }

        // Level 10
        if (level >= 10 && !this.achievedStats.has('stat_xp_level_10')) {
            achieved.push({
                id: 'stat_xp_level_10',
                name: 'Level 10',
                description: 'Reached level 10',
                points: 300,
                category: 'xp'
            });
        }

        // Level 25
        if (level >= 25 && !this.achievedStats.has('stat_xp_level_25')) {
            achieved.push({
                id: 'stat_xp_level_25',
                name: 'Level 25',
                description: 'Reached level 25',
                points: 1000,
                category: 'xp'
            });
        }

        // 10,000 XP
        if (total >= 10000 && !this.achievedStats.has('stat_xp_10k')) {
            achieved.push({
                id: 'stat_xp_10k',
                name: 'XP Accumulator',
                description: 'Earned 10,000 XP',
                points: 200,
                category: 'xp'
            });
        }

        return achieved;
    }

    /**
     * Check trophy stats for achievements
     */
    checkTrophyAchievements(trophies) {
        const achieved = [];
        const total = trophies.total || 0;

        // First trophy
        if (total >= 1 && !this.achievedStats.has('stat_trophy_first')) {
            achieved.push({
                id: 'stat_trophy_first',
                name: 'First Trophy',
                description: 'Earned your first trophy',
                points: 100,
                category: 'trophies'
            });
        }

        // 5 trophies
        if (total >= 5 && !this.achievedStats.has('stat_trophy_5')) {
            achieved.push({
                id: 'stat_trophy_5',
                name: 'Trophy Collector',
                description: 'Earned 5 trophies',
                points: 500,
                category: 'trophies'
            });
        }

        // 10 trophies
        if (total >= 10 && !this.achievedStats.has('stat_trophy_10')) {
            achieved.push({
                id: 'stat_trophy_10',
                name: 'Trophy Master',
                description: 'Earned 10 trophies',
                points: 1000,
                category: 'trophies'
            });
        }

        return achieved;
    }

    /**
     * Check milestone stats for achievements
     */
    checkMilestoneAchievements(milestones) {
        const achieved = [];
        const reached = milestones.reached || 0;

        // First milestone
        if (reached >= 1 && !this.achievedStats.has('stat_milestone_first')) {
            achieved.push({
                id: 'stat_milestone_first',
                name: 'First Milestone',
                description: 'Reached your first milestone',
                points: 100,
                category: 'milestones'
            });
        }

        // 5 milestones
        if (reached >= 5 && !this.achievedStats.has('stat_milestone_5')) {
            achieved.push({
                id: 'stat_milestone_5',
                name: 'Milestone Achiever',
                description: 'Reached 5 milestones',
                points: 500,
                category: 'milestones'
            });
        }

        return achieved;
    }

    /**
     * Calculate total points from all point systems
     */
    calculateTotalPoints(points) {
        if (!points || typeof points !== 'object') return 0;
        
        let total = 0;
        for (const key in points) {
            const value = points[key];
            if (typeof value === 'number') {
                total += value;
            } else if (typeof value === 'object' && value !== null) {
                // Handle nested objects (e.g., theme_points by theme)
                for (const subKey in value) {
                    if (typeof value[subKey] === 'number') {
                        total += value[subKey];
                    }
                }
            }
        }
        return total;
    }

    /**
     * Award achievement reward to user
     */
    async awardAchievementReward(achievement) {
        try {
            // Award via rewards system
            const response = await fetch(`${this.baseURL}/rewards/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    category: 'achievement',
                    reward_type: 'points',
                    amount: achievement.points,
                    description: `Stat Achievement: ${achievement.name}`,
                    source: 'stats_tracker',
                    metadata: {
                        achievement_id: achievement.id,
                        achievement_name: achievement.name,
                        category: achievement.category
                    }
                })
            });

            if (response.ok) {
                const data = await response.json();
                console.log(`[StatsTracker] Awarded achievement: ${achievement.name} (+${achievement.points} points)`);
                
                // Show notification
                this.showAchievementNotification(achievement);
                
                return data;
            }
        } catch (error) {
            console.error(`[StatsTracker] Error awarding achievement ${achievement.id}:`, error);
        }
    }

    /**
     * Show achievement notification
     */
    showAchievementNotification(achievement) {
        // Try to use existing notification system
        if (window.showToast) {
            window.showToast(
                `🏆 Achievement Unlocked: ${achievement.name}`,
                `+${achievement.points} points`,
                'success'
            );
        } else if (window.showNotification) {
            window.showNotification(
                `Achievement: ${achievement.name}`,
                `Earned ${achievement.points} points!`
            );
        } else {
            // Fallback: console log
            console.log(`🏆 Achievement: ${achievement.name} - +${achievement.points} points`);
        }
    }

    /**
     * Get all achieved stats
     */
    getAchievedStats() {
        return Array.from(this.achievedStats);
    }

    /**
     * Check if a stat has been achieved
     */
    hasAchieved(statId) {
        return this.achievedStats.has(statId);
    }

    /**
     * Get current stats cache
     */
    getStats() {
        return this.statsCache;
    }
}

// Global instance
window.statsAchievementsTracker = new StatsAchievementsTracker();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.statsAchievementsTracker.initialize();
    });
} else {
    window.statsAchievementsTracker.initialize();
}
