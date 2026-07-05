/**
 * Point Analytics Dashboard
 * Displays comprehensive point analytics and history
 */
class PointAnalyticsDashboard {
    constructor() {
        this.userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
        this.currentAnalytics = null;
        this.refreshInterval = null;
    }

    /**
     * Initialize the analytics dashboard
     */
    async init(userId = null) {
        this.userId = userId || localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
        await this.loadComprehensiveAnalytics();
        this.startAutoRefresh();
    }

    /**
     * Load comprehensive analytics
     */
    async loadComprehensiveAnalytics(days = 30) {
        try {
            const response = await fetch(
                `/api/points/analytics/comprehensive?user_id=${this.userId}&days=${days}`
            );
            const data = await response.json();
            
            if (data.success) {
                this.currentAnalytics = data.analytics;
                this.displayAnalytics(data.analytics);
                return data.analytics;
            } else {
                console.error('Failed to load analytics:', data.error);
                return null;
            }
        } catch (error) {
            console.error('Error loading analytics:', error);
            return null;
        }
    }

    /**
     * Display analytics in the UI
     */
    displayAnalytics(analytics) {
        // Current Points Summary
        this.displayCurrentPoints(analytics.current_points);
        
        // History Statistics
        this.displayHistoryStats(analytics.history_stats);
        
        // Trends
        this.displayTrends(analytics.trends);
        
        // Projections
        this.displayProjections(analytics.projections);
        
        // Insights
        this.displayInsights(analytics.insights);
    }

    /**
     * Display current points
     */
    displayCurrentPoints(currentPoints) {
        const container = document.getElementById('analytics-current-points');
        if (!container) return;

        const html = `
            <div class="analytics-section">
                <h3>Current Points</h3>
                <div class="points-grid">
                    ${Object.entries(currentPoints).map(([key, value]) => `
                        <div class="point-item">
                            <span class="point-label">${this.formatKey(key)}</span>
                            <span class="point-value">${this.formatNumber(value)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        container.innerHTML = html;
    }

    /**
     * Display history statistics
     */
    displayHistoryStats(stats) {
        const container = document.getElementById('analytics-history-stats');
        if (!container) return;

        const html = `
            <div class="analytics-section">
                <h3>History Statistics (${stats.period_days || 30} days)</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-label">Total Earned</div>
                        <div class="stat-value positive">${this.formatNumber(stats.total_earned || 0)}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Spent</div>
                        <div class="stat-value negative">${this.formatNumber(stats.total_spent || 0)}</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Net Change</div>
                        <div class="stat-value ${(stats.net_change || 0) >= 0 ? 'positive' : 'negative'}">
                            ${this.formatNumber(stats.net_change || 0)}
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Avg Per Day</div>
                        <div class="stat-value">${this.formatNumber(stats.average_per_day || 0)}</div>
                    </div>
                </div>
                ${this.displayBySource(stats.by_source)}
            </div>
        `;
        container.innerHTML = html;
    }

    /**
     * Display by source breakdown
     */
    displayBySource(bySource) {
        if (!bySource || Object.keys(bySource).length === 0) return '';

        const sorted = Object.entries(bySource)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);

        return `
            <div class="source-breakdown">
                <h4>Top Sources</h4>
                <div class="source-list">
                    ${sorted.map(([source, amount]) => `
                        <div class="source-item">
                            <span class="source-name">${source}</span>
                            <span class="source-amount ${amount >= 0 ? 'positive' : 'negative'}">
                                ${this.formatNumber(amount)}
                            </span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Display trends
     */
    displayTrends(trends) {
        const container = document.getElementById('analytics-trends');
        if (!container) return;

        const trend = trends.trend || 'stable';
        const changeRate = trends.change_rate || 0;
        const trendIcon = trend === 'increasing' ? '📈' : trend === 'decreasing' ? '📉' : '➡️';

        const html = `
            <div class="analytics-section">
                <h3>Trends</h3>
                <div class="trend-display">
                    <div class="trend-icon">${trendIcon}</div>
                    <div class="trend-info">
                        <div class="trend-label">${trend.charAt(0).toUpperCase() + trend.slice(1)}</div>
                        <div class="trend-rate ${changeRate >= 0 ? 'positive' : 'negative'}">
                            ${changeRate >= 0 ? '+' : ''}${changeRate.toFixed(1)}%
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML = html;
    }

    /**
     * Display projections
     */
    displayProjections(projections) {
        const container = document.getElementById('analytics-projections');
        if (!container) return;

        const html = `
            <div class="analytics-section">
                <h3>Projections</h3>
                <div class="projections-grid">
                    <div class="projection-card">
                        <div class="projection-label">Next 7 Days</div>
                        <div class="projection-value">${this.formatNumber(projections.next_7_days || 0)}</div>
                    </div>
                    <div class="projection-card">
                        <div class="projection-label">Next 30 Days</div>
                        <div class="projection-value">${this.formatNumber(projections.next_30_days || 0)}</div>
                    </div>
                    <div class="projection-card">
                        <div class="projection-label">Next 90 Days</div>
                        <div class="projection-value">${this.formatNumber(projections.next_90_days || 0)}</div>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML = html;
    }

    /**
     * Display insights
     */
    displayInsights(insights) {
        const container = document.getElementById('analytics-insights');
        if (!container) return;

        if (!insights || insights.length === 0) {
            container.innerHTML = '<div class="analytics-section"><p>No insights available</p></div>';
            return;
        }

        const html = `
            <div class="analytics-section">
                <h3>Insights</h3>
                <div class="insights-list">
                    ${insights.map(insight => `
                        <div class="insight-item">💡 ${insight}</div>
                    `).join('')}
                </div>
            </div>
        `;
        container.innerHTML = html;
    }

    /**
     * Load point history
     */
    async loadPointHistory(pointType = null, limit = 100) {
        try {
            let url = `/api/points/analytics/history?user_id=${this.userId}&limit=${limit}`;
            if (pointType) {
                url += `&point_type=${pointType}`;
            }

            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                this.displayHistory(data.history);
                return data.history;
            } else {
                console.error('Failed to load history:', data.error);
                return null;
            }
        } catch (error) {
            console.error('Error loading history:', error);
            return null;
        }
    }

