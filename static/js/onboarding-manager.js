/**
 * Onboarding Manager
 * Manages the onboarding flow for new users
 */
class OnboardingManager {
    constructor() {
        this.apiBase = '/api';
        this.userId = this.getUserId();
        this.currentStep = null;
        this.steps = [
            {id: 'welcome', name: 'Welcome', required: true, skipable: false},
            {id: 'profile_setup', name: 'Profile Setup', required: false, skipable: true},
            {id: 'skill_path', name: 'Skill Path Selection', required: true, skipable: false},
            {id: 'first_actions', name: 'First Actions', required: true, skipable: false},
            {id: 'dashboard_tour', name: 'Dashboard Tour', required: false, skipable: true},
            {id: 'complete', name: 'Complete', required: true, skipable: false}
        ];
        this.progress = null;
    }

    /**
     * Get user ID from localStorage or generate one
     */
    getUserId() {
        let userId = localStorage.getItem('game_user_id') || localStorage.getItem('user_id');
        
        if (!userId) {
            // Generate a temporary user ID
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('game_user_id', userId);
            localStorage.setItem('user_id', userId);
        }
        
        return userId;
    }

    /**
     * Check if user needs onboarding
     */
    async checkOnboardingStatus() {
        try {
            const response = await fetch(`${this.apiBase}/user/onboarding/status?user_id=${this.userId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    return data.status;
                }
            }
        } catch (error) {
            console.warn('Error checking onboarding status:', error);
        }
        
        // Default: check localStorage
        const onboarded = localStorage.getItem('user_onboarded');
        return {
            onboarding_started: false,
            onboarding_completed: onboarded === 'true',
            current_step: null,
            progress_percentage: onboarded === 'true' ? 100 : 0
        };
    }

    /**
     * Start onboarding
     */
    async start() {
        try {
            // First, ensure user exists
            await this.ensureUserExists();
            
            const response = await fetch(`${this.apiBase}/user/onboarding/start`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: this.userId})
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.progress = data.progress;
                    this.currentStep = data.progress.current_step;
                    return true;
                }
            }
        } catch (error) {
            console.error('Error starting onboarding:', error);
        }
        return false;
    }

    /**
     * Ensure user exists (create if needed)
     */
    async ensureUserExists() {
        try {
            // Check if user exists
            const checkResponse = await fetch(`${this.apiBase}/user/profile/${this.userId}`);
            if (checkResponse.ok) {
                const checkData = await checkResponse.json();
                if (checkData.success && checkData.profile) {
                    return true; // User exists
                }
            }
            
            // Create user
            const createData = {
                user_id: this.userId,
                device_fingerprint: this.getDeviceFingerprint(),
                screen_width: window.screen.width,
                screen_height: window.screen.height,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                language: navigator.language,
                referral_source: document.referrer ? 'external' : 'direct',
                referral_url: document.referrer || '',
                landing_page: window.location.pathname
            };
            
            const response = await fetch(`${this.apiBase}/user/create`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(createData)
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.success;
            }
        } catch (error) {
            console.error('Error ensuring user exists:', error);
        }
        return false;
    }

    /**
     * Get device fingerprint
     */
    getDeviceFingerprint() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('Device fingerprint', 2, 2);
        
        const fingerprint = [
            navigator.userAgent,
            navigator.language,
            screen.width + 'x' + screen.height,
            new Date().getTimezoneOffset(),
            canvas.toDataURL()
        ].join('|');
        
        // Simple hash
        let hash = 0;
        for (let i = 0; i < fingerprint.length; i++) {
            const char = fingerprint.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        
        return Math.abs(hash).toString(36);
    }

    /**
     * Complete a step
     */
    async completeStep(stepId, stepData = {}) {
        try {
            const response = await fetch(`${this.apiBase}/user/onboarding/complete-step`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    step_id: stepId,
                    step_data: stepData
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.progress = data.progress;
                    this.currentStep = data.progress.current_step;
                    
                    // If complete, mark in localStorage
                    if (data.progress.onboarding_completed) {
                        localStorage.setItem('user_onboarded', 'true');
                    }
                    
                    return true;
                }
            }
        } catch (error) {
            console.error('Error completing step:', error);
        }
        return false;
    }

    /**
     * Skip a step
     */
    async skipStep(stepId) {
        try {
            const response = await fetch(`${this.apiBase}/user/onboarding/skip`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: this.userId,
                    step_id: stepId
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.progress = data.progress;
                    this.currentStep = data.progress.current_step;
                    return true;
                }
            }
        } catch (error) {
            console.error('Error skipping step:', error);
        }
        return false;
    }

    /**
     * Get current progress
     */
    async getProgress() {
        try {
            const response = await fetch(`${this.apiBase}/user/onboarding/progress?user_id=${this.userId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.progress = data.progress;
                    this.currentStep = data.progress.current_step;
                    return data.progress;
                }
            }
        } catch (error) {
            console.warn('Error getting progress:', error);
        }
        return null;
    }

