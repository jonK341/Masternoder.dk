# Calculator Click Quests Integration Guide

## Overview

Calculator missions and quests can be integrated into the click-through game system as "click quests" - interactive quests that players can complete through clicking and using calculator skills.

## Calculator Missions as Click Quests

Calculator missions are perfect for click quests because they:
- Have clear targets (e.g., "Perform 10 calculations")
- Track progress automatically
- Offer rewards (XP and points)
- Integrate with the agent system

## Integration Steps

### 1. Load Calculator Missions in Click Game

Add calculator missions to the click game's mission system:

```javascript
// In click-through-game.js, add to loadGameData()
async loadGameData() {
    // ... existing code ...
    
    // Load calculator missions from agent system
    try {
        const response = await fetch(`${this.baseUrl}/api/agent/master-fix/missions?status=active`);
        const data = await response.json();
        
        if (data.success && data.missions) {
            // Filter calculator missions
            const calcMissions = data.missions.filter(m => m.id.startsWith('calc_mission'));
            
            // Add to missions array
            calcMissions.forEach(mission => {
                this.missions.push({
                    id: mission.id,
                    name: mission.name,
                    target: mission.target || 10,
                    reward: mission.reward?.points || 1000,
                    type: 'calculator',
                    description: mission.description,
                    progress: mission.progress || 0
                });
            });
        }
    } catch (error) {
        console.error('Error loading calculator missions:', error);
    }
}
```

### 2. Track Calculator Skill Usage

When a calculator skill is used, update mission progress:

```javascript
// Add method to track calculator skills
async trackCalculatorSkill(skillName, userId) {
    try {
        // Execute calculator skill
        const response = await fetch(`${this.baseUrl}/api/agent/master-fix/skill/${skillName}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_id: userId})
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Update relevant mission progress
            this.updateCalculatorMissionProgress(skillName);
            
            return result;
        }
    } catch (error) {
        console.error(`Error executing calculator skill ${skillName}:`, error);
    }
}

// Update mission progress based on skill
updateCalculatorMissionProgress(skillName) {
    this.missions.forEach(mission => {
        if (mission.type === 'calculator') {
            // Map skill names to mission IDs
            const skillToMission = {
                'calculate_with_intelligence': 'calc_mission_1',
                'detect_point_loss': 'calc_mission_2',
                'repair_all_systems': 'calc_mission_3',
                'predict_future_points': 'calc_mission_4',
                'analyze_patterns': 'calc_mission_5'
            };
            
            if (skillToMission[skillName] === mission.id) {
                mission.progress = (mission.progress || 0) + 1;
                
                // Check if mission complete
                if (mission.progress >= mission.target) {
                    this.completeCalculatorMission(mission);
                }
            }
        }
    });
}

// Complete calculator mission
async completeCalculatorMission(mission) {
    try {
        const response = await fetch(`${this.baseUrl}/api/agent/master-fix/complete-mission`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({mission_id: mission.id})
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Award reward
            this.points += mission.reward;
            this.totalEarned += mission.reward;
            
            // Show notification
            this.showNotification(`Mission Complete: ${mission.name}! +${mission.reward} points`, 'success');
            
            // Update UI
            this.updateMissionDisplay();
        }
    } catch (error) {
        console.error('Error completing mission:', error);
    }
}
```

### 3. Add Calculator Skill Buttons to UI

Add calculator skill buttons that players can click:

```javascript
// Add calculator skills section to UI
createCalculatorSkillsUI() {
    return `
        <div class="calculator-skills-section">
            <h3>Calculator Skills</h3>
            <div class="calculator-buttons">
                <button class="calc-skill-btn" data-skill="calculate_with_intelligence">
                    🧮 Calculate Points
                </button>
                <button class="calc-skill-btn" data-skill="detect_point_loss">
                    🔍 Detect Losses
                </button>
                <button class="calc-skill-btn" data-skill="repair_all_systems">
                    🔧 Repair Systems
                </button>
                <button class="calc-skill-btn" data-skill="predict_future_points">
                    🔮 Predict Future
                </button>
                <button class="calc-skill-btn" data-skill="analyze_patterns">
                    📊 Analyze Patterns
                </button>
            </div>
        </div>
    `;
}

// Add click handlers
initializeCalculatorSkills() {
    document.querySelectorAll('.calc-skill-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const skillName = btn.dataset.skill;
            
            // Check energy cost
            if (this.energy < 10) {
                this.showNotification('Not enough energy!', 'error');
                return;
            }
            
            // Use energy
            this.energy -= 10;
            
            // Execute skill
            const result = await this.trackCalculatorSkill(skillName, this.userId);
            
            if (result && result.success) {
                this.showNotification(`Used ${skillName}!`, 'success');
            }
        });
    });
}
```

### 4. Calculator Quests Integration

Load and track calculator quests:

```javascript
// Load calculator quests
async loadCalculatorQuests() {
    try {
        const response = await fetch(`${this.baseUrl}/api/agent/master-fix/quests?status=available`);
        const data = await response.json();
        
        if (data.success && data.quests) {
            const calcQuests = data.quests.filter(q => q.id.startsWith('calc_quest'));
            
            calcQuests.forEach(quest => {
                this.quests.push({
                    id: quest.id,
                    name: quest.name,
                    description: quest.description,
                    objectives: quest.objectives,
                    reward: quest.reward?.points || 1500,
                    type: 'calculator',
                    status: quest.status,
                    progress: quest.progress || {}
                });
            });
        }
    } catch (error) {
        console.error('Error loading calculator quests:', error);
    }
}

// Update quest progress
async updateCalculatorQuestProgress(questId, objectiveId) {
    try {
        const response = await fetch(`${this.baseUrl}/api/agent/master-fix/update-quest-progress`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                quest_id: questId,
                objective_id: objectiveId,
                progress: 100
            })
        });
        
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error updating quest progress:', error);
    }
}
```

## Mission Details

### Mission 1: Intelligence Calculator Master
- **Target**: 10 calculations
- **Reward**: 150 XP, 1000 points
- **Skill**: `calculate_with_intelligence`

### Mission 2: Loss Detection Specialist
- **Target**: 5 detections
- **Reward**: 120 XP, 800 points
- **Skill**: `detect_point_loss`

### Mission 3: System Repair Expert
- **Target**: 3 repairs
- **Reward**: 100 XP, 600 points
- **Skill**: `repair_all_systems`

### Mission 4: Future Predictor
- **Target**: 5 predictions
- **Reward**: 130 XP, 900 points
- **Skill**: `predict_future_points`

### Mission 5: Pattern Analyzer
- **Target**: 3 analyses
- **Reward**: 110 XP, 700 points
- **Skill**: `analyze_patterns`

## Quest Details

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

### Complete Mission
```
POST /api/agent/master-fix/complete-mission
Body: {"mission_id": "calc_mission_1"}
```

### Get Quests
```
GET /api/agent/master-fix/quests
GET /api/agent/master-fix/quests?status=available
```

### Update Quest Progress
```
POST /api/agent/master-fix/update-quest-progress
Body: {
    "quest_id": "calc_quest_1",
    "objective_id": "calc_intelligence",
    "progress": 100
}
```

## Example Integration

See `scripts/integrate_calculator_to_agents.py` for a complete integration script that:
1. Adds calculator skills to agent skillset
2. Initializes calculator missions and quests
3. Creates documentation

## Testing

To test calculator click quests:

1. Run the integration script:
   ```bash
   python scripts/integrate_calculator_to_agents.py
   ```

2. Start the click game and verify calculator missions/quests appear

3. Use calculator skills and verify progress updates

4. Complete missions/quests and verify rewards are awarded
