# Hunters Game - Leveling System Design

**Version:** 1.0.0  
**Date:** 2025-12-17  
**Status:** Design Complete

---

## 🎮 Game Overview

The Hunters Game is a comprehensive leveling-based RPG system integrated into the MasterNoder.dk video generation platform. Players progress through levels by creating videos, completing achievements, and reaching milestones.

---

## 🎯 Core Mechanics

### Leveling System

**XP Requirements Formula:**
```
Level 1-10:   Base XP = 1000 * level
Level 11-25:  Base XP = 2000 * level
Level 26-50:  Base XP = 3000 * level
Level 51-100: Base XP = 5000 * level
Level 100+:   Base XP = 10000 * level
```

**Total XP to reach level:**
- Level 1: 0 XP (starting level)
- Level 2: 1,000 XP
- Level 5: 10,000 XP
- Level 10: 55,000 XP
- Level 25: 500,000 XP
- Level 50: 2,000,000 XP
- Level 100: 10,000,000 XP

### XP Sources

1. **Video Generation**
   - Create video: 100 XP
   - High quality video: +50 XP bonus
   - Perfect quality video: +100 XP bonus
   - Batch generation: +25 XP per video

2. **Achievements**
   - First video: 100 XP
   - Video master (10 videos): 500 XP
   - Perfectionist: 300 XP
   - Category achievements: 150-600 XP
   - Special achievements: 700-800 XP

3. **Milestones**
   - Video count milestones: 200-5000 XP
   - Quality milestones: 600-1200 XP
   - Category milestones: 800-2000 XP

4. **Daily Activities**
   - Daily login: 50 XP
   - Return user bonus: 25 XP
   - Streak bonus: +10 XP per day (max 100 XP)

5. **Social Actions**
   - Share video: 25 XP
   - Like video: 5 XP
   - Comment: 15 XP
   - Watch video: 10 XP

---

## 🏆 Level Progression

### Level Tiers

**Novice Tier (Levels 1-10)**
- Title: "Novice Hunter"
- Unlock: Basic features
- Rewards: Starter themes, basic templates

**Apprentice Tier (Levels 11-25)**
- Title: "Apprentice Hunter"
- Unlock: Advanced features
- Rewards: Premium themes, advanced templates

**Expert Tier (Levels 26-50)**
- Title: "Expert Hunter"
- Unlock: Professional features
- Rewards: Exclusive themes, professional templates

**Master Tier (Levels 51-100)**
- Title: "Master Hunter"
- Unlock: All features
- Rewards: All themes, all templates, special badges

**Legend Tier (Level 100+)**
- Title: "Legendary Hunter"
- Unlock: Legendary status
- Rewards: Exclusive legendary themes, special recognition

### Level Rewards

Each level up grants:
- **XP Bonus:** 10% XP boost for next 10 actions
- **Unlock Points:** Points to unlock new features
- **Title Progress:** Progress toward next title
- **Stat Points:** Points to allocate to stats
- **Themes:** Unlock new video themes
- **Templates:** Unlock new templates

---

## 📊 Stats System

### Core Stats

1. **Creativity** (0-100)
   - Increases: Complex prompts, unique themes
   - Effect: Better video quality, more creative options

2. **Efficiency** (0-100)
   - Increases: Fast generations, batch operations
   - Effect: Faster generation times, lower costs

3. **Quality** (0-100)
   - Increases: High-quality videos, perfect scores
   - Effect: Better output quality, premium features

4. **Social** (0-100)
   - Increases: Shares, likes, comments
   - Effect: More visibility, social features

5. **Knowledge** (0-100)
   - Increases: Achievements, milestones, learning
   - Effect: Unlock advanced features, better recommendations

### Stat Allocation

- **Stat Points per Level:** 5 points
- **Max Stat Level:** 100
- **Respec Cost:** 1000 XP (can reset stats)

---

## 🎖️ Titles & Prestige

### Title System

Titles are earned at specific level milestones:

- **Level 1:** Novice Hunter
- **Level 10:** Apprentice Hunter
- **Level 25:** Expert Hunter
- **Level 50:** Master Hunter
- **Level 100:** Legendary Hunter
- **Level 150:** Grandmaster Hunter
- **Level 200:** Ultimate Hunter

### Prestige System

