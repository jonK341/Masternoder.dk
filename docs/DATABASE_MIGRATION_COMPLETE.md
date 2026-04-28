# Database Migration Complete - Hunters Game & Rewards

**Date:** 2025-01-20  
**Status:** ✅ **COMPLETE**

---

## 🎯 What Was Created

### 1. Complete Migration Script ✅

**File:** `scripts/migrate_hunters_game_complete.py`

**Features:**
- ✅ Creates all hunters game tables (player_levels, xp_history, daily_activities)
- ✅ Creates rewards system tables (rewards, user_rewards)
- ✅ Verifies table creation
- ✅ Shows table information and row counts
- ✅ Handles errors gracefully
- ✅ Uses both SQLAlchemy models and raw SQL

**Tables Created:**
1. `player_levels` - Player leveling data
2. `xp_history` - XP earning history
3. `daily_activities` - Daily activity tracking
4. `rewards` - Reward definitions
5. `user_rewards` - User reward claims

### 2. Rewards Population Script ✅

**File:** `scripts/populate_initial_rewards.py`

**Features:**
- ✅ Populates initial rewards data
- ✅ Includes level-based rewards
- ✅ Includes points-based rewards (XP, Generation, Battle, Social)
- ✅ Checks for existing rewards before inserting
- ✅ Shows summary statistics

**Rewards Created:**
- 3 Level-based rewards (Level 5, 10, 25)
- 3 XP-based rewards (1K, 5K, 10K XP)
- 2 Generation points rewards (100, 500)
- 2 Battle points rewards (50, 200)
- 2 Social points rewards (100, 500)

---

## 🚀 How to Use

### Step 1: Run Migration

```bash
cd /path/to/project
python scripts/migrate_hunters_game_complete.py
```

**Expected Output:**
```
======================================================================
Complete Hunters Game Database Migration
======================================================================

Step 1: Initializing database...
Step 2: Creating tables from models...
Step 3: Creating rewards tables...
Step 4: Verifying tables...
[OK] All tables created successfully!

Created tables:
  ✅ player_levels
  ✅ xp_history
  ✅ daily_activities
  ✅ rewards
  ✅ user_rewards

Table Information:
  player_levels: 0 rows
  xp_history: 0 rows
  daily_activities: 0 rows
  rewards: 0 rows
  user_rewards: 0 rows
```

### Step 2: Populate Initial Rewards

```bash
python scripts/populate_initial_rewards.py
```

**Expected Output:**
```
======================================================================
Populating Initial Rewards
======================================================================

Inserting 12 rewards...
  ✅ Inserted: Level 5 Achievement
  ✅ Inserted: Level 10 Milestone
  ✅ Inserted: Level 25 Expert
  ✅ Inserted: 1,000 XP Reward
  ✅ Inserted: 5,000 XP Milestone
  ✅ Inserted: 10,000 XP Achievement
  ✅ Inserted: 100 Generation Points
  ✅ Inserted: 500 Generation Points
  ✅ Inserted: 50 Battle Points
  ✅ Inserted: 200 Battle Points
  ✅ Inserted: 100 Social Points
  ✅ Inserted: 500 Social Points

[OK] Inserted 12 new rewards

Total rewards in database: 12

Rewards by type:
  level: 3
  points: 9
```

---

## 📊 Database Schema

### Rewards Table

```sql
CREATE TABLE rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reward_type VARCHAR(50) NOT NULL,        -- 'level' or 'points'
    reward_name VARCHAR(100) NOT NULL,
    reward_description TEXT,
    level_required INTEGER,                 -- For level-based rewards
    points_required INTEGER,                 -- For points-based rewards
    point_type VARCHAR(50),                   -- 'xp', 'generation', 'battle', 'social', etc.
    reward_data TEXT,                        -- JSON: themes, templates, stat_points, etc.
    icon VARCHAR(10) DEFAULT '🎁',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rewards_type ON rewards(reward_type);
CREATE INDEX idx_rewards_level ON rewards(level_required);
CREATE INDEX idx_rewards_points ON rewards(points_required);
```

### User Rewards Table

```sql
CREATE TABLE user_rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    reward_id INTEGER NOT NULL,
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, reward_id)
);

CREATE INDEX idx_user_rewards_user_id ON user_rewards(user_id);
CREATE INDEX idx_user_rewards_reward_id ON user_rewards(reward_id);
```

---

## 🔍 Verification

### Check Tables Exist

```python
from src.app import create_app
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    from src.db.models import db
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    required = ['player_levels', 'xp_history', 'daily_activities', 'rewards', 'user_rewards']
    for table in required:
        if table in tables:
            print(f"✅ {table} exists")
        else:
            print(f"❌ {table} missing")
```

### Check Rewards Data

```python
from src.app import create_app

app = create_app()
with app.app_context():
    from src.db.models import db
    
    result = db.session.execute("SELECT COUNT(*) FROM rewards")
    count = result.scalar()
    print(f"Total rewards: {count}")
    
    result = db.session.execute("SELECT reward_name, reward_type FROM rewards LIMIT 10")
    for row in result:
        print(f"  {row[0]} ({row[1]})")
```

---

## 📝 Reward Data Structure

### Level-Based Reward Example

```json
{
  "reward_type": "level",
  "reward_name": "Level 5 Achievement",
  "level_required": 5,
  "reward_data": {
    "themes": ["premium", "nature"],
    "stat_points": 5
  }
}
```

### Points-Based Reward Example

```json
{
  "reward_type": "points",
  "reward_name": "1,000 XP Reward",
  "points_required": 1000,
  "point_type": "xp",
  "reward_data": {
    "stat_points": 2,
    "themes": ["starter"]
  }
}
```

---

## ✅ Next Steps

### 1. Test Database Connection
- Verify tables are accessible
- Test queries
- Verify indexes

### 2. Implement Backend Endpoints
- `/api/game/hunters/rewards/next` - Get next reward
- `/api/game/hunters/rewards/by-points` - Get rewards by point type
- `/api/game/hunters/rewards/claim` - Claim reward

### 3. Test Points Page
- Verify rewards load correctly
- Test reward eligibility
- Test reward claiming

### 4. Add More Rewards
- Customize rewards for your game
- Add achievement-based rewards
- Add milestone rewards

---

## 🐛 Troubleshooting

### Tables Not Created

**Problem:** Migration script runs but tables don't exist

**Solutions:**
1. Check database permissions
2. Verify database path is correct
3. Check for SQL errors in output
4. Try running with verbose logging

### Rewards Not Inserting

**Problem:** Rewards population fails

**Solutions:**
1. Verify rewards table exists first
2. Check for duplicate key errors
3. Verify JSON format in reward_data
4. Check database connection

### Foreign Key Errors

**Problem:** user_rewards table has foreign key issues

**Solutions:**
1. SQLite doesn't enforce foreign keys by default
2. This is expected behavior
3. Application logic should handle referential integrity

---

## 📚 Related Files

- `docs/LOOSE_ENDS_AND_DATABASE_ANALYSIS.md` - Complete analysis
- `docs/POINTS_PAGE_IMPLEMENTATION_SUMMARY.md` - Points page docs
- `scripts/migrate_hunters_game.py` - Original migration (without rewards)
- `vidgenerator/points/index.html` - Points page frontend

---

**Last Updated:** 2025-01-20
