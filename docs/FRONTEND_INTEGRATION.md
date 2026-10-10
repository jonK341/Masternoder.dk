# Frontend Integration Guide - Hunters Game

**Date:** 2025-12-17  
**Status:** Ready for Implementation

---

## 🎨 UI Components

### 1. Level Display Widget

Display player level, XP progress, and title.

```html
<!-- Level Badge Component -->
<div class="level-badge" id="level-badge">
    <div class="level-number" id="level-number">1</div>
    <div class="level-title" id="level-title">Novice Hunter</div>
    <div class="xp-bar-container">
        <div class="xp-bar" id="xp-bar" style="width: 0%"></div>
        <div class="xp-text" id="xp-text">0 / 1000 XP</div>
    </div>
</div>
```

```css
.level-badge {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 15px;
    padding: 20px;
    color: white;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}

.level-number {
    font-size: 3em;
    font-weight: bold;
    margin-bottom: 10px;
}

.level-title {
    font-size: 1.2em;
    opacity: 0.9;
    margin-bottom: 15px;
}

.xp-bar-container {
    background: rgba(255,255,255,0.2);
    border-radius: 10px;
    height: 25px;
    position: relative;
    overflow: hidden;
}

.xp-bar {
    background: linear-gradient(90deg, #00ff88 0%, #00cc6a 100%);
    height: 100%;
    transition: width 0.5s ease;
    border-radius: 10px;
}

.xp-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 0.9em;
    font-weight: bold;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}
```

```javascript
// Load and display level info
async function loadLevelDisplay(userId) {
    try {
        const response = await fetch(
            `/vidgenerator/api/game/hunters/level?user_id=${userId}`
        );
        const data = await response.json();
        
        if (data.success) {
            const levelInfo = data.level_info;
            
            // Update level number
            document.getElementById('level-number').textContent = levelInfo.current_level;
            
            // Update title
            document.getElementById('level-title').textContent = levelInfo.title;
            
            // Update XP bar
            const progress = levelInfo.level_progress;
            document.getElementById('xp-bar').style.width = `${progress}%`;
            
            // Update XP text
            document.getElementById('xp-text').textContent = 
                `${levelInfo.current_xp.toLocaleString()} / ${levelInfo.xp_to_next_level.toLocaleString()} XP`;
        }
    } catch (error) {
        console.error('Error loading level display:', error);
    }
}

// Auto-refresh every 30 seconds
setInterval(() => loadLevelDisplay('default_user'), 30000);
```

---

### 2. Level Up Notification

Show animated notification when player levels up.

```html
<!-- Level Up Notification -->
<div class="level-up-notification" id="level-up-notification" style="display: none;">
    <div class="level-up-content">
        <div class="level-up-icon">🎉</div>
        <h2>Level Up!</h2>
        <p class="level-change" id="level-change">Level 5 → 6</p>
        <div class="level-up-rewards" id="level-up-rewards">
            <!-- Rewards will be inserted here -->
        </div>
        <button onclick="closeLevelUpNotification()">Awesome!</button>
    </div>
</div>
```

```css
.level-up-notification {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
    animation: fadeIn 0.3s ease;
}

.level-up-content {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 20px;
    padding: 40px;
    text-align: center;
    color: white;
    max-width: 500px;
    animation: slideUp 0.5s ease;
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}

.level-up-icon {
    font-size: 5em;
    animation: bounce 1s infinite;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideUp {
    from {
        transform: translateY(50px);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}

@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-20px); }
}
```