After reaching Level 100, players can:
- **Prestige:** Reset to Level 1 with permanent bonuses
- **Prestige Bonuses:** +10% XP gain per prestige
- **Prestige Titles:** Special prestige titles
- **Prestige Points:** Unlock exclusive content

---

## 🏅 Achievements Integration

### Achievement Categories

1. **Generation Achievements**
   - First video, video master, perfectionist
   - Speed demon, quality seeker

2. **Category Achievements**
   - Entertainment starter/master
   - Adult starter/master
   - Rights starter/master

3. **Special Achievements**
   - Streak master (30 day streak)
   - Social butterfly (100 shares)
   - Quality king (50 perfect videos)

### Milestone Integration

Milestones provide significant XP bonuses:
- Video count milestones (5, 10, 25, 50, 100)
- Quality milestones (80%, 90% average)
- Category milestones (10, 25 per category)

---

## 🎁 Rewards & Unlocks

### Level-Based Unlocks

**Level 5:**
- Unlock: Batch generation
- Theme: Nature theme
- Template: Basic documentary

**Level 10:**
- Unlock: Advanced settings
- Theme: Sci-fi theme
- Template: Advanced documentary

**Level 25:**
- Unlock: Custom themes
- Theme: Cyberpunk theme
- Template: Professional documentary

**Level 50:**
- Unlock: All features
- Theme: All themes
- Template: All templates

### Achievement Unlocks

- Complete achievement sets unlock special rewards
- Category mastery unlocks exclusive themes
- Perfect scores unlock premium templates

---

## 📈 Progression Tracking

### Player Profile

Each player has:
- **Current Level:** Current level (1-100+)
- **Current XP:** XP in current level
- **Total XP:** Lifetime XP earned
- **XP to Next Level:** XP needed for next level
- **Level Progress:** Percentage to next level
- **Stats:** Allocated stat points
- **Title:** Current title
- **Prestige Level:** Prestige count (if applicable)

### Leaderboards

1. **Global Leaderboard**
   - Top players by level
   - Top players by total XP
   - Top players by achievements

2. **Category Leaderboards**
   - Top in each category
   - Top by quality
   - Top by speed

3. **Weekly/Monthly Leaderboards**
   - Reset weekly/monthly
   - Special rewards for top players

---

## 🎮 Game Features

### Daily Challenges

- **Daily Quest:** Complete specific tasks
- **Rewards:** Bonus XP, stat points, unlocks
- **Streak Bonus:** Consecutive day bonuses

### Seasonal Events

- **Special Events:** Limited-time challenges
- **Event Rewards:** Exclusive themes, titles, badges
- **Event Leaderboards:** Separate event rankings

### Guild/Clan System (Future)

- **Form Guilds:** Team up with other players
- **Guild Challenges:** Complete challenges together
- **Guild Rewards:** Shared rewards and bonuses

---

## 🔄 Integration Points

### With Existing Systems

1. **XP System Integration**
   - All XP actions contribute to leveling
   - Level affects XP multipliers

2. **Achievement System Integration**
   - Achievements grant bonus XP
   - Level unlocks new achievements

3. **Milestone System Integration**
   - Milestones provide large XP bonuses
   - Level affects milestone rewards

4. **Video Generation Integration**
   - Video creation grants XP
   - Level unlocks generation features

---

## 📱 UI/UX Design

### Level Display

- **Level Badge:** Prominent level display
- **XP Bar:** Visual progress bar
- **Next Level Preview:** Show next level rewards
- **Stat Display:** Visual stat bars

### Progression Screen

- **Level History:** Show level progression
- **Achievement Gallery:** Display all achievements
- **Milestone Tracker:** Track milestone progress
- **Reward Preview:** Preview upcoming unlocks

### Leaderboard Screen

- **Global Rankings:** Top players
- **Category Rankings:** Category-specific
- **Personal Ranking:** Player's position
- **Filter Options:** Filter by category, time period

---

## 🎯 Game Balance

### XP Balance

- **Easy to Start:** Low XP requirements early levels
- **Steady Progress:** Consistent XP gains
- **Long-term Goals:** High XP requirements for high levels
- **Multiple Paths:** Various ways to earn XP

### Reward Balance

