/**
 * Agent Skill Sets Integration
 * Manages agent skill sets and abilities based on point systems
 */
class AgentSkillSets {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || window.location.origin;
        this.skillSets = new Map();
        this.agentAbilities = new Map();
        this.init();
    }

    init() {
        // Load skill sets data
        this.loadSkillSetsData();
        
        // Listen for point updates to check ability unlocks
        document.addEventListener('serviceUpdate', (event) => {
            if (event.detail.serviceName === 'points') {
                this.checkAbilityUnlocks(event.detail.data);
            }
        });
    }

    // Load skill sets from 178 point systems
    loadSkillSetsData() {
        // Skill sets structure based on 178_POINT_SYSTEMS_EXPANSION_PLAN.md
        const skillSetsData = {
            // Category 1: Core Engagement
            'xp': {
                name: 'Experience Mastery',
                abilities: [
                    { name: 'Basic Experience', threshold: 0, multiplier: 1.0 },
                    { name: 'Quick Learner', threshold: 100, multiplier: 1.1 },
                    { name: 'Fast Tracker', threshold: 500, multiplier: 1.2 },
                    { name: 'Rapid Progress', threshold: 1000, multiplier: 1.3 },
                    { name: 'Expert Learner', threshold: 2500, multiplier: 1.5 },
                    { name: 'Master Experience', threshold: 5000, multiplier: 2.0 },
                    { name: 'Legendary XP', threshold: 10000, multiplier: 2.5 }
                ]
            },
            'activity': {
                name: 'Activity Excellence',
                abilities: [
                    { name: 'Active User', threshold: 0, multiplier: 1.0 },
                    { name: 'Regular Participant', threshold: 50, multiplier: 1.1 },
                    { name: 'Daily Active', threshold: 200, multiplier: 1.1 },
                    { name: 'Highly Active', threshold: 500, multiplier: 1.2 },
                    { name: 'Activity Champion', threshold: 1000, multiplier: 1.3 },
                    { name: 'Activity Master', threshold: 2500, multiplier: 1.5 },
                    { name: 'Activity Legend', threshold: 5000, multiplier: 2.0 }
                ]
            },
            'battle': {
                name: 'Combat Mastery',
                abilities: [
                    { name: 'Warrior', threshold: 0, multiplier: 1.0 },
                    { name: 'Skilled Fighter', threshold: 100, multiplier: 1.1 },
                    { name: 'Battle Veteran', threshold: 500, multiplier: 1.2 },
                    { name: 'Combat Expert', threshold: 1000, multiplier: 1.3 },
                    { name: 'Battle Master', threshold: 2500, multiplier: 1.5 },
                    { name: 'Combat Legend', threshold: 5000, multiplier: 2.0 }
                ]
            },
            'video_generation': {
                name: 'Video Production Mastery',
                abilities: [
                    { name: 'Video Creator', threshold: 0, multiplier: 1.0 },
                    { name: 'Video Editor', threshold: 100, multiplier: 1.1 },
                    { name: 'Video Producer', threshold: 500, multiplier: 1.2 },
                    { name: 'Video Director', threshold: 1000, multiplier: 1.3 },
                    { name: 'Video Master', threshold: 2500, multiplier: 1.5 },
                    { name: 'Video Legend', threshold: 5000, multiplier: 2.0 }
                ]
            },
            'generation_points': {
                name: 'Generator Mastery',
                abilities: [
                    { name: 'Clip Starter', threshold: 0, multiplier: 1.0 },
                    { name: 'Scene Crafter', threshold: 100, multiplier: 1.1 },
                    { name: 'Story Builder', threshold: 500, multiplier: 1.2 },
                    { name: 'Video Architect', threshold: 1000, multiplier: 1.3 },
                    { name: 'Generation Master', threshold: 2500, multiplier: 1.5 },
                    { name: 'Generation Legend', threshold: 5000, multiplier: 2.0 }
                ]
            },
            'quality_points': {
                name: 'Tester Agent Quality Gate',
                abilities: [
                    { name: 'A- Validation', threshold: 0, multiplier: 1.0 },
                    { name: 'Cross-Browser Verified', threshold: 100, multiplier: 1.1 },
                    { name: 'Mobile Ready', threshold: 400, multiplier: 1.2 },
                    { name: 'Regression Guard', threshold: 900, multiplier: 1.3 },
                    { name: 'Release Gatekeeper', threshold: 1800, multiplier: 1.5 },
                    { name: 'A+++ Quality Champion', threshold: 3000, multiplier: 2.0 }
                ]
            },
            'activity_points': {
                name: 'Execution Discipline',
                abilities: [
                    { name: 'Routine Runner', threshold: 0, multiplier: 1.0 },
                    { name: 'Task Executor', threshold: 100, multiplier: 1.1 },
                    { name: 'Flow Optimizer', threshold: 500, multiplier: 1.2 },
                    { name: 'Ops Specialist', threshold: 1000, multiplier: 1.3 },
                    { name: 'Execution Master', threshold: 2500, multiplier: 1.5 }
                ]
            },
            'battle_points': {
                name: 'Battle Operations',
                abilities: [
                    { name: 'Arena Scout', threshold: 0, multiplier: 1.0 },
                    { name: 'Duel Strategist', threshold: 100, multiplier: 1.1 },
                    { name: 'Skirmish Captain', threshold: 500, multiplier: 1.2 },
                    { name: 'Battle Marshal', threshold: 1000, multiplier: 1.3 },
                    { name: 'War Legend', threshold: 2500, multiplier: 1.5 }
                ]
            },
            'quest_points': {
                name: 'Quest Progression',
                abilities: [
                    { name: 'Quest Initiate', threshold: 0, multiplier: 1.0 },
                    { name: 'Path Finder', threshold: 80, multiplier: 1.1 },
                    { name: 'Objective Solver', threshold: 350, multiplier: 1.2 },
                    { name: 'Campaign Leader', threshold: 800, multiplier: 1.3 },
                    { name: 'Quest Grandmaster', threshold: 1800, multiplier: 1.5 }
                ]
            },
            'social_points': {
                name: 'Community Influence',
                abilities: [
                    { name: 'Connector', threshold: 0, multiplier: 1.0 },
                    { name: 'Community Helper', threshold: 100, multiplier: 1.1 },
                    { name: 'Network Builder', threshold: 500, multiplier: 1.2 },
                    { name: 'Influence Leader', threshold: 1000, multiplier: 1.3 },
                    { name: 'Social Legend', threshold: 2500, multiplier: 1.5 }
                ]
            },
            'pvp_battle': {
                name: 'Player vs Player Mastery',
                abilities: [
                    { name: 'PvP Novice', threshold: 0, multiplier: 1.0 },
                    { name: 'PvP Fighter', threshold: 100, multiplier: 1.1 },
                    { name: 'PvP Warrior', threshold: 500, multiplier: 1.2 },
                    { name: 'PvP Expert', threshold: 1000, multiplier: 1.3 },
                    { name: 'PvP Master', threshold: 2500, multiplier: 1.5 },
                    { name: 'PvP Legend', threshold: 5000, multiplier: 2.0 },
                    { name: 'PvP Champion', threshold: 10000, multiplier: 2.5 }
                ]
            },
            'level_up': {
                name: 'Leveling Mastery',
                abilities: [
                    { name: 'Leveler', threshold: 0, multiplier: 1.0 },
                    { name: 'Fast Leveler', threshold: 100, multiplier: 1.1 },
                    { name: 'Expert Leveler', threshold: 500, multiplier: 1.2 },
                    { name: 'Master Leveler', threshold: 1000, multiplier: 1.3 },
                    { name: 'Leveling Legend', threshold: 2500, multiplier: 1.5 }
                ]
            },
            'exploration': {
                name: 'Exploration Mastery',
                abilities: [
                    { name: 'Explorer', threshold: 0, multiplier: 1.0 },
                    { name: 'Adventurer', threshold: 100, multiplier: 1.1 },
                    { name: 'Discovery Expert', threshold: 500, multiplier: 1.2 },
                    { name: 'Exploration Master', threshold: 1000, multiplier: 1.3 },
                    { name: 'Exploration Legend', threshold: 2500, multiplier: 1.5 }
                ]
            },
            'learning': {
                name: 'Learning Mastery',
                abilities: [
                    { name: 'Learner', threshold: 0, multiplier: 1.0 },
                    { name: 'Quick Learner', threshold: 100, multiplier: 1.1 },
                    { name: 'Learning Expert', threshold: 500, multiplier: 1.2 },
                    { name: 'Learning Master', threshold: 1000, multiplier: 1.3 },
                    { name: 'Learning Legend', threshold: 2500, multiplier: 1.5 }
                ]
            },
            'innovation': {
                name: 'Innovation Mastery',
                abilities: [
                    { name: 'Innovator', threshold: 0, multiplier: 1.0 },
                    { name: 'Creative Thinker', threshold: 100, multiplier: 1.1 },
                    { name: 'Innovation Expert', threshold: 500, multiplier: 1.2 },
                    { name: 'Innovation Master', threshold: 1000, multiplier: 1.3 },
                    { name: 'Innovation Legend', threshold: 2500, multiplier: 1.5 }
                ]
            }
        };

        // Store skill sets
        Object.entries(skillSetsData).forEach(([pointType, skillSet]) => {
            this.skillSets.set(pointType, skillSet);
        });
    }

    // Get skill set for a point type
    getSkillSet(pointType) {
        return this.skillSets.get(pointType) || null;
    }

    // Get current ability for a point type based on points
    getCurrentAbility(pointType, currentPoints) {
        const skillSet = this.getSkillSet(pointType);
        if (!skillSet) return null;

        // Find the highest ability unlocked
        let currentAbility = skillSet.abilities[0];
        for (const ability of skillSet.abilities) {
            if (currentPoints >= ability.threshold) {
                currentAbility = ability;
            } else {
                break;
            }
        }

        return currentAbility;
    }

    // Get all unlocked abilities for a point type
    getUnlockedAbilities(pointType, currentPoints) {
        const skillSet = this.getSkillSet(pointType);
        if (!skillSet) return [];

        return skillSet.abilities.filter(ability => currentPoints >= ability.threshold);
    }

    // Get next ability to unlock
    getNextAbility(pointType, currentPoints) {
        const skillSet = this.getSkillSet(pointType);
        if (!skillSet) return null;

        for (const ability of skillSet.abilities) {
            if (currentPoints < ability.threshold) {
                return {
                    ...ability,
                    pointsNeeded: ability.threshold - currentPoints
                };
            }
        }

        return null; // All abilities unlocked
    }

    // Check for ability unlocks when points update
    checkAbilityUnlocks(pointsData) {
        const unlockedAbilities = [];
        
        Object.entries(pointsData).forEach(([pointType, points]) => {
            const previousAbility = this.agentAbilities.get(pointType);
            const currentAbility = this.getCurrentAbility(pointType, points);
            
            if (currentAbility && (!previousAbility || currentAbility.name !== previousAbility.name)) {
                unlockedAbilities.push({
                    pointType,
                    ability: currentAbility,
                    points
                });
                
                // Dispatch unlock event
                this.dispatchAbilityUnlock(pointType, currentAbility);
            }
            
            this.agentAbilities.set(pointType, currentAbility);
        });

        return unlockedAbilities;
    }

    // Dispatch ability unlock event
    dispatchAbilityUnlock(pointType, ability) {
        const event = new CustomEvent('abilityUnlocked', {
            detail: { pointType, ability }
        });
        document.dispatchEvent(event);
        
        // Show notification
        this.showUnlockNotification(ability);
    }

    // Show unlock notification
    showUnlockNotification(ability) {
        const notification = document.createElement('div');
        notification.className = 'ability-unlock-notification';
        notification.innerHTML = `
            <div class="unlock-icon">✨</div>
            <div class="unlock-content">
                <div class="unlock-title">Ability Unlocked!</div>
                <div class="unlock-name">${ability.name}</div>
                <div class="unlock-multiplier">${ability.multiplier}x Multiplier</div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Remove after animation
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Get agent skill summary
    async getAgentSkillSummary(userId) {
        try {
            // Get all points for user
            const response = await fetch(`${this.baseUrl}/api/points/all?user_id=${userId}`);
            const data = await response.json();
            const points = data.points || {};

            const summary = {
                totalSkillSets: 0,
                totalAbilities: 0,
                unlockedAbilities: [],
                nextUnlocks: [],
                totalMultiplier: 1.0
            };

            // Process each point type
            Object.entries(points).forEach(([pointType, pointValue]) => {
                const skillSet = this.getSkillSet(pointType);
                if (skillSet) {
                    summary.totalSkillSets++;
                    const unlocked = this.getUnlockedAbilities(pointType, pointValue);
                    summary.totalAbilities += unlocked.length;
                    summary.unlockedAbilities.push({
                        pointType,
                        skillSetName: skillSet.name,
                        abilities: unlocked
                    });

                    // Calculate total multiplier (average of all multipliers)
                    const currentAbility = this.getCurrentAbility(pointType, pointValue);
                    if (currentAbility) {
                        summary.totalMultiplier *= currentAbility.multiplier;
                    }

                    // Get next unlock
                    const nextAbility = this.getNextAbility(pointType, pointValue);
                    if (nextAbility) {
                        summary.nextUnlocks.push({
                            pointType,
                            skillSetName: skillSet.name,
                            nextAbility
                        });
                    }
                }
            });

            return summary;
        } catch (error) {
            console.error('Error getting agent skill summary:', error);
            return null;
        }
    }

    // Render skill set display
    renderSkillSetDisplay(containerId, pointType, currentPoints) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const skillSet = this.getSkillSet(pointType);
        if (!skillSet) {
            container.innerHTML = '<p>No skill set available for this point type.</p>';
            return;
        }

        const currentAbility = this.getCurrentAbility(pointType, currentPoints);
        const nextAbility = this.getNextAbility(pointType, currentPoints);
        const unlockedAbilities = this.getUnlockedAbilities(pointType, currentPoints);

        const progress = nextAbility 
            ? ((currentPoints / nextAbility.threshold) * 100).toFixed(1)
            : 100;

        container.innerHTML = `
            <div class="skill-set-card">
                <h3 class="skill-set-name">${skillSet.name}</h3>
                <div class="current-ability">
                    <div class="ability-name">${currentAbility.name}</div>
                    <div class="ability-multiplier">${currentAbility.multiplier}x Multiplier</div>
                </div>
                <div class="ability-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <div class="progress-text">${currentPoints} / ${nextAbility ? nextAbility.threshold : 'MAX'} points</div>
                </div>
                ${nextAbility ? `
                    <div class="next-ability">
                        <div class="next-label">Next: ${nextAbility.name}</div>
                        <div class="next-points">${nextAbility.pointsNeeded} points needed</div>
                    </div>
                ` : '<div class="all-unlocked">All abilities unlocked! 🎉</div>'}
                <div class="abilities-list">
                    <h4>Unlocked Abilities:</h4>
                    ${unlockedAbilities.map(ability => `
                        <div class="ability-item ${ability.name === currentAbility.name ? 'active' : ''}">
                            <span class="ability-check">✓</span>
                            <span class="ability-name">${ability.name}</span>
                            <span class="ability-multiplier">${ability.multiplier}x</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
}

// Initialize agent skill sets
window.agentSkillSets = new AgentSkillSets();

// Listen for ability unlocks
document.addEventListener('abilityUnlocked', (event) => {
    const { pointType, ability } = event.detail;
    console.log(`Ability unlocked: ${ability.name} for ${pointType}`);
});
