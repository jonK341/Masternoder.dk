/**
 * Click-Through Game System
 * Interactive click games with missions, quests, clip stories, and unified point rewards
 */

class ClickThroughGame {
    constructor(userId, baseUrl = '') {
        this.userId = userId || 'default_user';
        this.baseUrl = baseUrl || window.location.origin;
        this.currentLevel = 1;
        this.currentMission = 0;
        this.currentQuest = 0;
        this.clicks = 0;
        this.points = 0;
        this.totalEarned = 0;
        this.energy = 100; // Energy system - max 100
        this.maxEnergy = 100;
        this.energyRegenRate = 0.5; // Energy per second
        this.lastEnergyUpdate = Date.now();
        this.gameState = {
            missionsCompleted: 0,
            questsCompleted: 0,
            clipStoriesViewed: 0,
            achievementsUnlocked: [],
            level: 1,
            totalClicks: 0,
            storyChapter: 0,
            storyProgress: 0,
            energyUsed: 0,
            energyRecovered: 0,
            clickStreak: 0,
            lastClickTime: 0,
            comboCounter: 0,
            criticalHits: 0
        };
        this.missions = [];
        this.quests = [];
        this.clipStories = [];
        this.achievements = [];
        this.story = []; // Complete story system
        this.clickTriggers = []; // Multiple click trigger points
        this.activeEffects = []; // Active visual effects
        this.counters = { // Multiple counter systems
            totalClicks: 0,
            successfulClicks: 0,
            criticalClicks: 0,
            comboCount: 0,
            energySpent: 0,
            energyGained: 0,
            pointsEarned: 0,
            rotations: 0,
            animations: 0
        };
        this.debuggerLoopActive = false;
        this.init();
    }

    async init() {
        await this.loadGameData();
        await this.loadUserProgress();
        this.initializeStory();
        this.initializeClickTriggers();
        this.startEnergyRegeneration();
        this.startDebuggerLoops();
        this.startCounterTickers();
    }
    
    initializeStory() {
        // Complete story system with chapters
        this.story = [
            {
                chapter: 0,
                title: 'The Awakening',
                content: 'You awaken in a realm of endless possibilities. As a Trophy Hunter, your journey begins with a single click. Each action shapes your destiny...',
                reward: 10,
                unlocks: ['basic_click']
            },
            {
                chapter: 1,
                title: 'First Steps',
                content: 'With your first clicks, you discover the power within. Energy flows through you, and you learn that every click consumes energy but grants progress.',
                reward: 25,
                unlocks: ['energy_system', 'point_generation']
            },
            {
                chapter: 2,
                title: 'The Hunt Begins',
                content: 'Your first mission appears. The path of a hunter is filled with challenges, but rewards await those who persevere.',
                reward: 50,
                unlocks: ['missions', 'quests']
            },
            {
                chapter: 3,
                title: 'Power Awakening',
                content: 'You reach level 5! Your skills grow, and you unlock the ability to perform critical hits. Rotations and visual effects become available.',
                reward: 100,
                unlocks: ['critical_hits', 'rotations', 'visual_effects']
            },
            {
                chapter: 4,
                title: 'The Debugger\'s Loop',
                content: 'You discover the mysterious debugger loops - strange energy sources that recover your strength when activated. Use them wisely!',
                reward: 150,
                unlocks: ['debugger_loops', 'energy_recovery']
            },
            {
                chapter: 5,
                title: 'Mastery Path',
                content: 'Level 10 achieved! You master the art of clicking. Multiple trigger points appear, each offering unique rewards and challenges.',
                reward: 250,
                unlocks: ['multiple_triggers', 'advanced_counters']
            },
            {
                chapter: 6,
                title: 'The Convergence',
                content: 'Your energy and skill converge. You unlock powerful combos that multiply your rewards. The counter systems synchronize.',
                reward: 400,
                unlocks: ['combos', 'counter_sync']
            },
            {
                chapter: 7,
                title: 'Legendary Status',
                content: 'Level 20! You become a legend. The story deepens as you unlock legendary abilities and discover hidden click zones.',
                reward: 600,
                unlocks: ['legendary_abilities', 'hidden_zones']
            },
            {
                chapter: 8,
                title: 'Eternal Hunt',
                content: 'Beyond level 30, you transcend normal limits. The story continues indefinitely, with new chapters unlocking as you progress.',
                reward: 1000,
                unlocks: ['transcendence', 'infinite_story']
            }
        ];
    }
    
    initializeClickTriggers() {
        // Multiple click trigger points
        this.clickTriggers = [
            { id: 'main', name: 'Main Click', multiplier: 1.0, energyCost: 1, unlockLevel: 0 },
            { id: 'power', name: 'Power Click', multiplier: 1.5, energyCost: 2, unlockLevel: 3 },
            { id: 'critical', name: 'Critical Click', multiplier: 2.5, energyCost: 5, unlockLevel: 5, criticalChance: 0.15 },
            { id: 'combo', name: 'Combo Click', multiplier: 3.0, energyCost: 8, unlockLevel: 10, requiresCombo: true },
            { id: 'legendary', name: 'Legendary Click', multiplier: 5.0, energyCost: 15, unlockLevel: 20, criticalChance: 0.30 },
            { id: 'debugger', name: 'Debugger Click', multiplier: 10.0, energyCost: 0, unlockLevel: 4, special: 'energy_recovery' },
            { id: 'rotation', name: 'Rotation Click', multiplier: 1.8, energyCost: 3, unlockLevel: 7, effect: 'rotation' },
            { id: 'energy_boost', name: 'Energy Boost', multiplier: 1.2, energyCost: 0, unlockLevel: 6, effect: 'energy_boost' }
        ];
    }
    
