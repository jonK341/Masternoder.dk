/**
 * Points Page JavaScript
 * Handles point counters, rewards linking, and counting/tracking
 */

const BASE_URL = window.location.origin;
const userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';

// Tab Management
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    loadQuickStats();
    loadPointCounters();
    loadRewards();
    initializeModals();
});

/**
 * Initialize tab switching
 */
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Update buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Update content
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`tab-${tabName}`).classList.add('active');
            
            // Load content based on tab
            switch(tabName) {
                case 'counters':
                    loadPointCounters();
                    break;
                case 'rewards':
                    loadRewards();
                    break;
                case 'counting':
                    loadCountingTracking();
                    break;
                case 'history':
                    loadHistory();
                    break;
            }
        });
    });
}

/**
 * Load quick stats
 */
async function loadQuickStats() {
    try {
        // Load level info
        const levelResponse = await fetch(
            `${BASE_URL}/api/game/hunters/level?user_id=${userId}`
        );
        const levelData = await levelResponse.json();
        
        if (levelData.success) {
            document.getElementById('quick-stat-xp').textContent = 
                levelData.level_info.total_xp.toLocaleString();
            document.getElementById('quick-stat-level').textContent = 
                levelData.level_info.current_level;
        }
        
        // Load points
        if (window.unifiedPointCounters) {
            await window.unifiedPointCounters.updateAllCounters();
            const points = await window.unifiedPointCounters.getAllPoints(userId);
            if (points) {
                document.getElementById('quick-stat-total').textContent = 
                    points.total_points?.toLocaleString() || '0';
            }
        }
        
        // Load available rewards count
        const rewardsResponse = await fetch(
            `${BASE_URL}/api/game/hunters/rewards?user_id=${userId}`
        );
        const rewardsData = await rewardsResponse.json();
        
        if (rewardsData.success && rewardsData.rewards) {
            const availableCount = rewardsData.rewards.filter(r => !r.claimed && r.available).length;
            document.getElementById('quick-stat-rewards').textContent = availableCount;
        }
    } catch (error) {
        console.error('Error loading quick stats:', error);
    }
}

/**
 * Load point counters with rewards linking
 */
async function loadPointCounters() {
    const grid = document.getElementById('point-counters-grid');
    if (!grid) return;
    
    // Show skeleton loaders
    grid.innerHTML = Array(8).fill(0).map(() => 
        '<div class="skeleton-loader" style="height: 200px;"></div>'
    ).join('');
    
    try {
        // Get all point systems
        const response = await fetch(`${BASE_URL}/api/point-calculator/systems`);
        const data = await response.json();
        
        if (data.success && data.systems) {
            // Get point values
            const pointPromises = data.systems.slice(0, 20).map(async (system) => {
                try {
                    const valueResponse = await fetch(
                        `${BASE_URL}/api/point-calculator/system/${system}/value?user_id=${userId}`
                    );
                    const valueData = await valueResponse.json();
                    return {
                        name: system,
                        value: valueData.value || 0,
                        category: getCategoryForSystem(system)
                    };
                } catch (e) {
                    return { name: system, value: 0, category: 'other' };
                }
            });
            
            const points = await Promise.all(pointPromises);
            
            // Render counters
            grid.innerHTML = points.map(point => createCounterCard(point)).join('');
            
            // Add click handlers
            document.querySelectorAll('.point-counter-card').forEach(card => {
                card.addEventListener('click', () => {
                    showCounterDetails(card.dataset.pointType, card.dataset.pointValue);
                });
            });
            
            // Add reward indicators
            points.forEach(point => {
                updateRewardIndicator(point.name, point.value);
            });
        }
    } catch (error) {
        console.error('Error loading point counters:', error);
        grid.innerHTML = '<p style="text-align: center; color: white;">Failed to load point counters</p>';
    }
}

/**
 * Create counter card HTML
 */
