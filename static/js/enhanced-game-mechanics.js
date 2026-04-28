/**
 * Enhanced Game Mechanics - Quests, Tournaments, Seasons, Point Notifications
 * Comprehensive integration with new game mechanics API
 */

(function() {
    'use strict';
    
    const BASE_URL = window.location.origin;
    const userId = localStorage.getItem('game_user_id') || 'default_user';
    
    // ========================================================================
    // POINT NOTIFICATION SYSTEM
    // ========================================================================
    
    class PointNotificationSystem {
        constructor() {
            this.container = null;
            this.notifications = [];
            this.init();
        }
        
        init() {
            // Create notification container
            this.container = document.createElement('div');
            this.container.id = 'point-notifications-container';
            this.container.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
                pointer-events: none;
                max-width: 350px;
            `;
            document.body.appendChild(this.container);
        }
        
        show(pointsData) {
            const notification = document.createElement('div');
            notification.className = 'point-notification';
            notification.style.cssText = `
                background: linear-gradient(135deg, rgba(0, 255, 136, 0.95), rgba(0, 212, 255, 0.95));
                color: #000;
                padding: 15px 20px;
                border-radius: 12px;
                box-shadow: 0 8px 24px rgba(0, 255, 136, 0.4);
                animation: slideInRight 0.3s ease-out;
                pointer-events: auto;
                backdrop-filter: blur(10px);
                border: 2px solid rgba(255, 255, 255, 0.3);
            `;
            
            let pointsText = '<div style="font-weight: 700; font-size: 1.1rem; margin-bottom: 8px;">✨ Points Earned!</div>';
            const points = pointsData.points_awarded || {};
            
            if (points.xp) pointsText += `<div style="margin: 4px 0;">💚 +${points.xp.toLocaleString()} XP</div>`;
            if (points.coins) pointsText += `<div style="margin: 4px 0;">💰 +${points.coins.toLocaleString()} Coins</div>`;
            if (points.credits) pointsText += `<div style="margin: 4px 0;">💳 +${points.credits.toLocaleString()} Credits</div>`;
            if (points.tokens) pointsText += `<div style="margin: 4px 0;">🎫 +${points.tokens.toLocaleString()} Tokens</div>`;
            if (points.battle_points) pointsText += `<div style="margin: 4px 0;">⚔️ +${points.battle_points.toLocaleString()} Battle Points</div>`;
            
            // Add stat points
            if (points.creativity) pointsText += `<div style="margin: 4px 0;">🎨 +${points.creativity} Creativity</div>`;
            if (points.efficiency) pointsText += `<div style="margin: 4px 0;">⚡ +${points.efficiency} Efficiency</div>`;
            if (points.quality) pointsText += `<div style="margin: 4px 0;">✨ +${points.quality} Quality</div>`;
            if (points.knowledge) pointsText += `<div style="margin: 4px 0;">📚 +${points.knowledge} Knowledge</div>`;
            if (points.social) pointsText += `<div style="margin: 4px 0;">👥 +${points.social} Social</div>`;
            
            notification.innerHTML = pointsText;
            this.container.appendChild(notification);
            this.notifications.push(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                notification.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                    const index = this.notifications.indexOf(notification);
                    if (index > -1) this.notifications.splice(index, 1);
                }, 300);
            }, 5000);
            
            // Click to dismiss
            notification.addEventListener('click', () => {
                notification.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                    const index = this.notifications.indexOf(notification);
                    if (index > -1) this.notifications.splice(index, 1);
                }, 300);
            });
        }
        
        awardAndShow(action, difficulty = 'normal', multiplier = 1.0) {
            fetch(`${BASE_URL}/api/game-mechanics/award-points`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: userId,
                    action: action,
                    difficulty: difficulty,
                    multiplier: multiplier
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success && data.points_awarded) {
                    this.show(data);
                    // Trigger refresh if callback exists
                    if (window.refreshGameData) window.refreshGameData();
                }
            })
            .catch(err => console.error('Error awarding points:', err));
        }
    }
    
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    // Initialize notification system
    window.pointNotifications = new PointNotificationSystem();
    
    // ========================================================================
    // QUESTS SYSTEM
    // ========================================================================
    
    window.loadQuests = async function() {
        const container = document.getElementById('quests-list');
        if (!container) return;
        
        container.innerHTML = '<div class="skeleton-loader" style="height: 150px;"></div>';
        
        try {
            const res = await fetch(`${BASE_URL}/api/game-mechanics/quests?user_id=${userId}`);
            const data = await res.json();
            
            if (data.success && data.quests && data.quests.length > 0) {
                container.innerHTML = data.quests.map(quest => {
                    const progress = quest.current ? (quest.current / quest.target * 100) : 0;
                    return `
                        <div class="action-card" style="margin-bottom: 15px;">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                                <div>
                                    <h3 style="color: var(--primary); margin-bottom: 5px;">${quest.name}</h3>
                                    <p style="color: rgba(255,255,255,0.7); font-size: 0.9rem;">${quest.description}</p>
                                </div>
                                <span style="background: rgba(0,255,136,0.2); padding: 4px 12px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">
                                    ${quest.status === 'completed' ? '✓ Completed' : 'Active'}
                                </span>
                            </div>
                            <div style="margin: 10px 0;">
                                <div style="background: rgba(255,255,255,0.1); border-radius: 8px; height: 8px; overflow: hidden;">
                                    <div style="background: var(--primary); height: 100%; width: ${progress}%; transition: width 0.3s;"></div>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 0.85rem; color: rgba(255,255,255,0.6);">
                                    <span>${quest.current || 0} / ${quest.target}</span>
                                    <span>${Math.round(progress)}%</span>
                                </div>
                            </div>
                            <div style="display: flex; gap: 10px; margin-top: 15px;">
                                <button class="action-btn" onclick="completeQuest('${quest.quest_id}')" 
                                        ${quest.status === 'completed' ? 'disabled style="opacity: 0.5;"' : ''}>
                                    ${quest.status === 'completed' ? '✓ Completed' : '🎯 Complete Quest'}
                                </button>
                                <div style="flex: 1; text-align: right; padding-top: 8px; color: #ffd700; font-weight: 600;">
                                    💰 ${quest.reward_points || 0} Reward
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: rgba(255,255,255,0.5);">
                        <div style="font-size: 3rem; margin-bottom: 15px;">📜</div>
                        <div>No active quests</div>
                        <button class="action-btn" onclick="createQuest('daily_battle')" style="margin-top: 20px;">
                            Create Daily Quest
                        </button>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading quests:', error);
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--error);">Failed to load quests</div>';
        }
    };
    
    window.createQuest = async function(questType) {
        try {
            const res = await fetch(`${BASE_URL}/api/game-mechanics/quest/create`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: userId,
                    quest_type: questType,
                    difficulty: 'normal'
                })
            });
            const data = await res.json();
            
            if (data.success) {
                loadQuests();
                if (window.toast) toast.success('Quest created!');
            }
        } catch (error) {
            console.error('Error creating quest:', error);
        }
    };
    
    window.completeQuest = async function(questId) {
        try {
            const res = await fetch(`${BASE_URL}/api/game-mechanics/quest/complete`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: userId,
                    quest_id: questId
                })
            });
            const data = await res.json();
            
            if (data.success) {
                if (data.comprehensive_points && data.comprehensive_points.points_awarded) {
                    window.pointNotifications.show(data.comprehensive_points);
                }
                loadQuests();
                if (window.toast) toast.success('Quest completed!');
            }
        } catch (error) {
            console.error('Error completing quest:', error);
        }
    };
    
    // ========================================================================
    // DAILY CHALLENGES
    // ========================================================================
    
    window.loadDailyChallenges = async function() {
        const container = document.getElementById('daily-challenges-list');
        if (!container) return;
        
        container.innerHTML = '<div class="skeleton-loader" style="height: 150px;"></div>';
        
        try {
            const res = await fetch(`${BASE_URL}/api/game-mechanics/daily-challenges?user_id=${userId}`);
            const data = await res.json();
            
            if (data.success && data.challenges && data.challenges.length > 0) {
                container.innerHTML = data.challenges.map(challenge => {
                    const progress = challenge.current ? (challenge.current / challenge.target * 100) : 0;
                    const multiplier = challenge.reward_multiplier || 1.0;
                    return `
                        <div class="action-card" style="margin-bottom: 15px; ${challenge.status === 'completed' ? 'opacity: 0.7;' : ''}">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                                <div>
                                    <h3 style="color: var(--primary); margin-bottom: 5px;">
                                        ${challenge.name}
                                        ${multiplier > 1 ? `<span style="background: rgba(255,215,0,0.3); padding: 2px 8px; border-radius: 8px; font-size: 0.8rem; margin-left: 8px;">${multiplier}x</span>` : ''}
                                    </h3>
                                    <p style="color: rgba(255,255,255,0.7); font-size: 0.9rem;">${challenge.description}</p>
                                </div>
                                ${challenge.status === 'completed' ? '<span style="color: var(--success);">✓</span>' : ''}
                            </div>
                            <div style="margin: 10px 0;">
                                <div style="background: rgba(255,255,255,0.1); border-radius: 8px; height: 8px; overflow: hidden;">
                                    <div style="background: var(--primary); height: 100%; width: ${progress}%; transition: width 0.3s;"></div>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 0.85rem; color: rgba(255,255,255,0.6);">
                                    <span>${challenge.current || 0} / ${challenge.target}</span>
                                    <span>${Math.round(progress)}%</span>
                                </div>
                            </div>
                            ${challenge.status !== 'completed' ? `
                                <button class="action-btn" onclick="completeDailyChallenge('${challenge.challenge_id}')" 
                                        style="margin-top: 10px; width: 100%;" ${progress < 100 ? 'disabled style="opacity: 0.5;"' : ''}>
                                    ${progress < 100 ? 'Keep Going!' : '🎯 Complete Challenge'}
                                </button>
                            ` : ''}
                        </div>
                    `;
                }).join('');
            } else {
                container.innerHTML = '<div style="text-align: center; padding: 40px; color: rgba(255,255,255,0.5);">No daily challenges available</div>';
            }
        } catch (error) {
            console.error('Error loading daily challenges:', error);
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--error);">Failed to load challenges</div>';
        }
    };
    
    window.completeDailyChallenge = async function(challengeId) {
        try {
            const res = await fetch(`${BASE_URL}/api/game-mechanics/daily-challenge/complete`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: userId,
                    challenge_id: challengeId
                })
            });
            const data = await res.json();
            
            if (data.success) {
                if (data.points_awarded && data.points_awarded.points_awarded) {
                    window.pointNotifications.show(data.points_awarded);
                }
                loadDailyChallenges();
                if (window.toast) toast.success('Challenge completed!');
            }
        } catch (error) {
            console.error('Error completing challenge:', error);
        }
    };
    
    // ========================================================================
    // TOURNAMENTS
    // ========================================================================
    
    window.loadTournaments = async function() {
        const container = document.getElementById('tournaments-list');
        if (!container) return;
        
        container.innerHTML = '<div class="skeleton-loader" style="height: 150px;"></div>';
        
        try {
            const res = await fetch(`${BASE_URL}/api/battle/fantasy/tournaments?status=open`);
            const data = await res.json();
            
            if (data.success && data.tournaments && data.tournaments.length > 0) {
                container.innerHTML = data.tournaments.map(tournament => {
                    const participants = tournament.participants ? tournament.participants.length : 0;
                    const maxParticipants = tournament.max_participants || 16;
                    const isJoined = tournament.participants && tournament.participants.includes(userId);
                    
                    return `
                        <div class="action-card" style="margin-bottom: 15px;">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                                <div>
                                    <h3 style="color: var(--battle-primary); margin-bottom: 5px;">${tournament.name}</h3>
                                    <p style="color: rgba(255,255,255,0.7); font-size: 0.9rem;">Type: ${tournament.type || 'Single Elimination'}</p>
                                </div>
                                <span style="background: rgba(0,255,136,0.2); padding: 4px 12px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">
                                    ${tournament.status || 'Open'}
                                </span>
                            </div>
                            <div style="margin: 10px 0; display: flex; gap: 20px; font-size: 0.9rem; color: rgba(255,255,255,0.6);">
                                <div>👥 ${participants} / ${maxParticipants}</div>
                                <div>💰 Entry: ${tournament.entry_fee || 0}</div>
                            </div>
                            ${tournament.prize_pool ? `
                                <div style="margin: 10px 0; padding: 10px; background: rgba(255,215,0,0.1); border-radius: 8px;">
                                    <div style="font-size: 0.9rem; color: #ffd700; font-weight: 600;">Prize Pool:</div>
                                    <div style="display: flex; gap: 15px; margin-top: 5px; font-size: 0.85rem;">
                                        ${Object.entries(tournament.prize_pool).map(([rank, amount]) => 
                                            `<span>${rank}: ${amount}</span>`
                                        ).join(' • ')}
                                    </div>
                                </div>
                            ` : ''}
                            <button class="action-btn" onclick="joinTournament('${tournament.tournament_id || tournament.id}')" 
                                    style="margin-top: 10px; width: 100%;" ${isJoined ? 'disabled style="opacity: 0.5;"' : ''}>
                                ${isJoined ? '✓ Already Joined' : '🏰 Join Tournament'}
                            </button>
                        </div>
                    `;
                }).join('');
            } else {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: rgba(255,255,255,0.5);">
                        <div style="font-size: 3rem; margin-bottom: 15px;">🏰</div>
                        <div>No active tournaments</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading tournaments:', error);
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--error);">Failed to load tournaments</div>';
        }
    };
    
    window.joinTournament = async function(tournamentId) {
        try {
            const res = await fetch(`${BASE_URL}/api/battle/fantasy/tournaments/${encodeURIComponent(tournamentId)}/join`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId })
            });
            const data = await res.json();
            
            if (data.success) {
                loadTournaments();
                if (window.toast) toast.success('Joined tournament!');
            } else {
                if (window.toast) toast.error(data.error || 'Failed to join tournament');
            }
        } catch (error) {
            console.error('Error joining tournament:', error);
        }
    };
    
    // ========================================================================
    // SEASONS
    // ========================================================================
    
    window.loadSeasons = async function() {
        const container = document.getElementById('seasons-list');
        if (!container) return;
        
        container.innerHTML = '<div class="skeleton-loader" style="height: 200px;"></div>';
        
        try {
            // For now, we'll create a placeholder season
            const season = {
                season_id: 'current_season',
                name: 'Current Season',
                status: 'active',
                start_date: new Date().toISOString(),
                end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
            };
            
            const daysLeft = Math.ceil((new Date(season.end_date) - new Date()) / (1000 * 60 * 60 * 24));
            
            container.innerHTML = `
                <div class="action-card" style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                        <div>
                            <h3 style="color: var(--battle-primary); margin-bottom: 5px;">${season.name}</h3>
                            <p style="color: rgba(255,255,255,0.7); font-size: 0.9rem;">${daysLeft} days remaining</p>
                        </div>
                        <span style="background: rgba(0,255,136,0.2); padding: 4px 12px; border-radius: 12px; font-size: 0.85rem; font-weight: 600;">
                            ${season.status}
                        </span>
                    </div>
                    <button class="action-btn" onclick="viewSeasonLeaderboard('${season.season_id}')" style="margin-top: 10px; width: 100%;">
                        📊 View Leaderboard
                    </button>
                </div>
            `;
        } catch (error) {
            console.error('Error loading seasons:', error);
            container.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--error);">Failed to load seasons</div>';
        }
    };
    
    window.viewSeasonLeaderboard = async function(seasonId) {
        try {
            const res = await fetch(`${BASE_URL}/api/battle/season/${seasonId}/leaderboard?limit=20`);
            const data = await res.json();
            
            if (data.success && data.leaderboard) {
                const modal = document.createElement('div');
                modal.style.cssText = `
                    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                    background: rgba(0,0,0,0.8); z-index: 10000;
                    display: flex; align-items: center; justify-content: center;
                `;
                modal.innerHTML = `
                    <div style="background: var(--bg-card); padding: 30px; border-radius: 16px; max-width: 600px; max-height: 80vh; overflow-y: auto;">
                        <h2 style="margin-bottom: 20px; color: var(--primary);">Season Leaderboard</h2>
                        <div>
                            ${data.leaderboard.map((player, index) => `
                                <div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                                    <div>
                                        <span style="font-weight: 600;">#${player.rank}</span>
                                        <span style="margin-left: 10px;">${player.user_id}</span>
                                    </div>
                                    <span style="color: var(--primary); font-weight: 600;">${player.points}</span>
                                </div>
                            `).join('')}
                        </div>
                        <button onclick="this.closest('div').parentElement.remove()" 
                                style="margin-top: 20px; padding: 10px 20px; background: var(--primary); border: none; border-radius: 8px; cursor: pointer;">
                            Close
                        </button>
                    </div>
                `;
                document.body.appendChild(modal);
            }
        } catch (error) {
            console.error('Error loading season leaderboard:', error);
        }
    };
    
    // Auto-load on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            // Load data when tabs are shown
            setTimeout(() => {
                if (document.getElementById('quests-list')) loadQuests();
                if (document.getElementById('daily-challenges-list')) loadDailyChallenges();
                if (document.getElementById('tournaments-list')) loadTournaments();
                if (document.getElementById('seasons-list')) loadSeasons();
            }, 1000);
        });
    } else {
        setTimeout(() => {
            if (document.getElementById('quests-list')) loadQuests();
            if (document.getElementById('daily-challenges-list')) loadDailyChallenges();
            if (document.getElementById('tournaments-list')) loadTournaments();
            if (document.getElementById('seasons-list')) loadSeasons();
        }, 1000);
    }
    
})();