    startEnergyRegeneration() {
        // Energy regeneration loop
        setInterval(() => {
            if (this.energy < this.maxEnergy) {
                const now = Date.now();
                const delta = (now - this.lastEnergyUpdate) / 1000; // seconds
                this.energy = Math.min(this.maxEnergy, this.energy + (this.energyRegenRate * delta));
                this.lastEnergyUpdate = now;
                this.updateEnergyDisplay();
            }
        }, 100); // Check every 100ms
    }
    
    startDebuggerLoops() {
        // Critical debugger loops for energy recovery
        setInterval(() => {
            if (this.debuggerLoopActive) {
                // Debugger loop active - recover energy faster
                if (this.energy < this.maxEnergy) {
                    const recovery = 2.0; // 2 energy per second during debugger loop
                    this.energy = Math.min(this.maxEnergy, this.energy + recovery);
                    this.gameState.energyRecovered += recovery;
                    this.counters.energyGained += recovery;
                    this.updateEnergyDisplay();
                }
            }
        }, 1000);
        
        // Randomly activate debugger loops
        setInterval(() => {
            if (Math.random() < 0.05 && this.currentLevel >= 4) { // 5% chance every interval
                this.activateDebuggerLoop();
            }
        }, 30000); // Check every 30 seconds
    }
    
    startCounterTickers() {
        // Multiple counter tickers that increment over time
        setInterval(() => {
            // Passive point generation (very slow)
            if (this.currentLevel >= 5) {
                const passivePoints = Math.floor(this.currentLevel * 0.1);
                this.points += passivePoints;
                this.counters.pointsEarned += passivePoints;
            }
        }, 5000); // Every 5 seconds
        
        // Combo decay
        setInterval(() => {
            const now = Date.now();
            if (this.gameState.clickStreak > 0 && (now - this.gameState.lastClickTime) > 3000) {
                // Decay combo if no clicks for 3 seconds
                this.gameState.clickStreak = Math.max(0, this.gameState.clickStreak - 1);
                this.gameState.comboCounter = 0;
            }
        }, 1000);
    }
    
    activateDebuggerLoop() {
        if (this.debuggerLoopActive) return;
        
        this.debuggerLoopActive = true;
        this.showNotification('🔧 Debugger Loop Activated! Energy recovery boosted!', 'debugger');
        
        // Debugger loop lasts 15 seconds
        setTimeout(() => {
            this.debuggerLoopActive = false;
            this.showNotification('Debugger Loop Deactivated', 'info');
        }, 15000);
    }
    
    updateEnergyDisplay() {
        // Update energy display in UI
        const energyEl = document.getElementById('click-game-energy');
        if (energyEl) {
            energyEl.textContent = `Energy: ${Math.floor(this.energy)}/${this.maxEnergy}`;
            energyEl.style.width = `${(this.energy / this.maxEnergy) * 100}%`;
            
            // Color based on energy level
            if (this.energy < 20) {
                energyEl.style.backgroundColor = '#ff4444';
            } else if (this.energy < 50) {
                energyEl.style.backgroundColor = '#ffaa00';
            } else {
                energyEl.style.backgroundColor = '#00ff88';
            }
        }
    }

    async loadGameData() {
        try {
            // Load missions
            const missionsRes = await fetch(`${this.baseUrl}/api/game/missions?user_id=${this.userId}`);
            const missionsData = await missionsRes.json();
            if (missionsData.success) {
                this.missions = missionsData.missions || this.getDefaultMissions();
            } else {
                this.missions = this.getDefaultMissions();
            }

            // Load quests
            const questsRes = await fetch(`${this.baseUrl}/api/game-mechanics/quests?user_id=${this.userId}`);
            const questsData = await questsRes.json();
            if (questsData.success) {
                this.quests = questsData.quests || this.getDefaultQuests();
            } else {
                this.quests = this.getDefaultQuests();
            }

            // Load clip stories
            this.clipStories = this.getDefaultClipStories();

            // Load achievements
            this.achievements = this.getDefaultAchievements();
        } catch (error) {
            console.error('Error loading game data:', error);
            // Use defaults
            this.missions = this.getDefaultMissions();
            this.quests = this.getDefaultQuests();
            this.clipStories = this.getDefaultClipStories();
            this.achievements = this.getDefaultAchievements();
        }
    }

    async loadUserProgress() {
        try {
            const res = await fetch(`${this.baseUrl}/api/game/click-game/progress?user_id=${this.userId}`);
            const data = await res.json();
            if (data.success && data.progress) {
                this.gameState = { ...this.gameState, ...data.progress };
                this.currentLevel = data.progress.level || 1;
                this.currentMission = data.progress.currentMission || 0;
                this.currentQuest = data.progress.currentQuest || 0;
                this.clicks = data.progress.totalClicks || 0;
                this.points = data.progress.totalEarned || 0;
            }
        } catch (error) {
            console.error('Error loading user progress:', error);
        }
    }