```javascript
// Show level up notification
function showLevelUpNotification(levelUpInfo) {
    const notification = document.getElementById('level-up-notification');
    const levelChange = document.getElementById('level-change');
    const rewards = document.getElementById('level-up-rewards');
    
    // Update level change
    levelChange.textContent = 
        `Level ${levelUpInfo.old_level} → ${levelUpInfo.new_level}`;
    
    // Show rewards
    let rewardsHTML = '';
    if (levelUpInfo.stat_points_gained > 0) {
        rewardsHTML += `<p>✨ ${levelUpInfo.stat_points_gained} Stat Points Gained!</p>`;
    }
    if (levelUpInfo.title_unlocked) {
        rewardsHTML += `<p>🏆 New Title: ${levelUpInfo.title_unlocked}</p>`;
    }
    if (levelUpInfo.themes_unlocked.length > 0) {
        rewardsHTML += `<p>🎨 Themes Unlocked: ${levelUpInfo.themes_unlocked.join(', ')}</p>`;
    }
    
    rewards.innerHTML = rewardsHTML || '<p>Keep up the great work!</p>';
    
    // Show notification
    notification.style.display = 'flex';
    
    // Auto-close after 5 seconds
    setTimeout(() => {
        closeLevelUpNotification();
    }, 5000);
}

function closeLevelUpNotification() {
    document.getElementById('level-up-notification').style.display = 'none';
}

// Listen for level ups (poll or use WebSocket)
async function checkForLevelUp(userId) {
    // This would be called after XP is awarded
    // Check if level_up flag is true in response
}
```

---

### 3. Stats Display & Allocation

Show stats and allow allocation of stat points.

```html
<!-- Stats Display -->
<div class="stats-container" id="stats-container">
    <h3>Your Stats</h3>
    <div class="available-points" id="available-points">
        Available Points: <span id="points-count">0</span>
    </div>
    
    <div class="stats-list" id="stats-list">
        <!-- Stats will be inserted here -->
    </div>
    
    <button id="allocate-stats-btn" onclick="openStatAllocation()" disabled>
        Allocate Points
    </button>
</div>

<!-- Stat Allocation Modal -->
<div class="stat-allocation-modal" id="stat-allocation-modal" style="display: none;">
    <div class="modal-content">
        <h2>Allocate Stat Points</h2>
        <div id="stat-allocation-form">
            <!-- Form will be inserted here -->
        </div>
        <div class="modal-actions">
            <button onclick="saveStatAllocation()">Save</button>
            <button onclick="closeStatAllocation()">Cancel</button>
        </div>
    </div>
</div>
```

```javascript
// Load and display stats
async function loadStats(userId) {
    try {
        const response = await fetch(
            `/vidgenerator/api/game/hunters/stats?user_id=${userId}`
        );
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            const availablePoints = data.available_stat_points;
            
            // Update available points
            document.getElementById('points-count').textContent = availablePoints;
            document.getElementById('allocate-stats-btn').disabled = availablePoints === 0;
            
            // Display stats
            const statsList = document.getElementById('stats-list');
            statsList.innerHTML = `
                <div class="stat-item">
                    <span class="stat-name">Creativity</span>
                    <div class="stat-bar">
                        <div class="stat-fill" style="width: ${stats.creativity}%"></div>
                    </div>
                    <span class="stat-value">${stats.creativity}/100</span>
                </div>
                <div class="stat-item">
                    <span class="stat-name">Efficiency</span>
                    <div class="stat-bar">
                        <div class="stat-fill" style="width: ${stats.efficiency}%"></div>
                    </div>
                    <span class="stat-value">${stats.efficiency}/100</span>
                </div>
                <div class="stat-item">
                    <span class="stat-name">Quality</span>
                    <div class="stat-bar">
                        <div class="stat-fill" style="width: ${stats.quality}%"></div>
                    </div>
                    <span class="stat-value">${stats.quality}/100</span>
                </div>
                <div class="stat-item">
                    <span class="stat-name">Social</span>
                    <div class="stat-bar">
                        <div class="stat-fill" style="width: ${stats.social}%"></div>
                    </div>
                    <span class="stat-value">${stats.social}/100</span>
                </div>
                <div class="stat-item">
                    <span class="stat-name">Knowledge</span>
                    <div class="stat-bar">
                        <div class="stat-fill" style="width: ${stats.knowledge}%"></div>
                    </div>
                    <span class="stat-value">${stats.knowledge}/100</span>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Open stat allocation modal
