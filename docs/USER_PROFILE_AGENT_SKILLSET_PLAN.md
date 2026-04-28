# User Profile & Agent Skillset System - Comprehensive Plan

**Date:** 2025-01-20  
**Status:** 🚀 IMPLEMENTATION  
**Type:** User Onboarding with Agent Skill Assignment & Info Scraping

---

## 🎯 Overview

A comprehensive system for user profiles with integrated agent skill sets. New users go through an automated onboarding process that scrapes information and assigns appropriate agent skills based on their profile and behavior.

---

## ✨ Core Features

### 1. **Enhanced User Profile System**
- Extended user profile with agent skill set tracking
- User preferences and behavior patterns
- Scraped information storage
- Agent assignment history
- Skill progression tracking

### 2. **Automated User Onboarding**
- Automatic user creation on first visit
- Information scraping from:
  - Browser/device fingerprinting
  - User agent strings
  - IP geolocation
  - Referral sources
  - Initial behavior patterns
  - Timezone and locale
- Profile enrichment over time

### 3. **Agent Skill Set Assignment**
- Automatic skill assignment based on:
  - User behavior patterns
  - Scraped information
  - User preferences
  - Activity types
- Skill progression system
- Skill unlocking mechanism
- Agent specialization paths

### 4. **Information Scraping System**
- Browser information collection
- Device fingerprinting
- Behavioral pattern analysis
- Preference inference
- Activity tracking
- Social signals detection

---

## 📋 System Architecture

### Components

1. **UserProfile Model** (`src/db/models.py`)
   - Extended with agent skill fields
   - Scraped data storage
   - Agent assignment tracking

2. **User Onboarding Service** (`backend/services/user_onboarding.py`)
   - User creation logic
   - Information scraping
   - Profile initialization

3. **Agent Skill Assigner** (`backend/services/user_agent_skills.py`)
   - Skill assignment logic
   - Skill progression
   - Agent matching

4. **User Profile Routes** (`backend/routes/user_profile_routes.py`)
   - User creation endpoints
   - Profile management
   - Skill management

5. **Info Scraper** (`backend/services/user_info_scraper.py`)
   - Browser/device info collection
   - Behavioral analysis
   - Data enrichment

---

## 🗄️ Database Schema

### UserProfile Table (Enhanced)
```sql
CREATE TABLE IF NOT EXISTS user_profiles (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE NOT NULL,
    username VARCHAR(100),
    preferences TEXT,  -- JSON
    agent_skillset_id VARCHAR(100),  -- Reference to agent skillset
    assigned_agent_ids TEXT,  -- JSON array of agent IDs
    skill_levels TEXT,  -- JSON object {skill: level}
    scraped_info TEXT,  -- JSON object with scraped data
    onboarding_complete BOOLEAN DEFAULT FALSE,
    onboarding_data TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### User Scraped Info Table
```sql
CREATE TABLE IF NOT EXISTS user_scraped_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    info_type VARCHAR(50) NOT NULL,  -- browser, device, location, behavior, etc.
    info_data TEXT,  -- JSON
    confidence_score DECIMAL(3,2),  -- 0.00 to 1.00
    source VARCHAR(100),  -- scraping method
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);
```

### User Agent Skills Table
```sql
CREATE TABLE IF NOT EXISTS user_agent_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    skill_name VARCHAR(100) NOT NULL,
    skill_level INTEGER DEFAULT 1,
    experience_points INTEGER DEFAULT 0,
    unlocked_at TIMESTAMP,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);
