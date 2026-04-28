/**
 * Template Services System
 * Integrates various backend services with the template system
 */
class TemplateServices {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || window.location.origin;
        this.services = new Map();
        this.cache = new Map();
        this.init();
    }

    init() {
        // Register available services
        this.registerService('points', this.getPointsService());
        this.registerService('leaderboard', this.getLeaderboardService());
        this.registerService('stats', this.getStatsService());
        this.registerService('agents', this.getAgentsService());
        this.registerService('battle', this.getBattleService());
    }

    registerService(name, service) {
        this.services.set(name, service);
    }

    getService(name) {
        return this.services.get(name);
    }

    // Points Service
    getPointsService() {
        return {
            async getAllPoints(userId) {
                try {
                    const response = await fetch(`${this.baseUrl}/api/points/all?user_id=${userId}`);
                    const data = await response.json();
                    return data.points || {};
                } catch (error) {
                    console.error('Error fetching points:', error);
                    return {};
                }
            },
            async addPoints(userId, pointType, amount, source = 'template') {
                try {
                    const response = await fetch(`${this.baseUrl}/api/points/add`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, point_type: pointType, amount, source })
                    });
                    return await response.json();
                } catch (error) {
                    console.error('Error adding points:', error);
                    return { success: false, error: error.message };
                }
            }
        };
    }

    // Leaderboard Service
    getLeaderboardService() {
        return {
            async getLeaderboard(systemId, limit = 100) {
                try {
                    const response = await fetch(`${this.baseUrl}/api/leaderboard/${systemId}?limit=${limit}`);
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching leaderboard:', error);
                    return { success: false, leaderboard: [] };
                }
            },
            async getUserRank(userId, systemId) {
                try {
                    const response = await fetch(`${this.baseUrl}/api/leaderboard/${systemId}/rank?user_id=${userId}`);
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching user rank:', error);
                    return { rank: null, points: 0 };
                }
            }
        };
    }

    // Stats Service
    getStatsService() {
        return {
            async getStats(userId) {
                try {
                    const response = await fetch(`${this.baseUrl}/api/stats/summary?user_id=${userId}`);
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching stats:', error);
                    return {};
                }
            },
            async getActivityStats(userId) {
                try {
                    const response = await fetch(`${this.baseUrl}/api/stats/activity?user_id=${userId}`);
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching activity stats:', error);
                    return {};
                }
            }
        };
    }

    // Agents Service
    getAgentsService() {
        return {
            async getAgents(userId) {
                try {
                    const response = await fetch(`${this.baseUrl}/api/agent/get-all?user_id=${userId}`);
                    const data = await response.json();
                    return data.agents || [];
                } catch (error) {
                    console.error('Error fetching agents:', error);
                    return [];
                }
            },
            async getAgentDetails(agentId) {
                try {
                    const response = await fetch(`${this.baseUrl}/api/agent/${agentId}`);
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching agent details:', error);
                    return {};
                }
            }
        };
    }

    // Battle Service
    getBattleService() {
        return {
            async getBattleHistory(userId, limit = 10) {
                try {
                    const response = await fetch(`${this.baseUrl}/api/game/battle/history?user_id=${userId}&limit=${limit}`);
                    return await response.json();
                } catch (error) {
                    console.error('Error fetching battle history:', error);
                    return { success: false, history: [] };
                }
            },
            async startBattle(userId, battleType = 'quick') {
                try {
                    const response = await fetch(`${this.baseUrl}/api/game/battle/start`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: userId, battle_type: battleType })
                    });
                    return await response.json();
                } catch (error) {
                    console.error('Error starting battle:', error);
                    return { success: false, error: error.message };
                }
            }
        };
    }

    // Generic service call with caching
    async callService(serviceName, method, ...args) {
        const cacheKey = `${serviceName}.${method}.${JSON.stringify(args)}`;
        const cacheTime = 5000; // 5 seconds cache

        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < cacheTime) {
                return cached.data;
            }
        }

        const service = this.getService(serviceName);
        if (!service || !service[method]) {
            throw new Error(`Service ${serviceName} or method ${method} not found`);
        }

        const result = await service[method](...args);
        this.cache.set(cacheKey, { data: result, timestamp: Date.now() });
        return result;
    }

    // Clear cache
    clearCache(serviceName = null) {
        if (serviceName) {
            for (const key of this.cache.keys()) {
                if (key.startsWith(serviceName)) {
                    this.cache.delete(key);
                }
            }
        } else {
            this.cache.clear();
        }
    }

    // Auto-update service data
    startAutoUpdate(serviceName, method, interval, ...args) {
        const update = async () => {
            try {
                const data = await this.callService(serviceName, method, ...args);
                this.dispatchServiceUpdate(serviceName, method, data);
            } catch (error) {
                console.error(`Auto-update error for ${serviceName}.${method}:`, error);
            }
        };

        update(); // Initial call
        return setInterval(update, interval);
    }

    // Dispatch service update event
    dispatchServiceUpdate(serviceName, method, data) {
        const event = new CustomEvent('serviceUpdate', {
            detail: { serviceName, method, data }
        });
        document.dispatchEvent(event);
    }
}

// Initialize template services
window.templateServices = new TemplateServices();

// Listen for service updates
document.addEventListener('serviceUpdate', (event) => {
    const { serviceName, method, data } = event.detail;
    console.log(`Service update: ${serviceName}.${method}`, data);
});