    /**
     * Display history list
     */
    displayHistory(history) {
        const container = document.getElementById('analytics-history-list');
        if (!container) return;

        if (!history || history.length === 0) {
            container.innerHTML = '<p>No history available</p>';
            return;
        }

        const html = `
            <div class="history-list">
                ${history.map(entry => `
                    <div class="history-item">
                        <div class="history-date">${this.formatDate(entry.timestamp)}</div>
                        <div class="history-type">${entry.point_type}</div>
                        <div class="history-amount ${entry.amount >= 0 ? 'positive' : 'negative'}">
                            ${entry.amount >= 0 ? '+' : ''}${this.formatNumber(entry.amount)}
                        </div>
                        <div class="history-source">${entry.source}</div>
                    </div>
                `).join('')}
            </div>
        `;
        container.innerHTML = html;
    }

    /**
     * Start auto-refresh
     */
    startAutoRefresh(intervalSeconds = 60) {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        this.refreshInterval = setInterval(() => {
            this.loadComprehensiveAnalytics();
        }, intervalSeconds * 1000);
    }

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Format number
     */
    formatNumber(num) {
        if (num === null || num === undefined) return '0';
        return Number(num).toLocaleString();
    }

    /**
     * Format date
     */
    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString();
    }

    /**
     * Format key (convert snake_case to Title Case)
     */
    formatKey(key) {
        return key.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }
}

// Global instance
const pointAnalyticsDashboard = new PointAnalyticsDashboard();

// Auto-initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        pointAnalyticsDashboard.init();
    });
} else {
    pointAnalyticsDashboard.init();
}