```

---

## 🔄 User Onboarding Flow

### Step 1: User Detection
- User visits site for first time
- System detects new user (IP/MAC/device fingerprint)
- Creates temporary user ID

### Step 2: Information Scraping
- Collect browser information:
  - User agent
  - Screen resolution
  - Timezone
  - Language
  - Plugins
  - Canvas fingerprint
- Collect device information:
  - Device type
  - OS
  - Browser version
- Collect behavioral data:
  - Initial page views
  - Click patterns
  - Time spent
  - Referral source

### Step 3: Profile Creation
- Create UserProfile record
- Store scraped information
- Initialize preferences
- Set default agent skillset

### Step 4: Agent Skill Assignment
- Analyze scraped data
- Match user profile to agent types
- Assign initial skills
- Create skill progression plan

### Step 5: Onboarding Completion
- Mark onboarding as complete
- Initialize user points
- Create initial quests/missions
- Welcome message

---

## 🤖 Agent Skill Assignment Logic

### Skill Assignment Rules

1. **Content Creator Path**
   - Skills: `generate_video`, `generate_image`, `create_template`
   - Trigger: User shows interest in content generation
   - Agents: `content_generator_agent`

2. **Battle Strategist Path**
   - Skills: `analyze_battle`, `create_strategy`, `optimize_tactics`
   - Trigger: User engages with battle system
   - Agents: `battle_strategy_agent`

3. **Social Player Path**
   - Skills: `manage_friends`, `coordinate_events`, `build_community`
   - Trigger: User shows social engagement
   - Agents: `social_engagement_agent`

4. **Analytics Path**
   - Skills: `analyze_user_behavior`, `track_metrics`, `generate_reports`
   - Trigger: User views analytics/stats
   - Agents: `analytics_agent`

5. **Balanced Path** (Default)
   - Skills: Mix of basic skills from multiple agents
   - Trigger: No specific pattern detected
   - Agents: Multiple agents with basic skills

### Skill Progression

- **Level 1**: Basic skills unlocked
- **Level 2**: Unlock at 100 XP
- **Level 3**: Unlock at 300 XP
- **Level 4**: Unlock at 600 XP
- **Level 5**: Unlock at 1000 XP

---

## 📡 API Endpoints

### User Creation & Onboarding

```
POST /api/user/create
POST /vidgenerator/api/user/create
- Create new user with scraping
- Body: {device_info, browser_info, initial_behavior}
- Returns: {user_id, profile, assigned_skills}

GET /api/user/profile/<user_id>
GET /vidgenerator/api/user/profile/<user_id>
- Get user profile with agent skills

POST /api/user/scrape-info
POST /vidgenerator/api/user/scrape-info
- Trigger additional info scraping
- Body: {user_id, scrape_type}
```

### Agent Skills Management

```
GET /api/user/agent-skills/<user_id>
GET /vidgenerator/api/user/agent-skills/<user_id>
- Get user's agent skills

POST /api/user/assign-skill
POST /vidgenerator/api/user/assign-skill
- Manually assign skill to user
- Body: {user_id, agent_id, skill_name}

POST /api/user/level-up-skill
POST /vidgenerator/api/user/level-up-skill
- Level up a skill
- Body: {user_id, skill_name, experience}
```

### Scraped Info

```
GET /api/user/scraped-info/<user_id>
GET /vidgenerator/api/user/scraped-info/<user_id>
- Get all scraped information

POST /api/user/enrich-profile
POST /vidgenerator/api/user/enrich-profile
- Enrich profile with additional scraping
- Body: {user_id, enrichment_type}
```

---

## 🔧 Implementation Steps

1. ✅ Create comprehensive plan document
2. ⏳ Create/update UserProfile model
3. ⏳ Create user onboarding service
4. ⏳ Create info scraper service
5. ⏳ Create agent skill assigner
6. ⏳ Create user profile routes
7. ⏳ Integrate with existing agent system
8. ⏳ Register blueprints
9. ⏳ Test user creation flow
10. ⏳ Test agent skill assignment

---

## 🎨 Frontend Integration

### User Onboarding UI
- Welcome screen for new users
- Profile setup wizard
- Agent skill selection (optional)
- Onboarding progress indicator

### Profile Display
- Show assigned agent skills
- Skill progression bars
- Agent recommendations
- Scraped info summary (privacy-aware)

---

## 🔒 Privacy & Security

- Store only necessary information
- Anonymize sensitive data
- User consent for scraping
- GDPR compliance
- Data retention policies
- User data export/deletion

---

## 📊 Analytics & Monitoring

- Track onboarding completion rates
- Monitor skill assignment distribution
- Analyze scraping effectiveness
- User engagement metrics
- Agent skill usage statistics

---

## 🚀 Future Enhancements

1. **AI-Powered Skill Assignment**
   - Machine learning for skill matching
   - Predictive skill recommendations

2. **Advanced Scraping**
   - Social media profile analysis
   - External data enrichment
   - Behavioral prediction

3. **Skill Marketplace**
   - Users can trade skills
   - Skill sharing between users
   - Custom skill creation

4. **Agent Personalization**
   - Custom agent creation
   - Agent personality matching
   - Dynamic skill adaptation

---

## 📝 Notes

- All scraping must respect user privacy
- Agent skills should enhance, not limit user experience
- Onboarding should be quick and non-intrusive
- Skill assignment should be transparent
- Users should be able to modify their skills

---

**End of Plan**
