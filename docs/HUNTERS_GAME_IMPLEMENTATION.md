# Hunters Game - Implementation Guide

**Version:** 1.0.0  
**Date:** 2025-12-17  
**Status:** Implementation Complete

---

## 📋 Overview

The Hunters Game leveling system has been fully implemented with all features. This guide explains how to use and integrate the system.

---

## ✅ What's Been Created

### 1. Core System Files

- **`backend/services/hunters_leveling_system.py`** - Complete leveling system
- **`backend/routes/hunters_game.py`** - API endpoints for leveling
- **`docs/HUNTERS_GAME_DESIGN.md`** - Complete game design document

### 2. Features Implemented

✅ **Leveling System**
- XP calculation and level progression
- 5 tier system (Novice → Legendary)
- Level-based rewards

✅ **Stats System**
- 5 core stats (Creativity, Efficiency, Quality, Social, Knowledge)
- Stat allocation
- Stat effects on gameplay

✅ **Title System**
- 7 titles from Novice to Ultimate Hunter
- Title progression tracking

✅ **Rewards System**
- Level-based unlocks
- Theme unlocks
- Template unlocks
- Stat points per level

✅ **XP Sources**
- Video generation
- Achievements
- Milestones
- Daily activities
- Social actions

✅ **Leaderboards**
- Global rankings
- Category-based rankings
- Multiple sorting options

✅ **Prestige System**
- Reset to level 1 with bonuses
- Permanent XP bonuses
- Prestige titles

---

## 🔌 API Endpoints

### Player Profile

**GET** `/api/game/hunters/profile?user_id=<user_id>`

Get complete player profile including level, stats, achievements, and progress.

**Response:**
```json
{
  "success": true,
  "profile": {
    "user_id": "user123",
    "leveling": {
      "current_level": 5,
      "current_xp": 4500,
      "total_xp": 4500,
      "xp_to_next_level": 500,
      "level_progress": 90.0,
      "title": "Novice Hunter",
      "stats": {...},
      "next_level_info": {...}
    },
    "achievements": [...],
    "milestones": [...],
    "xp_system": {...},
    "stats_points": 150
  }
}
```

### Level Information

**GET** `/api/game/hunters/level?user_id=<user_id>`

Get player level information.

### Award XP

**POST** `/api/game/hunters/award-xp`

Award XP to a player (internal use).

**Request:**
```json
{
  "user_id": "user123",
  "xp_amount": 100,
  "source": "video_generation",
  "action_type": "create_video",
  "metadata": {
    "video_id": "vid123",
    "quality": "high"
  }
}
```

### Stats Management

**GET** `/api/game/hunters/stats?user_id=<user_id>`

Get player stats.

**POST** `/api/game/hunters/allocate-stats`

Allocate stat points.

**Request:**
```json
{
  "user_id": "user123",
  "stat_allocations": {
    "creativity": 5,
    "efficiency": 3,
    "quality": 2
  }
}
```

### Leaderboard

**GET** `/api/game/hunters/leaderboard?limit=100&category=level`

Get leaderboard.

**Categories:** `level`, `xp`, `achievements`

### XP History

**GET** `/api/game/hunters/xp-history?user_id=<user_id>&limit=50`

Get XP history for a player.

### Rewards

**GET** `/api/game/hunters/rewards?level=5`

Get rewards for a specific level or all levels.

### Titles

**GET** `/api/game/hunters/titles`

Get all available titles.

### Prestige

**POST** `/api/game/hunters/prestige`

Prestige (reset to level 1 with bonuses).

**Request:**
```json
{
  "user_id": "user123"
}
```

### Calculate Level

**POST** `/api/game/hunters/calculate-level`

Utility endpoint to calculate level from XP.

**Request:**
```json
{
  "total_xp": 50000
}
```

---

## 🔗 Integration Points

### 1. Video Generation Integration

When a video is created, award XP:

```python
from backend.services.hunters_leveling_system import hunters_leveling_system

# After video creation
result = hunters_leveling_system.award_xp(
    user_id=user_id,
    xp_amount=100,  # Base XP for video creation
    source='video_generation',
    action_type='create_video',
    metadata={
        'video_id': video_id,
        'quality': quality,
        'theme': theme
    }
)

# Check for level up
if result['level_up']:
    # Handle level up (show notification, grant rewards, etc.)
    level_up_info = result['level_up_info']
    print(f"Level up! {old_level} → {new_level}")
```