    /**
     * Show onboarding modal
     */
    showOnboardingModal(stepId) {
        const step = this.steps.find(s => s.id === stepId);
        if (!step) return;

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'onboarding-modal';
        modal.id = 'onboarding-modal';
        modal.innerHTML = `
            <div class="onboarding-overlay"></div>
            <div class="onboarding-content">
                <div class="onboarding-header">
                    <h2>${step.name}</h2>
                    <button class="onboarding-close" onclick="window.onboardingManager.closeModal()">×</button>
                </div>
                <div class="onboarding-body" id="onboarding-step-content">
                    <!-- Step content will be loaded here -->
                </div>
                <div class="onboarding-footer">
                    <div class="onboarding-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${this.progress?.progress_percentage || 0}%"></div>
                        </div>
                        <span class="progress-text">${this.progress?.progress_percentage || 0}% Complete</span>
                    </div>
                    <div class="onboarding-actions">
                        ${step.skipable ? `<button class="btn-skip" onclick="window.onboardingManager.skipStep('${stepId}')">Skip</button>` : ''}
                        <button class="btn-next" onclick="window.onboardingManager.nextStep()">Next</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.loadStepContent(stepId);
    }

    /**
     * Load step content
     */
    loadStepContent(stepId) {
        const contentDiv = document.getElementById('onboarding-step-content');
        if (!contentDiv) return;

        let content = '';
        
        switch(stepId) {
            case 'welcome':
                content = `
                    <div class="welcome-step">
                        <h3>Welcome to MasterNoder!</h3>
                        <p>We're excited to have you here. Let's get you started with a quick setup.</p>
                        <div class="welcome-features">
                            <div class="feature-item">
                                <i class="fas fa-robot"></i>
                                <span>AI Agent Skills</span>
                            </div>
                            <div class="feature-item">
                                <i class="fas fa-chart-line"></i>
                                <span>Points & Rewards</span>
                            </div>
                            <div class="feature-item">
                                <i class="fas fa-users"></i>
                                <span>Social Features</span>
                            </div>
                        </div>
                    </div>
                `;
                break;
                
            case 'profile_setup':
                content = `
                    <div class="profile-setup-step">
                        <h3>Set Up Your Profile</h3>
                        <p>Tell us a bit about yourself (optional)</p>
                        <form id="profile-setup-form">
                            <div class="form-group">
                                <label>Display Name</label>
                                <input type="text" name="display_name" placeholder="Enter your name">
                            </div>
                            <div class="form-group">
                                <label>Bio (Optional)</label>
                                <textarea name="bio" placeholder="Tell us about yourself"></textarea>
                            </div>
                        </form>
                    </div>
                `;
                break;
                
            case 'skill_path':
                content = `
                    <div class="skill-path-step">
                        <h3>Choose Your Skill Path</h3>
                        <p>Select a path that matches your interests</p>
                        <div class="skill-paths">
                            <div class="skill-path-card" data-path="balanced" onclick="window.onboardingManager.selectSkillPath('balanced')">
                                <h4>Balanced</h4>
                                <p>Mix of all skills</p>
                            </div>
                            <div class="skill-path-card" data-path="creator" onclick="window.onboardingManager.selectSkillPath('creator')">
                                <h4>Creator</h4>
                                <p>Content creation focus</p>
                            </div>
                            <div class="skill-path-card" data-path="battle" onclick="window.onboardingManager.selectSkillPath('battle')">
                                <h4>Battle</h4>
                                <p>Strategy and tactics</p>
                            </div>
                            <div class="skill-path-card" data-path="social" onclick="window.onboardingManager.selectSkillPath('social')">
                                <h4>Social</h4>
                                <p>Community building</p>
                            </div>
                            <div class="skill-path-card" data-path="analytics" onclick="window.onboardingManager.selectSkillPath('analytics')">
                                <h4>Analytics</h4>
                                <p>Data and insights</p>
                            </div>
                        </div>
                    </div>
                `;
                break;
                
            case 'first_actions':
                content = `
                    <div class="first-actions-step">
                        <h3>Your First Actions</h3>
                        <p>Let's get you started with some quick tasks</p>
                        <div class="action-list">
                            <div class="action-item">
                                <i class="fas fa-check-circle"></i>
                                <span>Explore the dashboard</span>
                            </div>
                            <div class="action-item">
                                <i class="fas fa-circle"></i>
                                <span>Try the generator</span>
                            </div>
                            <div class="action-item">
                                <i class="fas fa-circle"></i>
                                <span>Check your points</span>
                            </div>
                        </div>
                    </div>
                `;
                break;
                
            case 'dashboard_tour':
                content = `
                    <div class="dashboard-tour-step">
                        <h3>Dashboard Tour</h3>
                        <p>Let's take a quick tour of your dashboard</p>
                        <div class="tour-points">
                            <p>• View your points and stats</p>
                            <p>• Check your agent skills</p>
                            <p>• See your achievements</p>
                            <p>• Access all features</p>
                        </div>
                    </div>
                `;
                break;
                
            case 'complete':
                content = `
                    <div class="complete-step">
                        <h3>🎉 You're All Set!</h3>
                        <p>Welcome to MasterNoder! You're ready to start your journey.</p>
                        <div class="completion-bonus">
                            <p><strong>Welcome Bonus:</strong> 100 XP Points</p>
                        </div>
                    </div>
                `;
                break;
        }
        
        contentDiv.innerHTML = content;
    }

    /**
     * Select skill path
     */
    async selectSkillPath(path) {
        // Update UI
        document.querySelectorAll('.skill-path-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-path="${path}"]`).classList.add('selected');
        
