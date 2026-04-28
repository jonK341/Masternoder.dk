# Onboarding and Profiles Integration Guide

**Date:** 2025-01-20  
**Status:** 📋 INTEGRATION PLAN

---

## 🔗 Integration Overview

This document outlines how the onboarding and profile systems integrate with each other and with existing systems.

---

## 🔄 System Integration Flow

```
New User Arrives
    ↓
Onboarding System Detects
    ↓
Profile Created (Minimal)
    ↓
Onboarding Flow Starts
    ↓
Profile Enriched (Automated)
    ↓
Skills Assigned
    ↓
First Actions Completed
    ↓
Profile Completed
    ↓
Onboarding Complete
    ↓
Full Profile Access
```

---

## 🔌 Integration Points

### 1. Onboarding → Profile

**Data Flow:**
- Onboarding creates initial profile
- Onboarding collects basic profile data
- Onboarding triggers profile enrichment
- Onboarding updates profile completion status

**API Calls:**
```javascript
// During onboarding
POST /api/user/create
POST /api/user/enrich-profile
PUT /api/user/profile/{user_id}
```

### 2. Profile → Onboarding

**Data Flow:**
- Profile completion triggers onboarding completion
- Profile data influences onboarding recommendations
- Profile stats affect onboarding progress

**API Calls:**
```javascript
// Check onboarding status
GET /api/user/onboarding/status
// Update based on profile
POST /api/user/onboarding/complete-step
```

### 3. Agent Skills → Both Systems

**Data Flow:**
- Onboarding assigns initial skills
- Profile displays skill information
- Skills influence profile recommendations
- Profile stats include skill data

**API Calls:**
```javascript
// Skill assignment
POST /api/user/assign-skill
GET /api/user/agent-skills/{user_id}
```

### 4. Points System → Both Systems

**Data Flow:**
- Onboarding awards welcome points
- Profile displays point statistics
- Points unlock profile features
- Points influence onboarding progress

**API Calls:**
```javascript
// Points during onboarding
POST /api/points/award
GET /api/points/comprehensive
```

---

## 📊 Data Sharing

### Shared Data Models

```python
# User Profile Data
{
    "user_id": "user_123",
    "profile": {
        "basic_info": {...},
        "preferences": {...},
        "stats": {...},
        "skills": {...},
        "onboarding": {
            "status": "completed",
            "completed_steps": [...],
            "skill_path": "balanced"
        }
    }
}
```

### Data Synchronization

**Real-time Updates:**
- Profile changes update onboarding status
- Onboarding progress updates profile
- Skill changes update both systems
- Point changes update profile stats

**Batch Updates:**
- Daily profile enrichment
- Weekly onboarding analytics
- Monthly skill progression
- Quarterly profile optimization

---

## 🎯 Integration Features

### 1. Unified User Experience
- Seamless transition from onboarding to profile
- Consistent UI/UX across systems
- Shared navigation and components
- Unified data display

### 2. Cross-System Recommendations
- Profile-based onboarding suggestions
- Onboarding-based profile recommendations
- Skill-based feature suggestions
- Activity-based content recommendations

### 3. Unified Analytics
- Combined onboarding and profile metrics
- Cross-system user journey tracking
- Unified reporting dashboard
- Integrated insights

---

## 🛠️ Technical Implementation

### Service Integration

```python
# backend/services/integrated_user_service.py
class IntegratedUserService:
    def __init__(self):
        self.onboarding = UserOnboarding()
        self.profile = UserProfile()
        self.skills = UserAgentSkills()
        self.scraper = UserInfoScraper()
    
    def create_new_user(self, user_id):
        # Create profile
        profile = self.profile.create(user_id)
        
        # Start onboarding
        onboarding = self.onboarding.start(user_id)
        
        # Scrape info
        info = self.scraper.scrape(user_id)
        
        # Enrich profile
        self.profile.enrich(user_id, info)
        
        # Assign skills
        self.skills.assign_initial(user_id)
        
        return {
            'profile': profile,
            'onboarding': onboarding,
            'skills': self.skills.get(user_id)
        }
```

### Frontend Integration

```javascript
// Frontend: Unified User Manager
class UnifiedUserManager {
    constructor() {
        this.onboarding = new OnboardingManager();
        this.profile = new ProfileManager();
    }
    
    async initializeUser(userId) {
        // Check onboarding status
        const onboardingStatus = await this.onboarding.getStatus(userId);
        
        // Load profile
        const profile = await this.profile.load(userId);
        
        // If onboarding incomplete, show onboarding
        if (!onboardingStatus.completed) {
            await this.onboarding.start();
        }
        
        // Update profile based on onboarding
        if (onboardingStatus.completed) {
            await this.profile.complete();
        }
    }
}
```

---

## 📋 Integration Checklist

### Backend Integration
- [ ] Create integrated user service
- [ ] Connect onboarding to profile
- [ ] Connect profile to onboarding
- [ ] Integrate with agent skills
- [ ] Integrate with points system
- [ ] Add data synchronization
- [ ] Add cross-system APIs

### Frontend Integration
- [ ] Create unified user manager
- [ ] Connect onboarding UI to profile
- [ ] Connect profile UI to onboarding
- [ ] Add shared components
- [ ] Add unified navigation
- [ ] Add cross-system features

### Testing Integration
- [ ] Test onboarding → profile flow
- [ ] Test profile → onboarding flow
- [ ] Test skill integration
- [ ] Test points integration
- [ ] Test data synchronization
- [ ] Test cross-system features

---

## 🚀 Deployment Strategy

### Phase 1: Backend Integration
1. Deploy integrated services
2. Update API endpoints
3. Test backend integration
4. Monitor performance

### Phase 2: Frontend Integration
1. Deploy unified UI
2. Update frontend components
3. Test user flows
4. Gather feedback

### Phase 3: Full Integration
1. Complete integration
2. Full system testing
3. Performance optimization
4. Production deployment

---

**Status:** 📋 Integration Plan Complete

**Next:** Begin implementation of integration points

---

**End of Integration Guide**
