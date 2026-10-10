/**
 * Simplified Two-Phase Generator with Auto Monetization
 * Streamlined generation process with automatic monetization integration
 */

class SimplifiedTwoPhaseGenerator {
    constructor() {
        this.currentDocId = null;
        this.intelligence = null;
        this.monetization = new AutoMonetization();
        this.initializeGenerator();
    }
    
    initializeGenerator() {
        // Setup UI - Wait for DOM to be ready
        const setupButtons = () => {
            const generateBtn = document.getElementById('generate-btn');
            if (generateBtn) {
                // Remove existing listeners to prevent duplicates
                const newBtn = generateBtn.cloneNode(true);
                generateBtn.parentNode.replaceChild(newBtn, generateBtn);
                
                // Add click handler
                newBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('[Generator] Generate button clicked');
                    this.startGeneration();
                });
                
                // Enable button
                newBtn.disabled = false;
                newBtn.style.opacity = '1';
                newBtn.style.cursor = 'pointer';
                console.log('[Generator] Generate button initialized and enabled');
            } else {
                console.warn('[Generator] Generate button not found, retrying...');
                setTimeout(setupButtons, 500);
            }
            
            // Also setup quick generate button
            const quickGenerateBtn = document.getElementById('quick-generate');
            if (quickGenerateBtn) {
                quickGenerateBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log('[Generator] Quick generate clicked');
                    this.startGeneration();
                });
            }
        };
        
        // Try immediately
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupButtons);
        } else {
            setupButtons();
        }
        
        // Also try after a delay to ensure everything is loaded
        setTimeout(setupButtons, 1000);
        
        // Initialize monetization
        this.monetization.initialize();
    }
    
    async startGeneration() {
        const promptInput = document.getElementById('prompt-input');
        const prompt = promptInput?.value.trim();
        
        // Validate input
        if (typeof generatorInputValidator !== 'undefined') {
            const validation = generatorInputValidator.validateAll({ prompt });
            if (!validation.valid) {
                if (typeof generatorErrorHandler !== 'undefined') {
                    generatorErrorHandler.handleError(
                        new Error(validation.allErrors.join(', ')),
                        { type: 'validation' }
                    );
                } else {
                    alert(validation.allErrors.join('\n'));
                }
                return;
            }
        } else if (!prompt) {
            alert('Please enter a prompt');
            return;
        }
        
        // Check monetization limits
        const canGenerate = await this.monetization.checkGenerationLimit();
        if (!canGenerate.allowed) {
            this.showUpgradePrompt(canGenerate.reason);
            return;
        }
        
        // Generate doc ID
        this.currentDocId = this.generateDocId();
        
        // Save initial progress
        if (progressPersistence) {
            progressPersistence.saveProgress({
                docId: this.currentDocId,
                prompt: prompt,
                status: 'starting',
                progress: 0,
                message: 'Starting generation...'
            });
        }
        
        // Show progress
        this.showProgress();
        
        // Start simplified two-phase process
        await this.phase1Intelligence(prompt);
    }
    
    async phase1Intelligence(prompt) {
        // Show Phase 1 frame
        this.showPhaseFrame(1, 'Service Worker Intelligence Collection');
        this.updateProgress(10, 'Phase 1: Service Worker gathering intelligence...');
        
        try {
            // Use retry manager if available
            const fetchFn = retryManager ? 
                () => retryManager.fetchJsonWithRetry('/vidgenerator/api/documentary/gather-intelligence', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        doc_id: this.currentDocId,
                        prompt: prompt,
                        title: prompt.substring(0, 50)
                    })
                }, {
                    onRetry: (attempt, maxAttempts, delay, error) => {
                        this.updateProgress(10, `Retrying intelligence gathering... (${attempt}/${maxAttempts})`);
                        console.log(`[Retry] Attempt ${attempt}/${maxAttempts} after ${delay}ms:`, error);
                    }
                }) :
                async () => {
                    const response = await fetch('/vidgenerator/api/documentary/gather-intelligence', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            doc_id: this.currentDocId,
                            prompt: prompt,
                            title: prompt.substring(0, 50)
                        })
                    });
                    
                    if (!response.ok) {
                        const contentType = response.headers.get('content-type');
                        if (!contentType || !contentType.includes('application/json')) {
                            const text = await response.text();
                            throw new Error(`Intelligence gathering failed: Server returned HTML (${response.status})`);
                        }
                        const errorData = await response.json().catch(() => ({}));
                        throw new Error(errorData.error || errorData.message || 'Intelligence gathering failed');
                    }
                    
                    return { response, data: await response.json() };
                };
            
            const result = await fetchFn();
            const data = result.data || result;
            this.intelligence = data.intelligence;
            
            this.updateProgress(50, 'Phase 1 Complete: Intelligence gathered!');
            
            // Log intelligence summary
            console.log('[Phase1] Intelligence gathered:', {
                sources: this.intelligence?.metadata?.sources_count || 0,
                score: this.intelligence?.metadata?.intelligence_score || 0,
                images: this.intelligence?.images?.images?.length || 0,
                research: Object.keys(this.intelligence?.research || {}).length
            });
            
            // Auto-monetization: Check if premium features should be suggested
            await this.monetization.suggestPremiumFeatures(this.intelligence);
            
            // Continue to Phase 2
            await this.phase2Generation();
            
        } catch (error) {
            console.error('[SimplifiedGenerator] Phase 1 error:', error);
            
            // Save error state
            if (progressPersistence) {
                progressPersistence.updateProgress({
                    status: 'failed',
                    error: error.message
                });
            }
            
            if (typeof generatorErrorHandler !== 'undefined') {
                generatorErrorHandler.handleError(error, { context: 'phase1' });
            } else {
                this.showError(error.message);
            }
        }
    }
    
    async phase2Generation() {
        // Show Phase 2 frame
        this.showPhaseFrame(2, 'AI Generation with Collected Intelligence');
        this.updateProgress(60, 'Phase 2: AI generating clips from intelligence...');
        
        try {
            const clipCount = document.getElementById('clip-count-setting')?.value || 10;
            const duration = document.getElementById('duration-input')?.value || 180;
            
            // Auto-monetization: Apply premium boosts if available
            const boosts = await this.monetization.getActiveBoosts();
            
            // Use retry manager if available
            const fetchFn = retryManager ?
                () => retryManager.fetchJsonWithRetry('/vidgenerator/api/documentary/generate-from-intelligence', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        doc_id: this.currentDocId,
                        intelligence: this.intelligence,
                        target_duration: duration,
                        clip_count: clipCount + (boosts.extra_clips || 0),
                        quality_boost: boosts.quality_boost || false,
                        speed_boost: boosts.speed_boost || false
                    })
                }, {
                    onRetry: (attempt, maxAttempts, delay, error) => {
                        this.updateProgress(60, `Retrying generation... (${attempt}/${maxAttempts})`);
                        console.log(`[Retry] Attempt ${attempt}/${maxAttempts} after ${delay}ms:`, error);
                    }
                }) :
                async () => {
                    const response = await fetch('/vidgenerator/api/documentary/generate-from-intelligence', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            doc_id: this.currentDocId,
                            intelligence: this.intelligence,
                            target_duration: duration,
                            clip_count: clipCount + (boosts.extra_clips || 0),
                            quality_boost: boosts.quality_boost || false,
                            speed_boost: boosts.speed_boost || false
                        })
                    });
                    
                    if (!response.ok) {
                        const contentType = response.headers.get('content-type');
                        if (!contentType || !contentType.includes('application/json')) {
                            const text = await response.text();
                            throw new Error(`Generation failed: Server returned HTML (${response.status})`);
                        }
                        const errorData = await response.json().catch(() => ({}));
                        throw new Error(errorData.error || errorData.message || 'Generation failed');
                    }
                    
                    return { response, data: await response.json() };
                };
            
            await fetchFn();
            
            // Poll for progress
            await this.pollProgress();
            
        } catch (error) {
            console.error('[SimplifiedGenerator] Phase 2 error:', error);
            if (typeof generatorErrorHandler !== 'undefined') {
                generatorErrorHandler.handleError(error, { context: 'phase2' });
            } else {
                this.showError(error.message);
            }
        }
    }
    
    async pollProgress() {
        const maxAttempts = 300;
        let attempts = 0;
        
        const poll = async () => {
            try {
                // Use retry manager if available for progress polling
                let data;
                if (retryManager) {
                    try {
                        const result = await retryManager.fetchJsonWithRetry(
                            `/vidgenerator/api/documentary/${this.currentDocId}/progress`,
                            { method: 'GET' },
                            { onRetry: () => {} } // Silent retries for polling
                        );
                        data = result.data;
                    } catch (error) {
                        // If progress endpoint fails, just skip this poll
                        console.warn('[SimplifiedGenerator] Progress poll failed:', error);
                        if (attempts < maxAttempts) {
                            attempts++;
                            setTimeout(poll, 2000);
                        }
                        return;
                    }
                } else {
                    const response = await fetch(`/vidgenerator/api/documentary/${this.currentDocId}/progress`);
                    if (!response.ok) {
                        const contentType = response.headers.get('content-type');
                        if (!contentType || !contentType.includes('application/json')) {
                            console.warn('[SimplifiedGenerator] Progress endpoint returned HTML, skipping poll');
                            if (attempts < maxAttempts) {
                                attempts++;
                                setTimeout(poll, 2000);
                            }
                            return;
                        }
                        if (attempts < maxAttempts) {
                            attempts++;
                            setTimeout(poll, 2000);
                        }
                        return;
                    }
                    data = JSONResponseHandler ? await JSONResponseHandler.safeJson(response) : await response.json();
                }
                this.updateProgress(data.progress || 0, data.message || 'Generating...');
                
                // Save progress
                if (progressPersistence) {
                    progressPersistence.updateProgress({
                        docId: this.currentDocId,
                        status: data.status || 'generating',
                        progress: data.progress || 0,
                        message: data.message || 'Generating...',
                        intelligence: this.intelligence
                    });
                }
                
                // Auto-monetization: Track usage
                await this.monetization.trackGeneration(data);
                
                if (data.status === 'complete' || data.progress >= 100) {
                    this.updateProgress(100, 'Complete!');
                    
                    // Clear saved progress on completion
                    if (progressPersistence) {
                        progressPersistence.clearProgress();
                    }
                    
                    await this.showResults(data);
                    return;
                }
                
                if (attempts < maxAttempts) {
                    attempts++;
                    setTimeout(poll, 2000);
                }
            } catch (error) {
                console.error('[SimplifiedGenerator] Poll error:', error);
                if (typeof generatorErrorHandler !== 'undefined') {
                    generatorErrorHandler.handleError(error, { context: 'polling' });
                }
                if (attempts < maxAttempts) {
                    attempts++;
                    setTimeout(poll, 2000);
                }
            }
        };
        
        poll();
    }
    
    async showResults(data) {
        // Hide phase frames
        this.hidePhaseFrames();
        this.updateProgress(100, 'Generation Complete!');
        
        // Show video result
        const resultContainer = document.getElementById('result-container');
        if (resultContainer && data.video_path) {
            resultContainer.innerHTML = `
                <video controls autoplay>
                    <source src="${data.video_path}" type="video/mp4">
                </video>
            `;
        }
        
        // Fire generation complete event for stats
        const generationCompleteEvent = new CustomEvent('generationComplete', {
            detail: {
                doc_id: this.currentDocId,
                video_path: data.video_path,
                duration: data.duration || 0,
                clip_count: data.clip_count || 0,
                quality_score: data.quality_score || 0,
                timestamp: new Date().toISOString()
            }
        });
        document.dispatchEvent(generationCompleteEvent);
        console.log('[Generator] Fired generationComplete event for stats');
        
        // Update stats counter if available
        if (typeof window.statsCounter !== 'undefined' && window.statsCounter) {
            try {
                await window.statsCounter.updateGenerationStats({
                    doc_id: this.currentDocId,
                    video_path: data.video_path,
                    duration: data.duration || 0,
                    clip_count: data.clip_count || 0,
                    quality_score: data.quality_score || 0,
                    status: 'completed'
                });
                console.log('[Generator] Stats updated via StatsCounter');
            } catch (error) {
                console.error('[Generator] Error updating stats:', error);
            }
        }
        
        // Update gallery
        await this.updateGallery(data);
        
        // Update stats (legacy method)
        await this.updateStats(data);
        
        // Auto-monetization: Award rewards
        await this.monetization.awardGenerationRewards(data);
        
        // Auto-monetization: Suggest next steps
        await this.monetization.suggestNextSteps(data);
    }
    
    showPhaseFrame(phaseNumber, title) {
        // Create or update phase frame
        let phaseFrame = document.getElementById('phase-frame');
        if (!phaseFrame) {
            phaseFrame = document.createElement('div');
            phaseFrame.id = 'phase-frame';
            phaseFrame.className = 'phase-frame';
            document.body.appendChild(phaseFrame);
        }
        
        phaseFrame.innerHTML = `
            <div class="phase-frame-content">
                <div class="phase-header">
                    <h2>Phase ${phaseNumber}</h2>
                    <span class="phase-title">${title}</span>
                </div>
                <div class="phase-indicator">
                    <div class="phase-dot phase-${phaseNumber}"></div>
                    <div class="phase-line"></div>
                </div>
            </div>
        `;
        
        phaseFrame.style.display = 'block';
    }
    
    hidePhaseFrames() {
        const phaseFrame = document.getElementById('phase-frame');
        if (phaseFrame) {
            phaseFrame.style.display = 'none';
        }
    }
    
    async updateGallery(data) {
        try {
            // Notify gallery that new video is available
            if (data.video_path && this.currentDocId) {
                await fetch('/vidgenerator/api/gallery/refresh', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        doc_id: this.currentDocId,
                        video_path: data.video_path
                    })
                });
                
                // Dispatch event for gallery to update
                document.dispatchEvent(new CustomEvent('galleryUpdated', {
                    detail: { doc_id: this.currentDocId, video_path: data.video_path }
                }));
            }
        } catch (error) {
            console.error('[SimplifiedGenerator] Gallery update error:', error);
        }
    }
    
    async updateStats(data) {
        try {
            // Update generation stats
            await fetch('/vidgenerator/api/stats/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'generation',
                    data: {
                        status: 'completed',
                        duration: data.duration || 0,
                        quality_score: data.quality_score || 0.8,
                        clips: data.clips || [],
                        doc_id: this.currentDocId
                    }
                })
            });
            
            // Dispatch event for stats to update
            document.dispatchEvent(new CustomEvent('statUpdated', {
                detail: { type: 'generation', data: data }
            }));
        } catch (error) {
            console.error('[SimplifiedGenerator] Stats update error:', error);
        }
    }
    
    showProgress() {
        const progressContainer = document.getElementById('progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
    }
    
    updateProgress(percent, message) {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        if (progressFill) {
            progressFill.style.width = `${percent}%`;
        }
        if (progressText) {
            progressText.textContent = message;
        }
    }
    
    showError(message) {
        alert(`Error: ${message}`);
    }
    
    showUpgradePrompt(reason) {
        // Show monetization upgrade prompt
        this.monetization.showUpgradeModal(reason);
    }
    
    generateDocId() {
        return `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}


class AutoMonetization {
    constructor() {
        this.userTier = 'free';
        this.generationsThisMonth = 0;
        this.activeBoosts = [];
        this.rewards = [];
    }
    
    async initialize() {
        // Load user tier and limits
        await this.loadUserProfile();
        
        // Setup monetization UI
        this.setupMonetizationUI();
    }
    
    async loadUserProfile() {
        try {
            const response = await fetch('/vidgenerator/api/user-profile/enhanced/current');
            if (response.ok) {
                const data = await response.json();
                this.userTier = data.profile?.subscription_tier || 'free';
                this.generationsThisMonth = data.profile?.generations_this_month || 0;
            }
        } catch (error) {
            console.error('[AutoMonetization] Load profile error:', error);
        }
    }
    
    async checkGenerationLimit() {
        const limits = {
            'free': 5,
            'pro': 50,
            'business': Infinity,
            'enterprise': Infinity
        };
        
        const limit = limits[this.userTier] || 5;
        
        if (this.generationsThisMonth >= limit) {
            return {
                allowed: false,
                reason: `You've reached your ${limit} video limit. Upgrade to generate more!`
            };
        }
        
        return { allowed: true };
    }
    
    async suggestPremiumFeatures(intelligence) {
        // Auto-suggest premium features based on intelligence quality
        if (intelligence.metadata?.intelligence_score > 80 && this.userTier === 'free') {
            this.showFeatureSuggestion({
                title: 'Premium Intelligence Available',
                message: 'Upgrade to Pro for enhanced AI features and better results',
                features: ['Advanced AI models', 'Higher quality', 'Faster processing']
            });
        }
    }
    
    async getActiveBoosts() {
        // Get active power-ups/boosts
        return {
            extra_clips: this.activeBoosts.find(b => b.type === 'extra_clips')?.value || 0,
            quality_boost: this.activeBoosts.some(b => b.type === 'quality_boost'),
            speed_boost: this.activeBoosts.some(b => b.type === 'speed_boost')
        };
    }
    
    async trackGeneration(data) {
        // Track generation for monetization
        this.generationsThisMonth++;
        
        // Update usage stats
        await fetch('/vidgenerator/api/monetization/track-usage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                doc_id: data.doc_id,
                tier: this.userTier,
                quality: data.quality_score,
                duration: data.duration
            })
        });
    }
    
    async awardGenerationRewards(data) {
        // Award coins/XP for generation
        if (this.userTier !== 'free') {
            const rewards = {
                coins: 100 * (data.quality_score || 0.5),
                xp: 50 * (data.quality_score || 0.5)
            };
            
            this.rewards.push(rewards);
            
            // Show reward notification
            this.showRewardNotification(rewards);
        }
    }
    
    async suggestNextSteps(data) {
        // Suggest monetization opportunities
        if (this.userTier === 'free' && data.quality_score > 0.8) {
            this.showUpgradeSuggestion({
                title: 'Great Quality!',
                message: 'Upgrade to Pro to remove watermarks and unlock premium features',
                cta: 'Upgrade Now'
            });
        }
    }
    
    setupMonetizationUI() {
        // Add monetization indicators to UI
        const generatorContainer = document.querySelector('.generator-frame-content');
        if (generatorContainer) {
            const monetizationBar = document.createElement('div');
            monetizationBar.className = 'monetization-bar';
            monetizationBar.innerHTML = `
                <div class="tier-indicator">
                    <span class="tier-badge ${this.userTier}">${this.userTier.toUpperCase()}</span>
                    <span class="usage-count">${this.generationsThisMonth} / ${this.getLimit()} videos</span>
                </div>
                <button class="upgrade-btn" onclick="window.autoMonetization.showUpgradeModal()">Upgrade</button>
            `;
            generatorContainer.insertBefore(monetizationBar, generatorContainer.firstChild);
        }
    }
    
    getLimit() {
        const limits = {
            'free': 5,
            'pro': 50,
            'business': 'Unlimited',
            'enterprise': 'Unlimited'
        };
        return limits[this.userTier] || 5;
    }
    
    showUpgradeModal(reason) {
        // Show upgrade modal
        const modal = document.createElement('div');
        modal.className = 'upgrade-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h2>Upgrade Required</h2>
                <p>${reason}</p>
                <div class="tier-options">
                    <div class="tier-option">
                        <h3>Pro - $29/month</h3>
                        <ul>
                            <li>50 videos/month</li>
                            <li>No watermark</li>
                            <li>All themes</li>
                            <li>Priority processing</li>
                        </ul>
                        <button onclick="window.autoMonetization.upgrade('pro')">Upgrade to Pro</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    showFeatureSuggestion(suggestion) {
        // Show feature suggestion toast
        const toast = document.createElement('div');
        toast.className = 'feature-suggestion-toast';
        toast.innerHTML = `
            <h4>${suggestion.title}</h4>
            <p>${suggestion.message}</p>
            <button onclick="this.parentElement.remove()">Dismiss</button>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }
    
    showRewardNotification(rewards) {
        // Show reward notification
        const notification = document.createElement('div');
        notification.className = 'reward-notification';
        notification.innerHTML = `
            <span>+${rewards.coins} coins</span>
            <span>+${rewards.xp} XP</span>
        `;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }
    
    showUpgradeSuggestion(suggestion) {
        // Show upgrade suggestion
        const suggestionEl = document.createElement('div');
        suggestionEl.className = 'upgrade-suggestion';
        suggestionEl.innerHTML = `
            <h4>${suggestion.title}</h4>
            <p>${suggestion.message}</p>
            <button onclick="window.autoMonetization.upgrade('pro')">${suggestion.cta}</button>
        `;
        document.body.appendChild(suggestionEl);
    }
    
    async upgrade(tier) {
        // Handle upgrade
        window.location.href = `/vidgenerator/upgrade?tier=${tier}`;
    }
}

// Initialize
let simplifiedGenerator = null;
let autoMonetization = null;

document.addEventListener('DOMContentLoaded', () => {
    simplifiedGenerator = new SimplifiedTwoPhaseGenerator();
    autoMonetization = new AutoMonetization();
    window.simplifiedGenerator = simplifiedGenerator;
    window.autoMonetization = autoMonetization;
});