function openStatAllocation() {
    const modal = document.getElementById('stat-allocation-modal');
    const form = document.getElementById('stat-allocation-form');
    
    // Get available points
    const availablePoints = parseInt(document.getElementById('points-count').textContent);
    
    // Create allocation form
    form.innerHTML = `
        <p>You have <strong>${availablePoints}</strong> points to allocate.</p>
        <div class="stat-allocation-item">
            <label>Creativity:</label>
            <input type="number" id="alloc-creativity" min="0" max="${availablePoints}" value="0">
        </div>
        <div class="stat-allocation-item">
            <label>Efficiency:</label>
            <input type="number" id="alloc-efficiency" min="0" max="${availablePoints}" value="0">
        </div>
        <div class="stat-allocation-item">
            <label>Quality:</label>
            <input type="number" id="alloc-quality" min="0" max="${availablePoints}" value="0">
        </div>
        <div class="stat-allocation-item">
            <label>Social:</label>
            <input type="number" id="alloc-social" min="0" max="${availablePoints}" value="0">
        </div>
        <div class="stat-allocation-item">
            <label>Knowledge:</label>
            <input type="number" id="alloc-knowledge" min="0" max="${availablePoints}" value="0">
        </div>
        <div id="allocation-total">Total: 0 / ${availablePoints}</div>
    `;
    
    // Add change listeners
    ['creativity', 'efficiency', 'quality', 'social', 'knowledge'].forEach(stat => {
        document.getElementById(`alloc-${stat}`).addEventListener('input', updateAllocationTotal);
    });
    
    modal.style.display = 'block';
}

function updateAllocationTotal() {
    const stats = ['creativity', 'efficiency', 'quality', 'social', 'knowledge'];
    const total = stats.reduce((sum, stat) => {
        const input = document.getElementById(`alloc-${stat}`);
        return sum + (parseInt(input.value) || 0);
    }, 0);
    
    const availablePoints = parseInt(document.getElementById('points-count').textContent);
    const totalEl = document.getElementById('allocation-total');
    totalEl.textContent = `Total: ${total} / ${availablePoints}`;
    totalEl.style.color = total > availablePoints ? 'red' : 'green';
}

// Save stat allocation
async function saveStatAllocation() {
    const userId = 'default_user'; // Get from session
    
    const statAllocations = {
        creativity: parseInt(document.getElementById('alloc-creativity').value) || 0,
        efficiency: parseInt(document.getElementById('alloc-efficiency').value) || 0,
        quality: parseInt(document.getElementById('alloc-quality').value) || 0,
        social: parseInt(document.getElementById('alloc-social').value) || 0,
        knowledge: parseInt(document.getElementById('alloc-knowledge').value) || 0
    };
    
    // Validate total
    const total = Object.values(statAllocations).reduce((a, b) => a + b, 0);
    const availablePoints = parseInt(document.getElementById('points-count').textContent);
    
    if (total > availablePoints) {
        alert(`You can only allocate ${availablePoints} points!`);
        return;
    }
    
    if (total === 0) {
        alert('Please allocate at least 1 point!');
        return;
    }
    
    try {
        const response = await fetch('/vidgenerator/api/game/hunters/allocate-stats', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: userId,
                stat_allocations: statAllocations
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Stats allocated successfully!');
            closeStatAllocation();
            loadStats(userId); // Reload stats
        } else {
            alert('Error: ' + (data.error || 'Failed to allocate stats'));
        }
    } catch (error) {
        console.error('Error allocating stats:', error);
        alert('Error allocating stats');
    }
}

function closeStatAllocation() {
    document.getElementById('stat-allocation-modal').style.display = 'none';
}
```

---

### 4. Leaderboard Display

Display global leaderboard.

```html
<!-- Leaderboard -->
<div class="leaderboard-container" id="leaderboard-container">
    <h2>🏆 Leaderboard</h2>
    <div class="leaderboard-filters">
        <button onclick="loadLeaderboard('level')" class="active">By Level</button>
        <button onclick="loadLeaderboard('xp')">By XP</button>
        <button onclick="loadLeaderboard('achievements')">By Achievements</button>
    </div>
    <div class="leaderboard-list" id="leaderboard-list">
        <!-- Leaderboard entries will be inserted here -->
    </div>