### 2. Achievement Integration

When achievements are earned, award bonus XP:

```python
# After checking achievements
new_achievements = game_achievement_system.check_and_award_achievements(user_id, stats)

for achievement in new_achievements:
    # Award bonus XP for achievement
    hunters_leveling_system.award_xp(
        user_id=user_id,
        xp_amount=achievement['points'],
        source='achievement',
        action_type='earn_achievement',
        metadata={'achievement_id': achievement['id']}
    )
```

### 3. Milestone Integration

When milestones are reached, award bonus XP:

```python
# After checking milestones
new_milestones = game_achievement_system.check_and_award_milestones(user_id, stats)

for milestone in new_milestones:
    # Award bonus XP for milestone
    hunters_leveling_system.award_xp(
        user_id=user_id,
        xp_amount=milestone['points'],
        source='milestone',
        action_type='reach_milestone',
        metadata={'milestone_id': milestone['id']}
    )
```

### 4. Daily Activities

Award XP for daily activities:

```python
# Daily login
hunters_leveling_system.award_xp(
    user_id=user_id,
    xp_amount=50,
    source='daily_activity',
    action_type='daily_login'
)

# Return user bonus
hunters_leveling_system.award_xp(
    user_id=user_id,
    xp_amount=25,
    source='daily_activity',
    action_type='return_user'
)
```

### 5. Social Actions

Award XP for social interactions:

```python
# Share video
hunters_leveling_system.award_xp(
    user_id=user_id,
    xp_amount=25,
    source='social',
    action_type='share_video',
    metadata={'video_id': video_id}
)

# Like video
hunters_leveling_system.award_xp(
    user_id=user_id,
    xp_amount=5,
    source='social',
    action_type='like_video'
)
```

---

## 📊 Database Integration

### Recommended Database Schema

```sql
-- Player levels table
CREATE TABLE IF NOT EXISTS player_levels (
    user_id VARCHAR(100) PRIMARY KEY,
    current_level INTEGER DEFAULT 1,
    current_xp INTEGER DEFAULT 0,
    total_xp INTEGER DEFAULT 0,
    xp_to_next_level INTEGER DEFAULT 1000,
    level_progress DECIMAL(5,2) DEFAULT 0.0,
    title VARCHAR(50) DEFAULT 'Novice Hunter',
    prestige_level INTEGER DEFAULT 0,
    stat_creativity INTEGER DEFAULT 0,
    stat_efficiency INTEGER DEFAULT 0,
    stat_quality INTEGER DEFAULT 0,
    stat_social INTEGER DEFAULT 0,
    stat_knowledge INTEGER DEFAULT 0,
    available_stat_points INTEGER DEFAULT 0,
    unlocked_themes TEXT,
    unlocked_templates TEXT,
    xp_bonus_percent INTEGER DEFAULT 0,
    xp_bonus_remaining INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- XP history table
CREATE TABLE IF NOT EXISTS xp_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100),
    xp_amount INTEGER,
    source VARCHAR(50),
    action_type VARCHAR(50),
    metadata TEXT,
    level_before INTEGER,
    level_after INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_xp_history_user ON xp_history(user_id);
CREATE INDEX IF NOT EXISTS idx_xp_history_created ON xp_history(created_at);
```

### Persistence

Currently, the system uses in-memory storage. To persist data:

1. **Add database models** in `src/db/models.py`
2. **Update service** to save/load from database
3. **Add migration** for new tables

---

## 🎨 Frontend Integration

### Display Level Information