function createCounterCard(point) {
    const formattedValue = point.value.toLocaleString();
    const progress = Math.min((point.value % 1000) / 1000 * 100, 100);
    
    return `
        <div class="point-counter-card" 
             data-point-type="${point.name}" 
             data-point-value="${point.value}"
             data-category="${point.category}">
            <div class="point-counter-header">
                <div class="point-counter-icon">${getIconForSystem(point.name)}</div>
                <div class="point-counter-name">${formatSystemName(point.name)}</div>
            </div>
            <div class="point-counter-value">${formattedValue}</div>
            <div class="point-counter-progress">
                <div class="point-counter-progress-bar" style="width: ${progress}%"></div>
            </div>
            <div class="reward-indicator" id="reward-indicator-${point.name}" style="display: none;">
                Loading rewards...
            </div>
        </div>
    `;
}

/**
 * Show counter details modal
 */
async function showCounterDetails(pointType, currentValue) {
    const modal = document.getElementById('counter-modal');
    const content = document.getElementById('counter-modal-content');
    
    // Show loading
    content.innerHTML = '<p>Loading...</p>';
    modal.style.display = 'block';
    
    try {
        // Get rewards for this point type
        const rewardsResponse = await fetch(
            `${BASE_URL}/api/game/hunters/rewards/by-points?point_type=${pointType}&current_value=${currentValue}`
        );
        const rewardsData = await rewardsResponse.json();
        
        // Get counting history
        const historyResponse = await fetch(
            `${BASE_URL}/api/game/hunters/xp-history?source=${pointType}&limit=20&user_id=${userId}`
        );
        const historyData = await historyResponse.json();
        
        // Render modal content
        content.innerHTML = `
            <h2>${formatSystemName(pointType)}</h2>
            <div style="font-size: 2em; font-weight: bold; color: #667eea; margin: 20px 0;">
                ${parseInt(currentValue).toLocaleString()} Points
            </div>
            
            <h3>Available Rewards</h3>
            <div class="rewards-grid" style="margin-top: 20px;">
                ${rewardsData.success && rewardsData.rewards ? 
                    rewardsData.rewards.map(r => createRewardCardHTML(r)).join('') :
                    '<p>No rewards available for this point type</p>'
                }
            </div>
            
            <h3 style="margin-top: 30px;">Recent Activity</h3>
            <div class="counting-timeline" style="margin-top: 20px;">
                ${historyData.success && historyData.history ? 
                    historyData.history.map(entry => createTimelineEntryHTML(entry)).join('') :
                    '<p>No activity yet</p>'
                }
            </div>
        `;
    } catch (error) {
        console.error('Error loading counter details:', error);
        content.innerHTML = '<p>Error loading details</p>';
    }
}

/**
 * Update reward indicator for a counter
 */
async function updateRewardIndicator(pointType, currentValue) {
    const indicator = document.getElementById(`reward-indicator-${pointType}`);
    if (!indicator) return;
    
    try {
        const response = await fetch(
            `${BASE_URL}/api/game/hunters/rewards/next?point_type=${pointType}&current_value=${currentValue}`
        );
        const data = await response.json();
        
        if (data.success && data.next_reward) {
            const pointsNeeded = data.next_reward.points_required - currentValue;
            if (pointsNeeded > 0) {
                indicator.textContent = `${pointsNeeded.toLocaleString()} until ${data.next_reward.name}`;
                indicator.style.display = 'block';
            } else {
                indicator.textContent = 'Reward available!';
                indicator.style.display = 'block';
                indicator.style.background = 'linear-gradient(135deg, #00ff88, #00cc6a)';
            }
        } else {
            indicator.style.display = 'none';
        }
    } catch (error) {
        console.error('Error updating reward indicator:', error);
        indicator.style.display = 'none';
    }
}

/**
 * Load rewards
 */
