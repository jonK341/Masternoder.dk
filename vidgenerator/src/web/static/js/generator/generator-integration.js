/**
 * Generator Integration System
 * Connects all generator features together
 */

class GeneratorIntegration {
    constructor() {
        this.currentDocId = null;
        this.generationState = {
            phase: 'idle', // idle, gathering, generating, completed, failed
            progress: 0,
            xpEarned: 0,
            theme: 'matrix',
            intelligence: null
        };
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadUserPreferences();
        this.connectToStats();
        this.connectToGame();
        this.connectToXP();
    }
    
    setupEventListeners() {
        // Connect generate button
        const generateBtn = document.getElementById('generate-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.startGeneration());
        }
        
        // Connect theme selector
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.addEventListener('change', (e) => {
                this.generationState.theme = e.target.value;
                this.updateThemeDisplay();
            });
        }
        
        // Connect prompt input
        const promptInput = document.getElementById('documentary-prompt');
        if (promptInput) {
            promptInput.addEventListener('input', () => this.analyzePrompt());
            promptInput.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 'Enter') {
                    this.startGeneration();
                }
            });
        }
    }
    
    async analyzePrompt() {
        const promptInput = document.getElementById('documentary-prompt');
        const prompt = promptInput?.value || '';
        
        if (prompt.length < 10) return;
        
        try {
            const response = await fetch('/vidgenerator/api/generator/generation-intelligence', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt})
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.intelligence) {
                    this.updateIntelligenceDisplay(data.intelligence);
                    this.suggestTheme(data.intelligence);
                }
            }
        } catch (error) {
            console.error('Error analyzing prompt:', error);
        }
    }
    
    updateIntelligenceDisplay(intelligence) {
        // Update UI with intelligence data
        const complexityEl = document.getElementById('prompt-complexity');
        if (complexityEl) {
            complexityEl.textContent = intelligence.prompt_analysis?.complexity || 'medium';
        }
        
        // Show theme suggestions
        if (intelligence.theme_suggestions && intelligence.theme_suggestions.length > 0) {
            this.showThemeSuggestions(intelligence.theme_suggestions);
        }
    }
    
    suggestTheme(suggestions) {
        if (suggestions.theme_suggestions && suggestions.theme_suggestions.length > 0) {
            const bestTheme = suggestions.theme_suggestions[0];
            const themeSelector = document.getElementById('theme-selector');
            if (themeSelector && bestTheme.confidence > 0.7) {
                themeSelector.value = bestTheme.theme;
                this.generationState.theme = bestTheme.theme;
                this.showNotification(`Suggested theme: ${bestTheme.theme} (${bestTheme.reason})`);
            }
        }
    }
    
    async startGeneration() {
        const promptInput = document.getElementById('documentary-prompt');
        const titleInput = document.getElementById('documentary-title');
        const durationSelect = document.getElementById('documentary-duration');
        const themeSelector = document.getElementById('theme-selector');
        
        const prompt = promptInput?.value?.trim() || '';
        const title = titleInput?.value?.trim() || '';
        const duration = parseInt(durationSelect?.value) || 45;
        const theme = themeSelector?.value || 'matrix';
        
        if (!prompt) {
            this.showError('Please enter a prompt');
            return;
        }
        
        // Update state
        this.generationState.phase = 'gathering';
        this.generationState.progress = 5;
        this.generationState.theme = theme;
        
        // Show progress
        this.updateProgressDisplay();
        
        try {
            // Phase 1: Gather intelligence
            const intelligenceResponse = await fetch('/vidgenerator/api/documentary/gather-intelligence', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    doc_id: this.currentDocId || undefined,
                    prompt,
                    title: title || undefined,
                    theme,
                    clip_duration: 10
                })
            });
            
            if (!intelligenceResponse.ok) {
                throw new Error('Failed to start intelligence gathering');
            }
            
            const intelligenceData = await intelligenceResponse.json();
            this.currentDocId = intelligenceData.doc_id;
            this.generationState.intelligence = intelligenceData;
            
            // Phase 2: Generate from intelligence
            this.generationState.phase = 'generating';
            this.generationState.progress = 50;
            this.updateProgressDisplay();
            
            const generateResponse = await fetch('/vidgenerator/api/documentary/generate-from-intelligence', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    doc_id: this.currentDocId,
                    intelligence: this.generationState.intelligence,
                    strategy: 'balanced',
                    target_duration: duration * 60,
                    clip_duration: 10,
                    theme
                })
            });
            
            if (!generateResponse.ok) {
                throw new Error('Generation failed');
            }
            
            const generateData = await generateResponse.json();
            
            if (generateData.success) {
                this.generationState.phase = 'completed';
                this.generationState.progress = 100;
                this.generationState.xpEarned = generateData.xp_awarded || 0;
                
                // Award XP
                await this.awardXP(generateData.xp_awarded || 0);
                
                // Update game stats
                await this.updateGameStats(theme);
                
                // Show success
                this.showSuccess('Generation completed!', generateData);
            } else {
                throw new Error(generateData.error || 'Generation failed');
            }
            
        } catch (error) {
            this.generationState.phase = 'failed';
            this.showError(error.message);
        } finally {
            this.updateProgressDisplay();
        }
    }
    
    async awardXP(amount) {
        if (!amount || amount <= 0) return;
        
        try {
            // XP is already awarded by the backend, but we can show notification
            this.showNotification(`🎉 Earned ${amount} XP!`, 'success');
            
            // Update XP display if available
            const xpDisplay = document.getElementById('current-xp');
            if (xpDisplay) {
                const currentXP = parseInt(xpDisplay.textContent) || 0;
                xpDisplay.textContent = currentXP + amount;
            }
            
            // Trigger XP update in stats
            if (window.loadStatistics) {
                window.loadStatistics();
            }
        } catch (error) {
            console.error('Error updating XP:', error);
        }
    }
    
    async updateGameStats(theme) {
        try {
            // Update hunters game
            const gameResponse = await fetch('/vidgenerator/api/game/hunters/complete-hunt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.getUserId(),
                    base_xp: 100,
                    success: true,
                    theme
                })
            });
            
            if (gameResponse.ok) {
                const gameData = await gameResponse.json();
                if (gameData.success) {
                    this.showNotification(`🎮 Game: Earned ${gameData.xp_earned || 0} XP from ${theme} theme!`, 'info');
                }
            }
        } catch (error) {
            console.error('Error updating game stats:', error);
        }
    }
    
    async calculateXPBonus() {
        const promptInput = document.getElementById('documentary-prompt');
        const themeSelector = document.getElementById('theme-selector');
        const durationSelect = document.getElementById('documentary-duration');
        
        const prompt = promptInput?.value || '';
        const theme = themeSelector?.value || 'matrix';
        const duration = parseInt(durationSelect?.value) || 45;
        
        try {
            const response = await fetch('/vidgenerator/api/generator/calculate-xp-bonus', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    prompt,
                    theme,
                    duration
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.xp_calculation) {
                    this.showXPPreview(data.xp_calculation);
                }
            }
        } catch (error) {
            console.error('Error calculating XP bonus:', error);
        }
    }
    
    showXPPreview(calculation) {
        const xpPreview = document.getElementById('xp-preview');
        if (xpPreview) {
            xpPreview.innerHTML = `
                <div style="background: rgba(0, 255, 0, 0.1); padding: 10px; border-radius: 5px; margin-top: 10px;">
                    <strong>Estimated XP:</strong> ${calculation.total_xp}
                    <br><small>Base: ${calculation.base_xp} × ${calculation.complexity_multiplier.toFixed(2)} (complexity) × ${calculation.theme_multiplier.toFixed(2)} (theme) × ${calculation.duration_multiplier.toFixed(2)} (duration)</small>
                </div>
            `;
        }
    }
    
    updateProgressDisplay() {
        const progressBar = document.getElementById('generation-progress');
        const statusText = document.getElementById('generation-status');
        
        if (progressBar) {
            progressBar.style.width = `${this.generationState.progress}%`;
        }
        
        if (statusText) {
            const statusMessages = {
                'idle': 'Ready to generate',
                'gathering': 'Gathering intelligence...',
                'generating': 'Generating video...',
                'completed': 'Generation completed!',
                'failed': 'Generation failed'
            };
            statusText.textContent = statusMessages[this.generationState.phase] || 'Unknown';
        }
    }
    
    updateThemeDisplay() {
        // Update theme-specific UI elements
        const theme = this.generationState.theme;
        document.body.className = document.body.className.replace(/theme-\w+/g, '');
        document.body.classList.add(`theme-${theme}`);
    }
    
    connectToStats() {
        // Auto-update stats after generation
        if (this.generationState.phase === 'completed') {
            if (window.loadStatistics) {
                window.loadStatistics();
            }
        }
    }
    
    connectToGame() {
        // Game integration is handled in updateGameStats
    }
    
    connectToXP() {
        // XP integration is handled in awardXP
    }
    
    loadUserPreferences() {
        try {
            const saved = localStorage.getItem('generator_preferences');
            if (saved) {
                const prefs = JSON.parse(saved);
                this.generationState.theme = prefs.theme || 'matrix';
                
                const themeSelector = document.getElementById('theme-selector');
                if (themeSelector) {
                    themeSelector.value = this.generationState.theme;
                }
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
        }
    }
    
    saveUserPreferences() {
        try {
            localStorage.setItem('generator_preferences', JSON.stringify({
                theme: this.generationState.theme
            }));
        } catch (error) {
            console.error('Error saving preferences:', error);
        }
    }
    
    getUserId() {
        // Get user ID from session or generate
        let userId = sessionStorage.getItem('user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('user_id', userId);
        }
        return userId;
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'success' ? 'rgba(0, 255, 0, 0.9)' : type === 'error' ? 'rgba(255, 0, 0, 0.9)' : 'rgba(0, 150, 255, 0.9)'};
            color: white;
            border-radius: 8px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message, data) {
        this.showNotification(message, 'success');
        
        // Show video if available
        if (data.video_path) {
            setTimeout(() => {
                window.location.href = `/vidgenerator/gallery?highlight=${this.currentDocId}`;
            }, 2000);
        }
    }
    
    showThemeSuggestions(suggestions) {
        const suggestionsEl = document.getElementById('theme-suggestions');
        if (suggestionsEl && suggestions.length > 0) {
            suggestionsEl.innerHTML = suggestions.map(s => `
                <div class="theme-suggestion" data-theme="${s.theme}" style="cursor: pointer; padding: 5px; margin: 5px 0; background: rgba(0, 255, 0, 0.1); border-radius: 5px;">
                    ${s.theme} (${(s.confidence * 100).toFixed(0)}% - ${s.reason})
                </div>
            `).join('');
            
            // Add click handlers
            suggestionsEl.querySelectorAll('.theme-suggestion').forEach(el => {
                el.addEventListener('click', () => {
                    const theme = el.dataset.theme;
                    const themeSelector = document.getElementById('theme-selector');
                    if (themeSelector) {
                        themeSelector.value = theme;
                        this.generationState.theme = theme;
                        this.updateThemeDisplay();
                    }
                });
            });
        }
    }
}

// Initialize on page load
let generatorIntegration;
document.addEventListener('DOMContentLoaded', () => {
    generatorIntegration = new GeneratorIntegration();
    
    // Make available globally
    window.generatorIntegration = generatorIntegration;
    
    // Connect to existing generator code if available
    if (window.startGeneration) {
        const originalStart = window.startGeneration;
        window.startGeneration = function(...args) {
            generatorIntegration.startGeneration();
            if (originalStart) originalStart.apply(this, args);
        };
    }
});