```javascript
// Fetch player profile
async function loadPlayerProfile(userId) {
    const response = await fetch(
        `/vidgenerator/api/game/hunters/profile?user_id=${userId}`
    );
    const data = await response.json();
    
    if (data.success) {
        const profile = data.profile.leveling;
        
        // Display level
        document.getElementById('player-level').textContent = profile.current_level;
        document.getElementById('player-title').textContent = profile.title;
        
        // Display XP progress
        const progressBar = document.getElementById('xp-progress-bar');
        progressBar.style.width = `${profile.level_progress}%`;
        progressBar.textContent = `${profile.current_xp} / ${profile.xp_to_next_level} XP`;
        
        // Display stats
        displayStats(profile.stats);
    }
}

// Display stats
function displayStats(stats) {
    document.getElementById('stat-creativity').textContent = stats.creativity;
    document.getElementById('stat-efficiency').textContent = stats.efficiency;
    document.getElementById('stat-quality').textContent = stats.quality;
    document.getElementById('stat-social').textContent = stats.social;
    document.getElementById('stat-knowledge').textContent = stats.knowledge;
}
```

### Level Up Notification

```javascript
// Check for level up after XP award
async function awardXP(userId, xpAmount, source, actionType, metadata) {
    const response = await fetch('/vidgenerator/api/game/hunters/award-xp', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            user_id: userId,
            xp_amount: xpAmount,
            source: source,
            action_type: actionType,
            metadata: metadata
        })
    });
    
    const data = await response.json();
    
    if (data.success && data.result.level_up) {
        // Show level up notification
        showLevelUpNotification(data.result.level_up_info);
    }
}

function showLevelUpNotification(levelUpInfo) {
    // Create notification
    const notification = document.createElement('div');
    notification.className = 'level-up-notification';
    notification.innerHTML = `
        <h2>🎉 Level Up!</h2>
        <p>Level ${levelUpInfo.old_level} → ${levelUpInfo.new_level}</p>
        <p>Title: ${levelUpInfo.title_unlocked || 'No new title'}</p>
        <p>Stat Points Gained: ${levelUpInfo.stat_points_gained}</p>
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 5 seconds
    setTimeout(() => notification.remove(), 5000);
}
```

---

## 🧪 Testing

### Test Level Calculation

```python
from backend.services.hunters_leveling_system import hunters_leveling_system

# Test level calculation
assert hunters_leveling_system.calculate_level(0) == 1
assert hunters_leveling_system.calculate_level(1000) == 2
assert hunters_leveling_system.calculate_level(55000) == 10
assert hunters_leveling_system.calculate_level(500000) == 25
```

### Test XP Award

```python
# Test XP award
result = hunters_leveling_system.award_xp(
    user_id='test_user',
    xp_amount=1000,
    source='test',
    action_type='test_action'
)

assert result['current_level'] >= 1
assert result['total_xp'] == 1000
```

---

## 📝 Next Steps

1. **Database Persistence**
   - Add database models
   - Implement save/load functions
   - Add migrations

2. **Frontend UI**
   - Create level display component
   - Create stat allocation interface
   - Create leaderboard page

3. **Integration**
   - Integrate with video generation
   - Integrate with achievements
   - Add daily challenges

4. **Advanced Features**
   - Prestige system UI
   - Seasonal events
   - Guild system

---

## 🎯 Usage Examples

### Complete Integration Example

```python
# In video generation route
from backend.services.hunters_leveling_system import hunters_leveling_system
from backend.services.game_achievements import game_achievement_system

# After video creation
user_id = 'user123'
video_quality = 'high'

# Award base XP
xp_result = hunters_leveling_system.award_xp(
    user_id=user_id,
    xp_amount=100,
    source='video_generation',
    action_type='create_video',
    metadata={'quality': video_quality}
)

# Quality bonus
if video_quality == 'high':
    hunters_leveling_system.award_xp(
        user_id=user_id,
        xp_amount=50,
        source='video_generation',
        action_type='high_quality_bonus'
    )

# Check achievements (which also award XP)
stats = calculate_user_stats(user_id)
achievement_result = game_achievement_system.update_user_stats(user_id, stats)

# Award achievement XP
for achievement in achievement_result.get('new_achievements', []):
    hunters_leveling_system.award_xp(
        user_id=user_id,
        xp_amount=achievement['points'],
        source='achievement',
        action_type='earn_achievement'
    )

# Return level up info if applicable
if xp_result['level_up']:
    return {
        'success': True,
        'video_created': True,
        'level_up': xp_result['level_up_info']
    }
```

---

**Last Updated:** 2025-12-17  
**Status:** Ready for Integration