async function loadRewards(filter = 'available') {
    const grid = document.getElementById('rewards-grid');
    if (!grid) return;
    
    grid.innerHTML = '<div class="skeleton-loader" style="height: 200px;"></div>'.repeat(6);
    
    try {
        const response = await fetch(
            `${BASE_URL}/api/game/hunters/rewards?user_id=${userId}`
        );
        const data = await response.json();
        
        if (data.success && data.rewards) {
            let filteredRewards = data.rewards;
            
            if (filter === 'available') {
                filteredRewards = data.rewards.filter(r => !r.claimed && r.available);
            } else if (filter === 'claimed') {
                filteredRewards = data.rewards.filter(r => r.claimed);
            } else if (filter === 'upcoming') {
                filteredRewards = data.rewards.filter(r => !r.available && !r.claimed);
            }
            
            grid.innerHTML = filteredRewards.map(reward => createRewardCardHTML(reward)).join('');
            
            // Add claim handlers
            document.querySelectorAll('.reward-claim-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const rewardId = btn.dataset.rewardId;
                    await claimReward(rewardId);
                });
            });
        }
    } catch (error) {
        console.error('Error loading rewards:', error);
        grid.innerHTML = '<p style="text-align: center; color: white;">Failed to load rewards</p>';
    }
}

/**
 * Create reward card HTML
 */
function createRewardCardHTML(reward) {
    const isAvailable = reward.available && !reward.claimed;
    const isClaimed = reward.claimed;
    const isUpcoming = !reward.available && !reward.claimed;
    
    let cardClass = 'reward-card';
    if (isClaimed) cardClass += ' claimed';
    if (isAvailable) cardClass += ' available';
    if (isUpcoming) cardClass += ' upcoming';
    
    return `
        <div class="${cardClass}">
            <div class="reward-icon">${reward.icon || '🎁'}</div>
            <div class="reward-name">${reward.name}</div>
            <div class="reward-description">${reward.description || ''}</div>
            <div class="reward-requirements">
                ${reward.level_required ? `Level ${reward.level_required} required` : ''}
                ${reward.points_required ? `${reward.points_required.toLocaleString()} points required` : ''}
            </div>
            ${isAvailable ? 
                `<button class="reward-claim-btn" data-reward-id="${reward.id}">Claim Reward</button>` :
                isClaimed ? 
                    '<button class="reward-claim-btn" disabled>Claimed</button>' :
                    '<button class="reward-claim-btn" disabled>Not Available</button>'
            }
        </div>
    `;
}

/**
 * Claim a reward
 */
async function claimReward(rewardId) {
    try {
        const response = await fetch(`${BASE_URL}/api/game/hunters/rewards/claim`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: userId,
                reward_id: rewardId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Reward claimed successfully!');
            loadRewards();
            loadQuickStats();
        } else {
            alert('Error: ' + (data.error || 'Failed to claim reward'));
        }
    } catch (error) {
        console.error('Error claiming reward:', error);
        alert('Error claiming reward');
    }
}

/**
 * Load counting and tracking
 */
async function loadCountingTracking(period = 'today') {
    try {
        // Load point source breakdown
        const breakdownResponse = await fetch(
            `${BASE_URL}/api/game/hunters/xp-history?user_id=${userId}&limit=100`
        );
        const breakdownData = await breakdownResponse.json();
        
        if (breakdownData.success && breakdownData.history) {
            // Calculate breakdown
            const breakdown = {};
            breakdownData.history.forEach(entry => {
                if (!breakdown[entry.source]) {
                    breakdown[entry.source] = 0;
                }
                breakdown[entry.source] += entry.xp_amount;
            });
            
            // Render breakdown chart
            const chart = document.getElementById('breakdown-chart');
            if (chart) {
                chart.innerHTML = Object.entries(breakdown)
                    .map(([source, amount]) => `
                        <div style="margin: 10px 0; padding: 10px; background: rgba(102, 126, 234, 0.1); border-radius: 10px;">
                            <strong>${formatSystemName(source)}</strong>: ${amount.toLocaleString()} points
                        </div>
                    `).join('');
            }
            
            // Load timeline
            const timeline = document.getElementById('counting-timeline');
            if (timeline) {
                timeline.innerHTML = breakdownData.history.slice(0, 20)
                    .map(entry => createTimelineEntryHTML(entry))
                    .join('');
            }
        }
    } catch (error) {
        console.error('Error loading counting tracking:', error);
    }
}

/**
 * Create timeline entry HTML
 */
