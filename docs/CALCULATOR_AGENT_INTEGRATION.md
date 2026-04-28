# Calculator Agent Integration Guide

## Overview

The Advanced Calculator has been integrated into the Agent System with skills, abilities, missions, and quests. These can be used as click quests in the click-through game system.

## Calculator Skills Added

1. **calculate_with_intelligence** - Perform intelligent calculations
2. **detect_point_loss** - Detect point losses
3. **repair_all_systems** - Repair all systems
4. **predict_future_points** - Predict future points
5. **analyze_patterns** - Analyze patterns
6. **get_calculator_statistics** - Get calculator statistics

## Calculator Missions

### Mission 1: Intelligence Calculator Master
- **Description**: Perform 10 intelligent calculations
- **Tasks**: 10 calculation tasks
- **Reward**: 150 XP, 1000 points

### Mission 2: Loss Detection Specialist
- **Description**: Detect and analyze 5 point losses
- **Tasks**: 5 detection tasks
- **Reward**: 120 XP, 800 points

### Mission 3: System Repair Expert
- **Description**: Repair systems 3 times
- **Tasks**: 3 repair tasks
- **Reward**: 100 XP, 600 points

### Mission 4: Future Predictor
- **Description**: Make 5 predictions for different users
- **Tasks**: 5 prediction tasks
- **Reward**: 130 XP, 900 points

### Mission 5: Pattern Analyzer
- **Description**: Analyze patterns for 3 users
- **Tasks**: 3 analysis tasks
- **Reward**: 110 XP, 700 points

## Calculator Quests

### Quest 1: Calculator Master Quest
- **Objectives**: Complete all calculator skills
- **Reward**: 200 XP, Calculator Master achievement, 1500 points

### Quest 2: Prediction Master Quest
- **Objectives**: Make predictions for 7, 30, and 90 days
- **Reward**: 180 XP, Prediction Master achievement, 1200 points

### Quest 3: System Guardian Quest
- **Objectives**: Detect losses and repair systems
- **Reward**: 170 XP, System Guardian achievement, 1100 points

### Quest 4: Pattern Analysis Expert
- **Objectives**: Analyze patterns and get statistics
- **Reward**: 160 XP, Pattern Expert achievement, 1000 points

## Using as Click Quests

Calculator missions and quests can be integrated into the click-through game system:

### In click-through-game.js

Add calculator missions to the missions array:
```javascript
{
    id: 'calc_mission_1',
    name: 'Intelligence Calculator Master',
    target: 10,  // 10 calculations
    reward: 1000,
    type: 'calculator'
}
```

Add calculator quests to the quests array:
```javascript
{
    id: 'calc_quest_1',
    name: 'Calculator Master Quest',
    target: 5,  // Complete 5 objectives
    reward: 1500,
    type: 'calculator'
}
```

### Tracking Progress

In the click game, track calculator skill usage:
```javascript
async function trackCalculatorSkill(skillName, userId) {
    const response = await fetch(`/api/agent/master-fix/skill/${skillName}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({user_id: userId})
    });
    return await response.json();
}

// Check mission/quest completion
async function checkCalculatorProgress() {
    const missions = await fetch('/api/agent/master-fix/missions?status=active');
    const quests = await fetch('/api/agent/master-fix/quests?status=in_progress');
    // Update UI with progress
}
```

## API Endpoints

### Execute Calculator Skill
```
POST /api/agent/master-fix/skill/calculate_with_intelligence
POST /vidgenerator/api/agent/master-fix/skill/calculate_with_intelligence
Body: {"user_id": "user_001"}
```

### Get Missions
```
GET /api/agent/master-fix/missions
GET /api/agent/master-fix/missions?status=active
```

### Get Quests
```
GET /api/agent/master-fix/quests
GET /api/agent/master-fix/quests?status=in_progress
```

## Integration Example

```javascript
// Example: Complete a calculator mission
async function completeCalculatorMission(missionId) {
    // Execute calculator skills
    await trackCalculatorSkill('calculate_with_intelligence', userId);
    
    // Check mission progress
    const missions = await fetch('/api/agent/master-fix/missions');
    const missionData = await missions.json();
    const mission = missionData.missions.find(m => m.id === missionId);
    
    // Update click game progress
    if (mission.progress >= 100) {
        clickGame.completeMission(missionId);
    }
}
```

## Next Steps

1. Integrate calculator missions into click-through-game.js
2. Add calculator quest tracking to the click game
3. Create UI elements for calculator missions/quests
4. Add calculator skill buttons to the agent interface
5. Test all calculator skills through the agent system