        // Save selection (will be used when completing step)
        this.selectedSkillPath = path;
    }

    /**
     * Next step
     */
    async nextStep() {
        if (this.currentStep === 'skill_path' && this.selectedSkillPath) {
            // Save skill path selection
            await this.completeStep('skill_path', {skill_path: this.selectedSkillPath});
        } else {
            await this.completeStep(this.currentStep);
        }
        
        // Move to next step
        if (this.progress && this.progress.current_step !== 'complete') {
            this.showOnboardingModal(this.progress.current_step);
        } else {
            this.closeModal();
            localStorage.setItem('user_onboarded', 'true');
        }
    }

    /**
     * Close modal
     */
    closeModal() {
        const modal = document.getElementById('onboarding-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Initialize onboarding
     */
    async init() {
        const status = await this.checkOnboardingStatus();
        
        if (!status.onboarding_completed && !status.onboarding_started) {
            // Start onboarding
            await this.start();
            if (this.currentStep) {
                this.showOnboardingModal(this.currentStep);
            }
        } else if (status.onboarding_started && !status.onboarding_completed) {
            // Resume onboarding
            await this.getProgress();
            if (this.currentStep) {
                this.showOnboardingModal(this.currentStep);
            }
        }
    }
}

// Initialize on page load
if (typeof window !== 'undefined') {
    window.onboardingManager = new OnboardingManager();
    
    // Auto-start onboarding if needed
    document.addEventListener('DOMContentLoaded', () => {
        // Check if user should see onboarding
        const shouldShowOnboarding = !localStorage.getItem('user_onboarded');
        if (shouldShowOnboarding) {
            setTimeout(() => {
                window.onboardingManager.init();
            }, 1000); // Wait 1 second after page load
        }
    });
}