function createTimelineEntryHTML(entry) {
    const date = new Date(entry.created_at);
    return `
        <div class="timeline-entry">
            <div class="timeline-icon">${getIconForSystem(entry.source)}</div>
            <div class="timeline-content">
                <div class="timeline-amount">+${entry.xp_amount.toLocaleString()} points</div>
                <div class="timeline-action">${entry.action_type || entry.source}</div>
            </div>
            <div class="timeline-date">${date.toLocaleDateString()} ${date.toLocaleTimeString()}</div>
        </div>
    `;
}

/**
 * Load history
 */
async function loadHistory() {
    const list = document.getElementById('history-list');
    if (!list) return;
    
    list.innerHTML = '<div class="skeleton-loader" style="height: 200px;"></div>'.repeat(5);
    
    try {
        const response = await fetch(
            `${BASE_URL}/api/game/hunters/xp-history?user_id=${userId}&limit=100`
        );
        const data = await response.json();
        
        if (data.success && data.history) {
            list.innerHTML = data.history.map(entry => createHistoryEntryHTML(entry)).join('');
        }
    } catch (error) {
        console.error('Error loading history:', error);
        list.innerHTML = '<p style="text-align: center; color: white;">Failed to load history</p>';
    }
}

/**
 * Create history entry HTML
 */
function createHistoryEntryHTML(entry) {
    const date = new Date(entry.created_at);
    return `
        <div class="history-entry">
            <div class="timeline-icon">${getIconForSystem(entry.source)}</div>
            <div class="timeline-content">
                <div class="timeline-amount">+${entry.xp_amount.toLocaleString()} points</div>
                <div class="timeline-action">${entry.action_type || entry.source}</div>
            </div>
            <div class="timeline-date">${date.toLocaleDateString()} ${date.toLocaleTimeString()}</div>
        </div>
    `;
}

/**
 * Initialize modals
 */
function initializeModals() {
    // Counter modal
    const counterModal = document.getElementById('counter-modal');
    const counterModalClose = document.getElementById('counter-modal-close');
    
    if (counterModalClose) {
        counterModalClose.addEventListener('click', () => {
            counterModal.style.display = 'none';
        });
    }
    
    window.addEventListener('click', (e) => {
        if (e.target === counterModal) {
            counterModal.style.display = 'none';
        }
    });
    
    // Reward modal
    const rewardModal = document.getElementById('reward-modal');
    const rewardModalClose = document.getElementById('modal-close');
    
    if (rewardModalClose) {
        rewardModalClose.addEventListener('click', () => {
            rewardModal.style.display = 'none';
        });
    }
    
    window.addEventListener('click', (e) => {
        if (e.target === rewardModal) {
            rewardModal.style.display = 'none';
        }
    });
    
    // Rewards filter buttons
    document.querySelectorAll('.rewards-filter .filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.rewards-filter .filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadRewards(btn.dataset.filter);
        });
    });
    
    // Time period buttons
    document.querySelectorAll('.time-period-selector .period-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.time-period-selector .period-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadCountingTracking(btn.dataset.period);
        });
    });
    
    // Category filter buttons
    document.querySelectorAll('.category-filters .filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.category-filters .filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const category = btn.dataset.category;
            document.querySelectorAll('.point-counter-card').forEach(card => {
                if (category === 'all' || card.dataset.category === category) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });
}

/**
 * Helper functions
 */
function getCategoryForSystem(system) {
    if (system.includes('battle') || system.includes('combat')) return 'battle';
    if (system.includes('social') || system.includes('share') || system.includes('like')) return 'social';
    if (system.includes('generation') || system.includes('video') || system.includes('xp')) return 'core';
    if (system.includes('special') || system.includes('bonus')) return 'special';
    return 'other';
}

function getIconForSystem(system) {
    if (system.includes('xp') || system.includes('experience')) return '⭐';
    if (system.includes('battle') || system.includes('combat')) return '⚔️';
    if (system.includes('social')) return '👥';
    if (system.includes('generation')) return '🎬';
    if (system.includes('quest')) return '🎯';
    if (system.includes('achievement')) return '🏆';
    return '💎';
}

function formatSystemName(system) {
    return system
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}
