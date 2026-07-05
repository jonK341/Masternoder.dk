/**
 * Real-Time Client - WebSocket for live updates
 */
class RealtimeClient {
    constructor() {
        this.socket = null;
        this.userId = localStorage.getItem('game_user_id') || 'default_user';
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        if (this.socket && this.connected) {
            return;
        }

        try {
            // Use Socket.IO client
            if (typeof io !== 'undefined') {
                this.socket = io(window.location.origin, {
                    query: {
                        user_id: this.userId
                    },
                    transports: ['websocket', 'polling']
                });

                this.socket.on('connect', () => {
                    this.connected = true;
                    this.reconnectAttempts = 0;
                    console.log('[Realtime] Connected');
                    this.onConnect();
                });

                this.socket.on('disconnect', () => {
                    this.connected = false;
                    console.log('[Realtime] Disconnected');
                    this.onDisconnect();
                });

                this.socket.on('points_update', (data) => {
                    this.handlePointsUpdate(data);
                });

                this.socket.on('quest_update', (data) => {
                    this.handleQuestUpdate(data);
                });

                this.socket.on('battle_update', (data) => {
                    this.handleBattleUpdate(data);
                });

                this.socket.on('reward_notification', (data) => {
                    this.handleRewardNotification(data);
                });

                this.socket.on('level_up', (data) => {
                    this.handleLevelUp(data);
                });

                this.socket.on('achievement_unlock', (data) => {
                    this.handleAchievementUnlock(data);
                });

                this.socket.on('leaderboard_update', (data) => {
                    this.handleLeaderboardUpdate(data);
                });
            } else {
                console.warn('[Realtime] Socket.IO not loaded');
            }
        } catch (error) {
            console.error('[Realtime] Connection error:', error);
            this.attemptReconnect();
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
            this.connected = false;
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`[Realtime] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connect(), delay);
        } else {
            console.error('[Realtime] Max reconnection attempts reached');
        }
    }

    onConnect() {
        // Subscribe to user room
        if (this.socket) {
            this.socket.emit('subscribe', {
                user_id: this.userId,
                room: `user_${this.userId}`
            });
        }
    }

    onDisconnect() {
        // Attempt to reconnect
        this.attemptReconnect();
    }

    handlePointsUpdate(data) {
        console.log('[Realtime] Points update:', data);
        // Update unified point counters
        if (window.unifiedPointCounters) {
            window.unifiedPointCounters.updateAllCounters();
        }
        // Show notification
        if (typeof toast !== 'undefined' && data.points_earned) {
            toast.success(`+${data.points_earned} points!`);
        }
    }

    handleQuestUpdate(data) {
        console.log('[Realtime] Quest update:', data);
        // Reload quests if on quest page
        if (window.location.pathname.includes('/quests')) {
            if (typeof loadQuests === 'function') {
                loadQuests();
            }
        }
    }

    handleBattleUpdate(data) {
        console.log('[Realtime] Battle update:', data);
        // Update battle UI if on battle page
        if (window.location.pathname.includes('/battle')) {
            if (typeof updateBattleUI === 'function') {
                updateBattleUI(data);
            }
        }
    }

    handleRewardNotification(data) {
        console.log('[Realtime] Reward notification:', data);
        // Show reward notification
        if (typeof toast !== 'undefined') {
            toast.success(`🎁 New reward: ${data.description || 'Reward available!'}`);
        }
        // Reload rewards if on rewards page
        if (window.location.pathname.includes('/rewards') || window.location.pathname.includes('/profile')) {
            if (typeof loadRewards === 'function') {
                loadRewards();
            }
        }
    }

    handleLevelUp(data) {
        console.log('[Realtime] Level up:', data);
        // Show level up notification
        if (typeof toast !== 'undefined') {
            toast.success(`🎉 Level Up! You reached level ${data.new_level}!`);
        }
        // Update level display
        if (window.unifiedPointCounters) {
            window.unifiedPointCounters.updateAllCounters();
        }
    }

    handleAchievementUnlock(data) {
        console.log('[Realtime] Achievement unlock:', data);
        // Show achievement notification
        if (typeof toast !== 'undefined') {
            toast.success(`🏆 Achievement Unlocked: ${data.achievement_name || 'Achievement'}!`);
        }
    }

    handleLeaderboardUpdate(data) {
        console.log('[Realtime] Leaderboard update:', data);
        // Update leaderboard if visible
        if (typeof updateLeaderboard === 'function') {
            updateLeaderboard(data);
        }
    }

    emit(event, data) {
        if (this.socket && this.connected) {
            this.socket.emit(event, data);
        }
    }
}

// Global instance
const realtimeClient = new RealtimeClient();

// Auto-connect on page load
document.addEventListener('DOMContentLoaded', () => {
    realtimeClient.connect();
});

// Reconnect on visibility change
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && !realtimeClient.connected) {
        realtimeClient.connect();
    }
});