</div>
```

```javascript
// Load leaderboard
async function loadLeaderboard(category = 'level') {
    try {
        const response = await fetch(
            `/vidgenerator/api/game/hunters/leaderboard?limit=100&category=${category}`
        );
        const data = await response.json();
        
        if (data.success) {
            const leaderboard = data.leaderboard;
            const list = document.getElementById('leaderboard-list');
            
            list.innerHTML = leaderboard.map(entry => `
                <div class="leaderboard-entry">
                    <span class="rank">#${entry.rank}</span>
                    <span class="title">${entry.title}</span>
                    <span class="level">Level ${entry.level}</span>
                    <span class="xp">${entry.total_xp.toLocaleString()} XP</span>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading leaderboard:', error);
    }
}
```

---

### 5. XP Award Integration

Integrate XP awards into existing actions.

```javascript
// Award XP after video creation
async function onVideoCreated(videoData) {
    // Video creation already awards XP automatically
    // But you can show a notification
    
    showXPN notification(50, 'Video Queued');
}

// Award XP for social actions
async function shareVideo(videoId) {
    try {
        const response = await fetch('/vidgenerator/api/social/share', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: getUserId(),
                video_id: videoId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showXPN notification(data.xp_awarded, 'Video Shared');
            
            // Check for level up
            if (data.level_up) {
                showLevelUpNotification(data.level_info);
            }
        }
    } catch (error) {
        console.error('Error sharing video:', error);
    }
}

// Show XP notification
function showXPN notification(xpAmount, action) {
    const notification = document.createElement('div');
    notification.className = 'xp-notification';
    notification.innerHTML = `
        <div class="xp-icon">✨</div>
        <div class="xp-text">+${xpAmount} XP</div>
        <div class="xp-action">${action}</div>
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Daily login
async function handleDailyLogin() {
    try {
        const response = await fetch('/vidgenerator/api/daily/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_id: getUserId()
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showXPN notification(data.xp_awarded, `Daily Login (Streak: ${data.streak})`);
            
            if (data.level_up) {
                showLevelUpNotification(data.level_info);
            }
        }
    } catch (error) {
        console.error('Error processing daily login:', error);
    }
}

// Call on page load
window.addEventListener('load', () => {
    handleDailyLogin();
    loadLevelDisplay(getUserId());
    loadStats(getUserId());
});
```

---

## 🎯 Complete Integration Example

### Full Page Integration

```html
<!DOCTYPE html>
<html>
<head>
    <title>Hunters Game - MasterNoder.dk</title>
    <link rel="stylesheet" href="/static/css/hunters-game.css">
</head>
<body>
    <!-- Header with Level Badge -->
    <header>
        <div class="level-badge" id="level-badge">
            <!-- Level display component -->
        </div>
    </header>
    
    <!-- Main Content -->
    <main>
        <!-- Stats Section -->
        <section class="stats-section">
            <div class="stats-container" id="stats-container">
                <!-- Stats display -->
            </div>
        </section>
        
        <!-- Leaderboard Section -->
        <section class="leaderboard-section">
            <div class="leaderboard-container" id="leaderboard-container">
                <!-- Leaderboard -->
            </div>
        </section>
    </main>
    
    <!-- Level Up Notification -->
    <div class="level-up-notification" id="level-up-notification">
        <!-- Level up popup -->
    </div>
    
    <script src="/static/js/hunters-game.js"></script>
</body>
</html>
```

---

## 📱 Mobile Responsive

All components are designed to be mobile-responsive:

```css
@media (max-width: 768px) {
    .level-badge {
        padding: 15px;
    }
    
    .level-number {
        font-size: 2em;
    }
    
    .stats-container {
        padding: 15px;
    }
}
```

---

## 🔄 Real-time Updates

### Option 1: Polling

```javascript
// Poll for updates every 30 seconds
setInterval(async () => {
    await loadLevelDisplay(getUserId());
    await loadStats(getUserId());
}, 30000);
```

### Option 2: Event-Based

```javascript
// Listen for XP awards
document.addEventListener('xpAwarded', (event) => {
    const { xpAmount, source } = event.detail;
    showXPN notification(xpAmount, source);
    
    // Reload level display
    loadLevelDisplay(getUserId());
});
```

---

## ✅ Integration Checklist

- [ ] Add level display to header/navbar
- [ ] Add stats display to profile page
- [ ] Add leaderboard page
- [ ] Integrate XP notifications
- [ ] Add level up animations
- [ ] Add daily login check
- [ ] Add social action XP awards
- [ ] Test all integrations

---

**Last Updated:** 2025-12-17

