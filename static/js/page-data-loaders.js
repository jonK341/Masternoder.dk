/**
 * Page Data Loaders
 * Page-specific data loading functions using BackendConnector
 */

// Profile Page Loader
class ProfilePageLoader {
    constructor() {
        this.userId = backendConnector.getUserId();
    }

    async loadAll() {
        const [profile, skills, stats, activity] = await Promise.allSettled([
            backendConnector.getUserProfileDisplay(this.userId),
            backendConnector.getUserAgentSkills(this.userId),
            backendConnector.getStats(this.userId),
            this.loadActivity()
        ]);

        return {
            profile: profile.status === 'fulfilled' ? profile.value : null,
            skills: skills.status === 'fulfilled' ? skills.value : null,
            stats: stats.status === 'fulfilled' ? stats.value : null,
            activity: activity.status === 'fulfilled' ? activity.value : null
        };
    }

    async loadActivity() {
        // Load XP history as activity
        const xpHistory = await backendConnector.getXPHistory(this.userId);
        return xpHistory;
    }
}

// Stats Page Loader
class StatsPageLoader {
    constructor() {
        this.userId = backendConnector.getUserId();
    }

    async loadAll() {
        const [stats, level, xpHistory, dailyActivities] = await Promise.allSettled([
            backendConnector.getStats(this.userId),
            backendConnector.getPlayerLevel(this.userId),
            backendConnector.getXPHistory(this.userId),
            backendConnector.getDailyActivities(this.userId)
        ]);

        return {
            stats: stats.status === 'fulfilled' ? stats.value : null,
            level: level.status === 'fulfilled' ? level.value : null,
            xpHistory: xpHistory.status === 'fulfilled' ? xpHistory.value : null,
            dailyActivities: dailyActivities.status === 'fulfilled' ? dailyActivities.value : null
        };
    }
}

// Social Page Loader
class SocialPageLoader {
    constructor() {
        this.userId = backendConnector.getUserId();
    }

    async loadAll() {
        const [socialData, profile] = await Promise.allSettled([
            backendConnector.getSocialData(this.userId),
            backendConnector.getUserProfile(this.userId)
        ]);

        return {
            social: socialData.status === 'fulfilled' ? socialData.value : null,
            profile: profile.status === 'fulfilled' ? profile.value : null
        };
    }
}

// Points Page Loader
class PointsPageLoader {
    constructor() {
        this.userId = backendConnector.getUserId();
    }

    async loadAll() {
        const [points, level, rewards] = await Promise.allSettled([
            backendConnector.getAllPoints(this.userId),
            backendConnector.getPlayerLevel(this.userId),
            backendConnector.getRewards(this.userId)
        ]);

        return {
            points: points.status === 'fulfilled' ? points.value : null,
            level: level.status === 'fulfilled' ? level.value : null,
            rewards: rewards.status === 'fulfilled' ? rewards.value : null
        };
    }
}

// Analytics Page Loader
class AnalyticsPageLoader {
    constructor() {
        this.userId = backendConnector.getUserId();
    }

    async loadAll() {
        const [analytics, stats, xpHistory] = await Promise.allSettled([
            backendConnector.getAnalytics(this.userId),
            backendConnector.getStats(this.userId),
            backendConnector.getXPHistory(this.userId)
        ]);

        return {
            analytics: analytics.status === 'fulfilled' ? analytics.value : null,
            stats: stats.status === 'fulfilled' ? stats.value : null,
            xpHistory: xpHistory.status === 'fulfilled' ? xpHistory.value : null
        };
    }
}

// Dashboard Page Loader
class DashboardPageLoader {
    constructor() {
        this.userId = backendConnector.getUserId();
    }

    async loadAll() {
        const [profile, points, level, agentStatus, agentSkills] = await Promise.allSettled([
            backendConnector.getUserProfile(this.userId),
            backendConnector.getAllPoints(this.userId),
            backendConnector.getPlayerLevel(this.userId),
            backendConnector.getAgentControllerStatus(),
            backendConnector.getAgentSkillsetStats()
        ]);

        return {
            profile: profile.status === 'fulfilled' ? profile.value : null,
            points: points.status === 'fulfilled' ? points.value : null,
            level: level.status === 'fulfilled' ? level.value : null,
            agentStatus: agentStatus.status === 'fulfilled' ? agentStatus.value : null,
            agentSkills: agentSkills.status === 'fulfilled' ? agentSkills.value : null
        };
    }
}

// Export loaders
window.pageDataLoaders = {
    profile: ProfilePageLoader,
    stats: StatsPageLoader,
    social: SocialPageLoader,
    points: PointsPageLoader,
    analytics: AnalyticsPageLoader,
    dashboard: DashboardPageLoader
};