    async saveProgress() {
        try {
            await fetch(`${this.baseUrl}/api/game/click-game/save-progress`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    progress: {
                        ...this.gameState,
                        level: this.currentLevel,
                        currentMission: this.currentMission,
                        currentQuest: this.currentQuest,
                        totalClicks: this.clicks,
                        totalEarned: this.points
                    }
                })
            });
        } catch (error) {
            console.error('Error saving progress:', error);
        }
    }

    async handleClick(triggerId = 'main', position = null) {
        // Get trigger info
        const trigger = this.clickTriggers.find(t => t.id === triggerId) || this.clickTriggers[0];
        
        // Check if trigger is unlocked
        if (this.currentLevel < trigger.unlockLevel) {
            this.showNotification(`Trigger "${trigger.name}" requires level ${trigger.unlockLevel}`, 'warning');
            return 0;
        }
        
        // Check energy
        if (this.energy < trigger.energyCost) {
            this.showNotification('Not enough energy! Wait for regeneration or activate debugger loop.', 'warning');
            return 0;
        }
        
        // Consume energy
        this.energy = Math.max(0, this.energy - trigger.energyCost);
        this.gameState.energyUsed += trigger.energyCost;
        this.counters.energySpent += trigger.energyCost;
        this.updateEnergyDisplay();
        
        // Update click counters
        this.clicks++;
        this.gameState.totalClicks = this.clicks;
        this.counters.totalClicks++;
        this.counters.successfulClicks++;
        
        // Combo system
        const now = Date.now();
        if (now - this.gameState.lastClickTime < 1000) { // Within 1 second
            this.gameState.clickStreak++;
            this.gameState.comboCounter++;
        } else {
            this.gameState.clickStreak = 1;
            this.gameState.comboCounter = 1;
        }
        this.gameState.lastClickTime = now;
        this.counters.comboCount = this.gameState.comboCounter;
        
        // Calculate points with multipliers
        const basePoints = 1;
        const levelMultiplier = 1 + (this.currentLevel - 1) * 0.1;
        const triggerMultiplier = trigger.multiplier || 1.0;
        const comboMultiplier = 1 + (this.gameState.comboCounter * 0.1); // +10% per combo
        const streakMultiplier = 1 + (this.gameState.clickStreak * 0.05); // +5% per streak
        const debuggerMultiplier = this.debuggerLoopActive ? 1.5 : 1.0;
        
        // Critical hit chance
        let criticalHit = false;
        if (trigger.criticalChance) {
            criticalHit = Math.random() < trigger.criticalChance;
            if (criticalHit) {
                this.gameState.criticalHits++;
                this.counters.criticalClicks++;
            }
        }
        const criticalMultiplier = criticalHit ? 3.0 : 1.0;
        
        const pointsEarned = Math.floor(
            basePoints * 
            levelMultiplier * 
            triggerMultiplier * 
            comboMultiplier * 
            streakMultiplier * 
            debuggerMultiplier * 
            criticalMultiplier
        );
        
        this.points += pointsEarned;
        this.totalEarned += pointsEarned;
        this.counters.pointsEarned += pointsEarned;
        
        // Award unified points
        await this.awardUnifiedPoints('click', pointsEarned, {
            trigger: triggerId,
            combo: this.gameState.comboCounter,
            streak: this.gameState.clickStreak,
            critical: criticalHit,
            energyUsed: trigger.energyCost
        });

        // Visual effects
        this.createClickEffect(position || { x: window.innerWidth / 2, y: window.innerHeight / 2 }, {
            points: pointsEarned,
            critical: criticalHit,
            combo: this.gameState.comboCounter,
            rotation: trigger.effect === 'rotation'
        });

        // Apply trigger effects
        if (trigger.effect === 'rotation') {
            this.applyRotationEffect();
            this.counters.rotations++;
        }
        if (trigger.effect === 'energy_boost') {
            this.energy = Math.min(this.maxEnergy, this.energy + 10);
            this.updateEnergyDisplay();
        }
        if (trigger.special === 'energy_recovery') {
            this.activateDebuggerLoop();
        }

        // Check missions
        await this.checkMissions();

        // Check quests
        await this.checkQuests();

        // Check achievements
        await this.checkAchievements();

        // Check level up
        await this.checkLevelUp();
        
        // Check story progression
        await this.checkStoryProgression();

        // Save progress
        await this.saveProgress();

        return { points: pointsEarned, critical: criticalHit, combo: this.gameState.comboCounter };
    }
    
    createClickEffect(position, data) {
        // Create visual click effect
        const effect = document.createElement('div');
        effect.className = 'click-effect';
        effect.style.cssText = `
            position: fixed;
            left: ${position.x}px;
            top: ${position.y}px;
            pointer-events: none;
            z-index: 9999;
            font-size: ${data.critical ? '28px' : '20px'};
            font-weight: bold;
            color: ${data.critical ? '#ff00ff' : '#00ff88'};
            text-shadow: 0 0 10px ${data.critical ? '#ff00ff' : '#00ff88'};
            transform: translate(-50%, -50%);
            animation: clickPulse 1s ease-out forwards;
            ${data.rotation ? 'animation: clickRotate 1s ease-out forwards;' : ''}
        `;
        
        let text = `+${data.points}`;
        if (data.critical) {
            text = '💥 CRITICAL! ' + text;
        }
        if (data.combo > 1) {
            text += ` (${data.combo}x Combo!)`;
        }
        effect.textContent = text;
        
        document.body.appendChild(effect);
        this.counters.animations++;
        
        // Add particle effect
        this.createParticles(position, data.critical ? 15 : 8);
        
        // Remove after animation
        setTimeout(() => {
            effect.remove();
        }, 1000);
    }
    
    createParticles(position, count) {
        // Create particle explosion effect
        for (let i = 0; i < count; i++) {
            const particle = document.createElement('div');
            particle.className = 'click-particle';
            const angle = (Math.PI * 2 * i) / count;
            const distance = 50 + Math.random() * 50;
            const x = position.x + Math.cos(angle) * distance;
            const y = position.y + Math.sin(angle) * distance;
            
            particle.style.cssText = `
                position: fixed;
                left: ${position.x}px;
                top: ${position.y}px;
                width: 6px;
                height: 6px;
                background: ${['#00ff88', '#0088ff', '#ff0088', '#ffaa00'][i % 4]};
                border-radius: 50%;
                pointer-events: none;
                z-index: 9998;
                animation: particleExplode 0.8s ease-out forwards;
                --target-x: ${x}px;
                --target-y: ${y}px;
            `;
            
            document.body.appendChild(particle);
            setTimeout(() => particle.remove(), 800);
        }
    }
    
    applyRotationEffect() {
        // Apply rotation effect to clickable elements
        const clickButtons = document.querySelectorAll('.click-trigger, .click-game-button');
        clickButtons.forEach(btn => {
            btn.style.transition = 'transform 0.3s ease';
            btn.style.transform = 'rotate(360deg) scale(1.1)';
            setTimeout(() => {
                btn.style.transform = 'rotate(0deg) scale(1)';
            }, 300);
        });
    }
    
    async checkStoryProgression() {
        // Check if story should advance
        const currentStory = this.story[this.gameState.storyChapter];
        if (!currentStory) return;
        
        let shouldAdvance = false;
        
        switch (this.gameState.storyChapter) {
            case 0:
                shouldAdvance = this.clicks >= 1;
                break;
            case 1:
                shouldAdvance = this.clicks >= 10;
                break;
            case 2:
                shouldAdvance = this.gameState.missionsCompleted >= 1;
                break;
            case 3:
                shouldAdvance = this.currentLevel >= 5;
                break;
            case 4:
                shouldAdvance = this.gameState.energyRecovered >= 50;
                break;
            case 5:
                shouldAdvance = this.currentLevel >= 10;
                break;
            case 6:
                shouldAdvance = this.gameState.comboCounter >= 10;
                break;
            case 7:
                shouldAdvance = this.currentLevel >= 20;
                break;
            case 8:
                shouldAdvance = this.currentLevel >= 30;
                break;
        }
        
        if (shouldAdvance && this.gameState.storyChapter < this.story.length - 1) {
            this.gameState.storyChapter++;
            this.gameState.storyProgress++;
            
            const storyChapter = this.story[this.gameState.storyChapter];
            const reward = storyChapter.reward * this.currentLevel;
            
            this.points += reward;
            this.totalEarned += reward;
            this.counters.pointsEarned += reward;
            
            await this.awardUnifiedPoints('story_chapter', reward);
            
            this.showNotification(`📖 Chapter ${this.gameState.storyChapter + 1}: ${storyChapter.title}! +${reward} points`, 'story');
            
            // Unlock features
            if (storyChapter.unlocks) {
                storyChapter.unlocks.forEach(unlock => {
                    this.showNotification(`🔓 Unlocked: ${unlock.replace(/_/g, ' ')}`, 'unlock');
                });
            }
        }
    }
    
    getStoryChapter() {
        return this.story[this.gameState.storyChapter] || this.story[0];
    }
    
    getAvailableTriggers() {
        return this.clickTriggers.filter(t => this.currentLevel >= t.unlockLevel);
    }

    async awardUnifiedPoints(action, amount, metadata = {}) {
        try {
            await fetch(`${this.baseUrl}/api/game-mechanics/award-points`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    action: action,
                    difficulty: metadata.critical ? 'extreme' : (metadata.combo > 5 ? 'hard' : 'normal'),
                    multiplier: amount,
                    metadata: {
                        source: 'click_through_game',
                        level: this.currentLevel,
                        clicks: this.clicks,
                        energy: this.energy,
                        ...metadata
                    }
                })
            });

            // Also award directly via points API with multiple categories
            const pointsData = {
                click_game_points: amount,
                activity_points: Math.floor(amount * 0.5),
                xp: Math.floor(amount * 0.3),
                game_points: Math.floor(amount * 0.4),
                progression_points: Math.floor(amount * 0.2)
            };
            
            // Bonus categories for special actions
            if (metadata.critical) {
                pointsData.critical_points = Math.floor(amount * 0.5);
                pointsData.combat_points = Math.floor(amount * 0.3);
            }
            if (metadata.combo > 1) {
                pointsData.combo_points = Math.floor(amount * metadata.combo * 0.1);
            }
            if (metadata.trigger === 'debugger') {
                pointsData.energy_points = Math.floor(amount * 0.6);
                pointsData.skill_points = Math.floor(amount * 0.4);
            }
            
            await fetch(`${this.baseUrl}/api/points/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.userId,
                    points: pointsData
                })
            });
        } catch (error) {
            console.error('Error awarding unified points:', error);
        }
    }

    async checkMissions() {
        const currentMission = this.missions[this.currentMission];
        if (!currentMission) return;

        if (this.clicks >= currentMission.target) {
            // Mission completed
            this.gameState.missionsCompleted++;
            
            const reward = currentMission.reward * this.currentLevel;
            this.points += reward;
            this.totalEarned += reward;

            await this.awardUnifiedPoints('mission_complete', reward);

            // Show notification
            this.showNotification(`Mission Complete: ${currentMission.name}! +${reward} points`, 'success');

            // Move to next mission
            this.currentMission++;
            if (this.currentMission >= this.missions.length) {
                // All missions complete, add new ones
                this.addNewMissions();
            }

            await this.saveProgress();
        }
    }

    async checkQuests() {
        const currentQuest = this.quests[this.currentQuest];
        if (!currentQuest) return;

        if (this.clicks >= currentQuest.target) {
            // Quest completed
            this.gameState.questsCompleted++;
            
            const reward = currentQuest.reward * this.currentLevel;
            this.points += reward;
            this.totalEarned += reward;

            await this.awardUnifiedPoints('quest_complete', reward);

            this.showNotification(`Quest Complete: ${currentQuest.name}! +${reward} points`, 'success');

            this.currentQuest++;
            if (this.currentQuest >= this.quests.length) {
                this.addNewQuests();
            }

            await this.saveProgress();
        }
    }

    async checkAchievements() {
        for (const achievement of this.achievements) {
            if (this.gameState.achievementsUnlocked.includes(achievement.id)) continue;

            let unlocked = false;
            switch (achievement.type) {
                case 'clicks':
                    unlocked = this.clicks >= achievement.target;
                    break;
                case 'level':
                    unlocked = this.currentLevel >= achievement.target;
                    break;
                case 'missions':
                    unlocked = this.gameState.missionsCompleted >= achievement.target;
                    break;
                case 'quests':
                    unlocked = this.gameState.questsCompleted >= achievement.target;
                    break;
                case 'stories':
                    unlocked = this.gameState.clipStoriesViewed >= achievement.target;
                    break;
                case 'achievements':
                    unlocked = this.gameState.achievementsUnlocked.length >= achievement.target;
                    break;
                case 'special':
                    // Special conditions (e.g., level 20 with 10000 clicks)
                    if (achievement.id === 36) {
                        unlocked = this.currentLevel >= 20 && this.clicks >= 10000;
                    }
                    break;
                case 'speed':
                    // Speed run achievements - would need session tracking
                    unlocked = false; // Implement session tracking for speed runs
                    break;
                case 'days':
                    // Daily login achievements - would need date tracking
                    unlocked = false; // Implement date tracking
                    break;
            }

            if (unlocked) {
                this.gameState.achievementsUnlocked.push(achievement.id);
                
                // Enhanced rewards with level multiplier and rarity bonus
                const baseReward = achievement.reward;
                const levelMultiplier = 1 + (this.currentLevel * 0.02); // +2% per level
                const rarityBonus = this.getRarityBonus(achievement.rarity);
                const reward = Math.floor(baseReward * levelMultiplier * rarityBonus);
                
                this.points += reward;
                this.totalEarned += reward;

                await this.awardUnifiedPoints('achievement_unlock', reward);

                // Extra bonus for legendary+ achievements
                if (['legendary', 'mythic', 'divine'].includes(achievement.rarity)) {
                    const extraBonus = Math.floor(reward * 0.5);
                    this.points += extraBonus;
                    this.totalEarned += extraBonus;
                    await this.awardUnifiedPoints('achievement_bonus', extraBonus);
                }

                this.showNotification(`Achievement Unlocked: ${achievement.name}! +${reward} points`, 'achievement');
            }
        }
    }

    getRarityBonus(rarity) {
        const bonuses = {
            'common': 1.0,
            'uncommon': 1.2,
            'rare': 1.5,
            'legendary': 2.0,
            'mythic': 3.0,
            'divine': 5.0
        };
        return bonuses[rarity] || 1.0;
    }

    async checkLevelUp() {
        // Dynamic level requirements - increases with level
        const baseClicksPerLevel = 100;
        const levelMultiplier = 1 + (this.currentLevel * 0.05); // +5% per level
        const clicksNeeded = Math.floor(baseClicksPerLevel * levelMultiplier);
        const totalClicksNeeded = this.calculateTotalClicksForLevel(this.currentLevel + 1);
        
        if (this.clicks >= totalClicksNeeded && this.clicks >= clicksNeeded) {
            const oldLevel = this.currentLevel;
            this.currentLevel++;
            this.gameState.level = this.currentLevel;

            // Extra reward points - increases with level
            const baseReward = 50;
            const levelBonus = this.currentLevel * 10;
            const streakBonus = this.gameState.missionsCompleted > 0 ? this.gameState.missionsCompleted * 5 : 0;
            const levelUpReward = baseReward + levelBonus + streakBonus;
            
            this.points += levelUpReward;
            this.totalEarned += levelUpReward;

            await this.awardUnifiedPoints('level_up', levelUpReward);

            // Level milestone bonuses
            if (this.currentLevel % 5 === 0) {
                const milestoneBonus = this.currentLevel * 100;
                this.points += milestoneBonus;
                this.totalEarned += milestoneBonus;
                await this.awardUnifiedPoints('level_milestone', milestoneBonus);
                this.showNotification(`🎉 Level ${this.currentLevel} Milestone! +${milestoneBonus} bonus points!`, 'level-up');
            }

            this.showNotification(`Level Up! You reached level ${this.currentLevel}! +${levelUpReward} points`, 'level-up');
            await this.saveProgress();
        }
    }

    calculateTotalClicksForLevel(targetLevel) {
        let total = 0;
        for (let i = 1; i < targetLevel; i++) {
            const multiplier = 1 + (i * 0.05);
            total += Math.floor(100 * multiplier);
        }
        return total;
    }

    getCurrentMission() {
        return this.missions[this.currentMission] || null;
    }

    getCurrentQuest() {
        return this.quests[this.currentQuest] || null;
    }

    getNextClipStory() {
        const storyIndex = this.gameState.clipStoriesViewed % this.clipStories.length;
        return this.clipStories[storyIndex];
    }

    async viewClipStory() {
        const story = this.getNextClipStory();
        if (!story) return null;

        this.gameState.clipStoriesViewed++;
        
        const reward = story.reward * this.currentLevel;
        this.points += reward;
        this.totalEarned += reward;

        await this.awardUnifiedPoints('clip_story_view', reward);

        await this.saveProgress();

        return { story, reward };
    }

    getDefaultMissions() {
        return [
            { id: 1, name: 'First Steps', description: 'Reach 10 clicks', target: 10, reward: 50, icon: '🚀' },
            { id: 2, name: 'Click Master', description: 'Reach 50 clicks', target: 50, reward: 100, icon: '👆' },
            { id: 3, name: 'Hundred Club', description: 'Reach 100 clicks', target: 100, reward: 200, icon: '💯' },
            { id: 4, name: 'Five Hundred', description: 'Reach 500 clicks', target: 500, reward: 500, icon: '🔥' },
            { id: 5, name: 'Thousand Clicks', description: 'Reach 1000 clicks', target: 1000, reward: 1000, icon: '🌟' },
            { id: 6, name: 'Ten Thousand', description: 'Reach 10000 clicks', target: 10000, reward: 5000, icon: '⭐' },
        ];
    }

    getDefaultQuests() {
        return [
            { id: 1, name: 'Daily Clicker', description: 'Click 20 times today', target: 20, reward: 100, icon: '📅' },
            { id: 2, name: 'Speed Demon', description: 'Click 100 times quickly', target: 100, reward: 200, icon: '⚡' },
            { id: 3, name: 'Persistent Hunter', description: 'Complete 5 missions', target: 5, reward: 300, icon: '🎯' },
            { id: 4, name: 'Story Explorer', description: 'View 3 clip stories', target: 3, reward: 250, icon: '📖' },
            { id: 5, name: 'Level Seeker', description: 'Reach level 5', target: 5, reward: 500, icon: '📈' },
        ];
    }

    getDefaultClipStories() {
        return [
            { id: 1, title: 'The Beginning', content: 'You start your journey as a Trophy Hunter. The path ahead is long, but every click brings you closer to greatness...', reward: 50, icon: '🎬' },
            { id: 2, title: 'First Victory', content: 'Your first trophy is earned! The feeling of accomplishment fills you with determination to continue...', reward: 75, icon: '🏆' },
            { id: 3, title: 'Rising Power', content: 'Your skills grow with each click. You feel yourself becoming stronger, faster, more precise...', reward: 100, icon: '⚡' },
            { id: 4, title: 'Mission Accomplished', content: 'You complete your first mission! The rewards are great, and your reputation spreads...', reward: 125, icon: '🎯' },
            { id: 5, title: 'Quest Master', content: 'You have mastered the art of questing. Every challenge you face only makes you stronger...', reward: 150, icon: '📜' },
            { id: 6, title: 'Legendary Status', content: 'You become a legend among hunters. Your name is whispered in awe throughout the land...', reward: 200, icon: '👑' },
            { id: 7, title: 'Master Hunter', content: 'You master the art of trophy hunting. No challenge is too great for you now...', reward: 250, icon: '🌟' },
            { id: 8, title: 'The Grand Collection', content: 'Your trophy collection grows legendary. Each piece tells a story of your journey...', reward: 300, icon: '💎' },
            { id: 9, title: 'Eternal Champion', content: 'You have achieved what few thought possible. You are truly an eternal champion...', reward: 400, icon: '✨' },
            { id: 10, title: 'Beyond Limits', content: 'You have transcended all limits. There is nothing left to prove, only glory to maintain...', reward: 500, icon: '🏅' },
        ];
    }

    getDefaultAchievements() {
        return [
            // Click Achievements
            { id: 1, name: 'Click Starter', description: 'Reach 10 clicks', type: 'clicks', target: 10, reward: 50, icon: '🎯', rarity: 'common' },
            { id: 2, name: 'Fifty Club', description: 'Reach 50 clicks', type: 'clicks', target: 50, reward: 100, icon: '👆', rarity: 'common' },
            { id: 3, name: 'Hundred Hero', description: 'Reach 100 clicks', type: 'clicks', target: 100, reward: 200, icon: '💯', rarity: 'common' },
            { id: 4, name: 'Five Hundred', description: 'Reach 500 clicks', type: 'clicks', target: 500, reward: 350, icon: '🔥', rarity: 'uncommon' },
            { id: 5, name: 'Thousand Master', description: 'Reach 1000 clicks', type: 'clicks', target: 1000, reward: 500, icon: '🌟', rarity: 'rare' },
            { id: 6, name: 'Five Thousand', description: 'Reach 5000 clicks', type: 'clicks', target: 5000, reward: 1000, icon: '⚡', rarity: 'rare' },
            { id: 7, name: 'Click Legend', description: 'Reach 10000 clicks', type: 'clicks', target: 10000, reward: 2000, icon: '👑', rarity: 'legendary' },
            { id: 8, name: 'Mega Clicker', description: 'Reach 25000 clicks', type: 'clicks', target: 25000, reward: 5000, icon: '💎', rarity: 'legendary' },
            { id: 9, name: 'Ultimate Clicker', description: 'Reach 50000 clicks', type: 'clicks', target: 50000, reward: 10000, icon: '🏆', rarity: 'mythic' },
            { id: 10, name: 'God Clicker', description: 'Reach 100000 clicks', type: 'clicks', target: 100000, reward: 25000, icon: '✨', rarity: 'mythic' },
            
            // Level Achievements
            { id: 11, name: 'Level 3 Rookie', description: 'Reach level 3', type: 'level', target: 3, reward: 150, icon: '⭐', rarity: 'common' },
            { id: 12, name: 'Level 5 Veteran', description: 'Reach level 5', type: 'level', target: 5, reward: 300, icon: '🌟', rarity: 'uncommon' },
            { id: 13, name: 'Level 10 Elite', description: 'Reach level 10', type: 'level', target: 10, reward: 600, icon: '💫', rarity: 'rare' },
            { id: 14, name: 'Level 15 Expert', description: 'Reach level 15', type: 'level', target: 15, reward: 900, icon: '🎖️', rarity: 'rare' },
            { id: 15, name: 'Level 20 Master', description: 'Reach level 20', type: 'level', target: 20, reward: 1500, icon: '👑', rarity: 'legendary' },
            { id: 16, name: 'Level 25 Champion', description: 'Reach level 25', type: 'level', target: 25, reward: 2500, icon: '💎', rarity: 'legendary' },
            { id: 17, name: 'Level 30 Grandmaster', description: 'Reach level 30', type: 'level', target: 30, reward: 4000, icon: '🏅', rarity: 'legendary' },
            { id: 18, name: 'Level 40 Legend', description: 'Reach level 40', type: 'level', target: 40, reward: 6000, icon: '⚡', rarity: 'mythic' },
            { id: 19, name: 'Level 50 Mythic', description: 'Reach level 50', type: 'level', target: 50, reward: 10000, icon: '🔥', rarity: 'mythic' },
            { id: 20, name: 'Level 100 Divine', description: 'Reach level 100', type: 'level', target: 100, reward: 25000, icon: '✨', rarity: 'divine' },
            
            // Mission Achievements
            { id: 21, name: 'Mission Complete', description: 'Complete 1 mission', type: 'missions', target: 1, reward: 100, icon: '✅', rarity: 'common' },
            { id: 22, name: 'Mission Expert', description: 'Complete 5 missions', type: 'missions', target: 5, reward: 300, icon: '🎯', rarity: 'uncommon' },
            { id: 23, name: 'Mission Master', description: 'Complete 10 missions', type: 'missions', target: 10, reward: 600, icon: '🎖️', rarity: 'rare' },
            { id: 24, name: 'Mission Legend', description: 'Complete 25 missions', type: 'missions', target: 25, reward: 1500, icon: '👑', rarity: 'legendary' },
            { id: 25, name: 'Mission God', description: 'Complete 50 missions', type: 'missions', target: 50, reward: 3000, icon: '💎', rarity: 'mythic' },
            
            // Quest Achievements
            { id: 26, name: 'Quest Novice', description: 'Complete 1 quest', type: 'quests', target: 1, reward: 80, icon: '📜', rarity: 'common' },
            { id: 27, name: 'Quest Champion', description: 'Complete 5 quests', type: 'quests', target: 5, reward: 350, icon: '🏅', rarity: 'uncommon' },
            { id: 28, name: 'Quest Hero', description: 'Complete 10 quests', type: 'quests', target: 10, reward: 700, icon: '⭐', rarity: 'rare' },
            { id: 29, name: 'Quest Master', description: 'Complete 20 quests', type: 'quests', target: 20, reward: 1500, icon: '🌟', rarity: 'legendary' },
            { id: 30, name: 'Quest Legend', description: 'Complete 50 quests', type: 'quests', target: 50, reward: 3500, icon: '👑', rarity: 'mythic' },
            
            // Story Achievements
            { id: 31, name: 'Story Explorer', description: 'View 1 clip story', type: 'stories', target: 1, reward: 60, icon: '📖', rarity: 'common' },
            { id: 32, name: 'Story Teller', description: 'View 5 clip stories', type: 'stories', target: 5, reward: 300, icon: '📚', rarity: 'uncommon' },
            { id: 33, name: 'Story Master', description: 'View 10 clip stories', type: 'stories', target: 10, reward: 600, icon: '🎬', rarity: 'rare' },
            { id: 34, name: 'Story Legend', description: 'View 25 clip stories', type: 'stories', target: 25, reward: 1500, icon: '🎭', rarity: 'legendary' },
            { id: 35, name: 'Story God', description: 'View 50 clip stories', type: 'stories', target: 50, reward: 3000, icon: '✨', rarity: 'mythic' },
            
            // Special Achievements
            { id: 36, name: 'Perfect Hunter', description: 'Reach level 20 with 10000 clicks', type: 'special', target: 0, reward: 2500, icon: '🎯', rarity: 'legendary' },
            { id: 37, name: 'Trophy Collector', description: 'Unlock 20 achievements', type: 'achievements', target: 20, reward: 2000, icon: '🏆', rarity: 'legendary' },
            { id: 38, name: 'Completionist', description: 'Unlock 50 achievements', type: 'achievements', target: 50, reward: 5000, icon: '💎', rarity: 'mythic' },
            { id: 39, name: 'Speed Runner', description: 'Reach level 10 in one session', type: 'speed', target: 10, reward: 1500, icon: '⚡', rarity: 'rare' },
            { id: 40, name: 'Dedicated Player', description: 'Play for 100 days', type: 'days', target: 100, reward: 3000, icon: '📅', rarity: 'legendary' },
        ];
    }

    addNewMissions() {
        const missionCount = this.missions.length + 1;
        const missionsToAdd = 3; // Add 3 missions at a time
        
        for (let i = 0; i < missionsToAdd; i++) {
            const missionNum = missionCount + i;
            const target = missionNum * 1000;
            const reward = missionNum * 100 + (i * 50); // Extra rewards
            
            this.missions.push({
                id: missionNum,
                name: this.getMissionName(missionNum),
                description: `Reach ${target.toLocaleString()} clicks`,
                target: target,
                reward: reward,
                icon: this.getMissionIcon(missionNum)
            });
        }
    }

    addNewQuests() {
        const questCount = this.quests.length + 1;
        const questsToAdd = 3; // Add 3 quests at a time
        
        for (let i = 0; i < questsToAdd; i++) {
            const questNum = questCount + i;
            const target = questNum * 50;
            const reward = questNum * 50 + (i * 25); // Extra rewards
            
            this.quests.push({
                id: questNum,
                name: this.getQuestName(questNum),
                description: this.getQuestDescription(questNum, target),
                target: target,
                reward: reward,
                icon: this.getQuestIcon(questNum)
            });
        }
    }

    getMissionName(num) {
        const names = [
            'Elite Hunter', 'Grand Master', 'Supreme Quest', 'Ultimate Challenge',
            'Mega Mission', 'Epic Journey', 'Legendary Task', 'Divine Objective'
        ];
        return names[(num - 1) % names.length] + ` ${num}`;
    }

    getMissionIcon(num) {
        const icons = ['🎯', '⚡', '🔥', '🌟', '👑', '💎', '✨', '🏆'];
        return icons[(num - 1) % icons.length];
    }

    getQuestName(num) {
        const names = [
            'Daily Challenge', 'Weekly Goal', 'Monthly Quest', 'Seasonal Objective',
            'Special Assignment', 'Bonus Task', 'Extra Mission', 'Ultimate Quest'
        ];
        return names[(num - 1) % names.length] + ` ${num}`;
    }

    getQuestIcon(num) {
        const icons = ['📜', '📋', '🎯', '⭐', '🌟', '💫', '🎖️', '🏅'];
        return icons[(num - 1) % icons.length];
    }

    getQuestDescription(num, target) {
        const descriptions = [
            `Click ${target} times`,
            `Earn ${target * 2} points`,
            `Complete ${Math.floor(target / 100)} levels`,
            `Finish ${Math.floor(target / 50)} missions`
        ];
        return descriptions[(num - 1) % descriptions.length];
    }

    showNotification(message, type = 'info') {
        if (window.gameNotifications && window.gameNotifications.showNotification) {
            window.gameNotifications.showNotification(message, type, { points: this.points });
        } else {
            // Fallback notification
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    getStats() {
        return {
            level: this.currentLevel,
            clicks: this.clicks,
            points: this.points,
            totalEarned: this.totalEarned,
            energy: this.energy,
            maxEnergy: this.maxEnergy,
            missionsCompleted: this.gameState.missionsCompleted,
            questsCompleted: this.gameState.questsCompleted,
            clipStoriesViewed: this.gameState.clipStoriesViewed,
            achievementsUnlocked: this.gameState.achievementsUnlocked.length,
            currentMission: this.getCurrentMission(),
            currentQuest: this.getCurrentQuest(),
            storyChapter: this.gameState.storyChapter,
            storyProgress: this.gameState.storyProgress,
            clickStreak: this.gameState.clickStreak,
            comboCounter: this.gameState.comboCounter,
            criticalHits: this.gameState.criticalHits,
            counters: this.counters,
            debuggerActive: this.debuggerLoopActive
        };
    }
    
    getCounters() {
        return this.counters;
    }
    
    getStory() {
        return {
            currentChapter: this.story[this.gameState.storyChapter],
            chapterNumber: this.gameState.storyChapter + 1,
            totalChapters: this.story.length,
            progress: this.gameState.storyProgress
        };
    }
}

// Add CSS for click effects
if (!document.getElementById('click-game-styles')) {
    const style = document.createElement('style');
    style.id = 'click-game-styles';
    style.textContent = `
        @keyframes clickPulse {
            0% {
                transform: translate(-50%, -50%) scale(0.5);
                opacity: 1;
            }
            100% {
                transform: translate(-50%, -100%) scale(1.2);
                opacity: 0;
            }
        }
        
        @keyframes clickRotate {
            0% {
                transform: translate(-50%, -50%) rotate(0deg) scale(0.8);
                opacity: 1;
            }
            50% {
                transform: translate(-50%, -50%) rotate(180deg) scale(1.2);
                opacity: 0.8;
            }
            100% {
                transform: translate(-50%, -100%) rotate(360deg) scale(1.5);
                opacity: 0;
            }
        }
        
        @keyframes particleExplode {
            0% {
                transform: translate(0, 0) scale(1);
                opacity: 1;
            }
            100% {
                transform: translate(calc(var(--target-x) - 50%), calc(var(--target-y) - 50%)) scale(0);
                opacity: 0;
            }
        }
        
        .click-effect {
            animation: clickPulse 1s ease-out forwards;
        }
        
        .click-particle {
            animation: particleExplode 0.8s ease-out forwards;
        }
        
        .click-trigger-button {
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }
        
        .click-trigger-button:hover {
            transform: scale(1.05) rotate(5deg);
        }
        
        .click-trigger-button.active {
            animation: clickPulse 0.3s ease-out;
        }
        
        .energy-bar {
            width: 100%;
            height: 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .energy-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff88, #0088ff);
            transition: width 0.3s ease;
            border-radius: 10px;
        }
        
        .energy-bar-fill.low {
            background: linear-gradient(90deg, #ff4444, #ffaa00);
        }
        
        .energy-bar-fill.medium {
            background: linear-gradient(90deg, #ffaa00, #ffdd00);
        }
        
        .debugger-active {
            animation: pulse 1s infinite;
            box-shadow: 0 0 20px rgba(0, 255, 136, 0.8);
        }
        
        @keyframes pulse {
            0%, 100% {
                opacity: 1;
                transform: scale(1);
            }
            50% {
                opacity: 0.8;
                transform: scale(1.05);
            }
        }
        
        .counter-display {
            display: inline-block;
            padding: 5px 10px;
            background: rgba(0, 255, 136, 0.1);
            border-radius: 5px;
            margin: 2px;
            font-size: 0.9em;
            border: 1px solid rgba(0, 255, 136, 0.3);
        }
        
        .counter-display.active {
            background: rgba(0, 255, 136, 0.2);
            border-color: rgba(0, 255, 136, 0.6);
            animation: counterTick 0.5s ease-out;
        }
        
        @keyframes counterTick {
            0% {
                transform: scale(1);
            }
            50% {
                transform: scale(1.1);
            }
            100% {
                transform: scale(1);
            }
        }
        
        .story-chapter {
            padding: 15px;
            margin: 10px 0;
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.1), rgba(255, 100, 255, 0.1));
            border-left: 4px solid var(--primary);
            border-radius: 5px;
        }
        
        .story-chapter.active {
            border-left-color: var(--accent);
            box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
        }
        
        .click-trigger-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }
        
        .trigger-button {
            padding: 15px;
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.2), rgba(255, 100, 255, 0.2));
            border: 2px solid var(--primary);
            border-radius: 10px;
            cursor: pointer;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .trigger-button:hover:not(.disabled) {
            transform: translateY(-3px) scale(1.05);
            box-shadow: 0 5px 20px rgba(0, 255, 136, 0.4);
        }
        
        .trigger-button.disabled {
            opacity: 0.5;
            cursor: not-allowed;
            border-color: var(--text-secondary);
        }
        
        .trigger-button.locked::after {
            content: '🔒';
            position: absolute;
            top: 5px;
            right: 5px;
            font-size: 0.8em;
        }
    `;
    document.head.appendChild(style);
}

// Export for use
window.ClickThroughGame = ClickThroughGame;
