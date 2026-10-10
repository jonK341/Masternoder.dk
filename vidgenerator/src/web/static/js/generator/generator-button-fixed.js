/**
 * Fixed Generator Button - Complete Integration
 * Connects service worker intelligence → AI generation → XP/stats → war plan
 */

class FixedGeneratorButton {
    constructor() {
        this.currentDocId = null;
        this.intelligence = null;
        this.superPrompt = null;
        this.generationState = {
            phase: 'idle',
            progress: 0,
            xpEarned: 0,
            stats: {}
        };
        this.init();
    }
    
    init() {
        this.setupButton();
        this.setupKeyboardShortcut();
        this.setupProgressDisplay();
    }
    
    setupButton() {
        const generateBtn = document.getElementById('generate-btn');
        if (!generateBtn) {
            console.error('[GeneratorButton] Generate button not found!');
            setTimeout(() => this.setupButton(), 1000);
            return;
        }
        
        // Remove existing listeners
        const newBtn = generateBtn.cloneNode(true);
        generateBtn.parentNode.replaceChild(newBtn, generateBtn);
        
        // Add click handler
        newBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('[GeneratorButton] Button clicked - starting generation');
            this.startCompleteGeneration();
        });
        
        // Enable button
        newBtn.disabled = false;
        newBtn.style.opacity = '1';
        newBtn.style.cursor = 'pointer';
        
        console.log('[GeneratorButton] Button initialized and ready');
    }
    
    setupKeyboardShortcut() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.startCompleteGeneration();
            }
        });
    }
    
    setupProgressDisplay() {
        // Ensure progress container exists
        const progressContainer = document.getElementById('progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }
    
    async startCompleteGeneration() {
        console.log('[GeneratorButton] Starting complete generation process');
        
        // Get inputs
        const promptInput = document.getElementById('documentary-prompt') || document.getElementById('prompt-input');
        const titleInput = document.getElementById('documentary-title');
        const durationSelect = document.getElementById('documentary-duration');
        const themeSelector = document.getElementById('theme-selector');
        const clipDurationInput = document.getElementById('clip-duration-setting');
        
        const prompt = promptInput?.value?.trim() || '';
        const title = titleInput?.value?.trim() || '';
        const duration = parseInt(durationSelect?.value) || 45;
        const theme = themeSelector?.value || 'matrix';
        const clipDuration = parseInt(clipDurationInput?.value) || 10;
        
        // Validate
        if (!prompt) {
            this.showError('Please enter a prompt');
            return;
        }
        
        // Generate doc ID
        this.currentDocId = this.generateDocId();
        
        // Show progress
        this.showProgress();
        this.updateProgress(5, '🚀 Starting generation process...');
        
        try {
            // STEP 1: Service Worker Intelligence Gathering
            this.updateProgress(10, '📡 Phase 1: Service Worker gathering intelligence...');
            const intelligence = await this.gatherIntelligenceViaServiceWorker(prompt, title, theme);
            
            // STEP 2: Create Super Prompt from Intelligence
            this.updateProgress(40, '🧠 Creating super prompt from intelligence...');
            this.superPrompt = this.createSuperPrompt(prompt, intelligence);
            
            // STEP 3: AI Generation with Super Prompt
            this.updateProgress(50, '🎬 Phase 2: AI generating video from super prompt...');
            const generationResult = await this.generateWithAI(this.superPrompt, intelligence, {
                doc_id: this.currentDocId,
                title,
                duration,
                theme,
                clip_duration: clipDuration
            });
            
            // STEP 4: Track XP and Stats
            this.updateProgress(90, '📊 Tracking XP and stats...');
            await this.trackXPAndStats(generationResult, theme);
            
            // STEP 5: Connect to War Plan
            this.updateProgress(95, '⚔️ Updating war plan...');
            await this.updateWarPlan(theme, generationResult);
            
            // STEP 6: Complete
            this.updateProgress(100, '✅ Generation complete!');
            this.showSuccess(generationResult);
            
        } catch (error) {
            console.error('[GeneratorButton] Generation error:', error);
            this.showError(error.message);
            this.updateProgress(0, `❌ Error: ${error.message}`);
        }
    }
    
    async gatherIntelligenceViaServiceWorker(prompt, title, theme) {
        console.log('[GeneratorButton] Gathering intelligence via service worker');
        
        // Request service worker to gather intelligence
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            return new Promise((resolve, reject) => {
                const messageChannel = new MessageChannel();
                
                messageChannel.port1.onmessage = (event) => {
                    if (event.data.success) {
                        console.log('[GeneratorButton] Intelligence gathered:', event.data.intelligence);
                        resolve(event.data.intelligence);
                    } else {
                        reject(new Error(event.data.error || 'Intelligence gathering failed'));
                    }
                };
                
                // Send gather request to service worker
                navigator.serviceWorker.controller.postMessage({
                    type: 'GATHER_INTELLIGENCE',
                    prompt,
                    title,
                    theme,
                    doc_id: this.currentDocId
                }, [messageChannel.port2]);
                
                // Fallback timeout
                setTimeout(() => {
                    reject(new Error('Intelligence gathering timeout'));
                }, 60000);
            });
        } else {
            // Fallback: Use API directly
            console.log('[GeneratorButton] Service worker not available, using API fallback');
            const response = await fetch('/vidgenerator/api/documentary/gather-intelligence', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    doc_id: this.currentDocId,
                    prompt,
                    title: title || undefined,
                    theme,
                    clip_duration: 10
                })
            });
            
            if (!response.ok) {
                throw new Error('Intelligence gathering failed');
            }
            
            const data = await response.json();
            return data.intelligence || {};
        }
    }
    
    createSuperPrompt(originalPrompt, intelligence) {
        console.log('[GeneratorButton] Creating super prompt from intelligence');
        
        // Build comprehensive super prompt from intelligence
        let superPrompt = `# COMPREHENSIVE DOCUMENTARY PROMPT\n\n`;
        superPrompt += `## Original Request:\n${originalPrompt}\n\n`;
        
        // Add research findings
        if (intelligence.research) {
            superPrompt += `## Research Findings:\n`;
            Object.entries(intelligence.research).forEach(([key, value]) => {
                if (value && typeof value === 'string') {
                    superPrompt += `- ${key}: ${value.substring(0, 200)}\n`;
                }
            });
            superPrompt += `\n`;
        }
        
        // Add keywords
        if (intelligence.keywords && intelligence.keywords.length > 0) {
            superPrompt += `## Key Terms:\n`;
            intelligence.keywords.slice(0, 10).forEach(kw => {
                superPrompt += `- ${kw.keyword || kw} (${kw.category || 'general'})\n`;
            });
            superPrompt += `\n`;
        }
        
        // Add images context
        if (intelligence.images && intelligence.images.images) {
            superPrompt += `## Visual Context:\n`;
            superPrompt += `Found ${intelligence.images.images.length} relevant images\n`;
            if (intelligence.images.images.length > 0) {
                superPrompt += `Primary image themes: ${intelligence.images.images.slice(0, 3).map(img => img.description || 'visual').join(', ')}\n`;
            }
            superPrompt += `\n`;
        }
        
        // Add metadata
        if (intelligence.metadata) {
            superPrompt += `## Intelligence Metadata:\n`;
            superPrompt += `- Sources: ${intelligence.metadata.sources_count || 0}\n`;
            superPrompt += `- Intelligence Score: ${intelligence.metadata.intelligence_score || 0}\n`;
            superPrompt += `- Quality: ${intelligence.metadata.quality || 'standard'}\n`;
            superPrompt += `\n`;
        }
        
        // Final instruction
        superPrompt += `## Generation Instructions:\n`;
        superPrompt += `Create a comprehensive documentary video using all the above intelligence. `;
        superPrompt += `Ensure visual consistency, factual accuracy, and engaging narrative flow. `;
        superPrompt += `Use the research findings to enhance the narrative depth and visual storytelling.`;
        
        this.superPrompt = superPrompt;
        console.log('[GeneratorButton] Super prompt created:', superPrompt.substring(0, 200) + '...');
        
        return superPrompt;
    }
    
    async generateWithAI(superPrompt, intelligence, options) {
        console.log('[GeneratorButton] Generating with AI using super prompt');
        
        // Prepare generation request with super prompt
        const generateData = {
            doc_id: options.doc_id,
            prompt: superPrompt, // Use super prompt instead of original
            original_prompt: options.prompt || superPrompt.substring(0, 200), // Keep original for reference
            title: options.title,
            intelligence: intelligence, // Pass full intelligence
            strategy: 'intelligent', // Use intelligent strategy
            target_duration: options.duration * 60,
            clip_duration: options.clip_duration,
            theme: options.theme,
            metadata: {
                super_prompt_used: true,
                intelligence_score: intelligence.metadata?.intelligence_score || 0,
                sources_count: intelligence.metadata?.sources_count || 0
            }
        };
        
        const response = await fetch('/vidgenerator/api/documentary/generate-from-intelligence', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(generateData)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Generation failed: ${errorText.substring(0, 200)}`);
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Generation failed');
        }
        
        return result;
    }
    
    async trackXPAndStats(result, theme) {
        console.log('[GeneratorButton] Tracking XP and stats');
        
        const xpAwarded = result.xp_awarded || 0;
        const userId = this.getUserId();
        
        // Calculate XP bonus
        const xpBonus = await this.calculateXPBonus(theme, result);
        const totalXP = xpAwarded + xpBonus;
        
        // Track in multiple systems
        try {
            // 1. Update stats
            await fetch('/vidgenerator/api/statistics', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    action: 'generation_complete',
                    doc_id: this.currentDocId,
                    xp: totalXP,
                    theme
                })
            });
            
            // 2. Update user profile
            await fetch('/vidgenerator/api/user/profile', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    last_generation: new Date().toISOString(),
                    total_generations: '+1'
                })
            });
            
            // 3. Track in game
            await fetch('/vidgenerator/api/game/hunters/complete-hunt', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: userId,
                    base_xp: 100,
                    success: true,
                    theme
                })
            });
            
            this.generationState.xpEarned = totalXP;
            this.generationState.stats = {
                xp_awarded: totalXP,
                xp_bonus: xpBonus,
                theme,
                doc_id: this.currentDocId
            };
            
            console.log(`[GeneratorButton] XP tracked: ${totalXP} (base: ${xpAwarded}, bonus: ${xpBonus})`);
            
        } catch (error) {
            console.error('[GeneratorButton] Error tracking XP/stats:', error);
        }
    }
    
    async calculateXPBonus(theme, result) {
        try {
            const response = await fetch('/vidgenerator/api/generator/calculate-xp-bonus', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    prompt: this.superPrompt || '',
                    theme,
                    duration: result.duration || 0,
                    quality_score: result.quality_score || 0.8
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.xp_calculation) {
                    return data.xp_calculation.total_xp - 100; // Bonus = total - base
                }
            }
        } catch (error) {
            console.error('[GeneratorButton] Error calculating XP bonus:', error);
        }
        return 0;
    }
    
    async updateWarPlan(theme, result) {
        console.log('[GeneratorButton] Updating war plan');
        
        try {
            const userId = this.getUserId();
            
            // Check if user has active war plan
            const statusResponse = await fetch(`/vidgenerator/api/war-plan/status/${userId}`);
            if (statusResponse.ok) {
                const statusData = await statusResponse.json();
                if (statusData.success && statusData.active) {
                    // Execute defense (generation counts as defense action)
                    await fetch('/vidgenerator/api/war-plan/defend', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            user_id: userId,
                            tactic: 'backup_system' // Generation is like creating backup content
                        })
                    });
                }
            }
        } catch (error) {
            console.error('[GeneratorButton] Error updating war plan:', error);
        }
    }
    
    showProgress() {
        const progressContainer = document.getElementById('progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
        
        const generateBtn = document.getElementById('generate-btn');
        if (generateBtn) {
            generateBtn.disabled = true;
            const loader = generateBtn.querySelector('.btn-loader');
            if (loader) loader.style.display = 'inline-block';
            const text = generateBtn.querySelector('.btn-text');
            if (text) text.textContent = 'Generating...';
        }
    }
    
    updateProgress(percentage, message) {
        this.generationState.progress = percentage;
        
        // Update progress bar
        const progressFill = document.getElementById('progress-fill');
        if (progressFill) {
            progressFill.style.width = `${percentage}%`;
        }
        
        // Update percentage
        const progressPercentage = document.getElementById('progress-percentage');
        if (progressPercentage) {
            progressPercentage.textContent = `${percentage}%`;
        }
        
        // Update message
        const progressText = document.getElementById('progress-text');
        if (progressText) {
            progressText.textContent = message;
        }
        
        console.log(`[GeneratorButton] Progress: ${percentage}% - ${message}`);
    }
    
    showSuccess(result) {
        const generateBtn = document.getElementById('generate-btn');
        if (generateBtn) {
            generateBtn.disabled = false;
            const loader = generateBtn.querySelector('.btn-loader');
            if (loader) loader.style.display = 'none';
            const text = generateBtn.querySelector('.btn-text');
            if (text) text.textContent = 'Generate Documentary';
        }
        
        // Show success notification
        this.showNotification(`✅ Generation complete! Earned ${this.generationState.xpEarned} XP`, 'success');
        
        // Redirect to gallery or show video
        if (result.video_path) {
            setTimeout(() => {
                window.location.href = `/vidgenerator/gallery?highlight=${this.currentDocId}`;
            }, 2000);
        }
    }
    
    showError(message) {
        const generateBtn = document.getElementById('generate-btn');
        if (generateBtn) {
            generateBtn.disabled = false;
            const loader = generateBtn.querySelector('.btn-loader');
            if (loader) loader.style.display = 'none';
            const text = generateBtn.querySelector('.btn-text');
            if (text) text.textContent = 'Generate Documentary';
        }
        
        this.showNotification(`❌ Error: ${message}`, 'error');
    }
    
    showNotification(message, type = 'info') {
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
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
    
    generateDocId() {
        return 'doc_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    getUserId() {
        let userId = sessionStorage.getItem('user_id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('user_id', userId);
        }
        return userId;
    }
}

// Initialize on page load
let fixedGeneratorButton;
document.addEventListener('DOMContentLoaded', () => {
    fixedGeneratorButton = new FixedGeneratorButton();
    window.fixedGeneratorButton = fixedGeneratorButton;
    console.log('[GeneratorButton] Fixed generator button initialized');
});

// Also try after a delay to ensure everything is loaded
setTimeout(() => {
    if (!fixedGeneratorButton) {
        fixedGeneratorButton = new FixedGeneratorButton();
        window.fixedGeneratorButton = fixedGeneratorButton;
    }
}, 2000);