- **Frequent Rewards:** Regular unlocks keep engagement
- **Meaningful Rewards:** Rewards provide real value
- **Exclusive Content:** High-level rewards are special
- **Achievable Goals:** All players can progress

---

## 🚀 Implementation Plan

### Phase 1: Core Leveling (Week 1)
- Level calculation system
- XP tracking and storage
- Basic level display

### Phase 2: Stats & Titles (Week 2)
- Stat allocation system
- Title system
- Stat effects

### Phase 3: Rewards & Unlocks (Week 3)
- Level-based unlocks
- Reward system
- Unlock tracking

### Phase 4: Leaderboards (Week 4)
- Global leaderboards
- Category leaderboards
- Ranking system

### Phase 5: Advanced Features (Week 5+)
- Daily challenges
- Seasonal events
- Prestige system

---

## 📊 Database Schema

### Player Levels Table

```sql
CREATE TABLE player_levels (
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
    unlocked_themes TEXT,
    unlocked_templates TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### XP History Table

```sql
CREATE TABLE xp_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100),
    xp_amount INTEGER,
    action_type VARCHAR(50),
    source VARCHAR(50),
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Level Rewards Table

```sql
CREATE TABLE level_rewards (
    level INTEGER PRIMARY KEY,
    xp_bonus_percent INTEGER DEFAULT 0,
    unlock_points INTEGER DEFAULT 0,
    stat_points INTEGER DEFAULT 5,
    theme_unlocks TEXT,
    template_unlocks TEXT,
    title_unlock VARCHAR(50)
);
```

---

## 🎨 Visual Design

### Level Badge

- **Circular Badge:** Level number in center
- **Color Coding:** Different colors per tier
- **Animation:** Level up animations
- **Glow Effect:** Higher levels have glow

### XP Bar

- **Progress Bar:** Visual XP progress
- **Next Level Indicator:** Show next level
- **XP Amount:** Current/total XP display
- **Percentage:** Progress percentage

### Stat Display

- **Stat Bars:** Visual stat representation
- **Stat Icons:** Icons for each stat
- **Allocation Interface:** Easy stat allocation
- **Effect Display:** Show stat effects

---

## 🔧 Technical Implementation

### Level Calculation

```python
def calculate_level(total_xp: int) -> int:
    """Calculate level from total XP"""
    if total_xp < 55000:  # Level 1-10
        return (total_xp // 1000) + 1
    elif total_xp < 500000:  # Level 11-25
        return 10 + ((total_xp - 55000) // 2000) + 1
    elif total_xp < 2000000:  # Level 26-50
        return 25 + ((total_xp - 500000) // 3000) + 1
    elif total_xp < 10000000:  # Level 51-100
        return 50 + ((total_xp - 2000000) // 5000) + 1
    else:  # Level 100+
        return 100 + ((total_xp - 10000000) // 10000) + 1

def xp_for_level(level: int) -> int:
    """Calculate total XP needed for a level"""
    if level <= 10:
        return (level - 1) * 1000
    elif level <= 25:
        return 55000 + (level - 10) * 2000
    elif level <= 50:
        return 500000 + (level - 25) * 3000
    elif level <= 100:
        return 2000000 + (level - 50) * 5000
    else:
        return 10000000 + (level - 100) * 10000
```

---

## 📝 API Endpoints

### Level System

- `GET /api/game/level` - Get player level info
- `POST /api/game/level/allocate-stats` - Allocate stat points
- `GET /api/game/level/rewards` - Get level rewards
- `GET /api/game/level/leaderboard` - Get leaderboard

### XP System

- `POST /api/game/xp/award` - Award XP (internal)
- `GET /api/game/xp/history` - Get XP history
- `GET /api/game/xp/next-level` - Get next level info

### Titles & Prestige

- `GET /api/game/titles` - Get available titles
- `POST /api/game/prestige` - Prestige (reset with bonuses)

---

## 🎯 Success Metrics

### Engagement Metrics

- **Daily Active Users:** Players active daily
- **Level Distribution:** Players per level range
- **Average Level:** Average player level
- **Retention Rate:** Players returning

### Progression Metrics

- **Average Time to Level:** Time to gain levels
- **XP Sources:** Where XP comes from
- **Stat Allocation:** How players allocate stats
- **Achievement Completion:** Achievement rates

---

**Last Updated:** 2025-12-17  
**Status:** Ready for Implementation

