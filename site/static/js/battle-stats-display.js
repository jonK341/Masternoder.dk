/**
 * Battle Stats Display Module
 * A+ Quality Statistics Display for All Battle Tabs
 */

class BattleStatsDisplay {
    constructor(baseUrl, userId) {
        this.baseUrl = baseUrl;
        this.userId = userId;
        this.statsCache = {};
    }

    /**
     * Fetch comprehensive stats for a specific tab
     */
    async fetchTabStats(tabName) {
        const cacheKey = `${tabName}_${this.userId}`;
        if (this.statsCache[cacheKey] && Date.now() - this.statsCache[cacheKey].timestamp < 30000) {
            return this.statsCache[cacheKey].data;
        }

        try {
            const response = await fetch(`${this.baseUrl}/api/battle/stats/${tabName}?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success && data.stats) {
                this.statsCache[cacheKey] = {
                    data: data.stats,
                    timestamp: Date.now()
                };
                return data.stats;
            }
            return null;
        } catch (error) {
            console.error(`Error fetching stats for ${tabName}:`, error);
            return null;
        }
    }

    /**
     * Display overview stats
     */
    async displayOverviewStats(containerId = 'battle-stats') {
        const stats = await this.fetchTabStats('overview');
        if (!stats) return;

        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="stat-box" style="border-left: 4px solid var(--primary);">
                <div class="stat-value" style="color: var(--primary);">${stats.total_battles || 0}</div>
                <div class="stat-label">Total Battles</div>
                <div style="font-size: var(--font-size-xs); color: var(--text-secondary); margin-top: var(--spacing-xs);">
                    ${stats.win_rate?.toFixed(1) || 0}% win rate
                </div>
            </div>
            <div class="stat-box" style="border-left: 4px solid #44ff44;">
                <div class="stat-value" style="color: #44ff44;">${stats.wins || 0}</div>
                <div class="stat-label">Victories</div>
                <div style="font-size: var(--font-size-xs); color: var(--text-secondary); margin-top: var(--spacing-xs);">
                    ${stats.losses || 0} losses
                </div>
            </div>
            <div class="stat-box" style="border-left: 4px solid #ffaa00;">
                <div class="stat-value" style="color: #ffaa00;">${stats.current_streak || 0}</div>
                <div class="stat-label">Win Streak</div>
                <div style="font-size: var(--font-size-xs); color: var(--text-secondary); margin-top: var(--spacing-xs);">
                    Best: ${stats.best_streak || 0}
                </div>
            </div>
            <div class="stat-box" style="border-left: 4px solid #ff6b6b;">
                <div class="stat-value" style="color: #ff6b6b;">${stats.rank || 'N/A'}</div>
                <div class="stat-label">Rank</div>
                <div style="font-size: var(--font-size-xs); color: var(--text-secondary); margin-top: var(--spacing-xs);">
                    Top ${stats.percentile?.toFixed(1) || 0}%
                </div>
            </div>
            <div class="stat-box" style="border-left: 4px solid #4ecdc4;">
                <div class="stat-value" style="color: #4ecdc4;">${stats.total_points || 0}</div>
                <div class="stat-label">Total Points</div>
                <div style="font-size: var(--font-size-xs); color: var(--text-secondary); margin-top: var(--spacing-xs);">
                    ${stats.trophies || 0} trophies
                </div>
            </div>
            <div class="stat-box" style="border-left: 4px solid #95e1d3;">
                <div class="stat-value" style="color: #95e1d3;">${stats.achievements_unlocked || 0}/${stats.total_achievements || 0}</div>
                <div class="stat-label">Achievements</div>
                <div style="font-size: var(--font-size-xs); color: var(--text-secondary); margin-top: var(--spacing-xs);">
                    ${stats.total_achievements > 0 ? ((stats.achievements_unlocked / stats.total_achievements * 100).toFixed(0)) : 0}% complete
                </div>
            </div>
        `;

        // Display performance overview
        this.displayPerformanceOverview(stats);
        this.displayRecentActivity(stats);
    }

    /**
     * Display performance overview
     */
    displayPerformanceOverview(stats) {
        const container = document.getElementById('battle-performance-overview');
        if (!container || !stats.performance_metrics) return;

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-md);">
                <div>
                    <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Accuracy</div>
                    <div style="font-size: 2em; font-weight: 700; color: var(--primary);">${stats.performance_metrics.accuracy || 0}%</div>
                </div>
                <div>
                    <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Reaction Time</div>
                    <div style="font-size: 2em; font-weight: 700; color: var(--primary);">${(stats.performance_metrics.reaction_time || 0).toFixed(2)}s</div>
                </div>
                <div>
                    <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Strategy Score</div>
                    <div style="font-size: 2em; font-weight: 700; color: var(--primary);">${stats.performance_metrics.strategy_score || 0}</div>
                </div>
                <div>
                    <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Adaptability</div>
                    <div style="font-size: 2em; font-weight: 700; color: var(--primary);">${stats.performance_metrics.adaptability || 0}%</div>
                </div>
            </div>
            ${stats.weekly_progress ? `
                <div style="margin-top: var(--spacing-lg); padding-top: var(--spacing-lg); border-top: 1px solid var(--border-primary);">
                    <h3 style="margin-bottom: var(--spacing-md);">Weekly Progress</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--spacing-md);">
                        <div>
                            <div style="font-size: 0.85em; color: var(--text-secondary);">Battles This Week</div>
                            <div style="font-size: 1.5em; font-weight: 700; color: var(--primary);">${stats.weekly_progress.battles_this_week || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.85em; color: var(--text-secondary);">Wins This Week</div>
                            <div style="font-size: 1.5em; font-weight: 700; color: #44ff44;">${stats.weekly_progress.wins_this_week || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.85em; color: var(--text-secondary);">Points This Week</div>
                            <div style="font-size: 1.5em; font-weight: 700; color: #ffaa00;">${stats.weekly_progress.points_this_week || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.85em; color: var(--text-secondary);">Rank Change</div>
                            <div style="font-size: 1.5em; font-weight: 700; color: ${(stats.weekly_progress.rank_change || 0) >= 0 ? '#44ff44' : '#ff4444'};">
                                ${(stats.weekly_progress.rank_change || 0) >= 0 ? '+' : ''}${stats.weekly_progress.rank_change || 0}
                            </div>
                        </div>
                    </div>
                </div>
            ` : ''}
        `;
    }

    /**
     * Display recent activity
     */
    displayRecentActivity(stats) {
        const container = document.getElementById('recent-battle-activity');
        if (!container || !stats.recent_activity) return;

        container.innerHTML = `
            <div style="display: flex; flex-direction: column; gap: var(--spacing-sm);">
                ${stats.recent_activity.slice(0, 5).map(activity => `
                    <div style="padding: var(--spacing-md); background: var(--bg-secondary); border-radius: var(--border-radius); border-left: 3px solid var(--primary);">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <div style="font-weight: 600; color: var(--text-primary); margin-bottom: var(--spacing-xs);">
                                    ${this.getActivityIcon(activity.type)} ${activity.description}
                                </div>
                                <div style="font-size: 0.85em; color: var(--text-secondary);">
                                    ${this.formatTimestamp(activity.timestamp)}
                                </div>
                            </div>
                            ${activity.points ? `
                                <div style="font-weight: 700; color: #ffaa00; font-size: 1.1em;">
                                    +${activity.points}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Display battle tab stats
     */
    async displayBattleTabStats() {
        const stats = await this.fetchTabStats('battle');
        if (!stats) return;

        // Update active battles count
        const activeBattlesEl = document.getElementById('active-battles-count');
        if (activeBattlesEl) activeBattlesEl.textContent = stats.active_battles || 0;

        // Update win streak
        const winStreakEl = document.getElementById('current-win-streak');
        if (winStreakEl) winStreakEl.textContent = stats.win_streak || 0;

        // Display battle type breakdown
        this.displayStatsTable('battle-type-stats', {
            title: 'Battle Type Breakdown',
            data: stats.battle_types || {},
            formatValue: (value) => `${value.count} battles (${value.win_rate?.toFixed(1)}% win rate)`
        });

        // Display opponent stats
        this.displayStatsTable('opponent-stats', {
            title: 'Opponent Statistics',
            data: stats.opponent_stats || {},
            formatValue: (value) => `${value.battles} battles (${value.win_rate?.toFixed(1)}% win rate)`
        });

        // Display difficulty stats
        this.displayStatsTable('difficulty-stats', {
            title: 'Difficulty Performance',
            data: stats.difficulty_stats || {},
            formatValue: (value) => `${value.battles} battles (${value.win_rate?.toFixed(1)}% win rate)`
        });
    }

    /**
     * Display tournament stats
     */
    async displayTournamentStats() {
        const stats = await this.fetchTabStats('tournaments');
        if (!stats) return;

        const container = document.getElementById('tab-tournaments');
        if (!container) return;

        // Create stats section if it doesn't exist
        let statsSection = container.querySelector('.tournament-stats-section');
        if (!statsSection) {
            statsSection = document.createElement('div');
            statsSection.className = 'tournament-stats-section';
            statsSection.style.cssText = 'margin-bottom: var(--spacing-xl);';
            container.insertBefore(statsSection, container.firstChild);
        }

        statsSection.innerHTML = `
            <div class="card" style="margin-bottom: var(--spacing-lg);">
                <div class="card-header">
                    <h2 class="card-title">📊 Tournament Statistics</h2>
                </div>
                <div style="padding: var(--spacing-lg);">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-lg);">
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Active Tournaments</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: var(--primary);">${stats.active_tournaments || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Completed</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: #44ff44;">${stats.completed_tournaments || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Win Rate</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: #ffaa00;">${stats.tournament_win_rate?.toFixed(1) || 0}%</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Current Rank</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: var(--secondary);">#${stats.current_rank || 'N/A'}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Display upcoming tournaments
        if (stats.upcoming_tournaments && stats.upcoming_tournaments.length > 0) {
            this.displayTournamentList('upcoming-tournaments', stats.upcoming_tournaments, 'Upcoming Tournaments');
        }

        // Display recent tournaments
        if (stats.recent_tournaments && stats.recent_tournaments.length > 0) {
            this.displayTournamentList('recent-tournaments', stats.recent_tournaments, 'Recent Tournaments');
        }
    }

    /**
     * Display tournament list
     */
    displayTournamentList(containerId, tournaments, title) {
        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.style.cssText = 'margin-top: var(--spacing-lg);';
            const tabContainer = document.getElementById('tab-tournaments');
            if (tabContainer) tabContainer.appendChild(container);
        }

        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">${title}</h3>
                </div>
                <div style="padding: var(--spacing-lg);">
                    <div style="display: grid; gap: var(--spacing-md);">
                        ${tournaments.map(tournament => `
                            <div style="padding: var(--spacing-md); background: var(--bg-secondary); border-radius: var(--border-radius); border-left: 3px solid var(--primary);">
                                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--spacing-xs);">
                                    <div>
                                        <div style="font-weight: 600; color: var(--text-primary);">${tournament.name}</div>
                                        <div style="font-size: 0.85em; color: var(--text-secondary); margin-top: var(--spacing-xs);">
                                            ${tournament.start_date ? `Starts: ${this.formatDate(tournament.start_date)}` : ''}
                                            ${tournament.completed_date ? `Completed: ${this.formatDate(tournament.completed_date)}` : ''}
                                        </div>
                                    </div>
                                    ${tournament.rank ? `
                                        <div style="font-weight: 700; color: var(--primary); font-size: 1.2em;">
                                            Rank #${tournament.rank}
                                        </div>
                                    ` : ''}
                                </div>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: var(--spacing-sm); margin-top: var(--spacing-sm);">
                                    ${tournament.participants ? `
                                        <div>
                                            <div style="font-size: 0.8em; color: var(--text-secondary);">Participants</div>
                                            <div style="font-weight: 600; color: var(--text-primary);">${tournament.participants}</div>
                                        </div>
                                    ` : ''}
                                    ${tournament.prize_pool ? `
                                        <div>
                                            <div style="font-size: 0.8em; color: var(--text-secondary);">Prize Pool</div>
                                            <div style="font-weight: 600; color: #ffaa00;">${tournament.prize_pool.toLocaleString()}</div>
                                        </div>
                                    ` : ''}
                                    ${tournament.round_reached ? `
                                        <div>
                                            <div style="font-size: 0.8em; color: var(--text-secondary);">Round Reached</div>
                                            <div style="font-weight: 600; color: var(--text-primary);">${tournament.round_reached}</div>
                                        </div>
                                    ` : ''}
                                    ${tournament.points_earned ? `
                                        <div>
                                            <div style="font-size: 0.8em; color: var(--text-secondary);">Points Earned</div>
                                            <div style="font-weight: 600; color: #44ff44;">+${tournament.points_earned}</div>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Display history stats
     */
    async displayHistoryStats() {
        const stats = await this.fetchTabStats('history');
        if (!stats) return;

        const container = document.getElementById('tab-history');
        if (!container) return;

        // Create stats summary
        let statsSummary = container.querySelector('.history-stats-summary');
        if (!statsSummary) {
            statsSummary = document.createElement('div');
            statsSummary.className = 'history-stats-summary';
            statsSummary.style.cssText = 'margin-bottom: var(--spacing-lg);';
            container.insertBefore(statsSummary, container.firstChild);
        }

        statsSummary.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">📊 Battle History Statistics</h2>
                </div>
                <div style="padding: var(--spacing-lg);">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--spacing-lg);">
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary);">Total Battles</div>
                            <div style="font-size: 2em; font-weight: 700; color: var(--primary);">${stats.total_battles || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary);">This Month</div>
                            <div style="font-size: 2em; font-weight: 700; color: #44ff44;">${stats.battles_this_month || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary);">This Week</div>
                            <div style="font-size: 2em; font-weight: 700; color: #ffaa00;">${stats.battles_this_week || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary);">Today</div>
                            <div style="font-size: 2em; font-weight: 700; color: #4ecdc4;">${stats.battles_today || 0}</div>
                        </div>
                    </div>
                    ${stats.history_summary ? `
                        <div style="margin-top: var(--spacing-lg); padding-top: var(--spacing-lg); border-top: 1px solid var(--border-primary);">
                            <h3 style="margin-bottom: var(--spacing-md);">Summary</h3>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-md);">
                                ${stats.history_summary.by_type ? Object.entries(stats.history_summary.by_type).map(([type, count]) => `
                                    <div>
                                        <div style="font-size: 0.85em; color: var(--text-secondary);">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
                                        <div style="font-size: 1.5em; font-weight: 700; color: var(--primary);">${count}</div>
                                    </div>
                                `).join('') : ''}
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        // Display recent battles table
        if (stats.recent_battles && stats.recent_battles.length > 0) {
            this.displayBattlesTable('recent-battles-table', stats.recent_battles, 'Recent Battles');
        }
    }

    /**
     * Display battles table
     */
    displayBattlesTable(containerId, battles, title) {
        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.style.cssText = 'margin-top: var(--spacing-lg);';
            const tabContainer = document.getElementById('tab-history');
            if (tabContainer) tabContainer.appendChild(container);
        }

        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">${title}</h3>
                </div>
                <div style="padding: var(--spacing-lg); overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid var(--border-primary);">
                                <th style="padding: var(--spacing-md); text-align: left; color: var(--text-secondary);">Date</th>
                                <th style="padding: var(--spacing-md); text-align: left; color: var(--text-secondary);">Type</th>
                                <th style="padding: var(--spacing-md); text-align: left; color: var(--text-secondary);">Opponent</th>
                                <th style="padding: var(--spacing-md); text-align: center; color: var(--text-secondary);">Result</th>
                                <th style="padding: var(--spacing-md); text-align: center; color: var(--text-secondary);">Duration</th>
                                <th style="padding: var(--spacing-md); text-align: center; color: var(--text-secondary);">Points</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${battles.map(battle => `
                                <tr style="border-bottom: 1px solid var(--border-primary);">
                                    <td style="padding: var(--spacing-md);">${this.formatDate(battle.date)}</td>
                                    <td style="padding: var(--spacing-md);">
                                        <span style="padding: 2px 8px; background: var(--bg-secondary); border-radius: var(--border-radius-sm); font-size: 0.85em;">
                                            ${battle.type || 'N/A'}
                                        </span>
                                    </td>
                                    <td style="padding: var(--spacing-md);">${battle.opponent || 'N/A'}</td>
                                    <td style="padding: var(--spacing-md); text-align: center;">
                                        <span style="padding: 4px 12px; border-radius: var(--border-radius-sm); font-weight: 600; 
                                            background: ${battle.result === 'win' ? 'rgba(68, 255, 68, 0.2)' : 'rgba(255, 68, 68, 0.2)'};
                                            color: ${battle.result === 'win' ? '#44ff44' : '#ff4444'};">
                                            ${battle.result === 'win' ? '✓ Win' : '✗ Loss'}
                                        </span>
                                    </td>
                                    <td style="padding: var(--spacing-md); text-align: center;">${this.formatDuration(battle.duration)}</td>
                                    <td style="padding: var(--spacing-md); text-align: center; color: #ffaa00; font-weight: 600;">
                                        ${battle.points_earned || 0}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    /**
     * Display leaderboard stats
     */
    async displayLeaderboardStats() {
        const stats = await this.fetchTabStats('leaderboard');
        if (!stats) return;

        const container = document.getElementById('tab-leaderboard');
        if (!container) return;

        // Create user rank card
        let rankCard = container.querySelector('.user-rank-card');
        if (!rankCard) {
            rankCard = document.createElement('div');
            rankCard.className = 'user-rank-card';
            rankCard.style.cssText = 'margin-bottom: var(--spacing-lg);';
            container.insertBefore(rankCard, container.firstChild);
        }

        rankCard.innerHTML = `
            <div class="card" style="border-left: 4px solid var(--primary);">
                <div class="card-header">
                    <h2 class="card-title">🏆 Your Ranking</h2>
                </div>
                <div style="padding: var(--spacing-lg);">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-lg);">
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Current Rank</div>
                            <div style="font-size: 3em; font-weight: 700; color: var(--primary);">#${stats.user_rank || 'N/A'}</div>
                            <div style="font-size: 0.85em; color: var(--text-secondary); margin-top: var(--spacing-xs);">
                                Top ${stats.percentile?.toFixed(1) || 0}% of ${stats.total_players || 0} players
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Total Points</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: #ffaa00;">${(stats.user_points || 0).toLocaleString()}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Wins</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: #44ff44;">${stats.user_wins || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Win Rate</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: var(--secondary);">${stats.user_win_rate?.toFixed(1) || 0}%</div>
                        </div>
                    </div>
                    ${stats.rank_progress ? `
                        <div style="margin-top: var(--spacing-lg); padding-top: var(--spacing-lg); border-top: 1px solid var(--border-primary);">
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-md);">
                                <div>
                                    <div style="font-size: 0.85em; color: var(--text-secondary);">Points to Next Rank</div>
                                    <div style="font-size: 1.5em; font-weight: 700; color: var(--primary);">${stats.rank_progress.points_to_next_rank || 0}</div>
                                </div>
                                <div>
                                    <div style="font-size: 0.85em; color: var(--text-secondary);">Estimated Battles</div>
                                    <div style="font-size: 1.5em; font-weight: 700; color: var(--primary);">${stats.rank_progress.estimated_battles_to_next_rank || 0}</div>
                                </div>
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        // Display top players table
        if (stats.top_players && stats.top_players.length > 0) {
            this.displayLeaderboardTable('top-players-table', stats.top_players, 'Top Players');
        }
    }

    /**
     * Display leaderboard table
     */
    displayLeaderboardTable(containerId, players, title) {
        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.style.cssText = 'margin-top: var(--spacing-lg);';
            const tabContainer = document.getElementById('tab-leaderboard');
            if (tabContainer) tabContainer.appendChild(container);
        }

        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">${title}</h3>
                </div>
                <div style="padding: var(--spacing-lg); overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid var(--border-primary);">
                                <th style="padding: var(--spacing-md); text-align: center; color: var(--text-secondary);">Rank</th>
                                <th style="padding: var(--spacing-md); text-align: left; color: var(--text-secondary);">Player</th>
                                <th style="padding: var(--spacing-md); text-align: right; color: var(--text-secondary);">Points</th>
                                <th style="padding: var(--spacing-md); text-align: center; color: var(--text-secondary);">Wins</th>
                                <th style="padding: var(--spacing-md); text-align: center; color: var(--text-secondary);">Win Rate</th>
                                <th style="padding: var(--spacing-md); text-align: right; color: var(--text-secondary);">Trophies</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${players.map(player => `
                                <tr style="border-bottom: 1px solid var(--border-primary); ${player.is_current_user ? 'background: rgba(255, 170, 0, 0.1);' : ''}">
                                    <td style="padding: var(--spacing-md); text-align: center; font-weight: 700; color: var(--primary);">
                                        #${player.rank}
                                    </td>
                                    <td style="padding: var(--spacing-md);">
                                        <div style="display: flex; align-items: center; gap: var(--spacing-sm);">
                                            ${player.is_current_user ? '<span style="color: #ffaa00;">★</span>' : ''}
                                            <span style="font-weight: ${player.is_current_user ? '700' : '500'};">
                                                ${player.username || player.user_id}
                                            </span>
                                        </div>
                                    </td>
                                    <td style="padding: var(--spacing-md); text-align: right; font-weight: 600; color: #ffaa00;">
                                        ${(player.points || 0).toLocaleString()}
                                    </td>
                                    <td style="padding: var(--spacing-md); text-align: center; color: #44ff44; font-weight: 600;">
                                        ${player.wins || 0}
                                    </td>
                                    <td style="padding: var(--spacing-md); text-align: center;">
                                        ${player.win_rate?.toFixed(1) || 0}%
                                    </td>
                                    <td style="padding: var(--spacing-md); text-align: right; color: var(--secondary); font-weight: 600;">
                                        ${player.trophies || 0}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    /**
     * Display intelligence stats
     */
    async displayIntelligenceStats() {
        const stats = await this.fetchTabStats('intelligence');
        if (!stats) return;

        const container = document.getElementById('tab-intelligence');
        if (!container) return;

        let intelSection = container.querySelector('.intelligence-stats-section');
        if (!intelSection) {
            intelSection = document.createElement('div');
            intelSection.className = 'intelligence-stats-section';
            intelSection.style.cssText = 'margin-bottom: var(--spacing-lg);';
            container.insertBefore(intelSection, container.firstChild);
        }

        intelSection.innerHTML = `
            <div class="card" style="margin-bottom: var(--spacing-lg);">
                <div class="card-header">
                    <h2 class="card-title">🧠 Intelligence Overview</h2>
                </div>
                <div style="padding: var(--spacing-lg);">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-lg);">
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Intelligence Level</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: var(--primary);">${stats.intelligence_level || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Intelligence Score</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: var(--secondary);">${stats.intelligence_score || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Next Win Probability</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: #44ff44;">${stats.predictive_analytics?.next_battle_win_probability?.toFixed(1) || 0}%</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Display recommendations
        if (stats.recommendations && stats.recommendations.length > 0) {
            this.displayRecommendations('intelligence-recommendations', stats.recommendations);
        }

        // Display performance analysis
        if (stats.performance_analysis) {
            this.displayPerformanceAnalysis('intelligence-analysis', stats.performance_analysis);
        }
    }

    /**
     * Display recommendations
     */
    displayRecommendations(containerId, recommendations) {
        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.style.cssText = 'margin-top: var(--spacing-lg);';
            const tabContainer = document.getElementById('tab-intelligence');
            if (tabContainer) tabContainer.appendChild(container);
        }

        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">💡 Recommendations</h3>
                </div>
                <div style="padding: var(--spacing-lg);">
                    <div style="display: grid; gap: var(--spacing-md);">
                        ${recommendations.map(rec => `
                            <div style="padding: var(--spacing-md); background: var(--bg-secondary); border-radius: var(--border-radius); 
                                border-left: 3px solid ${this.getPriorityColor(rec.priority)};">
                                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: var(--spacing-xs);">
                                    <div>
                                        <div style="font-weight: 600; color: var(--text-primary); margin-bottom: var(--spacing-xs);">
                                            ${rec.title}
                                        </div>
                                        <div style="font-size: 0.9em; color: var(--text-secondary);">
                                            ${rec.description}
                                        </div>
                                    </div>
                                    <span style="padding: 4px 8px; background: ${this.getPriorityColor(rec.priority)}; 
                                        border-radius: var(--border-radius-sm); font-size: 0.75em; font-weight: 600; text-transform: uppercase;">
                                        ${rec.priority}
                                    </span>
                                </div>
                                <div style="margin-top: var(--spacing-sm); padding-top: var(--spacing-sm); border-top: 1px solid var(--border-primary);">
                                    <div style="font-size: 0.85em; color: var(--text-secondary);">
                                        <strong>Action:</strong> ${rec.action}
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Display performance analysis
     */
    displayPerformanceAnalysis(containerId, analysis) {
        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.style.cssText = 'margin-top: var(--spacing-lg);';
            const tabContainer = document.getElementById('tab-intelligence');
            if (tabContainer) tabContainer.appendChild(container);
        }

        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📊 Performance Analysis</h3>
                </div>
                <div style="padding: var(--spacing-lg);">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: var(--spacing-lg);">
                        ${analysis.strengths ? `
                            <div>
                                <h4 style="color: #44ff44; margin-bottom: var(--spacing-md);">✅ Strengths</h4>
                                <ul style="list-style: none; padding: 0;">
                                    ${analysis.strengths.map(s => `<li style="padding: var(--spacing-xs) 0; color: var(--text-primary);">• ${s}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        ${analysis.weaknesses ? `
                            <div>
                                <h4 style="color: #ff4444; margin-bottom: var(--spacing-md);">⚠️ Weaknesses</h4>
                                <ul style="list-style: none; padding: 0;">
                                    ${analysis.weaknesses.map(w => `<li style="padding: var(--spacing-xs) 0; color: var(--text-primary);">• ${w}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        ${analysis.opportunities ? `
                            <div>
                                <h4 style="color: #ffaa00; margin-bottom: var(--spacing-md);">🎯 Opportunities</h4>
                                <ul style="list-style: none; padding: 0;">
                                    ${analysis.opportunities.map(o => `<li style="padding: var(--spacing-xs) 0; color: var(--text-primary);">• ${o}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        ${analysis.threats ? `
                            <div>
                                <h4 style="color: #ff6b6b; margin-bottom: var(--spacing-md);">⚠️ Threats</h4>
                                <ul style="list-style: none; padding: 0;">
                                    ${analysis.threats.map(t => `<li style="padding: var(--spacing-xs) 0; color: var(--text-primary);">• ${t}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Display resources stats
     */
    async displayResourcesStats() {
        const stats = await this.fetchTabStats('resources');
        if (!stats) return;

        const container = document.getElementById('tab-resources');
        if (!container) return;

        let statsSection = container.querySelector('.resources-stats-section');
        if (!statsSection) {
            statsSection = document.createElement('div');
            statsSection.className = 'resources-stats-section';
            statsSection.style.cssText = 'margin-bottom: var(--spacing-lg);';
            container.insertBefore(statsSection, container.firstChild);
        }

        statsSection.innerHTML = `
            <div class="card" style="margin-bottom: var(--spacing-lg);">
                <div class="card-header">
                    <h2 class="card-title">💎 Resources Overview</h2>
                </div>
                <div style="padding: var(--spacing-lg);">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-lg);">
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Total Power</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: var(--primary);">${(stats.total_power || 0).toLocaleString()}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Available Power</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: #44ff44;">${(stats.available_power || 0).toLocaleString()}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Gold</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: #ffaa00;">${(stats.resources?.gold || 0).toLocaleString()}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Gems</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: #4ecdc4;">${stats.resources?.gems || 0}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Energy</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: #95e1d3;">
                                ${stats.resources?.energy || 0}/${stats.resources?.max_energy || 0}
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">Trophies</div>
                            <div style="font-size: 2.5em; font-weight: 700; color: var(--secondary);">${stats.resources?.trophies || 0}</div>
                        </div>
                    </div>
                    ${stats.power_breakdown ? `
                        <div style="margin-top: var(--spacing-lg); padding-top: var(--spacing-lg); border-top: 1px solid var(--border-primary);">
                            <h3 style="margin-bottom: var(--spacing-md);">Power Breakdown</h3>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: var(--spacing-md);">
                                ${Object.entries(stats.power_breakdown).map(([type, value]) => `
                                    <div>
                                        <div style="font-size: 0.85em; color: var(--text-secondary);">${type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                                        <div style="font-size: 1.5em; font-weight: 700; color: var(--primary);">${(value || 0).toLocaleString()}</div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    /**
     * Generic stats table display
     */
    displayStatsTable(containerId, config) {
        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.style.cssText = 'margin-top: var(--spacing-lg);';
            const tabContainer = document.getElementById('tab-battle');
            if (tabContainer) tabContainer.appendChild(container);
        }

        const { title, data, formatValue } = config;
        
        container.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">${title}</h3>
                </div>
                <div style="padding: var(--spacing-lg);">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid var(--border-primary);">
                                <th style="padding: var(--spacing-md); text-align: left; color: var(--text-secondary);">Type</th>
                                <th style="padding: var(--spacing-md); text-align: left; color: var(--text-secondary);">Statistics</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${Object.entries(data).map(([key, value]) => `
                                <tr style="border-bottom: 1px solid var(--border-primary);">
                                    <td style="padding: var(--spacing-md); font-weight: 600; color: var(--text-primary);">
                                        ${key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}
                                    </td>
                                    <td style="padding: var(--spacing-md); color: var(--text-secondary);">
                                        ${formatValue ? formatValue(value) : JSON.stringify(value)}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    /**
     * Display stats for all remaining tabs
     */
    async displayTabStats(tabName) {
        const stats = await this.fetchTabStats(tabName);
        if (!stats) return;

        const container = document.getElementById(`tab-${tabName}`);
        if (!container) return;

        // Create stats section
        let statsSection = container.querySelector('.tab-stats-section');
        if (!statsSection) {
            statsSection = document.createElement('div');
            statsSection.className = 'tab-stats-section';
            statsSection.style.cssText = 'margin-bottom: var(--spacing-lg);';
            container.insertBefore(statsSection, container.firstChild);
        }

        // Generate stats display based on tab
        statsSection.innerHTML = this.generateStatsDisplay(tabName, stats);
    }

    /**
     * Generate stats display HTML for any tab
     */
    generateStatsDisplay(tabName, stats) {
        // Extract key metrics
        const keyMetrics = this.extractKeyMetrics(stats);
        
        return `
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">📊 ${this.getTabDisplayName(tabName)} Statistics</h2>
                </div>
                <div style="padding: var(--spacing-lg);">
                    ${keyMetrics.length > 0 ? `
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-lg); margin-bottom: var(--spacing-lg);">
                            ${keyMetrics.map(metric => `
                                <div>
                                    <div style="font-size: 0.9em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">${metric.label}</div>
                                    <div style="font-size: 2em; font-weight: 700; color: var(--primary);">${metric.value}</div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                    ${this.generateDetailedStats(stats)}
                </div>
            </div>
        `;
    }

    /**
     * Extract key metrics from stats object
     */
    extractKeyMetrics(stats) {
        const metrics = [];
        
        // Common patterns
        if (stats.total_battles !== undefined) metrics.push({ label: 'Total Battles', value: stats.total_battles });
        if (stats.wins !== undefined) metrics.push({ label: 'Wins', value: stats.wins });
        if (stats.win_rate !== undefined) metrics.push({ label: 'Win Rate', value: `${stats.win_rate.toFixed(1)}%` });
        if (stats.total_points !== undefined) metrics.push({ label: 'Total Points', value: stats.total_points.toLocaleString() });
        if (stats.rank !== undefined) metrics.push({ label: 'Rank', value: `#${stats.rank}` });
        if (stats.active_tournaments !== undefined) metrics.push({ label: 'Active Tournaments', value: stats.active_tournaments });
        if (stats.total_locations !== undefined) metrics.push({ label: 'Locations', value: stats.total_locations });
        if (stats.total_connections !== undefined) metrics.push({ label: 'Connections', value: stats.total_connections });
        if (stats.research_level !== undefined) metrics.push({ label: 'Research Level', value: stats.research_level });
        if (stats.hardware_level !== undefined) metrics.push({ label: 'Hardware Level', value: stats.hardware_level });
        
        return metrics.slice(0, 6); // Limit to 6 key metrics
    }

    /**
     * Generate detailed stats display
     */
    generateDetailedStats(stats) {
        let html = '';
        
        // Display arrays as tables
        Object.entries(stats).forEach(([key, value]) => {
            if (Array.isArray(value) && value.length > 0) {
                html += this.generateArrayTable(key, value);
            } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                // Display nested objects
                if (Object.keys(value).length > 0 && Object.keys(value).length < 10) {
                    html += this.generateObjectTable(key, value);
                }
            }
        });
        
        return html;
    }

    /**
     * Generate table from array
     */
    generateArrayTable(key, array) {
        if (array.length === 0) return '';
        
        // Get keys from first object
        const keys = Object.keys(array[0] || {});
        if (keys.length === 0) return '';
        
        return `
            <div style="margin-top: var(--spacing-lg);">
                <h3 style="margin-bottom: var(--spacing-md);">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid var(--border-primary);">
                                ${keys.map(k => `
                                    <th style="padding: var(--spacing-md); text-align: left; color: var(--text-secondary);">
                                        ${k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                    </th>
                                `).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${array.slice(0, 10).map(item => `
                                <tr style="border-bottom: 1px solid var(--border-primary);">
                                    ${keys.map(k => `
                                        <td style="padding: var(--spacing-md);">
                                            ${this.formatValue(item[k])}
                                        </td>
                                    `).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    /**
     * Generate table from object
     */
    generateObjectTable(key, obj) {
        return `
            <div style="margin-top: var(--spacing-lg);">
                <h3 style="margin-bottom: var(--spacing-md);">${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-md);">
                    ${Object.entries(obj).map(([k, v]) => `
                        <div style="padding: var(--spacing-md); background: var(--bg-secondary); border-radius: var(--border-radius);">
                            <div style="font-size: 0.85em; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">
                                ${k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </div>
                            <div style="font-size: 1.2em; font-weight: 600; color: var(--primary);">
                                ${this.formatValue(v)}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Format value for display
     */
    formatValue(value) {
        if (value === null || value === undefined) return 'N/A';
        if (typeof value === 'boolean') return value ? 'Yes' : 'No';
        if (typeof value === 'number') {
            if (value > 1000) return value.toLocaleString();
            if (value < 1 && value > 0) return value.toFixed(2);
            return value.toString();
        }
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    }

    /**
     * Helper methods
     */
    getActivityIcon(type) {
        const icons = {
            'battle_won': '⚔️',
            'battle_lost': '💥',
            'achievement': '🏆',
            'tournament': '🎯',
            'level_up': '⬆️',
            'reward': '🎁'
        };
        return icons[type] || '📌';
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 60) return `${minutes} minutes ago`;
        if (hours < 24) return `${hours} hours ago`;
        if (days < 7) return `${days} days ago`;
        return date.toLocaleDateString();
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    formatDuration(seconds) {
        if (!seconds) return 'N/A';
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${minutes}m ${secs}s`;
    }

    getPriorityColor(priority) {
        const colors = {
            'high': '#ff4444',
            'medium': '#ffaa00',
            'low': '#44ff44'
        };
        return colors[priority?.toLowerCase()] || '#666';
    }

    getTabDisplayName(tabName) {
        const names = {
            'overview': 'Overview',
            'battle': 'Battle',
            'tournaments': 'Tournaments',
            'history': 'History',
            'leaderboard': 'Leaderboard',
            'intelligence': 'Intelligence',
            'resources': 'Resources',
            'series': 'Series',
            'gps': 'GPS',
            'news': 'News',
            'peers': 'Peers & Network',
            'timepocket': 'Timepocket Real-Time',
            'trading': 'Trophy Trading & Collectibles',
            'missions': 'Missions & Quests',
            'ai-research': 'AI Research',
            'rewards': 'Rewards',
            'technology': 'Technology & Science',
            'autoplay': 'Autoplay & Recording',
            'social': 'Social',
            'teams': 'Teams & Groups',
            'alliances': 'Alliances',
            'groups-destroy': 'Group Destruction',
            'bonus-level': 'Bonus Level',
            'death-teleport': 'Death Teleport Install',
            'militia-forces': 'Militia Forces',
            'legal-content': 'Legal Content',
            'tech-hardware': 'Tech & Hardware',
            'death-portal': 'Death Portal',
            'experience-recount': 'Experience Recount',
            'enhanced-system': 'Enhanced Battle System'
        };
        return names[tabName] || tabName;
    }
}

// Export for use in battle page
if (typeof window !== 'undefined') {
    window.BattleStatsDisplay = BattleStatsDisplay;
}
